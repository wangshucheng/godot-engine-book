# 第 35 篇：软体与可变形体

> **本章导读**：软体与可变形体让物体「可以被压弯、被捏扁」，但 Godot 内置方案只覆盖了一小部分需求。
> 本章对比三条路线——内置 `SoftBody3D`（参数即调，零代码）、自研 PBD（第 30 篇的质点弹簧系统，可自定义撕裂与约束）、以及第三方插件；讲清固定点系统、旗帜与果冻两类典型实现，并给出 3.x 移除对照，避免继续用已被删掉的旧 API。
> **前置知识**：第 30 篇《布料模拟》
> **难度**：高级。

> **摘要**：软体（Soft Body）与可变形体让物体"可以被压弯、被捏扁"。Godot 4 提供内置的 `SoftBody3D`（基于 MeshInstance3D 的布料/软布模拟）；本文分析其真实属性与固定点系统，给出旗帜、果冻方块的完整配置，并对比 `SoftBody3D`、自研 PBD（第 30 篇）与顶点着色器位移三条实现路线。

---

## 一、三条实现路线

### 1.1 路线对比（扩写版）

| 路线 | 载体 | 适用 | 代价 | 成本 | 适用规模 | 视觉质量 |
|------|------|------|------|------|----------|----------|
| `SoftBody3D` | 内置节点 | 旗帜、披风、薄布料 | 每帧写回渲染网格，开销随顶点数增长 | **低**（零代码，参数即调） | 数百顶点 / 个位数实例 | 中（受限于 PBD 简化模型） |
| 自研 PBD | 第 30 篇的质点弹簧系统 | 需要撕裂、自定义约束的布料 | CPU 密集，需自己做渲染同步 | **高**（要写约束求解 + 顶点回写） | 上千顶点 / 数个实例 | 高（约束可完全自定义） |
| 顶点着色器位移 | Shader | 纯视觉的"软"（草、果冻抖动） | 零物理，仅视觉 | **极低**（一个材质） | 不限（GPU 承担） | 低（没有真实形变） |

> ⚠️ "成本 / 适用规模 / 视觉质量"三列是**工程选型参考**，不是实测基准；具体项目必须实测。

**先想清楚需求再选路线**：需要真实碰撞响应选前两者；只要视觉抖动，着色器最便宜。

### 1.2 选型决策

```
需要真实碰撞响应？
├─ 否 → 顶点着色器位移（1.4 节）
└─ 是 → 需要撕裂 / 自定义约束 / 布料自叠？
    ├─ 否 → SoftBody3D（第二至五节）
    └─ 是 → 自研 PBD（1.3 节）
```

### 1.3 路线二的两种落地方式

**A. `SkeletonModifier3D` 自研（推荐给骨骼驱动的布料）**

4.x 的骨骼动画有了统一的扩展点 `SkeletonModifier3D`——它是"骨骼修改器"的基类，在骨骼姿势计算之后、蒙皮之前运行，可以直接改写骨骼姿势。把它挂在 `Skeleton3D` 下，就能实现"披风/马尾随骨骼摆动"的自研物理。

```gdscript
extends SkeletonModifier3D

# 在骨骼姿势计算之后被调用，可以改写骨骼姿势
func _process_modification() -> void:
    # 在这里实现自己的约束求解：读取骨骼位置、积分、写入结果
    # get_skeleton() 拿到父级的 Skeleton3D
    pass
```

`SkeletonModifier3D`（4.3 起提供）的三个要点：

- 它的**父节点必须是 `Skeleton3D`**（`get_skeleton()` 就是取父节点）；
- 修改时机在 `AnimationMixer` 播放之后，所以动画不会覆盖你的结果；
- **`influence`（默认 `1.0`）由 `Skeleton3D` 自动施加**，所以 `_process_modification()` 里**不要自己再乘一遍 influence**，否则会叠加两次。

`modification_processed` 信号在修改完成时发出——想在同一帧读回改好的姿势，要用 `Skeleton3D.get_bone_pose()` / `get_bone_global_pose()` 在这个信号触发的时刻取。

