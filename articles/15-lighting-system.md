# 第 15 篇：光照系统

> **本章导读**：光照是 3D 场景里最贵的部分之一，也是"看起来对不对"最敏感的部分。
> 本章把 Godot 4.3 的光照拆成四层来讲：实时光源（三种类型 + 全部公共属性）、阴影（PCF 过滤、PSSM 级联、Shadow Atlas）、全局光照（六条互不相同的路线）、以及只在烘焙里出现的编辑器流程。
> 读完后你能：（1）照着类参考把一盏灯调对；（2）分清"该用烘焙还是实时"的六种 GI 路线；（3）定位阴影瑕疵到底是偏移问题还是级联问题；（4）自己走完一次 Lightmap 烘焙。
> **前置知识**：第 14 篇《场景渲染流程》第 5.5 ~ 5.7 节（阴影 / 体积雾 / SDFGI 在 pass 顺序里的位置）。
> **难度**：进阶。

> **摘要**：Godot 的光照系统支持实时光照、烘焙光照、全局光照。本文将深入分析光照类型、阴影、SDFGI。

---

## 一、光照概览

### 1.1 场景里的光从哪来

一个 3D 场景里，最终到达像素的光一共来自四个方向：

| 来源 | 载体 | 直接光 / 间接光 | 实时 / 烘焙 |
|------|------|----------------|------------|
| **平行光** | `DirectionalLight3D` | 直接光 | 实时 |
| **点光源** | `OmniLight3D` | 直接光 | 实时 |
| **聚光灯** | `SpotLight3D` | 直接光 | 实时 |
| **环境光 / 天空** | `Environment` + `Sky` | 间接光（环境光遮蔽、天光） | 实时 |
| **烘焙光贴图** | `LightmapGI` + `LightmapGIData` | 间接光 + 烘焙的直接光 | 烘焙 |
| **体素 GI** | `VoxelGI` + `VoxelGIData` | 间接光 | 烘焙（可运行时重烘焙） |
| **探针** | `LightmapProbe` / `ReflectionProbe` | 只**取**间接光，不产生 | 实时 |
| **屏幕空间间接光** | `Environment.ssil_enabled` | 间接光 | 实时 |
| **符号距离场 GI** | `Environment.sdfgi_enabled` | 间接光 | 实时 |

这张表先给出全局观感：Godot 4.3 里"直接光"几乎全是实时的，"间接光"则有六条完全不同的路线。它们**不能叠加使用**——同一时刻通常只有一条 GI 路线在起作用。

### 1.2 光源类型

| 类型 | 说明 | 使用场景 |
|------|------|---------|
| **DirectionalLight3D** | 平行光 | 太阳光 |
| **OmniLight3D** | 点光源 | 灯泡、火把 |
| **SpotLight3D** | 聚光灯 | 手电筒、舞台灯 |
| **WorldEnvironment** | 环境光 | 天空光 |

三盏实时光源都继承自 `Light3D`，共享同一套公共属性（能量、颜色、阴影开关、烘焙模式……），区别只在"光的形状"：

| | `DirectionalLight3D` | `OmniLight3D` | `SpotLight3D` |
|---|---|---|---|
| 形状 | 平行（无穷远） | 球形 | 圆锥 |
| 距离衰减 | ❌ 无 | ✅ `omni_range` | ✅ `spot_range` |
| 专属属性 | `directional_shadow_*`、`sky_mode` | `omni_range`、`omni_attenuation`、`omni_shadow_mode` | `spot_range`、`spot_angle`、`spot_attenuation`、`spot_angle_attenuation` |
| 阴影贴图形态 | 级联（正交） | 立方体 / 双抛物面 | 立方体 / 双抛物面（带视角裁剪） |

> 💡 `WorldEnvironment` **不是光源**，它是"把 `Environment` 资源挂到场景里"的载体节点。`Environment` 里的环境光、天空、雾、SDFGI 都要靠它生效。

### 1.3 光照属性

`Light3D` 的公共属性分四组：

**A. 颜色与强度**

| 属性 | 类型 | 说明 |
|------|------|------|
| `Light3D.light_color` | Color | 光源颜色 |
| `Light3D.light_energy` | float | 光源能量（"强度"） |
| `Light3D.light_specular` | float | 高光贡献倍率（1.0 为标准，0 表示不产生高光） |
| `Light3D.light_indirect_energy` | float | 间接光贡献倍率 |
| `Light3D.light_negative` | bool | **负光**——能量取负，用来"扣掉"一片区域的光 |
| `Light3D.light_temperature` | float | 色温（开尔文），与 `light_color` 共同决定最终颜色 |
| `Light3D.light_intensity_lux` / `light_intensity_lumens` | float | 物理光照单位下的强度读数（Lux / 流明） |

**B. 尺寸与角度**（决定软阴影的"光源有多大"）

| 属性 | 类型 | 说明 |
|------|------|------|
| `Light3D.light_size` | float | 光源在**世界空间**里的尺寸（点光 / 聚光的"灯泡半径"） |
| `Light3D.light_angular_distance` | float | 光源在**角度**上的张角（度） |

**C. 阴影开关与阴影参数**：见第 2 章。

**D. 通用开关**

| 属性 | 类型 | 说明 |
|------|------|------|
| `Light3D.light_cull_mask` | int | 哪些 `VisualInstance3D.layers` 层能被这盏灯照到 |
| `Light3D.light_projector` | Texture2D | 投影贴图（聚光/平行光可用的"幻灯片"） |
| `Light3D.light_bake_mode` | int（枚举） | `BAKE_DISABLED` / `BAKE_STATIC` / `BAKE_DYNAMIC`，决定这盏灯参不参与烘焙 |
| `Light3D.light_volumetric_fog_energy` | float | 这盏光在体积雾里的散射强度（乘数） |
| `Light3D.distance_fade_enabled` | bool | 距离淡出开关 |
| `Light3D.distance_fade_begin` / `distance_fade_length` | float | 淡出起点与长度 |
| `Light3D.distance_fade_shadow` | float | 阴影随距离淡出的曲线 |
| `Light3D.editor_only` | bool | 只在编辑器里生效 |

一份可直接跑的最小配置：

```gdscript
# 太阳：平行光
var sun := DirectionalLight3D.new()
sun.light_color = Color(1.0, 0.92, 0.82)   # 暖色阳光
sun.light_energy = 1.2
sun.light_specular = 0.6
sun.light_indirect_energy = 1.0
sun.shadow_enabled = true
sun.directional_shadow_max_distance = 80.0
add_child(sun)

# 灯泡：点光源
var bulb := OmniLight3D.new()
bulb.light_color = Color(1.0, 0.85, 0.65)
bulb.light_energy = 3.0
bulb.omni_range = 12.0
bulb.omni_attenuation = 1.5
bulb.light_size = 0.15
bulb.shadow_enabled = true
bulb.omni_shadow_mode = OmniLight3D.SHADOW_CUBE
bulb.shadow_opacity = 0.85
add_child(bulb)

# 手电筒：聚光灯
var torch := SpotLight3D.new()
torch.light_energy = 6.0
torch.spot_range = 25.0
torch.spot_angle = 35.0
torch.spot_attenuation = 1.0
torch.spot_angle_attenuation = 1.0
torch.light_angular_distance = 1.5
add_child(torch)
```

