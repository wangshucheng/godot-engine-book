# 第 16 篇：材质系统

> **本章导读**：材质是"着色器 + 一堆参数"的封装，Godot 把这两样东西分别放在 `Shader`（代码）和 `Material`（参数）两个资源里，再由 `ShaderMaterial` 把它们缝起来。
> 本章把这条链从**文本**一路追到**GPU 管线**：着色器语言前端 → 变体展开 → SPIR-V → 管线缓存 → uniform set，同时把 `StandardMaterial3D` 的全部参数组、PBR 的真实计算流程、材质共享的语义讲透。
> 读完后你能：（1）照着类参考把一个 PBR 材质调对；（2）说清"换材质为什么会卡一下"；（3）自己写出一个能被引擎正确编译的 `ShaderMaterial`；（4）知道 uniform 有哪几层、该往哪一层放。
> **前置知识**：第 15 篇《光照系统》（光照模型的输入）、第 17 篇《GDShader 语言》（着色器语法本身）。
> **难度**：进阶。

> **摘要**：Godot 的材质系统基于 StandardMaterial3D 和 ShaderMaterial。本文将深入分析材质类型、PBR 流程、材质实例化。

---

## 一、材质体系总览

### 1.1 Material 家族

```
Material (Resource)                     ← 基类：next_pass、render_priority
├── BaseMaterial3D                      ← 所有 PBR 参数都在这里
│   └── StandardMaterial3D              ← 编辑器里最常用的那个
└── ShaderMaterial                      ← 用自己的 Shader
```

| 类 | 用途 |
|----|------|
| `Material` | 抽象基类，定义"材质"这个概念：传递顺序、渲染优先级 |
| `BaseMaterial3D` | 完整的 PBR 参数集（albedo / metallic / roughness / normal / …） |
| `StandardMaterial3D` | `BaseMaterial3D` 的具名子类，编辑器里新建的默认 3D 材质就是它 |
| `ShaderMaterial` | 持有 `Shader` 资源 + 一组 uniform 覆盖值 |

> 💡 `StandardMaterial3D` 相对 `BaseMaterial3D` **没有增加任何属性**——它存在的意义是"编辑器里新建出来的默认材质是这个类型"，方便按类型做特判与资源管理。

### 1.2 三个最常用的材质类

**StandardMaterial3D** 是 Godot 的标准材质：

| 属性 | 说明 |
|------|------|
| **Albedo** | 基础颜色/纹理 |
| **Metallic** | 金属度 |
| **Roughness** | 粗糙度 |
| **Normal** | 法线贴图 |
| **Emission** | 自发光 |
| **AO** | 环境光遮蔽 |

**ShaderMaterial** 允许自定义 Shader：

```gdscript
var material = ShaderMaterial.new()
material.shader = load("res://shaders/custom.gdshader")
material.set_shader_parameter("albedo", Color.RED)
material.set_shader_parameter("roughness", 0.5)
```

**两者的本质区别**不在"能不能自定义"，而在**谁负责算光照**：

| | `StandardMaterial3D` | `ShaderMaterial` |
|---|---|---|
| 光照计算 | 引擎写好的固定管线 | **你写**（`ALBEDO` / `ROUGHNESS` / … 只是"往引擎的输入槽里填值"） |
| 能不能接收引擎的光照 | ✅ | ✅（前提是你在 `fragment()` 里把内置输出赋好） |
| 灵活性 | 低（参数有限） | 高 |
| 性能 | 稳定 | 取决于你写多复杂 |
| 什么时候用 | 绝大多数场景 | 需要特殊效果（卡通、溶解、能量护盾） |

### 1.3 材质挂在哪里：三个位置

一个 `MeshInstance3D` 上的材质可能来自三个地方，**后者覆盖前者**：

| 位置 | 属性 | 作用范围 |
|------|------|----------|
| 网格自带的 surface 材质 | `Mesh.surface_get_material()` | 整个资源（所有使用这个网格的实例） |
| 实例级覆盖 | `MeshInstance3D.set_surface_override_material()` | 这一个实例的某一个 surface |
| 节点级覆盖 | `GeometryInstance3D.material_override` | 这一个实例的**所有** surface |
| 叠加层 | `GeometryInstance3D.material_overlay` | 叠加在原材质之上（常用于高亮、选中） |

`material_override` 是**整个实例**换材质，`material_overlay` 是**再叠一层**（引擎会把 overlay 材质作为 next pass 链上的一环）。两者都是 `GeometryInstance3D` 的属性。

```gdscript
var mi: MeshInstance3D = $MeshInstance3D
mi.material_override = my_material   # 整个实例换材质
mi.material_overlay = highlight_mat  # 叠加一层高亮
```

> 💡 **性能坑**：`material_override` 会让这个实例**不再复用网格自带的材质**，uniform set 缓存也会失效。如果只是为了改一个颜色，优先用 `ShaderMaterial.set_shader_parameter()` 或 `RenderingServer.instance_geometry_set_shader_parameter()`。

### 1.4 材质是 Resource：共享语义先搞清楚

`Material` 继承自 `Resource`，所以它的**共享语义**和所有其他资源一样：

- 同一个 `Material` 资源被多个节点引用 → 它们**共享同一份数据**，改一个全部跟着变。
- `Material.duplicate()` → 得到一份**独立副本**。
- `Material.next_pass` → 材质链。

第 5 章会详细讲这块。

---

## 二、StandardMaterial3D 详解

`BaseMaterial3D` 的属性可以分成**十一个参数组**。下面按组过一遍。

### 2.1 基础 PBR 参数组

| 属性 | 类型 | 说明 |
|------|------|------|
| `BaseMaterial3D.albedo_color` | Color | 基础色（没有贴图时用） |
| `BaseMaterial3D.albedo_texture` | Texture2D | 基础色贴图 |
| `BaseMaterial3D.metallic` | float | 金属度：0 = 介质，1 = 金属 |
| `BaseMaterial3D.metallic_specular` | float | 金属度工作流下，非金属部分的镜面反射率（0 ~ 1，默认 0.5） |
| `BaseMaterial3D.roughness` | float | 粗糙度：0 = 镜面，1 = 全漫反射 |
| `BaseMaterial3D.normal_enabled` | bool | 是否启用法线贴图 |
| `BaseMaterial3D.normal_texture` | Texture2D | 法线贴图 |
| `BaseMaterial3D.normal_scale` | float | 法线强度 |
| `BaseMaterial3D.ao_enabled` | bool | 是否启用环境光遮蔽贴图 |
| `BaseMaterial3D.ao_texture` | Texture2D | AO 贴图 |
| `BaseMaterial3D.ao_light_affect` | float | AO 对直接光的影响 |
| `BaseMaterial3D.ao_on_uv2` | bool | AO 采样 UV2（lightmap UV） |
| `BaseMaterial3D.ao_texture_channel` | `BaseMaterial3D.TextureChannel` | AO 贴图取哪个通道 |
| `BaseMaterial3D.emission_enabled` | bool | 是否启用自发光 |
| `BaseMaterial3D.emission` | Color | 自发光颜色 |
| `BaseMaterial3D.emission_energy_multiplier` | float | 自发光能量倍率 |
| `BaseMaterial3D.emission_texture` | Texture2D | 自发光贴图 |
| `BaseMaterial3D.emission_operator` | `EMISSION_OP_ADD` / `EMISSION_OP_MULTIPLY` | 自发光与 albedo 的合成方式 |

```gdscript
var mat := StandardMaterial3D.new()
mat.albedo_color = Color(0.8, 0.8, 0.85)
mat.metallic = 0.0
mat.metallic_specular = 0.5
mat.roughness = 0.4
mat.normal_enabled = true
mat.normal_scale = 1.0
mat.emission_enabled = true
mat.emission = Color(1.0, 0.3, 0.1)
mat.emission_energy_multiplier = 2.0
```

### 2.2 纹理槽位（TextureParam）

`BaseMaterial3D` 把所有纹理参数收在一个枚举里，通过 `get_texture()` / `set_texture()` 访问：

