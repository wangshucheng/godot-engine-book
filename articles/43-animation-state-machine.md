# 第 43 篇：动画状态机

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 42 章 粒子系统  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

动画状态机（Animation State Machine）是游戏中管理角色动画切换的核心机制。通过状态机，开发者可以将复杂的动画逻辑抽象为状态、过渡和条件，使角色能够根据输入、物理状态和游戏事件在空闲、行走、奔跑、攻击、受击等动画之间自然切换。

Godot 通过 `AnimationTree` 节点提供强大的状态机支持，包括 `AnimationNodeStateMachine`、`AnimationNodeBlendTree`、`AnimationNodeBlendSpace2D` 等多种节点类型。本章将深入探讨动画状态机的架构、实现和优化。

---

## 🎯 学习目标

- 理解动画状态机的基本概念
- 掌握 `AnimationTree` 和 `AnimationNodeStateMachine` 的使用
- 学会配置状态、过渡和条件
- 熟悉子状态机和并行状态机
- 掌握动画状态机的性能优化

---

## 1. 动画状态机基础

### 1.1 什么是动画状态机

**动画状态机**是一种用状态、事件和过渡来组织动画的模型：

- **状态（State）**：一个具体的动画片段，如 `idle`、`walk`、`run`、`attack`
- **过渡（Transition）**：从一个状态切换到另一个状态的连接
- **条件（Condition）**：触发过渡的规则，如 `is_running = true`
- **参数（Parameter）**：控制状态机运行的变量

```
动画状态机示例:
┌─────────────────────────────────────────────────────────────┐
│                      角色动画状态机                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────┐         is_moving=true         ┌──────┐         │
│   │ idle │───────────────────────────────▶│ walk │         │
│   └──────┘                                 └──────┘         │
│      ▲                                       │              │
│      │ is_moving=false                       │ speed > 5    │
│      │                                       ▼              │
│   ┌──────┐         attack_triggered      ┌──────┐         │
│   │ dead │◀──────────────────────────────│ run  │         │
│   └──────┘                                └──────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Godot 状态机节点类型

Godot 的 `AnimationTree` 可以包含多种根节点：

| 节点类型 | 用途 | 适用场景 |
|----------|------|----------|
| `AnimationNodeStateMachine` | 状态机 | 角色动画切换 |
| `AnimationNodeBlendTree` | 混合树 | 复杂动画混合 |
| `AnimationNodeBlendSpace1D` | 1D 混合空间 | 根据单参数混合 |
| `AnimationNodeBlendSpace2D` | 2D 混合空间 | 根据方向/速度混合 |
| `AnimationNodeAnimation` | 单个动画 | 直接播放动画 |
| `AnimationNodeOneShot` | 一次性动画 | 攻击、受击 |
| `AnimationNodeTimeScale` | 时间缩放 | 调整播放速度 |

### 1.3 动画状态机处理流程

```
动画状态机处理流程:
┌─────────────────────────────────────────────────────────────┐
│                    动画状态机处理流程                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 游戏逻辑更新参数（速度、是否在地面上等）                │
│  2. 状态机评估当前状态的所有出边过渡条件                    │
│  3. 若条件满足，开始状态切换并混合过渡                      │
│  4. 计算目标动画的当前姿态                                  │
│  5. 将姿态应用到 Skeleton/BlendShape                        │
│  6. 输出最终动画 pose                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 创建基础状态机

### 2.1 场景结构

```
Player (CharacterBody3D)
├── MeshInstance3D
├── AnimationPlayer        # 包含 idle、walk、run、attack 等动画
└── AnimationTree          # 状态机控制器
    └── Root (AnimationNodeStateMachine)
```

### 2.2 基础状态机代码

