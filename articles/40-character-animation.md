# 第 40 篇：角色动画

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 39 章 动画混合  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

角色动画是游戏开发中最为复杂和重要的动画类型之一。从简单的人物移动到复杂的表情和肢体语言，角色动画能够为游戏带来生动的视觉效果和沉浸式体验。

Godot 提供了多种角色动画技术，包括基础角色动画、骨骼动画、表情动画、面部动画等。本章将深入探讨这些技术的实现和优化，并在第 9 章补上**程序化动画与物理驱动**（步行循环、布娃娃、地形适配）。

---

## 🎯 学习目标

- 理解角色动画的基本概念
- 掌握基础角色动画
- 学会骨骼动画实现
- 熟悉表情和面部动画
- 掌握角色动画优化
- 理解程序化动画与物理驱动动画的适用边界

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
        if animation_player.current_animation != "walk":
            animation_player.play("walk")
    else:
        if animation_player.current_animation != "idle":
            animation_player.play("idle")
```

### 2.2 动画状态机

```gdscript
# 动画状态机：AnimationNodeStateMachine 是「资源」，没有 transition_to() / get_current_state()；
# 运行时的切换接口是 AnimationNodeStateMachinePlayback（从 AnimationTree 的
# "parameters/playback" 参数上取回）。状态机的构建见第 43 篇。
class_name AnimationStateController

extends Node3D

@export var animation_player: AnimationPlayer
@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback

func _ready():
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(&"Idle")

func _process(_delta):
    # 根据角色状态更新动画状态
    var current_state := playback.get_current_node()

    if is_running():
        if current_state != &"Run":
            playback.travel(&"Run")
    elif is_moving():
        if current_state != &"Walk":
            playback.travel(&"Walk")
    else:
        if current_state != &"Idle":
            playback.travel(&"Idle")

    if is_jumping():
        if current_state != &"Jump":
            playback.travel(&"Jump")

func is_moving() -> bool:
    return $CharacterBody3D.velocity.length() > 0.1

func is_running() -> bool:
    return $CharacterBody3D.velocity.length() > 3.0

func is_jumping() -> bool:
    return $CharacterBody3D.is_on_floor() and Input.is_action_just_pressed("jump")
```

### 2.3 动画混合

```gdscript
# 动画混合：AnimationNodeBlend2 没有 set_input() / set_blend_amount()，
# 连线在编辑器里用 AnimationNodeBlendTree 完成，混合量走 AnimationTree 的参数路径。
class_name AnimationBlendingController

extends Node3D

@export var animation_player: AnimationPlayer
@export var tree: AnimationTree

# 混合树里该混合节点的名字（与编辑器里显示的一致）
@export var blend_node_name: StringName = &"locomotion"

func _ready():
    tree.active = true

func _process(_delta):
    # 更新混合
    update_blending()

func update_blending():
    var speed = $CharacterBody3D.velocity.length()
    var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
    # AnimationNodeBlend2 的混合量参数名是 blend_amount
    tree.set("parameters/%s/blend_amount" % blend_node_name, blend_amount)
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
    var time := animation_player.current_animation_position
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
    # has_animation() 定义在 AnimationMixer 上，必须通过 AnimationPlayer 调用
    if animation_player and animation_player.has_animation(expression):
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
# 角色动画缓存：缓存的是「角色专用的动画库」，而不是单条 Animation
# （单条 Animation 的运行时合成见第 37 篇第 6.3 节）
class_name CharacterAnimationCache

var _libraries: Dictionary = {}

func get_library(key: StringName) -> AnimationLibrary:
    if _libraries.has(key):
        return _libraries[key]

    var lib := AnimationLibrary.new()
    for anim_name in [&"idle", &"walk", &"run"]:
        var anim := Animation.new()
        anim.length = 1.0

        # 一条 TYPE_TRANSFORM_3D 轨道即可同时驱动位置 / 旋转 / 缩放；
        # 不存在 TRANSFORM_3D、ROTATION、SCALE 三种并列的轨道类型。
        var track_idx := anim.add_track(Animation.TYPE_TRANSFORM_3D)
        anim.track_set_path(track_idx, NodePath("Skeleton3D:Root"))
        anim.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
        anim.track_insert_key(track_idx, 1.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])

        lib.add_animation(anim_name, anim)

    _libraries[key] = lib
    return lib