| 枚举名 | 含义 |
|--------|------|
| `BaseMaterial3D.TEXTURE_ALBEDO` | 基础色 |
| `BaseMaterial3D.TEXTURE_METALLIC` | 金属度 |
| `BaseMaterial3D.TEXTURE_ROUGHNESS` | 粗糙度 |
| `BaseMaterial3D.TEXTURE_EMISSION` | 自发光 |
| `BaseMaterial3D.TEXTURE_NORMAL` | 法线 |
| `BaseMaterial3D.TEXTURE_RIM` | 边缘光 |
| `BaseMaterial3D.TEXTURE_CLEARCOAT` | 清漆 |
| `BaseMaterial3D.TEXTURE_FLOWMAP` | 流动图（各向异性） |
| `BaseMaterial3D.TEXTURE_AMBIENT_OCCLUSION` | 环境光遮蔽 |
| `BaseMaterial3D.TEXTURE_HEIGHTMAP` | 高度图 |
| `BaseMaterial3D.TEXTURE_SUBSURFACE_SCATTERING` | 次表面散射 |
| `BaseMaterial3D.TEXTURE_SUBSURFACE_TRANSMITTANCE` | 次表面透射 |
| `BaseMaterial3D.TEXTURE_BACKLIGHT` | 背光 |
| `BaseMaterial3D.TEXTURE_REFRACTION` | 折射 |
| `BaseMaterial3D.TEXTURE_DETAIL_MASK` | 细节遮罩 |
| `BaseMaterial3D.TEXTURE_DETAIL_ALBEDO` | 细节基础色 |
| `BaseMaterial3D.TEXTURE_DETAIL_NORMAL` | 细节法线 |
| `BaseMaterial3D.TEXTURE_ORM` | ORM 打包（AO / Roughness / Metallic 三合一） |

```gdscript
# 用 TextureParam 设置纹理
mat.set_texture(BaseMaterial3D.TEXTURE_ALBEDO, load("res://albedo.png"))
mat.set_texture(BaseMaterial3D.TEXTURE_NORMAL, load("res://normal.png"))
mat.set_texture(BaseMaterial3D.TEXTURE_ORM, load("res://orm.png"))
```

> 💡 **ORM 材质**是 3D 资产的事实标准：把 **AO / Roughness / Metallic** 打进一张 RGB 贴图（`TEXTURE_ORM`），省掉两次采样与两张贴图的显存。`BaseMaterial3D.orm_texture` 就是一个直接可用的属性。

### 2.3 高级特性开关（Feature）

十三个"高级特性"默认关闭，打开会额外增加计算量：

| 枚举名 | 特性 |
|--------|------|
| `BaseMaterial3D.FEATURE_EMISSION` | 自发光 |
| `BaseMaterial3D.FEATURE_NORMAL_MAPPING` | 法线贴图 |
| `BaseMaterial3D.FEATURE_RIM` | 边缘光 |
| `BaseMaterial3D.FEATURE_CLEARCOAT` | 清漆（车漆那一层） |
| `BaseMaterial3D.FEATURE_ANISOTROPY` | 各向异性 |
| `BaseMaterial3D.FEATURE_AMBIENT_OCCLUSION` | 环境光遮蔽 |
| `BaseMaterial3D.FEATURE_HEIGHT_MAPPING` | 高度图 / 视差 |
| `BaseMaterial3D.FEATURE_SUBSURFACE_SCATTERING` | 次表面散射 |
| `BaseMaterial3D.FEATURE_SUBSURFACE_TRANSMITTANCE` | 次表面透射 |
| `BaseMaterial3D.FEATURE_BACKLIGHT` | 背光 |
| `BaseMaterial3D.FEATURE_REFRACTION` | 折射 |
| `BaseMaterial3D.FEATURE_DETAIL` | 细节层 |

```gdscript
mat.set_feature(BaseMaterial3D.FEATURE_CLEARCOAT, true)
mat.set_feature(BaseMaterial3D.FEATURE_RIM, true)
```

> 💡 `set_feature()` 与直接改属性是**两种等价的入口**：改 `mat.clearcoat_enabled = true` 内部也是 `set_feature(FEATURE_CLEARCOAT, true)`。但 `set_feature()` 让你可以把"要开哪些特性"存成一份数据，批量套用到不同材质上。

### 2.4 标志位（Flags）

Flags 是**布尔开关的集合**，用来改变材质的整体行为：

| 枚举名 | 作用 |
|--------|------|
| `BaseMaterial3D.FLAG_DISABLE_DEPTH_TEST` | 关闭深度测试（永远画在最上层） |
| `BaseMaterial3D.FLAG_ALBEDO_FROM_VERTEX_COLOR` | 基础色来自顶点色 |
| `BaseMaterial3D.FLAG_SRGB_VERTEX_COLOR` | 顶点色按 sRGB 解释 |
| `BaseMaterial3D.FLAG_USE_POINT_SIZE` | 使用点大小 |
| `BaseMaterial3D.FLAG_FIXED_SIZE` | 固定大小（billboard / 粒子） |
| `BaseMaterial3D.FLAG_BILLBOARD_KEEP_SCALE` | billboard 保留缩放 |
| `BaseMaterial3D.FLAG_UV1_USE_TRIPLANAR` | UV1 三平面映射 |
| `BaseMaterial3D.FLAG_UV1_USE_WORLD_TRIPLANAR` | UV1 世界空间三平面映射 |
| `BaseMaterial3D.FLAG_UV2_USE_TRIPLANAR` | UV2 三平面映射 |
| `BaseMaterial3D.FLAG_UV2_USE_WORLD_TRIPLANAR` | UV2 世界空间三平面映射 |
| `BaseMaterial3D.FLAG_AO_ON_UV2` | AO 采样 UV2 |
| `BaseMaterial3D.FLAG_EMISSION_ON_UV2` | 自发光采样 UV2 |
| `BaseMaterial3D.FLAG_ALBEDO_TEXTURE_FORCE_SRGB` | 基础色贴图强制 sRGB |
| `BaseMaterial3D.FLAG_DONT_RECEIVE_SHADOWS` | 不接收阴影 |
| `BaseMaterial3D.FLAG_DISABLE_AMBIENT_LIGHT` | 不接收环境光 |
| `BaseMaterial3D.FLAG_USE_SHADOW_TO_OPACITY` | 用阴影做透明度 |
| `BaseMaterial3D.FLAG_USE_TEXTURE_REPEAT` | 启用纹理重复 |
| `BaseMaterial3D.FLAG_INVERT_HEIGHTMAP` | 反转高度图 |
| `BaseMaterial3D.FLAG_SUBSURFACE_MODE_SKIN` | 次表面用皮肤模式 |
| `BaseMaterial3D.FLAG_PARTICLE_TRAILS_MODE` | 粒子拖尾模式 |
| `BaseMaterial3D.FLAG_ALBEDO_TEXTURE_MSDF` | 基础色用 MSDF |
| `BaseMaterial3D.FLAG_DISABLE_FOG` | 不受雾影响 |

```gdscript
mat.set_flag(BaseMaterial3D.FLAG_ALBEDO_FROM_VERTEX_COLOR, true)
mat.set_flag(BaseMaterial3D.FLAG_DONT_RECEIVE_SHADOWS, false)
```

### 2.5 透明与混合

| 属性 | 取值 | 说明 |
|------|------|------|
| `BaseMaterial3D.transparency` | `TRANSPARENCY_DISABLED` / `TRANSPARENCY_ALPHA` / `TRANSPARENCY_ALPHA_SCISSOR` / `TRANSPARENCY_ALPHA_HASH` / `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS` | 透明模式 |
| `BaseMaterial3D.blend_mode` | `BLEND_MODE_MIX` / `BLEND_MODE_ADD` / `BLEND_MODE_SUB` / `BLEND_MODE_MUL` / `BLEND_MODE_PREMULT_ALPHA` | 混合方式 |
| `BaseMaterial3D.alpha_scissor_threshold` | float | alpha 裁剪阈值 |
| `BaseMaterial3D.alpha_hash_scale` | float | alpha hash 的抖动强度（`TRANSPARENCY_ALPHA_HASH` 用） |
| `BaseMaterial3D.alpha_antialiasing_mode` | `ALPHA_ANTIALIASING_OFF` / `ALPHA_ANTIALIASING_ALPHA_TO_COVERAGE` / `ALPHA_ANTIALIASING_ALPHA_TO_COVERAGE_AND_TO_ONE` | 抗锯齿方式 |
| `BaseMaterial3D.cull_mode` | `CULL_BACK` / `CULL_FRONT` / `CULL_DISABLED` | 剔除模式 |
| `BaseMaterial3D.depth_draw_mode` | `DEPTH_DRAW_OPAQUE_ONLY` / `DEPTH_DRAW_ALWAYS` / `DEPTH_DRAW_DISABLED` | 深度写入时机 |
| `BaseMaterial3D.no_depth_test` | bool | 关闭深度测试 |
| `BaseMaterial3D.shadow_to_opacity` | bool | 用阴影做透明度 |