```gdscript
# animation_state_machine.gd
class_name AnimationStateMachine
extends AnimationTree

@export var character: CharacterBody3D

# 参数引用（通过参数路径访问）
var playback_path: StringName = "parameters/playback"
var is_moving_param: StringName = "parameters/conditions/is_moving"
var is_running_param: StringName = "parameters/conditions/is_running"
var attack_trigger_param: StringName = "parameters/conditions/attack_trigger"

func _ready():
    # 必须激活 AnimationTree 才能运行
    active = true

func _process(_delta):
    # 更新状态机参数
    _update_parameters()

func _update_parameters():
    if not character:
        return
    
    var velocity = character.velocity
    var is_moving = velocity.length() > 0.1
    var is_running = velocity.length() > 5.0
    
    set(is_moving_param, is_moving)
    set(is_running_param, is_running)

func trigger_attack():
    # 一次性触发攻击
    set(attack_trigger_param, true)
    # 下一帧重置，避免持续触发
    await get_tree().process_frame
    set(attack_trigger_param, false)

func get_current_state() -> StringName:
    var playback = get(playback_path) as AnimationNodeStateMachinePlayback
    if playback:
        return playback.get_current_node()
    return &""

func travel_to(state_name: StringName):
    var playback = get(playback_path) as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(state_name)
```

### 2.3 编辑器配置步骤

1. **创建 AnimationPlayer**：添加 `idle`、`walk`、`run`、`attack` 等动画
2. **添加 AnimationTree**：将 `Anim Player` 属性指向 `AnimationPlayer`
3. **设置根节点类型**：选择 `AnimationNodeStateMachine`
4. **添加状态**：双击状态机视图，创建 `idle`、`walk`、`run`、`attack` 等状态
5. **配置过渡**：连接状态，设置条件参数
6. **设置自动开始**：指定 `Start` 状态的默认下一个状态

```
状态机配置:
┌─────────────────────────────────────────────────────────────┐
│                      编辑器状态机视图                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Start] ──▶ [idle] ──is_moving─▶ [walk] ──speed>5─▶ [run]│
│                  ▲        │              │              │  │
│                  │        │ attack       │ attack       │  │
│                  │        ▼              ▼              ▼  │
│                  └────── [attack] ◀──── [attack] ◀─── [run]│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 状态、过渡与条件

### 3.1 过渡类型

Godot 支持多种过渡方式：

`AnimationNodeStateMachineTransition` 的完整属性面（4.3 官方类参考）：

| 属性 | 取值 / 类型 | 说明 |
|---|---|---|
| `switch_mode` | `SWITCH_MODE_IMMEDIATE` / `SWITCH_MODE_SYNC` / `SWITCH_MODE_AT_END` | 切换方式；`At End` 等当前状态播完再切 |
| `xfade_time` | float（秒） | 交叉淡入时长，常用 0.1–0.3 |
| `xfade_curve` | `Curve` | 淡入缓动曲线，可自定义 |
| `advance_mode` | `ADVANCE_MODE_DISABLED` / `ADVANCE_MODE_ENABLED` / `ADVANCE_MODE_AUTO` | 推进模式，**三态**（默认值是 `ENABLED`） |
| `advance_condition` | `StringName` | 布尔条件名；值写在 `parameters/conditions/<名字>` |
| `advance_expression` | `String` | **4.x 新增**的表达式条件 |
| `reset` | bool（默认 true） | 切换时目标动画是否从头播放 |
| `priority` | int（默认 1） | 越小越优先；`travel()` 与 `AUTO` 判定时使用 |
| `break_loop_at_end` | bool | 即使动画在循环，也在周期末打断以便切换 |

**三种推进模式的区别**（`advance_mode`）：

| 模式 | 行为 | 典型用途 |
|---|---|---|
| `ADVANCE_MODE_DISABLED` | 禁用该过渡，`travel()` 与自动推进都不走它 | 受击动画未播完前锁死移动 |
| `ADVANCE_MODE_ENABLED` | **仅在 `travel()` 主动请求时**使用（默认值，最常用） | 由脚本决定何时切状态 |
| `ADVANCE_MODE_AUTO` | 条件 / 表达式为真时自动使用（常配 `At End`） | 走 → 跑这类连续量切换 |

### 3.2 过渡条件示例

```gdscript
# 在 _process 或物理更新中设置条件
func _physics_process(_delta):
    var is_on_floor = character.is_on_floor()
    var is_moving = Input.get_vector("left", "right", "forward", "back").length() > 0.1
    var is_running = Input.is_action_pressed("run")
    
    animation_tree.set("parameters/conditions/is_on_floor", is_on_floor)
    animation_tree.set("parameters/conditions/is_moving", is_moving)
    animation_tree.set("parameters/conditions/is_running", is_running)