> `shadow_max_distance` 是 **OmniLight3D / SpotLight3D** 的属性（点光/聚光的衰减距离）；平行光在 4.3 里只有 `directional_shadow_max_distance`、`directional_shadow_split_1/2/3`、`directional_shadow_fade_start`、`directional_shadow_pancake_size`、`directional_shadow_blend_splits` 这几个 `directional_shadow_*` 成员。

### 1.4 平行光的专属参数

| 属性 | 说明 |
|------|------|
| `DirectionalLight3D.sky_mode` | `SKY_MODE_LIGHT_AND_SKY` / `SKY_MODE_LIGHT_ONLY` / `SKY_MODE_SKY_ONLY`——平行光既当"太阳"又当"天空光"，还是只当其一 |
| `DirectionalLight3D.directional_shadow_max_distance` | 阴影的最远覆盖距离（默认 100.0） |

`sky_mode` 决定了"平行光和天空光是不是同一个东西"：设成 `SKY_MODE_LIGHT_ONLY` 时，天空会变成纯黑（只有这盏平行光照亮东西）；设成 `SKY_MODE_SKY_ONLY` 时，这盏灯不照亮物体，只给天空提供环境光。

### 1.5 负光：把一片区域"扣暗"

`Light3D.light_negative` 是一个很少用到但很实用的开关。打开后这盏灯的能量取负值，作用是**从已有的光里扣除**一部分。

典型用法：在一个房间里放一盏负光，位置与房间里的主灯重合但强度略高，用来抵消主灯从窗外漏进来的部分，让室内更暗——这样你不需要给室内的所有材质单独调暗。

### 1.6 物理光照单位

`Light3D.light_intensity_lux` 与 `Light3D.light_intensity_lumens` 把"能量"换算成现实世界的照度单位。注意两者的适用对象不同：

| 光源 | 现实单位 | 引擎里的量 |
|------|----------|------------|
| 平行光 | 照度（Lux） | 阳光正午约 100,000 Lux |
| 点光 / 聚光 | 光通量（流明） | 一个 60 W 白炽灯约 800 流明 |

`Light3D.get_correlated_color()` 可以拿到"色温 + 颜色"换算后的最终颜色（`Color`），用来在脚本里算实际照射到物体上的颜色。

```gdscript
var sun := DirectionalLight3D.new()
sun.light_temperature = 5600.0     # 正午偏冷
sun.light_energy = 1.0
var actual := sun.get_correlated_color()
print("实际颜色：", actual)
```

---

## 二、阴影系统

### 2.1 阴影类型

| 类型 | 说明 | 性能 |
|------|------|------|
| **硬阴影** | 清晰边缘 | 低 |
| **软阴影** | 模糊边缘（`Light3D.shadow_blur`） | 中 |
| **PCF 阴影** | 百分比渐近过滤，Godot 4 软阴影的底层算法 | 中 |
| **PSSM 级联阴影** | 平行光按视锥切分 2 / 4 段级联（`DirectionalLight3D.directional_shadow_mode`） | 中～高 |
| **PCSS** | 百分比渐近软阴影，由 `light_size` / `light_angular_distance` 控制光源角径 | 高 |

> **没有 VSM**：Godot 4.3 的 `DirectionalLight3D.ShadowMode` 只有 `SHADOW_ORTHOGONAL(0)` / `SHADOW_PARALLEL_2_SPLITS(1)` / `SHADOW_PARALLEL_4_SPLITS(2)`，Godot 3.x 同样没有方差阴影（VSM）。

### 2.2 阴影的公共开关与参数

所有实时光源共享 `Light3D` 上的阴影参数：

| 属性 | 类型 | 说明 |
|------|------|------|
| `Light3D.shadow_enabled` | bool | 总开关 |
| `Light3D.shadow_bias` | float | 沿光线方向的深度偏移 |
| `Light3D.shadow_normal_bias` | float | 沿法线方向的偏移 |
| `Light3D.shadow_blur` | float | PCF 过滤半径（越大越软，也越糊） |
| `Light3D.shadow_opacity` | float | 阴影不透明度（0 = 全透） |
| `Light3D.shadow_transmittance_bias` | float | 透射阴影的偏移修正 |
| `Light3D.shadow_reverse_cull_face` | bool | 反转剔除面 |

另外两个决定"光源有多大"的参数：

| 属性 | 说明 |
|------|------|
| `Light3D.light_size` | 世界空间里的光源尺寸（点光 / 聚光） |
| `Light3D.light_angular_distance` | 光源的角度张角（度） |

**`light_size` 与 `light_angular_distance` 的区别**是这一章最值得记住的一组对照：

| | `light_size` | `light_angular_distance` |
|---|---|---|
| 单位 | 世界单位（米） | 度 |
| 适用 | 点光 / 聚光（距离有限） | 平行光（距离无限） |
| 物理含义 | 灯泡的物理半径 | 太阳的视直径（0.53° 是真实太阳） |
| 对阴影的影响 | 越大，阴影边缘越软 | 越大，阴影边缘越软 |

对平行光来说，太阳"有大小"这件事在几何上不可能用世界尺寸表达（它在无穷远），所以只能用角度。

### 2.3 平行光：PSSM 级联

平行光最难的地方在于：它要从"太阳"一直照到"地平线"，而阴影贴图是正交的，贴图边长有限。要同时保证近处清晰、远处覆盖，只能**切成几段**，每段用一张贴图——这就是 **PSSM（Percentage-Closer Soft Shadows 的级联变体）**。

`DirectionalLight3D.directional_shadow_mode` 有三个取值：

| 取值 | 枚举名 | 级联数 | 适合场景 |
|------|--------|--------|----------|
| 0 | `SHADOW_ORTHOGONAL` | 1 | 固定视角的小场景、俯视视角、纯风格化 |
| 1 | `SHADOW_PARALLEL_2_SPLITS` | 2 | 中等场景 |
| 2 | `SHADOW_PARALLEL_4_SPLITS` | 4 | 大场景、第一人称、远景要求高 |

**级联是怎么分的**（这是理解阴影瑕疵的关键）：

```
相机视锥（近 → 远）
 ├──────────┬──────────┬──────────┬──────────┐
 │ 级联 0   │ 级联 1   │ 级联 2   │ 级联 3   │
 │ 最细     │ 稍粗     │ 更粗     │ 最粗     │
 └──────────┴──────────┴──────────┴──────────┘
   ↑ split_1    ↑ split_2    ↑ split_3   ↑ max_distance
```

每段级联的正交范围**逐渐变大**，贴图边长**不变**，所以越远的级联**每像素覆盖的世界尺寸越大**、越糊。这就是为什么远景阴影总是"毛茸茸"的——不是 bug，是级联的固有代价。

### 2.4 级联参数逐项解释