> ⚠️ 自研路线必须自己处理**渲染同步**：骨骼路线因为最终写回的是骨骼矩阵，引擎会自动渲染；但如果你改的是顶点，网格不会自动更新。

**B. CPU 质点网格（推荐给网格布）**

直接按第 30 篇的质点-弹簧模型实现：每个顶点是一个质点，相邻顶点间连一根距离约束，用 PBD（Position Based Dynamics）迭代若干步，再把结果写回 `ArrayMesh` 的顶点缓冲。

```gdscript
# 简化示意：质点 + 距离约束的 PBD 迭代
func _solve(delta: float) -> void:
    for _i in range(solver_iterations):
        for j in range(pin_count):
            _positions[j] = _pins[j]          # 固定点
        for c in _constraints:                # 距离约束
            var delta_v := _positions[c.b] - _positions[c.a]
            var dist := delta_v.length()
            if dist < 0.0001:
                continue
            var correction := delta_v / dist * (dist - c.rest) * 0.5
            _positions[c.a] += correction
            _positions[c.b] -= correction
```

这条路线代码量大、调试难，但**唯一能给你撕裂、自碰撞、非线性布料约束**的方案。

### 1.4 引擎内建的骨骼物理方案

除了自己写，4.x 还内置了两条骨骼物理路线（都属于 `SkeletonModifier3D` 的子类）：

| 类 | 起始版本 | 做什么 | 典型用途 |
|---|---|---|---|
| `PhysicalBoneSimulator3D` | **4.3** | 为 `PhysicalBone3D` 节点提供真实的刚体模拟，并把结果写回 `Skeleton3D` | 布娃娃、头发/尾巴的刚体近似 |
| `SpringBoneSimulator3D` | **4.4** | 用弹簧模型给骨骼链施加惯性摆动，并**尝试回到原始姿势** | 马尾、耳朵、披风、触手 |

> ⚠️ **版本注意**：常被误传成"4.5+ 才有"。实测核对结果——`PhysicalBoneSimulator3D` 在 **4.3 的 `doc/classes/` 中已经存在**；`SpringBoneSimulator3D` 在 **4.3 中不存在**（HTTP 404），**4.4 起才提供**。写"这两个都是 4.5+"是不准确的。

`PhysicalBoneSimulator3D` 的关键方法（4.3 类参考）：

| 方法 | 说明 |
|---|---|
| `physical_bones_start_simulation(bones = [])` | 开始模拟；可传骨骼名数组，只模拟指定的骨骼 |
| `physical_bones_stop_simulation()` | 停止模拟 |
| `is_simulating_physics()` | 是否正在模拟 |
| `physical_bones_add_collision_exception(rid)` / `physical_bones_remove_collision_exception(rid)` | 碰撞例外 |

`SpringBoneSimulator3D` 的 API 面大得多（4.4 类参考），核心是"骨骼链 + 每关节参数"：

| 方法族 | 说明 |
|---|---|
| `set_root_bone_name()` / `set_end_bone_name()` | 定义一条骨骼链（**不支持 Y 形分叉链**） |
| `set_stiffness()` / `set_drag()` / `set_gravity()` / `set_radius()` | 整条链的刚度、阻尼、重力、关节半径 |
| `set_joint_stiffness()` / `set_joint_drag()` / `set_joint_gravity()` / `set_joint_radius()` | 逐关节细分（需先 `set_individual_config(true)`） |
| `set_stiffness_damping_curve()` / `set_drag_damping_curve()` / `set_gravity_damping_curve()` / `set_radius_damping_curve()` | 用 `Curve` 沿骨骼链分布参数 |
| `set_collision_path()` / `set_enable_all_child_collisions()` | 碰撞体（`SpringBoneCollision3D`）列表 |
| `reset()` | 按当前姿势重置模拟状态，避免动画切换瞬间"炸开" |
| `set_center_from()` / `set_center_node()` | 决定"中心"是谁（世界原点 / 某个节点 / 某根骨骼），影响什么算"移动了" |

`SpringBoneSimulator3D` 有两条明确的警告：骨骼链**不能分叉**；`SpringBoneSimulator3D` 自身被缩放会导致行为异常（父 `Skeleton3D` 与骨骼都不要缩放）。

