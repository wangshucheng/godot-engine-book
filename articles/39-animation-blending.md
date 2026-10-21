# 第 39 篇：动画混合

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 38 章 动画控制器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

动画混合是游戏开发中实现流畅动画过渡和复杂动画效果的关键技术。通过动画混合，开发者可以将多个动画无缝地结合在一起，创造出更加自然和生动的角色动作。

Godot 的混合能力集中在 `AnimationNodeBlendTree`（混合树）里：树中挂着 `AnimationNodeBlend2`、
`AnimationNodeAdd2`、`AnimationNodeBlend3` 等混合节点，以及 `AnimationNodeBlendSpace1D` /
`AnimationNodeBlendSpace2D`（混合空间）。本章讲清楚这些节点**怎么连线、参数怎么写**，
以及"上半身 / 下半身分层"在 Godot 4.x 里的**真实实现方式**。

---

## 🎯 学习目标

- 理解动画混合的基本概念
- 掌握 `AnimationNodeBlend2` / `AnimationNodeAdd2` / `AnimationNodeBlend3` 的连线和参数
- 掌握 1D / 2D 混合空间（BlendSpace）的差异与三角剖分
- 熟悉 `AnimationLibrary` 的键名规则
- 掌握 Godot 4.x 的分层混合与轨道过滤机制
- 了解混合的性能优化手段

---

## 1. 动画混合基础

### 1.1 动画混合类型

```
动画混合类型:
┌─────────────────────────────────────────────────────────────┐
│                      动画混合类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 线性混合（Blend2 / Blend3）：按权重线性插值            │
│  2. 加法混合（Add2 / Add3）：把一份动画叠加到另一份上      │
│  3. 差值混合（Sub2）：从基础动画中减去另一份                 │
│  4. 时间同步混合（AnimationNodeSync 基类）：统一推进时间    │
│  5. 一次性混合（OneShot）：播一次再淡出                     │
│  6. 条件切换（Transition）：多输入之间按请求切换            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画混合流程

```
动画混合处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画混合处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationTree 求值节点图                                │
│  2. 每个混合节点按自己的权重组合各输入                       │
│  3. 组合后的属性值写回骨骼 / 节点属性                        │
│  4. AnimationNodeBlendTree 把结果送到 output 节点            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画混合参数

```gdscript
# 动画混合参数
class_name AnimationBlendParameters

@export var blend_weight: float = 0.5
@export var blend_mode: int = 0  # 0: linear, 1: add, 2: multiply
@export var blend_duration: float = 0.5

func _ready():
    # 初始化参数
    blend_weight = 0.5
    blend_mode = 0
    blend_duration = 0.5

func update_parameters():
    # 更新参数
    blend_weight = $CharacterBody2D.velocity.length() / 5.0
    blend_mode = Input.get_action_strength("blend_mode")
    blend_duration = Input.get_action_strength("blend_duration")
```

---

## 2. AnimationNodeBlend2

### 2.1 基础 AnimationNodeBlend2

```gdscript
# 基础 AnimationNodeBlend2
class_name BasicAnimationNodeBlend2

extends AnimationNodeBlend2

# AnimationNodeBlend2 在 Godot 4.x 里没有任何 <members>：
# 没有 set_input()、没有 set_blend_amount()、也没有 blend_amount 属性。
# 它只是 BlendTree 里的一个"有两个输入的混合器"，混合量是 AnimationTree 的参数。

@export var input_a: AnimationNode
@export var input_b: AnimationNode

func _ready():
    # AnimationNode 的输入端口用 add_input() / set_input_name() 声明，
    # 不是 set_input(index, node)。
    if input_a:
        add_input("in")
        set_input_name(0, "in")
    if input_b:
        add_input("blend")
        set_input_name(1, "blend")
```

> **重要更正**：Godot 4.x 的 `AnimationNode` 只提供
> `add_input(name)` / `remove_input(index)` / `set_input_name(index, name)` /
> `get_input_name(index)` / `get_input_count()` / `find_input(name)`。
> **没有 `set_input(index, node)`**——节点的连线是在 `AnimationNodeBlendTree` 里用
> `connect_node()` 完成的，不是往节点里"塞节点"。

### 2.2 混合量：写参数路径

`AnimationNodeBlend2` 的混合量是 **AnimationTree 的参数**，参数名为 `blend_amount`：

```gdscript
# AnimationNodeBlend2 的混合量只能通过 AnimationTree 的参数路径写入
class_name AnimationNodeBlend2Parameters

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"eye_blend"

func _ready():
    set_blend_amount(0.5)

# parameters/<节点名>/blend_amount
func set_blend_amount(value: float) -> void:
    tree.set("parameters/%s/blend_amount" % node_name, clampf(value, 0.0, 1.0))

func get_blend_amount() -> float:
    return float(tree.get("parameters/%s/blend_amount" % node_name))

func update_parameter() -> void:
    var value = $CharacterBody2D.velocity.length() / 5.0
    set_blend_amount(value)
```

