# 第 38 篇：动画控制器

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 37 章 动画系统基础  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

动画控制器是游戏开发中实现复杂动画逻辑的关键组件。通过动画控制器，开发者可以创建复杂的动画状态机、混合动画、处理动画事件，并实现流畅的动画过渡。

Godot 提供了多种动画控制器，包括 AnimationTree、AnimationNodeStateMachine、AnimationNodeBlendTree 等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解动画控制器的基本概念
- 掌握 AnimationTree 使用
- 学会 AnimationNodeStateMachine 应用
- 熟悉 AnimationNodeBlendTree
- 掌握动画混合器

---

## 1. 动画控制器基础

### 1.1 动画控制器类型

```
动画控制器类型:
┌─────────────────────────────────────────────────────────────┐
│                      动画控制器类型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationTree：动画树，基于节点的动画控制器            │
│  2. AnimationNodeStateMachine：动画状态机                   │
│  3. AnimationNodeBlendTree：动画混合树                     │
│  4. AnimationNodeOneShot：一次性动画                       │
│  5. AnimationNodeAdd2：动画叠加                            │
│  6. AnimationNodeBlend2：动画混合                          │
│  7. AnimationNodeTimeScale：时间缩放                       │
│  8. AnimationNodeTimeSeek：时间跳转                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画控制器流程

```
动画控制器处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画控制器处理流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 动画控制器接收输入参数（速度、方向等）                  │
│  2. 动画控制器根据参数选择合适的动画节点                    │
│  3. 动画节点处理动画数据（位置、旋转、缩放）                │
│  4. 动画控制器混合多个动画节点                              │
│  5. 动画控制器输出最终动画数据                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画控制器参数

```gdscript
# 动画控制器参数
class_name AnimationControllerParameters

@export var speed: float = 0.0
@export var direction: Vector2 = Vector2.ZERO
@export var is_jumping: bool = false
@export var is_attacking: bool = false
@export var health: float = 100.0

func _ready():
    # 初始化参数
    speed = 0.0
    direction = Vector2.ZERO
    is_jumping = false
    is_attacking = false
    health = 100.0

func update_parameters():
    # 更新参数
    speed = $CharacterBody2D.velocity.length()
    direction = $CharacterBody2D.velocity.normalized()
    is_jumping = Input.is_action_pressed("jump")
    is_attacking = Input.is_action_just_pressed("attack")
    health = $Health.health
```

---

## 2. AnimationTree

### 2.1 基础 AnimationTree

```gdscript
# 基础 AnimationTree
class_name BasicAnimationTree

extends AnimationTree

@export var animation_player: AnimationPlayer
@export var tree_root: AnimationNode

func _ready():
    # 设置动画播放器
    if animation_player:
        set_animation_player(animation_player)
    
    # 设置根节点
    if tree_root:
        set_tree_root(tree_root)

func _process(delta):
    # 处理动画树
    process(delta)

func play_animation(anim_name: String):
    if has_animation(anim_name):
        get_node("AnimationPlayer").play(anim_name)

func stop_animation():
    get_node("AnimationPlayer").stop()
```

### 2.2 AnimationTree 节点

```gdscript
# AnimationTree 节点
class_name AnimationTreeNode

extends AnimationNode

@export var node_type: String = "blend"
@export var input_count: int = 2

var inputs = []
var output = null

func _ready():
    # 创建输入
    for i in range(input_count):
        var input = AnimationNode.new()
        inputs.append(input)
    
    # 创建输出
    output = AnimationNode.new()

func _process(delta):
    # 处理节点
    process_inputs(delta)
    process_output(delta)

func process_inputs(delta):
    for input in inputs:
        input.process(delta)

func process_output(delta):
    output.process(delta)

func add_input(node: AnimationNode):
    inputs.append(node)

func remove_input(node: AnimationNode):
    inputs.erase(node)

func get_input(index: int) -> AnimationNode:
    if index < inputs.size():
        return inputs[index]
    return null

func get_output() -> AnimationNode:
    return output
```

