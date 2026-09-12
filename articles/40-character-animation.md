# 第 40 篇：角色动画

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 39 章 动画混合  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

角色动画是游戏开发中最为复杂和重要的动画类型之一。从简单的人物移动到复杂的表情和肢体语言，角色动画能够为游戏带来生动的视觉效果和沉浸式体验。

Godot 提供了多种角色动画技术，包括基础角色动画、骨骼动画、表情动画、面部动画等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解角色动画的基本概念
- 掌握基础角色动画
- 学会骨骼动画实现
- 熟悉表情和面部动画
- 掌握角色动画优化

---

## 1. 角色动画基础

### 1.1 角色动画类型

```
角色动画类型:
┌─────────────────────────────────────────────────────────────┐
│                      角色动画类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 基础动画：移动、旋转、缩放                              │
│  2. 骨骼动画：基于骨骼系统的动画                           │
│  3. 表情动画：面部表情和情绪                              │
│  4. 肢体动画：手部、腿部动作                               │
│  5. 姿态动画：站立、行走、奔跑、跳跃等                     │
│  6. 过渡动画：从一个动作平滑过渡到另一个动作               │
│  7. 互动动画：与环境和其他角色互动                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 角色动画组件

```
角色动画组件:
┌─────────────────────────────────────────────────────────────┐
│                      角色动画组件                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationPlayer：动画播放器                              │
│  2. AnimationTree：动画树                                    │
│  3. Skeleton3D：骨骼系统                                      │
│  4. MeshInstance3D：网格实例                                 │
│  5. CharacterBody3D：角色身体                                 │
│  6. Skeleton3D：骨骼数据（索引访问）                           │
│  7. AnimationMixer：动画混合器                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 角色动画流程

```
角色动画处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      角色动画处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 角色动画接收输入（键盘、鼠标、AI）                      │
│  2. 动画控制器处理输入并选择合适的动画                      │
│  3. 动画树根据状态机切换动画                                │
│  4. 骨骼动画计算每个骨骼的变换                              │
│  5. 网格应用骨骼变换并渲染                                  │
│  6. 角色身体更新位置和姿态                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 基础角色动画

### 2.1 基础动画播放

```gdscript
# 基础动画播放
class_name BasicCharacterAnimation

extends CharacterBody3D

@export var animation_player: AnimationPlayer
@export var speed: float = 5.0

func _ready():
    # 设置动画播放器
    if animation_player:
        animation_player.play("idle")

func _physics_process(delta):
    # 处理输入
    handle_input(delta)
    
    # 更新动画
    update_animation()
    
    # 移动角色
    move_and_slide()

func handle_input(delta):
    # 获取输入
    var input_vector = Vector3.ZERO
    if Input.is_action_pressed("move_forward"):
        input_vector.z -= 1
    if Input.is_action_pressed("move_backward"):
        input_vector.z += 1
    if Input.is_action_pressed("move_left"):
        input_vector.x -= 1
    if Input.is_action_pressed("move_right"):
        input_vector.x += 1
    
    # 归一化输入
    if input_vector.length() > 0:
        input_vector = input_vector.normalized()
    
    # 应用速度
    velocity.x = input_vector.x * speed
    velocity.z = input_vector.z * speed

func update_animation():
    # 根据速度更新动画
    if velocity.length() > 0.1:
        if animation_player.get_current_animation() != "walk":
            animation_player.play("walk")
    else:
        if animation_player.get_current_animation() != "idle":
            animation_player.play("idle")
```

### 2.2 动画状态机

```gdscript
# 动画状态机
class_name AnimationStateController

extends Node3D

@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine

func _ready():
    # 设置初始状态
    if state_machine:
        state_machine.transition_to("Idle")

func _process(delta):
    # 根据角色状态更新动画状态
    var current_state = state_machine.get_current_state()
    
    if is_moving():
        if current_state != "Walk":
            state_machine.transition_to("Walk")
    else:
        if current_state != "Idle":
            state_machine.transition_to("Idle")
    
    if is_running():
        if current_state != "Run":
            state_machine.transition_to("Run")
    
    if is_jumping():
        if current_state != "Jump":
            state_machine.transition_to("Jump")

func is_moving() -> bool:
    return $CharacterBody3D.velocity.length() > 0.1

func is_running() -> bool:
    return $CharacterBody3D.velocity.length() > 3.0