> **注意**：`AnimationNode.set_parameter(name, value)` 确实存在，但那是"节点自己的本地内存"
> （供自定义节点在 `_process()` 里存取），**不是**混合量。混合量只能走
> `tree.set("parameters/<节点名>/blend_amount", v)`。
> 官方文档给出的写法正是：
> `animation_tree.set("parameters/eye_blend/blend_amount", 1.0)`。

### 2.3 混合量的取值范围

`AnimationNodeBlend2` 的混合量常规取值为 `[0.0, 1.0]`：0 全是输入 A，1 全是输入 B。
超出 `[0, 1]` 可以做放大 / 反向混合，但官方类参考明确建议：
**要做这类效果请用 `AnimationNodeAdd2`**（Add2 的加法量取值范围是 `[-1.0, 1.0]`）。

---

## 3. AnimationNodeAdd2

### 3.1 基础 AnimationNodeAdd2

```gdscript
# 基础 AnimationNodeAdd2
class_name BasicAnimationNodeAdd2

extends AnimationNodeAdd2

@export var input_a: AnimationNode
@export var input_b: AnimationNode

func _ready():
    # Add2 的两个输入端口在编辑器里叫 "in" 与 "add"
    if input_a:
        add_input("in")
        set_input_name(0, "in")
    if input_b:
        add_input("add")
        set_input_name(1, "add")
```

`AnimationNodeAdd2` 的官方语义：

- 加法量 **大于 1.0**：`"in"` 端口的动画与 `"add"` 端口动画的**放大版**混合
- 加法量 **小于 0.0**：`"in"` 端口的动画与 `"add"` 端口动画的**反向版**混合

### 3.2 加法量：写参数路径

`AnimationNodeAdd2` 的加法量参数名是 `add_amount`（注意与 Blend2 的 `blend_amount` 不同）：

```gdscript
# AnimationNodeAdd2 的加法量：parameters/<节点名>/add_amount
class_name AnimationNodeAdd2Parameters

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"additive"

func _ready():
    set_add_amount(1.0)

func set_add_amount(value: float) -> void:
    tree.set("parameters/%s/add_amount" % node_name, clampf(value, -1.0, 1.0))

func get_add_amount() -> float:
    return float(tree.get("parameters/%s/add_amount" % node_name))

func update_parameter() -> void:
    var value = $CharacterBody2D.velocity.length() / 5.0
    set_add_amount(value)
```

---

## 4. AnimationNodeBlend3

### 4.1 基础 AnimationNodeBlend3

```gdscript
# 基础 AnimationNodeBlend3
class_name BasicAnimationNodeBlend3

extends AnimationNodeBlend3

@export var input_base: AnimationNode
@export var input_minus: AnimationNode
@export var input_plus: AnimationNode

func _ready():
    # Blend3 有三个输入：基础、-blend、+blend
    if input_base:
        add_input("in")
        set_input_name(0, "in")
    if input_minus:
        add_input("-blend")
        set_input_name(1, "-blend")
    if input_plus:
        add_input("+blend")
        set_input_name(2, "+blend")
```

`AnimationNodeBlend3` 的官方语义：三个输入分别是
「基础动画」「混合量为负时使用的动画」「混合量为正时使用的动画」，
混合量常规取值范围为 `[-1.0, 1.0]`；超出该范围做放大混合时建议改用 `AnimationNodeAdd3`。

### 4.2 混合量：写参数路径

```gdscript
# AnimationNodeBlend3 的混合量：parameters/<节点名>/blend_amount
class_name AnimationNodeBlend3Parameters

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"blend3"

func _ready():
    set_blend_amount(0.0)

func set_blend_amount(value: float) -> void:
    tree.set("parameters/%s/blend_amount" % node_name, clampf(value, -1.0, 1.0))

func get_blend_amount() -> float:
    return float(tree.get("parameters/%s/blend_amount" % node_name))

func update_parameter() -> void:
    var value_x = $CharacterBody2D.velocity.x / 5.0
    set_blend_amount(value_x)
```

---

## 5. 高级动画混合技术

### 5.1 分层动画混合

Godot 4.x 没有 Unity 那样的"Animation Layer / Avatar Mask"。**上半身 / 下半身分层**
在 Godot 里的标准做法是两条路线：

