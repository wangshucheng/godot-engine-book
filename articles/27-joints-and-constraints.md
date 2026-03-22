# 第 17 篇：关节和约束

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 26 章 物理材质  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

关节（Joints）和约束（Constraints）是物理系统中连接多个刚体、限制运动自由度的重要工具。从简单的铰链到复杂的车辆悬挂，从门轴到布娃娃系统，关节和约束让复杂的机械结构和生物运动成为可能。

Godot 提供了多种关节类型，包括铰链关节、滑块关节、锥形扭关节、通用关节等，每种关节都有其特定的用途和配置选项。

---

## 🎯 学习目标

- 理解关节和约束的基本原理
- 掌握各种关节类型的特性和用途
- 学会配置关节参数
- 熟悉关节约束的限制和驱动
- 能够创建复杂的机械结构

---

## 1. 关节基础

### 1.1 关节类型总览

```
Godot 3D 关节类型:
├── HingeJoint3D        # 铰链关节（单轴旋转）
├── SliderJoint3D       # 滑块关节（线性滑动）
├── ConeTwistJoint3D    # 锥形扭关节（球窝关节）
├── Generic6DOFJoint3D  # 6 自由度关节（完全控制）
└── PinJoint3D          # 钉关节（2D 铰链）

Godot 2D 关节类型:
├── PinJoint2D          # 钉关节（旋转）
├── GrooveJoint2D       # 凹槽关节（滑动）
└── DampedSpringJoint2D # 阻尼弹簧关节
```

### 1.2 自由度（DOF）

```
6 自由度概念:
┌─────────────────────────────────────────────────────────────┐
│                      6 自由度                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  线性自由度 (3):                                            │
│  ├─ X 轴：左右移动                                           │
│  ├─ Y 轴：上下移动                                           │
│  └─ Z 轴：前后移动                                           │
│                                                             │
│  角自由度 (3):                                              │
│  ├─ X 轴：俯仰（Pitch）                                      │
│  ├─ Y 轴：偏航（Yaw）                                        │
│  └─ Z 轴：翻滚（Roll）                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 关节创建基础

```gdscript
# 创建关节的基本步骤
func create_joint():
    # 1. 创建两个刚体
    var body_a = RigidBody3D.new()
    var body_b = RigidBody3D.new()
    
    # 2. 创建关节
    var joint = HingeJoint3D.new()
    
    # 3. 设置连接的刚体
    joint.node_a = body_a.get_path()
    joint.node_b = body_b.get_path()
    
    # 4. 设置关节位置
    joint.transform = Transform3D()
    
    # 5. 添加到场景
    add_child(joint)
```

---

## 2. 铰链关节（HingeJoint3D）

### 2.1 基础配置

```gdscript
# 创建铰链关节（门轴）
func create_hinge_joint():
    var joint = HingeJoint3D.new()
    
    # 设置旋转轴（Y 轴）
    joint.transform.basis = Basis(Vector3.UP, 0)
    
    # 设置角度限制
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_LOWER_ANGLE, deg_to_rad(-90))
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_UPPER_ANGLE, deg_to_rad(90))
    
    # 设置限制硬度
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_SOFTNESS, 0.9)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_RESTITUTION, 0.5)
    
    # 设置阻尼
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_DAMPING, 0.1)
    
    # 设置马达（可选）
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, 1.0)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_FORCE_LIMIT, 10.0)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, true)
    
    return joint
```

### 2.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| LIMIT_LOWER_ANGLE | 下限角度（弧度） | -PI/2 |
| LIMIT_UPPER_ANGLE | 上限角度（弧度） | PI/2 |
| LIMIT_SOFTNESS | 限制软度 | 0.9 |
| LIMIT_RESTITUTION | 限制反弹 | 0.5 |
| DAMPING | 阻尼 | 0.1 |
| MOTOR_TARGET_VELOCITY | 马达目标速度 | 1.0 |
| MOTOR_FORCE_LIMIT | 马达力限制 | 10.0 |
| MOTOR_ENABLED | 马达启用 | true/false |

### 2.3 应用： swinging 门

```gdscript
# 创建 swinging 门
func create_swinging_door():
    # 门框（静态）
    var frame = StaticBody3D.new()
    var frame_mesh = MeshInstance3D.new()
    frame_mesh.mesh = BoxMesh.new()
    frame_mesh.mesh.size = Vector3(0.2, 3, 0.2)
    frame.add_child(frame_mesh)
    
    # 门（刚体）
    var door = RigidBody3D.new()
    door.mass = 10
    var door_mesh = MeshInstance3D.new()
    door_mesh.mesh = BoxMesh.new()
    door_mesh.mesh.size = Vector3(0.1, 2.5, 1)
    door_mesh.position = Vector3(0.55, 0, 0)
    door.add_child(door_mesh)
    
    # 门的碰撞形状
    var door_collision = CollisionShape3D.new()
    door_collision.shape = BoxShape3D.new()
    door_collision.shape.size = Vector3(0.1, 2.5, 1)
    door_collision.position = Vector3(0.55, 0, 0)
    door.add_child(door_collision)
    
    # 铰链关节
    var hinge = HingeJoint3D.new()
    hinge.node_a = frame.get_path()
    hinge.node_b = door.get_path()
    hinge.transform.origin = Vector3(0, 1.25, 0)
    
    # 设置限制（0-90 度）
    hinge.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_LOWER_ANGLE, 0)
    hinge.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_UPPER_ANGLE, deg_to_rad(90))
    
    frame.add_child(door)
    frame.add_child(hinge)
    
    return frame