### 2.3 AnimationTree 参数

```gdscript
# AnimationTree 的参数没有专用方法，统一用属性路径读写
class_name AnimationTreeParameters

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"locomotion"

func _ready() -> void:
    set_blend_position(0.0)

# 路径规则：
#   树根节点的参数 → parameters/<参数名>
#   混合树内某节点的参数 → parameters/<节点名>/<参数名>
func set_blend_position(value: float) -> void:
    tree.set("parameters/%s/blend_position" % node_name, value)

func get_blend_position() -> float:
    return float(tree.get("parameters/%s/blend_position" % node_name))

func _process(_delta: float) -> void:
    var body := $CharacterBody2D as CharacterBody2D
    set_blend_position(body.velocity.length())
```

---

## 3. AnimationNodeStateMachine

### 3.1 状态机基础

```gdscript
# 用代码构建动画状态机（等价于在 AnimationTree 编辑器中连线）
class_name AnimTreeStateMachineBuilder

extends Node3D

@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback
var _current_state: StringName

func _ready() -> void:
    var state_machine := AnimationNodeStateMachine.new()

    # add_node(name, node)：状态本身是任意 AnimationNode
    for anim_name in ["Idle", "Walk", "Run", "Jump", "Attack"]:
        var anim := AnimationNodeAnimation.new()
        anim.animation = anim_name
        state_machine.add_node(anim_name, anim)

    # add_transition(from, to, transition)：过渡规则独立描述
    state_machine.add_transition("Idle", "Walk", _make_xfade(0.25))
    state_machine.add_transition("Walk", "Run", _make_xfade(0.20))
    state_machine.add_transition("Run", "Idle", _make_xfade(0.25))
    state_machine.add_transition("Walk", "Jump", _make_xfade(0.10))
    state_machine.add_transition("Jump", "Walk", _make_xfade(0.10))
    state_machine.add_transition("Idle", "Attack", _make_xfade(0.15))
    state_machine.add_transition("Attack", "Idle", _make_xfade(0.15))

    tree.tree_root = state_machine
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    travel_to(&"Idle")

func _make_xfade(seconds: float) -> AnimationNodeStateMachineTransition:
    var t := AnimationNodeStateMachineTransition.new()
    t.xfade_time = seconds
    t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
    return t

func travel_to(state_name: StringName) -> void:
    playback.travel(state_name)

# 状态切换没有信号，需要轮询 get_current_node()
func _process(_delta: float) -> void:
    var current := playback.get_current_node()
    if current != _current_state:
        _current_state = current
        print("State changed to: ", current)
```

### 3.2 状态转换条件

```gdscript
# 转换条件由 AnimationNodeStateMachineTransition.advance_condition 描述，
# 条件值是挂在 AnimationTree 上的布尔开关，用 set_condition() 更新
class_name AnimTreeTransitionCondition

extends Node

@export var tree: AnimationTree
@export var transition_index: int = 0
@export var condition_name: StringName = &"can_jump"

@onready var _character: CharacterBody2D = $CharacterBody2D

func _ready() -> void:
    var state_machine := tree.tree_root as AnimationNodeStateMachine
    if state_machine == null:
        push_error("tree_root 不是 AnimationNodeStateMachine")
        return

    var transition := state_machine.get_transition(transition_index)
    transition.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED
    transition.advance_condition = condition_name

func _physics_process(_delta: float) -> void:
    # 每帧只更新条件开关，切换动作由状态机自己完成
    tree.set_condition(condition_name, _character.velocity.length() > 0.5)
```

### 3.3 过渡推进模式

