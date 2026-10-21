# 第 19 篇：后处理效果

> **本卷定位**: 第二卷 渲染系统（12 篇）  
> **前置知识**: 第 18 篇《2D 渲染》  
> **难度**: ⭐⭐⭐⭐ 高级
>
> **本章导读**：
> 本章把 Godot 4.3 的后处理拆成两半来讲。
> 前半是**引擎内置**的效果：色调映射、泛光、SSAO、SSR、景深、色彩校正——每一项都给出 4.3 里真实存在的属性名，并标出那些"看起来像但其实没有"的坑。
> 后半是**自定义**后处理：Compositor / CompositorEffect 的 5 个回调点、4.3 的硬性限制，以及为什么铺一张 `canvas_item` 贴图**不叫**后处理。
> 读完你应该能分清"这个需求该用 `Environment` 还是该用 `Compositor`"，并且知道每种做法在 4.3 里的边界在哪。

---

## 📖 本章导读

后处理（Post-processing）是在场景渲染完成后，对最终图像进行屏幕空间处理的技术。从基本的色调映射到复杂的景深、运动模糊，后处理效果极大提升了游戏的视觉质量和艺术风格。

Godot 4.x 提供了强大的后处理系统，基于 Vulkan 的计算着色器和屏幕空间技术，支持多种高质量后处理效果。

---

## 🎯 学习目标

- 理解后处理渲染架构
- 掌握 WorldEnvironment 配置
- 熟悉常用后处理效果
- 掌握 `Environment` 上各效果属性的真实名字与限制
- 学会用 Compositor / CompositorEffect 写自定义后处理
- 掌握后处理性能优化技巧

---

## 1. 后处理架构

### 1.1 后处理渲染管线

```
后处理渲染流程:
┌─────────────────────────────────────────────────────────────┐
│                      后处理渲染管线                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 场景渲染                                                  │
│     └─▶ 渲染 3D/2D 场景到帧缓冲                               │
│                                                             │
│  2. 色调映射（Tone Mapping）                                 │
│     └─▶ HDR → LDR 转换                                       │
│                                                             │
│  3. 色彩校正（Color Correction）                             │
│     └─▶ 调整亮度、对比度、饱和度                             │
│                                                             │
│  4. 屏幕空间特效                                              │
│     └─▶ SSAO、SSR、景深等                                    │
│                                                             │
│  5. 泛光（Bloom）                                            │
│     └─▶ 高光区域模糊叠加                                     │
│                                                             │
│  6. 抗锯齿（Anti-aliasing）                                  │
│     └─▶ FXAA、SMAA、TAA                                      │
│                                                             │
│  7. 胶片颗粒/晕影                                             │
│     └─▶ 艺术效果                                             │
│                                                             │
│  8. 输出到屏幕                                                │
│     └─▶ 最终图像呈现                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

> 这张图是**概念图**，不是源码里的真实 pass 顺序。Godot 4.7.2 的实际 pass 顺序由 `servers/rendering/renderer_rd/renderer_scene_render_rd.cpp` 的 `_render_scene()` 决定，深度预通道、OIT、SDFGI、体积雾各自插在什么位置要看那段代码——第 14 篇《场景渲染流程》会逐行拆。

### 1.2 WorldEnvironment 节点

```gdscript
# 创建世界环境
var world_env = WorldEnvironment.new()
var env = Environment.new()

# 背景设置
env.background_mode = Environment.BG_SKY
env.background_color = Color(0.1, 0.1, 0.2)
env.sky = load("res://skybox.tres")

# 环境光
env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
env.ambient_light_energy = 0.5
env.ambient_light_color = Color(0.5, 0.6, 0.7)

# 应用环境
world_env.environment = env
add_child(world_env)
```

`WorldEnvironment` 上只有三个成员：

| 属性 | 说明 |
|---|---|
| `WorldEnvironment.environment` | `Environment` 资源 |
| `WorldEnvironment.camera_attributes` | 默认的相机属性（景深、自动曝光） |
| `WorldEnvironment.compositor` | `Compositor` 资源（见第 8 节） |

---

## 2. 色调映射（Tone Mapping）

### 2.1 色调映射模式

```gdscript
# 色调映射设置
env.tonemap_mode = Environment.TONE_MAPPER_ACES  # 推荐
# env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
# env.tonemap_mode = Environment.TONE_MAPPER_REINHARDT
# env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
```

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| ACES | 电影级色彩，自然过渡 | 高质量游戏、电影感 |
| Filmic | 胶片曲线，柔和对比 | 艺术风格游戏 |
| Reinhardt | 经典算法，平衡性好 | 通用场景 |
| Linear | 线性映射，无压缩 | HDR 显示、调试 |

> 4.3 的 `Environment.ToneMapper` 枚举只有这 4 个值。Godot 3.x 曾经有 `TONE_MAPPER_FILMIC` 之外的若干实验性选项，4.x 全部收敛成这四个。

### 2.2 曝光控制

```gdscript
# 整体曝光倍率（4.x 的 Environment 只有 tonemap_exposure）
env.tonemap_exposure = 1.0