| 属性 | 说明 |
|------|------|
| `DirectionalLight3D.directional_shadow_max_distance` | 整个阴影范围的**最远距离**（默认 100.0） |
| `DirectionalLight3D.directional_shadow_split_1` | 第 1 段与第 2 段的**分界**（0 ~ 1 的比例，相对最大距离） |
| `DirectionalLight3D.directional_shadow_split_2` | 第 2 段与第 3 段的分界 |
| `DirectionalLight3D.directional_shadow_split_3` | 第 3 段与第 4 段的分界 |
| `DirectionalLight3D.directional_shadow_fade_start` | 级联开始混合（淡出）的比例——避免级联边界"啪"地跳变 |
| `DirectionalLight3D.directional_shadow_blend_splits` | 混合的平滑度 |
| `DirectionalLight3D.directional_shadow_pancake_size` | 阴影"薄饼"的偏移量，用**近处**的深度精度换**远处**的精度 |

```gdscript
# 阴影设置（DirectionalLight3D）
var light = DirectionalLight3D.new()
light.shadow_enabled = true
light.directional_shadow_max_distance = 50  # 减少阴影距离
light.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
light.directional_shadow_split_1 = 0.1     # 各段距离（相对最大距离的比例）
light.directional_shadow_split_2 = 0.2
light.directional_shadow_split_3 = 0.5
light.shadow_bias = 0.1        # 阴影偏移
light.shadow_normal_bias = 2.0 # 沿法线偏移
```

> `shadow_orthogonal_size` 在 4.3 **不存在**。平行光的正交阴影范围由 `directional_shadow_max_distance` 决定；与之最接近的另一个属性是 `directional_shadow_pancake_size`（默认 20.0），它调整的是阴影"薄饼"偏移，用来在近处换取更高的深度精度，而不是阴影贴片的边长。

**调级联的实操顺序**：

1. 先把 `directional_shadow_max_distance` 设成"我只需要看到这么远"——它同时决定了四级联的总范围。
2. 再调三个 split：让靠近相机的级联覆盖更多（近处阴影通常最需要清晰）。
3. 最后调 `directional_shadow_fade_start`（默认接近 1），让级联之间的过渡落在视线不敏感的地方。
4. `directional_shadow_pancake_size` 只在"远处阴影闪烁 / 深度精度不够"时才需要动。

> ⚠️ `directional_shadow_max_distance` 调大 → 每级联覆盖范围变大 → 阴影变糊；同时级联数量不变时，等于"用更少的信息覆盖更大的面积"。

### 2.5 点光与聚光：立方体 vs 双抛物面

`OmniLight3D.omni_shadow_mode` 有两个取值：

| 取值 | 枚举名 | 贴图形态 | 特点 |
|------|--------|----------|------|
| 0 | `SHADOW_CUBE` | 立方体贴图（6 面） | 360° 无死角，精度高，开销大 |
| 1 | `SHADOW_DUAL_PARABOLOID` | 双抛物面（2 张） | 上下两个半球各一张，省一半开销，接缝处精度差 |

**选型建议**：

- 室内点光、烛火这类**近距离、小范围**的光：默认的 `SHADOW_CUBE` 就够。
- 大范围、无关紧要的环境点光（走廊里的一排小灯）：用 `SHADOW_DUAL_PARABOLOID` 省钱。
- 聚光灯虽然也有立方体阴影，但渲染时会把立方体**按视锥裁剪**，只渲染看得见的那一面，所以聚光的阴影开销比点光低。

### 2.6 Shadow Atlas：多盏灯的阴影贴图怎么放

平行光用"每盏灯一组级联贴图"，而**点光与聚光共用一张大贴图**——这张贴图就是 **Shadow Atlas（阴影图集）**。

```
Shadow Atlas（一张大贴图，例如 4096 × 4096）
┌──────────┬──────────┬──────────┬──────────┐
│ 灯 A     │ 灯 B     │ 灯 C     │ 灯 D     │
│ 1024²    │ 512²     │ 512²     │ 256²     │
└──────────┴──────────┴──────────┴──────────┘
```

规则是：

1. 每盏需要投影的灯在图集里占**一块正方形区域**，边长从固定的几档里选（256 / 512 / 1024 / 2048 …）。
2. 分配策略是**按需**：只有 `shadow_enabled` 且 `light_cull_mask` 能照到可见物体时，才会去占图集。
3. 图集满了，新的灯**拿不到阴影**（或者被降级）。

这条规则的直接后果是**"灯越多，阴影越糊"**：当图集不够用时，新加入的灯只能分到更小的区域，阴影分辨率下降。

**影响图集的因素**：

| 因素 | 影响 |
|------|------|
| 同时开启阴影的灯的数量 | 越多越挤 |
| 每盏灯照亮的范围 | 范围大 → 分到的区域大 |
| 物体的阴影精度要求 | 精度要求高 → 需要更大区域 |
| 图集的总边长 | 在项目设置里调整（4.3 位于「项目设置 → 图形 → 阴影」分组） |

> 💡 **实测技巧**：把「调试 → 显示性能」打开，盯住**阴影 pass** 那一项。如果它是帧时间的大头，第一反应应该是"关掉一些不必要的灯的阴影"，而不是"调低阴影质量"。

### 2.7 软阴影的两条路径

Godot 4.3 的软阴影有两条实现路径，行为差别很大：

| 路径 | 靠什么变软 | 表现 |
|------|------------|------|
| **PCF（Percentage Closer Filtering）** | `Light3D.shadow_blur` —— 采样核的半径 | **半影宽度恒定**（跟光源大小无关），远处也一样宽 |
| **PCSS（Percentage Closer Soft Shadows）** | `light_size` / `light_angular_distance` —— 光源的实际大小 | **半影随距离变宽**（近处窄、远处宽），更接近真实 |

这两条不是"二选一"，而是**同时生效**：

- `shadow_blur` 决定"最小有多软"；
- `light_size` / `light_angular_distance` 决定"半影随距离增长得多快"。

如果你的场景里**点光的阴影边缘看起来是硬边**，那是因为 `light_size` 是 0（默认）——点光源在物理上是零半径的，但视觉上完全不合理。给它一个 0.1 ~ 0.3 的值，阴影立刻会自然很多。

```gdscript
var bulb := OmniLight3D.new()
bulb.light_size = 0.2            # 灯泡半径 20 cm
bulb.shadow_blur = 1.5            # 基础 PCF 半径
bulb.shadow_enabled = true
```

### 2.8 阴影偏移四件套

阴影瑕疵 90% 出在偏移参数上。四个参数各管一件事：

| 参数 | 方向 | 调过头的症状 | 调不够的症状 |
|------|------|--------------|--------------|
| `shadow_bias` | 沿光线方向推远 | 阴影整体偏移、悬空 | 阴影出现条纹（shadow acne） |
| `shadow_normal_bias` | 沿表面法线推离 | 阴影脱离物体（peter-panning） | 同样出条纹 |
| `shadow_transmittance_bias` | 透射阴影专用 | 玻璃后的阴影变形 | 半透明物体的阴影不出现 |
| `shadow_reverse_cull_face` | 翻转剔除面 | — | 单面片物体的阴影消失 |