func clear_cache() -> void:
    _libraries.clear()
```

### 5.2 角色动画LOD

通用的"按距离选动画"写法见第 37 篇第 6.2 节。
角色级的 LOD 更关心**状态机与混合树的降级**，而不是换一条动画：

```gdscript
# 角色动画 LOD：按距离调整状态机与混合树的复杂度
class_name CharacterAnimationLOD

@export var lod_distances: Array[float] = [20.0, 50.0, 100.0]

## 越远的等级越简化：0 = 完整，1 = 关 IK，2 = 关表情，3 = 停机
@export var tree: AnimationTree

func current_level(camera_position: Vector3, character: Node3D) -> int:
    var distance := camera_position.distance_to(character.global_transform.origin)
    var level := 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            level = i + 1
    return level

func apply_lod(level: int) -> void:
    match level:
        0:
            tree.active = true
        1:
            # 停用动画树 = 冻结姿势（不是降级），
            # 真正的降级要换用更简单的混合结构，见第 8.3 节
            tree.active = true
        2:
            tree.active = true
        3:
            tree.active = false
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
    
    for important_bone in important_bones:
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
@export var tree: AnimationTree
@export var speed: float = 5.0

var playback: AnimationNodeStateMachinePlayback

func _ready():
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(&"Idle")

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
    if playback == null:
        return
    var current := playback.get_current_node()

    if velocity.length() > 0.1:
        if current != &"Walk":
            playback.travel(&"Walk")
    else:
        if current != &"Idle":
            playback.travel(&"Idle")
    
    if velocity.length() > 3.0:
        if current != &"Run":
            playback.travel(&"Run")
    
    if is_on_floor() and Input.is_action_just_pressed("jump"):
        if current != &"Jump":
            playback.travel(&"Jump")
```

### 6.2 骨骼动画系统

```gdscript
# 骨骼动画系统
class_name CharacterSkeletonAnimationSystem

extends Node3D

@export var animation_player: AnimationPlayer
@export var mesh: MeshInstance3D
@export var skeleton: Skeleton3D
@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback

func _ready():
    # 绑定骨骼到网格：MeshInstance3D.skeleton 是 NodePath
    if mesh and skeleton:
        mesh.skeleton = mesh.get_path_to(skeleton)

    # 设置动画播放器
    if animation_player:
        animation_player.root_node = animation_player.get_path_to(skeleton)

    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback

func _process(_delta):
    # 根据状态更新骨骼动画
    if playback == null:
        return
    var current := playback.get_current_node()
    if velocity.length() > 0.1:
        if current != &"Walk":
            playback.travel(&"Walk")
    else:
        if current != &"Idle":
            playback.travel(&"Idle")
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
@export var tree: AnimationTree
@export var expression_controller: ExpressionController
@export var facial_animation: FacialAnimationController
@export var speed: float = 5.0
@export var crouch_speed: float = 2.5

var playback: AnimationNodeStateMachinePlayback

func _ready():
    # 设置初始状态
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(&"Idle")
    
    # 设置初始表情
    expression_controller.set_expression("neutral")

func _process(_delta):
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
    if playback == null:
        return
    var current := playback.get_current_node()

    if input_vector.length() > 0.1 and Input.is_action_pressed("run"):
        if current != &"Run":
            playback.travel(&"Run")
    elif input_vector.length() > 0.1:
        if current != &"Walk":
            playback.travel(&"Walk")
    else:
        if current != &"Idle":
            playback.travel(&"Idle")
    
    if Input.is_action_just_pressed("jump"):
        if current != &"Jump":
            playback.travel(&"Jump")
    
    if Input.is_action_just_pressed("attack"):
        if current != &"Attack":
            playback.travel(&"Attack")

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