# 自动曝光属于相机属性，需挂到 Camera3D 的 attributes 上
var attrs := CameraAttributesPractical.new()
attrs.auto_exposure_enabled = true
attrs.auto_exposure_scale = 0.4
attrs.auto_exposure_speed = 0.5
camera.attributes = attrs
```

| 属性 | 归属 | 说明 |
|---|---|---|
| `Environment.tonemap_exposure` | `Environment` | 全局曝光倍率 |
| `Environment.tonemap_white` | `Environment` | 色调映射的白点 |
| `CameraAttributes.exposure_multiplier` | 相机属性（基类） | 单台相机的曝光倍率 |
| `CameraAttributes.exposure_sensitivity` | 相机属性（基类） | 手动曝光感光度 |
| `CameraAttributes.auto_exposure_enabled` | 相机属性（基类） | 开关自动曝光 |
| `CameraAttributes.auto_exposure_scale` | 相机属性（基类） | 自动曝光的调节范围 |
| `CameraAttributes.auto_exposure_speed` | 相机属性（基类） | 自动曝光的过渡速度 |
| `CameraAttributesPractical.auto_exposure_min_sensitivity` | 相机属性（子类） | 自动曝光的最小感光度 |
| `CameraAttributesPractical.auto_exposure_max_sensitivity` | 相机属性（子类） | 自动曝光的最大感光度 |

> 自动曝光的三个开关（`auto_exposure_enabled` / `auto_exposure_scale` / `auto_exposure_speed`）定义在**基类** `CameraAttributes` 上；两个感光度上下限（`auto_exposure_min_sensitivity` / `auto_exposure_max_sensitivity`）定义在**子类** `CameraAttributesPractical` 上。4.3 的 `CameraAttributes` 只有 5 个成员，多的那两个别写错类。

---

## 3. 泛光效果（Bloom）

### 3.1 泛光原理

```
泛光处理流程:
1. 提取高光区域（亮度阈值）
2. 高斯模糊（多次迭代）
3. 与原图叠加
```

### 3.2 泛光设置

```gdscript
# 启用泛光
env.glow_enabled = true
env.glow_intensity = 0.8           # 整体亮度倍率（默认 0.8）
env.glow_strength = 1.0            # 模糊扩散强度（默认 1.0）
env.glow_bloom = 0.0               # 让低于 HDR 阈值的暗部也参与泛光
env.glow_hdr_threshold = 1.0       # HDR 泛光的亮度阈值
env.glow_hdr_scale = 2.0           # HDR 泛光的溢出比例
env.glow_hdr_luminance_cap = 12.0  # HDR 泛光的亮度上限

# 泛光级别：1~7 级，越高级越模糊（默认只开启第 3 级）
env.set_glow_level(3, 1.0)
env.set_glow_level(4, 0.5)

# 泛光混合方式
env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
env.glow_mix = 0.05                # 仅 GLOW_BLEND_MODE_MIX 时生效
env.glow_normalized = false        # 各级别强度是否归一化

# 镜头脏污（可选）
env.glow_map = load("res://lens_dirt.png")
env.glow_map_strength = 0.8
```

> **4.3 的真实属性集**是 `glow_enabled` / `glow_levels`(1..7) / `glow_normalized` / `glow_intensity` / `glow_strength` / `glow_mix` / `glow_bloom` / `glow_blend_mode` / `glow_hdr_threshold` / `glow_hdr_scale` / `glow_hdr_luminance_cap` / `glow_map` / `glow_map_strength`。
>
> `glow_blur` 与 `glow_color` **都不存在**：模糊的"范围"由 `glow_strength` 与各级别决定，颜色则由 `glow_blend_mode` 决定（`GLOW_BLEND_MODE_ADDITIVE` / `SCREEN` / `SOFTLIGHT` / `REPLACE` / `MIX`）。

> 7 个泛光级别在属性列表里是 `glow_levels/1` … `glow_levels/7` 七个**独立槽位**（索引属性），面板上显示成一行 7 个滑杆。脚本里用 `Environment.set_glow_level(index, energy)` / `Environment.get_glow_level(index)` 读写，**没有**一个叫 `glow_levels` 的普通属性。

### 3.3 自定义泛光

```glsl
// 自定义泛光着色器
shader_type spatial;
render_mode unshaded;

uniform float bloom_threshold = 1.0;
uniform float bloom_intensity = 0.5;
uniform float bloom_blur = 1.0;