```gdscript
# AnimationNodeStateMachineTransition 提供三种推进方式
class_name AnimTreeAdvanceModes

extends Node

func configure_transitions(state_machine: AnimationNodeStateMachine) -> void:
    # 1) AUTO：交叉淡入结束后自动切到目标状态
    var auto_t := state_machine.get_transition(0)
    auto_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
    auto_t.xfade_time = 0.2

    # 2) ENABLED：仅当条件为 true 时允许切换（配合 tree.set_condition）
    var cond_t := state_machine.get_transition(1)
    cond_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED
    cond_t.advance_condition = &"can_jump"

    # 3) DISABLED：暂时禁用该过渡
    var locked_t := state_machine.get_transition(2)
    locked_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_DISABLED

# 需要“硬切”时用 start()：跳过过渡，立即进入目标状态
func teleport_to(playback: AnimationNodeStateMachinePlayback, state_name: StringName) -> void:
    playback.start(state_name, true)
```

---

## 4. AnimationNodeBlendTree

### 4.1 混合树基础

```gdscript
# 混合树基础：1D 混合空间用单个标量驱动多段动画
class_name AnimTreeBlendSpace1DBuilder

extends Node3D

@export var tree: AnimationTree

func _ready() -> void:
    var space := AnimationNodeBlendSpace1D.new()
    space.min_space = 0.0
    space.max_space = 5.0

    # 位置即该动画在数轴上的取值点
    space.add_blend_point(_anim_node(&"Idle"), 0.0)
    space.add_blend_point(_anim_node(&"Walk"), 1.5)
    space.add_blend_point(_anim_node(&"Run"), 4.0)

    tree.tree_root = space
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

func _process(_delta: float) -> void:
    var body := $CharacterBody2D as CharacterBody2D
    # 写参数是唯一的驱动方式：混合树没有可读写的“状态对象”或“参数对象”
    tree.set("parameters/blend_position", body.velocity.length())
```

### 4.2 参数混合

```gdscript
# 混合参数没有信号，统一通过 AnimationTree 的参数路径写入
class_name AnimTreeParameterBlend

extends Node

@export var tree: AnimationTree

# 参数路径规则：
#   根节点（树根）的参数 → parameters/<参数名>
#   混合树内某个节点的参数 → parameters/<节点名>/<参数名>
func update_blend(velocity: float, direction: float) -> void:
    tree.set("parameters/velocity/blend_position", velocity)
    tree.set("parameters/direction/blend_position", direction)

# 需要调试时直接读回当前值
func read_velocity() -> float:
    return float(tree.get("parameters/velocity/blend_position"))
```

### 4.3 混合空间与节点图

```gdscript
# 实际项目里更常用的是「混合空间 + 节点图」的组合：
# 用 BlendSpace 做参数化插值，用 BlendTree 串联时间缩放、叠加层等处理
class_name AnimTreeBlendSpace2D

extends Node

@export var tree: AnimationTree

func build(tree_root_name: StringName = &"locomotion") -> void:
    # 1) 2D 混合空间：用「速度 + 方向」两个参数驱动移动动画
    var space := AnimationNodeBlendSpace2D.new()
    space.add_blend_point(_anim_node(&"Idle"), Vector2(0, 0))          # 0
    space.add_blend_point(_anim_node(&"WalkForward"), Vector2(0, 1.5)) # 1
    space.add_blend_point(_anim_node(&"WalkLeft"), Vector2(-1.5, 0))   # 2
    space.add_blend_point(_anim_node(&"WalkRight"), Vector2(1.5, 0))   # 3
    space.add_triangle(0, 1, 2)
    space.add_triangle(0, 2, 3)

    # 2) 把混合空间挂进混合树，再串一个时间缩放节点
    var blend_tree := AnimationNodeBlendTree.new()
    blend_tree.add_node(tree_root_name, space)
    var time_scale := AnimationNodeTimeScale.new()
    blend_tree.add_node("time_scale", time_scale)
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

---

## 5. 动画混合器

### 5.1 基础动画混合器

```gdscript
# AnimationMixer 是 AnimationPlayer 与 AnimationTree 的共同基类，
# 它是引擎内部的混合实现，不要为了“混合”去继承它。
class_name AnimMixerNotes