| 方案 | 做法 | 适用 |
|---|---|---|
| 节点级叠加 | `AnimationNodeBlendTree` 中把下半身动画接到 `Blend2` 的基础输入，上半身动画接到 `Add2` 的 `add` 端口，用 `add_amount` 控制强度 | 上半身是"附加"动作（射击、招手） |
| 轨道级过滤 | 给混合节点开 **Filter**，只让部分轨道（骨骼）通过 | 两份动画都是"完整"动作，需要只取某几根骨骼 |

轨道级过滤是 Godot 4.x 的真实机制，详见第 9 节。

```gdscript
# 分层动画混合：下半身为基础，上半身用加法叠加
class_name LayeredAnimationBlending

extends Node

@export var tree: AnimationTree

# 混合树里的节点名（与编辑器里显示的一致）
@export var lower_node: StringName = &"lower_body"
@export var upper_node: StringName = &"upper_body"
@export var additive_node: StringName = &"additive"

func set_upper_weight(weight: float) -> void:
    # Add2 的加法量
    tree.set("parameters/%s/add_amount" % additive_node, clampf(weight, 0.0, 1.0))

func set_lower_weight(weight: float) -> void:
    # Blend2 的混合量
    tree.set("parameters/%s/blend_amount" % lower_node, clampf(weight, 0.0, 1.0))
```

### 5.2 时间同步混合

`AnimationNodeBlend2` / `Add2` / `Blend3` 都继承自 `AnimationNodeSync`，
该基类保证这些节点**共享同一个时间轴**，避免各走各的相位。

```gdscript
# 时间同步混合：AnimationNodeSync 子类共享时间轴
class_name TimeSyncedBlending

extends Node

@export var primary_animation: AnimationPlayer
@export var secondary_animation: AnimationPlayer
@export var sync_offset: float = 0.0

func _ready():
    # 连接信号（参数类型是 StringName）
    primary_animation.animation_started.connect(_on_primary_started)
    primary_animation.animation_finished.connect(_on_primary_finished)

func _on_primary_started(anim_name: StringName):
    # 同步开始次要动画
    if secondary_animation and secondary_animation.has_animation(anim_name):
        secondary_animation.play(anim_name)
        secondary_animation.seek(primary_animation.current_animation_position + sync_offset)

func _on_primary_finished(anim_name: StringName):
    # 同步结束次要动画
    if secondary_animation:
        secondary_animation.stop()

func update_sync():
    # 更新同步偏移
    if primary_animation.is_playing() and secondary_animation.is_playing():
        var primary_pos = primary_animation.current_animation_position
        var secondary_pos = secondary_animation.current_animation_position
        sync_offset = primary_pos - secondary_pos
```

### 5.3 权重动画混合

```gdscript
# 权重动画混合：自行计算权重，写进混合节点参数
class_name WeightedAnimationBlending

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"blend3"
@export var animations: Array = []
@export var weights: Array = []

func _ready():
    # 初始化权重
    for i in range(animations.size()):
        weights.append(0.0)

func update_weights():
    # 更新权重
    var total_weight = 0.0
    for i in range(animations.size()):
        weights[i] = get_animation_weight(i)
        total_weight += weights[i]

    # 归一化权重
    if total_weight > 0.0:
        for i in range(weights.size()):
            weights[i] /= total_weight

func get_animation_weight(index: int) -> float:
    # 根据条件计算权重
    match index:
        0:  # Idle
            return max(0.0, 1.0 - $CharacterBody2D.velocity.length() / 5.0)
        1:  # Walk
            return clamp($CharacterBody2D.velocity.length() / 5.0, 0.0, 1.0)
        2:  # Run
            return clamp(($CharacterBody2D.velocity.length() - 3.0) / 2.0, 0.0, 1.0)
        _:
            return 0.0

func apply_weights() -> void:
    # 把归一化后的权重写进混合节点参数
    tree.set("parameters/%s/blend_amount" % node_name, weights[2] - weights[1])
```

---

## 6. 动画混合优化

### 6.1 动画混合缓存

```gdscript
# 动画混合缓存：缓存的是 AnimationLibrary 资源
class_name AnimationBlendCache

var _libraries: Dictionary = {}

func get_library(key: StringName) -> AnimationLibrary:
    if _libraries.has(key):
        return _libraries[key]

    var lib := AnimationLibrary.new()
    var anim := Animation.new()
    anim.length = 1.0

    # 用 TYPE_VALUE 轨道做一个最简单的淡入淡出示例
    var track := anim.add_track(Animation.TYPE_VALUE)
    anim.track_set_path(track, NodePath("Sprite2D:modulate:a"))
    anim.track_insert_key(track, 0.0, 1.0)
    anim.track_insert_key(track, 1.0, 0.0)
    lib.add_animation(key, anim)

    _libraries[key] = lib
    return lib

func clear_cache() -> void:
    _libraries.clear()
```