**标准排查顺序**：

1. 先只调 `shadow_bias`，往大调，直到条纹消失。
2. 条纹消失但阴影明显"浮"起来了 → 把 `shadow_bias` 降回去，改用 `shadow_normal_bias`。
3. `shadow_normal_bias` 也调过头（阴影脱离）→ 降低它，回到第 1 步。

> 💡 **偏移不是免费的**。偏移越大，越不会出条纹，但阴影与物体的接触越"不真实"。真实引擎的做法是用"接触阴影"补回来——Godot 4.3 没有独立的接触阴影通道（那是 Unity 的特性），所以只能靠适当的偏移量来折中。

### 2.9 阴影相关的性能建议

| 建议 | 原因 |
|------|------|
| 能用 `BAKE_STATIC` 烘焙的灯就别开实时阴影 | 烘焙阴影不占 Shadow Atlas，也不占阴影 pass 的几何遍历 |
| 点光阴影按需开 | 灯一多，Shadow Atlas 就不够了，剩下的灯只能拿低分辨率阴影 |
| 平行光优先用 2 段级联 | 4 段级联的绘制量大约是 2 段的 2 倍 |
| `directional_shadow_max_distance` 别贪大 | 范围越大，级联覆盖越广，阴影越糊 |
| 远处物体关阴影 | `GeometryInstance3D.cast_shadow` 设成 `SHADOW_CASTING_SETTING_OFF` |
| 留意 `Light3D.light_cull_mask` | 用层遮罩把互不相干的区域分到不同的灯 |

### 2.10 用层遮罩把灯分开

`Light3D.light_cull_mask` 是一个位掩码，决定"这盏灯能照到哪些物体"。它匹配的是 `VisualInstance3D.layers`（物体所在的层）。

| 配置 | 效果 |
|------|------|
| 灯的 `light_cull_mask` = 物体 `layers` 的**按位与** | 灯照不到 → 物体在这盏灯下是全黑的 |
| 两者有公共位 | 灯能照到 |

典型用法：

1. 把场景分成"室内"与"室外"两层。
2. 室内的灯 `light_cull_mask` 只勾"室内"层 → 室外的灯不会照进来。
3. 室外的大范围环境光（`ReflectionProbe` 之类）同样按层过滤。

```gdscript
# 第 1 层 = 室内，第 2 层 = 室外
var indoor := OmniLight3D.new()
indoor.light_cull_mask = 1 << 0     # 只照第 1 层
add_child(indoor)

$OutdoorWall.layers = 1 << 1        # 第 2 层
```

> 💡 **层遮罩是"免费"的优化**：一盏照不到任何东西的灯，仍然要进阴影 pass、仍然要占 Shadow Atlas。把灯的遮罩配对好，能省掉一整轮几何渲染。

---

## 三、全局光照（GI）方案全景

### 3.1 Godot 4 的 GI 方案全景

4.3 注册了五个 GI 相关类，再加上环境里的 SDFGI，一共是六条互不相同的路线：

| 方案 | 载体 | 类型 | 说明 |
|------|------|------|------|
| **LightmapGI** | 节点 + `LightmapGIData` | 烘焙（静态） | 运行时开销最低；动态物体靠 `LightmapProbe` 取间接光 |
| **VoxelGI** | 节点 + `VoxelGIData` | 烘焙（可运行时更新） | 体素化探针，可动态重烘焙，开销高于 LightmapGI |
| **LightmapProbe** | 节点 | 探针 | 只为动态物体**取**间接光，本身不产生间接光 |
| **ReflectionProbe** | 节点 | 探针 | 提供反射与间接光 |
| **SDFGI** | `Environment.sdfgi_enabled` | 实时 | 符号距离场，随相机运行时更新，**仅 Forward+ 支持** |
| **SSIL** | `Environment.ssil_enabled` | 实时（屏幕空间） | 屏幕空间间接光，仅 Forward+ 支持 |

五个 GI 类的注册点在场景类型的注册代码里（`scene/register_scene_types.cpp:575-579` 附近）：

```cpp
// Godot 4.3 源码 - scene/register_scene_types.cpp:575-579 附近
// 注册的五个 GI 相关类：
//   VoxelGI / VoxelGIData    —— 体素 GI（节点 + 数据资源）
//   LightmapGI / LightmapGIData —— 光照贴图 GI（节点 + 数据资源）
//   LightmapProbe            —— 探针（只取光）
```

注意注册的是**五个类**（两个节点 + 两个数据资源 + 一个探针），而 `ReflectionProbe` 不在这五个里——它属于"探针"家族，和 `LightmapProbe` 是两类东西。

### 3.2 LightmapGI：静态烘焙的标准解

`LightmapGI` 是最常用的方案：**烘一次，运行时零成本**。

工作方式：把场景里标记为静态的网格按 UV2 展开成图集，烘焙器把每个 texel 的直接光与间接光算出来存进 `LightmapGIData`，运行时材质只要采样这张贴图即可。

| 特性 | 说明 |
|------|------|
| 运行时开销 | **几乎为零**（一次纹理采样） |
| 动态物体 | ❌ 不会出现在光贴图里 → 需要 `LightmapProbe` 补间接光 |
| 动态光源 | ❌ 烘焙时刻的光照被固化 |
| 内存 | 光贴图图集 + 烘焙数据 |
| 精度 | 高（离线求解，无实时近似误差） |

`LightmapGI` 的关键属性：

| 属性 | 说明 |
|------|------|
| `LightmapGI.light_data` | 烘焙产物，类型是 `LightmapGIData` |
| `LightmapGI.quality` | 烘焙质量：`BAKE_QUALITY_LOW` / `BAKE_QUALITY_MEDIUM` / `BAKE_QUALITY_HIGH` / `BAKE_QUALITY_ULTRA` |
| `LightmapGI.texel_scale` | 每个纹素覆盖的世界尺寸（越小越精细，也越慢） |
| `LightmapGI.max_texture_size` | 单张光贴图的最大边长 |
| `LightmapGI.bounces` | 反弹次数 |
| `LightmapGI.bounce_indirect_energy` | 间接光反弹的能量比例 |
| `LightmapGI.use_texture_for_bounces` | 反弹时使用纹理而非顶点色 |
| `LightmapGI.generate_probes_subdiv` | 顺带生成 `LightmapProbe` 的细分等级 |
| `LightmapGI.use_denoiser` / `denoiser_strength` / `denoiser_range` | 降噪设置 |
| `LightmapGI.bias` / `directional` / `interior` | 烘焙的偏置、方向性、室内模式 |
| `LightmapGI.environment_mode` | `ENVIRONMENT_MODE_DISABLED` / `ENVIRONMENT_MODE_SCENE` / `ENVIRONMENT_MODE_CUSTOM_SKY` / `ENVIRONMENT_MODE_CUSTOM_COLOR` |
| `LightmapGI.environment_custom_color` / `environment_custom_energy` / `environment_custom_sky` | 自定义环境光 |
| `LightmapGI.camera_attributes` | 相机属性（影响降噪与色调） |

### 3.3 VoxelGI：可以运行时重烘焙的 GI