### 1.5 路线三展开：顶点着色器位移

纯视觉方案：在顶点着色器里按噪声/正弦/伪随机偏移顶点，CPU 零开销。

```glsl
// 顶点着色器片段：按高度衰减的摆动
void vertex() {
    float phase = TIME * 2.0 + float(VERTEX.x) * 0.05;
    float falloff = clamp(1.0 - (VERTEX.y - 0.5) * 2.0, 0.0, 1.0);
    VERTEX.x += sin(phase) * 0.05 * falloff;
}
```

它的边界很清楚：**没有碰撞、没有惯性、没有与其他物体的交互**，也无法被游戏逻辑读取（除非额外把结果写回 CPU）。适合草丛、装饰性果冻、"看起来软"的道具。

---

## 二、SoftBody3D 详解

### 2.1 继承关系与数据流

```cpp
class SoftBody3D : public MeshInstance3D   // 4.3 源码，scene/3d/soft_body_3d.h
```

`SoftBody3D` **继承自 `MeshInstance3D`**：它本身就渲染一个网格，物理端模拟顶点位置，再通过渲染服务器把结果写回网格（内部辅助类 `SoftBodyRenderingServerHandler` 的 `set_vertex`/`set_normal`）。

### 2.2 真实属性清单（4.3 逐项核实）

| 属性 | 类型 | 默认值 | 作用 |
|------|------|--------|------|
| `simulation_precision` | `int` | `5`（编辑器范围 1–100） | 模拟精度（子步/迭代数），越高越稳定越贵 |
| `total_mass` | `float` | `1.0`（编辑器范围 0.01–10000） | 整个软体的总质量 |
| `linear_stiffness` | `float` | `0.5`（编辑器范围 0–1） | 线性刚度，越低越"软"；**有效区间就是 0.0–1.0** |
| `pressure_coefficient` | `float` | `0.0` | 内压（封闭网格充气效果） |
| `damping_coefficient` | `float` | `0.01`（编辑器范围 0–1） | 阻尼，抑制持续晃动 |
| `drag_coefficient` | `float` | `0.0`（编辑器范围 0–1） | 空气阻力。⚠️ 4.3 类参考明确标注：**"This value is currently unused by Godot's default physics implementation."**——Godot Physics 不用它，调它没有效果 |
| `parent_collision_ignore` | `NodePath` | `NodePath("")` | 忽略的碰撞父节点（避免与宿主自撞） |
| `collision_layer` / `collision_mask` | `int` | 都是 `1` | 与其他物理体的层/掩码 |
| `ray_pickable` | `bool` | `true` | 是否响应 `RayCast3D` |
| `disable_mode` | 枚举 | `DISABLE_MODE_REMOVE` | 进程被禁用时的行为，见 2.3 |

> ⚠️ **4.3 没有 `self_collision` 与 `collision_margin` 属性**——那是 Godot 3.x SoftBody 的属性，网上旧教程常照搬，在 4.x 会报"属性不存在"。软体自碰撞在 4.x 内置节点中不可用，需要自碰撞请走第 30 篇的自研 PBD。

> ⚠️ 官方类参考对 `SoftBody3D` 还有一句很重的提醒（原文）：**"There are many known bugs in SoftBody3D. Therefore, it's not recommended to use them for things that can affect gameplay (such as trampolines)."** —— 也就是说，别把它做成会影响玩法判定的东西（蹦床、可破坏物、关键机关）。

### 2.3 隐藏时的行为

`disable_mode` 决定软体**不可见**时的处理，两个取值（4.3 类参考原文语义）：

| 常量 | 值 | 行为 |
|---|---|---|
| `DISABLE_MODE_REMOVE` | `0`（默认） | 当 `Node.process_mode` 被设为 `PROCESS_MODE_DISABLED` 时，**从物理模拟中移除**，停止一切物理交互；节点重新被处理时**自动加回** |
| `DISABLE_MODE_KEEP_ACTIVE` | `1` | 当 `Node.process_mode` 被设为 `PROCESS_MODE_DISABLED` 时，**不影响物理模拟**（继续跑） |

