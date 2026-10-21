# 第 20 篇：粒子渲染

> **本章导读**：粒子是渲染系统里最容易「看起来很贵」的模块。本章把 Godot 4.x 的粒子拆成三层讲清楚：
> **节点层**（`GPUParticles2D` / `GPUParticles3D` / `CPUParticles2D` / `CPUParticles3D` 四个节点各自的职责与取舍）、
> **数据层**（`ParticleProcessMaterial` 过程材质的完整属性分组——发射形状、初速度、角速度、加速度、阻尼、曲线、缩放与颜色、湍流、碰撞、子发射器、粒子标志）、
> **渲染层**（`draw_pass_1..4`、`BILLBOARD_PARTICLES` 广告牌、粒子拖尾）。
> 读完你应该能独立回答三个问题：为什么 Compatibility 渲染器里 GPU 粒子不出画面；同一个特效该选 GPU 还是 CPU 粒子；
> 怎么用 `shader_type particles` 写自定义粒子着色器（`CUSTOM` / `COLOR` / `VELOCITY` / `MASS` / `ACTIVE` 等内置量）。
> **前置知识**：第 17 篇《GDShader 语言》、第 19 篇《后处理效果》。
> **难度**：进阶。

---

## 一、粒子系统架构

### 1.1 四种粒子节点

Godot 4.x 把粒子拆成了「维度 × 计算位置」两组维度，一共四个节点：

| 节点 | 维度 | 模拟计算发生在 | 适用场景 |
|------|------|----------------|----------|
| **GPUParticles2D** | 2D | GPU（compute shader） | 大量 2D 粒子、天气、弹幕、UI 装饰 |
| **GPUParticles3D** | 3D | GPU（compute shader） | 大量 3D 粒子：火焰、烟雾、魔法特效 |
| **CPUParticles2D** | 2D | CPU 主线程 | 粒子少、需要精确碰撞、必须跑在 Compatibility |
| **CPUParticles3D** | 3D | CPU 主线程 | 粒子少、需要与物理服务器真实碰撞、必须跑在 Compatibility |

> ⚠️ **重要区别（新手最常踩）**：`CPUParticles2D` / `CPUParticles3D` 把参数**摊平在节点自己身上**（`direction`、`spread`、`gravity`、`initial_velocity_min` 这些直接就是节点属性），**没有 `process_material` 属性**；
> 而 `GPUParticles2D` / `GPUParticles3D` 把参数放在 `process_material`（过程材质）里，节点自己只管数量、生命周期、时间与绘制通道。
> 把 CPU 粒子的写法搬到 GPU 粒子上，或者反过来，都会得到「属性不存在」的报错。

### 1.2 GPU 粒子与 CPU 粒子的分工与取舍

| 维度 | GPU 粒子 | CPU 粒子 |
|------|----------|----------|
| 模拟位置 | GPU 上的 compute shader，与渲染管线同一队列 | CPU 主线程 `_process`，逐粒子计算 |
| 粒子数量级 | 数万到数十万（受 `amount` 与显存限制） | 几百到几千，再多主线程就被吃满 |
| 每粒子成本 | 近似常数（与数量无关的固定开销 + 极小的每粒子开销） | 与数量线性相关 |
| 碰撞方式 | 4.3 在 `RenderingServer` 上注册了 `PARTICLES_COLLISION_TYPE_HEIGHTFIELD_COLLIDE` / `PARTICLES_COLLISION_TYPE_SDF_COLLIDE` / `PARTICLES_COLLISION_TYPE_SPHERE_COLLIDE` 等类型，走高度场 / SDF 近似 | 交给物理服务器，与真实 `CollisionShape3D` 求交 |
| 与物理服务器的交互 | 不参与（GPU 粒子不是刚体） | 参与，可触发 `body_entered` 一类信号 |
| 绘制方式 | 一次实例化绘制提交全部粒子（网格实例） | 每个粒子一个实例化绘制，但仍然合在一个提交里 |
| 后端限制 | **Compatibility 渲染器不支持** | 所有后端都支持 |

**选型口诀**：

- 粒子数量上千、且不需要真实物理碰撞 → **GPU 粒子**；
- 粒子数量只有几十上百、且需要撞到场景里的墙/角色/地面 → **CPU 粒子**；
- 项目要同时支持 Web / 老旧移动设备（只能跑 Compatibility） → **CPU 粒子**（GPU 粒子在那个后端下不出画面，见 1.4）。

### 1.3 粒子的一帧生命周期

```
GPUParticles3D（一帧）
    │
    ├─ 发射阶段：按 explosiveness / randomness / lifetime_randomness
    │            决定这一帧有多少粒子出生、初值落在哪个区间
    │
    ├─ 模拟阶段：过程材质（ParticleProcessMaterial）或粒子着色器
    │            推进位置 / 速度 / 旋转 / 缩放 / 颜色 / 寿命
    │
    ├─ 绘制阶段：按 draw_pass_1..4 把每个粒子实例化出来
    │            （广告牌、朝向、拖尾都在这一步定型）
    │
    └─ 回收阶段：寿命归零的粒子被回收，腾出的槽位给下一批新粒子
```

几个和时间相关的开关值得单独记住：

| 属性 | 含义 | 典型用法 |
|------|------|----------|
| `preprocess` | 预热秒数 | 让粒子在第一帧就已经铺开，避免「出场时是一坨」 |
| `fixed_fps` | 固定模拟帧率 | 模拟 30 帧、渲染 60 帧，省一半模拟开销 |
| `fract_delta` | 固定帧率时是否使用分数帧增量 | 配合 `fixed_fps` 做时间插值 |
| `interpolate` | 位置插值 | 固定模拟帧率下让运动看起来仍然平滑 |
| `interp_to_end` | 插值到寿命末尾 | 粒子即将消失前仍然连续 |
| `speed_scale` | 时间缩放 | 慢动作 / 快进特效 |
| `one_shot` + `explosiveness` | 一次性爆发 | 爆炸、冲击波 |

### 1.4 Compatibility 渲染器下 GPU 粒子不可用（硬限制）

这是 4.x 最容易被忽略的兼容性断点：

- Forward+ 与 Mobile 渲染器基于 Vulkan / D3D12，**有 compute shader**，GPU 粒子的模拟就跑在 compute 上；
- Compatibility 渲染器（OpenGL 3.3 / GLES3）**没有 compute shader**，因此 `GPUParticles2D` / `GPUParticles3D` 在这个后端下**不会渲染出任何粒子**；
- 官方类参考在 `GPUParticles3D` 的描述里也写明了这一点：GPU 粒子节点在 Compatibility 后端不可用。

**降级策略（按推荐顺序）**：

1. 在项目设置里固定渲染后端（`rendering/renderer/rendering_method`），确保目标平台不会意外落到 Compatibility；
2. 如果必须同时支持 Compatibility，用 `RenderingServer.get_video_adapter_name()` 之类的信息做不了可靠判断——**正确做法是让美术/策划在两种后端下各验收一次**；
3. 必须双端兼容时，把关键特效做成 `CPUParticles3D`，或者准备一份「简化版」特效资源按后端切换。

> 📌 **注意**：这不是「性能差」，是「完全不显示」。调试时先确认渲染后端，再怀疑粒子参数。

### 1.5 粒子活在哪个坐标系里

粒子系统最容易出的第二个问题是「粒子跟着我走 / 粒子不跟着我走」，这由三个属性共同决定：