`VoxelGI` 用**体素化**的方式表示场景遮挡，探针在体素网格上求解间接光。

| 特性 | 说明 |
|------|------|
| 运行时开销 | 比 LightmapGI 高（要采样体素） |
| 动态物体 | ⚠️ 部分支持——体素化时会被记录进遮挡信息 |
| 动态光源 | ✅ 可以在运行时重新烘焙 |
| 体积 | 随场景体积与 `subdiv` 增长 |

| 属性 | 说明 |
|------|------|
| `VoxelGI.data` | 体素数据，类型是 `VoxelGIData` |
| `VoxelGI.size` | 体素化区域的尺寸（X / Y / Z 的格数） |
| `VoxelGI.subdiv` | 细分等级：`SUBDIV_64` / `SUBDIV_128` / `SUBDIV_256` / `SUBDIV_512` |
| `VoxelGI.camera_attributes` | 相机属性 |
| `VoxelGI.bake()` | **在运行时烘焙**（4.3 里 VoxelGI 有这个方法，LightmapGI 没有） |
| `VoxelGI.debug_bake()` | 调试用的烘焙 |

`VoxelGIData` 上的参数：

| 属性 | 说明 |
|------|------|
| `VoxelGIData.normal_bias` | 法线方向偏置（减少漏光） |
| `VoxelGIData.bias` | 通用偏置 |
| `VoxelGIData.dynamic_range` | 动态范围压缩 |
| `VoxelGIData.energy` | 能量倍率 |
| `VoxelGIData.use_two_bounces` | 是否计算两次反弹 |
| `VoxelGIData.propagation` | 传播方式 |
| `VoxelGIData.interior` | 室内模式（影响多次反弹的传播） |

> 💡 **`VoxelGI.bake()` 存在、`LightmapGI.bake()` 不存在**，这是 4.3 里两个烘焙方案最大的 API 差异。VoxelGI 可以在游戏运行时重烘焙（适合"玩家建造后重新计算 GI"的场景），代价是重烘焙的那一帧会有明显卡顿。

### 3.4 LightmapProbe：只取光，不发光

`LightmapProbe` 是**采样点**，不是光源。它的工作是：在运行时从 `LightmapGIData`（或 `VoxelGIData`）里取出该位置的间接光，供**动态物体**使用。

典型用法是：一张烘焙好的光贴图场景里放一个飞行的角色，角色用实时材质渲染，它需要知道"我所在位置的间接光是什么颜色"——探针就是干这个的。

```gdscript
# 在场景里放若干个 LightmapProbe，覆盖动态物体活动的区域
var lp := LightmapProbe.new()
lp.position = Vector3(0, 2, 0)
add_child(lp)
```

**探针的密度决定质量**：探针之间是插值的，探针太稀会导致间接光"糊成一片"；探针太密会增加内存与采样开销。

| 方案 | 探针来源 |
|------|----------|
| `LightmapGI` | 烘焙时按 `LightmapGI.generate_probes_subdiv` 自动生成（可手摆覆盖） |
| `VoxelGI` | 随体素一起烘焙 |
| `SDFGI` | 运行时自动生成的探针网格（不可手动摆放） |

> ⚠️ `LightmapProbe` 在 4.3 的类参考里**没有任何属性**（它继承 `Node3D`，只多了 `position` / `rotation` 这些变换属性）。它没有 `bake` 方法，也没有"烘焙质量"属性——这些都在 `LightmapGI` 上。

### 3.5 ReflectionProbe：反射 + 间接光

`ReflectionProbe` 渲染一张 cubemap，供**镜面反射**与**间接光**使用。

| 属性 | 说明 |
|------|------|
| `ReflectionProbe.size` | 探针盒的尺寸（决定 cubemap 的分辨率档位） |
| `ReflectionProbe.origin_offset` | 探针盒的原点偏移 |
| `ReflectionProbe.max_distance` | 影响范围上限 |
| `ReflectionProbe.update_mode` | `UPDATE_ONCE` / `UPDATE_ALWAYS` |
| `ReflectionProbe.ambient_mode` | `AMBIENT_DISABLED` / `AMBIENT_ENVIRONMENT` / `AMBIENT_COLOR` |
| `ReflectionProbe.ambient_color` / `ambient_color_energy` | 自定义环境色 |
| `ReflectionProbe.box_projection` | 盒式投影（用于盒装房间的反射） |
| `ReflectionProbe.enable_shadows` | 反射里是否含阴影 |
| `ReflectionProbe.cull_mask` / `reflection_mask` | 剔除遮罩 |
| `ReflectionProbe.interior` | 室内模式 |
| `ReflectionProbe.mesh_lod_threshold` | 生成反射时网格的 LOD 阈值 |
| `ReflectionProbe.intensity` | 强度 |

```gdscript
var probe := ReflectionProbe.new()
probe.size = Vector3(10, 4, 10)
probe.update_mode = ReflectionProbe.UPDATE_ALWAYS
probe.ambient_mode = ReflectionProbe.AMBIENT_COLOR
probe.ambient_color = Color(0.2, 0.22, 0.3)
probe.max_distance = 40.0
add_child(probe)
```

> 💡 `update_mode = UPDATE_ALWAYS` 每帧重算 cubemap，开销不小。静态场景用 `UPDATE_ONCE` 即可；只有当场景里的东西会动、反射需要跟着变时才用 `UPDATE_ALWAYS`。

### 3.6 SDFGI 设置

SDFGI 是**完全实时**的间接光方案：用符号距离场表示遮挡，运行时在 GPU 上求解探针。

```gdscript
# 启用 SDFGI
# 注意：WorldEnvironment.environment 默认为 null，必须先 new 一个 Environment 赋进去，
#       否则下面一行会报 "Invalid access to property or key 'environment' on a base object of type 'null'"
var world_env := WorldEnvironment.new()
var env := Environment.new()
world_env.environment = env
add_child(world_env)

env.sdfgi_enabled = true
# sdfgi_y_scale 是枚举（50% / 75% / 100%），不是浮点数
env.sdfgi_y_scale = Environment.SDFGI_Y_SCALE_75_PERCENT
env.sdfgi_cascades = 4
env.sdfgi_max_distance = 204.8
env.sdfgi_min_cell_size = 0.2
```

> 泛光（glow）和 SDFGI 是两回事：它们只是挂在同一个 `Environment` 资源上的两组独立属性。
>
> ```gdscript
> env.glow_enabled = true   # 泛光，与 SDFGI 无关
> ```

SDFGI 的完整参数与它在 pass 顺序里的位置，见第 14 篇第 5.7 节。这里只强调选型层面的一条：

| 场景 | 建议 |
|------|------|
| 移动端 | **不要用** SDFGI（Mobile 渲染器不支持） |
| 静态关卡 | 用 `LightmapGI`，质量更高、运行时零成本 |
| 动态场景 / 玩家建造 | 用 `VoxelGI`（可运行时重烘焙）或 SDFGI（完全实时） |
| 远景 | SDFGI 的级联外精度会明显下降 |

### 3.7 SSIL：屏幕空间间接光