```

### 3.3 旅行（Travel）机制

`travel()` 方法可以让状态机沿最短路径前往目标状态：

```gdscript
# travel() 属于 AnimationNodeStateMachinePlayback，**不属于 AnimationTree**。
# animation_tree.travel("run") 会报
# Invalid call. Nonexistent function 'travel' in base 'AnimationTree'。
var playback = animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback

# 从当前状态旅行到目标状态，自动经过中间状态
playback.travel("run")

playback.travel("attack")
playback.start("idle")  # 立即切换到 idle（硬切，不走过渡）
playback.next()         # 若存在 travel / auto advance 的下一路径，立刻切到下一状态
playback.stop()         # 停止状态机
```

### 3.4 状态机与 Playback 的完整接口

`AnimationNodeStateMachine`（资源侧，用于**构建**与**编辑**状态图）：

| 方法 | 说明 |
|---|---|
| `add_node(name, node, position = Vector2())` | 添加一个状态（状态本身是任意 `AnimationNode`） |
| `replace_node(name, node)` | 替换某个状态 |
| `get_node(name)` / `has_node(name)` | 按名取 / 查状态 |
| `rename_node(name, new_name)` | 重命名状态 |
| `remove_node(name)` | 删除状态 |
| `add_transition(from, to, transition)` | 添加过渡 |
| `get_transition(idx)` | **按整数索引**取过渡 |
| `get_transition_from(idx)` / `get_transition_to(idx)` | 取过渡的起点 / 终点 |
| `get_transition_count()` | 过渡总数 |
| `has_transition(from, to)` | 是否存在某条过渡 |
| `remove_transition(from, to)` / `remove_transition_by_index(idx)` | 删除过渡 |

`AnimationNodeStateMachinePlayback`（运行时侧，用于**驱动**已配置好的状态机）：

| 方法 | 说明 |
|---|---|
| `travel(to_node, reset_on_teleport = true)` | 沿 A\* 最短路径前往目标状态 |
| `start(node, reset = true)` | 立即开始播放指定状态 |
| `next()` | 立刻切到 travel / auto advance 的下一状态 |
| `stop()` / `is_playing()` | 停止 / 查询 |
| `get_current_node()` | 当前状态名 |
| `get_current_play_position()` / `get_current_length()` | 当前状态内的播放位置 / 状态长度 |
| `get_fading_from_node()` | 正在淡出的源状态名 |
| `get_travel_path()` | A\* 算出的当前旅行路径（`StringName[]`） |

> **注意**：`get_transition()` 只接受**单个 int 索引**，不接受 `("idle", "walk")`
> 这样的起止节点名。要按节点名定位过渡，请遍历
> `get_transition_count()` + `get_transition_from(i)` / `get_transition_to(i)`。

### 3.5 一次性动画

攻击、受击等动画播放一次后应自动返回：

```gdscript
# 配置 attack 状态的出边：
# - attack -> idle：Advance Condition = "is_attacking = false"，Switch Mode = "At End"
# 或使用 Reset Trigger 在动画结束时自动重置触发器

func perform_attack():
    animation_tree.set("parameters/conditions/attack_trigger", true)
```

---

## 4. 高级状态机

### 4.1 子状态机

当状态过多时，可以将相关状态组织为子状态机：

```
子状态机示例:
┌─────────────────────────────────────────────────────────────┐
│                        战斗子状态机                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [CombatSubState]                                          │
│   ├── [idle_combat]                                         │
│   ├── [attack_light]                                        │
│   ├── [attack_heavy]                                        │
│   ├── [block]                                               │
│   └── [dodge]                                               │
│                                                             │
│   子状态机内部有过渡，外部通过入口/出口连接                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**真实做法**：把子状态机作为一个 `AnimationNodeStateMachine` 资源
`add_node()` 进父状态机，并把它自己的 `state_machine_type` 设为
`STATE_MACHINE_TYPE_NESTED`（嵌套）或 `STATE_MACHINE_TYPE_GROUPED`（分组）：