> **更正**：Godot 4.x **没有** `AnimationBlend` 这个类（那是 3.x 的遗留）。
> 4.x 里"混合"是 `AnimationNodeBlend2` / `Add2` / `Blend3` 这些**资源**，
> 它们被挂在 `AnimationNodeBlendTree` 上；动画本身存放在 `AnimationLibrary` 里。

### 6.2 动画混合LOD

```gdscript
# 动画混合LOD：按距离切换到更简单的混合结构
class_name AnimationBlendLOD

@export var tree: AnimationTree
@export var lod_distances: Array = [10, 30, 50]

# 远距离时把混合权重固定成"只有下半身"的简化状态
@export var lod_blend_amount: Array[float] = [1.0, 0.5, 0.0]
@export var node_name: StringName = &"locomotion"

func update_lod(camera_position: Vector2, character: Node2D):
    var distance = camera_position.distance_to(character.global_transform.origin)

    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1

    lod_index = min(lod_index, lod_blend_amount.size() - 1)
    tree.set("parameters/%s/blend_amount" % node_name, lod_blend_amount[lod_index])
```

### 6.3 动画混合压缩

```gdscript
# 动画混合压缩：减少混合树里同时参与求值的输入数
class_name AnimationBlendCompressor

@export var tree: AnimationTree
@export var max_inputs: int = 2

# AnimationNodeBlendTree 的连接关系可在运行时增删：
# disconnect_node(input_node, input_index) 断开某个输入
func compress_blend(node_name: StringName, input_indices: Array[int]) -> void:
    var blend_tree := tree.tree_root as AnimationNodeBlendTree
    if blend_tree == null:
        return
    for idx in input_indices:
        if idx >= max_inputs:
            blend_tree.disconnect_node(node_name, idx)
```

---

## 7. 实践：角色动画混合

### 7.1 基础角色动画混合

```gdscript
# 基础角色动画混合：BlendTree 的连线在编辑器里完成，脚本只写混合量
class_name CharacterAnimationBlending

extends Node2D

@export var tree: AnimationTree
@export var blend_node_name: StringName = &"locomotion"

func _ready():
    tree.active = true

func update_blending():
    var speed = $CharacterBody2D.velocity.length()
    var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
    # 混合量走参数路径
    tree.set("parameters/%s/blend_amount" % blend_node_name, blend_amount)
```

### 7.2 骨骼动画混合

```gdscript
# 骨骼动画混合
class_name SkeletonAnimationBlending

extends Node3D

@export var tree: AnimationTree
@export var skeleton: Skeleton3D
@export var blend_node_name: StringName = &"locomotion"

func _ready():
    tree.active = true

func update_blending():
    # CharacterBody3D 的速度在 4.x 里叫 velocity（不是 3.x 的 linear_velocity）
    var speed = $CharacterBody3D.velocity.length()
    var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
    tree.set("parameters/%s/blend_amount" % blend_node_name, blend_amount)
```

### 7.3 2D 动画混合

```gdscript
# 2D 动画混合
class_name SpriteAnimationBlending

extends Node2D

@export var tree: AnimationTree
@export var blend_node_name: StringName = &"locomotion"

func _ready():
    tree.active = true

func update_blending():
    var speed = $CharacterBody2D.velocity.length()
    var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
    tree.set("parameters/%s/blend_amount" % blend_node_name, blend_amount)
```

---

## 8. 混合空间详解

### 8.1 1D 混合空间（AnimationNodeBlendSpace1D）

1D 混合空间把若干动画放在一条虚拟数轴上，按当前参数值在**相邻两个**动画之间线性插值。

```
1D 混合空间示例（移动速度）:
┌─────────────────────────────────────────────────────────────┐
│ 速度参数：0.0 → 1.0 → 2.0 → 3.0                            │
│         ↓     ↓     ↓     ↓                                 │
│ 动画：  静止  走路  跑步  冲刺                               │
│                                                             │
│ 混合点:                                                     │
│ 0.0-1.0: 静止 ↔ 走路                                        │
│ 1.0-2.0: 走路 ↔ 跑步                                        │
│ 2.0-3.0: 跑步 ↔ 冲刺                                        │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 1D 混合空间：用代码构建速度驱动的 Idle → Walk → Run
class_name AnimationBlendSpace1DBuilder

extends Node3D

@export var tree: AnimationTree

func _ready() -> void:
    var space := AnimationNodeBlendSpace1D.new()
    space.min_space = 0.0
    space.max_space = 5.0

    # add_blend_point(node, pos)：pos 是该动画在数轴上的位置
    space.add_blend_point(_anim_node(&"Idle"), 0.0)
    space.add_blend_point(_anim_node(&"Walk"), 1.5)
    space.add_blend_point(_anim_node(&"Run"), 4.0)

    tree.tree_root = space
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

# 混合位置通过 AnimationTree 的参数路径写入
func update_blend(speed: float) -> void:
    tree.set("parameters/blend_position", speed)
```