```

---

## 3. 滑块关节（SliderJoint3D）

### 3.1 基础配置

```gdscript
# 创建滑块关节（抽屉）
func create_slider_joint():
    var joint = SliderJoint3D.new()
    
    # 设置滑动轴（X 轴）
    joint.transform.basis = Basis(Vector3.RIGHT, 0)
    
    # 设置线性限制
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_LOWER, 0)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_UPPER, 0.5)
    
    # 设置限制软度
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_SOFTNESS, 0.9)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_RESTITUTION, 0.1)
    
    # 设置阻尼
    joint.set_param(SliderJoint3D.PARAM_LINEAR_DAMPING, 0.5)
    
    # 设置弹簧（可选）
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, 10.0)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_DAMPING, 1.0)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, 0.25)
    
    return joint
```

### 3.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| LINEAR_LIMIT_LOWER | 下限位置 | 0 |
| LINEAR_LIMIT_UPPER | 上限位置 | 0.5 |
| LINEAR_LIMIT_SOFTNESS | 限制软度 | 0.9 |
| LINEAR_LIMIT_RESTITUTION | 限制反弹 | 0.1 |
| LINEAR_DAMPING | 线性阻尼 | 0.5 |
| LINEAR_SPRING_STIFFNESS | 弹簧刚度 | 10.0 |
| LINEAR_SPRING_DAMPING | 弹簧阻尼 | 1.0 |
| LINEAR_SPRING_EQUILIBRIUM_POINT | 弹簧平衡点 | 0.25 |

### 3.3 应用：升降机

```gdscript
# 创建升降机平台
func create_elevator():
    # 固定轨道
    var track = StaticBody3D.new()
    var track_mesh = MeshInstance3D.new()
    track_mesh.mesh = BoxMesh.new()
    track_mesh.mesh.size = Vector3(0.2, 10, 0.2)
    track.add_child(track_mesh)
    
    # 升降平台
    var platform = RigidBody3D.new()
    platform.mass = 100
    platform.linear_damp = 0.5
    var platform_mesh = MeshInstance3D.new()
    platform_mesh.mesh = BoxMesh.new()
    platform_mesh.mesh.size = Vector3(3, 0.2, 3)
    platform.add_child(platform_mesh)
    
    # 滑块关节
    var slider = SliderJoint3D.new()
    slider.node_a = track.get_path()
    slider.node_b = platform.get_path()
    slider.transform.origin = Vector3(0, 5, 0)
    slider.transform.basis = Basis(Vector3.UP, 0)
    
    # 设置移动范围（0-10 米）
    slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_LOWER, 0)
    slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_UPPER, 10)
    
    track.add_child(platform)
    track.add_child(slider)
    
    return track
```

---

## 4. 锥形扭关节（ConeTwistJoint3D）

### 4.1 基础配置

```gdscript
# 创建锥形扭关节（肩膀）
func create_cone_twist_joint():
    var joint = ConeTwistJoint3D.new()
    
    # 设置锥形角度限制
    joint.set_param(ConeTwistJoint3D.PARAM_SWING_SPAN, deg_to_rad(45))
    joint.set_param(ConeTwistJoint3D.PARAM_TWIST_SPAN, deg_to_rad(90))
    joint.set_param(ConeTwistJoint3D.PARAM_BIAS, 0)
    
    # 设置软度
    joint.set_param(ConeTwistJoint3D.PARAM_SOFTNESS, 0.8)
    
    # 设置阻尼
    joint.set_param(ConeTwistJoint3D.PARAM_DAMPING, 0.1)
    
    # 设置弹簧（可选）
    joint.set_param(ConeTwistJoint3D.PARAM_SPRING_STIFFNESS, 10.0)
    joint.set_param(ConeTwistJoint3D.PARAM_SPRING_DAMPING, 1.0)
    
    return joint
