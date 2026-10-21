# 第 44 篇：骨骼动画

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 43 章 动画状态机  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

骨骼动画是 3D 角色动画的底座：动画曲线写入**骨骼姿势**，蒙皮把骨骼姿势作用到网格顶点上，
角色才会动。

本章讲清四件事：

1. `Skeleton3D` 的数据模型与**姿势 API**（局部姿势 / 全局姿势 / 姿势覆盖）
2. 骨骼与网格的绑定：`MeshInstance3D` + `Skin` + 骨骼导入
3. 骨骼扩展点：`SkeletonModifier3D`、`SkeletonIK3D`、`SkeletonProfileHumanoid`
4. 蒙皮与多通道蒙皮：GPU 蒙皮由引擎内建，4 / 8 骨骼权重通道、Blend Shape、分层叠加

> **程序化动画**（步行循环、物理驱动、动态地形适配）见第 40 篇《角色动画》的
> 「程序化动画与物理驱动」一章。

---

## 🎯 学习目标

- 掌握 `Skeleton3D` 的索引式姿势 API
- 理解局部姿势与全局姿势的区别，以及姿势覆盖（override）的用法
- 掌握骨骼与网格的绑定关系与 `Skin` 资源
- 理解 `SkeletonModifier3D` 扩展点与 `SkeletonIK3D` 的能力边界
- 了解 Godot 4.x **没有**通用 FABRIK / CCD IK 节点这一事实
- 掌握蒙皮、多骨骼权重通道与分层叠加的实现方式
- 了解骨骼 LOD 的可行做法

---

## 1. 骨骼系统基础

### 1.1 Skeleton3D 的数据模型

`Skeleton3D` 里**没有**骨骼节点。骨骼是 `Skeleton3D` 内部的一张**扁平表**，
用整数索引访问：

| API | 说明 |
|---|---|
| `get_bone_count()` | 骨骼数量 |
| `get_bone_name(idx)` / `set_bone_name(idx, name)` | 骨骼名 |
| `find_bone(name)` | 按名字查索引，**找不到返回 -1** |
| `get_bone_parent(idx)` | 父骨骼索引，无父则 -1 |
| `get_bone_children(idx)` | 子骨骼索引数组 |
| `get_bone_rest(idx)` | 静止姿势（bind pose） |
| `get_bone_global_rest(idx)` | 静止姿势（全局） |
| `localize_rests()` | 把全局静止姿势转成局部 |

骨骼层级来自**导入的模型**（glTF / FBX），运行时不能随意增删；
`add_bone()` / `remove_bone()` 等方法存在，但主要用于程序化生成骨架，常规项目不应使用。

### 1.2 姿势 API

姿势分两层：

- **局部姿势（pose）**：相对父骨骼的变换，用 `get_bone_pose()` / `set_bone_pose()` 读写
- **全局姿势（global pose）**：相对 `Skeleton3D` 节点的世界变换，用
  `get_bone_global_pose()` / `set_bone_global_pose()` 读写

```gdscript
# 骨骼姿势读写：局部姿势 vs 全局姿势
class_name SkeletonPoseAccess

extends Node3D

@export var skeleton: Skeleton3D

## 局部姿势：相对父骨骼
func get_local_pose(bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return Transform3D()
    return skeleton.get_bone_pose(idx)

func set_local_pose(bone_name: StringName, pose: Transform3D) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_pose(idx, pose)

## 分量式读写：位置 / 旋转 / 缩放分别设置
func set_bone_position(bone_name: StringName, pos: Vector3) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_pose_position(idx, pos)

func set_bone_rotation(bone_name: StringName, rot: Quaternion) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_pose_rotation(idx, rot)

func set_bone_scale(bone_name: StringName, scale: Vector3) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_pose_scale(idx, scale)

## 全局姿势：相对 Skeleton3D 节点
func get_global_pose(bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return Transform3D()
    return skeleton.get_bone_global_pose(idx)

func set_global_pose(bone_name: StringName, pose: Transform3D) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_global_pose(idx, pose)
```