### 8.1 运动匹配（Motion Matching）

> ⚠️ **Godot 4.x 没有内建的运动匹配支持。**
> 引擎既没有 Motion Matching 节点，也没有相关的采样 / 检索 API。
> 下面给出的是**自研方案**的思路与骨架代码，不是引擎现成能力；
> 如果你的项目需要这个功能，要么自研，要么使用第三方插件。

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

**真实可行的落地路径**（没有内建支持时的常规做法）：

| 步骤 | 做法 | Godot 侧可用 API |
|---|---|---|
| ① 采样动画库 | 离线用 DCC 工具把每段动画按固定步长采样成"骨骼姿势特征"（每根关键骨骼的位置 + 朝向） | 离线导出，或运行时用 `Animation.track_get_key_value()` + `Skeleton3D.get_bone_pose()` 采样 |
| ② 建特征库 | 把采样结果写成 KD-Tree / 网格加速结构，随项目一起加载 | 自研数据结构（GDScript 可做，简单场景用线性扫描 + 粗筛也够用） |
| ③ 每帧检索 | 取当前角色的实时骨骼特征，在特征库里找最近邻 | `Skeleton3D.get_bone_pose()` / `get_bone_global_pose()` 读取当前姿势 |
| ④ 播放与过渡 | 用 `AnimationPlayer.play()` + `seek()` 跳到匹配帧，并做短暂交叉淡入 | `AnimationPlayer.play(name, custom_blend)` + `seek(t, true)` |
| ⑤ 兜底 | 检索失败 / 置信度不足时回退到 BlendSpace 驱动的普通移动动画 | `AnimationNodeBlendSpace1D/2D`（见第 39 篇） |

> **工程建议**：多数项目用不上完整的运动匹配。Godot 4.x 的
> `AnimationNodeBlendSpace1D/2D` + 状态机已经能覆盖绝大多数第三人称移动需求；
> 把预算留给美术资产与手感调校，通常比自研运动匹配划算。

