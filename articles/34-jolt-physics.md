# 第 34 篇：Jolt Physics

> **本章导读**：Jolt 是 Godot 4.4 起随引擎分发的第三方物理引擎，**4.6 起新建 3D 项目默认使用它**——这条版本事实是本章的核心。
> 本章厘清三件事：Jolt 是什么、4.1–4.3 用扩展 / 4.4–4.5 内置但非默认 / 4.6 起默认的时间线；怎么在项目设置里切换与验证；以及换成 Jolt 之后**哪些代码不用改、哪些行为会有差异**（尤其是 CCD 与睡眠阈值）。
> **前置知识**：第 23 篇《Godot 物理架构概述》
> **难度**：进阶。

> **摘要**：Jolt 是由 Jorrit Rouwe 开发、在《Horizon Forbidden West》中验证过的高性能物理引擎。Godot 4.4 起将其作为内置模块随引擎分发（4.1–4.3 通过 godot-jolt 扩展使用）。本文讲解启用方式、与 Godot Physics 的取舍、运行时探测与调优清单。

---

## 一、Jolt 是什么

| 事实 | 说明 |
|------|------|
| 来源 | Jorrit Rouwe 的开源 C++ 物理引擎，曾在《地平线：西之绝境》中承载全场景物理 |
| 4.1–4.3 | 以 GDExtension 形式提供（godot-jolt 项目），需手动安装 |
| 4.4 起 | 官方将其合并为**内置引擎模块**，随编辑器/导出模板分发 |
| 4.4–4.5 状态 | 官方文档标注为实验性（experimental / not finished / lacks feature parity） |
| 4.6 起 | 官方文档写明「**By default, new projects will use it as the physics engine**」——**新建 3D 项目默认使用 Jolt**（已有项目不受影响，需手动切换） |
| 定位 | 3D 物理；**2D 物理不受影响**，仍由 Godot Physics 2D 驱动 |

> 版本提示：本书示例基线为 4.7.2，Jolt 自 4.4 起内置；4.1–4.3 需安装扩展。
> 关于"默认"这件事要分清两个版本：4.4 把 Jolt 做成了内置模块但**不是默认**；
> **4.6 才开始让新建项目默认使用 Jolt**（老项目仍保留原来的 Godot Physics 设置）。

### 1.1 版本进展时间线（以官方发布页与官方文档为准）

| 版本 | 时间 | Jolt 的状态 | 关键变化 |
|---|---|---|---|
| 4.1–4.3 | 2024 年 | 第三方 GDExtension | 需要自己下载 `godot-jolt` 扩展；项目设置在 `physics/jolt_3d` 分类下 |
| **4.4** | 2025-03 | **内置模块，实验性** | 官方合并进引擎（PR #99895）；项目设置迁移到 `physics/jolt_physics_3d`；扩展项目转为"维护模式"；官方文档明确写"尚未完成、实验性、功能不对等" |
| 4.5 | 2025 年 | 内置模块，实验性 | 官方 Jolt 文档的"与 Godot Physics 的显著差异"清单比 4.4 少了一条：`Area3D` 与静态体默认不检测的行为差异不再单列（但 `SoftBody3D` ↔ `Area3D` 仍不支持） |
| **4.6** | 2026-01-26 | **去掉实验标签，成为默认** | 发布页原文："we're confident enough to remove the experimental label and make Jolt the default physics engine for all new 3D projects"；同时注明"Existing projects aren't affected"。`simulation/areas_detect_static_bodies` 这一设置项在 4.6 的 `ProjectSettings.xml` 中已不存在 |
| 4.7 | 2026-06-18 | 默认可用 | 官方 Jolt 文档新增：**Jolt 支持 `SoftBody3D` 与 `Area3D` 的交互**（风、重力、overlap 信号），这是 4.4–4.6 都没有的能力 |

> 关于"默认"的精确机制：4.4 与 4.6 的 `ProjectSettings.xml` 里，`physics/3d/physics_engine` 的**默认值都是 `"DEFAULT"`**。4.6 起的"新建项目默认用 Jolt"是**项目管理器创建项目时写入 `project.godot`** 实现的，不是靠改默认值。因此老项目升级引擎后设置不会被改动——这与发布页的说明一致。

---

## 二、启用与切换

### 2.1 项目设置（4.4+）

路径：**项目设置 → 物理 → 3D → 物理引擎（Physics Engine）→ Jolt Physics**。