> ⚠️ `set_bone_global_pose()` 的官方说明：若同时改了多根骨骼的全局姿势，
> 每次调用都会触发一次脏姿势重算，性能会明显下降。批量修改时应改用
> `set_bone_pose()`（局部姿势）并自行预计算。

### 1.3 姿势覆盖（override）

"覆盖"用于在动画姿势之上叠加一层额外修正（IK 结果、程序化偏移、调试姿态）：

```gdscript
# 全局姿势覆盖：amount 是强度，persistent 表示是否持续保持
class_name BonePoseOverride

extends Node3D

@export var skeleton: Skeleton3D

func override_bone(bone_name: StringName, pose: Transform3D, amount: float = 1.0) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    # 注意：写入的必须是「全局姿势」。
    # 若手里是世界变换，先转成全局姿势：
    #   pose = skeleton.global_transform.affine_inverse() * world_transform
    skeleton.set_bone_global_pose_override(idx, pose, amount, true)

func clear_overrides() -> void:
    skeleton.clear_bones_global_pose_override()

func get_override(bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return Transform3D()
    return skeleton.get_bone_global_pose_override(idx)
```

> **版本提示**：`Skeleton3D.set_bone_global_pose_override()` 在 **4.3 中已被标记 deprecated**，
> 新代码优先走 `SkeletonModifier3D`（见第 4 节）。4.4 仍保留该方法，只是不再推荐。

### 1.4 骨骼启用与停用

```gdscript
# 停用不参与动画的骨骼
class_name BoneCulling

extends Node3D

@export var skeleton: Skeleton3D

func set_bone_active(bone_name: StringName, active: bool) -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return
    skeleton.set_bone_enabled(idx, active)

func is_bone_active(bone_name: StringName) -> bool:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return false
    return skeleton.is_bone_enabled(idx)
```

`Skeleton3D` 的信号：

| 信号 | 触发时机 |
|---|---|
| `skeleton_updated` | 骨架数据（骨骼表）变化后 |
| `pose_updated` | 姿势更新后 |
| `bone_list_changed` | 骨骼列表变化 |
| `bone_enabled_changed` | 骨骼启用状态变化 |

---

## 2. 骨骼与网格的绑定

### 2.1 MeshInstance3D ↔ Skeleton3D

```gdscript
# 网格绑定到骨架
class_name MeshSkeletonBinding

extends Node3D

@export var mesh: MeshInstance3D
@export var skeleton: Skeleton3D

func _ready() -> void:
    if mesh and skeleton:
        # skeleton 是 NodePath：从 MeshInstance3D 出发指向 Skeleton3D
        mesh.skeleton = mesh.get_path_to(skeleton)
```

`MeshInstance3D` 上与骨骼/蒙皮相关的三个属性：

| 属性 | 类型 | 说明 |
|---|---|---|
| `mesh` | `Mesh` | 网格资源 |
| `skeleton` | `NodePath` | 指向驱动它的 `Skeleton3D` |
| `skin` | `Skin` | 该网格实例使用的蒙皮绑定（可覆盖网格自带绑定） |

### 2.2 Skin 资源

`Skin` 描述"哪些骨骼、绑定到哪些顶点权重、绑定矩阵是什么"：

| 方法 | 说明 |
|---|---|
| `add_bind(bone_idx, bind_pose)` | 添加一条绑定 |
| `add_named_bind(bone_name, bind_pose)` | 按骨骼名添加绑定 |
| `set_bind_count(n)` / `get_bind_count()` | 绑定数量 |
| `set_bind_name(idx, name)` / `get_bind_name(idx)` | 绑定的骨骼名 |
| `set_bind_bone(idx, bone_idx)` / `get_bind_bone(idx)` | 对应的骨骼索引 |
| `set_bind_pose(idx, pose)` / `get_bind_pose(idx)` | 绑定矩阵 |
| `clear_binds()` | 清空 |