```gdscript
# 运动匹配的自研骨架：仅演示检索流程，不是引擎内建能力
class_name MotionMatchingSystem

extends Node

@export var animation_player: AnimationPlayer

## 特征库：每项记录 "动画名 / 时间 / 特征向量"
@export var animation_database: Array[Dictionary] = []
@export var search_radius: float = 0.5
@export var blend_time: float = 0.1

## 需要参与检索的骨骼（通常是骨盆 + 双脚）
@export var feature_bones: Array[StringName] = [&"Hips", &"LeftFoot", &"RightFoot"]

func _ready():
    _build_animation_database()

func _build_animation_database():
    # 真实项目里这一步应当离线完成（见上面的落地路径表格），
    # 运行时只负责检索。
    var animations: Array[StringName] = [&"walk", &"run", &"strafe_left", &"strafe_right"]
    for anim_name in animations:
        var frames := _extract_animation_frames(anim_name)
        for frame in frames:
            animation_database.append({
                "animation": anim_name,
                "time": frame["time"],
                "pose": frame["pose"],
            })

func _extract_animation_frames(anim_name: StringName) -> Array:
    # 采样实现：按固定步长取关键帧的骨骼姿势
    var frames: Array = []
    var anim := animation_player.get_animation(anim_name)
    if anim == null:
        return frames
    var step := 1.0 / 30.0
    var t := 0.0
    while t < anim.length:
        frames.append({"time": t, "pose": _sample_pose(anim, t)})
        t += step
    return frames

func _sample_pose(anim: Animation, time: float) -> PackedVector3Array:
    # 真实实现需要把动画 seek 到 time 后读取 Skeleton3D 的姿势；
    # 这里只给出特征结构。
    var pose := PackedVector3Array()
    for _bone in feature_bones:
        pose.append(Vector3.ZERO)
    return pose

func update(delta: float):
    var best_match := _search_best_match()
    if best_match.is_empty():
        return
    _transition_to_animation(best_match["animation"], best_match["time"], blend_time)

func _search_best_match() -> Dictionary:
    var best_score := INF
    var best_match := {}
    for clip in animation_database:
        var score := _pose_distance(clip["pose"], _current_feature())
        if score < best_score:
            best_score = score
            best_match = clip
    return best_match

func _current_feature() -> PackedVector3Array:
    return PackedVector3Array()

func _pose_distance(a: PackedVector3Array, b: PackedVector3Array) -> float:
    var d := 0.0
    for i in range(mini(a.size(), b.size())):
        d += a[i].distance_to(b[i])
    return d

func _transition_to_animation(anim_name: StringName, start_time: float, blend: float):
    animation_player.play(anim_name, blend)
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
│ 优化项            │ 影响              │ 优化建议              │
├─────────────────────────────────────────────────────────────┤
│ 骨骼数量          │ 姿势求值开销上升  │ 按需停用次要骨骼      │
│ 动画更新频率      │ 每帧曲线求值      │ LOD 降低远处更新      │
│ 混合节点数量      │ 节点图求值开销    │ 简化混合树            │
│ IK 链数量        │ 额外迭代求解      │ 限制关键部位          │
│ 蒙皮顶点数        │ GPU 负载          │ 控制网格精度          │
└─────────────────────────────────────────────────────────────┘

> ⚠️ 示意数据（未附测试环境）：上表只描述**定性**趋势，
> 不含任何具体的百分比或毫秒数。骨骼数、混合节点数、IK 链数对帧时间的实际影响，
> 与骨骼数、轨道数、目标机型、是否开启 GPU 蒙皮强相关，
> 必须在目标设备上用 Godot Profiler / `Performance.get_monitor()` 实测，
> 不要照搬其它引擎的经验数字。

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

## 9. 程序化动画与物理驱动

前面讲的都是"播现成动画"。这一章讲另一条路线：**动画由脚本实时计算出来**，
或者由物理模拟驱动。它与骨骼动画（第 44 篇）互补——前者是"离线做好"，后者是"在线算"。

> **版本边界（重要）**：Godot 4.x 的物理骨骼方案分两条线，起始版本不同：
> - `PhysicalBoneSimulator3D` —— **4.3 起就有**（4.3 / 4.4 的 `doc/classes/` 均可取到该类 XML）；
> - `SpringBoneSimulator3D` —— **4.4 起才提供**（4.3 的 `doc/classes/SpringBoneSimulator3D.xml` 返回 404）；
> - `SkeletonModifier3D` —— 4.3 起就有，是这两个模拟器的共同扩展点。
>
> 把这两个类一并说成"4.5+ 才有"是不准确的；4.3 用 `SkeletonModifier3D` 自研，4.4 起可直接用 `SpringBoneSimulator3D`。
> （以及 `SkeletonIK3D` / `SkeletonProfileHumanoid`）。

### 9.1 程序化步行循环

```
程序化步行循环:
┌─────────────────────────────────────────────────────────────┐
│ 关键参数：                                                  │
│ - 步幅长度（Stride Length）                                 │
│ - 步频（Step Frequency）                                    │
│ - 抬脚高度（Foot Lift）                                     │
│ - 身体起伏（Body Bob）                                      │
│                                                             │
│ 相位关系：                                                  │
│ - 左脚相位：0°                                              │
│ - 右脚相位：180°                                            │
│ - 左手相位：180°（与右脚相反）                              │
│ - 右手相位：0°（与左脚相反）                                │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 程序化步行控制器：用 BoneAttachment3D 拿到脚/手的实际节点位置
class_name ProceduralWalkController

extends Node3D

@export var walk_speed: float = 2.0
@export var stride_length: float = 0.8
@export var foot_lift: float = 0.15
@export var body_bob: float = 0.05

@export var skeleton: Skeleton3D