关键点：判据是 `process_mode`，**不是可见性**。把节点 `visible = false` 并不会停止模拟；只有把 `process_mode` 设为 `PROCESS_MODE_DISABLED`（或用 `set_process_mode()` 禁用）才会触发这套逻辑。

这就是"不可见但仍在飘动"的旗子用 `KEEP_ACTIVE`、而"看不见就该省掉"的软体用 `REMOVE` 的原因。

### 2.4 `SoftBody3D` 的真实限制

除了 2.2 提到的属性缺失，4.x 的 `SoftBody3D` 还有几条必须知道的限制：

| 限制 | 事实 | 后果 / 对策 |
|---|---|---|
| **无自碰撞** | 4.x 内置节点没有 `self_collision` | 布料会穿过自己（围巾自叠、旗帜卷到自己身上）。需要自碰撞请走第 30 篇的自研 PBD |
| **无独立碰撞形状** | 软体直接用**网格顶点**参与碰撞，没有 `CollisionShape3D` 那样可单独调的碰撞代理 | 无法把"渲染网格"与"碰撞网格"分开；想减少碰撞成本只能降低网格顶点数 |
| **节点变换在运行时被强制接管** | 4.3 的 `SoftBody3D` 在 `NOTIFICATION_TRANSFORM_CHANGED` 里会调用 `set_as_top_level(true)` 并把 `transform` 置为单位矩阵 | **不要试图用移动/旋转 `SoftBody3D` 节点来摆放软体**——运行时你的变换会被引擎覆盖。正确做法是把 `SoftBody3D` 放在原点，用网格本身建模位置；真要整体搬动，请改父节点 |
| **网格会被复制并改造** | `_become_mesh_owner()` 会用原网格复制一份 `ArrayMesh`，加上 `ARRAY_FLAG_USE_DYNAMIC_UPDATE`、去掉压缩属性 | 你的原始网格资源不会被污染，但内存里会多一份副本；大网格要留意 |
| **渲染写回发生在渲染帧** | `_draw_soft_mesh()` 挂在 `RenderingServer` 的 `frame_pre_draw` 信号上，每渲染帧写回一次顶点与法线 | 物理步率高于渲染帧率时，中间帧的形变不会显示；顶点数据每帧都要 `mesh_surface_update_vertex_region` |
| **4.3 无法给软体施加外力** | 4.3 的 `PhysicsServer3D` 软体接口里**没有** `soft_body_apply_*` 系列；节点层也没有 `apply_point_force()` 之类 | 4.3 里软体只能被动响应重力、碰撞与 `Area3D` 的风。4.6 的 `PhysicsServer3DExtension` 已有 `_soft_body_apply_point_force` / `_soft_body_apply_central_force` / `_soft_body_apply_point_impulse` / `_soft_body_apply_central_impulse`，4.4–4.6 之间引入 |
| **与 Jolt 的共存边界** | 4.4–4.6 的 Jolt **不支持** `SoftBody3D` 与 `Area3D` 的交互（连风/重力都没有）；**4.7 起支持**，且额外支持 overlap 信号 | 见第 34 篇 3.1 节第 13 行。用 Jolt + 软体 + 风场时，先确认引擎版本 |

### 2.5 与 Jolt 的共存

`SoftBody3D` 在 Godot Physics 与 Jolt 下都能工作，但能力边界不同：

| 能力 | Godot Physics | Jolt 4.4–4.6 | Jolt 4.7 |
|---|---|---|---|
| 软体基本模拟 | 支持 | 支持 | 支持 |
| `Area3D` 的风（`wind_force_magnitude` 等） | 支持 | **不支持** | 支持 |
| `Area3D` 的重力覆盖 | 支持 | **不支持** | 支持 |
| `Area3D` 的 `body_entered` 等 overlap 信号 | **不支持**（Godot Physics 侧就不发） | 不支持 | **支持**（Jolt 比 Godot Physics 还多） |

所以"软体 + 风场"这套玩法在 Godot Physics 下可用，在 Jolt 4.4–4.6 下**风不起作用**。要么在 4.7 上用 Jolt，要么这段玩法单独用 Godot Physics 跑（但一个项目只有一个 3D 后端）。

---

## 三、固定点系统（pin）

