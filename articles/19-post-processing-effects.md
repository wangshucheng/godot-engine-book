# 第 9 篇：后处理效果

> **本卷定位**: 第二卷 渲染系统（12 篇）  
> **前置知识**: 第 18 章 2D 渲染  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

后处理（Post-processing）是在场景渲染完成后，对最终图像进行屏幕空间处理的技术。从基本的色调映射到复杂的景深、运动模糊，后处理效果极大提升了游戏的视觉质量和艺术风格。

Godot 4.x 提供了强大的后处理系统，基于 Vulkan 的计算着色器和屏幕空间技术，支持多种高质量后处理效果。

---

## 🎯 学习目标

- 理解后处理渲染架构
- 掌握 WorldEnvironment 配置
- 熟悉常用后处理效果
- 学会自定义后处理着色器
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

### 2.2 曝光控制

```gdscript
# 曝光设置
env.sdr_brightness = 1.0      # SDR 亮度
env.sdr_color = Color(1, 1, 1) # SDR 颜色

# 自动曝光
env.adjustment_auto_exposure_enabled = true
env.adjustment_auto_exposure_scale = 0.4
env.adjustment_auto_exposure_speed = 0.5
```

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
env.glow_intensity = 0.5          # 强度（0-1）
env.glow_bloom = 0.5              # 泛光量（0-1）
env.glow_blur = 1.0               # 模糊强度
env.glow_hdr_threshold = 1.0      # HDR 阈值
env.glow_hdr_scale = 2.0          # HDR 缩放

# 泛光级别（控制模糊程度）
env.glow_levels = 7  # 1-15，越高越模糊

# 各颜色通道强度
env.glow_color = Color(1, 1, 1)  # 泛光颜色
```

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
# 启用 SSAO
env.ssao_enabled = true
env.ssao_quality = Environment.SSAO_QUALITY_HIGH  # LOW, MEDIUM, HIGH
env.ssao_radius = 1.0           # 半径
env.ssao_intensity = 1.0        # 强度
env.ssao_bias = 0.02            # 偏差
env.ssao_light_affect = 0.5     # 光照影响
```

### 4.3 性能对比

| 质量 | 采样数 | 性能开销 | 推荐平台 |
|------|--------|----------|----------|
| Low | 8 | 低 | 移动设备 |
| Medium | 16 | 中 | 中端 PC |
| High | 32 | 高 | 高端 PC |

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
# 启用 SSR
env.ss_reflections_enabled = true
env.ss_reflections_quality = Environment.SSR_QUALITY_HIGH
env.ss_reflections_max_roughness = 0.5  # 最大粗糙度
env.ss_reflections_roughness_layers = 4 # 粗糙度层级
```

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
# 景深模式
env.dof_blur_enabled = true
env.dof_blur_quality = Environment.DOF_BLUR_QUALITY_HIGH
env.dof_blur_focal_distance = 10.0  # 焦点距离
env.dof_blur_focal_length = 50.0    # 焦距（mm）
env.dof_blur_aperture = 2.8         # 光圈（f-stop）
```

### 6.2 景深效果

| 参数 | 影响 | 推荐值 |
|------|------|--------|
| Focal Distance | 焦点平面距离 | 根据场景调整 |
| Focal Length | 镜头焦距 | 35-85mm |
| Aperture | 光圈大小 | f/1.4-f/5.6 |

### 6.3 动态景深

```gdscript
# 动态焦点（跟随玩家）
func _process(delta):
    var player_pos = player.global_transform.origin
    var camera_pos = camera.global_transform.origin
    var distance = player_pos.distance_to(camera_pos)
    
    # 更新焦点距离
    env.dof_blur_focal_distance = distance
```

---

## 7. 运动模糊（Motion Blur）

### 7.1 运动模糊类型

```gdscript
# 运动模糊设置
env.motion_blur_enabled = true
env.motion_blur_quality = Environment.MOTION_BLUR_QUALITY_HIGH
env.motion_blur_shutter_exposure = 1.0  # 快门曝光
```

### 7.2 运动模糊原理

```
运动模糊计算:
1. 存储上一帧深度和位置
2. 计算像素速度场
3. 沿速度方向采样
4. 累积模糊效果
```

### 7.3 性能考量

| 质量 | 采样数 | 性能开销 |
|------|--------|----------|
| Low | 4 | 低 |
| Medium | 8 | 中 |
| High | 16 | 高 |

---

## 8. 色彩校正（Color Correction）

### 8.1 基础调整

```gdscript
# 色彩调整
env.adjustment_brightness = 1.0
env.adjustment_contrast = 1.0
env.adjustment_saturation = 1.0

# 色相/饱和度曲线
var curve = Curve.new()
curve.add_point(Vector2(0, 0))
curve.add_point(Vector2(0.5, 0.5))
curve.add_point(Vector2(1, 1))
env.adjustment_color_correction_curve = curve
```