| 属性 | 作用 | 典型取值 |
|------|------|----------|
| `local_coords` | 粒子出生后是否继续使用发射器的局部坐标 | `true` = 跟着发射器走（弹道类特效）；`false` = 留在世界空间（火雨、烟花） |
| `transform_align` | 粒子网格如何对齐 | `TRANSFORM_ALIGN_DISABLED` / `TRANSFORM_ALIGN_Z_BILLBOARD` / `TRANSFORM_ALIGN_Y_TO_VELOCITY` / `TRANSFORM_ALIGN_Z_BILLBOARD_Y_TO_VELOCITY` |
| `emission_shape_offset` | 发射点相对节点的偏移 | 做「炮口在枪管末端」时用它 |

**两组常用组合**：

| 想要的效果 | `local_coords` | `transform_align` | 原因 |
|------------|----------------|-------------------|------|
| 跟随角色的能量光环 | `true` | `TRANSFORM_ALIGN_Z_BILLBOARD` | 光环要跟着人动，面片要朝屏幕 |
| 抛物线飞行的箭矢 | `true` | `TRANSFORM_ALIGN_Y_TO_VELOCITY` | 箭要跟着速度方向，且要跟着发射者 |
| 从空中落下的雨滴 | `false` | `TRANSFORM_ALIGN_Z_BILLBOARD` | 雨滴属于世界，不该被雨云带着跑 |
| 世界空间里的烟花 | `false` | `TRANSFORM_ALIGN_DISABLED` | 烟花有自己的旋转逻辑 |

> 📌 `transform_align` 的默认值是 `TRANSFORM_ALIGN_DISABLED`——**不设它的话，粒子网格会保持网格自身的朝向**，
> 拿一个面片当粒子就会看到「面片侧对镜头」的现象。面片类粒子几乎总要设成 `TRANSFORM_ALIGN_Z_BILLBOARD`。

---

## 二、粒子发射器与过程材质

### 2.1 GPUParticles3D 的节点级属性

`GPUParticles3D` 继承自 `GeometryInstance3D`，节点自己的属性可以按用途分成五组：

| 分组 | 属性 | 说明 |
|------|------|------|
| **数量** | `amount` | 同时存在的粒子数上限 |
| | `amount_ratio` | 实际生效比例（0~1），配合距离/可见性做「远处的粒子少一点」 |
| **寿命与节奏** | `lifetime` | 单个粒子存活秒数 |
| | `one_shot` | 一次性发射（爆发） |
| | `explosiveness` | 爆发度：0 表示均匀发射，1 表示全部挤在第一帧 |
| | `randomness` | 发射时刻的随机抖动比例（0~1） |
| | `lifetime_randomness` | 粒子寿命的随机比例（0~1），写在过程材质上 |
| | `speed_scale` | 时间缩放 |
| | `fixed_fps` / `fract_delta` / `interpolate` / `interp_to_end` | 固定模拟帧率与插值 |
| | `preprocess` | 预热秒数 |
| **空间** | `local_coords` | 粒子是否跟随发射器移动（关掉 = 发射后留在世界空间） |
| | `visibility_aabb` | 用于视锥剔除的包围盒 |
| | `transform_align` | 粒子朝向策略（`TRANSFORM_ALIGN_DISABLED` / `TRANSFORM_ALIGN_Z_BILLBOARD` / `TRANSFORM_ALIGN_Y_TO_VELOCITY` / `TRANSFORM_ALIGN_Z_BILLBOARD_Y_TO_VELOCITY`） |
| | `draw_order` | 绘制顺序（`DRAW_ORDER_INDEX` / `DRAW_ORDER_LIFETIME` / `DRAW_ORDER_REVERSE_LIFETIME` / `DRAW_ORDER_VIEW_DEPTH`） |
| **绘制** | `draw_pass_1` ~ `draw_pass_4` | 最多 4 个绘制通道，每个通道一个 `Mesh` |
| | `draw_passes` | 实际启用的通道数（1~4） |
| | `draw_skin` | 给粒子绘制蒙皮网格用的 `Skin` |
| **开关** | `emitting` | 是否正在发射 |
| | `trail_enabled` / `trail_lifetime` | 粒子拖尾（4.3 新增） |
| | `sub_emitter` | 子发射器目标（`NodePath`） |
| | `process_material` | 过程材质（`Material` 类型） |

一个最小可用的 GPU 粒子节点：

```gdscript
var emitter := GPUParticles3D.new()
emitter.amount = 512
emitter.lifetime = 1.5
emitter.one_shot = false
emitter.explosiveness = 0.0
emitter.local_coords = false
emitter.draw_pass_1 = quad_mesh
emitter.draw_passes = 1
emitter.process_material = process_material
```

### 2.2 发射形状：属性属于 `ParticleProcessMaterial`

```gdscript
# 发射形状是 ParticleProcessMaterial 的属性，不是 GPUParticles3D 的
var process_material := ParticleProcessMaterial.new()

# 点发射器
process_material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_POINT

# 球体发射器
process_material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
process_material.emission_sphere_radius = 1.0

# 盒状发射器
process_material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
process_material.emission_box_extents = Vector3(1, 1, 1)

# 挂到发射器上
var emitter := GPUParticles3D.new()
emitter.process_material = process_material
```

> `GPUParticles3D` 的成员表里**没有** `emission_shape`、`emission_sphere_radius`、`emission_box_extents`——这三个都是 `ParticleProcessMaterial` 的属性，常量前缀也必须是 `ParticleProcessMaterial.EMISSION_SHAPE_*`。

4.3 的 `ParticleProcessMaterial.EmissionShape` 枚举一共有 7 个可用形状（外加一个 `EMISSION_SHAPE_MAX` 哨兵）：

| 枚举值 | 形状 | 配套属性 |
|--------|------|----------|
| `EMISSION_SHAPE_POINT` | 单点 | — |
| `EMISSION_SHAPE_SPHERE` | 实心球体内随机 | `emission_sphere_radius` |
| `EMISSION_SHAPE_SPHERE_SURFACE` | 球面壳层随机 | `emission_sphere_radius` |
| `EMISSION_SHAPE_BOX` | 立方体内随机 | `emission_box_extents` |
| `EMISSION_SHAPE_POINTS` | 从一张点云贴图取点 | `emission_point_count`、`emission_point_texture` |
| `EMISSION_SHAPE_DIRECTED_POINTS` | 点云 + 每点的发射方向 | `emission_point_count`、`emission_point_texture`、`emission_normal_texture` |
| `EMISSION_SHAPE_RING` | 圆环 | `emission_ring_axis`、`emission_ring_radius`、`emission_ring_inner_radius`、`emission_ring_height` |

还有三个通用修饰参数：

| 属性 | 说明 |
|------|------|
| `emission_shape_offset` | 发射形状相对节点原点的偏移（做「枪口偏移」很好用） |
| `emission_shape_scale` | 发射形状的缩放（比逐个改半径方便） |
| `flatness` | 把球压扁成圆盘的比例（0~1），配合 `EMISSION_SHAPE_SPHERE` 做「扁平的烟」 |

### 2.3 过程材质 `ParticleProcessMaterial` 属性全表（按功能分组）

过程材质继承自 `Material`，它是「一份参数模板」——多个粒子节点可以共用同一个过程材质实例。

#### （1）发射形状组

| 属性 | 类型 | 说明 |
|------|------|------|
| `emission_shape` | int | 发射形状枚举（`EMISSION_SHAPE_*`） |
| `emission_sphere_radius` | float | 球 / 球面半径 |
| `emission_box_extents` | Vector3 | 盒形状的半尺寸 |
| `emission_ring_axis` | Vector3 | 圆环法线方向 |
| `emission_ring_radius` | float | 圆环外半径 |
| `emission_ring_inner_radius` | float | 圆环内半径 |
| `emission_ring_height` | float | 圆环厚度 |
| `emission_point_count` | int | 点云贴图里取的点数 |
| `emission_point_texture` | Texture2D | 点云贴图（红通道存坐标） |
| `emission_normal_texture` | Texture2D | 每点法线（`EMISSION_SHAPE_DIRECTED_POINTS` 用） |
| `emission_shape_offset` | Vector3 | 形状偏移 |
| `emission_shape_scale` | Vector3 | 形状缩放 |
| `flatness` | float | 压扁比例 |

