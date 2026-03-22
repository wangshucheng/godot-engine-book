# 第 23 篇：动画系统基础

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 32 章 物理性能优化  
> **难度等级**: ⭐⭐ 中级

---

## 📖 本章导读

动画系统是游戏开发中实现角色和物体动态效果的关键组件。从简单的角色动画到复杂的机械动画，动画系统能够为游戏带来生动的视觉效果和交互体验。

Godot 提供了多种动画系统，包括动画播放器、动画混合器、动画控制器等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解动画系统的基本概念
- 掌握动画播放器使用
- 学会动画混合器应用
- 熟悉动画控制器
- 掌握骨骼动画系统

---

## 1. 动画系统基础

### 1.1 动画类型

```
动画类型分类:
┌─────────────────────────────────────────────────────────────┐
│                      动画类型                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 关键帧动画：通过关键帧定义动画（最常用）                │
│  2. 过渡动画：基于状态机自动切换动画                       │
│  3. 程序化动画：通过脚本生成动画                           │
│  4. 骨骼动画：基于骨骼系统的动画                          │
│  5. 视频动画：使用视频文件作为动画                          │
│  6. 2D 动画：2D 物体的动画                                 │
│  7. 3D 动画：3D 物体的动画                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画组件

```
动画系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      动画组件                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationPlayer：动画播放器                               │
│  2. AnimationNodeStateMachine：动画状态机                    │
│  3. AnimationNodeBlendTree：动画混合树                        │
│  4. AnimationNodeStateMachineTrack：状态机轨道                │
│  5. AnimationNodeBlendTreeTrack：混合树轨道                  │
│  6. AnimationNodeBlendTreeState：混合树状态                  │
│  7. AnimationNodeBlendTreeParameter：混合树参数              │
│  8. AnimationNodeStateMachineState：状态机状态              │
│  9. AnimationNodeStateMachineParameter：状态机参数          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画流程

```
动画处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画处理流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 动画播放器接收时间更新信号                               │
│  2. 动画播放器调用动画节点处理动画                           │
│  3. 动画节点根据时间更新动画曲线                             │
│  4. 动画节点更新节点属性（位置、旋转、缩放）                 │
│  5. 节点应用变换到场景物体                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 动画时间

```gdscript
# 动画时间管理
class_name AnimationTimeManager

@export var playback_speed: float = 1.0
@export var time_scale: float = 1.0

var current_time: float = 0.0

func _process(delta):
    current_time += delta * playback_speed * time_scale

func get_time():
    return current_time

func reset_time():
    current_time = 0.0

func set_time(time: float):
    current_time = time
```

---

## 2. 动画播放器

### 2.1 基础动画播放器

```gdscript
# 基础动画播放器
class_name BasicAnimationPlayer

extends AnimationPlayer

@export var animation_name: String = "walk"
@export var loop: bool = true

func _ready():
    # 设置播放器
    if not animation_name.empty():
        play(animation_name)
    
    # 启用循环
    if loop:
        set_loop_mode(LoopMode.LOOP)

func _process(delta):
    # 检查动画是否播放完成
    if is_playing() and not loop:
        stop()

func play_animation(anim_name: String):
    if has_animation(anim_name):
        play(anim_name)
    else:
        print("Animation not found: ", anim_name)

func stop_animation():
    stop()
```

### 2.2 动画播放控制

```gdscript
# 动画播放控制
class_name AnimationController

@export var animation_player: AnimationPlayer
@export var animation_name: String

func _ready():
    if animation_player and not animation_name.empty():
        animation_player.play(animation_name)

func play():
    if animation_player and not animation_name.empty():
        animation_player.play(animation_name)

func stop():
    if animation_player:
        animation_player.stop()

func set_speed(speed: float):
    if animation_player:
        animation_player.set_speed_scale(speed)

func set_loop(loop: bool):
    if animation_player:
        animation_player.set_loop_mode(loop ? LoopMode.LOOP : LoopMode.ONCE)

func set_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)
```

### 2.3 动画事件

```gdscript
# 动画事件处理
class_name AnimationEventProcessor

extends Node3D

@export var animation_player: AnimationPlayer
@export var event_name: String