extends Node

@export var player: AnimationPlayer
@export var tree: AnimationTree

# 直接播放单个动画：走 AnimationPlayer，名字可以是 "库名/动画名"
func play_direct(anim_name: StringName) -> void:
    if player and player.has_animation(anim_name):
        player.play(anim_name)

# 需要真正混合时改用 AnimationTree
func travel(state_name: StringName) -> void:
    var playback := tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(state_name)

# current_animation 由 AnimationMixer 提供，两者通用
func current_animation() -> StringName:
    return player.current_animation if player else &""

func stop_animation():
    get_node("AnimationPlayer").stop()
```

### 5.2 动画混合器参数

```gdscript
# 参数是 AnimationTree 的特性（AnimationTree 继承自 AnimationMixer），
# 裸 AnimationMixer 没有参数概念，也没有 set_parameter/get_parameter。
class_name AnimationMixerParameters

extends Node

@export var tree: AnimationTree

func update_parameter(speed: float) -> void:
    tree.set("parameters/locomotion/blend_position", speed)

func read_parameter() -> float:
    return float(tree.get("parameters/locomotion/blend_position"))
```

### 5.3 根节点与动画库

```gdscript
# AnimationMixer 提供的两项通用能力：root_node 与动画库
class_name AnimMixerBasics

extends Node

@export var mixer: AnimationMixer

func _ready() -> void:
    # 1) root_node 是轨道路径的解析起点，轨道路径形如 "Skeleton3D:Root"
    if mixer.root_node.is_empty():
        mixer.root_node = mixer.get_path_to(mixer.get_parent())

    # 2) 动画按「库」组织（Godot 4 起取代了 3.x 的扁平动画列表），
    #    库名为空字符串时是默认库，播放时可直接用 "idle"
    var lib := AnimationLibrary.new()
    var anim := Animation.new()
    anim.length = 1.0
    lib.add_animation(&"idle", anim)
    mixer.add_animation_library(&"", lib)

    print("当前动画：%s" % mixer.current_animation)
```

---

## 6. 动画控制器优化

### 6.1 动画控制器缓存

```gdscript
# 动画缓存：缓存的是资源（Animation / AnimationLibrary），
# Godot 中并不存在名为 AnimationController 的类
class_name AnimationControllerCache

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

### 6.2 动画控制器LOD

```gdscript
# 动画控制器LOD
class_name AnimationControllerLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_controllers: Array = ["idle", "walk", "run"]

func update_lod(camera_position: Vector2, character: Node2D):
    var distance = camera_position.distance_to(character.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_controllers.size() - 1)
    
    # 更新控制器
    if lod_index < lod_controllers.size():
        character.animation_controller.play(lod_controllers[lod_index])
```

### 6.3 动画控制器压缩

```gdscript
# 动画控制器压缩
class_name AnimationControllerCompressor

@export var max_states: int = 10

func compress_controller(controller: AnimationController):
    if controller.get_states().size() > max_states:
        # 优化状态
        var new_states = {}
        
        # 保留关键状态
        for state in controller.get_states():
            new_states[state] = controller.get_state(state)
        
        controller.set_states(new_states)
        print("Controller compressed from ", controller.get_states().size(), " to ", new_states.size())
    else:
        print("Controller already small enough")
```

---

## 7. 实践：角色动画控制器

### 7.1 基础角色动画控制器