对应的项目设置键为 `physics/3d/physics_engine`，可选值包括默认的 `GodotPhysics3D` 与 `Jolt Physics`：

```gdscript
# 用代码确认当前引擎（与第 23 篇 2.3 节一致）
func get_physics_engine_name() -> String:
    return str(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT"))
```

切换是**项目级**的：整个 3D 物理世界从启动起就运行在 Jolt 上，无需逐对象指定。

### 2.2 4.1–4.3 的安装

1. 从 Asset Library 或 godot-jolt 的 GitHub Release 获取与引擎版本匹配的扩展包；
2. 解压到 `res://addons/godot-jolt/`；
3. 启用扩展并重启编辑器，随后同样在项目设置中切换物理引擎。

### 2.3 代码无需改动

Jolt 是**即插即用（drop-in）替换**：`RigidBody3D`、`CharacterBody3D`、`Area3D`、`PhysicsDirectSpaceState3D` 等节点与查询 API 完全不变。第 23–33 篇的所有示例在两种引擎下语义一致——差异只在表现（稳定性、性能、边缘行为的细节）。

### 2.4 编译开关：自己编译引擎时怎么带上 Jolt

4.4+ 的官方编辑器与导出模板**已经内置** Jolt，普通用户不需要编译。但如果你要自编译引擎（例如加自定义模块、做平台移植），需要知道模块是怎么被开关的。

Godot 的 SCons 构建系统把每个模块目录名映射成一个布尔选项。4.4 的 `SConstruct` 第 402 行：

```python
# SConstruct（4.4）
opts.Add(BoolVariable(f"module_{name}_enabled", f"Enable module '{name}'", enabled))
```

于是 `modules/jolt_physics/` 对应的开关就是：

```bash
# 编译时带上 Jolt 模块
scons platform=linuxbsd target=editor module_jolt_physics_enabled=yes
```

配套的两个事实：

- **模块默认是启用的**。`SConstruct` 第 393 行是 `if env["modules_enabled_by_default"]:`，只有显式传 `modules_enabled_by_default=no` 才会关掉全部模块（此时仍需逐个 `module_xxx_enabled=yes` 打开）。
- **Jolt 模块有平台门槛**。4.4 的 `modules/jolt_physics/config.py`：

  ```python
  # modules/jolt_physics/config.py（4.4）
  def can_build(env, platform):
      return not env["disable_3d"] and not env["arch"] == "ppc32"
  ```

  也就是：**纯 2D 构建（`disable_3d`）与 32 位 PowerPC 不编译 Jolt**。做 2D-only 移植时不用管它。

### 2.5 第三方物理后端的接入点：`PhysicsServer3DExtension`

Jolt 之所以能"一行项目设置"就接管整个 3D 物理世界，是因为引擎在 4.4 引入了**物理服务器的扩展点**：`PhysicsServer3DExtension`。

4.4 / 4.6 的 `doc/classes/PhysicsServer3DExtension.xml` 说明写得很直接：

> "This class extends PhysicsServer3D by providing additional virtual methods that can be overridden. When these methods are overridden, they will be called instead of the internal methods of the physics server. Intended for use with GDExtension to create custom implementations of PhysicsServer3D."

它把 `PhysicsServer3D` 的全部内部方法拆成**必须重写（`virtual required`）**的虚函数，第三方后端继承它即可接管：

| 虚函数族 | 职责 |
|---|---|
| `_init()` / `_finish()` | 后端初始化与析构 |
| `_step(step)` | 推进一个物理步 |
| `_flush_queries()` / `_is_flushing_queries()` | 查询的刷新时机 |
| `_sync()` / `_end_sync()` | 物理状态与渲染线程的同步 |
| `_body_create()` / `_body_set_state()` / `_body_apply_impulse()` … | 刚体的完整生命周期 |
| `_area_create()` / `_area_set_monitor_callback()` … | 区域体与监测回调 |
| `_space_create()` / `_space_set_param()` / `_space_get_direct_state()` | 空间与查询入口 |
| `_box_shape_create()` / `_sphere_shape_create()` / `_concave_polygon_shape_create()` … | 形状工厂 |
| `_joint_make_pin()` / `_joint_make_hinge()` / `_joint_make_slider()` … | 关节工厂 |
| `_soft_body_create()` / `_soft_body_pin_point()` / `_soft_body_update_rendering_server()` … | 软体 |