#### （2）初始运动组

| 属性 | 类型 | 说明 |
|------|------|------|
| `direction` | Vector3 | 发射方向 |
| `spread` | float | 相对 `direction` 的扩散角（度） |
| `initial_velocity_min` / `initial_velocity_max` | float | 初速度区间 |
| `angular_velocity_min` / `angular_velocity_max` | float | 角速度区间（度/秒） |
| `angle_min` / `angle_max` | float | 初始旋转角区间 |
| `orbit_velocity_min` / `orbit_velocity_max` | float | 绕发射器轴的公转速度 |
| `linear_accel_min` / `linear_accel_max` | float | 线性加速度区间 |
| `radial_accel_min` / `radial_accel_max` | float | 径向加速度区间 |
| `tangential_accel_min` / `tangential_accel_max` | float | 切向加速度区间 |
| `directional_velocity_min` / `directional_velocity_max` | float | 沿 `direction` 的额外速度 |
| `radial_velocity_min` / `radial_velocity_max` | float | 径向额外速度 |
| `gravity` | Vector3 | 重力向量（注意是 **Vector3**，不是标量） |
| `damping_min` / `damping_max` | float | 阻尼区间 |
| `velocity_pivot` | Vector3 | 速度旋转轴（做「螺旋」用） |
| `inherit_velocity_ratio` | float | 继承发射器自身速度的比例 |
| `scale_over_velocity_min` / `scale_over_velocity_max` | float | 按速度缩放的系数 |

#### （3）缩放、颜色与动画组

| 属性 | 类型 | 说明 |
|------|------|------|
| `scale_min` / `scale_max` | float | 初始缩放区间 |
| `color` | Color | 初始颜色 |
| `color_ramp` | Texture2D | 生命周期的颜色渐变（用 `GradientTexture1D`） |
| `color_initial_ramp` | Texture2D | 出生时的随机颜色渐变 |
| `hue_variation_min` / `hue_variation_max` | float | 色相随机范围 |
| `anim_speed_min` / `anim_speed_max` | float | 贴图动画播放速度区间 |
| `anim_offset_min` / `anim_offset_max` | float | 贴图动画起始帧偏移区间 |
| `lifetime_randomness` | float | 寿命随机比例 |

#### （4）曲线组

所有曲线类属性的类型都是 `Texture2D`，实际使用时接一个 `CurveTexture`（内部挂 `Curve`）：

| 属性 | 驱动的量 |
|------|----------|
| `scale_curve` | 缩放 |
| `alpha_curve` | 透明度 |
| `angle_curve` | 旋转角 |
| `angular_velocity_curve` | 角速度 |
| `damping_curve` | 阻尼 |
| `linear_accel_curve` | 线性加速度 |
| `orbit_velocity_curve` | 公转速度 |
| `radial_accel_curve` | 径向加速度 |
| `tangential_accel_curve` | 切向加速度 |
| `scale_over_velocity_curve` | 速度缩放系数 |
| `directional_velocity_curve` | 方向速度 |
| `radial_velocity_curve` | 径向速度 |
| `velocity_limit_curve` | 生命期内的速度上限曲线（按 lifetime 取值，钳制最终速度的模长） |
| `hue_variation_curve` | 色相变化 |
| `anim_speed_curve` / `anim_offset_curve` | 贴图动画速度 / 偏移 |
| `turbulence_influence_over_life` | 湍流影响力随生命变化 |
| `emission_curve` | 颜色随生命周期的渐变曲线（CurveTexture，乘在 COLOR 上；仅 unshaded 材质可见） |

#### （5）湍流组

| 属性 | 类型 | 说明 |
|------|------|------|
| `turbulence_enabled` | bool | 是否开启湍流 |
| `turbulence_noise_strength` | float | 噪声强度 |
| `turbulence_noise_scale` | float | 噪声缩放（越大越细碎） |
| `turbulence_noise_speed` | Vector3 | 噪声在三个轴上的流动速度 |
| `turbulence_noise_speed_random` | float | 速度随机比例 |
| `turbulence_initial_displacement_min` / `max` | float | 出生时的随机位移 |
| `turbulence_influence_min` / `max` | float | 湍流影响力度区间 |

#### （6）碰撞组

| 属性 | 类型 | 说明 |
|------|------|------|
| `collision_mode` | int | `COLLISION_DISABLED` / `COLLISION_RIGID` / `COLLISION_HIDE_ON_CONTACT` |
| `collision_bounce` | float | 反弹系数 |
| `collision_friction` | float | 摩擦系数 |
| `collision_use_scale` | bool | 碰撞是否考虑粒子缩放（配合 `GPUParticles3D.collision_base_size`） |

#### （7）子发射器组

| 属性 | 类型 | 说明 |
|------|------|------|
| `sub_emitter_mode` | int | `SUB_EMITTER_DISABLED` / `SUB_EMITTER_CONSTANT` / `SUB_EMITTER_AT_END` / `SUB_EMITTER_AT_COLLISION` |
| `sub_emitter_amount_at_end` | int | 粒子消亡时派生的粒子数 |
| `sub_emitter_amount_at_collision` | int | 碰撞时派生的粒子数 |
| `sub_emitter_frequency` | float | 常量模式下的派生频率 |
| `sub_emitter_keep_velocity` | bool | 子粒子是否继承父粒子速度 |

#### （8）粒子标志组

| 属性 | 对应枚举 | 含义 |
|------|----------|------|
| `particle_flag_align_y` | `PARTICLE_FLAG_ALIGN_Y_TO_VELOCITY` | 让粒子的 Y 轴对齐速度方向 |
| `particle_flag_rotate_y` | `PARTICLE_FLAG_ROTATE_Y` | 只绕 Y 轴旋转 |
| `particle_flag_disable_z` | `PARTICLE_FLAG_DISABLE_Z` | 锁死 Z 轴（2D 风格粒子常用） |
| `particle_flag_damping_as_friction` | `PARTICLE_FLAG_DAMPING_AS_FRICTION` | 把阻尼当作摩擦而不是衰减 |

> 📌 `ParticleProcessMaterial.set_particle_flag()` / `get_particle_flag()` 提供按枚举开关的写法：
> `process_material.set_particle_flag(ParticleProcessMaterial.PARTICLE_FLAG_ROTATE_Y, true)`。
> 与之对应，`ParticleProcessMaterial.PARTICLE_FLAG_ROTATE_Y` 这一组是**过程材质上的枚举**，不是 `GPUParticles3D` 上的。

### 2.4 曲线控制：曲线、曲线贴图与渐变贴图

过程材质里的曲线槽位类型都是 `Texture2D`，所以有三件套：

| 资源 | 作用 |
|------|------|
| `Curve` | 真正的曲线数据（关键帧、切线） |
| `CurveTexture` | 把 `Curve` 包装成一张 `Texture2D`，好让过程材质引用 |
| `Gradient` + `GradientTexture1D` | 颜色渐变，包装成 `Texture2D` 给 `color_ramp` / `color_initial_ramp` |

构造一条「先快后慢」的缩放曲线：