func is_jumping() -> bool:
    return $CharacterBody3D.is_on_floor() and Input.is_action_just_pressed("jump")
```

### 2.3 动画混合

```gdscript
# 动画混合
class_name AnimationBlendingController

extends Node3D

@export var animation_player: AnimationPlayer
@export var blend_node: AnimationNodeBlend2

func _ready():
    # 设置混合节点
    if blend_node:
        blend_node.set_input(0, $Idle)
        blend_node.set_input(1, $Walk)
        blend_node.set_blend_amount(0.0)

func _process(delta):
    # 更新混合
    update_blending()

func update_blending():
    if blend_node:
        var speed = $CharacterBody3D.velocity.length()
        var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
        blend_node.set_blend_amount(blend_amount)
```

---

## 3. 骨骼动画

### 3.1 骨骼系统

```gdscript
# 骨骼系统：脚本直接挂在 Skeleton3D 上，用索引访问骨骼
class_name SkeletonController

extends Skeleton3D

@export var animation_player: AnimationPlayer
@export var mesh: MeshInstance3D

func _ready() -> void:
    # 绑定网格到骨架
    if mesh:
        mesh.skeleton = mesh.get_path_to(self)

    # AnimationPlayer 通过 NodePath 指明被驱动的骨架
    if animation_player:
        animation_player.root_node = animation_player.get_path_to(self)

func play_animation(anim_name: StringName) -> void:
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)

func update_bones() -> void:
    if animation_player == null:
        return

    # 曲线求值与骨骼写入由引擎完成，脚本侧只查询进度
    var time := animation_player.get_current_animation_position()
    var anim := animation_player.get_animation(&"walk")
    if anim == null:
        return
    print("播放中：%.2fs / %d 根骨骼 / %d 条轨道" % [
        time, get_bone_count(), anim.get_track_count()])

func get_bone_transform(bone_name: StringName) -> Transform3D:
    var idx := find_bone(bone_name)
    return get_bone_pose(idx) if idx != -1 else Transform3D()
```

### 3.2 骨骼约束

```gdscript
# 骨骼约束
class_name BoneConstraint

extends Node3D

@export var skeleton: Skeleton3D
@export var bone_name: String
@export var target_node: Node3D

func _ready():
    if skeleton and not bone_name.empty():
        # 连接更新信号
        skeleton.skeleton_updated.connect(_on_skeleton_updated)

func _on_skeleton_updated():
    # 应用约束
    apply_constraint()

func apply_constraint() -> void:
    var idx := skeleton.find_bone(bone_name)
    if idx == -1 or target_node == null:
        return

    # 骨骼不是节点，没有 global_transform；全局姿势用 get_bone_global_pose() 读取
    var bone_pose := skeleton.get_bone_global_pose(idx)
    var direction := (target_node.global_transform.origin - bone_pose.origin).normalized()

    # 计算约束后的姿势：沿方向推出固定距离
    var constrained := bone_pose
    constrained.origin = bone_pose.origin + direction * 1.0

    # 用 override 写回：amount 是权重，persistent=true 表示每帧保持覆盖
    skeleton.set_bone_global_pose_override(idx, constrained, 1.0, true)
```

### 3.3 骨骼跟随

```gdscript
# 骨骼跟随
class_name BoneFollower

extends Node3D

@export var skeleton: Skeleton3D
@export var bone_name: String
@export var target_bone: String
@export var follow_amount: float = 1.0

func _ready():
    if skeleton and not bone_name.empty() and not target_bone.empty():
        skeleton.skeleton_updated.connect(_on_skeleton_updated)

func _on_skeleton_updated():
    # 应用跟随
    apply_follow()

func apply_follow() -> void:
    var idx := skeleton.find_bone(bone_name)
    var target_idx := skeleton.find_bone(target_bone)
    if idx == -1 or target_idx == -1:
        return

    var current := skeleton.get_bone_global_pose(idx)
    var target := skeleton.get_bone_global_pose(target_idx)

    # 按权重插值位置与旋转（基向量用 slerp 保持正交性）
    var blended := current
    blended.origin = current.origin.lerp(target.origin, follow_amount)
    blended.basis = current.basis.slerp(target.basis, follow_amount)

    skeleton.set_bone_global_pose_override(idx, blended, 1.0, true)