void fragment() {
    vec4 color = texture(TEXTURE, UV);

    // 提取高光
    float brightness = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 bloom = max(color.rgb - bloom_threshold, vec3(0.0));

    // 应用强度
    bloom *= bloom_intensity;

    // 输出
    ALBEDO = color.rgb + bloom;
}
```

> ⚠️ 这段代码是**材质着色器**，不是后处理 pass：它作用在**某一个物体**的表面上，不是作用在整帧画面上。要对整帧做泛光，用 `Environment.glow_enabled` / `glow_intensity`，或者用第 8 节的 Compositor。

---

## 4. 屏幕空间环境光遮蔽（SSAO）

### 4.1 SSAO 原理

```
SSAO 计算流程:
1. 从深度缓冲重建世界空间位置
2. 在半球内采样多个点
3. 比较采样点深度
4. 计算遮蔽因子
5. 应用到环境光
```

### 4.2 SSAO 设置

```gdscript
# 启用 SSAO（仅 Forward+ 支持）
env.ssao_enabled = true
env.ssao_radius = 1.0             # 遮蔽半径
env.ssao_intensity = 2.0          # 遮蔽强度
env.ssao_power = 1.5              # 遮蔽分布曲线
env.ssao_detail = 0.5             # 细节层强度
env.ssao_horizon = 0.06           # 地平线判定阈值
env.ssao_sharpness = 0.98         # 边缘锐度
env.ssao_light_affect = 0.0       # 对直接光的影响
env.ssao_ao_channel_affect = 0.0  # 对材质 AO 贴图的影响
```

> 4.3 的 `Environment` 上**没有** `ssao_quality`、`Environment.SSAO_QUALITY_HIGH`、`ssao_bias` 这三个东西。质量档位（`RenderingServer.ENV_SSAO_QUALITY_VERY_LOW` ~ `ENV_SSAO_QUALITY_ULTRA`）是渲染服务器内部的参数，`Environment` 不暴露对应属性；偏差也不由材质提供，而是由引擎在深度重建时统一处理。

### 4.3 主要参数

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> SSAO 的实际开销随屏幕分辨率、采样质量与目标硬件变化很大，请在目标平台实测。

| 参数 | 典型值 | 作用 | 开销影响 |
|------|--------|------|----------|
| `ssao_radius` | 1.0 | 遮蔽的空间半径 | 半径越大，采样范围越远，质量越好也越慢 |
| `ssao_intensity` | 2.0 | 遮蔽强度倍率 | 只影响观感，基本不影响开销 |
| `ssao_power` | 1.5 | 遮蔽的分布曲线 | 影响暗部过渡 |
| `ssao_detail` | 0.5 | 细节层强度 | 增加细节采样开销 |
| `ssao_sharpness` | 0.98 | 边缘锐度 | 低会造成物体边缘发糊 |

---

## 5. 屏幕空间反射（SSR）

### 5.1 SSR 原理

```
SSR 计算流程:
1. 从深度缓冲重建世界空间
2. 射线追踪屏幕空间
3. 查找反射交点
4. 采样反射颜色
5. 混合到最终图像
```

### 5.2 SSR 设置

```gdscript
# 启用 SSR（仅 Forward+ 支持）
env.ssr_enabled = true
env.ssr_max_steps = 64        # 屏幕空间步进的最大步数，越高越准也越慢
env.ssr_fade_in = 0.15        # 从被反射物体到反射命中点的淡入距离
env.ssr_fade_out = 2.0        # 从反射命中点到"全局"反射的淡出距离
env.ssr_depth_tolerance = 0.2 # 深度容差
```

> 4.3 的 SSR 属性只有 `ssr_enabled` / `ssr_max_steps` / `ssr_fade_in` / `ssr_fade_out` / `ssr_depth_tolerance` 五个。`ss_reflections_enabled` / `ss_reflections_quality` / `ss_reflections_max_roughness` / `ss_reflections_roughness_layers` 全是拼写漂移，4.x 里并不存在。

### 5.3 SSR 优化

```
✅ 优化建议:
1. 限制反射距离
2. 降低粗糙度层级
3. 使用 SSR 淡出
4. 结合探针反射
5. 仅在需要时启用
```

---

## 6. 景深效果（Depth of Field）

### 6.1 景深类型

```gdscript
# 4.x 的景深由 CameraAttributesPractical 提供，不再挂在 Environment 上
var attrs := CameraAttributesPractical.new()
attrs.dof_blur_far_enabled = true
attrs.dof_blur_far_distance = 10.0   # 远焦开始模糊的距离
attrs.dof_blur_far_transition = 5.0  # 过渡带宽度
attrs.dof_blur_near_enabled = true
attrs.dof_blur_near_distance = 2.0   # 近焦开始模糊的距离
attrs.dof_blur_amount = 0.05         # 模糊强度（0-0.1）
camera.attributes = attrs
```

`CameraAttributesPractical` 的**全部**成员只有这 9 个：

| 属性 | 说明 |
|---|---|
| `CameraAttributesPractical.dof_blur_far_enabled` | 远焦模糊开关 |
| `CameraAttributesPractical.dof_blur_far_distance` | 远焦开始距离 |
| `CameraAttributesPractical.dof_blur_far_transition` | 远焦过渡带宽度 |
| `CameraAttributesPractical.dof_blur_near_enabled` | 近焦模糊开关 |
| `CameraAttributesPractical.dof_blur_near_distance` | 近焦开始距离 |
| `CameraAttributesPractical.dof_blur_near_transition` | 近焦过渡带宽度 |
| `CameraAttributesPractical.dof_blur_amount` | 模糊总强度（0~0.1） |
| `CameraAttributesPractical.auto_exposure_min_sensitivity` | 自动曝光的最低灵敏度 |
| `CameraAttributesPractical.auto_exposure_max_sensitivity` | 自动曝光的最高灵敏度 |

> 加上基类 `CameraAttributes` 的 5 个曝光属性，`CameraAttributesPractical` 一共 **14** 个成员。除此之外它**没有任何** `motion_blur_*`——4.3 根本没有运动模糊。

### 6.2 景深效果

| 参数 | 影响 | 推荐值 |
|------|------|--------|
| dof_blur_far_distance | 远景开始模糊的距离 | 根据场景调整 |
| dof_blur_far_transition | 远景过渡带宽度 | 5-20 |
| dof_blur_near_distance | 近景开始模糊的距离 | 1-3 |
| dof_blur_amount | 模糊强度 | 0.03-0.08 |

### 6.3 动态景深

```gdscript
# 动态焦点（跟随玩家）
func _process(delta):
    var player_pos = player.global_transform.origin
    var camera_pos = camera.global_transform.origin
    var distance = player_pos.distance_to(camera_pos)

    # 更新远焦距离
    camera_attributes.dof_blur_far_distance = distance
```

---

## 7. 色彩校正（Color Correction）

### 7.1 基础调整

```gdscript
# 色彩调整（需要先打开 adjustment_enabled）
env.adjustment_enabled = true
env.adjustment_brightness = 1.0
env.adjustment_contrast = 1.0
env.adjustment_saturation = 1.0
```

> 4.3 的 `Environment` 上**没有** `adjustment_color_correction_curve`——它既不是属性名，类型也不对（`Curve` 资源）。色彩校正曲线在 4.x 里是用 **LUT 纹理**（`adjustment_color_correction`）来表达的：1 维用 `GradientTexture1D`，复杂曲线用 `Texture3D`。

### 7.2 色彩查找表（LUT）

```gdscript
# 使用 LUT 进行色彩校正
# adjustment_color_correction 的类型是 Texture（Texture2D / Texture3D）
env.adjustment_enabled = true
env.adjustment_color_correction = load("res://lut.png")   # Texture2D
# 或者用一维 LUT：
# env.adjustment_color_correction = load("res://lut_1d.tres")  # GradientTexture1D
# 复杂 LUT 用 Texture3D：
# env.adjustment_color_correction = load("res://lut_3d.tres")

# ⚠️ 4.x 的任何版本都不能手动设 use_1d_color_correction——它不是脚本属性
# env.use_1d_color_correction = true   # ← 4.3 到 4.8 都会报 Invalid set index
# 引擎按 adjustment_color_correction 的纹理类型自动决定走 2D LUT 还是 1D LUT
```

> `adjustment_color_correction_lut` 与 `adjustment_color_correction_lut_scale` 在 4.3 **不存在**——`adjustment_color_correction` 本身就是那个 LUT 贴图，缩放由贴图本身的尺寸决定。
>
> ⚠️ **`use_1d_color_correction` 从来就不是脚本可设的属性**。它是 `Environment` 的**内部成员**（`scene/resources/environment.h:223`），从 4.3 起就存在，但**从来没有**出现在 4.3 到 4.8 的类参考里。引擎根据 `adjustment_color_correction` 的纹理类型**自动派生**它：喂 `Texture2D` 走 2D LUT，喂 `GradientTexture1D` 走 1D LUT（`scene/resources/environment.cpp:1081-1083`）。
>
> 所以在 4.3 写 `env.use_1d_color_correction = true` 确实会报 `Invalid set index`——但**别以为 4.4 之后就能手动选了**，那一版起它同样不能手动设。

### 7.3 2D 叠加式调色（注意：这不是 3D 后处理）

下面这个 `canvas_item` 着色器**不是** Godot 的 3D 后处理机制，它只是一个铺在全屏 `ColorRect` / `TextureRect` 上的 2D 图层：

```glsl
// 2D 叠加层着色器（铺在 ColorRect 上）
shader_type canvas_item;