`Environment.ssil_enabled` 打开的是**屏幕空间**间接光：它从当前屏幕的深度与颜色里推断光线的多次反弹。

| 属性 | 说明 |
|------|------|
| `Environment.ssil_enabled` | 开关 |
| `Environment.ssil_intensity` | 强度 |
| `Environment.ssil_radius` | 采样半径 |
| `Environment.ssil_sharpness` | 锐度 |
| `Environment.ssil_normal_rejection` | 法线剔除（减少屏幕边缘的误判） |

**SSIL 的根本限制**：它只能看到**屏幕里已经画出来的东西**。屏幕外的物体对间接光没有任何贡献，物体刚进入屏幕时也没有历史数据。所以它常与 SSAO 一起开（`Environment.ssao_enabled`），作为"轻量级 GI"的补充，而不是替代。

### 3.8 环境光与反射光

除了上面五条 GI 路线，`Environment` 上还有两组最基础的光：

| 属性 | 取值 | 说明 |
|------|------|------|
| `Environment.ambient_light_source` | `AMBIENT_SOURCE_BG` / `AMBIENT_SOURCE_DISABLED` / `AMBIENT_SOURCE_COLOR` / `AMBIENT_SOURCE_SKY` | 环境光从哪来 |
| `Environment.ambient_light_color` | Color | 自定义环境色 |
| `Environment.ambient_light_energy` | float | 环境光强度 |
| `Environment.ambient_light_sky_contribution` | float | 天空对环境光的贡献比例 |
| `Environment.reflected_light_source` | `REFLECTION_SOURCE_BG` / `REFLECTION_SOURCE_DISABLED` / `REFLECTION_SOURCE_SKY` | 反射光从哪来 |
| `Environment.background_mode` | `BG_CLEAR_COLOR` / `BG_COLOR` / `BG_SKY` / `BG_CANVAS` / `BG_KEEP` / `BG_CAMERA_FEED` | 背景怎么画 |

> 💡 `AMBIENT_SOURCE_SKY` 意味着"天空既是背景，也是环境光"。这时**平行光的 `sky_mode` 就会影响整个场景的亮度**——把太阳设成 `SKY_MODE_LIGHT_ONLY` 会让天空变黑、环境光也没了。

### 3.9 GI 方案选型表

| 维度 | LightmapGI | VoxelGI | LightmapProbe | ReflectionProbe | SDFGI | SSIL |
|------|-----------|---------|---------------|-----------------|-------|------|
| 产生间接光 | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| 烘焙 | 编辑器 | 编辑器 / 运行时 | 依附于烘焙 | 运行时 | 不需要 | 不需要 |
| 运行时开销 | 极低 | 中 | 低 | 中～高 | 中～高 | 低 |
| 动态物体 | ❌（需探针） | ⚠️ 部分 | ✅（取光） | ✅ | ✅ | ✅ |
| 动态光源 | ❌ | ✅（需重烘焙） | ✅（取烘焙结果） | ✅ | ✅ | ✅ |
| Mobile 支持 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 内存开销 | 中 | 中 | 低 | 中 | 中～高 | 低 |

**一句话选型**：

- **静态关卡 → `LightmapGI`**（默认答案）。
- **玩家能改造场景 → `VoxelGI` + 运行时 `bake()`**。
- **完全动态、且是桌面平台 → `SDFGI`**。
- **动态物体需要接收间接光 → 加 `LightmapProbe`**（Lightmap 方案）或依赖 SDFGI/SSIL。
- **需要真实镜面反射 → `ReflectionProbe`**。

---

## 四、光照烘焙流程

### 4.1 烘焙光照贴图

`LightmapGI` 的**烘焙只在编辑器里进行**，4.3 的 `LightmapGI` 类没有暴露任何 `<methods>`，`bake()` 之类的方法并不存在。正确流程是：

```
编辑器操作（不是脚本）：
1. 在场景里添加 LightmapGI 节点
2. 把静态网格的 GeometryInstance3D.gi_mode 设为 GI_MODE_STATIC
3. 保证网格有 UV2（Lightmap）
4. 把光源的 Light3D.light_bake_mode 设为 BAKE_STATIC
5. 点工具栏的 "Bake Lightmap" 按钮
   ↓
烘焙完成后，节点上会自动出现一个 LightmapGIData 资源
```

脚本侧能做的只是**读取**烘焙结果：

```gdscript
var gi := $LightmapGI
var data := gi.light_data          # 类型是 LightmapGIData，不是 String
if data != null:
    print("已烘焙，可以读取 LightmapGIData 资源")
else:
    print("尚未烘焙：请在编辑器中点击 Bake Lightmap")
```

> `gi.light_data = "res://lightmap.gi"` 是错的：`light_data` 的类型是 **`LightmapGIData` 资源**，官方文档写明"This resource is automatically created after baking, and is not meant to be created manually"——它由烘焙流程自动创建并写回。
>
> 烘焙质量用 `LightmapGI.quality`，取值是 `BAKE_QUALITY_LOW` / `BAKE_QUALITY_MEDIUM` / `BAKE_QUALITY_HIGH` / `BAKE_QUALITY_ULTRA`（不是 `QUALITY_HIGH`）。光源侧的烘焙开关是 `Light3D.light_bake_mode`：`BAKE_DISABLED` / `BAKE_STATIC` / `BAKE_DYNAMIC`（不是 `LightmapGI.BAKE_MODE_STATIC`——`LightmapGI` 上并没有 `bake_mode` 这个成员）。

#### 4.1.1 静态 / 动态 / 禁用：三档烘焙模式

`Light3D.light_bake_mode` 的三个取值，决定这盏灯在烘焙时**怎么**参与：

| 取值 | 含义 | 典型用法 |
|------|------|----------|
| `BAKE_DISABLED` | 完全不参与烘焙 | 纯实时的动态光（玩家角色的手电筒） |
| `BAKE_STATIC` | 烘焙进光贴图，运行时不再计算 | 太阳、不会动的吊灯 |
| `BAKE_DYNAMIC` | 只烘焙它的间接光贡献，直射光仍实时计算 | 会移动的灯（虽然位置变了，但间接光仍然有用） |

对应的网格侧也有一个开关：

```gdscript
# 静态网格：烘焙进光贴图
$StaticBox.gi_mode = GeometryInstance3D.GI_MODE_STATIC
# 动态网格：不进光贴图，靠探针取间接光
$Player.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
# 完全不参与 GI
$Prop.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
```

`GeometryInstance3D.gi_mode` 的三个取值是 `GI_MODE_DISABLED` / `GI_MODE_STATIC` / `GI_MODE_DYNAMIC`。

> 💡 **`BAKE_STATIC` 的灯在运行时就不再产生实时直射光**。烘焙之后如果把这盏灯的 `light_bake_mode` 改成 `BAKE_DISABLED` 而不重新烘焙，画面会**变暗**（少了烘焙进去的那部分）——这是"改了灯却变暗"最常见的原因。

### 4.2 烘焙质量与纹素密度