```gdscript
# 构建一个嵌套子状态机
func build_combat_sub_state_machine() -> AnimationNodeStateMachine:
    var sub := AnimationNodeStateMachine.new()
    sub.state_machine_type = AnimationNodeStateMachine.STATE_MACHINE_TYPE_NESTED

    for state_name in [&"idle_combat", &"attack_light", &"attack_heavy", &"block", &"dodge"]:
        var anim := AnimationNodeAnimation.new()
        anim.animation = state_name
        sub.add_node(state_name, anim)

    return sub

# 把子状态机挂进父状态机
func attach_to_parent(parent: AnimationNodeStateMachine,
        sub: AnimationNodeStateMachine) -> void:
    parent.add_node("CombatSubState", sub)

# 进入子状态机中的特定状态：用 "父/子" 路径寻址
func travel_into_sub_state() -> void:
    var playback = animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    playback.travel("CombatSubState/attack_light")
```

`state_machine_type` 的三种取值（`AnimationNodeStateMachine.StateMachineType`）：

| 常量 | 语义 |
|---|---|
| `STATE_MACHINE_TYPE_ROOT` | 根状态机：seek 到开头视为从起始状态播放，过渡到结束状态视为退出 |
| `STATE_MACHINE_TYPE_NESTED` | 嵌套：seek 到开头视为 seek 当前状态的动画，过渡到结束状态视为退出 |
| `STATE_MACHINE_TYPE_GROUPED` | 分组：不能独立运行，必须有 `ROOT` 或 `NESTED` 的父 / 祖先状态机 |

### 4.2 混合树与状态机结合

状态机的某个状态可以是 BlendTree，实现更复杂的动画：

```gdscript
# 例如 "locomotion" 状态使用 BlendSpace2D
# 根据速度和方向混合 walk、run、strafe 等动画

# 设置 BlendSpace2D 参数
animation_tree.set("parameters/locomotion/blend_position", 
    Vector2(input_direction.x, input_direction.y))
```

### 4.3 并行状态机

Godot 4.x 支持通过 `AnimationNodeBlendTree` 并行运行多个状态机：

```
并行状态机:
┌─────────────────────────────────────────────────────────────┐
│                       并行动画混合树                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [UpperBodyStateMachine] ──┐                               │
│                             ├──▶ [Add2] ──▶ [Output]       │
│   [LowerBodyStateMachine] ──┘                               │
│                                                             │
│   上半身可以攻击/招手，下半身控制行走                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 代码完整示例

### 5.1 角色动画控制器

```gdscript
# player_animation_controller.gd
extends Node

@export var animation_tree: AnimationTree
@export var character: CharacterBody3D

var _playback: AnimationNodeStateMachinePlayback

func _ready():
    animation_tree.active = true
    _playback = animation_tree.get("parameters/playback")

func _physics_process(_delta):
    _update_ground_state()
    _update_movement_state()

func _update_ground_state():
    var is_on_floor = character.is_on_floor()
    animation_tree.set("parameters/conditions/is_on_floor", is_on_floor)
    animation_tree.set("parameters/conditions/is_in_air", not is_on_floor)

func _update_movement_state():
    var input_dir = Input.get_vector("left", "right", "forward", "back")
    var is_moving = input_dir.length() > 0.1 and character.is_on_floor()
    var is_running = Input.is_action_pressed("run") and is_moving
    
    animation_tree.set("parameters/conditions/is_moving", is_moving)
    animation_tree.set("parameters/conditions/is_running", is_running)
    animation_tree.set("parameters/conditions/is_idle", not is_moving)

func attack():
    if _playback.get_current_node() in ["idle", "walk", "run"]:
        animation_tree.set("parameters/conditions/attack_trigger", true)
        await get_tree().process_frame
        animation_tree.set("parameters/conditions/attack_trigger", false)

func jump():
    animation_tree.set("parameters/conditions/jump_trigger", true)
    await get_tree().process_frame
    animation_tree.set("parameters/conditions/jump_trigger", false)