```

### 4.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| SWING_SPAN | 摆动角度范围 | 45° |
| TWIST_SPAN | 扭转角度范围 | 90° |
| BIAS | 偏差 | 0 |
| SOFTNESS | 软度 | 0.8 |
| DAMPING | 阻尼 | 0.1 |
| SPRING_STIFFNESS | 弹簧刚度 | 10.0 |
| SPRING_DAMPING | 弹簧阻尼 | 1.0 |

### 4.3 应用：布娃娃手臂

```gdscript
# 创建布娃娃手臂
func create_ragdoll_arm():
    # 上臂
    var upper_arm = RigidBody3D.new()
    upper_arm.mass = 2
    var upper_arm_collision = CollisionShape3D.new()
    upper_arm_collision.shape = CapsuleShape3D.new()
    upper_arm_collision.shape.radius = 0.15
    upper_arm_collision.shape.height = 0.4
    upper_arm.add_child(upper_arm_collision)
    
    # 前臂
    var lower_arm = RigidBody3D.new()
    lower_arm.mass = 1.5
    var lower_arm_collision = CollisionShape3D.new()
    lower_arm_collision.shape = CapsuleShape3D.new()
    lower_arm_collision.shape.radius = 0.12
    lower_arm_collision.shape.height = 0.35
    lower_arm_collision.position = Vector3(0, -0.4, 0)
    lower_arm.add_child(lower_arm_collision)
    
    # 肘关节（锥形扭关节）
    var elbow = ConeTwistJoint3D.new()
    elbow.node_a = upper_arm.get_path()
    elbow.node_b = lower_arm.get_path()
    elbow.transform.origin = Vector3(0, -0.2, 0)
    
    # 设置肘部限制
    elbow.set_param(ConeTwistJoint3D.PARAM_SWING_SPAN, deg_to_rad(30))
    elbow.set_param(ConeTwistJoint3D.PARAM_TWIST_SPAN, deg_to_rad(120))
    
    upper_arm.add_child(lower_arm)
    upper_arm.add_child(elbow)
    
    return upper_arm
```

---

## 5. 6 自由度关节（Generic6DOFJoint3D）

### 5.1 基础配置

```gdscript
# 创建 6 自由度关节
func create_6dof_joint():
    var joint = Generic6DOFJoint3D.new()
    
    # 线性轴设置（X, Y, Z）
    for axis in range(3):
        # 启用/禁用线性运动
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LIMIT_SOFTNESS, 0.9)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_DAMPING, 0.5)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_RESTITUTION, 0.1)
    
    # 角轴设置（X, Y, Z）
    for axis in range(3):
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, 0)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, 0)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LIMIT_SOFTNESS, 0.9)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_DAMPING, 0.5)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_RESTITUTION, 0.1)
    
    return joint
```

### 5.2 轴向配置

```gdscript
# 配置特定轴向
func configure_6dof_axis(joint: Generic6DOFJoint3D, axis: int, 
                         linear_enabled: bool, angular_enabled: bool,
                         linear_range: float = 1.0, angular_range: float = PI):
    
    # 线性轴
    if linear_enabled:
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -linear_range)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, linear_range)
    else:
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
    
    # 角轴
    if angular_enabled:
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, -angular_range)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, angular_range)
    else:
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, 0)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, 0)
```

### 5.3 应用：车辆悬挂

```gdscript
# 创建车辆悬挂系统
func create_vehicle_suspension():
    # 车身
    var chassis = RigidBody3D.new()
    chassis.mass = 1000
    
    # 车轮
    var wheel = RigidBody3D.new()
    wheel.mass = 20
    
    # 6DOF 关节（悬挂）
    var suspension = Generic6DOFJoint3D.new()
    suspension.node_a = chassis.get_path()
    suspension.node_b = wheel.get_path()
    
    # Y 轴（上下）允许移动
    suspension.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.2)
    suspension.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.2)
    suspension.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, 50.0)
    suspension.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, 5.0)
    suspension.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, 0)
    
    # 其他轴锁定
    for axis in [0, 2]:
        suspension.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
        suspension.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
    
    # 所有角轴锁定
    for axis in range(3):
        suspension.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, 0)
        suspension.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, 0)
    
    return suspension
```

---

## 6. 2D 关节

### 6.1 PinJoint2D（钉关节）

```gdscript
# 创建 2D 钉关节（钟摆）
func create_pendulum():
    # 固定点
    var anchor = StaticBody2D.new()
    
    # 摆锤
    var pendulum = RigidBody2D.new()
    pendulum.mass = 1
    var collision = CollisionShape2D.new()
    collision.shape = CircleShape2D.new()
    collision.shape.radius = 0.2
    pendulum.add_child(collision)
    pendulum.position = Vector2(0, 1)
    
    # 钉关节
    var pin = PinJoint2D.new()
    pin.node_a = anchor.get_path()
    pin.node_b = pendulum.get_path()
    
    anchor.add_child(pendulum)
    anchor.add_child(pin)
    
    return anchor