| 参数 | 影响 |
|------|------|
| `LightmapGI.quality` | 烘焙器的采样质量（`BAKE_QUALITY_LOW` ~ `BAKE_QUALITY_ULTRA`） |
| `LightmapGI.texel_scale` | 纹素的世界尺寸，**这是决定精度的主要旋钮** |
| `LightmapGI.max_texture_size` | 单张图集的最大边长 |
| `LightmapGI.bounces` | 反弹次数 |
| `LightmapGI.use_denoiser` | 是否降噪（4.3 默认开启） |
| `LightmapGI.use_texture_for_bounces` | 反弹时用纹理而不是顶点色 |

**精度问题的排查顺序**：

1. 阴影边界糊 → 不是光贴图问题，是 `LightmapGI.texel_scale` 太大（纹素太大）。
2. 间接光有噪点 → 提高 `quality`，或依赖 `use_denoiser`。
3. 间接光整体偏暗 → 检查 `bounce_indirect_energy` 与 `Environment.ambient_light_energy`。

### 4.3 LightmapGI 的环境光模式

`LightmapGI.environment_mode` 决定烘焙时"用哪份环境光"：

| 取值 | 含义 |
|------|------|
| `ENVIRONMENT_MODE_DISABLED` | 烘焙里不包含环境光 |
| `ENVIRONMENT_MODE_SCENE` | 用场景里 `WorldEnvironment` 的环境光 |
| `ENVIRONMENT_MODE_CUSTOM_SKY` | 用 `environment_custom_sky` 指定的天空 |
| `ENVIRONMENT_MODE_CUSTOM_COLOR` | 用 `environment_custom_color` 指定的纯色 |

自定义模式对应的属性是 `LightmapGI.environment_custom_color`（Color）、`LightmapGI.environment_custom_energy`（float）、`LightmapGI.environment_custom_sky`（`Sky` 资源）。

> 💡 **"我改了 `Environment.ambient_light_color`，但烘焙出来的图没变"** —— 几乎总是因为 `environment_mode` 不在 `ENVIRONMENT_MODE_SCENE`。用 `ENVIRONMENT_MODE_CUSTOM_COLOR` 时，场景环境被完全忽略。

### 4.4 探针的生成

烘焙 Lightmap 时，可以顺带生成 `LightmapProbe` 的数据：

| 属性 | 说明 |
|------|------|
| `LightmapGI.generate_probes_subdiv` | `GENERATE_PROBES_DISABLED` / `GENERATE_PROBES_SUBDIV_4` / `GENERATE_PROBES_SUBDIV_8` / `GENERATE_PROBES_SUBDIV_16` / `GENERATE_PROBES_SUBDIV_32` |

数值越大，探针网格越密，动态物体取到的间接光越细腻，内存也越大。

烘焙产物 `LightmapGIData` 上也有几个值得知道的成员：

| 成员 | 说明 |
|------|------|
| `LightmapGIData.lightmap_textures` | 光贴图纹理数组 |
| `LightmapGIData.light_texture` | 单张光贴图 |
| `LightmapGIData.get_user_count()` | 引用计数（多个场景共用一份烘焙数据时用得上） |
| `LightmapGIData.get_user_path()` | 引用者路径 |
| `LightmapGIData.is_using_spherical_harmonics()` | 是否使用球谐 |
| `LightmapGIData.set_uses_spherical_harmonics()` | 切换球谐模式 |

### 4.5 VoxelGI 的运行时重烘焙

`VoxelGI` 允许在运行时重烘焙，这是它相对 `LightmapGI` 最大的能力差异：

```gdscript
var voxel := VoxelGI.new()
voxel.size = Vector3(32, 8, 32)
voxel.subdiv = VoxelGI.SUBDIV_256
add_child(voxel)

# 场景发生变化后（例如玩家造了新建筑）重新烘焙
voxel.bake()
```

`VoxelGI.debug_bake()` 是给编辑器调试用的烘焙入口。

> ⚠️ **运行时烘焙会卡帧**。`VoxelGI.bake()` 是同步调用，烘焙期间主线程会停住。工程上的常见做法是：分摊到多帧、或者在玩家"进入一个区域"这种有加载动画的时机触发。

### 4.6 烘焙 vs 实时

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际开销取决于场景规模、光源数量与目标硬件，请在目标平台实测。

| 维度 | 烘焙 | 实时 |
|------|------|------|
| **性能** | 高 | 中 |
| **质量** | 高 | 中 |
| **动态** | ❌ | ✅ |
| **内存** | 高 | 低 |

这张表说的是"**烘焙过程** vs **运行时**"：烘焙是一次性的、可接受的高开销；运行时是每帧的、必须低开销。烘焙完的 LightmapGI 运行时开销是**最低**的一档。

---

## 五、体积雾与光照

### 5.1 Environment 的体积雾参数

体积雾与光照的关系，核心是 `Light3D.light_volumetric_fog_energy`——它把光源能量按比例转成雾中的散射。

| 属性 | 说明 |
|------|------|
| `Environment.volumetric_fog_enabled` | 总开关 |
| `Environment.volumetric_fog_density` | 雾的密度 |
| `Environment.volumetric_fog_albedo` | 雾的散射颜色 |
| `Environment.volumetric_fog_emission` / `volumetric_fog_emission_energy` | 雾的自发光 |
| `Environment.volumetric_fog_length` | 采样步进长度 |
| `Environment.volumetric_fog_detail_spread` | 细节噪声扩散 |
| `Environment.volumetric_fog_anisotropy` | 各向异性（越接近 1 越前向散射） |
| `Environment.volumetric_fog_ambient_inject` | 注入多少环境光 |
| `Environment.volumetric_fog_gi_inject` | 注入多少进 GI 缓冲 |
| `Environment.volumetric_fog_sky_affect` | 天空受雾影响的程度 |
| `Environment.volumetric_fog_temporal_reprojection_enabled` | 时间重投影 |
| `Environment.volumetric_fog_temporal_reprojection_amount` | 重投影混合量 |

### 5.2 FogVolume 节点

体积雾是"三维介质"，需要 `FogVolume` 节点告诉引擎"介质在哪里"：

| 属性 | 说明 |
|------|------|
| `FogVolume.material` | 雾体使用的材质 |
| `FogVolume.size` | 雾体作用范围 |

`FogVolume` 继承自 `VisualInstance3D`，因此它**在场景树里是一个会被视锥剔除的实例**。把它放在场景中心或玩家附近，是常规做法。

> ⚠️ **体积雾只在 Forward+ 渲染器上可用**。Mobile 与 Compatibility 渲染器都不支持它，需要用 `Environment.fog_enabled` 那一组深度雾参数代替。详见第 14 篇第 5.6 节。

### 5.3 灯在雾里的表现

`Light3D.light_volumetric_fog_energy` 是**乘数**：

| 调大 | 效果 |
|------|------|
| 接近 1.0 | 灯在雾里形成明显的光柱 |
| 调到 0 | 灯完全不参与体积雾散射 |

> 💡 **调雾里灯的亮度，别去动 `light_energy`**——那会把物体表面的照明一起改掉，看起来"整个场景都亮了"。正确做法是单独调 `light_volumetric_fog_energy`。