### 8.2 2D 混合空间（AnimationNodeBlendSpace2D）

2D 混合空间把动画放在二维平面上，按当前 `Vector2` 参数在**包含该点的三角形**内做重心插值。

```
2D 混合空间示例（移动方向）:
┌─────────────────────────────────────────────────────────────┐
│                      Y (向前/向后)                           │
│                      ↑                                      │
│                      │                                      │
│         左后 ●       │       ● 右后                         │
│                      │                                      │
│  左 ●───────●───────●───────● 右   → X (向左/向右)          │
│       左前   │  前   │  右前                                 │
│                      │                                      │
│         ● 左后       │       ● 右前                         │
│                      │                                      │
└─────────────────────────────────────────────────────────────┘

混合权重计算:
- 用当前 (X, Y) 找到包含它的三角形
- 用三角形的三个顶点做重心插值
- 混合这 3 个动画
```

**2D 与 1D 的关键差异**：

| 维度 | BlendSpace1D | BlendSpace2D |
|---|---|---|
| 参数类型 | `float` | `Vector2` |
| 参与混合的动画数 | 2（相邻两点） | 3（所在三角形的三点） |
| 三角剖分 | 不需要 | 需要 |
| 剖分方式 | —— | `auto_triangles = true` 时用 Delaunay 自动剖分；否则用 `add_triangle(x, y, z)` 手工指定 |
| 混合模式 | `BLEND_MODE_INTERPOLATED` / `DISCRETE` / `DISCRETE_CARRY` | 同左 |

**关于「对称性修正」**：2D 混合空间本身**不提供**"自动镜像左/右方向"的开关。
常见的"对称修正"有两种做法：

1. **动画资源层**：导入时只做一套右向动画，左向用骨骼的负 X 缩放镜像生成（会丢失非对称细节）。
2. **节点图层**：在 `AnimationNodeBlendTree` 里为左右方向各建一条分支，用
   `AnimationNodeBlend2` 按输入方向做混合。

```gdscript
# 2D 混合空间
class_name AnimationBlendSpace2DBuilder

extends Node

@export var tree: AnimationTree

func build_2d_blend() -> void:
    var space := AnimationNodeBlendSpace2D.new()

    # 依次添加混合点，索引按添加顺序为 0、1、2、3
    space.add_blend_point(_anim_node(&"Idle"), Vector2(0, 0))            # 0
    space.add_blend_point(_anim_node(&"WalkForward"), Vector2(0, 1.5))  # 1
    space.add_blend_point(_anim_node(&"WalkLeft"), Vector2(-1.5, 0))    # 2
    space.add_blend_point(_anim_node(&"WalkRight"), Vector2(1.5, 0))    # 3

    # 默认 auto_triangles = true（自动 Delaunay 剖分）。
    # 需要手工控制时才关闭自动剖分并显式声明三角形。
    space.auto_triangles = false
    space.add_triangle(0, 1, 2)
    space.add_triangle(0, 2, 3)

    tree.tree_root = space
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

# 2D 混合空间的参数是 Vector2
func update_blend(velocity: Vector2) -> void:
    tree.set("parameters/blend_position", velocity)
```

### 8.3 把混合空间接进混合树

```gdscript
# 混合树 + 混合空间的典型组合
class_name BlendTreeWithBlendSpace

extends Node

@export var tree: AnimationTree

func build(tree_root_name: StringName = &"locomotion") -> void:
    # 1) 2D 混合空间：用「速度 + 方向」两个参数驱动移动动画
    var space := AnimationNodeBlendSpace2D.new()
    space.add_blend_point(_anim_node(&"Idle"), Vector2(0, 0))
    space.add_blend_point(_anim_node(&"WalkForward"), Vector2(0, 1.5))
    space.add_blend_point(_anim_node(&"WalkLeft"), Vector2(-1.5, 0))
    space.add_blend_point(_anim_node(&"WalkRight"), Vector2(1.5, 0))

    # 2) 把混合空间挂进混合树，再串一个时间缩放节点
    var blend_tree := AnimationNodeBlendTree.new()
    blend_tree.add_node(tree_root_name, space)
    var time_scale := AnimationNodeTimeScale.new()
    blend_tree.add_node("time_scale", time_scale)

    # connect_node(输入节点名, 输入端口索引, 输出节点名)
    # BlendTree 内置一个名为 "output" 的输出节点
    blend_tree.connect_node(tree_root_name, 0, "time_scale")
    blend_tree.connect_node("time_scale", 0, "output")

    tree.tree_root = blend_tree
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

# 参数路径随节点位置变化，写参数时务必用编辑器里显示的完整路径
func update_blend(velocity: Vector2, speed_scale: float) -> void:
    tree.set("parameters/locomotion/blend_position", velocity)
    tree.set("parameters/time_scale/scale", clampf(speed_scale, 0.2, 2.0))
```