uniform float brightness = 1.0;
uniform float contrast = 1.0;
uniform float saturation = 1.0;
uniform vec3 tint = vec3(1.0);

void fragment() {
    vec4 color = texture(TEXTURE, UV);

    color.rgb *= brightness;
    color.rgb = (color.rgb - 0.5) * contrast + 0.5;
    float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    color.rgb = mix(vec3(gray), color.rgb, saturation);
    color.rgb *= tint;

    COLOR = color;
}
```

> 它的作用范围只限于这个 CanvasItem 覆盖的屏幕区域，**不会**作用于 3D 场景本身，也不会参与色调映射与 GI。真正要接管 3D 后处理管线，见下一节的 Compositor / CompositorEffect。

---

## 8. 自定义后处理：Compositor / CompositorEffect

Godot 4.3 提供了**真正**的后处理扩展点：`Compositor` 资源 + `CompositorEffect` 抽象资源。`CompositorEffect` 会在渲染线程上的指定阶段回调，把额外的 pass 插入到 3D 渲染管线里。

这两个类都定义在 `scene/resources/compositor.cpp`（同一个文件里），类参考分别是 `Compositor.xml` 与 `CompositorEffect.xml`。

### 8.1 为什么铺一张 canvas_item 贴图不算后处理

这是本章最需要先纠正的一个方向性问题。

| | 2D 叠加层（`canvas_item`） | 真正的后处理（Compositor） |
|---|---|---|
| 作用对象 | 一个 `CanvasItem` 覆盖的屏幕矩形 | 整帧 3D 渲染结果 |
| 在管线中的位置 | 3D 之后，作为独立的 2D 图层 | 3D 管线**内部**（不透明后 / 天空后 / 透明前 / 透明后） |
| 能否读到深度缓冲 | ❌ 读不到 | ✅ `RenderSceneBuffersRD` |
| 能否读到运动矢量 | ❌ | ✅（需 `needs_motion_vectors`） |
| 能否读到法线 / 粗糙度 | ❌ | ✅（需 `needs_normal_roughness`，Forward+ 限定） |
| 是否参与色调映射 | ❌ 排在色调映射之后 | ✅ 可以排在色调映射之前 |
| 是否影响 GI / 反射 | ❌ | ✅ |

一句话：**2D 叠加层是在"已经渲染完的画面"上再画一张图；后处理是在"渲染画面"这件事的中间插一脚。** 需求一旦涉及深度、屏幕空间坐标、或者要在色调映射之前动手脚，就只有 Compositor 能做。

### 8.2 两个资源的分工

| 资源 | 类型 | 职责 |
|---|---|---|
| `Compositor` | `Resource` | 效果**列表**的容器。把若干 `CompositorEffect` 打包，交给相机或世界环境 |
| `CompositorEffect` | `Resource`（抽象基类） | 真正的效果。必须继承并实现 `_render_callback` |

`Compositor` 在 4.3 只有**一个**成员：

| 成员 | 类型 | 说明 |
|---|---|---|
| `Compositor.compositor_effects` | `CompositorEffect[]` | 效果列表 |

> 它**没有** `add_effect()` 方法，也没有叫 `effects` 的属性，效果列表要直接赋给 `compositor_effects`。

`CompositorEffect` 在 4.3 的全部成员：

| 成员 | 类型 | 说明 |
|---|---|---|
| `CompositorEffect.enabled` | `bool` | 关掉就不生效，但保留在列表里 |
| `CompositorEffect.effect_callback_type` | `int` | 5 个回调点之一，决定回调插在管线哪一步 |
| `CompositorEffect.access_resolved_color` | `bool` | 开启 MSAA 时，先做一次颜色缓冲 resolve |
| `CompositorEffect.access_resolved_depth` | `bool` | 开启 MSAA 时，先做一次深度缓冲 resolve |
| `CompositorEffect.needs_motion_vectors` | `bool` | 让引擎在 opaque 阶段算出运动矢量 |
| `CompositorEffect.needs_normal_roughness` | `bool` | 让引擎在深度预通道里输出法线 + 粗糙度（**仅 Forward+**） |
| `CompositorEffect.needs_separate_specular` | `bool` | 把高光单独渲进一张缓冲，效果之后再合并（**仅 Forward+**） |
| `CompositorEffect._render_callback(effect_callback_type, render_data)` | 虚方法 | 回调本体 |

### 8.3 挂载方式

`Compositor` 可以挂在两个地方：

| 挂载点 | 属性 | 作用范围 |
|---|---|---|
| 相机 | `Camera3D.compositor` | 只影响这台相机渲染的视口 |
| 世界环境 | `WorldEnvironment.compositor` | 影响所有没有单独指定 compositor 的相机 |

```gdscript
# 1) 写一个继承 CompositorEffect 的脚本
# res://effects/my_effect.gd
extends CompositorEffect

func _render_callback(effect_callback_type: int, render_data: RenderData) -> void:
    if effect_callback_type != CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT:
        return
    var buffers := render_data.get_render_scene_buffers() as RenderSceneBuffersRD
    if buffers == null:
        return
    # 在这里用 RenderingDevice 插入你自己的渲染 pass
    # ...

# 2) 在场景里挂上 Compositor
var compositor := Compositor.new()
var effect := preload("res://effects/my_effect.gd").new()
effect.effect_callback_type = CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
effect.needs_normal_roughness = true      # 需要法线/粗糙度缓冲
effect.needs_motion_vectors = true        # 需要运动矢量缓冲
compositor.compositor_effects = [effect]  # 4.3 只有这一个成员