### 8.2 色彩查找表（LUT）

```gdscript
# 使用 LUT 进行色彩校正
var lut_texture = load("res://lut.png")
env.adjustment_color_correction_lut = lut_texture
env.adjustment_color_correction_lut_scale = 1.0
```

### 8.3 自定义色彩校正着色器

```glsl
// 后处理着色器
shader_type canvas_item;

uniform float brightness = 1.0;
uniform float contrast = 1.0;
uniform float saturation = 1.0;
uniform vec3 tint = vec3(1.0);

void fragment() {
    vec4 color = texture(TEXTURE, UV);
    
    // 亮度
    color.rgb *= brightness;
    
    // 对比度
    color.rgb = (color.rgb - 0.5) * contrast + 0.5;
    
    // 饱和度
    float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    color.rgb = mix(vec3(gray), color.rgb, saturation);
    
    // 色调
    color.rgb *= tint;
    
    // 色调映射（简单 ACES）
    color.rgb = color.rgb * (2.51 * color.rgb + 0.03) / 
                (color.rgb * (2.43 * color.rgb + 0.59) + 0.14);
    
    COLOR = color;
}
```

---

## 9. 抗锯齿（Anti-aliasing）

### 9.1 抗锯齿类型

```gdscript
# 项目设置中的抗锯齿
# 渲染 → 抗锯齿 → 质量

# FXAA（快速近似抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/fxaa_enabled", true)

# SMAA（子像素形态抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/smaa_enabled", true)

# TAA（时间抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/taa_enabled", true)

# MSAA（多重采样抗锯齿）
ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 2)  # 2x, 4x, 8x
```

### 9.2 抗锯齿对比

| 类型 | 质量 | 性能 | 适用场景 |
|------|------|------|----------|
| FXAA | 低 | 极高 | 移动设备、性能优先 |
| SMAA | 中 | 高 | 中端 PC |
| TAA | 高 | 中 | 高端 PC、动态场景 |
| MSAA | 高 | 低 | 静态场景、VR |

---

## 10. 艺术效果

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

---

## 11. 性能优化

### 11.1 后处理性能分析

```
后处理性能开销排序（从高到低）:
1. TAA（时间抗锯齿）
2. SSR（屏幕空间反射）
3. 景深（DOF）
4. 运动模糊
5. SSAO
6. 泛光
7. 色彩校正
8. FXAA/SMAA
```

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
        env.ss_reflections_enabled = false
        env.dof_blur_enabled = false
        env.motion_blur_enabled = false
        env.glow_enabled = true
        env.glow_levels = 3
    elif fps < 60:
        # 中帧率：中等质量
        env.ssao_enabled = true
        env.ssao_quality = Environment.SSAO_QUALITY_MEDIUM
        env.ss_reflections_enabled = false
        env.dof_blur_enabled = true
        env.dof_blur_quality = Environment.DOF_BLUR_QUALITY_MEDIUM
        env.motion_blur_enabled = false
        env.glow_enabled = true
        env.glow_levels = 5
    else:
        # 高帧率：高质量
        env.ssao_enabled = true
        env.ssao_quality = Environment.SSAO_QUALITY_HIGH
        env.ss_reflections_enabled = true
        env.dof_blur_enabled = true
        env.dof_blur_quality = Environment.DOF_BLUR_QUALITY_HIGH
        env.motion_blur_enabled = true
        env.glow_enabled = true
        env.glow_levels = 7
```

---

## 📝 本章总结

### 核心要点

1. **WorldEnvironment 是后处理核心**，集中管理所有效果
2. **色调映射决定整体观感**，ACES 是推荐选择
3. **泛光和 SSAO 提升真实感**，但性能开销较大
4. **景深和运动模糊增强沉浸感**，适合电影化体验
5. **性能优化需要平衡质量**，根据目标平台调整

### 关键术语

| 术语 | 解释 |
|------|------|
| Tone Mapping | 色调映射，HDR→LDR 转换 |
| Bloom | 泛光，高光区域模糊效果 |
| SSAO | 屏幕空间环境光遮蔽 |
| SSR | 屏幕空间反射 |
| DOF | 景深，焦点外模糊效果 |
| LUT | 色彩查找表 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Post-processing](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_lighting.html)
- **WorldEnvironment 参考**: [WorldEnvironment Class](https://docs.godotengine.org/en/stable/classes/class_worldenvironment.html)
- **环境参考**: [Environment Class](https://docs.godotengine.org/en/stable/classes/class_environment.html)
- **源码位置**: `servers/rendering/renderer_rd/effects/`
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

*写作时间：2026-03-20*  
*字数：约 6,500 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 11:00 AM*