```

### 6.2 GrooveJoint2D（凹槽关节）

```gdscript
# 创建 2D 凹槽关节（滑动门）
func create_sliding_door_2d():
    # 轨道
    var track = StaticBody2D.new()
    
    # 门
    var door = RigidBody2D.new()
    door.mass = 5
    
    # 凹槽关节
    var groove = GrooveJoint2D.new()
    groove.node_a = track.get_path()
    groove.node_b = door.get_path()
    groove.groove_a = Vector2(-1, 0)
    groove.groove_b = Vector2(1, 0)
    groove.anchor_a = Vector2(0, 0)
    
    track.add_child(door)
    track.add_child(groove)
    
    return track
```

### 6.3 DampedSpringJoint2D（阻尼弹簧关节）

```gdscript
# 创建 2D 阻尼弹簧
func create_damped_spring():
    var body_a = RigidBody2D.new()
    var body_b = RigidBody2D.new()
    
    var spring = DampedSpringJoint2D.new()
    spring.node_a = body_a.get_path()
    spring.node_b = body_b.get_path()
    spring.anchor_a = Vector2(0, 0)
    spring.anchor_b = Vector2(0, 0)
    spring.rest_length = 2.0
    spring.stiffness = 10.0
    spring.damping = 0.5
    
    return spring
```

---

## 7. 关节马达和弹簧

### 7.1 马达配置

```gdscript
# 配置关节马达
func setup_joint_motor(joint: HingeJoint3D, target_velocity: float, force_limit: float):
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, target_velocity)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_FORCE_LIMIT, force_limit)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, true)

# 马达控制
func control_motor(joint: HingeJoint3D, enabled: bool):
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, enabled)

func set_motor_speed(joint: HingeJoint3D, speed: float):
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, speed)
```

### 7.2 弹簧配置

```gdscript
# 配置关节弹簧
func setup_joint_spring(joint: SliderJoint3D, stiffness: float, damping: float, equilibrium: float):
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, stiffness)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_DAMPING, damping)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, equilibrium)
```

---

## 8. 实践：机械结构

### 8.1 起重机

```gdscript
# 创建简易起重机
func create_crane():
    # 基座
    var base = StaticBody3D.new()
    
    # 吊臂（铰链关节）
    var arm = RigidBody3D.new()
    arm.mass = 100
    
    # 吊钩（滑块关节）
    var hook = RigidBody3D.new()
    hook.mass = 10
    
    # 吊臂关节
    var arm_joint = HingeJoint3D.new()
    arm_joint.node_a = base.get_path()
    arm_joint.node_b = arm.get_path()
    arm_joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_LOWER_ANGLE, deg_to_rad(-30))
    arm_joint.set_param(HingeJoint3D.PARAM_ANGULAR_LIMIT_UPPER_ANGLE, deg_to_rad(30))
    
    # 吊钩关节
    var hook_joint = SliderJoint3D.new()
    hook_joint.node_a = arm.get_path()
    hook_joint.node_b = hook.get_path()
    hook_joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_LOWER, 0)
    hook_joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_UPPER, 5)
    
    base.add_child(arm)
    base.add_child(arm_joint)
    arm.add_child(hook)
    arm.add_child(hook_joint)
    
    return base
```

### 8.2 多米诺骨牌链

```gdscript
# 创建多米诺骨牌链（使用关节连接）
func create_domino_chain(count: int, spacing: float):
    var dominos = []
    
    for i in range(count):
        var domino = RigidBody3D.new()
        domino.mass = 0.5
        
        var collision = CollisionShape3D.new()
        collision.shape = BoxShape3D.new()
        collision.shape.size = Vector3(0.1, 0.5, 0.3)
        domino.add_child(collision)
        
        domino.global_transform.origin = Vector3(i * spacing, 0.25, 0)
        add_child(domino)
        dominos.append(domino)
    
    # 用短链条连接（可选，增加稳定性）
    for i in range(count - 1):
        var joint = Generic6DOFJoint3D.new()
        joint.node_a = dominos[i].get_path()
        joint.node_b = dominos[i + 1].get_path()
        
        # 允许小范围移动
        for axis in range(3):
            joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.05)
            joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.05)
        
        add_child(joint)