```gdscript
# 运行时构建 Skin：把网格的蒙皮绑定到另一套骨架
class_name SkinRebinder

extends Node3D

@export var mesh: MeshInstance3D
@export var skeleton: Skeleton3D

func rebind_to_skeleton(target_skeleton: Skeleton3D) -> void:
    var skin := Skin.new()
    for i in skeleton.get_bone_count():
        var bone_name := skeleton.get_bone_name(i)
        var target_idx := target_skeleton.find_bone(bone_name)
        if target_idx == -1:
            continue
        skin.add_named_bind(bone_name, skeleton.get_bone_rest(i))
    mesh.skin = skin
    mesh.skeleton = mesh.get_path_to(target_skeleton)
```

> `Skeleton3D` 还提供了 `create_skin_from_rest_transforms()` 与 `register_skin()`，
> 用于从静止姿势直接生成 `Skin` 并注册到骨架上。

### 2.3 骨骼导入与 glTF 层级

骨骼层级**来自导入的模型文件**，不在代码里手工拼：

- 推荐用 **glTF 2.0 / GLB** 作为交换格式（Godot 对 glTF 的支持最完整）
- 导入后场景里会出现 `Skeleton3D` + `MeshInstance3D`（网格已带上 `Skin`）
- 导入选项里可以配置"骨骼作为节点 / 骨骼作为纯姿势数据"（Create Bone Attachment 等）
- 人形模型建议以 **T-pose** 导入：Godot 4.x 的骨骼混合会优先选择"离静止姿势最近"的旋转路径，
  T-pose 能显著减少多段动画混合时骨骼穿过身体的问题

---

## 3. 骨骼附加与跟随

### 3.1 BoneAttachment3D

需要让某个节点（武器、粒子、特效）跟随某根骨骼运动时，用 `BoneAttachment3D`，
而不是每帧手算变换：

```gdscript
# BoneAttachment3D：让节点跟随骨骼
class_name BoneAttacher

extends Node3D

@export var skeleton: Skeleton3D

func attach(target: Node3D, bone_name: StringName) -> BoneAttachment3D:
    var attachment := BoneAttachment3D.new()
    attachment.bone_name = bone_name
    skeleton.add_child(attachment)
    target.reparent(attachment)
    return attachment

## 如果骨骼不在本骨架下，可以指向外部骨架
func attach_external(target: Node3D, external: Skeleton3D, bone_name: StringName) -> BoneAttachment3D:
    var attachment := BoneAttachment3D.new()
    attachment.bone_name = bone_name
    attachment.use_external_skeleton = true
    attachment.external_skeleton = external.get_path()
    skeleton.add_child(attachment)
    target.reparent(attachment)
    return attachment
```

`BoneAttachment3D` 的成员：

| 成员 | 说明 |
|---|---|
| `bone_name` | 跟随的骨骼名 |
| `bone_idx` | 骨骼索引（只读，由 `bone_name` 同步） |
| `override_pose` | 是否覆盖骨骼姿势 |
| `use_external_skeleton` | 是否使用外部骨架 |
| `external_skeleton` | 外部骨架的 NodePath |

---

## 4. 骨骼扩展点：SkeletonModifier3D

### 4.1 扩展点机制

`SkeletonModifier3D` 是 `Node3D`，**必须是 `Skeleton3D` 的子节点**。官方描述：

> This node should be used to implement **custom IK solvers, constraints, or skeleton physics**.

机制要点：

| 事项 | 说明 |
|---|---|
| 执行时机 | 若场景里有 `AnimationMixer`，修改**总是在播放之后**执行 |
| 扩展点 | 重写虚函数 `_process_modification()` |
| 取得骨架 | `get_skeleton()` 返回父级 `Skeleton3D` |
| 权重 | `influence`（0~1）由 `Skeleton3D` **自动**应用到修改器写入的所有姿势上，修改器自己**不要**再插值 |
| 开关 | `active` 为 false 时不执行 |
| 完成通知 | 信号 `modification_processed`（此刻读 `get_bone_pose()` 才是修改后的结果） |