> `transparency` 与 `depth_draw_mode` 的分工、以及它们在深度预通道里的关系，见第 14 篇第 5.4 节。**这两个属性名字相近但管的是不同开关**，是最容易踩的一条。

### 2.6 折射、次表面与背光

| 属性 | 说明 |
|------|------|
| `BaseMaterial3D.refraction_enabled` | 开启折射 |
| `BaseMaterial3D.refraction_scale` | 折射强度 |
| `BaseMaterial3D.refraction_texture_channel` | 折射贴图取哪个通道 |
| `BaseMaterial3D.subsurf_scatter_enabled` | 次表面散射 |
| `BaseMaterial3D.subsurf_scatter_strength` | 散射强度 |
| `BaseMaterial3D.subsurf_scatter_texture` | 散射贴图（厚度） |
| `BaseMaterial3D.subsurf_scatter_skin_mode` | 皮肤模式 |
| `BaseMaterial3D.subsurf_scatter_transmittance_enabled` | 次表面透射 |
| `BaseMaterial3D.subsurf_scatter_transmittance_color` | 透射颜色 |
| `BaseMaterial3D.subsurf_scatter_transmittance_depth` | 透射深度 |
| `BaseMaterial3D.subsurf_scatter_transmittance_boost` | 透射增强 |
| `BaseMaterial3D.backlight_enabled` | 背光（薄物体的透光） |
| `BaseMaterial3D.backlight` | 背光颜色 |
| `BaseMaterial3D.backlight_texture` | 背光贴图 |

### 2.7 高度图与视差

| 属性 | 说明 |
|------|------|
| `BaseMaterial3D.heightmap_enabled` | 开启高度图 |
| `BaseMaterial3D.heightmap_texture` | 高度图贴图 |
| `BaseMaterial3D.heightmap_scale` | 视差强度 |
| `BaseMaterial3D.heightmap_min_layers` / `heightmap_max_layers` | 视差采样层数范围 |
| `BaseMaterial3D.heightmap_deep_parallax` | 深度视差（更准也更贵） |
| `BaseMaterial3D.heightmap_flip_tangent` / `heightmap_flip_binormal` | 切线方向翻转 |

### 2.8 顶点色、billboard 与各向异性

| 属性 | 说明 |
|------|------|
| `BaseMaterial3D.vertex_color_use_as_albedo` | 顶点色作为基础色 |
| `BaseMaterial3D.vertex_color_is_srgb` | 顶点色按 sRGB 解释 |
| `BaseMaterial3D.billboard_mode` | `BILLBOARD_DISABLED` / `BILLBOARD_ENABLED` / `BILLBOARD_FIXED_Y` / `BILLBOARD_PARTICLES` |
| `BaseMaterial3D.billboard_keep_scale` | billboard 保留缩放 |
| `BaseMaterial3D.anisotropy_enabled` | 各向异性 |
| `BaseMaterial3D.anisotropy` | 各向异性强度 |
| `BaseMaterial3D.anisotropy_flowmap` | 流动图（控制各向异性方向） |
| `BaseMaterial3D.rim_enabled` | 边缘光 |
| `BaseMaterial3D.rim` | 边缘光强度 |
| `BaseMaterial3D.rim_tint` | 边缘光染色（0 = 不染色） |
| `BaseMaterial3D.clearcoat_enabled` / `clearcoat` / `clearcoat_roughness` | 清漆层 |
| `BaseMaterial3D.grow` / `grow_amount` | 沿法线膨胀（描边常用） |
| `BaseMaterial3D.uv1_scale` / `uv1_offset` / `uv1_triplanar` / `uv1_world_triplanar` | UV1 控制 |
| `BaseMaterial3D.uv2_scale` / `uv2_offset` / `uv2_triplanar` / `uv2_world_triplanar` | UV2 控制 |
| `BaseMaterial3D.texture_filter` / `texture_repeat` | 采样过滤与重复 |
| `BaseMaterial3D.shading_mode` | `SHADING_MODE_UNSHADED` / `SHADING_MODE_PER_PIXEL` / `SHADING_MODE_PER_VERTEX` |
| `BaseMaterial3D.diffuse_mode` | `DIFFUSE_BURLEY` / `DIFFUSE_LAMBERT` / `DIFFUSE_LAMBERT_WRAP` / `DIFFUSE_TOON` |
| `BaseMaterial3D.specular_mode` | `SPECULAR_SCHLICK_GGX` / `SPECULAR_TOON` / `SPECULAR_DISABLED` |

---

## 三、ShaderMaterial 与自定义着色器

### 3.1 创建与赋值

```gdscript
var shader := Shader.new()
shader.code = """
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec4 albedo : source_color = vec4(1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float pulse : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    ALBEDO = albedo.rgb;
    ROUGHNESS = roughness;
    EMISSION = albedo.rgb * pulse;
}
"""

var sm := ShaderMaterial.new()
sm.shader = shader
sm.set_shader_parameter("albedo", Color(1.0, 0.4, 0.2))
sm.set_shader_parameter("pulse", 0.8)
```

注意 `Shader.code` 里的第一行 `shader_type spatial;` —— 它决定了这个 shader 属于哪一类，内置变量与内置输出完全不同（`ALBEDO` 是 spatial 的，`COLOR` 是 canvas_item 的）。

`Shader.get_mode()` 可以读回这个类型，枚举是 `Shader.MODE_SPATIAL` / `MODE_CANVAS_ITEM` / `MODE_PARTICLES` / `MODE_SKY` / `MODE_FOG`。

### 3.2 uniform 覆盖

| 方法 | 说明 |
|------|------|
| `ShaderMaterial.set_shader_parameter(name, value)` | 覆盖一个 uniform 的值 |
| `ShaderMaterial.get_shader_parameter(name)` | 读回当前值 |

**未覆盖的 uniform 用什么值？** 用着色器里写的默认值（`uniform float roughness = 0.5;`），或者 `Shader.set_default_texture_parameter()` 单独指定的默认纹理。

> 💡 **覆盖是"整个材质"级别的**。同一份 `Shader` 可以被多个 `ShaderMaterial` 引用，各自覆盖成不同的值——这正是"一份着色器、多种外观"的正确做法。

### 3.3 默认纹理参数

纹理 uniform 的默认值单独走一条通道：

| 方法 | 说明 |
|------|------|
| `Shader.set_default_texture_parameter(name, value)` | 给某个纹理 uniform 设默认纹理 |
| `Shader.get_default_texture_parameter(name)` | 读回默认纹理 |

如果材质侧**没有**覆盖这个纹理 uniform，就会用 `Shader` 上的默认纹理。

### 3.4 全局 uniform

全局 uniform 是**跨所有材质共享**的一份值：一处修改，所有引用它的材质同时变化。

**脚本侧**（`RenderingServer` 提供全套接口）：

| 方法 | 说明 |
|------|------|
| `RenderingServer.global_shader_parameter_add(name, type, default_value)` | 注册一个全局 uniform |
| `RenderingServer.global_shader_parameter_set(name, value)` | 设置值 |
| `RenderingServer.global_shader_parameter_get(name)` | 读值 |
| `RenderingServer.global_shader_parameter_remove(name)` | 注销 |
| `RenderingServer.global_shader_parameter_get_list()` | 列出全部 |
| `RenderingServer.global_shader_parameter_get_type(name)` | 查类型 |
| `RenderingServer.global_shader_parameter_set_override(name, value)` | 设置"覆盖值"（无视材质的局部设置） |