```

---

## 📝 本章总结

### 核心要点

1. **关节连接多个刚体**，限制或允许特定方向的运动
2. **铰链关节用于旋转**，如门轴、钟摆
3. **滑块关节用于线性运动**，如抽屉、升降机
4. **锥形扭关节用于球窝连接**，如肩膀、髋部
5. **6DOF 关节提供完全控制**，适合复杂机械

### 关键术语

| 术语 | 解释 |
|------|------|
| DOF | 自由度，独立运动的方向数量 |
| Hinge Joint | 铰链关节，单轴旋转 |
| Slider Joint | 滑块关节，线性滑动 |
| Cone Twist Joint | 锥形扭关节，球窝连接 |
| 6DOF Joint | 6 自由度关节，完全控制 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Joints](https://docs.godotengine.org/en/stable/tutorials/physics/joints.html)
- **关节参考**: [HingeJoint3D](https://docs.godotengine.org/en/stable/classes/class_hingejoint3d.html)
- **源码位置**: `servers/physics_3d/joints/`
- **技术博客**: [Godot Physics Joints Guide](https://godotengine.org/article/physics-joints-guide/)

---

## 📋 下一章预告

**第 28 篇：车辆物理**

- 车辆物理架构
- 车轮碰撞
- 悬挂系统
- 引擎和传动
- 车辆控制器

---

*写作时间：2026-03-20*  
*字数：约 7,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*

---

## 9. 关节马达和驱动（新增）

### 9.1 马达基础

关节马达（Motor）用于驱动关节运动，提供持续的力或速度控制。

```
马达类型:
┌─────────────────────────────────────────────────────────────┐
│ 关节类型          │ 马达支持      │ 控制方式               │
├─────────────────────────────────────────────────────────────┤
│ HingeJoint3D      │ ✅ 角速度马达  │ 速度/力矩控制          │
│ SliderJoint3D     │ ✅ 线性马达    │ 速度/力控制            │
│ ConeTwistJoint3D  │ ❌ 无马达      │ 被动关节               │
│ Generic6DOFJoint  │ ✅ 多轴马达    │ 每轴独立控制           │
│ PinJoint2D        │ ✅ 角速度马达  │ 速度控制               │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 铰链关节马达

```gdscript
# 铰链关节马达配置
func setup_hinge_motor(joint: HingeJoint3D):
    # 启用马达
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, true)
    
    # 目标速度（弧度/秒）
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, deg_to_rad(90))
    
    # 最大力矩
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_MAX_IMPULSE, 100.0)
    
    # 马达模式
    # JOINT_MOTOR_TARGET_VELOCITY: 速度控制
    # JOINT_MOTOR_FORCE_LIMIT: 力矩限制
    
    print("Motor enabled: ", joint.is_enabled(HingeJoint3D.PARAM_ANGULAR_MOTOR))

# 速度控制示例
class_name MotorizedHinge

extends HingeJoint3D

@export var target_speed: float = 90.0  # 度/秒
@export var max_torque: float = 50.0    # 最大力矩

func _ready():
    # 启用马达
    set_param(PARAM_ANGULAR_MOTOR_ENABLED, true)
    set_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, deg_to_rad(target_speed))
    set_param(PARAM_ANGULAR_MOTOR_MAX_IMPULSE, max_torque)

func _physics_process(delta):
    # 动态调整速度
    if Input.is_action_pressed("speed_up"):
        set_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, deg_to_rad(180))
    elif Input.is_action_pressed("slow_down"):
        set_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, deg_to_rad(45))
    
    # 反转方向
    if Input.is_action_just_pressed("reverse"):
        var current = get_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY)
        set_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, -current)

# 力矩控制示例
func setup_torque_control(joint: HingeJoint3D, torque: float):
    # 设置力矩限制模式
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, true)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, 0.0)
    joint.set_param(HingeJoint3D.PARAM_ANGULAR_MOTOR_MAX_IMPULSE, torque)
    
    # 施加力矩（通过手动应用）
    var body_b = joint.get_node_b()
    if body_b:
        var body = get_node_or_null(body_b)
        if body is RigidBody3D:
            body.apply_torque(Vector3.UP * torque)
```

### 9.3 滑块关节马达