**能从中读出什么**：

1. 第三方后端是**整台服务器级替换**，不是"挂在节点上的插件"——你必须实现全部虚函数。
2. `_body_set_force_integration_callback()` 与 `_body_set_state_sync_callback()` 都在列表里，说明 `_integrate_forces` 这套回调协议是**服务器无关**的，换后端不用改业务代码。
3. `_soft_body_*` 也在列表里，说明软体同样是服务器能力的一部分——这也是为什么 Jolt 能接管 `SoftBody3D`（见 3.1 节第 13 行）。

> 对绝大多数项目来说，**这些不需要你写**——Jolt 已经是官方模块。但了解这个扩展点能回答两个常见问题："为什么 Jolt 能无缝接管"、"我能不能自己写一个物理后端"。答案是：能，但工作量是"实现一个完整的物理引擎 + 一层服务器适配"，不是写个插件。

---

## 三、与 Godot Physics 的取舍

| 维度 | Godot Physics | Jolt Physics |
|------|---------------|--------------|
| 线程模型 | 单线程为主 | 多线程任务系统，大规模场景收益明显 |
| 稳定性 | 复杂堆叠场景易抖动 | 工业级求解器，堆叠与约束更稳 |
| 功能对齐 | 完整 | 4.4 时实验性，部分行为有差异；4.6+ 已补齐大部分能力 |
| 默认状态 | 4.3 及以前默认 | **4.6 起新建 3D 项目默认使用 Jolt** |
| 2D | 唯一实现 | 不涉及（2D 始终用 Godot Physics 2D） |
| 体积 | 内置 | 内置（4.4+），导出模板已包含 |

选型建议（与第 23 篇 9.3 节一致）：

- **4.6+ 的新项目**：3D 默认就是 Jolt，通常不需要额外决策；2D 项目仍用 Godot Physics 2D；
- **从 4.3 及更早版本迁移过来的项目**：默认仍是 Godot Physics，是否切换取决于项目类型——大型 3D、物理模拟为主的项目值得实测切换；小型 2D 项目没有切换的必要；
- 任何切换都必须在目标平台上重跑性能与行为测试——两个引擎的接触表现、休眠阈值并不逐一等价（指标解读差异见第 32 篇 8.8 节）。

### 3.1 逐项行为差异对照表（含版本标注）

这张表逐项列出两个后端**行为层面**的差异，而不是性能宣传。每一行都标出该差异在哪个版本成立，依据是 Godot 官方 Jolt 文档（`godot-docs` 的 `tutorials/physics/using_jolt_physics.rst`）与 `ProjectSettings.xml`。