func hurt():
    _playback.travel("hurt")

func die():
    _playback.travel("death")
```

### 5.2 状态机配置代码

```gdscript
# 通过代码动态配置状态机（高级用法）
func _setup_state_machine():
    var state_machine = AnimationNodeStateMachine.new()
    
    # 添加状态
    state_machine.add_node("idle", AnimationNodeAnimation.new())
    state_machine.add_node("walk", AnimationNodeAnimation.new())
    state_machine.add_node("run", AnimationNodeAnimation.new())
    
    # 添加过渡
    state_machine.add_transition("idle", "walk", AnimationNodeStateMachineTransition.new())
    state_machine.add_transition("walk", "idle", AnimationNodeStateMachineTransition.new())
    
    # 设置条件
    # get_transition() 只接受**单个 int 索引**（过渡在图中的序号），
    # 不接受 ("idle", "walk") 这样的起止节点名。
    # 要按起止节点定位过渡，就遍历 get_transition_count()，
    # 配合 get_transition_from(i) / get_transition_to(i)。
    var to_walk := _find_transition(state_machine, &"idle", &"walk")
    if to_walk:
        to_walk.advance_condition = "is_moving"

    # 应用为 AnimationTree 根节点
    animation_tree.tree_root = state_machine

# 按起止节点名查找过渡
func _find_transition(state_machine: AnimationNodeStateMachine,
        from: StringName, to: StringName) -> AnimationNodeStateMachineTransition:
    for i in state_machine.get_transition_count():
        if state_machine.get_transition_from(i) == from and state_machine.get_transition_to(i) == to:
            return state_machine.get_transition(i)
    return null
```

---

## 6. 常见状态机模式

### 6.1 平台角色状态机

```
平台角色状态:
┌─────────────────────────────────────────────────────────────┐
│                      平台角色状态机                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [idle] ←──────→ [walk] ←──────→ [run]                   │
│     │                │                │                     │
│     │ jump           │ jump           │ jump                │
│     ▼                ▼                ▼                     │
│   [jump_up] ──▶ [jump_loop] ──▶ [jump_land]                │
│     │                                     │                 │
│     │ 不在地面上                          │ 在地面上        │
│     └─────────────────────────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 战斗角色状态机

```gdscript
# 战斗状态切换
func _input(event):
    if event.is_action_pressed("attack_light"):
        _trigger_state("attack_light")
    elif event.is_action_pressed("attack_heavy"):
        _trigger_state("attack_heavy")
    elif event.is_action_pressed("block"):
        animation_tree.set("parameters/conditions/is_blocking", true)
    elif event.is_action_released("block"):
        animation_tree.set("parameters/conditions/is_blocking", false)

func _trigger_state(state_name: StringName):
    # 检查能否从当前状态切换到攻击状态
    var current = _playback.get_current_node()
    if current in ["idle", "walk", "run"]:
        _playback.travel(state_name)
```

---

## 7. 性能优化

### 7.1 状态机优化原则

| 优化项 | 说明 |
|--------|------|
| 减少状态数量 | 状态过多会增加评估开销 |
| 合理设置 Blend 时间 | 过长的混合会增加计算量 |
| 避免每帧调用 travel() | travel 应在事件触发时调用 |
| 使用 BlendSpace 替代密集状态 | locomotion 用 BlendSpace2D 更高效 |
| 停用不用的 AnimationTree | 远处或不可见角色可设置 `active = false`（注意：这是**冻结**而不是**降级**，详见 7.2） |

### 7.2 LOD 与动画状态机