```gdscript
# 滑块关节马达配置
func setup_slider_motor(joint: SliderJoint3D):
    # 启用线性马达
    joint.set_param(SliderJoint3D.PARAM_LINEAR_MOTOR_ENABLED, true)
    
    # 目标速度（米/秒）
    joint.set_param(SliderJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 2.0)
    
    # 最大力
    joint.set_param(SliderJoint3D.PARAM_LINEAR_MOTOR_MAX_IMPULSE, 500.0)
    
    # 启用角马达（可选，用于旋转）
    joint.set_param(SliderJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, true)
    joint.set_param(SliderJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, deg_to_rad(45))
    joint.set_param(SliderJoint3D.PARAM_ANGULAR_MOTOR_MAX_IMPULSE, 50.0)

# 电梯控制器
class_name ElevatorController

extends SliderJoint3D

@export var floor_height: float = 3.0
@export var max_floors: int = 10
@export var speed: float = 2.0

var current_floor: int = 1
var target_floor: int = 1

func _ready():
    # 配置马达
    set_param(PARAM_LINEAR_MOTOR_ENABLED, true)
    set_param(PARAM_LINEAR_MOTOR_MAX_IMPULSE, 1000.0)
    
    # 设置限位
    set_param(PARAM_LINEAR_LIMIT_LOWER, 0)
    set_param(PARAM_LINEAR_LIMIT_UPPER, floor_height * (max_floors - 1))

func go_to_floor(floor: int):
    target_floor = clamp(floor, 1, max_floors)
    var target_height = (target_floor - 1) * floor_height
    
    # 计算方向
    var current_height = get_param(PARAM_LINEAR_POSITION)
    var direction = sign(target_height - current_height)
    
    # 设置马达速度
    set_param(PARAM_LINEAR_MOTOR_TARGET_VELOCITY, direction * speed)
    
    print("Going to floor ", target_floor, " (", target_height, "m)")

func _physics_process(delta):
    var current_height = get_param(PARAM_LINEAR_POSITION)
    var target_height = (target_floor - 1) * floor_height
    
    # 检查是否到达目标楼层
    if abs(current_height - target_height) < 0.1:
        set_param(PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 0.0)
        print("Arrived at floor ", target_floor)
```

### 9.4 6DOF 关节多轴马达

```gdscript
# 6DOF 关节多轴马达配置
func setup_6dof_motors(joint: Generic6DOFJoint3D):
    # 线性轴（X, Y, Z）
    joint.set_param(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_ENABLED, Vector3(1, 1, 0))
    joint.set_param(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, Vector3(1, 0, 0))
    joint.set_param(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_MAX_IMPULSE, Vector3(100, 100, 0))
    
    # 角轴（X, Y, Z）
    joint.set_param(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_ENABLED, Vector3(1, 0, 1))
    joint.set_param(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, Vector3(0, 0, deg_to_rad(45)))
    joint.set_param(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_MAX_IMPULSE, Vector3(50, 0, 50))

# 机械臂控制器
class_name RoboticArmController

extends Generic6DOFJoint3D

@export var arm_speed: float = 1.0
@export var rotation_speed: float = 90.0

func move_linear(direction: Vector3):
    set_param(PARAM_LINEAR_MOTOR_ENABLED, direction)
    set_param(PARAM_LINEAR_MOTOR_TARGET_VELOCITY, direction * arm_speed)

func rotate_axis(axis: Vector3):
    set_param(PARAM_ANGULAR_MOTOR_ENABLED, axis)
    set_param(PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, axis * deg_to_rad(rotation_speed))

func stop():
    set_param(PARAM_LINEAR_MOTOR_ENABLED, Vector3.ZERO)
    set_param(PARAM_ANGULAR_MOTOR_ENABLED, Vector3.ZERO)
```

### 9.5 马达性能优化

```
马达性能考量:
┌─────────────────────────────────────────────────────────────┐
│ 因素              │ 影响            │ 优化建议              │
├─────────────────────────────────────────────────────────────┤
│ 马达数量          │ CPU 负载 +5-10%/个  │ 限制同时激活数量    │
│ 最大力矩          │ 稳定性          │ 避免过大值            │
│ 速度目标          │ 物理稳定性      │ 渐变而非突变          │
│ 关节类型          │ 计算复杂度      │ 简单关节优先          │
└─────────────────────────────────────────────────────────────┘

最佳实践:
✅ 使用渐变速度（lerp）
✅ 设置合理的力矩限制
✅ 避免多个马达对抗
✅ 定期清理闲置马达
❌ 速度突变
❌ 超大力矩
❌ 马达互锁
```

---

## 10. 关节断裂机制（新增）

### 10.1 断裂原理

当关节承受的力超过阈值时，关节应该断裂（断开连接），模拟真实的物理破坏。

```
断裂触发条件:
┌─────────────────────────────────────────────────────────────┐
│ 条件类型          │ 检测方式          │ 适用场景            │
├─────────────────────────────────────────────────────────────┤
│ 力超过阈值        │ get_applied_force() │ 拉扯、撞击         │
│ 速度超过阈值      │ get_applied_impulse() │ 高速冲击         │
│ 角度超过限制      │ get_angle()       │ 过度扭转            │
│ 距离超过限制      │ get_param()       │ 拉伸过度            │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 基础断裂实现

```gdscript
# 可断裂的关节
class_name BreakableJoint

extends HingeJoint3D

