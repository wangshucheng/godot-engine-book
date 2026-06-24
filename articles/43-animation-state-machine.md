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

| 过渡属性 | 说明 | 建议值 |
|----------|------|--------|
| `Switch Mode` | 切换模式：`Immediate`、`Sync`、`At End` | `At End` 用于循环动画 |
| `Blend` | 混合时间（秒） | 0.1-0.3 |
| `Advance Mode` | 推进模式：`Auto`、`Disabled` | `Auto` 自动评估条件 |
| `Advance Condition` | 条件表达式 | `is_running` |

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
# 从当前状态旅行到目标状态，自动经过中间状态
animation_tree.travel("run")

# 也可以获取 playback 对象进行更精细控制
var playback = animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
playback.travel("attack")
playback.start("idle")  # 立即切换到 idle
playback.stop()         # 停止状态机
```

### 3.4 一次性动画

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

```gdscript
# 进入子状态机中的特定状态
var playback = animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
playback.travel("CombatSubState/attack_light")
```

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
    var to_walk = state_machine.get_transition("idle", "walk")
    to_walk.advance_condition = "is_moving"
    
    # 应用为 AnimationTree 根节点
    animation_tree.tree_root = state_machine
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
| 禁用不用的 AnimationTree | 远处或不可见角色可设置 `active = false` |

### 7.2 LOD 与动画状态机

```gdscript
# 根据距离简化动画更新
func _process(delta):
    var distance = global_position.distance_to(camera.global_position)
    
    if distance > 50.0:
        animation_tree.active = false  # 远距离禁用
    else:
        animation_tree.active = true
        if distance > 20.0:
            # 减少过渡混合时间
            animation_tree.set("parameters/locomotion/blend_space_2d/blend_mode", 
                AnimationNodeBlendSpace2D.BLEND_MODE_INTERP)
```

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

## 参考资料

1. [Godot 文档 - AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html)
2. [Godot 文档 - State Machine](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html#state-machine)
3. 《Game Animation Programming》

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [第 42 篇：粒子系统](#)  
**下一篇**: [第 44 篇：骨骼动画](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