类型用 `RenderingServer` 的 `GLOBAL_VAR_TYPE_` 系列常量（`RenderingServer.GLOBAL_VAR_TYPE_COLOR`、`RenderingServer.GLOBAL_VAR_TYPE_FLOAT` 等）：

| 类型常量 | 用途 |
|----------|------|
| `RenderingServer.GLOBAL_VAR_TYPE_FLOAT` | 浮点 |
| `RenderingServer.GLOBAL_VAR_TYPE_VEC2` / `VEC3` / `VEC4` | 向量 |
| `RenderingServer.GLOBAL_VAR_TYPE_COLOR` | 颜色 |
| `RenderingServer.GLOBAL_VAR_TYPE_INT` / `UINT` | 整数 |
| `RenderingServer.GLOBAL_VAR_TYPE_BOOL` | 布尔 |
| `RenderingServer.GLOBAL_VAR_TYPE_MAT3` / `MAT4` | 矩阵 |
| `RenderingServer.GLOBAL_VAR_TYPE_SAMPLER2D` / `SAMPLER2DARRAY` / `SAMPLER3D` / `SAMPLERCUBE` | 采样器 |
| `RenderingServer.GLOBAL_VAR_TYPE_TRANSFORM` / `TRANSFORM_2D` | 变换 |
| `RenderingServer.GLOBAL_VAR_TYPE_RECT2` | 矩形 |

```gdscript
# 注册一个全局颜色，所有引用它的材质都会变
RenderingServer.global_shader_parameter_add(
    "weather_tint", RenderingServer.GLOBAL_VAR_TYPE_COLOR, Color(1, 1, 1))
RenderingServer.global_shader_parameter_set("weather_tint", Color(0.6, 0.7, 0.9))
```

**着色器侧**要在声明上加 `global` 关键字：

```glsl
shader_type spatial;

global uniform vec4 weather_tint;

void fragment() {
    ALBEDO = ALBEDO * weather_tint.rgb;
}
```

> 📌 全局 uniform 的典型用途：**时间**、**天气色调**、**玩家状态**（无敌时全屏偏色）、**调试开关**。这类值"每个材质都要用、但每帧只改一次"——放在全局 uniform 里，比给上百个材质各覆盖一次便宜得多。

### 3.5 按实例覆盖

除了材质级覆盖，Godot 4 还支持**按渲染实例**覆盖 uniform：

| 方法 | 说明 |
|------|------|
| `RenderingServer.instance_geometry_set_shader_parameter(instance, name, value)` | 给某个渲染实例设置 uniform |
| `RenderingServer.instance_geometry_get_shader_parameter(instance, name)` | 读回 |
| `RenderingServer.instance_geometry_get_shader_parameter_list(instance)` | 列出该实例可用的 uniform |

```gdscript
var mi: MeshInstance3D = $MeshInstance3D
RenderingServer.instance_geometry_set_shader_parameter(
    mi.get_instance(), "albedo", Color(1.0, 0.0, 0.0))
```

这条路径**不复制材质**，只是在渲染时对这个实例单独传一份参数——适合"同一批物体，每个高亮颜色不同"的场景。

### 3.6 ShaderMaterial vs StandardMaterial3D 选型

| 需求 | 选择 |
|------|------|
| 常规 PBR 表面 | `StandardMaterial3D` |
| 只是想改颜色 / 粗糙度 | `StandardMaterial3D` 直接改属性 |
| 想要"一份着色器、多种外观" | `ShaderMaterial` + `set_shader_parameter()` |
| 卡通渲染 / 描边 / 溶解 | `ShaderMaterial` |
| 需要引擎内建的高级特性（清漆、次表面、视差） | `StandardMaterial3D`（自己在 shader 里重写这些很痛苦） |
| 需要 SSAO / 阴影 / 反射探针正常参与 | 两者都可以，但 `ShaderMaterial` 里要**记得给内置输出赋值** |

> 💡 **`ShaderMaterial` 不会"自动"继承引擎的光照**。你在 `fragment()` 里只写 `ALBEDO = vec3(1.0);` 却期望它被场景光照亮——**不会**。`ShaderMaterial` 的 `fragment()` 里不写 `ALBEDO` / `ROUGHNESS` / `NORMAL` 等输出，这些槽位就是空的，物体只会被环境光按"默认无光照"的方式渲染。

---

## 四、PBR 计算流程

### 4.1 PBR 原理

PBR（基于物理的渲染）模拟真实材质：

```
光线入射
    ↓
微表面反射
├── 镜面分量：GGX / Schlick（BaseMaterial3D.SPECULAR_SCHLICK_GGX，默认）
└── 漫反射分量：Lambert / Burley（BaseMaterial3D.DIFFUSE_BURLEY，默认；
                设为 DIFFUSE_LAMBERT 可得到更"平"的漫反射）
    ↓
透射与吸收（仅 Transparent 材质走这条分支）
```

> 金属（`metallic = 1`）没有漫反射分量，albedo 直接作为镜面反射的乘数；非金属则用 albedo 作为漫反射色，镜面反射叠加在其上。

### 4.2 PBR 参数

| 参数 | 范围 | 说明 |
|------|------|------|
| **Albedo** | 0-1 | 基础颜色 |
| **Metallic** | 0-1 | 0=非金属，1=金属 |
| **Roughness** | 0-1 | 0=光滑，1=粗糙 |
| **Normal** | - | 法线方向 |

### 4.3 漫反射：四种模式

`BaseMaterial3D.diffuse_mode` 决定漫反射项怎么算：

| 取值 | 模型 | 特点 |
|------|------|------|
| `DIFFUSE_BURLEY`（默认） | Burley / Remez | 有能量归一化，亮处不"过曝" |
| `DIFFUSE_LAMBERT` | Lambert | 最平、最便宜、纯 `N·L` |
| `DIFFUSE_LAMBERT_WRAP` | Wrapped Lambert | 允许光"绕到"背面一点，柔化明暗交界 |
| `DIFFUSE_TOON` | Toon | 卡通分段 |

**`DIFFUSE_LAMBERT_WRAP` 是做"半兰伯特"最省事的开关**——很多手写 shader 里手写的 `wrap = (N·L + w) / (1 + w)`，在这里只需要换一个枚举值。

### 4.4 镜面：三种模式

`BaseMaterial3D.specular_mode`：

| 取值 | 模型 | 特点 |
|------|------|------|
| `SPECULAR_SCHLICK_GGX`（默认） | GGX + Schlick 菲涅尔 | 物理上最接近真实，能量守恒 |
| `SPECULAR_TOON` | Toon 高光 | 卡通 |
| `SPECULAR_DISABLED` | 无 | 只剩漫反射（常用于卡通或纯手绘风格） |

### 4.5 金属度工作流与能量守恒

`metallic` 是个 0 ~ 1 的混合值，它在着色器里同时控制两件事：

| metallic | 漫反射色 | 镜面色 | 说明 |
|----------|----------|--------|------|
| 0 | albedo | `metallic_specular` 决定的 F0 | 典型介质（塑料、木头、皮肤） |
| 1 | **0**（无漫反射） | albedo | 金属（铝、金、铜） |
| 0.5 | albedo 的一半 | 混合 | 脏金属 / 氧化表面 |

**`metallic_specular` 是"非金属的 F0"**：

| 值 | 对应现实 |
|----|----------|
| 0.0 | 纯介电质、无反射（水、玻璃的界面） |
| 0.5（默认） | 典型介电质 F0 ≈ 0.04 ~ 0.06 |
| 1.0 | 极端高反射的涂层 |

> 💡 **"我的金属看起来像塑料"** —— 九成是 `metallic_specular` 太低 + `roughness` 太高。金属的 F0 就是 albedo 本身，`metallic_specular` 对金属**不起作用**。

### 4.6 高级层的叠加顺序

一个开了全套高级特性的 `BaseMaterial3D`，着色器里的计算顺序大致是：