```gdscript
# 根据距离简化动画更新
func _process(_delta):
    var distance = global_position.distance_to(camera.global_position)
    
    if distance > 50.0:
        # 远距离停机。
        # 注意：active = false 只是"不再推进动画"，
        # 被动画驱动的属性会**停在最后一次写入的值上**（冻结），而不是回到静止姿势。
        # 这不是"降级"——真正的降级要换用更简单的混合结构。
        animation_tree.active = false
    else:
        animation_tree.active = true
        if distance > 20.0:
            # 切换混合模式：
            # blend_mode 是 AnimationNodeBlendSpace2D 的**成员**，不是 AnimationTree 的参数，
            # 不能用 set("parameters/...") 写。
            # 真实枚举是 BLEND_MODE_INTERPOLATED / BLEND_MODE_DISCRETE /
            # BLEND_MODE_DISCRETE_CARRY（没有 BLEND_MODE_INTERP）。
            var blend_tree := animation_tree.tree_root as AnimationNodeBlendTree
            if blend_tree:
                var space := blend_tree.get_node("locomotion") as AnimationNodeBlendSpace2D
                if space:
                    space.blend_mode = AnimationNodeBlendSpace2D.BLEND_MODE_DISCRETE
```

> **枚举名提醒**：2D 混合空间的混合模式在 4.x 里叫
> `AnimationNodeBlendSpace2D.BLEND_MODE_INTERPOLATED`（线性插值）、
> `BLEND_MODE_DISCRETE`（取最近点，适合逐帧 2D 动画）、
> `BLEND_MODE_DISCRETE_CARRY`（离散且保留上一个动画的播放位置）。
> `BLEND_MODE_INTERP` **不存在**。

---

## 8. 与 Unity Animator 对比

| 维度 | Godot AnimationTree | Unity Animator |
|------|---------------------|----------------|
| 根节点 | StateMachine / BlendTree / BlendSpace | Animator Controller |
| 参数类型 | Float、Bool、Trigger（通过条件表达） | Float、Int、Bool、Trigger |
| 过渡条件 | 表达式字符串 | 可视化条件 |
| 子状态机 | 支持 | 支持（Sub-State Machine） |
| BlendTree | AnimationNodeBlendSpace1D/2D | Blend Tree |
| 代码控制 | `travel()`、`set()` | `SetFloat()`、`Play()` |
| 可视化编辑 | ✅ 内置 | ✅ 内置 |
| 运行时创建 | 支持代码创建 | 支持代码创建 |

---

## 9. 调试与排错

### 9.1 可视化调试

```gdscript
# 在调试面板查看当前状态
func _process(_delta):
    if Engine.is_editor_hint():
        return
    
    var current = _playback.get_current_node()
    DebugDraw.text_3d(str(current), global_position + Vector3.UP * 2.0)
```

### 9.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 状态不切换 | `active = false` | 设置 `active = true` |
| 过渡条件不触发 | 参数名拼写错误 | 检查参数路径 |
| 动画卡住 | Trigger 未重置 | 触发后下一帧重置 |
| 混合不自然 | Blend 时间过短/过长 | 调整 Blend 时长 |
|  travel 无效 | 当前状态无到达目标的路径 | 添加过渡连接 |

---

## 10. 总结

### 核心要点

1. **状态机是动画管理的核心工具**，将复杂动画切换抽象为状态和过渡
2. **Godot 使用 `AnimationTree` + `AnimationNodeStateMachine`** 实现状态机
3. **条件参数驱动过渡**，通过 `set()` 动态更新
4. **`travel()` 实现平滑路径切换**，避免直接硬切
5. **子状态机和混合树**可以处理更复杂的角色动画需求
6. **合理优化**可以提升大量角色场景的性能

### 实践建议

- ✅ 将角色动画拆分为逻辑清晰的状态
- ✅ 使用 BlendSpace2D 处理 locomotion
- ✅ 用 Trigger 处理一次性动画（攻击、受击）
- ✅ 避免在 `_process` 中每帧调用 `travel()`
- ✅ 对远处角色禁用 `AnimationTree`

### 下一篇预告

下一篇文章将深入分析 **骨骼动画（Skeletal Animation）**，包括骨骼绑定、IK、程序化动画等高级技术。

---

## 🔗 延伸阅读

1. [Godot 文档 - AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html)
2. [Godot 文档 - State Machine](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html#state-machine)
3. 《Game Animation Programming》

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

## 📋 上下篇导航

**上一篇**: [第 41 篇：动画曲线](/articles/41-animation-curves.md)
**下一篇**: [第 44 篇：骨骼动画](/articles/44-skeletal-animation.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