```gdscript
# 1) 造 Curve
var scale_curve := Curve.new()
scale_curve.min_value = 0.0
scale_curve.max_value = 2.0
scale_curve.add_point(Vector2(0.0, 0.0))          # 出生时缩放为 0
scale_curve.add_point(Vector2(0.2, 1.0), 0.0, 0.0) # 20% 寿命时长到最大
scale_curve.add_point(Vector2(1.0, 0.0), 0.0, 0.0) # 死亡时缩回 0

# 2) 包装成 CurveTexture
var curve_texture := CurveTexture.new()
curve_texture.curve = scale_curve
curve_texture.width = 64

# 3) 挂到过程材质上
var process_material := ParticleProcessMaterial.new()
process_material.scale_curve = curve_texture
```

> `Curve` 的 `min_value` / `max_value` 是**取值钳制范围**，不是曲线的 X 范围；X 方向（生命时间 0~1）由曲线自身的关键帧位置决定。
> `Curve.set_point_left_mode()` / `set_point_right_mode()` 控制切线是自由还是直线（`Curve.TANGENT_FREE` / `Curve.TANGENT_LINEAR`）。

颜色渐变同理：

```gdscript
var gradient := Gradient.new()
gradient.set_color(0, Color(1.0, 0.8, 0.2, 1.0))   # 出生：亮黄
gradient.set_color(1, Color(0.2, 0.2, 0.2, 0.0))   # 死亡：暗且透明

var gradient_texture := GradientTexture1D.new()
gradient_texture.gradient = gradient
gradient_texture.width = 64

var process_material := ParticleProcessMaterial.new()
process_material.color_ramp = gradient_texture
```

> ⚠️ `color_ramp` 的渐变是**线性空间**的插值，`Gradient.interpolation_color_space` 决定插值空间（`GRADIENT_COLOR_SPACE_LINEAR` / `GRADIENT_COLOR_SPACE_SRGB` / `GRADIENT_COLOR_SPACE_OKLAB`）。
> 想让「先亮后暗」的观感更接近直觉，通常选 `GRADIENT_COLOR_SPACE_SRGB`。

### 2.5 缩放与颜色：三套机制别搞混

| 想要的效果 | 用哪个属性 |
|------------|------------|
| 每个粒子出生时大小随机 | `scale_min` / `scale_max` |
| 粒子随生命时间变大变小 | `scale_curve`（接 `CurveTexture`） |
| 粒子跑得越快越大 | `scale_over_velocity_min` / `scale_over_velocity_max` + `scale_over_velocity_curve` |
| 每个粒子出生时颜色随机 | `color_initial_ramp`（接 `GradientTexture1D`） |
| 粒子随生命时间变色 / 淡出 | `color_ramp`（接 `GradientTexture1D`）+ `alpha_curve` |
| 粒子之间色相微差 | `hue_variation_min` / `hue_variation_max` |

> 💡 常见坑：`scale_min` / `scale_max` 是**倍率**，不是尺寸。网格本身 1 米大、`scale_max = 2.0`，粒子最大就是 2 米。
> 另外 `color` 里的 alpha 乘上 `color_ramp` 里的 alpha 才是最终 alpha。

### 2.6 子发射器

「粒子生粒子」用子发射器实现，两个东西缺一不可：

1. **父粒子**：`GPUParticles3D.sub_emitter` 指向一个 `NodePath`，目标是另一个粒子节点；
2. **父粒子的过程材质**：`sub_emitter_mode` 决定什么时候派生。

| 模式 | 行为 | 配套属性 |
|------|------|----------|
| `SUB_EMITTER_DISABLED` | 不派生 | — |
| `SUB_EMITTER_CONSTANT` | 按频率持续派生 | `sub_emitter_frequency` |
| `SUB_EMITTER_AT_END` | 粒子寿命结束时派生 | `sub_emitter_amount_at_end` |
| `SUB_EMITTER_AT_COLLISION` | 粒子碰撞时派生 | `sub_emitter_amount_at_collision` |

```gdscript
var parent_emitter := GPUParticles3D.new()
parent_emitter.sub_emitter = NodePath("../Sparks")
```

> ⚠️ 4.3 的 `GPUParticles3D` 上**只有 `sub_emitter` 这一个 `NodePath` 属性**（指向「子发射器节点」），
> `sub_emitter_node_paths` 并不存在——那是 Godot 3.x 的写法。别把 3.x 的属性名带进来。

### 2.7 碰撞与遮挡

**GPU 粒子的碰撞**（过程材质侧）：

```gdscript
var process_material := ParticleProcessMaterial.new()
process_material.collision_mode = ParticleProcessMaterial.COLLISION_RIGID
process_material.collision_bounce = 0.4
process_material.collision_friction = 0.2
```

> ⚠️ `COLLISION_DISABLED` / `COLLISION_RIGID` / `COLLISION_HIDE_ON_CONTACT` 是 **`ParticleProcessMaterial` 上的常量**，
> `GPUParticles3D` 的成员表里没有它们。写 `GPUParticles3D.COLLISION_HIDE_ON_CONTACT` 会直接报「无此成员」。

4.3 的 GPU 粒子碰撞走的是高度场 / SDF 近似，碰撞体大小由 `GPUParticles3D.collision_base_size` 决定；
`RenderingServer` 上注册了对应的粒子碰撞类型常量（`PARTICLES_COLLISION_TYPE_HEIGHTFIELD_COLLIDE`、
`PARTICLES_COLLISION_TYPE_SDF_COLLIDE`、`PARTICLES_COLLISION_TYPE_SPHERE_COLLIDE`、
`PARTICLES_COLLISION_TYPE_BOX_COLLIDE` 等）。

**CPU 粒子的碰撞**：走物理服务器，需要场景里有真实的碰撞体（`StaticBody3D` + `CollisionShape3D`），
CPU 粒子自身用 `CPUParticles3D.mesh` 指定要绘制的网格。

**遮挡与剔除**：

| 属性 | 作用 |
|------|------|
| `GPUParticles3D.visibility_aabb` | 粒子系统的包围盒；填一个固定值比让引擎每帧重算更省 CPU |
| `GeometryInstance3D.visibility_range_begin` / `visibility_range_end` | 距离剔除（详见第 21 篇） |
| `GeometryInstance3D.ignore_occlusion_culling` | 不参与遮挡剔除 |
| `GPUParticles3D.amount_ratio` | 远处把粒子数量按比例降下来，比整个关掉更自然 |

### 2.8 CPU 粒子的参数是摊平的

`CPUParticles3D` 没有过程材质，参数直接写在节点上，命名与过程材质一致但少了「过程」二字：

| 过程材质 | CPUParticles3D |
|----------|----------------|
| `initial_velocity_min` / `max` | `initial_velocity_min` / `max` |
| `angular_velocity_min` / `max` | `angular_velocity_min` / `max` |
| `gravity` | `gravity`（Vector3） |
| `damping_min` / `max` | `damping_min` / `max` |
| `scale_min` / `max` | `scale_amount_min` / `max` |
| `scale_curve` | `scale_curve_x` / `scale_curve_y` / `scale_curve_z`（三条独立曲线） |
| `color_ramp` | `color_ramp`（`Texture2D`） |
| `emission_shape` 等 | 同名 |

> 📌 `CPUParticles3D` 的缩放曲线是 **X / Y / Z 三条独立曲线**，而过程材质只有一条 `scale_curve`——
> 这是两者最容易混的地方之一。

### 2.9 搭一个完整的三层特效（可直接跑）

下面这段脚本把「主火焰 + 火星 + 地面烟尘」三层粒子一次性搭出来，覆盖本章讲到的绝大多数属性：