```
1. 基础色        albedo_color × albedo_texture
2. 法线          normal_texture → TBN 空间 → 视空间
3. 高度 / 视差   heightmap（沿法线偏移采样坐标）
4. 细节层        detail_albedo / detail_normal 叠加
5. 漫反射 + 镜面  ← 这里进入光照方程
6. 边缘光        rim（视角相关的加色）
7. 清漆          clearcoat（独立的 GGX 层，叠在基础层之上）
8. 各向异性      anisotropy（拉伸镜面高光）
9. 次表面散射    subsurf_scatter（透光扩散）
10. 背光        backlight（背面透光）
11. 自发光        emission
12. 折射 / 透射   refraction（Transparent 分支）
13. Alpha       按 transparency 模式决定 discard / 混合
```

**每一层都是可选的**，通过 `set_feature()` 开关。关掉不用的层，是最直接的材质优化手段。

### 4.7 Alpha 与透明分支

`BaseMaterial3D.transparency` 决定透明是怎么实现的：

| 模式 | 机制 | 代价 |
|------|------|------|
| `TRANSPARENCY_DISABLED` | 全不透明 | 最便宜 |
| `TRANSPARENCY_ALPHA` | alpha 混合 | 不写深度，排序有瑕疵 |
| `TRANSPARENCY_ALPHA_SCISSOR` | alpha 低于阈值就 `discard` | 保留深度，能投影 |
| `TRANSPARENCY_ALPHA_HASH` | alpha hash 抖动（配合 TAA） | 保留深度，画面有噪点 |
| `TRANSPARENCY_ALPHA_DEPTH_PRE_PASS` | 深度预通道里先写深度 | 需要额外的预通道 |

> 这一组与深度预通道、渲染排序的关系，见第 14 篇第 5.1 与 5.4 节。

---

## 五、材质共享与实例化

### 5.1 实例化优势

| 优势 | 说明 |
|------|------|
| **性能** | 共享底层数据 |
| **内存** | 减少内存占用 |
| **灵活性** | 独立修改参数 |

### 5.2 实例化示例

```gdscript
# 创建基础材质
var base_material = StandardMaterial3D.new()
base_material.albedo_color = Color.RED

# 创建实例
var instance1 = base_material.duplicate()
var instance2 = base_material.duplicate()

# 独立修改
instance1.albedo_color = Color.BLUE
instance2.roughness = 0.8
```

> ⚠️ **但这是"最贵的灵活"**：`duplicate()` 出来的是**独立的 `Material` 资源**，渲染器要为每一个单独建 uniform set、单独绑定。第 4 章第 4.5 节讲过：Draw Call 的收益主要来自"共享材质"，盲目 `duplicate()` 会把这份收益全部吃掉。

### 5.3 三种"独立化"的手段对比

| 手段 | 数据独立？ | 渲染侧代价 | 什么时候用 |
|------|-----------|------------|-----------|
| `material.duplicate()` | 完全独立 | 高（新的 uniform set） | 真的要换整套外观 |
| `resource_local_to_scene = true` | 每个场景实例一份 | 中 | 同一份 prefab 在不同场景里要不同参数 |
| `ShaderMaterial.set_shader_parameter()` | uniform 值独立 | 低（同一材质资源？） | 只是改几个 uniform 的值 |

`Resource.resource_local_to_scene` 打开后，资源在**每个进入场景的实例**上都会有一份副本：

```gdscript
var local := StandardMaterial3D.new()
local.resource_local_to_scene = true
local.albedo_color = Color.RED
```

`Resource.setup_local_to_scene()` 是它的编程入口——在 `Resource` 被"本地化"时调用，用来给每个副本做一次初始化。

> 💡 **`resource_local_to_scene` 的常见误解**：它不是"复制一份数据"，而是"标记这个资源需要按场景实例复制"。真正决定是否复制的是 `setup_local_to_scene()` 的默认实现（`Resource._setup_local_to_scene()` 会 `duplicate()` 一份）。所以对 `Material` 来说，打开这个开关基本等价于"每个实例一份副本"。

### 5.4 next_pass：材质链

`Material.next_pass` 让一个材质在渲染完自己之后**接着渲染另一个材质**：

```gdscript
var base := StandardMaterial3D.new()
base.albedo_color = Color.RED

var detail := StandardMaterial3D.new()
detail.albedo_texture = load("res://detail.png")
detail.blend_mode = BaseMaterial3D.BLEND_MODE_MUL

detail.next_pass = base
```

**典型用途**：

| 用途 | 做法 |
|------|------|
| 细节层叠加 | 细节材质 `BLEND_MODE_MUL` 叠在主材质上 |
| 描边 | 外扩材质（`grow`）+ 反向剔除作为 next pass |
| 自发光脉冲 | 一个 `unshaded` 的发光材质作为 next pass |
| 光照贴图叠加 | 把 `lightmap_mode` 的材质挂成 next pass |

`Material` 还有两个用于判断"能不能这么干"的内部方法：`Material._can_do_next_pass()` 与 `Material._can_use_render_priority()`。

> 💡 **next_pass 会打破材质共享的收益**——它把一个绘制拆成了两次，Draw Call 翻倍。只有在效果确实需要时才用。

### 5.5 渲染侧的收益：uniform set 复用

| 共享的东西 | 共享后的效果 | 不共享的后果 |
|------------|--------------|--------------|
| **Uniform set** | 渲染器缓存并复用已绑定的 uniform buffer 绑定 | 每个表面都要重新绑定一组 buffer |
| **着色器管线** | 同一材质变体共享同一个 pipeline | 换材质 = 换 pipeline |
| **纹理绑定** | 纹理只在第一次使用时绑定 | 重复绑定 |

**结论**：

- 外观完全相同的物体 → **共享同一个材质资源**。
- 外观有细微差别 → 优先考虑 `MultiMesh` 的实例颜色（`MultiMesh.use_colors` + `set_instance_color()`）或 `RenderingServer.instance_geometry_set_shader_parameter()`。
- 实在要独立的完整材质 → `duplicate()`，但要意识到代价。

### 5.6 常见反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 循环里 `material.duplicate()` | 每份一个 uniform set，Draw Call 与状态切换暴涨 | `MultiMesh` + 实例颜色 |
| 每个物体一个 `StandardMaterial3D` | 同上 | 共享一份 |
| 用 `material_override` 改颜色 | 整个实例换材质，破坏共享 | `ShaderMaterial.set_shader_parameter()` |
| 给不需要的材质开全套高级特性 | 白白增加着色计算 | `set_feature()` 关掉用不上的 |
| 把 `next_pass` 当万能叠加 | Draw Call 翻倍 | 先试 `BLEND_MODE_MUL` 单材质方案 |

---

## 六、Shader 编译链路

这是本章最硬核的一节。一份 `.gdshader` 从**文本**到**GPU 可执行的管线**，中间要经过六个阶段。

### 6.1 总览

```
① Shader 资源（文本）                    scene/resources/material.h → Shader
      │  code 字符串
      ▼
② ShaderLanguage 前端解析                servers/rendering/shader_language.cpp
      │  语法树 + uniform 列表 + render_mode 列表
      ▼
③ 变体展开（Variant）                   servers/rendering/renderer_rd/forward_clustered/
      │  render_mode 的每种组合 = 一个变体    scene_shader_forward_clustered.cpp
      ▼
④ 内置代码拼接 → 生成完整 GLSL            servers/rendering/renderer_rd/shaders/
      │                                          forward_clustered/scene_forward_clustered.glsl
      ▼
⑤ 编译成 SPIR-V                          RenderingDevice.shader_compile_spirv_from_source()
      │  servers/rendering/renderer_rd/shader_rd.cpp（RD 侧封装）
      ▼
⑥ 管线缓存 + 材质存储                     servers/rendering/renderer_rd/pipeline_cache_rd.cpp
      │  PipelineCache（按 shader 变体 + 状态缓存 pipeline）  storage_rd/material_storage.cpp
      ▼
   GPU 可执行的渲染管线
```

### 6.2 第一步：Shader 资源

`Shader` 只是一个 `Resource`，它存的是**文本**：

| 成员 | 说明 |
|------|------|
| `Shader.code` | 着色器源码 |
| `Shader.get_mode()` | 读出 `shader_type`（`MODE_SPATIAL` 等） |
| `Shader.get_shader_uniform_list()` | 列出这个 shader 里的所有 uniform |
| `Shader.get_default_texture_parameter(name)` / `set_default_texture_parameter(name, value)` | 纹理 uniform 的默认值 |