### 4.2 自定义修改器示例

```gdscript
# 自定义骨骼修改器：把某根骨骼"钉"到目标位置
class_name PinBoneModifier

extends SkeletonModifier3D

@export var bone_name: StringName = &"Hand"
@export var target: Node3D

func _process_modification() -> void:
    # _process_modification 里只写 100% 的结果，不要自己乘 influence
    var skeleton := get_skeleton()
    if skeleton == null or target == null:
        return

    var idx := skeleton.find_bone(bone_name)
    if idx == -1:
        return

    # 目标位置换算成全局姿势
    var desired_global := skeleton.global_transform.affine_inverse() * target.global_transform

    # 保持原朝向，只改位置
    var current := skeleton.get_bone_global_pose(idx)
    desired_global.basis = current.basis

    skeleton.set_bone_global_pose_override(idx, desired_global, 1.0, true)
```

---

## 5. IK 的真实实现方式

### 5.1 SkeletonIK3D：只有两骨 IK

Godot 4.x 内置的 IK 节点只有 **`SkeletonIK3D`**，它做的是**两骨 IK**（把末端骨骼放到目标位置）：

| 成员 | 说明 |
|---|---|
| `root_bone` | 根骨骼（链的起点） |
| `tip_bone` | 末端骨骼（链的终点） |
| `target` | 目标 `Transform3D` |
| `target_node` | 目标节点路径（填了它就用节点的实际变换） |
| `interpolation` | 插值系数 0~1 |
| `max_iterations` | 最大迭代次数 |
| `min_distance` | 最小生效距离 |
| `magnet` / `use_magnet` | 磁吸目标 |
| `override_tip_basis` | 是否覆盖末端骨骼朝向 |

方法：`start()` / `stop()` / `is_running()` / `get_parent_skeleton()`。

```gdscript
# 使用 SkeletonIK3D 做两骨 IK
class_name TwoBoneIKUsage

extends Node3D

@export var ik: SkeletonIK3D
@export var target: Node3D

func _ready() -> void:
    if ik and target:
        # target_node 是 NodePath 属性，按"相对于 SkeletonIK3D 自身"解析
        ik.target_node = ik.get_path_to(target)
        ik.start()

func _exit_tree() -> void:
    if ik:
        ik.stop()
```

### 5.2 Godot 4.x 没有通用 FABRIK / CCD 节点

必须讲清楚的事实：

> **Godot 4.x（4.0 ~ 4.5）没有通用的 FABRIK / CCD IK 节点。**
> 内置的 `SkeletonIK3D` 只能解**两骨链**（root → tip）。
> 多骨链（3 骨以上）、CCD、FABRIK、末端旋转对齐（pole / twist）在 4.x 里
> **没有现成节点**，需要自己实现。

可行路径：

| 路径 | 说明 |
|---|---|
| ① 自研 `SkeletonModifier3D` | 在 `_process_modification()` 里实现 CCD / FABRIK 求解，写回骨骼姿势（推荐） |
| ② 骨骼拆成多段两骨 IK | 把长链拆成若干两骨段，逐段求解，精度换性能 |
| ③ 使用第三方插件 | Godot Asset Library 上有 IK 插件，多数也是基于 `SkeletonModifier3D` |

> **不要**把 `SkeletonIK3D` 当成 3.x 遗留：它在 Godot **4.3 / 4.4 / master 分支中仍然存在**，
> 只是能力有限（仅两骨）。

### 5.3 4.6 起的原生 IK 框架

Godot 在 4.6 引入了一套**原生 IK 框架**，建立在重构后的 `SkeletonModifier3D` 之上：