### 8.4 混合树的性能优化

```
混合树性能考量:
┌─────────────────────────────────────────────────────────────┐
│ 因素              │ 影响            │ 优化建议              │
├─────────────────────────────────────────────────────────────┤
│ 混合节点数量      │ 增加求值开销    │ 限制层级深度          │
│ 混合参数更新频率  │ 每帧计算        │ 按需更新              │
│ 动画轨道数量      │ 内存 + 计算     │ 禁用未使用轨道        │
│ 混合权重计算      │ 浮点运算        │ 缓存结果              │
└─────────────────────────────────────────────────────────────┘

最佳实践:
✅ 使用 1D/2D 混合空间代替多层 Blend2
✅ 缓存混合权重计算结果
✅ 禁用远处角色的动画混合
✅ 简化混合树结构
❌ 过深的混合树嵌套
❌ 每帧重新创建混合节点
❌ 不必要的混合参数更新
```

> ⚠️ 示意数据（未附测试环境）：上表中的"影响"一列只描述**定性**趋势
> （求值开销随节点数与轨道数增长），未给出具体百分比。
> 真实的 ms 级开销必须在目标机型上用 `Performance.get_monitor(Performance.TIME_PROCESS)`
> 与 Godot Profiler 实测，不能照搬别处的数字。

---

## 9. 分层混合与轨道过滤（Godot 4.x 的真实机制）

### 9.1 先澄清：Godot 4.x 没有 AnimationMask

很多 Unity 用户移植到 Godot 时会找"Animation Mask"，在 Godot 4.x 里**找不到**：

- Godot 4.3 / 4.4 / 4.5 / master 的全部类中 **都不存在 `AnimationMask` 类**
- `AnimationPlayer` 上 **没有** `set_track_enabled()` 方法
- 也不存在 `parameters/<节点>/mask` 或 `parameters/<节点>/request` 这种参数

Godot 4.x 实现"上半身 / 下半身分层"的真实机制是**混合节点的轨道过滤器（Filter）**：

```
AnimationNode（混合节点）的 Filter 面板：
┌─────────────────────────────────────────────────────────────┐
│ 轨道路径                                │ 过滤动作           │
├─────────────────────────────────────────────────────────────┤
│ Skeleton3D:Spine                       │ PASS               │
│ Skeleton3D:Spine2                      │ PASS               │
│ Skeleton3D:LeftArm                     │ PASS               │
│ Skeleton3D:RightArm                    │ PASS               │
│ Skeleton3D:LeftLeg                     │ STOP               │
│ Skeleton3D:RightLeg                    │ STOP               │
└─────────────────────────────────────────────────────────────┘
```

四种过滤动作（`AnimationNode.FilterAction` 官方枚举）：

| 常量 | 值 | 含义 |
|---|---|---|
| `FILTER_IGNORE` | 0 | 不使用过滤 |
| `FILTER_PASS` | 1 | 匹配过滤路径的属性**允许通过** |
| `FILTER_STOP` | 2 | 匹配过滤路径的属性**被丢弃** |
| `FILTER_BLEND` | 3 | 匹配过滤路径的属性**按混合值混合** |

### 9.2 用 Filter 实现上半身 / 下半身分层

```gdscript
# 用 AnimationNode 的轨道过滤器实现上半身/下半身分层
class_name UpperBodyLayerFilter

extends Node

@export var tree: AnimationTree

# 混合树里"上半身混合节点"的名字
@export var upper_node_name: StringName = &"upper_body"

func _ready() -> void:
    var blend_tree := tree.tree_root as AnimationNodeBlendTree
    if blend_tree == null:
        push_error("tree_root 不是 AnimationNodeBlendTree")
        return

    var upper_node := blend_tree.get_node(upper_node_name) as AnimationNode
    if upper_node == null:
        push_error("混合树里没有名为 %s 的节点" % upper_node_name)
        return

    # 打开过滤：只有列出的骨骼轨道会通过
    upper_node.filter_enabled = true

    # set_filter_path(path, enable)：path 是动画轨道路径，形如 "Skeleton3D:Spine"
    for bone in [&"Spine", &"Spine2", &"Head", &"LeftArm", &"RightArm"]:
        upper_node.set_filter_path(NodePath("Skeleton3D:%s" % bone), true)

    # 也可以查询某条路径当前是否被过滤
    # print(upper_node.is_path_filtered(NodePath("Skeleton3D:Spine")))

    # 路径格式与 Animation.track_set_path() 一致：
    # "节点路径:属性名" 或 "节点路径:骨骼名"
```