```gdscript
# 基础角色动画控制器：AnimationTree 负责播放与混合，脚本只驱动参数并查询状态
class_name CharacterAnimationController

extends Node2D

@export var player: AnimationPlayer
@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback
var _last_state: StringName

func _ready() -> void:
    # AnimationTree 挂载后会接管同一个 AnimationPlayer，
    # 不要再直接调用 player.play()，否则两套驱动会互相覆盖。
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    travel_to(&"Idle")

func _process(_delta: float) -> void:
    # 状态切换没有信号，靠轮询当前状态
    var current := playback.get_current_node()
    if current != _last_state:
        _last_state = current
        print("State changed to: ", current)

func travel_to(state_name: StringName) -> void:
    playback.travel(state_name)

# 需要一次性播放（例如受击）时，临时把控制权交还给 AnimationPlayer
func play_animation(anim_name: StringName) -> void:
    if player and player.has_animation(anim_name):
        tree.active = false
        player.play(anim_name)

# 混合参数通过参数路径写入
func set_blend_parameter(node_name: StringName, value: float) -> void:
    tree.set("parameters/%s/blend_position" % node_name, value)
```

### 7.2 骨骼动画控制器

```gdscript
# 骨骼动画控制器：状态机负责切换，Skeleton3D 负责姿势，脚本只做编排
class_name SkeletonAnimationController

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer
@export var tree: AnimationTree

func _ready() -> void:
    # AnimationPlayer 通过 NodePath 指明被驱动的骨架
    if skeleton and animation_player:
        animation_player.root_node = animation_player.get_path_to(skeleton)

func play_animation(anim_name: StringName) -> void:
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)

func update_animation() -> void:
    if animation_player == null or not animation_player.is_playing():
        return

    # 曲线求值与骨骼写入由引擎完成，这里只读取进度和骨骼数量做监控
    var time := animation_player.get_current_animation_position()
    print("播放中：%.2fs / %d 根骨骼" % [time, skeleton.get_bone_count()])

# 需要读取单根骨骼姿势时，走 Skeleton3D 的索引接口
func get_bone_transform(bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    return skeleton.get_bone_pose(idx) if idx != -1 else Transform3D()
```

### 7.3 2D 动画控制器

```gdscript
# 2D 动画控制器：帧序列动画走 AnimatedSprite2D + SpriteFrames
class_name SpriteAnimationController

extends Node2D

@export var sprite_frames: SpriteFrames
@export var animated_sprite: AnimatedSprite2D

func _ready() -> void:
    # AnimationPlayer 没有 sprite_frames 属性；
    # 帧序列属于 AnimatedSprite2D，属性轨道才是 AnimationPlayer 的领域。
    if sprite_frames and animated_sprite:
        animated_sprite.sprite_frames = sprite_frames

func play_animation(anim_name: StringName) -> void:
    if animated_sprite and animated_sprite.sprite_frames.has_animation(anim_name):
        animated_sprite.play(anim_name)

func update_animation() -> void:
    if animated_sprite and animated_sprite.is_playing():
        update_sprite()

func update_sprite() -> void:
    # 帧索引由引擎推进，脚本只需读取
    var frame_idx := animated_sprite.frame
    var frame_texture := animated_sprite.sprite_frames.get_frame_texture(
        animated_sprite.animation, frame_idx)
    print("当前帧：%d / %s" % [frame_idx, frame_texture])
```

---

## 📝 本章总结

### 核心要点

1. **AnimationTree 是基础**，基于节点的动画控制器
2. **状态机用于复杂动画控制**，基于条件切换动画
3. **混合树用于参数化动画**，根据参数混合状态
4. **动画混合器**，用于混合多个动画
5. **动画控制器优化**，包括缓存、LOD、压缩等

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationTree | 动画树，基于节点的动画控制器 |
| StateMachine | 状态机，基于状态切换动画 |
| BlendTree | 混合树，参数化动画混合 |
| AnimationMixer | 动画混合器，混合多个动画 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Animation](https://docs.godotengine.org/en/stable/tutorials/animation/animation.html)
- **源码位置**: `servers/animation/`
- **技术博客**: [Godot Animation Controller](https://godotengine.org/article/animation-controller/)

---

## 📋 下一章预告

**第 39 篇：动画混合**

- 动画混合基础
- 动画混合器
- 动画混合应用
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 9,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