```

---

## 4. 表情和面部动画

### 4.1 表情基础

```gdscript
# 表情系统
class_name ExpressionController

extends Node3D

@export var mesh: MeshInstance3D
@export var animation_player: AnimationPlayer

var current_expression = "neutral"

func _ready():
    # 设置初始表情
    set_expression("neutral")

func set_expression(expression: String):
    current_expression = expression
    
    # 应用表情
    match expression:
        "neutral":
            set_neutral_expression()
        "happy":
            set_happy_expression()
        "sad":
            set_sad_expression()
        "angry":
            set_angry_expression()
        "surprised":
            set_surprised_expression()

func set_neutral_expression():
    # 设置中性表情
    $Mouth.position.y = 0
    $Eyes.scale = Vector3(1, 1, 1)
    $Cheeks.scale = Vector3(1, 1, 1)

func set_happy_expression():
    # 设置开心表情
    $Mouth.position.y = 0.2
    $Eyes.scale = Vector3(1.2, 1.2, 1.2)
    $Cheeks.scale = Vector3(1.1, 1.1, 1.1)

func set_sad_expression():
    # 设置悲伤表情
    $Mouth.position.y = -0.2
    $Eyes.scale = Vector3(0.8, 0.8, 0.8)
    $Cheeks.scale = Vector3(0.9, 0.9, 0.9)

func set_angry_expression():
    # 设置生气表情
    $Mouth.position.y = -0.1
    $Eyes.scale = Vector3(0.9, 0.9, 0.9)
    $Eyebrows.position.y = 0.1

func set_surprised_expression():
    # 设置惊讶表情
    $Mouth.position.y = 0.3
    $Eyes.scale = Vector3(1.3, 1.3, 1.3)
    $Eyebrows.position.y = -0.2
```

### 4.2 面部动画

```gdscript
# 面部动画
class_name FacialAnimationController

extends Node3D

@export var mesh: MeshInstance3D
@export var animation_player: AnimationPlayer

func _ready():
    # 设置动画播放器
    if animation_player:
        animation_player.play("neutral")

func play_expression(expression: String):
    if animation_player and has_animation(expression):
        animation_player.play(expression)

func _on_speak():
    # 播放说话动画
    play_expression("speak")

func _on_happy():
    # 播放开心动画
    play_expression("happy")

func _on_sad():
    # 播放悲伤动画
    play_expression("sad")

func _on_angry():
    # 播放生气动画
    play_expression("angry")

func _on_surprised():
    # 播放惊讶动画
    play_expression("surprised")
```

### 4.3 表情过渡

```gdscript
# 表情过渡
class_name ExpressionTransition

extends Node3D

@export var expression_controller: ExpressionController
@export var transition_duration: float = 0.5

var current_transition_time = 0.0
var start_expression = ""
var target_expression = ""

func _ready():
    if expression_controller:
        start_expression = expression_controller.current_expression
        target_expression = start_expression

func _process(delta):
    # 更新过渡
    if current_transition_time < transition_duration:
        current_transition_time += delta
        
        # 计算混合比例
        var t = current_transition_time / transition_duration
        
        # 混合表达式
        interpolate_expression(t)

func interpolate_expression(t: float):
    if expression_controller:
        # 插值中性
        if start_expression == "neutral":
            # 从中间插值到目标
            if target_expression == "happy":
                # 混合中性和开心
                pass
            elif target_expression == "sad":
                # 混合中性和悲伤
                pass
        
        # 插值开心
        elif start_expression == "happy":
            if target_expression == "neutral":
                # 从开心插值到中间
                pass

func transition_to_expression(expression: String):
    start_expression = expression_controller.current_expression
    target_expression = expression
    current_transition_time = 0.0
```

---

## 5. 角色动画优化

### 5.1 动画缓存

```gdscript
# 动画缓存：运行时代码合成 Animation 资源
class_name CharacterAnimationCache

var cache: Dictionary = {}

func get_animation(anim_name: StringName) -> Animation:
    if cache.has(anim_name):
        return cache[anim_name]

    var anim := Animation.new()
    anim.length = 1.0

    # 一条 TYPE_TRANSFORM_3D 轨道即可同时驱动位置 / 旋转 / 缩放；
    # 不存在 TRANSFORM_3D、ROTATION、SCALE 三种并列的轨道类型。
    var track_idx := anim.add_track(Animation.TYPE_TRANSFORM_3D)
    anim.track_set_path(track_idx, NodePath("Skeleton3D:Root"))
    anim.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    anim.track_insert_key(track_idx, 1.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])

    cache[anim_name] = anim
    return anim