---

## 六、实战：把一个场景改成"烘焙 + 少量实时光"

### 6.1 决策流程

```
场景是静态的吗？
├─ 是 → LightmapGI（烘焙一次）
│        └─ 有动态物体吗？
│           ├─ 有 → 手工摆 LightmapProbe 覆盖动态区域
│           └─ 无 → 结束
└─ 否（运行时会有大改动）
   ├─ 桌面端 → SDFGI
   └─ 需要玩家建造 → VoxelGI + 运行时 bake()
```

### 6.2 改造步骤

以"静态室内关卡 + 一个会走的角色"为例：

| 步 | 做什么 | 对应属性 |
|----|--------|----------|
| 1 | 放 `LightmapGI` 节点 | — |
| 2 | 把所有静态网格标成静态 | `GeometryInstance3D.gi_mode = GI_MODE_STATIC` |
| 3 | 给网格生成 UV2 | 编辑器：网格 → 生成 UV2 |
| 4 | 把太阳与吊灯设为参与烘焙 | `Light3D.light_bake_mode = BAKE_STATIC` |
| 5 | 把角色的灯设为不参与 | `Light3D.light_bake_mode = BAKE_DISABLED` |
| 6 | 放 `LightmapProbe` 覆盖角色活动区 | — |
| 7 | 烘焙 | 编辑器：Bake Lightmap |
| 8 | 运行时检查 | `gi.light_data != null` |

```gdscript
func _ready() -> void:
    var gi: LightmapGI = $LightmapGI
    if gi.light_data == null:
        push_warning("LightmapGI 尚未烘焙：场景会缺少烘焙光照")
    for probe in get_tree().get_nodes_in_group("lightmap_probe"):
        pass
```

### 6.3 常见问题速查

| 现象 | 最可能的原因 |
|------|--------------|
| 改了 `light_energy` 但画面没变 | 这盏灯是 `BAKE_STATIC`，它的能量已经烘进光贴图了 |
| 改了 `Environment.ambient_light_color` 但烘焙没反应 | `LightmapGI.environment_mode` 不在 `ENVIRONMENT_MODE_SCENE` |
| 角色比周围暗一截 | 没放 `LightmapProbe`，或探针太稀 |
| 场景整体偏灰 | `bounce_indirect_energy` 太低，或 `ambient_light_energy` 太高 |
| 阴影边缘有条纹 | 调大 `shadow_bias`；或 `light_size` 为 0 导致阴影过硬 |
| 阴影整体悬空 | `shadow_normal_bias` 过大 |
| 远景阴影很糊 | 级联的必然结果；缩小 `directional_shadow_max_distance` |
| 灯一多阴影就变糊 | Shadow Atlas 不够用了 |
| 移动端没有 GI | 渲染器是 Mobile / Compatibility，不支持 SDFGI 与 SSIL |

---

## 📝 本章总结

光照这条线可以拆成三段来看：**直接光**（三盏实时光源 + 它们的阴影）、**间接光**（六条互不相同的 GI 路线）、以及**烘焙**（编辑器里那套只在 `LightmapGI` 上存在的流程）。

三段之间最重要的结构性事实是：**直接光几乎全是实时的，间接光则必须在"烘焙"与"实时"之间做选择**。`LightmapGI` 与 `VoxelGI` 是烘焙派（前者只能在编辑器烘，后者能在运行时烘），`SDFGI` 与 `SSIL` 是实时派（且只在 Forward+ 上可用），`LightmapProbe` 与 `ReflectionProbe` 则不产生间接光，只负责"取"。

---

## 核心要点

1. **实时光源只有三种**（`DirectionalLight3D` / `OmniLight3D` / `SpotLight3D`），全部继承 `Light3D`，公共属性在 `Light3D` 上，专属属性在各子类。
2. **平行光没有 `shadow_max_distance`**，只有 `directional_shadow_max_distance` 与三个 split；`shadow_orthogonal_size` 在 4.7.2 仍不存在。
3. **PSSM 级联**由 `directional_shadow_mode` 选 1 / 2 / 4 段；级联越多越清晰也越贵，远景阴影糊是级联的固有代价而非 bug。
4. **点光与聚光共用一张 Shadow Atlas**：图集越挤，阴影分辨率越低；`light_size` 决定半影宽度，`light_angular_distance` 决定角度张角。
5. **Godot 4.7.2 仍没有 VSM**，软阴影靠 `shadow_blur`（PCF）与 `light_size` / `light_angular_distance`（PCSS）共同完成。
6. **GI 有六条路线**：LightmapGI（烘焙）、VoxelGI（可运行时重烘焙）、LightmapProbe（只取光）、ReflectionProbe（反射）、SDFGI（实时，仅 Forward+）、SSIL（屏幕空间，仅 Forward+）。
7. **LightmapGI 的烘焙只在编辑器里**，`LightmapGI` 没有 `bake()` 方法、没有 `bake_mode`；质量枚举是 `BAKE_QUALITY_*`，开关在 `Light3D.light_bake_mode`，产物是 `LightmapGIData` 资源。
8. **`VoxelGI.bake()` 存在而 `LightmapGI.bake()` 不存在**——这是 4.3 里两个烘焙方案最关键的 API 差异。

---

## 🔗 延伸阅读

- **官方文档**: [3D 灯光与阴影](https://docs.godotengine.org/en/stable/tutorials/3d/lights_and_shadows.html)、[使用 Lightmap 全局光照](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/using_lightmap_gi.html)、[使用 VoxelGI](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/using_voxel_gi.html)
- **类参考**: [Light3D](https://docs.godotengine.org/en/stable/classes/class_light3d.html)、[DirectionalLight3D](https://docs.godotengine.org/en/stable/classes/class_directionallight3d.html)、[LightmapGI](https://docs.godotengine.org/en/stable/classes/class_lightmapgi.html)、[VoxelGI](https://docs.godotengine.org/en/stable/classes/class_voxelgi.html)、[LightmapProbe](https://docs.godotengine.org/en/stable/classes/class_lightmapprobe.html)、[ReflectionProbe](https://docs.godotengine.org/en/stable/classes/class_reflectionprobe.html)、[Environment](https://docs.godotengine.org/en/stable/classes/class_environment.html)
- **源码位置**: `scene/3d/lightmap_gi.h/.cpp`、`scene/3d/voxel_gibake.h`、`scene/register_scene_types.cpp`（五个 GI 类的注册）、`servers/rendering/renderer_rd/`（阴影贴图分配与渲染）

---

## 📋 下一章预告

**第 16 篇：材质系统**

- StandardMaterial3D 与 ShaderMaterial
- PBR 的真实计算流程：微表面反射 + 漫反射
- 材质共享与实例化
- Shader 编译链路：文本 → 变体 → SPIR-V → 管线缓存
- UBO 写法与 uniform 覆盖
- 用距离淡出 / 近处淡出 / 可见性范围做"材质 LOD"

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 14 篇：场景渲染流程](/articles/14-scene-rendering-flow.md)
**下一篇**: [第 16 篇：材质系统](/articles/16-material-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