# 骨骼节点（由 BoneAttachment3D 提供，不是骨骼本身——骨骼不是节点）
var left_foot: Node3D
var right_foot: Node3D
var left_hand: Node3D
var right_hand: Node3D
var hips: Node3D

# 相位
var walk_phase: float = 0.0

func _ready():
    _find_bones()

func _find_bones():
    # 骨骼不是节点，要通过 BoneAttachment3D 拿到跟随骨骼的节点
    left_foot = _attach(&"Foot_L")
    right_foot = _attach(&"Foot_R")
    left_hand = _attach(&"Hand_L")
    right_hand = _attach(&"Hand_R")
    hips = _attach(&"Hips")

func _attach(bone_name: StringName) -> Node3D:
    var attachment := BoneAttachment3D.new()
    attachment.bone_name = bone_name
    skeleton.add_child(attachment)
    return attachment

func _process(delta):
    var input_direction = _get_input_direction()
    
    if input_direction.length() > 0.1:
        _update_walk(input_direction, delta)
    else:
        _reset_to_idle()

func _get_input_direction() -> Vector2:
    var direction = Vector2.ZERO
    direction.x = Input.get_axis("ui_left", "ui_right")
    direction.y = Input.get_axis("ui_up", "ui_down")
    return direction

func _update_walk(direction: Vector2, delta):
    # 更新相位
    var speed_factor = direction.length() * walk_speed
    walk_phase += speed_factor * delta * 2.0
    
    # 限制相位在 0-2π
    walk_phase = fposmod(walk_phase, TAU)
    
    # 计算脚部位置
    _update_foot(left_foot, walk_phase, direction)
    _update_foot(right_foot, walk_phase + PI, direction)
    
    # 计算手部摆动
    _update_hand(left_hand, walk_phase + PI, direction)
    _update_hand(right_hand, walk_phase, direction)
    
    # 计算身体起伏
    _update_body_bob(direction)

func _update_foot(foot: Node3D, phase: float, direction: Vector2):
    if not foot:
        return
    
    # 正弦波计算抬脚
    var lift = sin(phase) * foot_lift
    lift = max(0, lift)  # 只向上
    
    # 前后移动
    var forward_offset = cos(phase) * stride_length * 0.5
    
    # 应用变换
    var original_pos = foot.position
    foot.position = original_pos + Vector3(
        forward_offset * direction.x,
        lift,
        forward_offset * direction.y
    )

func _update_hand(hand: Node3D, phase: float, direction: Vector2):
    if not hand:
        return
    
    # 手臂摆动
    var swing = sin(phase) * 0.3  # 摆动角度
    
    hand.rotation.x = swing * direction.y
    hand.rotation.z = -swing * direction.x

func _update_body_bob(direction: Vector2):
    if not hips:
        return
    
    # 身体上下起伏
    var bob = abs(sin(walk_phase * 2.0)) * body_bob
    hips.position.y = bob * direction.length()

func _reset_to_idle():
    # 逐渐回到待机姿势
    walk_phase = 0.0
```

> **注意**：上面演示的是"直接改节点变换"的简化做法。真正把程序化动作写回角色骨架，
> 应该用 `Skeleton3D.set_bone_pose_position()` / `set_bone_pose_rotation()`
> 或 `SkeletonModifier3D`（见第 44 篇第 4 节），而不是改 `BoneAttachment3D` 的位置。

### 9.2 物理驱动动画

```gdscript
# 布娃娃物理系统
class_name RagdollPhysics

extends Node

@export var skeleton: Skeleton3D
# AnimationPlayer 与 Skeleton3D 在 4.x 中是同级节点，
# Skeleton3D 上并没有 animation_player 属性，必须自己导出引用。
@export var animation_player: AnimationPlayer
@export var ragdoll_scene: PackedScene

var ragdoll_instance: Node3D
var bone_bodies: Dictionary = {}