func clear_cache() -> void:
    cache.clear()
```

### 5.2 角色动画LOD

```gdscript
# 角色动画LOD
class_name CharacterAnimationLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_animations: Array = ["simple", "medium", "complex"]

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

### 5.3 骨骼动画优化

```gdscript
# 骨骼动画优化
class_name SkeletonAnimationOptimizer

@export var max_bones: int = 50

func optimize_skeleton(skeleton: Skeleton3D) -> void:
    # 骨骼列表来自导入的模型，运行时不能增删；
    # 正确做法是用 set_bone_enabled() 把不参与动画的骨骼排除在求值之外
    var disabled := 0

    for i in skeleton.get_bone_count():
        var bone_name := skeleton.get_bone_name(i)
        var keep := i < max_bones or is_important_bone(bone_name)
        if skeleton.is_bone_enabled(i) != keep:
            skeleton.set_bone_enabled(i, keep)
            if not keep:
                disabled += 1

    print("Skeleton optimized: %d 根骨骼已停用" % disabled)

func is_important_bone(bone_name: String) -> bool:
    # 判断骨骼是否重要
    var important_bones = [
        "Root", "Spine", "Chest", "Head",
        "LeftArm", "LeftForearm", "LeftHand",
        "RightArm", "RightForearm", "RightHand",
        "LeftLeg", "LeftKnee", "LeftFoot",
        "RightLeg", "RightKnee", "RightFoot"
    ]
    
    forimportant_bone in important_bones:
        if bone_name.contains(important_bone):
            return true
    
    return false
```

---

## 6. 实践：完整角色动画系统

### 6.1 基础角色动画系统

```gdscript
# 基础角色动画系统
class_name BasicCharacterAnimationSystem

extends CharacterBody3D

@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine
@export var speed: float = 5.0

func _ready():
    # 设置初始状态
    if state_machine:
        state_machine.transition_to("Idle")

func _physics_process(delta):
    # 处理输入
    handle_input(delta)
    
    # 更新动画
    update_animation()

func handle_input(delta):
    # 获取输入
    var input_vector = Vector3.ZERO
    if Input.is_action_pressed("move_forward"):
        input_vector.z -= 1
    if Input.is_action_pressed("move_backward"):
        input_vector.z += 1
    if Input.is_action_pressed("move_left"):
        input_vector.x -= 1
    if Input.is_action_pressed("move_right"):
        input_vector.x += 1
    
    # 归一化输入
    if input_vector.length() > 0:
        input_vector = input_vector.normalized()
    
    # 应用速度
    velocity.x = input_vector.x * speed
    velocity.z = input_vector.z * speed

func update_animation():
    # 根据状态更新动画
    if state_machine:
        if velocity.length() > 0.1:
            if state_machine.get_current_state() != "Walk":
                state_machine.transition_to("Walk")
        else:
            if state_machine.get_current_state() != "Idle":
                state_machine.transition_to("Idle")
        
        if velocity.length() > 3.0:
            if state_machine.get_current_state() != "Run":
                state_machine.transition_to("Run")
        
        if is_on_floor() and Input.is_action_just_pressed("jump"):
            if state_machine.get_current_state() != "Jump":
                state_machine.transition_to("Jump")
```

### 6.2 骨骼动画系统

```gdscript
# 骨骼动画系统
class_name CharacterSkeletonAnimationSystem

extends Skeleton3D

@export var animation_player: AnimationPlayer
@export var mesh: MeshInstance3D
@export var state_machine: AnimationNodeStateMachine

func _ready():
    # 绑定骨骼到网格
    if mesh:
        mesh.skeleton = self
    
    # 设置动画播放器
    if animation_player:
        animation_player.root_node = animation_player.get_path_to(self)

func _process(delta):
    # 根据状态更新骨骼动画
    if state_machine:
        if velocity.length() > 0.1:
            if state_machine.get_current_state() != "Walk":
                state_machine.transition_to("Walk")
        else:
            if state_machine.get_current_state() != "Idle":
                state_machine.transition_to("Idle")
```