**编译是懒的**：改 `Shader.code` 不会立刻触发重编译，而是打上"脏标记"，等真正要渲染的时候才重编。这解释了一个常见现象：**改了 shader 代码，画面没立刻变，直到该材质重新进入可见列表**。

### 6.3 第二步：ShaderLanguage 前端

`servers/rendering/shader_language.cpp` 是整个着色器语言的前端（4.3 里约 365 KB，是 `servers/rendering/` 下最大的单文件之一）。它负责：

| 阶段 | 做什么 |
|------|--------|
| **词法分析** | 把文本切成 token，识别注释、字符串、标识符 |
| **语法分析** | 递归下降构建语法树；检查类型是否匹配 |
| **语义检查** | 检查 `render_mode` 是否合法、uniform 是否与内置函数重名、类型转换是否合法 |
| **中间表示** | 产出"节点树"，并抽出 uniform 列表、varying 列表、render_mode 列表 |

**这一步产出的 uniform 列表，后面被两个地方用到**：

1. `Shader.get_shader_uniform_list()` 直接返回它。
2. 渲染器用它来决定 uniform buffer 里要留哪些槽位。

> 📌 **"uniform 名字和内置函数重名"是一个真实的编译期错误**。`shader_language.cpp` 里注册了 `texture`（12 个重载）等全局内建函数；你在全局作用域写 `uniform sampler2D texture;` 会把它遮蔽掉，随后 `texture(uv)` 的调用就会编译失败。详见第 17 篇。

### 6.4 第三步：变体（Variant）

**一个 `Shader` 资源，在运行时对应多个"变体"。** 变体由 `render_mode` 的取值组合决定。

```glsl
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;
```

这一行里的**每一个 `render_mode` 都是一个布尔开关**。引擎在编译期会为"常用组合"生成若干套变体，运行时按实际取值挑一套。

**判断"变体"的粒度**：

| 级别 | 举例 | 影响 |
|------|------|------|
| **编译期常量** | `shading_mode`、`cull_mode`、`diffuse_mode`、`specular_mode`、`blend_mode` | 不同取值 → **不同 SPIR-V** |
| **运行期开关** | `depth_draw_opaque`、`unshaded`、`world_vertex_coords` | 不同取值 → **同一份 SPIR-V，走不同分支** |

> 💡 这就是为什么 `unshaded` 不会产生新管线，而 `cull_back` / `cull_front` 会：**前者是着色器里的一个 uniform 分支，后者是管线状态**。

### 6.5 第四步：内置代码拼接

用户写的 `.gdshader` 只是"半份"着色器。真正跑在 GPU 上的是**引擎内置 GLSL + 你的代码**拼出来的一份：

```glsl
// Godot 4.7.2 源码 - servers/rendering/renderer_rd/shaders/forward_clustered/scene_forward_clustered.glsl
// 这一大段是引擎内建的 spatial 着色器：包含 SceneData / LightsData 的读取、
// 阴影采样、簇化光照循环、雾、体积雾等。
// 你的 .gdshader 的 vertex() / fragment() 被"嵌入"到其中。
```

拼装的逻辑在 `servers/rendering/renderer_rd/forward_clustered/scene_shader_forward_clustered.cpp` 里（`SceneShaderForwardClustered` 类）。它同时负责：

- 把 `render_mode` 映射成 `#define`（前面第 14 篇第 5.1 节引用的 `actions.render_mode_defines` 就是这里）。
- 把内置函数与内置变量注入用户代码的作用域。
- 记录"这个变体用了哪些 uniform"。

### 6.6 第五步：SPIR-V

生成的完整 GLSL 要编译成 SPIR-V。这一步在 `RenderingDevice` 层：

| 方法 | 说明 |
|------|------|
| `RenderingDevice.shader_compile_spirv_from_source(source, stage)` | 从 GLSL 源码编译出 SPIR-V |
| `RenderingDevice.shader_create_from_spirv(spirv_data)` | 用 SPIR-V 创建一个 `RDShaderFile` |
| `RenderingDevice.shader_create_from_bytecode(bytecode)` | 从字节码（离线编译产物）创建 |

RD 侧的封装在 `servers/rendering/renderer_rd/shader_rd.cpp`。

> 💡 **SPIR-V 的意义在于跨厂商**：Godot 把 GLSL 编译成 SPIR-V（而不是直接生成某家 GPU 的机器码），这样同一份着色器可以喂给 Vulkan / D3D12 / Metal 的驱动，由驱动再做"最后一公里"的优化。`shader_compile_binary_from_spirv()` 则是把 SPIR-V 进一步编译成驱动字节码的入口。

### 6.7 第六步：管线缓存

有了 SPIR-V，还要把它和**管线状态**（混合、深度、剔除、拓扑……）组合成一条完整的渲染管线。这条管线由**管线缓存**管理：

| 位置 | 说明 |
|------|------|
| `servers/rendering/renderer_rd/pipeline_cache_rd.cpp` | 管线缓存实现 |
| `PipelineCache` | 按"着色器变体 + 状态组合"缓存管线 |
| `RenderingDevice.render_pipeline_create()` | 创建一条管线 |
| `RenderingDevice.draw_list_bind_render_pipeline()` | 绑定管线 |

**管线缓存的键**大致是：

```
(着色器变体, 混合模式, 深度写/测试, 剔除模式, 拓扑, 多重采样数, 颜色附件数, ...)
```

同一个键的请求会**命中缓存**，直接复用已有的管线；没命中才会真正调用驱动创建。

**这就是"换材质会卡一下"的根因**：

- 你在运行时改了一个**编译期常量**级别的 `render_mode`（比如 `cull_mode`）→ 产生新变体 → 需要新 SPIR-V → 需要新管线 → **驱动侧可能要重新编译**（几十毫秒到几百毫秒的卡顿）。
- 你只是改了一个 **uniform 值**（颜色、粗糙度）→ 不产生新变体 → 只更新 uniform buffer → **不卡**。

> 📌 **运行时改 `render_mode` 是危险操作**。`render_mode` 是在着色器编译期决定的，运行时改它等于要求引擎"热重编译一份着色器"。编辑器里改是安全的（会触发重载），但打包后的游戏里改就是运行时卡顿。

### 6.8 第七步：材质存储与 uniform set

管线准备好之后，材质数据要进到 GPU。这一层由 **material storage** 负责：

| 位置 | 说明 |
|------|------|
| `servers/rendering/renderer_rd/storage_rd/material_storage.cpp` | 材质数据、uniform set 的组织 |
| `uniform_set_cache_storage.cpp` | uniform set 的缓存 |
| `RenderingDevice.uniform_buffer_create()` | 创建 uniform buffer |
| `RenderingDevice.uniform_set_create()` | 创建 uniform set（buffer + 采样器等的组合） |

**一个 uniform set 里装的是**：这个材质用到的所有 uniform buffer 段 + 纹理采样器。

材质级 uniform（你在 `.gdshader` 里写的 `uniform float x;`）的值被写进**该材质专属的 uniform buffer**。改一个 uniform 值时，引擎只更新这个 buffer 的一段数据，**不重建 uniform set、不重建管线**——这就是"改 uniform 不卡"的机制。

### 6.9 变体清单

一份 `.gdshader` 到底会编译出几份？可以从三个来源推：

| 来源 | 例子 | 影响 |
|------|------|------|
| `render_mode` 的组合 | `unshaded` on/off、`cull_back`/`cull_front`/`cull_disabled` | 每个组合一份变体 |
| 着色器类型 | `spatial` / `canvas_item` / `particles` / `sky` / `fog` | 每个类型独立 |
| 渲染后端 | Forward+ / Mobile / Compatibility | 不同后端的内建 GLSL 不同，变体不共用 |

**实践建议**：

1. **不要在运行时改 `render_mode`**（见 6.7）。
2. **把"偶尔不同"的参数做成 uniform，不要做成 `render_mode`**。比如"要不要有雾"用 uniform 做，不要用 `render_mode fog_disabled`。
3. **同一份着色器尽量只在一个 `Shader` 资源里写**，让引擎复用变体。
4. **用 `Material.inspect_native_shader_code()` 看实际生成结果**——它把引擎最终拼出来的原生 GLSL 打出来，是排查"我的 shader 为什么这样表现"的第一工具。