```gdscript
# 火焰 + 火星 + 烟尘，三层粒子
var root := Node3D.new()

# ---------- 第 1 层：主火焰 ----------
var fire := GPUParticles3D.new()
fire.amount = 128
fire.lifetime = 0.8
fire.draw_passes = 1
fire.local_coords = false
fire.transform_align = GPUParticles3D.TRANSFORM_ALIGN_Z_BILLBOARD

var fire_quad := QuadMesh.new()
fire_quad.size = Vector2(0.4, 0.6)

var fire_mat := StandardMaterial3D.new()
fire_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
fire_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
fire_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
fire_mat.vertex_color_use_as_albedo = true
fire_mat.albedo_texture = load("res://fx/fire.png")
fire_quad.material = fire_mat
fire.draw_pass_1 = fire_quad

var fire_process := ParticleProcessMaterial.new()
fire_process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
fire_process.emission_sphere_radius = 0.2
fire_process.direction = Vector3(0, 1, 0)
fire_process.spread = 15.0
fire_process.initial_velocity_min = 1.0
fire_process.initial_velocity_max = 2.0
fire_process.gravity = Vector3(0, 1.5, 0)
fire_process.scale_min = 0.6
fire_process.scale_max = 1.2
fire_process.color = Color(1.0, 0.6, 0.2, 1.0)
fire.process_material = fire_process
root.add_child(fire)

# ---------- 第 2 层：火星（火星的子发射器来自火焰） ----------
var sparks := GPUParticles3D.new()
sparks.amount = 64
sparks.lifetime = 1.4
sparks.draw_passes = 1
sparks.local_coords = false
sparks.sub_emitter = NodePath("../Sparks")

var spark_process := ParticleProcessMaterial.new()
spark_process.sub_emitter_mode = ParticleProcessMaterial.SUB_EMITTER_AT_END
spark_process.sub_emitter_amount_at_end = 4
spark_process.gravity = Vector3(0, -6.0, 0)
spark_process.collision_mode = ParticleProcessMaterial.COLLISION_RIGID
sparks.process_material = spark_process
root.add_child(sparks)

# ---------- 第 3 层：烟尘 ----------
var smoke := GPUParticles3D.new()
smoke.amount = 32
smoke.lifetime = 2.5
smoke.draw_passes = 1
smoke.local_coords = false

var smoke_process := ParticleProcessMaterial.new()
smoke_process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
smoke_process.emission_sphere_radius = 0.35
smoke_process.direction = Vector3(0, 1, 0)
smoke_process.spread = 30.0
smoke_process.initial_velocity_min = 0.4
smoke_process.initial_velocity_max = 0.9
smoke_process.gravity = Vector3(0, 0.4, 0)
smoke_process.damping_min = 0.6
smoke_process.damping_max = 1.2
smoke_process.scale_min = 0.8
smoke_process.scale_max = 1.4
smoke.process_material = smoke_process
root.add_child(smoke)
```

> ⚠️ 脚本里 `sub_emitter` 写的是一个 `NodePath` 字符串（如 `"../Sparks"`），**必须与场景树里的实际节点路径一致**；
> 纯代码运行时（没有 `.tscn` 场景）这个路径是无效的，子发射器不会触发。
> 这也是为什么编辑器里做子发射器更省事：直接在检查器里拖节点引用。

> ⚠️ 加色混合（`BLEND_MODE_ADD`）的粒子**不需要**写 alpha 渐变，加色模式下 alpha 直接决定加上去的强度；
> 普通混合（`BLEND_MODE_MIX`）才需要用 `color_ramp` 做淡出。

---

## 三、粒子着色器：`shader_type particles`

### 3.1 过程材质与粒子着色器的分工

| 需求 | 用什么 |
|------|--------|
| 「粒子往上飘、越飘越慢、慢慢变大变淡」 | `ParticleProcessMaterial`（用曲线和区间参数就够了） |
| 「粒子按噪声场运动」「粒子颜色由自己的逻辑决定」「粒子之间互相影响」 | `shader_type particles` 自定义着色器 |
| 「粒子数量少、但每颗粒子的行为很特殊」 | `shader_type particles` |

两者的关系是：**过程材质负责基础运动，粒子着色器负责覆盖或补充**。
一个 `GPUParticles3D` 的 `process_material` 可以是 `ParticleProcessMaterial`，也可以是挂了 `particles` 着色器的 `ShaderMaterial`。

### 3.2 两个入口函数：`start()` 与 `process()`

```glsl
shader_type particles;

// 粒子出生时被调用一次
void start() {
    // 在这里写 COLOR / VELOCITY / ROTATION / POSITION / CUSTOM / MASS
    // 表示「这个粒子出生时的初始状态」
}

// 粒子存活的每一帧被调用
void process() {
    // DELTA：距上一帧的时间
    // LIFETIME：剩余寿命
    // 在这里读 COLOR / VELOCITY / ... 并写回
}
```

> ⚠️ `particles` 着色器**没有 fragment 函数**，也没有 spatial 着色器里的 `ALBEDO` / `NORMAL` / `ROUGHNESS` 那套输出。
> 粒子着色器只负责**模拟与变换**，真正的着色仍然由绘制通道上的材质（`StandardMaterial3D` 或另一个 `ShaderMaterial`）完成。

### 3.3 4.3 的粒子着色器内置量

| 内置量 | 类型 | 含义 |
|--------|------|------|
| `EMISSION_TRANSFORM` | mat4 | 发射器的变换矩阵（把发射器局部空间换算到世界空间用） |
| `POSITION` | vec3 | 粒子位置（`process()` 里可写） |
| `VELOCITY` | vec3 | 粒子速度（`process()` 里可写） |
| `ROTATION` | vec3 | 粒子旋转角（`process()` 里可写） |
| `COLOR` | vec4 | 粒子颜色（含 alpha） |
| `CUSTOM` | vec4 | 自定义数据，**不参与渲染**，纯给逻辑用 |
| `MASS` | float | 粒子质量 |
| `ACTIVE` | bool | 粒子是否存活；在 `process()` 里写 `ACTIVE = false` 立刻回收该粒子 |
| `LIFETIME` | float | 剩余寿命 |
| `DELTA` | float | 距上一帧的时间增量 |
> ⚠️ `FLAG_DISABLE_Z` / `FLAG_ROTATE_Y` / `FLAG_ALIGN_Y` **不是粒子着色器内置量**——4.7.2 的 `particles` 着色器里没有它们（`servers/rendering/shader_types.cpp:393-397`、`:398-400` 只有 `FLAG_EMIT_*` 与 `RESTART_*`）。
>
> 它们是 `ParticleProcessMaterial` 上的**过程材质属性**：`particle_flag_disable_z` / `particle_flag_rotate_y` / `particle_flag_align_y`，对应枚举 `ParticleProcessMaterial.PARTICLE_FLAG_DISABLE_Z` / `_ROTATE_Y` / `_ALIGN_Y_TO_VELOCITY`——见本章过程材质一节。

配套的 `GPUParticles3D` 侧常量（4.7.2 的类常量，描述 `start()` 里哪些输出会被写回粒子状态）：

| 常量 | 含义 |
|------|------|
| `EMIT_FLAG_POSITION` | `POSITION` 的输出生效 |
| `EMIT_FLAG_ROTATION_SCALE` | `ROTATION` 的输出生效 |
| `EMIT_FLAG_VELOCITY` | `VELOCITY` 的输出生效 |
| `EMIT_FLAG_COLOR` | `COLOR` 的输出生效 |
| `EMIT_FLAG_CUSTOM` | `CUSTOM` 的输出生效 |

> 📌 4.3 里这些 `EMIT_FLAG_*` 是 **`GPUParticles3D` 的类常量**，脚本里没有对应的可写属性；
> 实际控制初始状态的做法是在 `start()` 里直接写 `POSITION` / `VELOCITY` / `COLOR` / `CUSTOM`。