| # | 维度 | Godot Physics | Jolt Physics | 成立版本 |
|---|---|---|---|---|
| 1 | 默认状态 | 4.3 及以前默认 | 4.4 内置但需手动启用；**4.6 起新建 3D 项目默认** | 4.4 / 4.6 |
| 2 | 官方标签 | 完整 | 4.4–4.5 标注 experimental；4.6 去掉 | 4.4–4.5 / 4.6 |
| 3 | 休眠参数 | `physics/3d/sleep_threshold_linear`（0.1）、`sleep_threshold_angular`（0.13962634）、`time_before_sleep`（0.5） | `simulation/allow_sleep`（true）、`sleep_velocity_threshold`（0.03）、`sleep_time_threshold`（0.5） | 4.4+ |
| 4 | 接触偏移（margin） | **完全不使用** `Shape3D` 的 `margin` | 把 `margin` 当作 "convex radius"，并用 `collisions/collision_margin_fraction`（0.08）按形状 AABB 最小轴自动换算，`margin` 只作为上限 | 4.4+ |
| 5 | 连续碰撞支持度 | 支持（`RigidBody3D.continuous_cd`） | 支持，且阈值改由 `simulation/continuous_cd_movement_threshold`（0.75）、`continuous_cd_max_penetration`（0.25）控制，**以比例而非百分数表达** | 4.4+ |
| 6 | 穿模稳定方式 | Baumgarte 按弹簧式处理，**可能过冲**（物体被弹开） | 只修正位置、不修正速度，**不会过冲但可能更慢**；强度由 `simulation/baumgarte_stabilization_factor`（0.2）控制，`0` = 关闭，`1` = 一个物理步解决（快但常不稳定） | 4.4+ |
| 7 | 关节马达 / 软限位 | 完整支持 | **不支持**：PinJoint3D 的 `bias`/`damping`/`impulse_clamp`；HingeJoint3D 的 `bias`/`softness`/`relaxation`；SliderJoint3D 的 `angular_*` 与 `*_limit/{softness,restitution,damping}`；ConeTwistJoint3D 的 `bias`/`relaxation`/`softness`；Generic6DOFJoint3D 的 `*_limit_*/{softness,restitution,damping,erp}`。**设成非默认值会触发警告** | 4.4+ |
| 8 | 接触事件 | `FREEZE_MODE_KINEMATIC` 的刚体照常报告与静态/运动学体的接触 | 默认**不**报告与静态/运动学体的接触（性能考虑），需开 `simulation/generate_all_kinematic_contacts`（默认 false） | 4.4+ |
| 9 | `Area3D` 检测静态体 | 照常检测 | 4.4 默认**不**检测（`simulation/areas_detect_static_bodies` 默认 false）；4.5 起官方文档不再单列此差异，4.6 的 `ProjectSettings.xml` 中已无该设置项 → 视为已对齐 | 4.4 / 4.6 |
| 10 | 单体关节的"世界"归属 | 视 `node_a` 为世界（忽略 `node_b`） | 视 `node_b` 为世界（`node_a` 代表世界）；`physics/jolt_physics_3d/joints/world_node` 可切换以兼容旧项目 | 4.4+ |
| 11 | 接触冲量 | `PhysicsDirectBodyState3D.get_contact_impulse()` 为实测量 | 为**预估**值（依据接触流形与速度提前算出），仅当两物体不与其他物体碰撞时才准确 | 4.4+ |
| 12 | 射线 `face_index` | 正常返回 | 默认恒为 `-1`，需开 `queries/enable_ray_cast_face_index`（默认 false）；开启后 `ConcavePolygonShape3D` 内存约 **+25%** | 4.4+ |
| 13 | `SoftBody3D` ↔ `Area3D` | 支持风、重力、overlap 信号 | **4.4–4.6 不支持**（连风/重力都没有）；**4.7 起支持**，且比 Godot Physics 还多支持 `Area3D` 的各种 overlap 信号与方法 | 4.4–4.6 / 4.7 |
| 14 | `WorldBoundaryShape3D` | 有效平面尺寸上限较大 | 上限**明显更小**（为避免精度问题），可用 `limits/world_boundary_shape_size`（2000.0）调整 | 4.4+ |
| 15 | 幽灵碰撞（ghost collision） | 无专门机制 | 两套机制：active edge detection（`collisions/active_edge_threshold`，0.87266463）+ enhanced internal edge removal（`simulation/` / `queries/` / `motion_queries/` 三个开关）。**两者都不作用于两个不同物体之间的幽灵碰撞** | 4.4+ |
| 16 | `_integrate_forces` | 支持 | 支持（协议在 `PhysicsServer3DExtension` 层面定义，与后端无关），但**直接改写状态的代码必须在 Jolt 下复测** | 4.4+ |
| 17 | 线程模型 | 引擎可选 `physics/3d/run_on_separate_thread`（默认 false） | 模块有线程安全，**支持** `physics/3d/run_on_separate_thread`；官方注明"未经充分测试，仍应视为实验性" | 4.4+ |
| 18 | 质量单位 | 千克（kg） | 千克（kg）——**两个 3D 后端没有质量单位差异** | 4.4+ |

第 18 行值得展开一句：**真正的单位陷阱在 2D 与 3D 之间，而不是在两个 3D 后端之间**。3D 物理两边都用米/千克/秒（`physics/3d/default_gravity` 默认 `9.8`）；2D 物理用像素（`physics/2d/default_gravity` 默认 `980`，`Area2D.gravity` 默认 `980.0`）。把 3D 的参数直接搬进 2D 会差两个数量级。

第 3 行也要展开：**两边的休眠阈值不逐一等价**。Godot Physics 的 `sleep_threshold_linear` 是世界单位下的线速度阈值，Jolt 的 `sleep_velocity_threshold` 默认 `0.03`，数量级与判定口径都不同。**"以前睡的现在不睡"（或相反）是切换后最常见的可见回归**。

---

## 四、运行时探测与容错

```gdscript
func is_jolt_active() -> bool:
    return str(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT")) == "Jolt Physics"
```

用途：