---

## 七、UBO 与 uniform 的三层结构

### 7.1 什么是 UBO

**UBO（Uniform Buffer Object，统一缓冲区对象）** 是把一堆 uniform 打包进**一个** GPU buffer 的做法。

| | 每个 uniform 一个 buffer（UBO 之前） | 打包进一个 UBO |
|---|---|---|
| 绑定次数 | N 次 | 1 次 |
| 状态切换 | N 次 | 1 次 |
| 布局 | 分散 | 连续、可按 std140 规则布局 |
| 典型用法 | 小量、独立 | 大量、结构化（矩阵数组、场景数据） |

Godot 4.3 的渲染器**重度依赖 UBO**：场景数据（相机矩阵、光照参数、雾参数）、光源数据（每个簇的光源列表）都是打包好的 uniform buffer，每个 pass 只绑定一次就拿到几十个参数。

### 7.2 引擎侧的三层 uniform

| 层 | 谁写的 | 怎么改 | 共享范围 |
|----|--------|--------|----------|
| **引擎内建 uniform buffer** | 引擎（SceneData / LightsData / 材质数据） | 引擎自动 | 全局，所有 pass |
| **材质级 uniform** | 你在 `.gdshader` 里写的 `uniform float x;` | `ShaderMaterial.set_shader_parameter()` | 该材质资源 |
| **全局 uniform** | 你在 `.gdshader` 里写的 `global uniform ...` | `RenderingServer.global_shader_parameter_set()` | **所有材质** |

第 1 层你完全碰不到（也不需要碰）；第 2、3 层是你的战场。

### 7.3 材质级 uniform 是怎么被打包进去的

一个 `ShaderMaterial` 的 uniform 数据流：

```
.gdshader 里的 uniform 声明
      │  ShaderLanguage 前端解析
      ▼
uniform 列表（名字 / 类型 / hint）
      │  SceneShaderForwardClustered 记录
      ▼
该变体专属的 uniform buffer 布局
      │  material_storage 写入
      ▼
GPU 上的 uniform buffer + uniform set
```

**关键推论**：

1. **同一材质的多个实例共享同一个 uniform buffer**。所以给 100 个物体用同一个 `ShaderMaterial`，只存一份 uniform 数据。
2. **改 uniform 值 = 更新 buffer 的一段**。不重建 uniform set，不重建管线，所以不卡。
3. **改 `render_mode` = 新变体 = 新 buffer 布局 = 新 uniform set = 新管线**。这才是卡顿的来源。

### 7.4 global uniform：跨材质共享的正确姿势

前面 3.4 节已经给了完整 API。这里从 UBO 的角度补一句：

**全局 uniform 的本质，是让引擎把这一份数据放进一个"所有材质共用"的 uniform buffer 段**。所以：

- 注册一次，所有引用它的材质都能读到。
- 修改一次，所有材质立刻生效（**不需要遍历材质**）。
- 代价是每次修改会触发所有引用它的材质**重传这一段数据**。

```gdscript
# 注册（通常在初始化时做一次）
RenderingServer.global_shader_parameter_add(
    "day_time", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 12.0)

# 修改（每帧或按需）
RenderingServer.global_shader_parameter_set("day_time", 18.5)
```

### 7.5 UBO 写法要点

虽然 4.3 的着色器语言不让你手写 `set` / `binding` 编号（这些由引擎分配），但"把 uniform 组织好"这件事仍然有明确的工程实践：

| 原则 | 理由 |
|------|------|
| **材质级 uniform 只放"这个材质自己的参数"** | 材质级 uniform 会被打包进该材质的 buffer；放太多会让每个材质的 buffer 变大 |
| **跨材质共享的常量放 global uniform** | 一处更新，所有材质生效；避免 N 个材质各存一份 |
| **"每帧都变"的大数组不要放 uniform** | 那是顶点/实例数据，应该走顶点属性或 storage buffer |
| **能用 const 就不用 uniform** | `const` 是编译期常量，完全不占运行时带宽 |
| **纹理用 sampler2D 而不是 texture 数组** | Godot 的纹理 uniform 有专门的 hint 机制（`source_color` / `filter_*` / `repeat_*`），走的是采样器绑定而不是数据拷贝 |

> 📌 **"材质之间传数据"的正解**：不是"把数据复制到每个材质"，而是"把数据做成 global uniform"或"用同一个材质 + 实例颜色"。这两条路都不会让 uniform buffer 膨胀。

---

## 八、Shader 变体与 uniform 覆盖

### 8.1 变体从哪来

| 来源 | 例子 | 是否产生新 SPIR-V |
|------|------|----------------|
| `render_mode` 的编译期常量 | `cull_back` ↔ `cull_front` | ✅ |
| `render_mode` 的运行期开关 | `depth_draw_opaque` ↔ `depth_draw_always` | ❌（同一份，分支不同） |
| 着色器类型 | `spatial` ↔ `canvas_item` | ✅ |
| 渲染后端 | Forward+ ↔ Mobile | ✅ |
| uniform 值 | 颜色变了 | ❌（只更新 buffer） |

### 8.2 覆盖的优先级

从"离像素最近"到"离像素最远"：

| 层级 | 谁在设 | 怎么设 |
|------|--------|--------|
| **按实例覆盖** | `RenderingServer.instance_geometry_set_shader_parameter()` | 渲染时对这个实例单独传参 |
| **材质级覆盖** | `ShaderMaterial.set_shader_parameter()` | 该材质资源的所有使用处 |
| **全局 uniform** | `RenderingServer.global_shader_parameter_set()` | 所有引用它的材质 |
| **着色器默认值** | `.gdshader` 里写的 `= 0.5` | 该 shader 的兜底值 |
| **默认纹理参数** | `Shader.set_default_texture_parameter()` | 纹理 uniform 的兜底值 |

`RenderingServer.global_shader_parameter_set_override()` 是"无视材质级设置、强制全局值"的口子。

### 8.3 调试三件套

```gdscript
# 1) 列出这个 shader 的 uniform
var shader := Shader.new()
shader.code = "shader_type spatial;\nuniform vec4 tint : source_color;\nuniform float k;\n"
for u in shader.get_shader_uniform_list():
    print(u.get("name"), "  type=", u.get("type"), "  hint=", u.get("hint"))

# 2) 看引擎最终生成的原生 GLSL
var mat := StandardMaterial3D.new()
print(mat.inspect_native_shader_code())

# 3) 看某个实例当前有哪些 shader 参数
var mi: MeshInstance3D = $MeshInstance3D
print(RenderingServer.instance_geometry_get_shader_parameter_list(mi.get_instance()))
```

| 工具 | 回答什么问题 |
|------|--------------|
| `Shader.get_shader_uniform_list()` | "我到底声明了哪些 uniform？名字对不对？" |
| `Material.inspect_native_shader_code()` | "引擎把我的 shader 拼成了什么？为什么表现是这样？" |
| `RenderingServer.instance_geometry_get_shader_parameter_list()` | "这个实例上实际有哪些 uniform 可覆盖？" |
| `RenderingServer.get_shader_parameter_list()` | "这个渲染服务器上注册了哪些材质参数？" |

> 💡 **`inspect_native_shader_code()` 是排查"为什么我的 shader 效果不对"的第一工具**。它输出的就是引擎最终交给 `glslang` 编译的那份 GLSL，能看到引擎注入了哪些 `#define`、uniform 布局长什么样、你的代码被嵌在哪个位置。

---

## 九、材质优化

### 9.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **共享材质** | 减少材质数量 |
| **距离淡出** | `distance_fade_mode` + `distance_fade_min_distance` / `distance_fade_max_distance`，远处把物体淡出 |
| **近处淡出** | `proximity_fade_enabled` + `proximity_fade_distance`，物体靠近相机时淡出 |
| **几何 LOD** | `GeometryInstance3D.visibility_range_begin/end` + `lod_bias`，远处整体不可见 / 换低模 |
| **纹理压缩** | 减少显存占用 |
| **实例化** | 相同网格用 `MultiMesh` 合并成一次实例化绘制 |