### 3.4 一个完整例子：带噪声漂移的火花

```glsl
shader_type particles;

uniform float drift_strength = 2.0;
uniform float spin_speed = 3.0;
uniform bool use_custom_seed = true;

void start() {
    // 每个粒子出生时的初始状态
    CUSTOM = vec4(use_custom_seed ? randf() : 0.0, 0.0, 0.0, 0.0);
    VELOCITY = vec3(0.0, 1.0, 0.0);
    MASS = 0.05;
    COLOR = vec4(1.0, 0.8, 0.3, 1.0);
}

void process() {
    // 用 CUSTOM 累加「本颗粒子已经活了多久」——CUSTOM 是粒子着色器里
    // 唯一能跨帧保存的自定义通道
    CUSTOM.y += DELTA;

    // 存活时间归一化：1 表示刚出生，0 表示即将消失
    float life = clamp(LIFETIME, 0.0, 1.0);

    // 用 CUSTOM 里存的随机种子做一个廉价的伪随机漂移
    float t = CUSTOM.x * 6.2831853 + CUSTOM.y;
    vec3 drift = vec3(sin(t), cos(t * 1.3), sin(t * 0.7));

    VELOCITY += drift * drift_strength * DELTA;
    VELOCITY.y -= 9.8 * DELTA;          // 手写重力
    POSITION += VELOCITY * DELTA;

    // 旋转
    ROTATION += vec3(0.0, spin_speed * DELTA, 0.0);

    // 越老越暗、越老越透明
    COLOR = vec4(COLOR.rgb * life, COLOR.a * life);
}
```

对应的材质与节点：

```gdscript
var shader := Shader.new()
shader.code = """
shader_type particles;
...
"""

var shader_material := ShaderMaterial.new()
shader_material.shader = shader

var emitter := GPUParticles3D.new()
emitter.amount = 256
emitter.lifetime = 1.2
emitter.process_material = shader_material
```

> ⚠️ 粒子着色器只在 **Forward+ / Mobile** 后端有效；Compatibility 后端本来就不跑 GPU 粒子，这条限制是叠加的。
> 另外 `LIFETIME` 是「本颗粒子的剩余寿命」、`DELTA` 是「距上一帧的时间增量」——单位一样但含义不同，最容易在这里写错。
> 需要「系统启动以来的时间」这类全局量时，用 `CUSTOM` 自己累加（见 3.4 的例子），不要凭印象套用别的着色器的内置量。

### 3.5 `CUSTOM` 的用法：`CUSTOM` 是唯一的「用户数据通道」

`CUSTOM` 是 vec4，**不参与渲染**，专门用来在 `start()` 和 `process()` 之间传递自定义状态：

```glsl
void start() {
    CUSTOM = vec4(randf(), randf(), randf(), 1.0);   // 前三个分量当随机种子
}

void process() {
    // 用 CUSTOM 保存「这个粒子已经跳了几次」
    float hops = CUSTOM.w;
    if (hops < 3.0 && POSITION.y < 0.0) {
        POSITION.y = 0.0;
        VELOCITY.y = abs(VELOCITY.y) * 0.7;   // 弹一下
        CUSTOM.w = hops + 1.0;                // 记账
    }
}
```

> 💡 `CUSTOM` 在 `start()` 里写、在 `process()` 里读，值会跨帧保留；
> 而 `COLOR` / `VELOCITY` 在 `process()` 里是「读到什么就是什么」，不会自动保留上一帧的写入结果以外的语义，
> 需要自己把需要跨帧的数据写进 `CUSTOM`。

### 3.6 粒子着色器不支持什么

| 想做的事 | 能不能在 `particles` 着色器里做 |
|----------|-----------------------------------|
| 改粒子的颜色 | ✅ 写 `COLOR` |
| 改粒子的位置 / 速度 / 旋转 | ✅ 写 `POSITION` / `VELOCITY` / `ROTATION` |
| 提前回收粒子 | ✅ 写 `ACTIVE = false` |
| 改粒子最终长什么样（金属度、粗糙度、法线） | ❌ 要去绘制通道的材质上做 |
| 写 fragment 代码 | ❌ `particles` 着色器没有 fragment 阶段 |
| 用 `ALBEDO` / `NORMAL` / `ROUGHNESS` | ❌ 那是 `spatial` 着色器的输出，编译不过 |
| 在 Compatibility 后端工作 | ❌ Compatibility 不支持 GPU 粒子 |

### 3.7 粒子着色器怎么调试

粒子着色器没有可视化编辑器，只能靠「改一点、看一点」地试。三个实用手段：

1. **用 `CUSTOM` 夹带调试数据**：把想要观察的数值塞进 `CUSTOM`，再用绘制通道的材质把它显示出来（`vertex_color_use_as_albedo` + 一个取 `CUSTOM` 的 `spatial` 着色器）；
2. **用 `COLOR` 输出调试色**：把 `COLOR.rgb` 设成你怀疑的量（例如把速度映射成红色），一眼就能看出运动是否异常；
3. **用 Visual Profiler 看 GPU 侧耗时**：粒子着色器在 GPU 上跑，CPU 侧看不出来。抓帧方法见第 22 篇《渲染调试工具》。

```glsl
shader_type particles;

void start() {
    CUSTOM = vec4(0.0);
}

void process() {
    // 调试：把速度大小映射到红色通道，寿命映射到绿色通道
    float speed = length(VELOCITY);
    COLOR = vec4(speed * 0.1, clamp(LIFETIME, 0.0, 1.0), 0.0, 1.0);
}
```

> 💡 调试用的 `COLOR` 会直接进入绘制通道，所以只要材质的 `vertex_color_use_as_albedo` 开着，
> 你在游戏里看到的就是你的调试色——不需要额外的可视化通道。

---

## 四、粒子渲染路径

### 4.1 绘制通道：`draw_pass_1..4`

```gdscript
var emitter := GPUParticles3D.new()

# 第一个绘制通道用一块面片
var quad := QuadMesh.new()

# 贴图通过材质的 albedo_texture 指定
var mat := StandardMaterial3D.new()
mat.albedo_texture = load("res://particle.png")

# 翻页动画（sprite sheet）由材质的 particles_anim_* 控制
mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
mat.particles_anim_h_frames = 4
mat.particles_anim_v_frames = 4
mat.particles_anim_loop = true

quad.material = mat
emitter.draw_pass_1 = quad
emitter.draw_passes = 1
```

> - `GPUParticles3D` 的成员是 `draw_pass_1` ~ `draw_pass_4` 与 `draw_passes`，没有 `texture`。
> - `h_frames` / `v_frames` 也不在 `GPUParticles3D` 上；4.3 里 `Sprite2D` 用 `hframes` / `vframes`，`AnimatedSprite2D` 已经改用 `SpriteFrames` 资源，两者都没有 `h_frames`。
> - 2D 的 `GPUParticles2D` 确实有 `texture` 属性，别把 2D 的写法搬到 3D。

四个通道的典型分工：

| 通道 | 常见用途 |
|------|----------|
| `draw_pass_1` | 主体（火焰、烟雾） |
| `draw_pass_2` | 加色的高光 / 火星 |
| `draw_pass_3` | 减色的烟尘 / 阴影层 |
| `draw_pass_4` | 拖尾或碎屑 |

`draw_passes` 决定实际渲染几个通道。通道越多，绘制提交越多，也越容易出现「粒子一多就掉帧」。

### 4.2 材质与广告牌