| 类 | 作用 |
|---|---|
| `IKModifier3D` | IK 修改器的基类（继承 `SkeletonModifier3D`） |
| `TwoBoneIK3D` | 两骨 IK（`SkeletonIK3D` 的继任者） |
| `FABRIK3D` | FABRIK 求解器 |
| `CCDIK3D` | CCD 求解器 |
| `SplineIK3D` | 样条 IK |
| `JacobianIK3D` | 雅可比 IK |

> ⚠️ **版本提示**：以上类在 **4.4 与 4.5 中不存在**（`doc/classes` 检索零命中），
> 只在 master / 4.6+ 可用。写 4.x 项目时请用 `SkeletonModifier3D` 自研，或继续用 `SkeletonIK3D`。

---

## 6. 人形骨架规范

`SkeletonProfileHumanoid` 描述一套**标准人形骨骼命名与分组**（Godot 4.4 引入）：

| 成员 | 说明 |
|---|---|
| `root_bone` | 根骨骼名 |
| `bone_size` | 骨骼数量 |
| `group_size` | 分组数量 |
| `scale_base_bone` | 用于计算比例的基准骨骼 |

它提供的是**命名约定**（头、脊柱、左右臂、左右腿等分组与标准名），
让不同来源的人形模型可以被同一套代码识别——例如"把左手 IK 到剑柄"这类逻辑，
可以按标准名而不是按美术自定义名来查找骨骼。

```gdscript
# 用人形骨架规范查找标准骨骼
class_name HumanoidBoneLookup

extends Node3D

@export var skeleton: Skeleton3D
@export var profile: SkeletonProfileHumanoid

func find_by_profile(bone_name: StringName) -> int:
    if skeleton == null:
        return -1
    return skeleton.find_bone(bone_name)
```

---

## 7. 蒙皮与多通道蒙皮

### 7.1 GPU 蒙皮由引擎内建

Godot 的蒙皮是**引擎内建的 GPU 蒙皮**，不是脚本实现的：

- 顶点着色阶段由引擎的蒙皮管线处理，脚本**不参与**逐顶点计算
- `Skeleton3D` 的姿势变化 → 渲染服务器拿到新的骨骼矩阵 → 顶点按权重混合
- 脚本只需负责"写骨骼姿势"，不需要也不应该去算顶点位置

> 常见误解："能不能用 compute shader 自己做蒙皮" —— 引擎的 `RenderingServer` **没有**公开的
> `compute_pipeline_create` 之类的接口，Godot 4.x 的着色器也不支持 `@compute_shader` 注解。
> 自定义蒙皮要么走引擎内建管线，要么把模型转成其它形态（如 `MultiMesh`）。

### 7.2 顶点骨骼权重：4 / 8 通道

Godot 的网格顶点格式里，骨骼影响数量有**两档**：

| 通道数 | 条件 | 说明 |
|---|---|---|
| 4 | 默认 | 每顶点 4 个骨骼索引 + 4 个权重（`ARRAY_BONES` / `ARRAY_WEIGHTS` 各 4 个数） |
| 8 | 网格带 `ARRAY_FLAG_USE_8_BONE_WEIGHTS` 标记 | 每顶点 8 个骨骼索引 + 8 个权重，**索引与权重数组长度翻倍** |

这就是 Godot 4.x 意义上的**多通道蒙皮**：一个顶点可以同时受 8 根骨骼影响，
用于解决肩关节、胯部等大形变区域的"塌陷"问题。

| `Mesh` 常量 | 值 | 含义 |
|---|---|---|
| `Mesh.ARRAY_BONES` | 10 | 骨骼索引 |
| `Mesh.ARRAY_WEIGHTS` | 11 | 骨骼权重 |
| `Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS` | 134217728 | 标记每顶点最多 8 根骨骼影响 |

导入时是否启用 8 通道，取决于 DCC 工具导出的蒙皮数据与导入选项；
导出 glTF 时目标平台不支持 8 权重会被压回 4 权重。

### 7.3 Blend Shape

表情、肌肉形变等通过 **Blend Shape** 实现：