布料要有"钉在杆上"的顶点。SoftBody3D 的固定点是**顶点索引级**的：

```gdscript
# 把顶点 0 钉在一个 Node3D 上（跟随该节点移动）
# ⚠️ 4.x 的真实签名是 set_point_pinned(point_index: int, pinned: bool,
#    attachment_path: NodePath = NodePath(""))
#    没有 pin_point / pin_point_toggle / set_pinned_points_indices 这三个方法。
soft_body.set_point_pinned(0, true, ^"Pole/Anchor")
print(soft_body.is_point_pinned(0))

# 取消固定
soft_body.set_point_pinned(0, false)
```

> 固定点跟随的 `Node3D` 是通过 `set_point_pinned()` 的**第三个参数**传入的，**没有** `spatial_attachment_path` 这个属性（那是 Godot 3.x SoftBody 的成员，4.x 已移除）。批量固定就循环调用 `set_point_pinned()`。

### 3.1 节点层完整 API（4.3 `SoftBody3D.xml` 全量）

`SoftBody3D` 暴露给脚本的方法一共 20 个，与固定点相关的只有三个：

| 方法 | 签名 | 说明 |
|------|------|------|
| `set_point_pinned` | `(point_index: int, pinned: bool, attachment_path: NodePath = NodePath(""))` | 固定 / 解固定某个顶点。第三个参数指向一个 `Node3D` 时，该顶点会跟随它移动；留空则固定在当前位置 |
| `is_point_pinned` | `(point_index: int) -> bool` | 查询某个顶点是否被固定 |
| `get_point_transform` | `(point_index: int) -> Vector3` | 取该模拟点的位置 |

其余 17 个是属性读写与碰撞例外管理：`get_physics_rid()`、`set/get_collision_layer()`、`set/get_collision_mask()`、`set/get_collision_layer_value()`、`set/get_collision_mask_value()`、`set/get_parent_collision_ignore()`、`set/get_disable_mode()`、`get_collision_exceptions()`、`add_collision_exception_with()`、`remove_collision_exception_with()`、`set/get_simulation_precision()`、`set/get_total_mass()`、`set/get_linear_stiffness()`、`set/get_pressure_coefficient()`、`set/get_damping_coefficient()`、`set/get_drag_coefficient()`、`set/is_ray_pickable()`。

> ⚠️ **`get_point_transform()` 的名字有误导性**：它返回的是 `Vector3`（一个位置），不是 `Transform3D`。而且这里有一处**类参考与实现不一致**，值得知道：
>
> - 4.3 类参考的描述是 "Returns local translation of a vertex in the surface array."（表面数组中顶点的局部位移）；
> - 但 4.3 的实现 `SoftBody3D::get_point_transform()` 实际调用的是 `PhysicsServer3D.soft_body_get_point_global_position()`，返回的是**全局位置**。
>
> 也就是说**以实现为准：它给的是全局坐标**。要拿"相对软体原点的偏移"，得自己减掉 `global_position`。

### 3.2 编辑器里的 `pinned_points` 与 `attachments`

虽然节点上没有 `spatial_attachment_path` 属性，但**编辑器检查器里能看到固定点配置**——这是 `SoftBody3D` 通过 `_get_property_list()` / `_set()` 动态暴露的一组属性（4.3 源码 `soft_body_3d.cpp`）：

| 动态属性 | 类型 | 说明 |
|---|---|---|
| `pinned_points` | `PackedInt32Array` | 被固定的顶点索引列表 |
| `attachments/<i>/point_index` | `int` | 第 i 个固定点对应的顶点索引 |
| `attachments/<i>/spatial_attachment_path` | `NodePath` | 第 i 个固定点跟随的节点路径 |
| `attachments/<i>/offset` | `Vector3` | 第 i 个固定点的偏移（相对锚点） |

所以两件事同时成立：

1. 脚本里**没有** `SoftBody3D.spatial_attachment_path` 属性（写了会报错）；
2. 但在编辑器里，你**可以直接在检查器上勾选固定点、指定锚点节点**——那条路径走的就是 `attachments/<i>/spatial_attachment_path`。