func enable_ragdoll():
    # 禁用动画
    if animation_player:
        animation_player.stop()
    
    # 创建布娃娃
    if ragdoll_instance:
        ragdoll_instance.queue_free()
    
    ragdoll_instance = ragdoll_scene.instantiate()
    ragdoll_instance.global_transform = skeleton.global_transform
    get_parent().add_child(ragdoll_instance)
    
    # 同步骨骼位置
    _sync_bones_to_ragdoll()
    
    # 启用物理
    _enable_physics()

func disable_ragdoll():
    # 禁用物理
    _disable_physics()
    
    # 同步回骨骼
    _sync_ragdoll_to_bones()
    
    # 移除布娃娃
    if ragdoll_instance:
        ragdoll_instance.queue_free()
        ragdoll_instance = null
    
    # 恢复动画
    if animation_player:
        animation_player.play("idle")

func _sync_bones_to_ragdoll():
    # 将骨骼位置同步到布娃娃
    for bone_name in bone_bodies:
        var bone_idx = skeleton.find_bone(bone_name)
        if bone_idx >= 0:
            var bone_pose = skeleton.get_bone_global_pose(bone_idx)
            var rigid_body = bone_bodies[bone_name]
            rigid_body.global_transform = bone_pose

func _sync_ragdoll_to_bones():
    # 将布娃娃位置同步回骨骼
    for bone_name in bone_bodies:
        var rigid_body = bone_bodies[bone_name]
        var bone_idx = skeleton.find_bone(bone_name)
        if bone_idx >= 0:
            skeleton.set_bone_global_pose_override(bone_idx, rigid_body.global_transform, 1.0, true)

func _enable_physics():
    for bone_name in bone_bodies:
        var rigid_body = bone_bodies[bone_name]
        rigid_body.freeze = false

func _disable_physics():
    for bone_name in bone_bodies:
        var rigid_body = bone_bodies[bone_name]
        rigid_body.freeze = true
```

> ⚠️ `set_bone_global_pose_override()` 在 Godot 4.3 起已标记 deprecated。
> 物理骨骼建议走 `SkeletonModifier3D`（4.4+ 提供，本书基线 4.7.2 已包含）；
> 4.3 起可用 `PhysicalBoneSimulator3D`，4.4 起还可直接用 `SpringBoneSimulator3D`。

```gdscript
# Secondary 运动（头发、衣物等）
class_name SecondaryMotion

extends Node3D

@export var spring_stiffness: float = 10.0
@export var spring_damping: float = 5.0
@export var gravity: float = 9.8

var target_position: Vector3
var current_velocity: Vector3

func _ready():
    target_position = position

func _physics_process(delta):
    # 计算目标位置（跟随父节点）
    var parent_global = get_parent().global_transform.origin
    var expected_position = parent_global + position
    
    # 弹簧力
    var displacement = position - target_position
    var spring_force = -spring_stiffness * displacement
    
    # 阻尼力
    var damping_force = -spring_damping * current_velocity
    
    # 重力
    var gravity_force = Vector3(0, -gravity, 0)
    
    # 合力
    var total_force = spring_force + damping_force + gravity_force
    
    # 更新速度（F=ma, m=1）
    current_velocity += total_force * delta
    
    # 更新位置
    position += current_velocity * delta
    
    # 限制最大位移
    position = position.clamp(Vector3(-1, -1, -1), Vector3(1, 1, 1))
```

### 9.3 动态地形适配

```gdscript
# 动态脚步适配
class_name DynamicFootstepAdapter

# 用了 global_transform / get_world_3d()，必须继承 Node3D 而不是 Node
extends Node3D

@export var foot_ik: Array[SkeletonIK3D]
@export var ray_length: float = 2.0
@export var step_smoothness: float = 10.0

var foot_targets: Array[Node3D] = []

func _ready():
    _create_foot_targets()

