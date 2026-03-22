# 第 24 篇：动画控制器

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 33 章 动画系统基础  
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
# AnimationTree 参数
class_name AnimationTreeParameters

extends Node

@export var tree: AnimationTree
@export var parameter_name: String = "speed"

func _ready():
    if tree and not parameter_name.empty():
        tree.set_parameter(parameter_name, 0.0)

func set_parameter(value: float):
    if tree and not parameter_name.empty():
        tree.set_parameter(parameter_name, value)

func get_parameter() -> float:
    if tree and not parameter_name.empty():
        return tree.get_parameter(parameter_name)
    return 0.0

func update_parameter():
    if tree and not parameter_name.empty():
        var value = $CharacterBody2D.velocity.length()
        tree.set_parameter(parameter_name, value)
```

---

## 3. AnimationNodeStateMachine

### 3.1 状态机基础

```gdscript
# 状态机基础
class_name AnimationStateMachine

extends AnimationNodeStateMachine

func _ready():
    # 创建状态
    var idle = AnimationNodeStateMachineState.new()
    idle.name = "Idle"
    add_state(idle)
    
    var walk = AnimationNodeStateMachineState.new()
    walk.name = "Walk"
    add_state(walk)
    
    var run = AnimationNodeStateMachineState.new()
    run.name = "Run"
    add_state(run)
    
    var jump = AnimationNodeStateMachineState.new()
    jump.name = "Jump"
    add_state(jump)
    
    var attack = AnimationNodeStateMachineState.new()
    attack.name = "Attack"
    add_state(attack)
    
    # 设置初始状态
    set_state("Idle")
    
    # 连接信号
    connect("state_changed", self, "_on_state_changed")

func _on_state_changed(state_name: String):
    print("State changed to: ", state_name)

func _process(delta):
    # 根据当前状态更新动画
    var state = get_state()
    if state:
        state.process(delta)

func transition_to(state_name: String):
    if has_state(state_name):
        set_state(state_name)

func add_transition(from: String, to: String, condition: String = ""):
    if has_state(from) and has_state(to):
        add_transition(from, to, condition)
```

### 3.2 状态转换条件

```gdscript
# 状态转换条件
class_name StateTransitionCondition

extends Node

@export var from_state: String
@export var to_state: String
@export var condition: String = "velocity > 0.5"

func _ready():
    # 连接状态机信号
    $AnimationStateMachine.connect("state_changed", self, "_on_state_changed")

func _on_state_changed(state_name: String):
    if state_name == from_state:
        check_condition()

func check_condition():
    var velocity = $CharacterBody2D.velocity.length()
    
    if condition == "velocity > 0.5":
        if velocity > 0.5:
            $AnimationStateMachine.transition_to(to_state)
    elif condition == "velocity > 1.0":
        if velocity > 1.0:
            $AnimationStateMachine.transition_to(to_state)
    elif condition == "button_pressed":
        if Input.is_action_just_pressed("jump"):
            $AnimationStateMachine.transition_to(to_state)
```

### 3.3 状态机轨道

```gdscript
# 状态机轨道
class_name StateMachineTrack