- 依赖 Jolt 专属调优时给出提示（例如堆叠玩法的关卡加载时打印引擎名，便于 QA 复现）；
- 工具插件在两种引擎下选择不同的诊断阈值。

注意：**物理 API 不做引擎分支**。凡是需要按引擎写不同代码的需求，先怀疑用法错误——两个引擎公开给脚本的接口是同一套。

---

## 五、调优清单

### 5.1 项目设置的真实键名（以 `ProjectSettings.xml` 为准）

Jolt 的调优项集中在项目设置的 **Physics → Jolt Physics 3D** 分节（4.4+ 内置模块）。下表是 4.4 `doc/classes/ProjectSettings.xml` 里**逐项核实过的全部 33 个** `physics/jolt_physics_3d/*` 设置项及其默认值：

**simulation（模拟）**

| 设置键 | 默认值 | 说明 |
|---|---|---|
| `physics/jolt_physics_3d/simulation/velocity_steps` | `10` | 速度求解迭代次数 |
| `physics/jolt_physics_3d/simulation/position_steps` | `2` | 位置求解迭代次数 |
| `physics/jolt_physics_3d/simulation/baumgarte_stabilization_factor` | `0.2` | 穿模稳定强度；`0` = 关闭，`1` = 一个物理步解决 |
| `physics/jolt_physics_3d/simulation/allow_sleep` | `true` | 是否允许休眠 |
| `physics/jolt_physics_3d/simulation/sleep_velocity_threshold` | `0.03` | 休眠的线速度阈值 |
| `physics/jolt_physics_3d/simulation/sleep_time_threshold` | `0.5` | 休眠的时间阈值 |
| `physics/jolt_physics_3d/simulation/use_enhanced_internal_edge_removal` | `true` | 增强型内部边缘移除（模拟阶段） |
| `physics/jolt_physics_3d/simulation/areas_detect_static_bodies` | `false` | **`Area3D` 是否检测静态体**——4.4 默认关闭；4.6 的 `ProjectSettings.xml` 中已无此项（视为已对齐） |
| `physics/jolt_physics_3d/simulation/generate_all_kinematic_contacts` | `false` | 是否为运动学刚体生成全部接触 |
| `physics/jolt_physics_3d/simulation/penetration_slop` | `0.02` | 允许的穿透量（相当于 Godot Physics 的 `contact_max_allowed_penetration`） |
| `physics/jolt_physics_3d/simulation/speculative_contact_distance` | `0.02` | 推测性接触距离 |
| `physics/jolt_physics_3d/simulation/bounce_velocity_threshold` | `1.0` | 触发反弹的最小相对速度 |
| `physics/jolt_physics_3d/simulation/continuous_cd_movement_threshold` | `0.75` | 触发 CCD 的移动量阈值（**比例**，非百分数） |
| `physics/jolt_physics_3d/simulation/continuous_cd_max_penetration` | `0.25` | CCD 允许的最大穿透（**比例**） |
| `physics/jolt_physics_3d/simulation/body_pair_contact_cache_enabled` | `true` | 物体对接触缓存 |
| `physics/jolt_physics_3d/simulation/body_pair_contact_cache_distance_threshold` | `0.001` | 接触缓存的距离阈值 |
| `physics/jolt_physics_3d/simulation/body_pair_contact_cache_angle_threshold` | `0.034906585` | 接触缓存的角度阈值 |
| `physics/jolt_physics_3d/simulation/soft_body_point_radius` | `0.01` | 软体点的碰撞半径 |

**collisions / queries / motion_queries（碰撞与查询）**

| 设置键 | 默认值 | 说明 |
|---|---|---|
| `physics/jolt_physics_3d/collisions/collision_margin_fraction` | `0.08` | 碰撞 margin = 该系数 × 形状 AABB 最小轴；`margin` 属性只作上限 |
| `physics/jolt_physics_3d/collisions/active_edge_threshold` | `0.87266463` | active edge detection 的角度阈值（弧度） |
| `physics/jolt_physics_3d/queries/use_enhanced_internal_edge_removal` | `false` | 增强型内部边缘移除（查询阶段） |
| `physics/jolt_physics_3d/queries/enable_ray_cast_face_index` | `false` | 射线是否返回 `face_index`；开启后 `ConcavePolygonShape3D` 内存约 +25% |
| `physics/jolt_physics_3d/motion_queries/use_enhanced_internal_edge_removal` | `true` | 增强型内部边缘移除（运动查询阶段） |
| `physics/jolt_physics_3d/motion_queries/recovery_iterations` | `4` | 运动查询的穿透恢复迭代次数 |
| `physics/jolt_physics_3d/motion_queries/recovery_amount` | `0.4` | 运动查询的穿透恢复量（**比例**） |