- 网格资源上带有一组 blend shape（形状键）
- 动画用 `Animation.TYPE_BLEND_SHAPE` 轨道驱动它们：

```gdscript
# 用 TYPE_BLEND_SHAPE 轨道驱动表情
class_name BlendShapeDriver

extends Node

@export var player: AnimationPlayer

func build_face_animation() -> void:
    var anim := Animation.new()
    anim.length = 2.0

    # Blend Shape 轨道：路径形如 "MeshInstance3D:blend_shape_name"
    var track := anim.add_track(Animation.TYPE_BLEND_SHAPE)
    anim.track_set_path(track, NodePath("MeshInstance3D:smile"))
    anim.track_insert_key(track, 0.0, 0.0)
    anim.track_insert_key(track, 0.2, 1.0)

    var lib := player.get_animation_library("")
    if lib:
        lib.add_animation(&"smile", anim)
```

### 7.4 多通道叠加：Filter / Add2 / Blend2

"一个角色同时受多层影响"（上半身叠加下半身、加法表情）在 Godot 4.x 里有三种叠加通道：

| 通道 | 机制 | 语义 |
|---|---|---|
| **混合（Mix）** | `AnimationNodeBlend2` / `Blend3`，参数 `blend_amount` | 按权重线性插值（MIX） |
| **加法（Add）** | `AnimationNodeAdd2` / `Add3`，参数 `add_amount` | 把一份动画**加**到另一份上（ADD），取值 `[-1, 1]` |
| **过滤（Filter）** | `AnimationNode.filter_enabled` + `set_filter_path()` | 决定哪些**轨道**（骨骼）参与本次混合 |

「MODULATE / ADD」这两个说法对应的是**混合语义**而非 Godot 的类名：
Godot 4.x 里没有 `AnimationNodeModulate` 之类的类，
"调制"效果由 `AnimationNodeBlend2`（MIX 语义）承担，
"叠加"效果由 `AnimationNodeAdd2`（ADD 语义）承担。
详细用法见第 39 篇《动画混合》第 9 节。

> ⚠️ `AnimationMixer.deterministic = true`（`AnimationTree` 默认）时，
> `AnimationNodeAdd2` / `Add3` / `Sub2` 或权重大于 1.0 的混合**可能产生非预期结果**，
> 官方类参考在 `deterministic` 条目下明确提示这一点。

---

## 8. 骨骼 LOD

Godot 4.x **没有**内置的"骨骼 LOD"开关（不存在按距离自动降骨骼数的机制）。
可行做法有两类：

### 8.1 停用次要骨骼

```gdscript
# 远处角色停用次要骨骼，减少姿势求值
class_name SkeletonBoneLOD

extends Node3D

@export var skeleton: Skeleton3D
@export var lod_distances: Array[float] = [20.0, 50.0, 100.0]
@export var keep_bones: Array[StringName] = [
    &"Root", &"Hips", &"Spine", &"Chest", &"Head",
    &"LeftUpperArm", &"RightUpperArm",
    &"LeftUpperLeg", &"RightUpperLeg"
]

func update_lod(camera_position: Vector3) -> void:
    var distance := camera_position.distance_to(skeleton.global_position)

    var lod := 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod = i + 1

    for i in skeleton.get_bone_count():
        var bone_name := skeleton.get_bone_name(i)
        var keep := lod == 0 or _is_keep_bone(bone_name)
        if skeleton.is_bone_enabled(i) != keep:
            skeleton.set_bone_enabled(i, keep)

func _is_keep_bone(bone_name: String) -> bool:
    for keep in keep_bones:
        if bone_name.contains(String(keep)):
            return true
    return false
```

> ⚠️ 示意数据（未附测试环境）：`lod_distances = [20, 50, 100]` 是示例值，
> 必须按角色尺寸、镜头 FOV 与目标机型实测调整。

### 8.2 网格级 LOD