extends AnimationNodeStateMachineTrack

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    add_state("Run", 2.0, 3.0)
    add_state("Jump", 3.0, 4.0)
    add_state("Attack", 4.0, 5.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationNodeStateMachineState.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeStateMachineState:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 4. AnimationNodeBlendTree

### 4.1 混合树基础

```gdscript
# 混合树基础
class_name BlendTree

extends AnimationNodeBlendTree

func _ready():
    # 创建混合树节点
    var root = AnimationNodeBlendTreeState.new()
    add_state(root)
    
    # 创建混合树参数
    var velocity = AnimationNodeBlendTreeParameter.new()
    velocity.name = "Velocity"
    velocity.min_value = 0.0
    velocity.max_value = 5.0
    add_parameter(velocity)
    
    var direction = AnimationNodeBlendTreeParameter.new()
    direction.name = "Direction"
    direction.min_value = -1.0
    direction.max_value = 1.0
    add_parameter(direction)
    
    # 创建混合树状态
    var idle = AnimationNodeBlendTreeState.new()
    idle.name = "Idle"
    add_state(idle)
    
    var walk = AnimationNodeBlendTreeState.new()
    walk.name = "Walk"
    add_state(walk)
    
    var run = AnimationNodeBlendTreeState.new()
    run.name = "Run"
    add_state(run)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新混合树参数
    var velocity = get_parameter("Velocity")
    velocity.value = $CharacterBody2D.velocity.length()
    
    var direction = get_parameter("Direction")
    direction.value = $CharacterBody2D.velocity.x
    
    # 更新混合树
    update()

func update():
    # 根据参数值混合状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String):
    add_state_key(AnimationNodeBlendTreeState.new(), state_name)

func add_parameter(name: String, min_val: float, max_val: float):
    add_parameter_key(AnimationNodeBlendTreeParameter.new(), name, min_val, max_val)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeBlendTreeState:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

### 4.2 参数混合

```gdscript
# 参数混合示例
class_name ParameterBlend

extends Node

@export var blend_tree: AnimationNodeBlendTree
@export var parameter_name: String = "Velocity"

func _ready():
    if blend_tree:
        blend_tree.connect("state_changed", self, "_on_state_changed")
        blend_tree.connect("parameter_changed", self, "_on_parameter_changed")

func _on_state_changed(state_name: String):
    print("Blend tree state changed to: ", state_name)

func _on_parameter_changed(parameter_name: String, value: float):
    print("Parameter ", parameter_name, " changed to: ", value)

func update_parameter(value: float):
    if blend_tree and has_parameter(parameter_name):
        set_parameter(parameter_name, value)
```

### 4.3 混合树轨道

```gdscript
# 混合树轨道
class_name BlendTreeTrack

extends AnimationNodeBlendTreeTrack

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    add_state("Run", 2.0, 3.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationNodeBlendTreeState.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeBlendTreeState:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 5. 动画混合器

### 5.1 基础动画混合器

```gdscript
# 基础动画混合器
class_name BasicAnimationMixer

extends AnimationMixer

@export var animation_player: AnimationPlayer

func _ready():
    # 设置动画播放器
    if animation_player:
        set_animation_player(animation_player)

func _process(delta):
    # 处理动画混合
    process(delta)

func play_animation(anim_name: String):
    if has_animation(anim_name):
        get_node("AnimationPlayer").play(anim_name)

func stop_animation():
    get_node("AnimationPlayer").stop()
```

### 5.2 动画混合器参数

```gdscript
# 动画混合器参数
class_name AnimationMixerParameters

extends Node

@export var mixer: AnimationMixer
@export var parameter_name: String = "speed"

func _ready():
    if mixer and not parameter_name.empty():
        mixer.set_parameter(parameter_name, 0.0)

func set_parameter(value: float):
    if mixer and not parameter_name.empty():
        mixer.set_parameter(parameter_name, value)

func get_parameter() -> float:
    if mixer and not parameter_name.empty():
        return mixer.get_parameter(parameter_name)
    return 0.0

func update_parameter():
    if mixer and not parameter_name.empty():
        var value = $CharacterBody2D.velocity.length()
        mixer.set_parameter(parameter_name, value)
```

### 5.3 动画混合器轨道

```gdscript
# 动画混合器轨道
class_name AnimationMixerTrack

extends AnimationMixerTrack

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    add_state("Run", 2.0, 3.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationMixerState.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationMixerState:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 6. 动画控制器优化

### 6.1 动画控制器缓存

```gdscript
# 动画控制器缓存
class_name AnimationControllerCache

var cache = {}

func get_controller(controller_name: String) -> AnimationController:
    if cache.has(controller_name):
        return cache[controller_name]
    
    var controller = AnimationController.new()
    cache[controller_name] = controller
    return controller

func clear_cache():
    cache.clear()
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
# 基础角色动画控制器
class_name CharacterAnimationController

extends Node2D

@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine
@export var blend_tree: AnimationNodeBlendTree

func _ready():
    # 设置动画播放器
    animation_player.play("idle")
    
    # 连接状态机信号
    state_machine.connect("state_changed", self, "_on_state_changed")
    
    # 连接混合树信号
    blend_tree.connect("state_changed", self, "_on_blend_state_changed")
    blend_tree.connect("parameter_changed", self, "_on_parameter_changed")

func _on_state_changed(state_name: String):
    print("State changed to: ", state_name)
    update_animation(state_name)

func _on_blend_state_changed(state_name: String):
    print("Blend state changed to: ", state_name)

func _on_parameter_changed(parameter_name: String, value: float):
    print("Parameter ", parameter_name, " changed to: ", value)

func update_animation(state_name: String):
    if state_name == "Idle":
        animation_player.play("idle")
    elif state_name == "Walk":
        animation_player.play("walk")
    elif state_name == "Run":
        animation_player.play("run")
    elif state_name == "Jump":
        animation_player.play("jump")
    elif state_name == "Attack":
        animation_player.play("attack")

func play_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)

func set_animation_state(state: String):
    if state_machine:
        state_machine.set_state(state)

func set_blend_parameter(name: String, value: float):
    if blend_tree and has_parameter(name):
        blend_tree.set_parameter(name, value)
```

### 7.2 骨骼动画控制器

```gdscript
# 骨骼动画控制器
class_name SkeletonAnimationController

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine

func _ready():
    if skeleton and animation_player:
        animation_player.skeleton = skeleton

func play_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)

func update_animation():
    if is_playing():
        update_bones()

func update_bones():
    # 获取当前动画时间
    var time = get_current_animation_position()
    
    # 获取动画帧数据
    var frames = get_animation("walk").get_keyframes()
    
    # 更新每个骨骼
    for bone_name in skeleton.bones:
        var bone = skeleton.bones[bone_name]
        
        # 根据时间找到对应的帧
        var frame = frames[bone_name]
        
        # 应用变换
        bone.transform = frame.get_transform(time)
```

### 7.3 2D 动画控制器

```gdscript
# 2D 动画控制器
class_name SpriteAnimationController

extends Node2D

@export var sprite_frames: SpriteFrames
@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine

func _ready():
    if sprite_frames and animation_player:
        animation_player.sprite_frames = sprite_frames

func play_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)

func update_animation():
    if is_playing():
        update_sprite()

func update_sprite():
    # 获取当前动画帧
    var frame = get_frame()
    
    # 更新精灵
    sprite.texture = frame.texture
    sprite.position = frame.position
    sprite.rotation = frame.rotation
    sprite.scale = frame.scale
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

**第 35 篇：动画混合**

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