**limits / joints（上限与关节）**

| 设置键 | 默认值 | 说明 |
|---|---|---|
| `physics/jolt_physics_3d/limits/max_bodies` | `10240` | 最大刚体数 |
| `physics/jolt_physics_3d/limits/max_body_pairs` | `65536` | 最大物体对数 |
| `physics/jolt_physics_3d/limits/max_contact_constraints` | `20480` | 最大接触约束数 |
| `physics/jolt_physics_3d/limits/max_linear_velocity` | `500.0` | 最大线速度 |
| `physics/jolt_physics_3d/limits/max_angular_velocity` | `47.12389` | 最大角速度（**弧度**，不是角度） |
| `physics/jolt_physics_3d/limits/temporary_memory_buffer_size` | `32` | 模拟栈分配器的临时内存缓冲大小（MB） |
| `physics/jolt_physics_3d/limits/world_boundary_shape_size` | `2000.0` | `WorldBoundaryShape3D` 的有效平面尺寸上限 |
| `physics/jolt_physics_3d/joints/world_node` | `0` | 单体关节时把"世界"视为 `node_a`（兼容 Godot Physics）还是 `node_b`（Jolt 默认） |

### 5.2 三条常见误解的更正

网上（含早期版本的书稿）常见的 Jolt"调优项"里，有三条**在 4.4/4.6 的 `ProjectSettings.xml` 里根本不存在**：

| 常见说法 | 实际情况 |
|---|---|
| "Simulation → Worker Count（物理线程数）" | Jolt 模块**没有** worker 线程数设置项。线程相关的开关是引擎通用项：`physics/3d/run_on_separate_thread`（默认 `false`）、`physics/common/physics_ticks_per_second`（默认 `60`）、`physics/common/max_physics_steps_per_frame`（默认 `8`） |
| "Contacts → Max Contact Points（单对最多接触点）" | 没有这个设置项。接近的是**整体上限**：`limits/max_contact_constraints`（20480）、`limits/max_body_pairs`（65536）、`limits/max_bodies`（10240） |
| "Physics → Jolt Physics 的分节叫 *Jolt Physics*" | 分节名是 **Jolt Physics 3D**，设置前缀是 `physics/jolt_physics_3d/`（4.1–4.3 的扩展版用的是 `physics/jolt_3d/`，内置模块统一改名过） |

另外，`Use Enhanced Internal Edge Removal` **不是一项而是一项三份**：`simulation/`（默认 `true`）、`queries/`（默认 `false`）、`motion_queries/`（默认 `true`）各有一个，只改其中一处不会影响其他阶段。

### 5.3 调优顺序

调优顺序建议：先保证帧内物理耗时（`Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)`）稳定，再逐项微调，每改一项都做前后对比——与第 32 篇的基准测试流程相同。

推荐次序：

1. **先调 `simulation/velocity_steps` / `simulation/position_steps`**：这是求解精度的主开关。堆叠不稳时先加 `position_steps`（默认 2），再考虑 `velocity_steps`（默认 10）；
2. **再调 `simulation/baumgarte_stabilization_factor`**（默认 0.2）：穿模严重时上调；但 `1.0` 通常会不稳定；
3. **然后调 `simulation/penetration_slop` 与 `simulation/speculative_contact_distance`**：这两项决定"多近算接触"，直接影响高速物体的穿透；
4. **最后才碰 `limits/*`**：把上限调大只是把崩溃换成卡顿；
5. **`queries/enable_ray_cast_face_index` 按需开**：它带来约 25% 的凹多边形内存开销，不为调试就别开。

> ⚠️ 以上是**调优方向**建议，不含实测数值；具体数值必须在目标硬件与目标场景上实测对比。

---

## 六、迁移检查清单

从 Godot Physics 迁移到 Jolt 时，逐项确认：