### 9.3 用 `Animation.track_set_enabled()` 做运行时轨道开关

如果需要在**运行时**按条件关掉某条 `Animation` 资源的轨道，用的是
`Animation.track_set_enabled(track_idx, enabled)`——注意它在 **Animation 资源**上，
不是在 `AnimationPlayer` 上：

```gdscript
# 运行时开关 Animation 的轨道
class_name TrackEnableSwitch

extends Node

@export var player: AnimationPlayer

func set_track_enabled(anim_name: StringName, track_idx: int, enabled: bool) -> void:
    var anim := player.get_animation(anim_name)
    if anim == null:
        return
    anim.track_set_enabled(track_idx, enabled)

func is_track_enabled(anim_name: StringName, track_idx: int) -> bool:
    var anim := player.get_animation(anim_name)
    if anim == null:
        return false
    return anim.track_is_enabled(track_idx)
```

> **更正**：`AnimationPlayer.set_track_enabled()` **不存在**，
> 正确写法是 `anim.track_set_enabled(track_idx, enabled)`（`anim` 取自 `get_animation()`）。

### 9.4 加法动画混合（Additive Blending）

叠加表情、手势等"增量动作"用 `AnimationNodeAdd2`：

```gdscript
# 加法动画混合
class_name AdditiveAnimationMixer

extends Node

@export var base_animation: StringName = &"idle"
@export var additive_animations: Array[StringName] = [&"wave", &"nod", &"look_around"]

@export var tree: AnimationTree

func _ready():
    _setup_additive_blend_tree()

func _setup_additive_blend_tree():
    var blend_tree := AnimationNodeBlendTree.new()

    # 基础动画节点
    var base_node := AnimationNodeAnimation.new()
    base_node.animation = base_animation
    blend_tree.add_node("base", base_node)

    # 每个加法动画配一个 Add2 节点，并串成链
    var prev_name := "base"
    for i in range(additive_animations.size()):
        var anim_name := additive_animations[i]

        var anim_node := AnimationNodeAnimation.new()
        anim_node.animation = anim_name
        blend_tree.add_node(String(anim_name), anim_node)

        var add_node := AnimationNodeAdd2.new()
        var add_name := "add_%d" % i
        blend_tree.add_node(add_name, add_node)

        # base → add_0 → add_1 → … → output
        blend_tree.connect_node(prev_name, 0, add_name)
        blend_tree.connect_node(String(anim_name), 0, add_name)
        prev_name = add_name

    blend_tree.connect_node(prev_name, 0, "output")

    tree.tree_root = blend_tree
    tree.active = true

# 设置加法动画权重：Add2 的参数名是 add_amount
func set_additive_weight(node_name: StringName, weight: float) -> void:
    tree.set("parameters/%s/add_amount" % node_name, clampf(weight, -1.0, 1.0))

# 切换基础动画
func set_base(anim_name: StringName) -> void:
    var blend_tree := tree.tree_root as AnimationNodeBlendTree
    var base_node := blend_tree.get_node("base") as AnimationNodeAnimation
    if base_node:
        base_node.animation = anim_name
```

> ⚠️ `AnimationNodeAdd2` 的加法量超过 `1.0` 会得到"放大叠加"的结果；
> `AnimationMixer.deterministic = true`（`AnimationTree` 的默认值）时，
> `AnimationNodeAdd2` / `Add3` / `Sub2` 或权重大于 1.0 的混合**可能产生非预期结果**
> （官方类参考在 `deterministic` 条目下明确提示）。做加法混合时保持权重在 `[-1, 1]` 最稳。

### 9.5 实时混合权重调整

```gdscript
# 动态混合权重控制器
class_name DynamicBlendWeightController

extends Node

@export var weight_parameter: String = "blend_weight"
@export var smoothing: float = 0.2

var target_weight: float = 0.0
var current_weight: float = 0.0
@export var tree: AnimationTree

func _ready():
    if tree == null:
        tree = $AnimationTree

func _process(delta):
    # 平滑过渡权重
    current_weight = lerp(current_weight, target_weight, smoothing * delta * 60.0)

    # 更新参数
    tree.set("parameters/" + weight_parameter, current_weight)

# 示例：根据速度动态混合走路/跑步
func update_movement_blend(speed: float):
    var walk_speed = 2.0
    var run_speed = 6.0

    if speed < walk_speed:
        target_weight = 0.0  # 完全走路
    elif speed > run_speed:
        target_weight = 1.0  # 完全跑步
    else:
        # 线性插值
        target_weight = (speed - walk_speed) / (run_speed - walk_speed)

# 示例：根据距离动态混合瞄准
func update_aim_blend(target_distance: float):
    var close_range = 5.0
    var far_range = 20.0

    if target_distance < close_range:
        target_weight = 1.0  # 完全瞄准
    elif target_distance > far_range:
        target_weight = 0.0  # 不瞄准
    else:
        target_weight = 1.0 - (target_distance - close_range) / (far_range - close_range)
```