`offset` 的含义值得留意：4.3 的实现里，它记录的是**锚点节点与软体之间的相对偏移**（`attachment_node->get_global_transform().affine_inverse() * get_global_transform()` 再变换顶点位置），这样锚点移动时顶点能保持正确的相对位置。

### 3.3 Godot 3.x 有、4.x 没有的 API 对照表

网上大量软体教程是从 3.x 抄来的，其中相当一部分方法在 4.x **完全不存在**（不是改名，是没了）：

| 3.x 的写法 | 4.x 的情况 | 4.x 正确做法 |
|---|---|---|
| `pin_point(index, pin)` | C++ 层有，**脚本层未暴露** | `set_point_pinned(index, pin)` |
| `pin_point_toggle(index)` | C++ 层有，**脚本层未暴露** | `set_point_pinned(index, not is_point_pinned(index))` |
| `set_pinned_points_indices(Array)` | C++ 层有，**脚本层未暴露** | 循环调用 `set_point_pinned()` |
| `add_point(position)` | **4.x 完全不存在** | 无（4.x 软体的拓扑由网格决定，不能运行时加点） |
| `clear_points()` | **4.x 完全不存在** | 无 |
| `set_point_position(index, pos)` | **4.x 完全不存在** | 无（4.x 没有暴露"设置顶点位置"的节点 API） |
| `get_point_position(index)` | **4.x 完全不存在** | `get_point_transform(index)`（返回 `Vector3`） |
| `get_point_count()` | **4.x 完全不存在** | `mesh.get_surface_count()` / `ArrayMesh` 的顶点数组长度 |
| `set_shrinking_factor(v)` / `get_shrinking_factor()` | **节点层 4.x 没有** | 服务器层在 4.6 才有（`_soft_body_set_shrinking_factor`） |
| `set_self_collision_enabled(true)` | **4.x 完全不存在** | 无（自碰撞不可用） |
| `set_collision_margin(v)` | **4.x 完全不存在** | 无 |

写 4.x 代码时，对照这张表把 3.x 的调用逐个换掉——**直接照抄 3.x 教程的脚本会整段报错**，而不是"静默不生效"。

---

## 四、实践

### 4.1 旗帜

```gdscript
# 旗帜：细长平面网格 + 顶边两个固定点 + 适度阻尼
func make_flag() -> SoftBody3D:
    var flag := SoftBody3D.new()
    flag.mesh = preload("res://flag_mesh.obj")   # 顶点数适中的平面网格
    flag.simulation_precision = 8                # 默认值偏低的场景可上调
    flag.total_mass = 0.5
    flag.linear_stiffness = 0.3                  # 布料要"软"
    flag.damping_coefficient = 0.05              # 太高会像纸板
    flag.drag_coefficient = 0.1                  # 空气阻力让摆动衰减
    flag.parent_collision_ignore = "../FlagPole" # 不与旗杆自撞
    add_child(flag)

    flag.set_point_pinned(0, true, ^"FlagPole/Top")     # 顶边固定
    flag.set_point_pinned(1, true, ^"FlagPole/Top")
    return flag
```

### 4.2 果冻方块（内压）

```gdscript
# 封闭网格 + 内压：压扁后回弹的"果冻"
func make_jelly() -> SoftBody3D:
    var jelly := SoftBody3D.new()
    jelly.mesh = preload("res://cube_mesh.obj")  # 封闭网格
    jelly.simulation_precision = 12
    jelly.total_mass = 2.0
    jelly.linear_stiffness = 0.7                 # 偏硬
    jelly.pressure_coefficient = 1.5             # 内压撑起体积
    jelly.damping_coefficient = 0.1
    add_child(jelly)
    return jelly
```

### 4.3 与角色交互

软体与 `RigidBody3D`/`CharacterBody3D` 的碰撞通过 `collision_layer`/`collision_mask` 正常工作；需要"踩上去"的布桥，把 `disable_mode` 设为 `KEEP_ACTIVE`，并确认角色的碰撞掩码覆盖软体的层。

### 4.4 布料 / 绳索 / 橡胶的实际搭配

三类常见软体的需求差别很大，参数与拓扑应该分别设计：