- [ ] **两个后端分别跑一遍基线**：先用 Godot Physics 跑一遍目标场景，把帧耗时、刚体位置、接触点数量等**记录成基线**，再切到 Jolt 跑同一场景做对比。没有基线就无从判断"变好了还是变坏了"——这一步与第 32 篇的基准测试流程是同一件事；
- [ ] **场景逐个过**：接触表现（弹跳、摩擦、堆叠高度）与之前是否一致；
- [ ] **约束关节**：马达速度、限制角度在两个引擎下的求解结果差异；**并确认没有使用 Jolt 不支持的关节属性**（见 3.1 节第 7 行），否则运行时会刷警告；
- [ ] **休眠行为**：阈值不同可能导致"以前睡的现在不睡"（或相反），观察 `sleeping` 状态；
- [ ] **CCD**：高速投射物两边的穿透表现差异；Jolt 的阈值改用比例表达，迁移时不要直接搬百分数；
- [ ] **`_integrate_forces`**：直接改写物理状态的代码（第 24/33 篇模式）要在 Jolt 下复测；
- [ ] **接触冲量的用法**：如果游戏逻辑依赖 `get_contact_impulse()` 的数值（做伤害计算、击退），注意 Jolt 下这是**预估值**，只有两物体不与其他物体碰撞时才准确；
- [ ] **`Area3D` 的检测范围**：4.4 下 Jolt 默认不检测静态体；如果游戏依赖"玩家进入 Area 触发"，确认目标体不是纯静态体；
- [ ] **`SoftBody3D` 的 `Area3D` 交互**：如果用了风/重力区域，4.4–4.6 的 Jolt **完全不支持**这种交互（见 3.1 节第 13 行），4.7 才支持；
- [ ] **单体关节**：如果场景里有只指定了一个 body 的关节，检查限位方向是否被 Jolt 翻转（`joints/world_node` 可切回兼容行为）；
- [ ] **射线结果的 `face_index`**：如果代码依赖 `face_index` 判定命中的是哪个面，需要开 `queries/enable_ray_cast_face_index`，否则恒为 `-1`；
- [ ] **导出模板**：确认使用的导出模板包含 Jolt 模块（4.4+ 官方模板已包含）。

---

## 七、总结

- Jolt 是 4.4 起**内置**的 3D 物理替代实现，多线程、大规模场景更稳；4.4–4.5 时仍属实验性，**4.6 起新建 3D 项目默认使用 Jolt**（老项目设置不变）；
- 启用只需一个项目设置（`physics/3d/physics_engine`），节点与查询 API 完全不变；
- 2D 物理与 Jolt 无关——2D 始终是 Godot Physics 2D；
- 真正需要逐项核对的是 3.1 节那张 18 行的差异表，**其中第 3、7、8、13 行最容易在项目里踩到**；
- `physics/jolt_physics_3d/*` 有 33 个设置项（4.4）/ 32 个（4.6），键名以本节 5.1 的表为准；
- 迁移的核心工作是**行为复测**，不是代码改写（指标解读差异见第 32 篇 8.8 节）；
- 想自己接一个物理后端，入口是 `PhysicsServer3DExtension`（4.4+），但那意味着实现一整个物理引擎。

---

## 🔗 延伸阅读

- **使用 Jolt Physics（官方文档）**: <https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html>
- **godot-jolt 项目**: <https://github.com/godot-jolt/godot-jolt>
- **Jolt 官方**: <https://github.com/jrouwe/JoltPhysics>
- **PhysicsServer3DExtension**: <https://docs.godotengine.org/en/stable/classes/class_physicsserver3dextension.html>
- **Godot 4.4 发布说明**: <https://godotengine.org/releases/4.4/>
- **Godot 4.6 发布说明**: <https://godotengine.org/releases/4.6/>
- **源码位置**: `modules/jolt_physics/`（`config.py`、`SCsub`）、`doc/classes/PhysicsServer3DExtension.xml`

---

## 📋 下一章预告

**第 35 篇：软体与可变形体**

- `SoftBody3D` 的真实属性与固定点系统（含 3.x 已移除的 API）
- 4.x 软体是内置简化 PBD：没有自碰撞、没有独立碰撞形状
- `SoftBody3D` 与 Jolt 的共存边界（4.4–4.6 不支持 `Area3D` 交互，4.7 才支持）
- `SkeletonModifier3D` / `PhysicalBoneSimulator3D` / `SpringBoneSimulator3D` 三条自研路线
- 布料、绳索、橡胶的实际搭配

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 33 篇：2D 物理系统](/articles/33-2d-physics.md)
**下一篇**: [第 35 篇：软体与可变形体](/articles/35-soft-bodies.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