> Godot 4 **没有**"材质 LOD"这种按距离切换材质的功能。等价手段是上面这三条：材质级的**距离淡出 / 近处淡出**（在着色器里按距离调 alpha 或 dither），以及节点级的**可见性范围**（直接把远处的物体剔出渲染列表）。

### 9.2 材质数量是硬成本

材质数量的开销来自三处：

| 开销项 | 说明 |
|--------|------|
| **Draw Call** | 每个可见表面至少一次绘制 |
| **Uniform set** | 每个材质一份 uniform set，切换材质就要重新绑定 |
| **管线** | 每个"材质变体 + 状态组合"一条管线，缓存满了就要新建 |

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际数值取决于场景规模、材质数量与目标硬件，请在目标平台实测。

| 材质数量 | DrawCall | 帧率 |
|---------|---------|------|
| 100 | 100 | 60 FPS |
| 50 | 50 | 90 FPS |
| 10 | 10 | 120 FPS |

> ⚠️ 下表为示意数据（未附测试环境）。实际开销取决于场景规模与目标硬件，请在目标平台实测。

### 9.3 纹理压缩

| 格式 | 用途 |
|------|------|
| **VRAM Compressed** | 法线贴图、AO 贴图等"读多写少"的 |
| **Lossless / Uncompressed** | 需要精确读回的（遮罩、查找表） |
| **BPTC / S3TC / ETC2** | 导入时按平台选，显存直接省 4 ~ 8 倍 |

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际显存占用取决于分辨率、格式与 mipmap 设置，请在目标平台实测。

| 贴图 | 2048² RGBA8 未压缩 | 同尺寸 VRAM 压缩后 |
|------|--------------------|-------------------|
| 单张 | ~16 MB | ~4 MB（4:1） |
| 10 张 | ~160 MB | ~40 MB |

### 9.4 距离淡出与近处淡出

| 属性 | 说明 |
|------|------|
| `BaseMaterial3D.distance_fade_mode` | 距离淡出模式；`DISTANCE_FADE_DISABLED` 表示关闭（4.3 的 `BaseMaterial3D` **没有** `distance_fade_enabled` 这个开关，开关就是模式本身） |
| `BaseMaterial3D.distance_fade_mode` 的四种取值 | `DISTANCE_FADE_DISABLED` / `DISTANCE_FADE_PIXEL_ALPHA` / `DISTANCE_FADE_PIXEL_DITHER` / `DISTANCE_FADE_OBJECT_DITHER` |
| `BaseMaterial3D.distance_fade_min_distance` | 淡出起点 |
| `BaseMaterial3D.distance_fade_max_distance` | 淡出终点 |
| `BaseMaterial3D.proximity_fade_enabled` | 近处淡出开关 |
| `BaseMaterial3D.proximity_fade_distance` | 淡出距离 |

两种淡出模式的区别：

- `DISTANCE_FADE_PIXEL_ALPHA` / `PIXEL_DITHER`：在**像素层面**渐变，需要写 alpha，会把材质变成半透明。
- `DISTANCE_FADE_OBJECT_DITHER`：在**物体层面**用抖动遮罩，材质仍然是完全不透明的，**不写深度**。

> 💡 **优先用 `DISTANCE_FADE_OBJECT_DITHER`**：它不会把物体变成透明，深度缓冲保持正确，也就不会破坏透明排序。

### 9.5 优化清单

按收益从大到小：

1. **合并材质**：把外观相同的物体共享一份材质资源。
2. **关掉用不上的高级特性**：`set_feature()` 把不需要的层关掉。
3. **删掉多余的 `next_pass`**：每一个 next pass 都是一次额外绘制。
4. **用 ORM 贴图**：把 AO / Roughness / Metallic 合成一张，省采样省显存。
5. **用 `MultiMesh` + 实例颜色**代替"复制材质"。
6. **远处物体关阴影、关高级特性**：`GeometryInstance3D.cast_shadow` + `visibility_range`。
7. **别在运行时改 `render_mode`**：那是热重编译。

---

## 📝 本章总结

材质这条线可以拆成三段来看：**参数**（`BaseMaterial3D` 的十一个参数组与 `ShaderMaterial` 的 uniform 覆盖）、**计算**（PBR 的漫反射 / 镜面 / 金属度工作流）、**编译**（从 `.gdshader` 文本到 GPU 管线的六步链路）。

三段之间最关键的一条结构性事实是：**`Material` 是 `Resource`**，所以"共享还是独立"是一个**场景组织层的决定**，而不是渲染器的决定。渲染器只是忠实地按你给的资源去建 uniform set 与管线——你在运行时不停 `duplicate()`，代价就全部由 GPU 状态切换来承担。

---

## 核心要点

1. **材质家族**：`Material` → `BaseMaterial3D` → `StandardMaterial3D`，另一支是 `Material` → `ShaderMaterial`；`StandardMaterial3D` 相对 `BaseMaterial3D` 没有增加任何属性。
2. **`StandardMaterial3D` 的十一个参数组**：基础 PBR、纹理槽（`BaseMaterial3D.TextureParam`）、高级特性（`BaseMaterial3D.Feature`）、标志位（`BaseMaterial3D.Flags`）、透明混合、折射/次表面/背光、高度图、顶点色/billboard/各向异性。
3. **PBR 的三个旋钮**：`diffuse_mode`（Burley 默认）、`specular_mode`（Schlick GGX 默认）、`metallic_specular`（非金属的 F0，默认 0.5）；金属没有漫反射分量。
4. **材质的三个挂载位置**：网格自带 → 实例 surface 覆盖 → `material_override` / `material_overlay`，后者破坏共享。
5. **`ShaderMaterial` 不会自动获得引擎光照**：必须在 `fragment()` 里给 `ALBEDO` / `ROUGHNESS` / `NORMAL` 等内置输出赋值。
6. **编译链路六步**：Shader 文本 → `shader_language.cpp` 前端 → 变体展开 → 内置 GLSL 拼接 → SPIR-V → 管线缓存 + material storage。
7. **改 uniform 不卡、改 `render_mode` 卡**：前者只更新 uniform buffer 的一段，后者要新 SPIR-V、新 uniform set、新管线，驱动侧可能重编译。
8. **uniform 分三层**：引擎内建 UBO（碰不到）、材质级 uniform（`set_shader_parameter()`）、全局 uniform（`global uniform` + `RenderingServer.global_shader_parameter_set()`）；跨材质共享的数据应该放第三层。

---

## 🔗 延伸阅读

- **官方文档**: [Standard Material 3D 与 ORM Material 3D](https://docs.godotengine.org/en/stable/tutorials/3d/standard_material_3d.html)、[着色器语言参考](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/shading_language.html)、[使用 ShaderMaterial](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/shading_language.html)
- **类参考**: [StandardMaterial3D](https://docs.godotengine.org/en/stable/classes/class_standardmaterial3d.html)、[ShaderMaterial](https://docs.godotengine.org/en/stable/classes/class_shadermaterial.html)、[Shader](https://docs.godotengine.org/en/stable/classes/class_shader.html)、[Material](https://docs.godotengine.org/en/stable/classes/class_material.html)、[GeometryInstance3D](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html)
- **源码位置**: `scene/resources/material.cpp`、`modules/visual_shader/visual_shader.cpp`、`servers/rendering/shader_language.cpp`、`servers/rendering/renderer_rd/shader_rd.cpp`、`servers/rendering/renderer_rd/pipeline_cache_rd.cpp`、`servers/rendering/renderer_rd/storage_rd/material_storage.cpp`、`servers/rendering/renderer_rd/forward_clustered/scene_shader_forward_clustered.cpp`

---

## 📋 下一章预告

**第 17 篇：GDShader 语言**

- spatial / canvas_item / particles 三种着色器类型
- 全局作用域的合法声明：uniform / varying / const
- 内置变量与内置函数：ALBEDO、UV、TIME、texture()
- 水波与溶解两个可运行的完整示例

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 15 篇：光照系统](/articles/15-lighting-system.md)
**下一篇**: [第 17 篇：GDShader 语言](/articles/17-gdshader-language.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