### 6.3 表情动画系统

```gdscript
# 表情动画系统
class_name ExpressionAnimationSystem

extends Node3D

@export var expression_controller: ExpressionController
@export var facial_animation: FacialAnimationController

func _ready():
    # 设置初始表情
    expression_controller.set_expression("neutral")

func _process(delta):
    # 根据角色状态更新表情
    if Input.is_action_just_pressed("happy"):
        expression_controller.set_expression("happy")
        facial_animation.play_expression("happy")
    elif Input.is_action_just_pressed("sad"):
        expression_controller.set_expression("sad")
        facial_animation.play_expression("sad")
    elif Input.is_action_just_pressed("angry"):
        expression_controller.set_expression("angry")
        facial_animation.play_expression("angry")
    elif Input.is_action_just_pressed("surprised"):
        expression_controller.set_expression("surprised")
        facial_animation.play_expression("surprised")
    else:
        expression_controller.set_expression("neutral")
        facial_animation.play_expression("neutral")
```

### 6.4 完整角色动画控制器

```gdscript
# 完整角色动画控制器
class_name FullCharacterAnimationController

extends Node3D

@export var animation_player: AnimationPlayer
@export var state_machine: AnimationNodeStateMachine
@export var expression_controller: ExpressionController
@export var facial_animation: FacialAnimationController
@export var speed: float = 5.0
@export var crouch_speed: float = 2.5

func _ready():
    # 设置初始状态
    if state_machine:
        state_machine.transition_to("Idle")
    
    # 设置初始表情
    expression_controller.set_expression("neutral")

func _process(delta):
    # 根据输入更新动画
    update_animation()

func update_animation():
    # 获取输入
    var input_vector = Vector3.ZERO
    if Input.is_action_pressed("move_forward"):
        input_vector.z -= 1
    if Input.is_action_pressed("move_backward"):
        input_vector.z += 1
    if Input.is_action_pressed("move_left"):
        input_vector.x -= 1
    if Input.is_action_pressed("move_right"):
        input_vector.x += 1
    
    # 归一化输入
    if input_vector.length() > 0:
        input_vector = input_vector.normalized()
    
    # 应用速度
    var current_speed = speed
    if Input.is_action_pressed("crouch"):
        current_speed = crouch_speed
    
    # 根据状态更新动画
    if state_machine:
        if input_vector.length() > 0.1:
            if state_machine.get_current_state() != "Walk":
                state_machine.transition_to("Walk")
        else:
            if state_machine.get_current_state() != "Idle":
                state_machine.transition_to("Idle")
        
        if input_vector.length() > 0.1 and Input.is_action_pressed("run"):
            if state_machine.get_current_state() != "Run":
                state_machine.transition_to("Run")
        
        if Input.is_action_just_pressed("jump"):
            if state_machine.get_current_state() != "Jump":
                state_machine.transition_to("Jump")
        
        if Input.is_action_just_pressed("attack"):
            if state_machine.get_current_state() != "Attack":
                state_machine.transition_to("Attack")

func play_expression(expression: String):
    expression_controller.set_expression(expression)
    facial_animation.play_expression(expression)

func update_facial_animation(is_speaking: bool):
    if is_speaking:
        facial_animation.play_expression("speak")
    else:
        facial_animation.play_expression("neutral")
```

---

## 8. 高级角色动画技术

### 8.1 运动匹配基础（Motion Matching）

运动匹配是一种数据驱动的角色动画技术，通过搜索动画数据库找到最佳匹配当前状态的动画片段。