func _ready():
    if animation_player and not event_name.empty():
        animation_player.connect("animation_finished", self, "_on_animation_finished")
        animation_player.connect("animation_started", self, "_on_animation_started")

func _on_animation_started(anim_name: String):
    print("Animation started: ", anim_name)

func _on_animation_finished(anim_name: String):
    print("Animation finished: ", anim_name)
    # 可以在这里添加动画结束后的逻辑

func trigger_event(event_name: String):
    if animation_player:
        animation_player.seek(animation_player.length())
```

---

## 3. 动画状态机

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

extends Node3D

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
    var velocity = $CharacterBody3D.linear_velocity.length()
    
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

## 4. 动画混合树

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
    velocity.value = $CharacterBody3D.linear_velocity.length()
    
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

extends Node3D

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

## 5. 骨骼动画系统

### 5.1 骨骼基础

```gdscript
# 骨骼系统基础
class_name SkeletonSystem

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer

func _ready():
    if skeleton and animation_player:
        animation_player.skeleton = skeleton

func play_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)

func set_bone_transform(bone_name: String, transform: Transform3D):
    if skeleton and skeleton.has_bone(bone_name):
        skeleton.bones[bone_name].transform = transform

func get_bone_transform(bone_name: String) -> Transform3D:
    if skeleton and skeleton.has_bone(bone_name):
        return skeleton.bones[bone_name].transform
    return Transform3D()

func add_bone(bone_name: String, parent: String = ""):
    if not skeleton.has_bone(bone_name):
        var bone = Bone3D.new()
        bone.name = bone_name
        if parent:
            skeleton.bones[parent].add_child(bone)
        else:
            skeleton.add_child(bone)
        skeleton.bones[bone_name] = bone
        return bone
    return null

func remove_bone(bone_name: String):
    if skeleton and skeleton.has_bone(bone_name):
        skeleton.bones[bone_name].queue_free()
        skeleton.bones.erase(bone_name)
```

### 5.2 骨骼动画播放器

```gdscript
# 骨骼动画播放器
class_name SkeletonAnimationPlayer

extends AnimationPlayer

func _ready():
    # 设置骨骼动画播放器
    if has_animation("walk"):
        play("walk")

func _process(delta):
    # 更新骨骼动画
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

### 5.3 骨骼绑定

```gdscript
# 骨骼绑定
class_name SkeletonBinder

extends Node3D

@export var mesh: MeshInstance3D
@export var skeleton: Skeleton3D

func _ready():
    # 绑定骨骼到网格
    if mesh and skeleton:
        mesh.skeleton = skeleton
        mesh.set_surface_skeleton(0, skeleton)
    
    # 创建骨骼
    create_skeleton()

func create_skeleton():
    # 创建简单的骨骼结构
    var root = skeleton.bones["Root"]
    
    # 腿部
    var left_leg = add_bone("LeftLeg", "Root")
    var right_leg = add_bone("RightLeg", "Root")
    
    # 腿部关节
    var left_knee = add_bone("LeftKnee", "LeftLeg")
    var right_knee = add_bone("RightKnee", "RightLeg")
    
    # 腿部末端
    var left_foot = add_bone("LeftFoot", "LeftKnee")
    var right_foot = add_bone("RightFoot", "RightKnee")
    
    # 腿部骨骼设置
    left_leg.transform = Transform3D(Basis(), Vector3(0, -0.5, 0))
    left_knee.transform = Transform3D(Basis(), Vector3(0, -0.3, 0))
    left_foot.transform = Transform3D(Basis(), Vector3(0, -0.2, 0))
    
    right_leg.transform = Transform3D(Basis(), Vector3(0, -0.5, 0))
    right_knee.transform = Transform3D(Basis(), Vector3(0, -0.3, 0))
    right_foot.transform = Transform3D(Basis(), Vector3(0, -0.2, 0))
    
    # 上身
    var spine = add_bone("Spine", "Root")
    var chest = add_bone("Chest", "Spine")
    var head = add_bone("Head", "Chest")
    
    # 上身骨骼设置
    spine.transform = Transform3D(Basis(), Vector3(0, 0.5, 0))
    chest.transform = Transform3D(Basis(), Vector3(0, 0.3, 0))
    head.transform = Transform3D(Basis(), Vector3(0, 0.2, 0))
    
    # 手臂
    var left_arm = add_bone("LeftArm", "Chest")
    var right_arm = add_bone("RightArm", "Chest")
    
    # 手臂关节
    var left_elbow = add_bone("LeftElbow", "LeftArm")
    var right_elbow = add_bone("RightElbow", "RightArm")
    
    # 手臂末端
    var left_hand = add_bone("LeftHand", "LeftElbow")
    var right_hand = add_bone("RightHand", "RightElbow")
    
    # 手臂骨骼设置
    left_arm.transform = Transform3D(Basis(), Vector3(-0.3, 0.2, 0))
    left_elbow.transform = Transform3D(Basis(), Vector3(0, -0.2, 0))
    left_hand.transform = Transform3D(Basis(), Vector3(0, -0.1, 0))
    
    right_arm.transform = Transform3D(Basis(), Vector3(0.3, 0.2, 0))
    right_elbow.transform = Transform3D(Basis(), Vector3(0, -0.2, 0))
    right_hand.transform = Transform3D(Basis(), Vector3(0, -0.1, 0))
```