| 目标 | 拓扑 | 关键参数 | 固定点 | 典型失败点 |
|---|---|---|---|---|
| **布料 / 旗帜** | 薄平面网格（几行 × 几十列） | `linear_stiffness` 低（0.2–0.4）、`damping_coefficient` 0.02–0.05、`simulation_precision` 6–10 | 顶边一整排顶点固定到一个锚点 | 顶边只固定一个点 → 布料会绕着那个点扭；应固定一整排 |
| **绳索 / 链条** | 细长网格或一串胶囊体 | `linear_stiffness` 中（0.4–0.6）、`damping_coefficient` 低（0.01–0.02） | 起点一个固定点 + 末端一个（做绳结） | 无自碰撞 → 长绳会穿过自己；端点没固定 → 整条绳飘走 |
| **橡胶 / 果冻** | **封闭**网格（球、立方体） | `pressure_coefficient` > 0（1.0–2.0）、`linear_stiffness` 偏高（0.6–0.8）、`damping_coefficient` 0.05–0.1 | 通常不固定（靠碰撞形变）或只固定底部一两个点 | 网格不封闭 → 内压没有体积可作用，看起来像一张纸 |

```gdscript
# 布料：顶边整排固定
func make_cloth(width: int, height: int) -> SoftBody3D:
	var cloth := SoftBody3D.new()
	cloth.mesh = _make_grid_mesh(width, height)
	cloth.simulation_precision = 8
	cloth.total_mass = 0.5
	cloth.linear_stiffness = 0.3       # 软
	cloth.damping_coefficient = 0.03   # 别太高，高了像纸板
	cloth.drag_coefficient = 0.1
	cloth.parent_collision_ignore = ^"../ClothPole"
	add_child(cloth)

	# 顶边（索引 0..width-1）全部固定到同一个锚点
	for x in range(width):
		cloth.set_point_pinned(x, true, ^"ClothPole/Top")
	return cloth
```

```gdscript
# 绳索：起点固定 + 末端固定
func make_rope(points: int) -> SoftBody3D:
	var rope := SoftBody3D.new()
	rope.mesh = _make_line_mesh(points)
	rope.simulation_precision = 10
	rope.linear_stiffness = 0.5
	rope.damping_coefficient = 0.015
	add_child(rope)
	rope.set_point_pinned(0, true, ^"RopeAnchor")
	rope.set_point_pinned(points - 1, true, ^"RopeTip")
	return rope
```

```gdscript
# 橡胶块：封闭网格 + 内压
func make_jelly() -> SoftBody3D:
	var jelly := SoftBody3D.new()
	jelly.mesh = preload("res://cube_mesh.obj")   # 必须封闭
	jelly.simulation_precision = 12
	jelly.total_mass = 2.0
	jelly.linear_stiffness = 0.7
	jelly.pressure_coefficient = 1.5
	jelly.damping_coefficient = 0.1
	add_child(jelly)
	return jelly
```

> 三条通用经验：① 布料**一定**用薄平面网格，厚网格会让内压参数失去意义；② 固定点要"成排"而不是"成点"；③ `damping_coefficient` 是最容易调过头的一项——太高会像纸板，太低会永久晃动。

---

## 五、性能与限制

### 5.1 成本排序

- **顶点数是第一成本**：模拟开销与顶点数成正比，旗帜用几百顶点足够，不要拿高模直接软体化；
- **`simulation_precision` 是第二成本**：精度翻倍 ≈ 耗时翻倍，先调它再调网格；
- **实例数是第三成本**：每个 `SoftBody3D` 都有自己的网格副本与模拟状态，几十个同屏软体要重新评估方案；
- **隐藏即省**：不可见的软体把 `disable_mode` 设为 `REMOVE`（注意判据是 `process_mode`，见 2.3）。

### 5.2 渲染写回的开销来源

`SoftBody3D` 的渲染写回是 CPU → GPU 的带宽消耗，来源有三处：

1. **顶点位置回写**：每个顶点一次 `set_vertex()`，写进顶点缓冲；
2. **法线回写**：每个顶点一次 `set_normal()`（八面体编码成 `uint32`）；
3. **整块缓冲上传**：`commit_changes()` 调用 `mesh_surface_update_vertex_region()`，把改过的顶点区域重新传给渲染服务器。