func _create_foot_targets():
    for i in range(foot_ik.size()):
        var target = Node3D.new()
        add_child(target)
        foot_targets.append(target)
        
        # 连接到 IK
        if i < foot_ik.size():
            # SkeletonIK3D.target 是 Transform3D，
            # 指向节点要用 target_node（NodePath）。
            # NodePath 属性按"相对于持有该属性的节点"解析，
            # 所以用 get_path_to() 而不是绝对路径。
            foot_ik[i].target_node = foot_ik[i].get_path_to(target)

func _physics_process(delta):
    for i in range(foot_targets.size()):
        _update_foot_target(i, delta)

func _update_foot_target(foot_index: int, delta):
    var target = foot_targets[foot_index]
    
    # 射线检测地面
    var from = target.global_transform.origin + Vector3.UP * ray_length
    var to = target.global_transform.origin - Vector3.UP * 0.5
    
    var space_state = get_world_3d().direct_space_state
    var query = PhysicsRayQueryParameters3D.create(from, to)
    var result = space_state.intersect_ray(query)
    
    if result.has("position"):
        # 找到地面，平滑移动
        var ground_pos = result["position"]
        target.global_transform.origin = target.global_transform.origin.lerp(
            ground_pos, 
            step_smoothness * delta
        )
        
        # 调整脚部旋转匹配地面法线
        if result.has("normal"):
            var up = -result["normal"]
            target.global_transform.basis = target.global_transform.basis.looking_at(
                target.global_transform.origin + up, 
                Vector3.FORWARD
            )
```

> **能力边界**：`SkeletonIK3D` 只能解**两骨链**。
> 需要 3 骨以上的脚部 IK（如完整腿部链）时，
> 4.4 及更早版本必须用 `SkeletonModifier3D` 自研求解器；
> 4.6+ 才有原生的 `FABRIK3D` / `CCDIK3D` 等 IK 节点。

```gdscript
# 角色坡度适配
class_name SlopeAdapter

extends CharacterBody3D

@export var max_slope_angle: float = 45.0
@export var slope_adapt_speed: float = 5.0

var target_rotation: float = 0.0

func _physics_process(delta):
    # 检测地面坡度
    var slope_angle = _get_slope_angle()
    
    # 计算目标旋转
    target_rotation = deg_to_rad(slope_angle)
    
    # 平滑旋转
    rotation.x = lerp_angle(rotation.x, target_rotation, slope_adapt_speed * delta)
    
    # 如果坡度过大，阻止移动
    if abs(slope_angle) > max_slope_angle:
        velocity = Vector3.ZERO

func _get_slope_angle() -> float:
    # 射线检测前方地面
    var from = global_transform.origin + Vector3.UP * 0.5
    var to = from + -global_transform.basis.z * 1.0
    
    var space_state = get_world_3d().direct_space_state
    var query = PhysicsRayQueryParameters3D.create(from, to)
    var result = space_state.intersect_ray(query)
    
    if result.has("normal"):
        var normal = result["normal"]
        var angle = rad_to_deg(normal.angle_to(Vector3.UP))
        return angle
    
    return 0.0
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
- **SkeletonModifier3D**: <https://docs.godotengine.org/en/stable/classes/class_skeletonmodifier3d.html>
- **源码位置**: `scene/animation/`（`animation_mixer.cpp`、`animation_player.cpp`、
  `animation_tree.cpp`、`animation_node_state_machine.cpp`、`animation_blend_space_1d.cpp`、
  `animation_blend_space_2d.cpp`、`tween.cpp`）、`scene/resources/animation.cpp`、
  `scene/resources/animation_library.cpp`、`scene/3d/skeleton_3d.cpp`

> **注意**：Godot 4.3 的 `servers/` 目录下**没有** `animation/` 子目录，动画系统全部位于 `scene/animation/`。

---

## 📋 上下篇导航

**上一篇**: [第 39 篇：动画混合](/articles/39-animation-blending.md)
**下一篇**: [第 41 篇：动画曲线](/articles/41-animation-curves.md)

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

*写作时间：2026-03-20*  
*最近一次技术勘误：2026-09-12*  
*状态：✅ 完成*