# 3) 挂到相机或 WorldEnvironment 上
$Camera3D.compositor = compositor
# 或：
$WorldEnvironment.compositor = compositor
```

底层对应的渲染服务器接口是 `RenderingServer.compositor_create()`、`RenderingServer.compositor_set_compositor_effects()`、`RenderingServer.compositor_effect_create()`、`RenderingServer.compositor_effect_set_callback()`、`RenderingServer.compositor_effect_set_enabled()`、`RenderingServer.compositor_effect_set_flag()`；相机侧的挂载是 `RenderingServer.camera_set_compositor()`，场景侧是 `RenderingServer.scenario_set_compositor()`。

> 顺序有意义：`compositor_effects` 数组里靠前的效果**先**执行。同一个回调点挂多个效果时，数组顺序就是执行顺序。

### 8.4 五个回调点

`CompositorEffect.EffectCallbackType` 决定回调插在管线的哪一步。下面的措辞直接取自 4.3 的 `CompositorEffect.xml`：

| 常量 | 值 | 官方描述 | 直觉理解 |
|---|---|---|---|
| `CompositorEffect.EFFECT_CALLBACK_TYPE_PRE_OPAQUE` | 0 | 在不透明渲染 pass **之前**、深度预通道（若启用）**之后**回调 | 拿到深度、还没画不透明物体 |
| `CompositorEffect.EFFECT_CALLBACK_TYPE_POST_OPAQUE` | 1 | 在不透明渲染 pass **之后**、天空渲染**之前**回调 | 物体已经画上去了，天还没画 |
| `CompositorEffect.EFFECT_CALLBACK_TYPE_POST_SKY` | 2 | 在天空渲染**之后**、back buffer 创建**之前**回调（若启用，还早于次表面散射与屏幕空间反射） | 场景完整了，但还没进后处理链 |
| `CompositorEffect.EFFECT_CALLBACK_TYPE_PRE_TRANSPARENT` | 3 | 在透明渲染 pass **之前**回调（此时天空已渲染、back buffer 已创建） | 要在透明物体之前插一刀 |
| `CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT` | 4 | 在透明渲染 pass **之后**、任何内置后处理与渲染目标输出**之前**回调 | 最"晚"的位置，几乎是最终画面 |
| `CompositorEffect.EFFECT_CALLBACK_TYPE_MAX` | 5 | 枚举大小 | 不是可用取值 |

把五个点连起来看：

```
深度预通道
    │
    ├── PRE_OPAQUE  ← 回调点 0
    │
不透明物体
    │
    ├── POST_OPAQUE ← 回调点 1
    │
天空
    │
    ├── POST_SKY    ← 回调点 2
    │
    │  （back buffer 创建 / SSS / SSR）
    │
    ├── PRE_TRANSPARENT ← 回调点 3
    │
透明物体
    │
    ├── POST_TRANSPARENT ← 回调点 4
    │
内置后处理（色调映射 / 泛光 / 抗锯齿 …）
    │
输出到渲染目标
```

> 选点的直觉：**想改"物体本身"就用 0/1；想改"天空参与之后的整体光照"就用 2；想在透明物体之前拦一道就用 3；想在最终输出前做最后的加工就用 4。**

### 8.5 4.3 的限制

这一节是 `CompositorEffect` 最容易踩坑的地方。4.7.2 的 `scene/resources/compositor.cpp` 里，`CompositorEffect::_validate_property()` 会按 `effect_callback_type` **隐藏**不适用的属性：

```cpp
void CompositorEffect::_validate_property(PropertyInfo &p_property) const {
    if (p_property.name == "access_resolved_color" && effect_callback_type == EFFECT_CALLBACK_TYPE_POST_TRANSPARENT) {
        p_property.usage = PROPERTY_USAGE_NONE;
    }
    if (p_property.name == "access_resolved_depth" && effect_callback_type == EFFECT_CALLBACK_TYPE_POST_TRANSPARENT) {
        p_property.usage = PROPERTY_USAGE_NONE;
    }
    if (p_property.name == "needs_separate_specular" && effect_callback_type != EFFECT_CALLBACK_TYPE_POST_SKY) {
        p_property.usage = PROPERTY_USAGE_NONE;
    }
}
```

翻译成使用规则：

| 标志 | 4.3 的生效条件 | 不满足时 |
|---|---|---|
| `access_resolved_color` | **只在** `EFFECT_CALLBACK_TYPE_POST_TRANSPARENT` 下有效 | 其它回调点下该属性在编辑器里被隐藏（`PROPERTY_USAGE_NONE`） |
| `access_resolved_depth` | **只在** `EFFECT_CALLBACK_TYPE_POST_TRANSPARENT` 下有效 | 同上 |
| `needs_separate_specular` | **只在** `EFFECT_CALLBACK_TYPE_POST_SKY` 下有效 | 其它回调点下被隐藏 |
| `needs_motion_vectors` | 无回调点限制 | 引擎在 opaque 阶段算运动矢量 |
| `needs_normal_roughness` | 额外要求 **Forward+ 渲染器** | Mobile / Compatibility 下拿不到 normal_roughness 缓冲 |

还有两条**渲染方法**层面的限制：

| 渲染方法 | 4.3 是否支持 CompositorEffect | 原因 |
|---|---|---|
| **Forward+** | ✅ 完全支持 | 走 `servers/rendering/renderer_rd/renderer_scene_render_rd.cpp`，由 `RendererSceneRenderRD::_process_compositor_effects()` 派发回调 |
| **Mobile** | ✅ 支持（但 `needs_normal_roughness` / `needs_separate_specular` 不可用） | 同样是 RD 渲染器，但不走 forward_clustered 的法线粗糙度缓冲 |
| **Compatibility（GLES3）** | ❌ **不支持** | 它有独立的一套场景渲染器（`drivers/gles3/rasterizer_scene_gles3.cpp`）和独立的缓冲对象类型（GLES3 自己的 RenderSceneBuffers 子类），整份文件里没有一处合成器回调派发代码 |

最后一条尤其重要：**把项目切到 Compatibility 渲染器时，`CompositorEffect` 会静默失效**——回调根本不会被调用，`render_data.get_render_scene_buffers()` 拿到的也不是 `RenderSceneBuffersRD`。所以在写自定义后处理前，第一件事是确认目标渲染方法。

还有一条容易忽略的限制：**渲染反射探针（ReflectionProbe）时会跳过全部合成器效果**。4.7.2 的 `RendererSceneRenderRD::_process_compositor_effects()` 开头就有这么一段判断——渲染数据里带着反射探针就直接 `return`。这意味着你在探针贴图里看到的是"没有自定义后处理"的画面，这是正常的。

另外两条使用纪律：

- 回调运行在**渲染线程**上，不是主线程；
- `render_data` **只在回调期间有效**，不能存下来下次再用。

### 8.6 缓冲区访问

回调里通过 `RenderData` 拿到渲染状态：

```gdscript
var render_data: RenderData          # 回调的第二个参数
render_data.get_render_scene_buffers()   # → RenderSceneBuffers
render_data.get_environment()           # → Environment
render_data.get_camera_attributes()     # → CameraAttributes
render_data.get_render_scene_data()     # → 场景端数据
```

拿到 `RenderSceneBuffers` 后要**转成** `RenderSceneBuffersRD`（`RenderSceneBuffers` 是基类，RD 是它的子类）：

```gdscript
var buffers := render_data.get_render_scene_buffers() as RenderSceneBuffersRD
if buffers == null:
    return