---

## 6. 动画优化

### 6.1 动画压缩

```gdscript
# 动画压缩
class_name AnimationCompressor

@export var max_keyframes: int = 100

func compress_animation(anim: Animation):
    if anim.get_keyframes().size() > max_keyframes:
        # 优化关键帧
        var new_keys = {}
        
        # 保留关键帧
        for bone in anim.get_keyframes():
            var keys = anim.get_keyframes(bone)
            new_keys[bone] = keys.slice(0, max_keyframes)
        
        anim.set_keyframes(new_keys)
        print("Animation compressed from ", anim.get_keyframes().size(), " to ", new_keys.size())
    else:
        print("Animation already small enough")
```

### 6.2 动画LOD

```gdscript
# 动画LOD
class_name AnimationLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_animations: Array = ["walk", "run", "idle"]

func update_lod(camera_position: Vector3, character: Node3D):
    var distance = camera_position.distance_to(character.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_animations.size() - 1)
    
    # 更新动画
    if lod_index < lod_animations.size():
        character.animation_player.play(lod_animations[lod_index])
```

### 6.3 动画缓存

```gdscript
# 动画缓存
class_name AnimationCache

var cache = {}

func get_animation(anim_name: String) -> Animation:
    if cache.has(anim_name):
        return cache[anim_name]
    
    var anim = Animation.new()
    anim.add_track(AnimationTrackType.TRANSFORM_3D, "Transform3D")
    anim.add_track(AnimationTrackType.ROTATION, "Rotation")
    anim.add_track(AnimationTrackType.SCALE, "Scale")
    
    cache[anim_name] = anim
    return anim

func clear_cache():
    cache.clear()
```

---

## 7. 实践：角色动画

### 7.1 基础角色动画

```gdscript
# 基础角色动画系统
class_name CharacterAnimationSystem

extends Node3D

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

### 7.2 骨骼动画系统

```gdscript
# 骨骼动画系统
class_name SkeletonAnimationSystem

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer

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

### 7.3 2D 动画系统

```gdscript
# 2D 动画系统
class_name SpriteAnimationSystem

extends Node2D

@export var sprite_frames: SpriteFrames
@export var animation_player: AnimationPlayer

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

1. **动画播放器是基础**，负责播放动画
2. **状态机用于复杂动画控制**，基于条件切换动画
3. **混合树用于参数化动画**，根据参数混合状态
4. **骨骼动画系统**，基于骨骼系统的动画
5. **动画优化**，包括压缩、LOD、缓存等

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationPlayer | 动画播放器，控制动画播放 |
| StateMachine | 状态机，基于状态切换动画 |
| BlendTree | 混合树，参数化动画混合 |
| Skeleton | 骨骼，动画系统的核心 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Animation](https://docs.godotengine.org/en/stable/tutorials/animation/animation.html)
- **源码位置**: `servers/animation/`
- **技术博客**: [Godot Animation System](https://godotengine.org/article/animation-system/)

---

## 📋 下一章预告

**第 34 篇：动画控制器**

- 动画控制器基础
- 动画混合器
- 动画曲线编辑器
- 动画混合器应用

---

*写作时间：2026-03-20*  
*字数：约 8,500 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*