```
运动匹配流程:
┌─────────────────────────────────────────────────────────────┐
│  1. 采集角色运动数据 → 动画数据库                           │
│  2. 每帧搜索数据库 → 找到最佳匹配动画                       │
│  3. 平滑过渡到匹配动画                                      │
│  4. 重复步骤 2-3                                            │
│                                                             │
│ 搜索特征:                                                   │
│ - 当前位置/速度/方向                                        │
│ - 骨骼姿态                                                  │
│ - 动画曲线导数                                              │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 简化的运动匹配系统
class_name MotionMatchingSystem

extends Node

@export var animation_database: Array[Dictionary] = []
@export var search_radius: float = 0.5
@export var blend_time: float = 0.1

var animation_player: AnimationPlayer
var current_pose: Dictionary = {}
var current_velocity: Vector3 = Vector3.ZERO

func _ready():
    animation_player = $AnimationPlayer
    _build_animation_database()

func _build_animation_database():
    # 从动画片段提取特征数据
    var animations = ["walk", "run", "strafe_left", "strafe_right", "backpedal"]
    
    for anim_name in animations:
        var frames = _extract_animation_frames(anim_name)
        for frame in frames:
            animation_database.append({
                "animation": anim_name,
                "time": frame["time"],
                "pose": frame["pose"],
                "velocity": frame["velocity"],
                "direction": frame["direction"]
            })

func _extract_animation_frames(anim_name: String) -> Array:
    # 提取动画的关键帧数据
    # 简化实现
    return [{"time": 0.0, "pose": {}, "velocity": Vector3.ZERO, "direction": Vector3.FORWARD}]

func update(delta):
    # 获取当前角色状态
    var desired_velocity = _get_desired_velocity()
    var current_pose = _get_current_pose()
    
    # 搜索最佳匹配
    var best_match = _search_best_match(desired_velocity, current_pose)
    
    if best_match:
        # 过渡到匹配动画
        _transition_to_animation(best_match["animation"], best_match["time"], blend_time)

func _search_best_match(desired_vel: Vector3, pose: Dictionary) -> Dictionary:
    var best_score = INF
    var best_match = null
    
    for clip in animation_database:
        # 计算速度差异
        var vel_diff = (desired_vel - clip["velocity"]).length()
        
        # 计算姿态差异（简化）
        var pose_diff = 0.0
        
        # 综合评分
        var score = vel_diff * 0.7 + pose_diff * 0.3
        
        if score < best_score:
            best_score = score
            best_match = clip
    
    return best_match

func _transition_to_animation(anim_name: String, start_time: float, blend_time: float):
    animation_player.play(anim_name, blend_time)
    animation_player.seek(start_time, true)
```

### 8.2 程序化手势系统

```gdscript
# 程序化手势生成器
class_name ProceduralGestureSystem

extends Node

@export var arm_ik: SkeletonIK3D
@export var hand_target: Node3D

# 手势定义
var gestures = {
    "wave": {
        "phases": [
            {"rotation": Vector3(0, 0, 0), "duration": 0.0},
            {"rotation": Vector3(0, 0, 45), "duration": 0.3},
            {"rotation": Vector3(0, 0, -45), "duration": 0.3},
            {"rotation": Vector3(0, 0, 45), "duration": 0.3},
            {"rotation": Vector3(0, 0, 0), "duration": 0.3}
        ]
    },
    "point": {
        "phases": [
            {"rotation": Vector3(0, 0, 0), "duration": 0.0},
            {"rotation": Vector3(0, 30, 0), "duration": 0.2},
            {"rotation": Vector3(0, 60, 0), "duration": 0.2}
        ]
    },
    "thumbs_up": {
        "phases": [
            {"rotation": Vector3(0, 0, 0), "duration": 0.0},
            {"rotation": Vector3(90, 0, 0), "duration": 0.3}
        ]
    }
}

var current_gesture: String = ""
var gesture_phase: int = 0
var gesture_timer: float = 0.0

func play_gesture(gesture_name: String):
    if gestures.has(gesture_name):
        current_gesture = gesture_name
        gesture_phase = 0
        gesture_timer = 0.0
        _apply_gesture_phase()

func _process(delta):
    if current_gesture != "":
        gesture_timer += delta
        
        var phases = gestures[current_gesture]["phases"]
        if gesture_phase < phases.size():
            var phase = phases[gesture_phase]
            
            if gesture_timer >= phase["duration"]:
                gesture_phase += 1
                gesture_timer = 0.0
                
                if gesture_phase < phases.size():
                    _apply_gesture_phase()
                else:
                    current_gesture = ""  # 完成

func _apply_gesture_phase():
    var phases = gestures[current_gesture]["phases"]
    var phase = phases[gesture_phase]
    
    # 应用旋转（简化）
    hand_target.transform.basis = Basis.from_euler(deg_to_rad(phase["rotation"]))

# 手势混合
func blend_gestures(gesture_a: String, gesture_b: String, weight: float):
    # 混合两个手势的权重
    # 用于复杂手势过渡
    pass
```

### 8.3 角色动画性能优化