```

`RenderSceneBuffersRD` 上能取到的东西：

| 想要什么 | 取法 |
|---|---|
| 颜色缓冲 | `buffers.get_texture("render_buffers", "color")`（或 `buffers.get_color_texture()`） |
| 深度缓冲 | `buffers.get_texture("render_buffers", "depth")`（或 `buffers.get_depth_texture()`） |
| 运动矢量缓冲 | `buffers.get_velocity_texture()` |
| 法线 + 粗糙度缓冲 | `buffers.get_texture("forward_clustered", "normal_roughness")`（Forward+ 专用） |
| 渲染目标 | `buffers.get_render_target()` |
| 内部尺寸（放大前） | `buffers.get_internal_size()` |
| 目标尺寸（放大后） | `buffers.get_target_size()` |
| 3D MSAA 采样数 | `buffers.get_msaa_3d()` |
| 屏幕空间抗锯齿模式 | `buffers.get_screen_space_aa()` |
| 是否开了 TAA | `buffers.get_use_taa()` |
| 3D 缩放模式 | `buffers.get_scaling_3d_mode()` |
| 纹理采样数 | `buffers.get_texture_samples()` |
| 是否开了抖动（debanding） | `buffers.get_use_debanding()` |
| FSR 锐度 | `buffers.get_fsr_sharpness()` |
| 视图数（XR 双目） | `buffers.get_view_count()` |
| 判断某个名字的纹理是否存在 | `buffers.has_texture(context, name)` |

> 这些"缓冲名字"（`"render_buffers"` / `"forward_clustered"`）是渲染后端内部的命名空间，官方 `CompositorEffect.xml` 的成员说明里直接给出了取值，照抄即可。名字写错时 `get_texture()` 返回空 RID，不会崩溃——所以要**判空**。

### 8.7 最小可用例子

下面这个例子只做一件事：**在最终输出前，把整帧的饱和度压低**。它展示了完整的骨架，但真正"画"的部分需要 `RenderingDevice` 的底层调用。

```gdscript
# res://effects/desaturate.gd
extends CompositorEffect

var _rd: RenderingDevice
var _pipeline: RID = RID()
var _shader: RID = RID()
var _uniform_set: RID = RID()

func _init() -> void:
    # 渲染设备只在 RD 渲染器（Forward+ / Mobile）下可用
    _rd = RenderingServer.get_rendering_device()

func _render_callback(effect_callback_type: int, render_data: RenderData) -> void:
    # 回调可能在任意阶段被调用，这里只处理自己关心的那一个
    if effect_callback_type != CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT:
        return

    var buffers := render_data.get_render_scene_buffers() as RenderSceneBuffersRD
    if buffers == null:
        return

    # 要读已 resolve 的颜色缓冲，必须开 access_resolved_color，
    # 而它只在 POST_TRANSPARENT 下有效
    var color_tex := buffers.get_texture("render_buffers", "color")
    if color_tex == null:
        return

    # —— 到这里已经拿到后处理能用的颜色缓冲 ——
    #
    # 接下来用 RenderingDevice 手工搭一个全屏 pass：
    #   1) _rd.shader_create_from_spirv(...)     从 SPIR-V 创建着色器
    #   2) _rd.render_pipeline_create(...)        创建渲染管线
    #   3) _rd.uniform_set_create(...)            创建 uniform set
    #   4) _rd.draw_list_begin_for_screen(...)    开一个屏幕空间绘制列表
    #   5) 绑定管线 / 顶点数组 / 索引数组 / uniform set
    #   6) _rd.draw_list_draw(...) + _rd.draw_list_end(...)
    #
    # 这一段样板代码很长，官方 "Compositor" 教程给的是完整可运行版本；
    # 本章只把「怎么拿到缓冲、怎么判断自己在哪个阶段」这两件最关键的事讲清楚。