---

## 10. AnimationLibrary 的键名规则

Godot 4.x 起动画按**库（library）**组织，`AnimationPlayer` 内部是一张
`StringName → AnimationLibrary` 的表；每个库内部再是一张 `StringName → Animation` 的表。

```
AnimationPlayer
 └── 库 ""（默认库）        →  Animation "idle", "walk", "run"
 └── 库 "movement"          →  Animation "run", "strafe_left"
 └── 库 "combat"            →  Animation "attack", "block"
```

引用动画时的键名规则（`AnimationPlayer` 官方类参考）：

| 目标 | 键名写法 |
|---|---|
| 默认库里的动画 | `"idle"`（省略库名与斜杠） |
| 非默认库里的动画 | `"movement/run"`（`库名/动画名`） |
| `AnimationNodeAnimation.animation` | 同样是这个键名 |

```gdscript
# 动画库与键名
class_name AnimationLibraryHelper

extends Node

@export var player: AnimationPlayer

func _ready() -> void:
    # 打印所有库名与其中的动画名
    for lib_name in player.get_animation_library_list():
        var lib := player.get_animation_library(lib_name)
        print("库 %s → %s" % [lib_name, lib.get_animation_list()])

    # 判断某个键名是否存在
    if player.has_animation(&"movement/run"):
        player.play(&"movement/run")
```

> **写错库名会静默失败**：`has_animation()` 返回 false，`play()` 什么也不做，
> 没有报错。排查动画不播时，第一件事就是核对库名。

---

## 📝 本章总结

### 核心要点

1. **`AnimationNodeBlend2` / `Add2` / `Blend3` 没有任何成员属性**，混合量是树参数
2. **混合量参数名**：Blend2 / Blend3 = `blend_amount`，Add2 = `add_amount`
3. **连线在 `AnimationNodeBlendTree` 上做**：`add_node()` + `connect_node()`
4. **1D / 2D 混合空间的差异**：参数类型、参与混合的动画数、2D 需要三角剖分
5. **Godot 4.x 没有 `AnimationMask`**，分层靠 `AnimationNode` 的轨道 Filter + `Add2`
6. **运行时开关轨道**用 `Animation.track_set_enabled()`
7. **动画键名**遵循 `"库名/动画名"`

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationNodeBlend2 | 两个动画的线性混合 |
| AnimationNodeAdd2 | 两个动画的加法混合 |
| AnimationNodeBlend3 | 三个动画的混合 |
| AnimationNodeBlendSpace1D / 2D | 1D / 2D 混合空间 |
| AnimationNodeBlendTree | 混合树，参数化动画混合的容器 |
| Filter | AnimationNode 的轨道过滤器，Godot 4.x 的分层机制 |
| Additive Blending | 加法混合，叠加动画效果 |

---

## 🔗 延伸阅读

- **官方文档 · Using AnimationTree**: <https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html>
- **官方文档 · AnimationNodeBlendTree**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeblendtree.html>
- **官方文档 · AnimationNodeBlend2**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeblend2.html>
- **官方文档 · AnimationNodeAdd2**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeadd2.html>
- **官方文档 · AnimationNodeBlend3**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeblend3.html>
- **官方文档 · AnimationNodeBlendSpace1D**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeblendspace1d.html>
- **官方文档 · AnimationNodeBlendSpace2D**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeblendspace2d.html>
- **官方文档 · AnimationLibrary**: <https://docs.godotengine.org/en/stable/classes/class_animationlibrary.html>
- **源码位置**: `scene/animation/`（`animation_blend_tree.cpp`、`animation_blend_space_1d.cpp`、
  `animation_blend_space_2d.cpp`、`animation_mixer.cpp`、`animation_tree.cpp`）、
  `scene/resources/animation.cpp`、`scene/resources/animation_library.cpp`

> **注意**：Godot 4.3 的 `servers/` 目录下没有 `animation/` 子目录。

---

## 📋 上下篇导航

**上一篇**: [第 38 篇：动画控制器](/articles/38-animation-controller.md)
**下一篇**: [第 40 篇：角色动画](/articles/40-character-animation.md)

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

*写作时间：2026-03-20*  
*最近一次技术勘误：2026-09-12*  
*状态：✅ 完成*