| 属性 | 说明 |
|------|------|
| `BaseMaterial3D.billboard_mode` | `BILLBOARD_DISABLED` / `BILLBOARD_ENABLED` / `BILLBOARD_FIXED_Y` / `BILLBOARD_PARTICLES` |
| `BaseMaterial3D.billboard_keep_scale` | 广告牌时是否保持缩放 |
| `BaseMaterial3D.particles_anim_h_frames` / `_v_frames` | 贴图动画的帧数（4 帧 × 4 帧的图集） |
| `BaseMaterial3D.particles_anim_loop` | 贴图动画是否循环 |
| `BaseMaterial3D.use_particle_trails` | 材质层面的拖尾支持 |
| `BaseMaterial3D.vertex_color_use_as_albedo` | 把顶点色（即粒子 `COLOR`）当作 albedo，**做颜色渐变必须开** |
| `StandardMaterial3D.transparency` | 半透明排序模式 |

> 📌 `BILLBOARD_PARTICLES` 与普通 `BILLBOARD_ENABLED` 的区别：前者是**专门给粒子用的**模式，
> 会额外考虑粒子的旋转与缩放（例如 `particle_flag_rotate_y` 打开时，粒子绕 Y 轴转而面片仍然朝屏幕）。
> 做 2D 风格的 3D 粒子时用 `BILLBOARD_PARTICLES` + `particle_flag_disable_z`，观感最接近 2D。

### 4.3 粒子拖尾（4.3 新增）

`GPUParticles3D.trail_enabled` 打开后，节点会保留粒子的历史位置形成拖尾，`trail_lifetime` 控制拖尾保留多久。
配套材质要打开 `BaseMaterial3D.use_particle_trails`，否则看不到效果。
拖尾会显著增加每粒子的顶点量，**只适合少量、慢速的粒子**（箭矢、弹道、能量流）。

### 4.4 可见性与剔除

| 手段 | 效果 | 代价 |
|------|------|------|
| `visibility_aabb` 固定 | 视锥剔除不再每帧重算 AABB | AABB 太小会被错误剔除，太大则失去剔除意义 |
| `visibility_range_begin` / `_end` | 超出距离直接不画 | 远处硬切，需要配淡出 |
| `visibility_range_fade_mode` | 淡出而不是硬切 | 仅 Forward+ 生效 |
| `amount_ratio` | 远处减少粒子数量 | 需要脚本按距离动态改，或配合可见性回调 |
| `fixed_fps` | 降低模拟频率 | 快速运动时需要 `interpolate` 补偿 |

### 4.5 2D 与 3D 的差异对照

| 维度 | GPUParticles2D | GPUParticles3D |
|------|----------------|----------------|
| 绘制内容 | `texture`（一张贴图） | `draw_pass_1..4`（网格 + 材质） |
| 帧数控制 | `hframes` / `vframes` 风格的翻页由 `ParticleProcessMaterial` 的 `anim_speed_*` 控制 | 由材质的 `particles_anim_h_frames` / `_v_frames` 控制 |
| 可见性矩形 | `visibility_rect` | `visibility_aabb` |
| 颜色 | `color`（`Color`） | `color`（`Color`），绘制材质还要开 `vertex_color_use_as_albedo` |
| 变换对齐 | 2D 平面 | `transform_align` 枚举（Z 轴广告牌等） |
| 碰撞 | 与物理服务器的 2D 碰撞 | 高度场 / SDF 近似 |
| 兼容性 | 同样不支持 Compatibility 后端 | 同样不支持 Compatibility 后端 |

### 4.6 透明、混合与排序

粒子的「体积感」几乎全靠混合模式做出来，选错模式是「特效很脏」的常见原因：

| 混合模式 | 常量 | 观感 | 典型用途 |
|----------|------|------|----------|
| 普通混合 | `BLEND_MODE_MIX` | 正常遮挡关系，靠 alpha 淡出 | 烟雾、尘、实体碎块 |
| 加色 | `BLEND_MODE_ADD` | 发光感，黑色等于透明 | 火焰、火星、魔法辉光 |
| 减色 | `BLEND_MODE_SUB` | 变暗 | 烟雾的暗部、吸光效果 |
| 相乘 | `BLEND_MODE_MUL` | 乘算 | 水面下的焦散感、污渍 |
| 预乘 alpha | `BLEND_MODE_PREMULT_ALPHA` | 避免边缘发黑 | 半透明 UI 类粒子 |

配套的两个关键点：

- **`transparency` 要显式设成 `TRANSPARENCY_ALPHA`**（或 `TRANSPARENCY_ALPHA_SCISSOR` / `TRANSPARENCY_ALPHA_HASH`）；
  默认的 `TRANSPARENCY_DISABLED` 会让材质按不透明渲染，alpha 被忽略；
- **排序**：半透明粒子之间不写深度，Godot 4 按**物体中心到相机的距离**排序。
  粒子系统作为一个整体参与排序，粒子之间不会逐个排序——
  这意味着「同一个粒子系统里的粒子互相穿插」是正常现象，不要用排序去解决它。

> 💡 加色 + `vertex_color_use_as_albedo` + 低分辨率贴图，是 Godot 里性价比最高的「看起来很高级」的粒子组合。

---

## 五、性能与调优

### 5.1 粒子成本拆成三块

```
一帧的粒子总成本
    ├── 模拟成本：每粒子的物理积分（位置 / 速度 / 旋转 / 缩放 / 颜色）
    │     └── CPU 粒子：随粒子数线性增长；GPU 粒子：几乎与粒子数无关
    │
    ├── 提交成本：把 N 个粒子变成绘制提交
    │     └── 与「绘制通道数 × 材质数」相关，与粒子数几乎无关
    │
    └── 填充成本：片元着色器跑了多少次（过度绘制）
          └── 与「粒子在屏幕上覆盖的面积」正相关 —— 小粒子铺满屏幕最贵
```

**关键认知**：GPU 粒子的瓶颈几乎从不是「模拟」，而是**过度绘制（overdraw）**。
一团占据半屏的浓烟，填充成本可能是同样数量的小火星的几十倍。

### 5.2 优化清单

| 技巧 | 说明 | 成本 |
|------|------|------|
| **GPU 粒子** | 使用 GPU 加速（Compatibility 渲染器不支持 GPU 粒子） | 低 |
| **固定模拟帧率** | `fixed_fps = 30` + `interpolate = true` | 低 |
| **降分辨率材质** | 粒子贴图用 64×64 / 128×128 而不是 512×512 | 低 |
| **减少绘制通道** | `draw_passes = 1` 而不是 4 | 低 |
| **减少屏幕覆盖** | 缩小粒子的屏幕尺寸，或减少数量 | 中 |
| **预热** | `preprocess` 避免出场瞬间的峰值 | 低 |
| **LOD** | 远距离减少粒子（配合 `visibility_range`） | 中 |
| **Culling** | 屏幕外不渲染（`GPUParticles3D.visibility_aabb`） | 低 |
| **共享材质** | 多个粒子系统共用同一个材质，减少状态切换 | 低 |
| **用 `amount_ratio` 做距离降级** | 远处减粒子而不是全关 | 中 |

### 5.3 性能对照

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际 CPU 占用与帧率取决于粒子着色器复杂度、绘制通道数与目标硬件，请在目标平台实测。
> 完整测试条件模板见第 21 篇《渲染性能优化》。

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。实际开销取决于场景规模与目标硬件，请在目标平台实测。

| 粒子数量 | CPU 占用 | 帧率 |
|---------|---------|------|
| 100 | 1% | 120 FPS |
| 1000 | 5% | 60 FPS |
| 10000 | 30% | 30 FPS |

> 上表是 **CPU 粒子**的量级参考。GPU 粒子在 10000 个时的 CPU 占用会低得多，
> 但 GPU 侧可能因为过度绘制而先撞上填充率上限——两种瓶颈的排查方式完全不同（见第 21 篇与第 22 篇）。