```

几个要点值得单独拎出来：

- `RenderingServer.get_rendering_device()` 在 **Compatibility 渲染器下返回空**，所以第一行就该判空；
- 回调里拿到的 `RenderSceneBuffersRD` 是**引擎内部对象**的脚本包装，不要长期持有；
- 用 `buffers.get_texture("render_buffers", "color")` 拿到的 RID 是引擎的纹理资源，**不能**直接 `RenderingDevice.texture_update()` 写它，只能作为采样源。

### 8.8 CompositorEffect 是实验性 API

4.3 的 `CompositorEffect.xml` 在类声明上带着 `experimental` 属性：

> "The implementation may change as more of the rendering internals are exposed over time."

也就是说，**API 可能在 4.x 的小版本之间变化**。实践建议：

1. 把 `CompositorEffect` 的使用**隔离**在一个或几个脚本里，不要散落在业务代码中；
2. 在项目里固定引擎版本（写进 `README`），升级时优先回归这几处；
3. 如果需求只是"调色 / 变暗 / 加颗粒"，用 `Environment.adjustment_brightness` / `adjustment_contrast` / `adjustment_saturation` 加上 LUT 就够了，不需要碰它；
4. 真正需要 `CompositorEffect` 的场景是：读深度、读运动矢量、读法线粗糙度、或者在色调映射之前插 pass。

### 8.9 Environment 还是 Compositor：选型表

| 需求 | 用什么 |
|---|---|
| 调亮度 / 对比度 / 饱和度 | `Environment.adjustment_brightness` / `adjustment_contrast` / `adjustment_saturation` |
| 套 LUT 做风格化 | `Environment.adjustment_color_correction` |
| 全局曝光、自动曝光 | `Environment.tonemap_exposure` + `CameraAttributes.auto_exposure_enabled` / `auto_exposure_scale` / `auto_exposure_speed` |
| 辉光 | `Environment.glow_enabled` / `glow_intensity` / `glow_strength` |
| 环境光遮蔽 | `Environment.ssao_enabled` / `ssao_radius` / `ssao_intensity` |
| 屏幕空间反射 | `Environment.ssr_enabled` / `ssr_max_steps` |
| 景深 | `CameraAttributesPractical.dof_blur_amount` / `dof_blur_far_distance` / `dof_blur_near_distance` |
| 体积雾 / 深度雾 | `Environment.volumetric_fog_enabled` / `volumetric_fog_density`；`Environment.fog_enabled` / `fog_density` |
| 景深之外的整体画面柔化 | `Environment` 没有；用 `Compositor` 或 2D 叠加层 |
| 读深度做描边 / 软粒子 | `Compositor`（`POST_TRANSPARENT`） |
| 读运动矢量做自定义 TAA | `Compositor`（需 `needs_motion_vectors`） |
| 在色调映射之前改颜色 | `Compositor`（`PRE_OPAQUE` / `POST_OPAQUE`） |
| 屏幕边缘渐晕 / 色差（只要求"看起来像"） | 2D 叠加层足够（见 7.3 / 10 节） |
| 屏幕边缘渐晕 / 色差（要求正确遮挡） | `Compositor` |

---

## 9. 抗锯齿（Anti-aliasing）

### 9.1 抗锯齿类型

```gdscript
# 项目设置中的抗锯齿
# 渲染 → 抗锯齿 → 质量

# 屏幕空间抗锯齿：0=关闭，1=FXAA，2=SMAA
ProjectSettings.set_setting("rendering/anti_aliasing/quality/screen_space_aa", 1)

# TAA（时间抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/use_taa", true)

# MSAA（多重采样抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 2)  # 2x, 4x, 8x
```

> 4.3 的 `ProjectSettings` **没有** `set()` 方法，只有 `set_setting()`。写 `ProjectSettings.set("a", b)` 会落到 `Object.set(property, value)`，把设置键当成属性名，结果是设置没生效、还可能刷一堆报错。

### 9.2 抗锯齿对比

| 类型 | 质量 | 性能 | 适用场景 |
|------|------|------|----------|
| FXAA | 低 | 极高 | 移动设备、性能优先 |
| SMAA | 中 | 高 | 中端 PC |
| TAA | 高 | 中 | 高端 PC、动态场景 |
| MSAA | 高 | 低 | 静态场景、VR |

---

## 10. 艺术效果

> 下面三个例子都是 `canvas_item` 着色器，用法是铺一个全屏 `ColorRect` / `TextureRect` 作为 **2D 叠加层**。它们**不是** 3D 后处理管线的一部分：不会参与色调映射，也不会影响 GI 与反射。要在 3D 管线里做这些效果，请走第 8 节的 Compositor / CompositorEffect。

### 10.1 胶片颗粒

```glsl
shader_type canvas_item;

uniform float grain_amount = 0.05;
uniform float grain_size = 1.0;

float random(vec2 uv) {
    return fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
    vec4 color = texture(TEXTURE, UV);

    // 添加颗粒
    float grain = random(UV * grain_size + TIME) * 2.0 - 1.0;
    color.rgb += grain * grain_amount;

    COLOR = color;
}
```

### 10.2 晕影效果

```glsl
shader_type canvas_item;

uniform float vignette_intensity = 0.3;
uniform float vignette_roundness = 0.5;

void fragment() {
    vec4 color = texture(TEXTURE, UV);

    // 计算晕影
    vec2 uv_center = UV - 0.5;
    float dist = length(uv_center);
    float vignette = 1.0 - smoothstep(0.5 - vignette_roundness,
                                       0.5 + vignette_roundness,
                                       dist);

    color.rgb *= mix(1.0, 0.0, vignette_intensity * vignette);

    COLOR = color;
}
```

### 10.3 色差效果

```glsl
shader_type canvas_item;

uniform float chromatic_aberration = 0.002;

void fragment() {
    vec2 uv = UV;
    vec2 center = vec2(0.5, 0.5);
    vec2 offset = (uv - center) * chromatic_aberration;

    float r = texture(TEXTURE, uv - offset).r;
    float g = texture(TEXTURE, uv).g;
    float b = texture(TEXTURE, uv + offset).b;

    COLOR = vec4(r, g, b, 1.0);
}
```

> 注意这三种效果都是"**整屏统一**"的——它们对 UI、粒子、HUD 一视同仁。如果只想给 3D 场景加晕影而不想压暗 UI，就得用 `Compositor` 在 3D 管线里做。

---

## 11. 性能优化

### 11.1 后处理性能分析

```
后处理性能开销排序（从高到低）:
1. TAA（时间抗锯齿）
2. SSR（屏幕空间反射）
3. 景深（DOF）
4. 体积雾
5. SSAO
6. 泛光
7. 色彩校正
8. FXAA/SMAA
```

> ⚠️ 上面是**经验排序**，不是实测数据。实际开销随分辨率、效果参数、渲染方法差异极大，请用第 22 篇《渲染调试工具》里的帧分析工具在目标硬件上实测。

### 11.2 优化策略

```
✅ 优化清单:
1. 根据目标平台选择质量级别
2. 使用 LOD 系统动态调整
3. 降低分辨率渲染后处理
4. 禁用不必要的效果
5. 使用计算着色器优化
6. 批处理后处理通道
7. 使用异步计算
8. 缓存中间结果
```

### 11.3 动态质量调整

```gdscript
# 根据帧率动态调整后处理质量
func _process(delta):
    var fps = Performance.get_monitor(Performance.TIME_FPS)

    if fps < 30:
        # 低帧率：降低质量
        env.ssao_enabled = false
        env.ssr_enabled = false
        camera_attributes.dof_blur_far_enabled = false
        env.glow_enabled = true
        env.set_glow_level(3, 1.0)
    elif fps < 60:
        # 中帧率：中等质量
        env.ssao_enabled = true
        env.ssao_radius = 0.5
        env.ssao_detail = 0.0
        env.ssr_enabled = false
        camera_attributes.dof_blur_far_enabled = true
        camera_attributes.dof_blur_amount = 0.03
        env.glow_enabled = true
        env.set_glow_level(5, 1.0)
    else:
        # 高帧率：高质量
        env.ssao_enabled = true
        env.ssao_radius = 1.0
        env.ssao_detail = 0.5
        env.ssr_enabled = true
        camera_attributes.dof_blur_far_enabled = true
        camera_attributes.dof_blur_amount = 0.05
        env.glow_enabled = true
        env.set_glow_level(7, 1.0)