@export var break_force: float = 500.0  # 断裂力阈值
@export var break_impulse: float = 100.0  # 断裂冲量阈值

var is_broken: bool = false

signal joint_broken

func _ready():
    # 启用接触监控
    contact_monitor = true

func _physics_process(delta):
    if is_broken:
        return
    
    # 检测施加的力
    var applied_force = get_applied_force()
    var applied_impulse = get_applied_impulse()
    
    # 检查是否超过阈值
    if applied_force.length() > break_force:
        _break_joint("Force exceeded: " + str(applied_force.length()))
    
    if applied_impulse.length() > break_impulse:
        _break_joint("Impulse exceeded: " + str(applied_impulse.length()))

func _break_joint(reason: String):
    if is_broken:
        return
    
    is_broken = true
    print("Joint broken: ", reason)
    
    # 断开连接
    _disconnect_joint()
    
    # 触发信号
    emit_signal("joint_broken")
    
    # 播放效果
    _play_break_effect()

func _disconnect_joint():
    # 方法 1：设置节点 B 为空
    set_node_b(NodePath())
    
    # 方法 2：从场景中移除关节
    # queue_free()
    
    # 方法 3：禁用关节
    # set_param(PARAM_ANGULAR_MOTOR_ENABLED, false)

func _play_break_effect():
    # 播放音效
    # $BreakSound.play()
    
    # 生成粒子
    # var particles = $BreakParticles.duplicate()
    # get_parent().add_child(particles)
    # particles.restart()
    pass
```

### 10.3 高级断裂系统

```gdscript
# 高级断裂管理系统
class_name JointBreakageSystem

extends Node

@export var global_break_multiplier: float = 1.0

var active_joints: Array = []

func _ready():
    # 注册所有可断裂关节
    var joints = get_tree().get_nodes_in_group("breakable_joints")
    for joint in joints:
        register_joint(joint)

func register_joint(joint: Node):
    if not joint.has_signal("joint_broken"):
        joint.connect("joint_broken", _on_joint_broken.bind(joint))
    active_joints.append(joint)

func _on_joint_broken(joint: Node):
    print("Joint broken: ", joint.name)
    active_joints.erase(joint)
    
    # 触发连锁反应（可选）
    _check_chain_reaction(joint)

func _check_chain_reaction(broken_joint: Node):
    # 检查相邻关节是否也应该断裂
    var neighbors = get_connected_joints(broken_joint)
    for neighbor in neighbors:
        # 增加相邻关节的受力
        if neighbor is BreakableJoint:
            neighbor.apply_stress(100.0)  # 额外应力

# 可断裂关节基类
class_name BreakableJointBase

extends Joint3D

@export var max_force: float = 1000.0
@export var max_impulse: float = 200.0
@export var max_angle: float = 360.0  # 度
@export var safety_factor: float = 1.0  # 安全系数

var accumulated_stress: float = 0.0
var stress_decay: float = 0.9  # 应力衰减

signal on_break

func _physics_process(delta):
    # 累积应力
    var current_force = get_applied_force().length()
    var current_impulse = get_applied_impulse().length()
    
    # 计算应力值（0-1）
    var force_stress = current_force / (max_force * safety_factor)
    var impulse_stress = current_impulse / (max_impulse * safety_factor)
    
    # 累积
    accumulated_stress = max(0, accumulated_stress - stress_decay * delta)
    accumulated_stress += max(force_stress, impulse_stress) * delta
    
    # 检查断裂
    if accumulated_stress > 1.0:
        _break()
    
    # 角度检查（仅旋转关节）
    if self is HingeJoint3D:
        var angle = rad_to_deg((self as HingeJoint3D).get_param(HingeJoint3D.PARAM_ANGULAR_POSITION))
        if abs(angle) > max_angle:
            _break()

func _break():
    emit_signal("on_break")
    queue_free()

func apply_stress(amount: float):
    accumulated_stress += amount / max_force
```

### 10.4 断裂效果

```gdscript
# 断裂效果管理器
class_name BreakageEffects

extends Node

@export var break_sound: AudioStream
@export var break_particles: PackedScene
@export var break_debris: PackedScene

func play_break_effects(position: Vector3, normal: Vector3):
    # 播放音效
    _play_sound(position)
    
    # 生成粒子
    _spawn_particles(position, normal)
    
    # 生成碎片
    _spawn_debris(position, normal)

func _play_sound(position: Vector3):
    var player = AudioStreamPlayer3D.new()
    player.stream = break_sound
    player.global_transform.origin = position
    add_child(player)
    player.play()
    
    # 自动清理
    player.finished.connect(func(): player.queue_free())