写回挂在 `RenderingServer` 的 `frame_pre_draw` 上，所以**每渲染帧一次**，而不是每物理步一次。这带来两个后果：

> ⚠️ 下面用 240 FPS / 60 Hz 作为算例（示意数据，未附测试环境），只为说明倍数关系。

- 物理步率高于渲染帧率时，中间帧的形变不会显示出来（视觉上"慢半拍"）；
- 渲染帧率越高，写回次数越多——如果游戏是 240 FPS 而物理是 60 Hz，写回成本是 4 倍。

顶点数多时这就是 CPU → GPU 的带宽瓶颈。**减顶点数比调参数有效得多**。

### 5.3 功能边界

- **无自碰撞**：4.x 内置节点不支持（见 2.2 与 2.4），围巾自叠等需求用第 30 篇 PBD；
- **无独立碰撞形状**：碰撞直接用网格顶点，无法把渲染网格与碰撞网格分离（见 2.4）；
- **节点变换被引擎接管**：运行时不要靠移动 `SoftBody3D` 节点来摆放它（见 2.4）；
- **4.3 无法施加外力**：`PhysicsServer3D` 软体接口里没有 `soft_body_apply_*`（见 2.4）；
- **与 Jolt 的共存边界**：4.4–4.6 的 Jolt 不支持软体与 `Area3D` 的交互，4.7 才支持（见 2.5）。

---

## 六、总结

- `SoftBody3D` 继承 `MeshInstance3D`，六个参数（precision/mass/stiffness/pressure/damping/drag）决定一切手感；其中 `drag_coefficient` 在 4.3 的默认物理实现里**根本没被使用**；
- **固定点系统**是布料玩法的核心：顶点索引级 `set_point_pinned(index, pinned, attachment_path)` + `Node3D` 锚点跟随；编辑器检查器里对应的是动态属性 `pinned_points` 与 `attachments/<i>/spatial_attachment_path`；
- 4.3 的内置节点**没有** `self_collision`/`collision_margin`（旧教程照搬会报错），自碰撞需求走第 30 篇 PBD；
- **3.x 的一整套软体 API 在 4.x 不存在**（`add_point` / `clear_points` / `set_point_position` / `get_point_position` / `get_point_count`），照抄 3.x 教程会整段报错，对照表见 3.3；
- `disable_mode` 控制进程被禁用时是否继续模拟，是最容易拿到的性能节省——但判据是 `process_mode`，不是可见性；
- 骨骼方向的自研路线已经不需要从零开始：`SkeletonModifier3D`（4.3 起）、`PhysicalBoneSimulator3D`（4.3 起）、`SpringBoneSimulator3D`（4.4 起）都是现成的扩展点。

---

## 🔗 延伸阅读

- **SoftBody3D**: <https://docs.godotengine.org/en/stable/classes/class_softbody3d.html>
- **SkeletonModifier3D**: <https://docs.godotengine.org/en/stable/classes/class_skeletonmodifier3d.html>
- **PhysicalBoneSimulator3D**: <https://docs.godotengine.org/en/stable/classes/class_physicalbonesimulator3d.html>
- **SpringBoneSimulator3D**: <https://docs.godotengine.org/en/stable/classes/class_springbonesimulator3d.html>
- **源码位置**: `scene/3d/soft_body_3d.cpp` / `scene/3d/soft_body_3d.h`（模拟与渲染写回）、`servers/physics_3d/`（软体服务器接口）
- **自研布料路线**: 见第 30 篇（质点弹簧与 PBD）

---

## 📋 下一章预告

**第 36 篇：物理调试与问题排查**

- 2D 与 3D 的性能监视器对照
- Jolt vs Godot Physics：同一场景行为不同的定位路径
- 软体专项排查：穿插、抖动、穿模
- 常见错法逐条（形状被禁用、层掩码算错、父子关系错位……）
- "现象 → 可能原因 → 验证方法"速查表

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 34 篇：Jolt Physics](/articles/34-jolt-physics.md)
**下一篇**: [第 36 篇：物理调试与问题排查](/articles/36-physics-debugging.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
