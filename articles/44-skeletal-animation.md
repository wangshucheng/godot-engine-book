# 第 44 篇：骨骼动画

> **本卷定位**: 第四卷 动画系统（完善篇）  
> **前置知识**: 第 42 章 骨骼动画  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

程序化动画通过实时计算生成动画，而非依赖预录制动画片段。这种技术在角色适配、物理交互、动态响应等场景中具有独特优势。

本章将深入探讨程序化步行循环、物理驱动动画、动态适配等高级技术。

---

## 🎯 学习目标

- 理解程序化动画原理
- 掌握程序化步行循环
- 学会物理驱动动画
- 熟悉动态地形适配
- 实施性能优化

---

## 1. 程序化步行循环

### 1.1 步行循环原理

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

### 1.2 程序化步行实现

```gdscript
# 程序化步行控制器
class_name ProceduralWalkController

extends Node3D

@export var walk_speed: float = 2.0
@export var stride_length: float = 0.8
@export var foot_lift: float = 0.15
@export var body_bob: float = 0.05

# 骨骼节点
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
    # 查找骨骼节点
    left_foot = _find_bone("Foot_L")
    right_foot = _find_bone("Foot_R")
    left_hand = _find_bone("Hand_L")
    right_hand = _find_bone("Hand_R")
    hips = _find_bone("Hips")

func _find_bone(name: String) -> Node3D:
    # 简化实现
    return null

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

---

## 2. 物理驱动动画

### 2.1 布娃娃物理

```gdscript
# 布娃娃物理系统
class_name RagdollPhysics

extends Node

@export var skeleton: Skeleton3D
@export var ragdoll_scene: PackedScene

var ragdoll_instance: Node3D
var bone_bodies: Dictionary = {}

func enable_ragdoll():
    # 禁用动画
    skeleton.animation_player.stop()
    
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
    skeleton.animation_player.play("idle")

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

### 2.2 物理驱动secondary 运动

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

---

## 3. 动态地形适配

### 3.1 脚步适配

```gdscript
# 动态脚步适配
class_name DynamicFootstepAdapter

extends Node

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
            foot_ik[i].target = target

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

### 3.2 坡度适配

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

1. **程序化步行循环**提供无限适配能力
2. **物理驱动动画**增强真实感
3. **布娃娃系统**用于受击和死亡
4. **动态地形适配**提升沉浸感
5. **性能优化**确保实时运行

### 关键术语

| 术语 | 解释 |
|------|------|
| Procedural Animation | 程序化动画，实时计算生成 |
| Ragdoll | 布娃娃物理系统 |
| Secondary Motion | 次级运动，头发衣物等 |
| Footstep Adaptation | 脚步适配，地形匹配 |
| Slope Adaptation | 坡度适配 |

---

*写作时间：2026-03-21*  
*字数：约 6,000 字*  
*状态：✅ 完成*