```
角色动画性能优化清单:
┌─────────────────────────────────────────────────────────────┐
│ 优化项            │ 影响          │ 优化建议                │
├─────────────────────────────────────────────────────────────┤
│ 骨骼数量          │ CPU +2-5%/10 骨 │ 限制在 50-70 骨         │
│ 动画更新频率      │ 每帧计算      │ LOD 降低远处更新        │
│ 混合节点数量      │ +3-8%/个      │ 简化混合树              │
│ IK 链数量         │ +5-10%/链     │ 限制关键部位            │
│ 蒙皮顶点数        │ GPU 负载       │ 控制网格精度            │
└─────────────────────────────────────────────────────────────┘

最佳实践:
✅ 使用动画 LOD（远处简化）
✅ 禁用不可见角色的动画
✅ 缓存动画混合权重
✅ 批量更新动画
❌ 每帧重新创建动画节点
❌ 过深的混合树
❌ 不必要的 IK 计算
```

```gdscript
# 角色动画 LOD 系统
class_name CharacterAnimationLODSystem

extends Node

@export var lod_distances: Array[float] = [20.0, 50.0, 100.0]
@export var player: Node3D

var animation_tree: AnimationTree
var current_lod: int = 0

enum LODLevel {
    HIGH,     # 0-20m: 完整更新
    MEDIUM,   # 20-50m: 简化更新
    LOW,      # 50-100m: 最低更新
    DISABLED  # 100m+: 暂停
}

func _ready():
    animation_tree = $AnimationTree

func _process(delta):
    if not player:
        return
    
    var distance = global_transform.origin.distance_to(player.global_transform.origin)
    _update_lod(distance)
    
    match current_lod:
        LODLevel.HIGH:
            _update_full_animation()
        LODLevel.MEDIUM:
            _update_simplified_animation()
        LODLevel.LOW:
            _update_minimal_animation()
        LODLevel.DISABLED:
            pass  # 暂停更新

func _update_lod(distance: float):
    var old_lod = current_lod
    
    if distance < lod_distances[0]:
        current_lod = LODLevel.HIGH
    elif distance < lod_distances[1]:
        current_lod = LODLevel.MEDIUM
    elif distance < lod_distances[2]:
        current_lod = LODLevel.LOW
    else:
        current_lod = LODLevel.DISABLED
    
    if old_lod != current_lod:
        _on_lod_changed()

func _on_lod_changed():
    match current_lod:
        LODLevel.HIGH:
            animation_tree.set_process(true)
            _enable_all_features()
        LODLevel.MEDIUM:
            _disable_ik()
            _simplify_blend_tree()
        LODLevel.LOW:
            _disable_expressions()
            _reduce_update_rate()
        LODLevel.DISABLED:
            animation_tree.set_process(false)

func _enable_all_features():
    # 启用所有功能
    pass

func _disable_ik():
    # 禁用 IK
    pass

func _simplify_blend_tree():
    # 简化混合树
    pass
```

---

## 📝 本章总结

### 核心要点

1. **角色动画需要多系统协作**，包括骨骼、混合、状态机
2. **骨骼动画是核心**，IK 增强真实感
3. **表情和手势增加细节**，提升角色表现力
4. **运动匹配提供流畅移动**
5. **程序化手势丰富交互**
6. **LOD 优化提升性能**

### 关键术语

| 术语 | 解释 |
|------|------|
| Character Animation | 角色动画 |
| Skeleton Animation | 骨骼动画 |
| Facial Animation | 面部表情动画 |
| Motion Matching | 运动匹配 |
| Procedural Gesture | 程序化手势 |
| Animation LOD | 动画细节层次 |

---

## 🔗 延伸阅读

- **Skeleton3D**: <https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html>
- **AnimationPlayer**: <https://docs.godotengine.org/en/stable/classes/class_animationplayer.html>
- **BoneAttachment3D**: <https://docs.godotengine.org/en/stable/classes/class_boneattachment3d.html>
- **源码位置**: `scene/animation/`, `servers/animation/`

---

## 📋 下一章预告

**第 41 篇：动画曲线**

- 动画曲线编辑器基础
- 关键帧编辑
- 曲线调整技术
- 动画预览与优化

---

*写作时间：2026-03-20*  
*最近一次技术勘误：2026-09-12*  
*状态：✅ 完成*