### 5.4 与第 42 篇《动画性能优化》的分工

| 主题 | 归属 | 理由 |
|------|------|------|
| 粒子**渲染**：绘制通道、广告牌、贴图动画、拖尾、粒子着色器 | **本篇** | 粒子是渲染系统的一部分 |
| 动画 **LOD**：骨骼数量分级、动画压缩、动画批处理 | **第 42 篇** | 属于动画系统（第四卷） |
| 骨骼网格**批量更新**（SkinnedMesh + MultiMesh） | **第 42 篇** | 属于动画系统的批量更新策略 |
| 粒子数量按距离降级 | **本篇** | 属于粒子渲染路径 |

> 📌 简单说：**本篇管「粒子长什么样、怎么画」，第 42 篇管「骨骼动画怎么省」**。
> 两篇都会碰到 `MultiMesh`，但用途不同——本篇的多网格是「同一种粒子网格的 N 个实例」，
> 第 42 篇的多网格是「N 个带骨骼的角色共用一份骨骼动画数据」。

### 5.5 怎么测粒子的成本

粒子的成本要拆成「模拟」和「绘制」两块看，单看帧率没有意义。下面这个采样器可以直接挂进场景里跑：

```gdscript
# 粒子成本采样器：挂在场景里，每秒记一次渲染统计
extends Node

const SAMPLE_SECONDS := 10.0

var _elapsed: float = 0.0
var _samples: Array = []

func _process(delta: float) -> void:
	_elapsed += delta
	if _elapsed < 1.0:
		return
	_elapsed = 0.0
	_samples.append({
		"fps": Performance.get_monitor(Performance.TIME_FPS),
		"objects": Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
		"primitives": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
	})
	if _samples.size() >= int(SAMPLE_SECONDS):
		_report()

func _report() -> void:
	var total := 0.0
	for s in _samples:
		total += s["fps"]
	print("平均 FPS：", total / _samples.size())
	print("采样点数：", _samples.size())
	_samples.clear()
```

**怎么读这些数字**：

| 现象 | 结论 | 下一步 |
|------|------|--------|
| `objects` 暴涨、`draw_calls` 基本不变 | 粒子数量多但提交少 | 模拟成本为主 → 降 `amount` / 开 `fixed_fps` |
| `draw_calls` 暴涨 | 绘制通道多 / 材质没共享 | 降 `draw_passes`、合并材质 |
| 帧率掉了但上面两个数都没怎么变 | **过度绘制**（填充率瓶颈） | 缩小粒子屏幕尺寸、降贴图分辨率、改混合模式 |
| 帧率稳定但 `TIME_FPS` 抖动大 | 采样窗口太短 | 采样至少 10 秒，丢弃前 2 秒预热 |

> ⚠️ 任何结论都要带上测试条件（引擎版本、GPU、分辨率、场景规模、采样方式），
> 完整模板见第 21 篇《渲染性能优化》的「统一性能数字口径与测试条件模板」。

---

## 六、常见坑速查

| 现象 | 真实原因 |
|------|----------|
| `Invalid set index 'emission_shape'` | 写在了 `GPUParticles3D` 上；它属于 `ParticleProcessMaterial` |
| `Invalid set index 'texture'`（3D） | 3D 粒子用 `draw_pass_1..4`，`texture` 是 `GPUParticles2D` 才有的 |
| `Invalid set index 'h_frames'` | 4.3 里是 `hframes` / `vframes`（2D），3D 用材质的 `particles_anim_h_frames` |
| `Invalid set index 'sub_emitter_node_paths'` | 4.3 只有 `sub_emitter` 一个 `NodePath` |
| 粒子完全不显示 | 渲染后端是 Compatibility；GPU 粒子在那个后端不可用 |
| 粒子颜色没变化 | 材质的 `vertex_color_use_as_albedo` 没开 |
| 粒子卡在原地 | `local_coords` 与 `transform_align` 的组合不符合预期；或过程材质的 `gravity` 没设 |
| 粒子出生瞬间是一坨 | 没设 `preprocess` |
| 特效远处突然消失 | `visibility_range_end` 没有配 `visibility_range_end_margin` 淡出 |
| 粒子多就掉帧 | 多半是过度绘制，不是模拟成本；先降屏幕覆盖面积 |

---

## 核心要点

1. **粒子类型**：GPU 粒子（GPU 模拟，**Compatibility 后端不可用**）与 CPU 粒子（主线程模拟，参数摊平在节点上）；两者取舍看「数量」与「是否需要真实物理碰撞」。
2. **发射形状**：属于 `ParticleProcessMaterial`（`emission_shape` / `emission_sphere_radius` / `emission_box_extents`），`GPUParticles3D` 成员表里没有这三个属性。
3. **过程材质属性分组**：发射形状、初始运动、缩放颜色、曲线、湍流、碰撞、子发射器、粒子标志——曲线槽位类型统一是 `Texture2D`（接 `CurveTexture` 或 `GradientTexture1D`）。
4. **绘制通道**：3D 粒子用 `draw_pass_1..4` + `draw_passes`，材质侧用 `BILLBOARD_PARTICLES` 与 `particles_anim_*` 做广告牌与翻页。
5. **粒子着色器**：`shader_type particles` 提供 `start()` / `process()`，内置量有 `EMISSION_TRANSFORM`、`POSITION`、`VELOCITY`、`ROTATION`、`COLOR`、`CUSTOM`、`MASS`、`ACTIVE`、`LIFETIME`、`DELTA` 与三个 `FLAG_*`；它**没有** fragment 阶段，也**没有** `ALBEDO` 那套输出。
6. **性能**：GPU 粒子的瓶颈通常在过度绘制而不是模拟；`fixed_fps` + `interpolate`、`amount_ratio`、`visibility_range` 是三个低成本的降载手段。
7. **分工**：粒子渲染在本篇，动画 LOD 与骨骼批量更新在第 42 篇《动画性能优化》。
8. **数字纪律**：任何粒子性能数字都必须附带引擎版本、GPU、分辨率、场景规模与采样方式（模板见第 21 篇）。

---

## 🔗 延伸阅读

- **官方文档**: [3D 粒子系统](https://docs.godotengine.org/en/stable/tutorials/3d/particles/index.html)、[粒子材质](https://docs.godotengine.org/en/stable/tutorials/3d/particles/process_material.html)、[粒子着色器（Shader reference）](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/particle_shader.html)
- **类参考**: [GPUParticles3D](https://docs.godotengine.org/en/stable/classes/class_gpuparticles3d.html)、[CPUParticles3D](https://docs.godotengine.org/en/stable/classes/class_cpuparticles3d.html)、[ParticleProcessMaterial](https://docs.godotengine.org/en/stable/classes/class_particleprocessmaterial.html)、[StandardMaterial3D](https://docs.godotengine.org/en/stable/classes/class_standardmaterial3d.html)
- **源码位置**: `scene/3d/gpu_particles_3d.h`、`scene/3d/cpu_particles_3d.h`、`scene/resources/particle_process_material.cpp`、`servers/rendering/renderer_rd/shaders/storage/`

---

## 📋 下一章预告

**第 21 篇：渲染性能优化**

- Draw Call 的来源与削减手段（MultiMesh / 共享材质 / 可见性范围）
- LOD：`visibility_range` 与 `lod_bias`（4.7.2 仍没有 `LOD3D` 节点）
- 遮挡剔除：基于 **Embree** 的 `OccluderInstance3D`
- 统一性能数字口径与测试条件模板

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 19 篇：后处理效果](/articles/19-post-processing-effects.md)
**下一篇**: [第 21 篇：渲染性能优化](/articles/21-performance-optimization.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