func _spawn_particles(position: Vector3, normal: Vector3):
    if break_particles:
        var particles = break_particles.instantiate()
        particles.global_transform.origin = position
        particles.look_at(position + normal)
        add_child(particles)
        particles.restart()

func _spawn_debris(position: Vector3, normal: Vector3):
    if break_debris:
        for i in range(3):  # 生成 3 个碎片
            var debris = break_debris.instantiate()
            debris.global_transform.origin = position
            
            if debris is RigidBody3D:
                # 随机方向飞散
                var direction = (Vector3(randf(), randf(), randf()) - Vector3.ONE * 0.5).normalized()
                debris.apply_central_impulse(direction * 5.0)
            
            add_child(debris)
```

### 10.5 断裂阈值配置

```
推荐断裂阈值:
┌─────────────────────────────────────────────────────────────┐
│ 关节类型          │ 力阈值 (N)   │ 冲量阈值 (Ns) │ 角度阈值  │
├─────────────────────────────────────────────────────────────┤
│ 门铰链           │ 500-1000     │ 100-200       │ 180°     │
│ 起重机吊臂       │ 5000-10000   │ 1000-2000     │ 90°      │
│ 角色关节         │ 200-500      │ 50-100        │ 45°      │
│ 车辆悬挂         │ 2000-5000    │ 500-1000      │ 30°      │
│ 绳索/链条        │ 100-300      │ 20-50         │ N/A      │
│ 玻璃连接         │ 50-100       │ 10-20         │ 5°       │
└─────────────────────────────────────────────────────────────┘

动态阈值调整:
- 疲劳累积：多次受力后阈值降低
- 环境因素：雨天/腐蚀降低阈值
- 材料差异：钢铁 > 木材 > 玻璃
```

### 10.6 实用案例：绳索断裂

```gdscript
# 可断裂的绳索
class_name BreakableRope

extends Node3D

@export var rope_segments: int = 10
@export var segment_length: float = 0.5
@export var break_force: float = 200.0

var joints: Array = []
var segments: Array = []

func _ready():
    _create_rope()

func _create_rope():
    var last_body: RigidBody3D = null
    
    for i in range(rope_segments):
        # 创建绳段
        var segment = RigidBody3D.new()
        segment.mass = 0.5
        segment.collision_layer = 0  # 不碰撞
        
        # 碰撞形状
        var collision = CollisionShape3D.new()
        var shape = CapsuleShape3D.new()
        shape.radius = 0.05
        shape.height = segment_length
        collision.shape = shape
        segment.add_child(collision)
        
        # 网格
        var mesh = MeshInstance3D.new()
        var cylinder = CylinderMesh.new()
        cylinder.top_radius = 0.05
        cylinder.bottom_radius = 0.05
        cylinder.height = segment_length
        mesh.mesh = cylinder
        segment.add_child(mesh)
        
        segment.position = Vector3(0, -i * segment_length, 0)
        add_child(segment)
        segments.append(segment)
        
        # 创建关节
        if last_body:
            var joint = PinJoint3D.new()
            joint.node_a = last_body.get_path()
            joint.node_b = segment.get_path()
            
            # 添加断裂脚本
            var breakable = BreakableJoint.new()
            breakable.max_force = break_force
            joint.add_child(breakable)
            
            add_child(joint)
            joints.append(joint)
        else:
            # 第一个段固定在天花板上
            segment.mode = RigidBody3D.MODE_STATIC
        
        last_body = segment

# 切割绳索
func cut_rope(index: int):
    if index >= 0 and index < joints.size():
        var joint = joints[index]
        joint.queue_free()
        joints.remove_at(index)
        print("Rope cut at segment ", index)
```

---

## 📝 本章总结（更新）

### 核心要点（更新）

1. **关节连接多个刚体**，限制或允许特定方向的运动
2. **铰链关节用于旋转**，如门轴、钟摆
3. **滑块关节用于线性运动**，如抽屉、升降机
4. **锥形扭关节用于球窝连接**，如肩膀、髋部
5. **6DOF 关节提供完全控制**，适合复杂机械
6. **关节马达提供动力**，实现速度/力矩控制（新增）
7. **关节断裂模拟破坏**，增加真实感和游戏性（新增）

### 关键术语（更新）

| 术语 | 解释 |
|------|------|
| DOF | 自由度，独立运动的方向数量 |
| Hinge Joint | 铰链关节，单轴旋转 |
| Slider Joint | 滑块关节，线性滑动 |
| Cone Twist Joint | 锥形扭关节，球窝连接 |
| 6DOF Joint | 6 自由度关节，完全控制 |
| Joint Motor | 关节马达，驱动关节运动（新增） |
| Break Force | 断裂力，关节承受的最大力（新增） |
| Stress Accumulation | 应力累积，疲劳损伤机制（新增） |