```

> 4.3 的 `Environment` 上没有 `ssao_quality` 属性，质量只能靠 `ssao_radius` / `ssao_detail` / `ssao_intensity` 这类参数间接调节；`CameraAttributesPractical` 上也没有 `motion_blur_enabled`——4.3 根本没有运动模糊。

### 11.4 自定义后处理的开销

用 `CompositorEffect` 时要额外注意：

| 开销来源 | 说明 |
|---|---|
| 额外的全屏 pass | 每个 pass 都是一次全屏采样 + 一次全屏写回 |
| `needs_normal_roughness` | 让引擎在深度预通道里多输出一张法线粗糙度缓冲 |
| `needs_motion_vectors` | 让引擎在 opaque 阶段额外算运动矢量 |
| `access_resolved_color` / `access_resolved_depth` | 开启 MSAA 时多一次 resolve（全屏操作） |
| `needs_separate_specular` | 高光被单独渲进一张缓冲，之后再合并 |

所以：**能用 `Environment` 解决的，不要用 `CompositorEffect`**；能用一个 pass 解决的，不要拆成两个。

---

## 核心要点

1. **4.3 的后处理参数全在 `Environment` 与 `CameraAttributes` 上**，且每个属性名都要按 4.3 的真实拼写写：`ssr_enabled` / `ssao_enabled` / `glow_intensity` / `adjustment_color_correction`。
2. **4.7.2 仍没有运动模糊**：`Environment` 上没有任何 `motion_blur*` 属性，`CameraAttributesPractical` 的成员只有 `dof_blur_*` 与继承自基类的 `auto_exposure_*`。
3. **景深与自动曝光属于相机**（`CameraAttributesPractical`），不属于 `Environment`；`Environment` 上只有 `tonemap_exposure`。
4. **色彩校正是 LUT 贴图**（`adjustment_color_correction`，类型 `Texture`），不是 `Curve`；至于「一维 LUT」开关 `use_1d_color_correction`，截至 4.7.2 的 `Environment` 上**并没有**这个属性，写上去会直接报"属性不存在"。
5. **铺一张 `canvas_item` 贴图不是后处理**——它排在 3D 之后、只覆盖自己的屏幕区域、读不到深度与运动矢量。
6. **真正的自定义后处理走 `Compositor` + `CompositorEffect`**：`Compositor` 只有 `compositor_effects` 一个成员，效果要继承 `CompositorEffect` 并实现 `_render_callback`。
7. **5 个回调点**：`PRE_OPAQUE` / `POST_OPAQUE` / `POST_SKY` / `PRE_TRANSPARENT` / `POST_TRANSPARENT`，选点决定你能看到什么、能改什么。
8. **4.3 的限制**：`access_resolved_color` / `access_resolved_depth` 只在 `POST_TRANSPARENT` 有效，`needs_separate_specular` 只在 `POST_SKY` 有效，`needs_normal_roughness` / `needs_separate_specular` 仅 Forward+，**Compatibility 渲染器完全不支持** `CompositorEffect`。

### 关键术语

| 术语 | 解释 |
|------|------|
| Tone Mapping | 色调映射，HDR→LDR 转换 |
| Bloom | 泛光，高光区域模糊效果 |
| SSAO | 屏幕空间环境光遮蔽 |
| SSR | 屏幕空间反射 |
| DOF | 景深，焦点外模糊效果 |
| LUT | 色彩查找表 |
| Compositor | 合成器资源，承载一组后处理效果 |
| CompositorEffect | 合成器效果基类，在渲染线程的指定阶段回调 |
| Back Buffer | 后缓冲，3D 场景渲染的中间结果 |

---

## 🔗 延伸阅读

- **官方文档**: [环境与后处理（Environment and post-processing）](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)、[合成器（Compositor）](https://docs.godotengine.org/en/stable/tutorials/rendering/compositor.html)
- **类参考**: [WorldEnvironment](https://docs.godotengine.org/en/stable/classes/class_worldenvironment.html)、[Environment](https://docs.godotengine.org/en/stable/classes/class_environment.html)、[CompositorEffect](https://docs.godotengine.org/en/stable/classes/class_compositoreffect.html)、[Compositor](https://docs.godotengine.org/en/stable/classes/class_compositor.html)、[RenderData](https://docs.godotengine.org/en/stable/classes/class_renderdata.html)、[RenderSceneBuffersRD](https://docs.godotengine.org/en/stable/classes/class_renderscenebuffersrd.html)
- **源码位置**: `scene/resources/compositor.cpp`（`Compositor` 与 `CompositorEffect` 两个类）、`servers/rendering/renderer_rd/renderer_compositor_rd.cpp`、`servers/rendering/renderer_rd/renderer_scene_render_rd.cpp`、`servers/rendering/renderer_rd/effects/`
- **技术博客**: [Godot 4.0 Post-processing Deep Dive](https://godotengine.org/article/godot-4-0-post-processing-deep-dive/)

---

## 📋 下一章预告

**第 20 篇：粒子渲染**

- 粒子系统架构
- GPU 粒子 vs CPU 粒子
- 粒子材质详解
- 高级粒子特效
- 性能优化

---

**作者**: wangshucheng
**首发平台**: 微信公众号
**写作时间**: 2026 年 3 月
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 18 篇：2D 渲染](/articles/18-2d-rendering.md)
**下一篇**: [第 20 篇：粒子渲染](/articles/20-particle-rendering.md)

---

*最后更新：2026-03-20 11:00 AM*