`GeometryInstance3D`（`MeshInstance3D` 的基类）自带可见性范围 LOD：

| 属性 | 说明 |
|---|---|
| `visibility_range_begin` / `visibility_range_end` | 可见性范围起止 |
| `visibility_range_begin_margin` / `visibility_range_end_margin` | 边缘余量 |
| `visibility_range_fade_mode` | 淡出模式 |

把角色的高模 / 低模做成两套 `MeshInstance3D`，用可见性范围切换，
是比"运行时改骨骼"更稳妥的降级方案。

---

## 📝 本章总结

### 核心要点

1. **`Skeleton3D` 用索引访问骨骼**，`find_bone()` 找不到返回 -1
2. **局部姿势**用 `get_bone_pose()` / `set_bone_pose()`，**全局姿势**用 `get_bone_global_pose()`
3. **姿势覆盖**用 `set_bone_global_pose_override()`（4.3 起 deprecated），新代码走 `SkeletonModifier3D`
4. **`BoneAttachment3D`** 让节点跟随骨骼，避免手算变换
5. **`SkeletonModifier3D` 是骨骼扩展点**，官方定位就是"自定义 IK / 约束 / 骨骼物理"
6. **Godot 4.x 没有通用 FABRIK / CCD 节点**，只有两骨的 `SkeletonIK3D`；4.6+ 才有原生 IK 框架
7. **GPU 蒙皮由引擎内建**，脚本不参与逐顶点计算；顶点支持 4 或 8 骨骼权重通道
8. **多通道叠加**靠 `Blend2`（MIX）/ `Add2`（ADD）/ Filter（轨道级）

### 关键术语

| 术语 | 解释 |
|------|------|
| Skeleton3D | 骨骼容器，索引式访问 |
| Pose | 骨骼姿势，分局部与全局 |
| Bone Rest | 静止姿势 / bind pose |
| Override | 姿势覆盖，用于叠加修正 |
| Skin | 蒙皮绑定资源 |
| BoneAttachment3D | 跟随骨骼的附加节点 |
| SkeletonModifier3D | 骨骼修改扩展点 |
| SkeletonIK3D | 两骨 IK 节点 |
| Blend Shape | 网格形状键，用于表情与形变 |
| Bone Weight | 顶点受骨骼影响的权重 |

---

## 🔗 延伸阅读

- **官方文档 · Skeleton3D**: <https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html>
- **官方文档 · BoneAttachment3D**: <https://docs.godotengine.org/en/stable/classes/class_boneattachment3d.html>
- **官方文档 · SkeletonModifier3D**: <https://docs.godotengine.org/en/stable/classes/class_skeletonmodifier3d.html>
- **官方文档 · SkeletonIK3D**: <https://docs.godotengine.org/en/stable/classes/class_skeletonik3d.html>
- **官方文档 · SkeletonProfileHumanoid**: <https://docs.godotengine.org/en/stable/classes/class_skeletonprofilehumanoid.html>
- **官方文档 · Skin**: <https://docs.godotengine.org/en/stable/classes/class_skin.html>
- **官方文档 · Mesh**: <https://docs.godotengine.org/en/stable/classes/class_mesh.html>
- **官方文档 · 导入 3D 场景**: <https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/index.html>
- **官方博客 · Design of the Skeleton Modifier 3D**: <https://godotengine.org/article/design-of-the-skeleton-modifier-3d/>
- **源码位置**: `scene/3d/skeleton_3d.cpp`、`scene/3d/bone_attachment_3d.cpp`、
  `scene/3d/skeleton_modifier_3d.cpp`、`scene/resources/skin.cpp`、`scene/resources/mesh.cpp`

---

## 📋 上下篇导航

**上一篇**: [第 43 篇：动画状态机](/articles/43-animation-state-machine.md)
**下一篇**: [第 42 篇：动画性能优化](/articles/42-particle-system.md)

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

*写作时间：2026-03-21*  
*字数：约 2,600 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
