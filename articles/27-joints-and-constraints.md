# 第 27 篇：关节和约束

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
└── PinJoint3D          # 钉关节（3D 钉连接，两个物体只保留一个点重合）

Godot 2D 关节类型:
├── PinJoint2D          # 钉关节（2D 旋转铰链）
├── GrooveJoint2D       # 凹槽关节（滑动）
└── DampedSpringJoint2D # 阻尼弹簧关节
```

> ⚠️ `PinJoint3D` 是**3D 钉关节**（两个刚体在锚点处重合、其余自由度自由），不是"2D 铰链"；2D 版是 `PinJoint2D`。另外，`PinJoint3D` 的服务器侧参数只有 `PIN_JOINT_BIAS` / `PIN_JOINT_DAMPING` / `PIN_JOINT_IMPULSE_CLAMP`，没有角度限制与马达——需要限位请改用 `HingeJoint3D`。

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
    
    # 启用并设置角度限制（开关属于 Flag，不是 Param）
    joint.set_flag(HingeJoint3D.FLAG_USE_LIMIT, true)
    joint.set_param(HingeJoint3D.PARAM_LIMIT_LOWER, deg_to_rad(-90))
    joint.set_param(HingeJoint3D.PARAM_LIMIT_UPPER, deg_to_rad(90))
    
    # 限制的柔化与松弛
    # 注意：PARAM_LIMIT_SOFTNESS 在 4.x 已被标记为 deprecated，
    #      官方说明"引擎从不使用它，仅为兼容性保留"，不要指望它生效。
    joint.set_param(HingeJoint3D.PARAM_LIMIT_RELAXATION, 0.5)
    
    # 马达（可选）
    joint.set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, true)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, 1.0)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_MAX_IMPULSE, 10.0)
    
    return joint
```

### 2.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| PARAM_LIMIT_LOWER / UPPER | 旋转角下限 / 上限（弧度） | -PI/2 / PI/2 |
| PARAM_LIMIT_BIAS | 限制的误差修正偏置 | 0 |
| PARAM_LIMIT_RELAXATION | 限制松弛程度，越小越严格 | 0.5 |
| PARAM_MOTOR_TARGET_VELOCITY | 马达目标速度（弧度/秒） | 1.0 |
| PARAM_MOTOR_MAX_IMPULSE | 马达最大冲量 | 10.0 |
| FLAG_USE_LIMIT / FLAG_ENABLE_MOTOR | 限制与马达开关（Flag 枚举） | true |

> **Param 与 Flag 的分工**：`HingeJoint3D` 的开关类参数（是否使用限位、是否启用马达）属于 **Flag** 枚举（`set_flag` / `get_flag`），数值类参数属于 **Param** 枚举（`set_param` / `get_param`）。写成 `set_param(..., PARAM_ANGULAR_MOTOR_ENABLED, ...)` 会报"常量不存在"——4.x 里根本没有 `PARAM_ANGULAR_MOTOR_*` 这一族名字。

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
    # ⚠️ 限位是 Flag 开关：不显式打开 FLAG_USE_LIMIT，
    #    PARAM_LIMIT_LOWER / UPPER 写了也不会生效。
    hinge.set_flag(HingeJoint3D.FLAG_USE_LIMIT, true)
    hinge.set_param(HingeJoint3D.PARAM_LIMIT_LOWER, 0)
    hinge.set_param(HingeJoint3D.PARAM_LIMIT_UPPER, deg_to_rad(90))
    
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
    
    # 设置限制软度与回弹
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_SOFTNESS, 0.9)
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_RESTITUTION, 0.1)
    
    # 设置限制阻尼
    # ⚠️ 4.x 的名字是 PARAM_LINEAR_LIMIT_DAMPING（不是 PARAM_LINEAR_DAMPING）
    joint.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_DAMPING, 0.5)
    
    return joint
```

> ⚠️ **4.x 的滑块关节没有弹簧**。`SliderJoint3D` 的 `Param` 枚举只有 `PARAM_LINEAR_LIMIT_*` / `PARAM_LINEAR_MOTION_*` / `PARAM_LINEAR_ORTHOGONAL_*` / `PARAM_ANGULAR_*` 这几族（见 `servers/physics_server_3d.h` 的 `SliderJointParam`），**没有** `PARAM_LINEAR_SPRING_STIFFNESS` / `PARAM_LINEAR_SPRING_DAMPING` / `PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT`，3.x 教程里的这几行在 4.x 会报"常量不存在"。
>
> 需要弹簧效果时的三条路：
> 1. **2D**：用 `DampedSpringJoint2D`（它就是为弹簧设计的关节）；
> 2. **3D**：用 `Generic6DOFJoint3D` 的线性弹簧（`PARAM_LINEAR_SPRING_STIFFNESS` / `_DAMPING` / `_EQUILIBRIUM_POINT`，并显式打开 `FLAG_ENABLE_LINEAR_SPRING`）；
> 3. **自行施力**：在 `_integrate_forces` 里按胡克定律 `F = -k·Δx - c·v` 调用 `apply_central_force()`。
>
> 另外 `SliderJoint3D` 也**没有马达参数**（没有 `PARAM_LINEAR_MOTOR_*`），需要线性驱动请走上面第 2 或第 3 条。

### 3.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| PARAM_LINEAR_LIMIT_LOWER | 线性下限位置 | 0 |
| PARAM_LINEAR_LIMIT_UPPER | 线性上限位置 | 0.5 |
| PARAM_LINEAR_LIMIT_SOFTNESS | 限制软度 | 0.9 |
| PARAM_LINEAR_LIMIT_RESTITUTION | 限制回弹 | 0.1 |
| PARAM_LINEAR_LIMIT_DAMPING | 限制阻尼 | 0.5 |
| PARAM_LINEAR_MOTION_SOFTNESS / _RESTITUTION / _DAMPING | 线性运动的软度/回弹/阻尼 | 按需 |
| PARAM_LINEAR_ORTHOGONAL_SOFTNESS / _RESTITUTION / _DAMPING | 垂直于滑动方向的约束参数 | 按需 |
| PARAM_ANGULAR_LIMIT_UPPER / _LOWER / _SOFTNESS / _RESTITUTION / _DAMPING | 角度限制系列 | 按需 |

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
    
    # 设置软度与松弛
    # ⚠️ 4.x 的 ConeTwistJoint3D.Param 只有这五个：
    #    PARAM_SWING_SPAN / PARAM_TWIST_SPAN / PARAM_BIAS / PARAM_SOFTNESS / PARAM_RELAXATION
    #    没有 PARAM_DAMPING，也没有 PARAM_SPRING_STIFFNESS / PARAM_SPRING_DAMPING。
    joint.set_param(ConeTwistJoint3D.PARAM_SOFTNESS, 0.8)
    joint.set_param(ConeTwistJoint3D.PARAM_RELAXATION, 0.5)
    
    return joint
```

### 4.2 参数详解

| 参数 | 说明 | 典型值 |
|------|------|--------|
| PARAM_SWING_SPAN | 摆动角度范围 | 45° |
| PARAM_TWIST_SPAN | 扭转角度范围 | 90° |
| PARAM_BIAS | 偏差 | 0 |
| PARAM_SOFTNESS | 软度 | 0.8 |
| PARAM_RELAXATION | 松弛 | 0.5 |

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
# ⚠️ 4.x 的 Generic6DOFJoint3D 没有 set_param(axis, PARAM, value) 这种统一入口。
#    公开方法是按轴分开的：
#      set_param_x / set_param_y / set_param_z (Param, real_t)
#      set_flag_x  / set_flag_y  / set_flag_z  (Flag, bool)
#    （见 scene/3d/physics/joints/generic_6dof_joint_3d.h）
#
# 4.x 配置 6DOF 关节的套路就是"逐轴设参数 + 逐轴开开关"。
# 下面先给三个按轴的辅助函数，再给主流程。

# 按轴设置线性限制（X/Y/Z 各调一次对应的 set_param_x/y/z）
func _set_linear_limit(joint: Generic6DOFJoint3D, axis: int,
                       lower: float, upper: float) -> void:
    match axis:
        Vector3.AXIS_X:
            joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, lower)
            joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, upper)
        Vector3.AXIS_Y:
            joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, lower)
            joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, upper)
        Vector3.AXIS_Z:
            joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, lower)
            joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, upper)

# 按轴设置角限制
func _set_angular_limit(joint: Generic6DOFJoint3D, axis: int,
                         lower: float, upper: float) -> void:
    match axis:
        Vector3.AXIS_X:
            joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, lower)
            joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, upper)
        Vector3.AXIS_Y:
            joint.set_param_y(Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, lower)
            joint.set_param_y(Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, upper)
        Vector3.AXIS_Z:
            joint.set_param_z(Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, lower)
            joint.set_param_z(Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, upper)

# 按轴开关限制（限位/弹簧都是 Flag，不开就不生效）
func _set_linear_limit_enabled(joint: Generic6DOFJoint3D, axis: int, enabled: bool) -> void:
    match axis:
        Vector3.AXIS_X: joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, enabled)
        Vector3.AXIS_Y: joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, enabled)
        Vector3.AXIS_Z: joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, enabled)

func _set_linear_spring_enabled(joint: Generic6DOFJoint3D, axis: int, enabled: bool) -> void:
    match axis:
        Vector3.AXIS_X: joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, enabled)
        Vector3.AXIS_Y: joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, enabled)
        Vector3.AXIS_Z: joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, enabled)


# 创建 6 自由度关节
func create_6dof_joint():
    var joint = Generic6DOFJoint3D.new()
    
    # 线性轴：三个轴都锁死（下限=上限=0），并显式打开限位开关
    for axis in [Vector3.AXIS_X, Vector3.AXIS_Y, Vector3.AXIS_Z]:
        _set_linear_limit(joint, axis, 0.0, 0.0)
        _set_linear_limit_enabled(joint, axis, true)
    
    # 角轴：同样全部锁死
    for axis in [Vector3.AXIS_X, Vector3.AXIS_Y, Vector3.AXIS_Z]:
        _set_angular_limit(joint, axis, 0.0, 0.0)
        match axis:
            Vector3.AXIS_X: joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
            Vector3.AXIS_Y: joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
            Vector3.AXIS_Z: joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
    
    return joint
```

> ⚠️ **两个必须知道的坑**
>
> 1. **没有 `set_param(axis, PARAM, value)`**：4.x 只提供 `set_param_x/y/z` 与 `set_flag_x/y/z`。旧教程里 `joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)` 这种写法在 4.x 会直接报"函数不存在"。
> 2. **限位与弹簧默认是关闭的**：即使把 `PARAM_LINEAR_LOWER_LIMIT` / `PARAM_LINEAR_SPRING_STIFFNESS` 都写上了，只要没有显式 `set_flag_*(FLAG_ENABLE_LINEAR_LIMIT / FLAG_ENABLE_LINEAR_SPRING, true)`，**限制与弹簧都不会生效**。这是 6DOF 关节"参数写了却没反应"的头号原因。

### 5.2 轴向配置

```gdscript
# 配置特定轴向
func configure_6dof_axis(joint: Generic6DOFJoint3D, axis: int, 
                         linear_enabled: bool, angular_enabled: bool,
                         linear_range: float = 1.0, angular_range: float = PI):
    
    # 线性轴
    if linear_enabled:
        _set_linear_limit(joint, axis, -linear_range, linear_range)
    else:
        _set_linear_limit(joint, axis, 0.0, 0.0)
    # 限位必须显式打开
    _set_linear_limit_enabled(joint, axis, true)
    
    # 角轴
    if angular_enabled:
        _set_angular_limit(joint, axis, -angular_range, angular_range)
    else:
        _set_angular_limit(joint, axis, 0.0, 0.0)
    
    # 角限位同样要显式打开
    match axis:
        Vector3.AXIS_X: joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
        Vector3.AXIS_Y: joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
        Vector3.AXIS_Z: joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
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
    
    # Y 轴（上下）允许移动 ±0.2m
    suspension.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.2)
    suspension.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.2)
    # 线性弹簧：刚度、阻尼、平衡点
    suspension.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, 50.0)
    suspension.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, 5.0)
    suspension.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, 0.0)
    # ⚠️ 必须显式打开限位与弹簧开关，否则上面这些参数一个都不生效
    suspension.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
    suspension.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, true)
    
    # 其他轴锁定（线性）
    suspension.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
    suspension.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
    suspension.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
    suspension.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
    suspension.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
    suspension.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
    
    # 所有角轴锁定
    for axis in [Vector3.AXIS_X, Vector3.AXIS_Y, Vector3.AXIS_Z]:
        _set_angular_limit(suspension, axis, 0.0, 0.0)
    suspension.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
    suspension.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
    suspension.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT, true)
    
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
# ⚠️ 4.x 的 HingeJoint3D 没有 PARAM_ANGULAR_MOTOR_* 这一族常量。
#    真实枚举是：PARAM_BIAS / PARAM_LIMIT_UPPER / PARAM_LIMIT_LOWER /
#               PARAM_LIMIT_BIAS / PARAM_LIMIT_SOFTNESS / PARAM_LIMIT_RELAXATION /
#               PARAM_MOTOR_TARGET_VELOCITY / PARAM_MOTOR_MAX_IMPULSE
#    马达的开关是 Flag：FLAG_USE_LIMIT / FLAG_ENABLE_MOTOR
func setup_joint_motor(joint: HingeJoint3D, target_velocity: float, force_limit: float):
    # 启用马达（开关是 Flag，不是 Param）
    joint.set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, true)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, target_velocity)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_MAX_IMPULSE, force_limit)

# 马达控制
func control_motor(joint: HingeJoint3D, enabled: bool):
    joint.set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, enabled)

func set_motor_speed(joint: HingeJoint3D, speed: float):
    joint.set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, speed)
```

### 7.2 弹簧配置

```gdscript
# 配置关节弹簧
# ⚠️ Godot 4 的 3D 滑块关节没有弹簧参数：
#    SliderJoint3D.Param 里只有 LIMIT_* / MOTION_* / ORTHOGONAL_* 三族，
#    不存在 PARAM_LINEAR_SPRING_STIFFNESS / _DAMPING / _EQUILIBRIUM_POINT。
#
#    需要 3D 弹簧时的两条可行路径：
#    1) 用 Generic6DOFJoint3D 的线性弹簧（并显式打开 FLAG_ENABLE_LINEAR_SPRING）；
#    2) 自己按胡克定律施力。
func setup_6dof_spring(joint: Generic6DOFJoint3D, axis: int,
                       stiffness: float, damping: float, equilibrium: float):
    match axis:
        Vector3.AXIS_X:
            joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, stiffness)
            joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, damping)
            joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, equilibrium)
            joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, true)
        Vector3.AXIS_Y:
            joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, stiffness)
            joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, damping)
            joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, equilibrium)
            joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, true)
        Vector3.AXIS_Z:
            joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, stiffness)
            joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, damping)
            joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, equilibrium)
            joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING, true)

# 或者自己施加胡克力（不依赖任何关节类型）
func apply_spring_force(body: RigidBody3D, anchor: Vector3, stiffness: float, damping: float) -> void:
    var displacement := anchor - body.global_position
    var velocity := body.linear_velocity
    var force := displacement * stiffness - velocity * damping
    body.apply_central_force(force)
```

> 2D 有专门的 `DampedSpringJoint2D`（`stiffness` / `damping` / `rest_length`），3D **没有**对应的 `DampedSpringJoint3D`。

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
    # ⚠️ 4.x 没有 PARAM_ANGULAR_LIMIT_LOWER_ANGLE / _UPPER_ANGLE，
    #    铰链限位参数名是 PARAM_LIMIT_LOWER / PARAM_LIMIT_UPPER，
    #    而且必须显式打开限位开关 FLAG_USE_LIMIT。
    arm_joint.set_flag(HingeJoint3D.FLAG_USE_LIMIT, true)
    arm_joint.set_param(HingeJoint3D.PARAM_LIMIT_LOWER, deg_to_rad(-30))
    arm_joint.set_param(HingeJoint3D.PARAM_LIMIT_UPPER, deg_to_rad(30))
    
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
        
        # 允许小范围移动（按轴设置，且要显式打开限位开关）
        joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.05)
        joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.05)
        joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.05)
        joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.05)
        joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.05)
        joint.set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.05)
        joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
        joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
        joint.set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT, true)
        
        add_child(joint)
```

---

## 9. 关节马达和驱动

### 9.1 马达基础

关节马达（Motor）用于驱动关节运动，提供持续的力或速度控制。

```
马达类型:
┌─────────────────────────────────────────────────────────────┐
│ 关节类型          │ 马达支持      │ 控制方式               │
├─────────────────────────────────────────────────────────────┤
│ HingeJoint3D      │ ✅ 角速度马达  │ 速度/力矩控制          │
│ SliderJoint3D     │ ❌ 无马达参数  │ 自行施力 / 改用 6DOF   │
│ ConeTwistJoint3D  │ ❌ 无马达      │ 被动关节               │
│ Generic6DOFJoint  │ ✅ 多轴马达    │ 每轴独立控制           │
│ PinJoint2D        │ ✅ 角速度马达  │ 速度控制               │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 铰链关节马达

```gdscript
# 铰链关节马达配置
func setup_hinge_motor(joint: HingeJoint3D):
    # 启用马达（开关是 Flag：FLAG_ENABLE_MOTOR）
    joint.set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, true)
    
    # 目标速度（弧度/秒）
    joint.set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, deg_to_rad(90))
    
    # 最大力矩
    joint.set_param(HingeJoint3D.PARAM_MOTOR_MAX_IMPULSE, 100.0)
    
    # 查询马达是否开启：用 get_flag(FLAG_ENABLE_MOTOR)
    print("Motor enabled: ", joint.get_flag(HingeJoint3D.FLAG_ENABLE_MOTOR))

# 速度控制示例
class_name MotorizedHinge

extends HingeJoint3D

@export var target_speed: float = 90.0  # 度/秒
@export var max_torque: float = 50.0    # 最大力矩

func _ready():
    # 启用马达
    set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, true)
    set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, deg_to_rad(target_speed))
    set_param(HingeJoint3D.PARAM_MOTOR_MAX_IMPULSE, max_torque)

func _physics_process(delta):
    # 动态调整速度
    if Input.is_action_pressed("speed_up"):
        set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, deg_to_rad(180))
    elif Input.is_action_pressed("slow_down"):
        set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, deg_to_rad(45))
    
    # 反转方向
    if Input.is_action_just_pressed("reverse"):
        var current = get_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY)
        set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, -current)

# 力矩控制示例
func setup_torque_control(joint: HingeJoint3D, torque: float):
    # 设置力矩限制模式
    joint.set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, true)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_TARGET_VELOCITY, 0.0)
    joint.set_param(HingeJoint3D.PARAM_MOTOR_MAX_IMPULSE, torque)
    
    # 施加力矩（通过手动应用）
    var body = get_node_or_null(node_b)
    if body is RigidBody3D:
        body.apply_torque(Vector3.UP * torque)
```

### 9.3 滑块关节马达

```gdscript
# ⚠️ Godot 4 的 SliderJoint3D 没有马达参数。
#    SliderJoint3D.Param 里不存在 PARAM_LINEAR_MOTOR_ENABLED /
#    PARAM_LINEAR_MOTOR_TARGET_VELOCITY / PARAM_LINEAR_MOTOR_MAX_IMPULSE，
#    也不存在 PARAM_LINEAR_POSITION（拿不到滑块当前位置）。
#
#    路线 A：用 Generic6DOFJoint3D 的线性马达（见 9.4 节）
#    路线 B：自己按目标速度施力（下面的电梯控制器）
```

```gdscript
# 电梯控制器（路线 B：自行施力驱动）
# 关节用 SliderJoint3D 限制行程，用力来驱动
class_name ElevatorController

extends Node3D

@export var floor_height: float = 3.0
@export var max_floors: int = 10
@export var speed: float = 2.0
@export var drive_force: float = 2000.0

@export var platform: RigidBody3D
@export var slider: SliderJoint3D

var current_floor: int = 1
var target_floor: int = 1
var _origin_height: float = 0.0

func _ready():
    if platform:
        _origin_height = platform.global_position.y
    # 设置限位（SliderJoint3D 唯一的"行程"控制）
    slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_LOWER, 0)
    slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_UPPER, floor_height * (max_floors - 1))

func go_to_floor(floor: int):
    target_floor = clamp(floor, 1, max_floors)
    var target_height = (target_floor - 1) * floor_height
    print("Going to floor ", target_floor, " (", target_height, "m)")

func _physics_process(delta):
    if platform == null:
        return
    var target_height = _origin_height + (target_floor - 1) * floor_height
    var current_height = platform.global_position.y
    var error = target_height - current_height

    # 到达目标楼层：停止驱动
    if abs(error) < 0.1:
        return

    # 简单的 P 控制：误差 → 目标速度 → 力
    var target_velocity = clamp(error * 2.0, -speed, speed)
    var velocity_error = target_velocity - platform.linear_velocity.y
    platform.apply_central_force(Vector3.UP * velocity_error * drive_force / max(speed, 0.001))
```

### 9.4 6DOF 关节多轴马达

```gdscript
# 6DOF 关节多轴马达配置
# ⚠️ 4.x 没有 PARAM_LINEAR_MOTOR_ENABLED / PARAM_ANGULAR_MOTOR_ENABLED 这类"整轴开关"参数：
#    马达的启用是【按轴的 Flag】：
#      FLAG_ENABLE_MOTOR          —— 该轴马达总开关
#      FLAG_ENABLE_LINEAR_MOTOR   —— 该轴线性马达
#    数值参数：PARAM_LINEAR_MOTOR_TARGET_VELOCITY / PARAM_LINEAR_MOTOR_FORCE_LIMIT
#              PARAM_ANGULAR_MOTOR_TARGET_VELOCITY / PARAM_ANGULAR_MOTOR_FORCE_LIMIT
func setup_6dof_motors(joint: Generic6DOFJoint3D):
    # 线性马达：只开 Y 轴
    joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 1.0)
    joint.set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_FORCE_LIMIT, 100.0)
    joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_MOTOR, true)
    joint.set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_MOTOR, true)

# 机械臂控制器
class_name RoboticArmController

extends Generic6DOFJoint3D

@export var arm_speed: float = 1.0
@export var rotation_speed: float = 90.0

func move_linear(direction: Vector3):
    # direction 的每个分量对应一个轴的目标速度
    set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, direction.x * arm_speed)
    set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, direction.y * arm_speed)
    set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, direction.z * arm_speed)
    set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_MOTOR, true)
    set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_MOTOR, true)
    set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_MOTOR, true)

func rotate_axis(axis: Vector3):
    set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, axis.x * deg_to_rad(rotation_speed))
    set_param_y(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, axis.y * deg_to_rad(rotation_speed))
    set_param_z(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, axis.z * deg_to_rad(rotation_speed))
    set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_MOTOR, true)
    set_flag_y(Generic6DOFJoint3D.FLAG_ENABLE_MOTOR, true)
    set_flag_z(Generic6DOFJoint3D.FLAG_ENABLE_MOTOR, true)

func stop():
    set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 0.0)
    set_param_y(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 0.0)
    set_param_z(Generic6DOFJoint3D.PARAM_LINEAR_MOTOR_TARGET_VELOCITY, 0.0)
    set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, 0.0)
    set_param_y(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, 0.0)
    set_param_z(Generic6DOFJoint3D.PARAM_ANGULAR_MOTOR_TARGET_VELOCITY, 0.0)
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

## 10. 关节断裂机制

### 10.1 断裂原理

当关节承受的力超过阈值时，关节应该断裂（断开连接），模拟真实的物理破坏。

```
断裂触发条件:
┌─────────────────────────────────────────────────────────────┐
│ 条件类型          │ 检测方式          │ 适用场景            │
├─────────────────────────────────────────────────────────────┤
│ 约束受力过大      │ 两端相对偏转角    │ 拉扯、撞击          │
│ 撞击动量过大      │ 刚体接触信号      │ 高速冲击            │
│ 角度超过限制      │ 自行记录相对角度  │ 过度扭转            │
│ 距离超过限制      │ 两端相对位移      │ 拉伸过度            │
└─────────────────────────────────────────────────────────────┘

> ⚠️ 4.x 的 `Joint3D` 没有 `get_applied_force()` / `get_applied_impulse()`（3.x `PhysicsBody` 的接口），
> 也没有"当前关节角度"参数。上面两种判据都是用可测量的量近似出来的。
```

### 10.2 基础断裂实现

```gdscript
# 可断裂的关节
# ⚠️ Godot 4 的 Joint3D 没有 get_applied_force() / get_applied_impulse()
#    （那是 3.x PhysicsBody 的接口），也没有 contact_monitor 属性
#    （contact_monitor 属于 RigidBody3D 这类物理体，不属于关节）。
#    4.x 也没有直接查询"关节约束力"的接口，常见做法是量测约束两端的
#    相对偏转来间接反映受力；撞击强度则由刚体的接触冲量给出。
class_name BreakableJoint

extends HingeJoint3D

@export var break_force: float = 500.0      # 断裂力阈值（用相对偏转折算）
@export var break_impulse: float = 100.0   # 断裂冲量阈值
@export var max_angle_degrees: float = 45.0  # 允许的最大相对偏转（度）

var is_broken: bool = false

signal joint_broken

func _ready():
    # 撞击强度用两端刚体的接触信号捕捉
    # （刚体侧需要 contact_monitor = true 且 max_contacts_reported > 0）
    for body in [get_node_or_null(node_a), get_node_or_null(node_b)]:
        if body is RigidBody3D:
            body.body_entered.connect(_on_body_entered)

func _physics_process(delta):
    if is_broken:
        return
    
    # 约束受力：用两端的相对偏转角折算（约束越"硬"，偏转越小）
    var deviation := _constraint_deviation_degrees()
    if deviation > max_angle_degrees:
        _break_joint("Deviation exceeded: " + str(deviation))

func _on_body_entered(other: Node) -> void:
    if is_broken:
        return
    # 用撞击者的动量近似冲量
    if other is RigidBody3D:
        var momentum := other.linear_velocity.length() * other.mass
        if momentum > break_impulse:
            _break_joint("Impact momentum exceeded: " + str(momentum))

# 约束两端的相对偏转角（度）
func _constraint_deviation_degrees() -> float:
    var a := get_node_or_null(node_a) as RigidBody3D
    var b := get_node_or_null(node_b) as RigidBody3D
    if a == null or b == null:
        return 0.0
    var rel := a.global_transform.basis.get_rotation_quaternion().inverse() \
        * b.global_transform.basis.get_rotation_quaternion()
    return rad_to_deg(rel.get_angle())

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
    
    # 方法 3：禁用马达（马达开关是 Flag）
    # set_flag(HingeJoint3D.FLAG_ENABLE_MOTOR, false)

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
    # ⚠️ Joint3D 没有 get_applied_force() / get_applied_impulse()，
    #    也没有"当前关节角度"参数（没有 PARAM_ANGULAR_POSITION）。
    #    改用可测量的量：约束两端的相对偏转 + 撞击动量。
    var deviation := _constraint_deviation_degrees()
    var momentum := _max_impact_momentum()
    
    # 计算应力值（0-1）
    var force_stress = deviation / (max_angle * safety_factor)
    var impulse_stress = momentum / (max_impulse * safety_factor)
    
    # 累积
    accumulated_stress = max(0, accumulated_stress - stress_decay * delta)
    accumulated_stress += max(force_stress, impulse_stress) * delta
    
    # 检查断裂
    if accumulated_stress > 1.0:
        _break()

func _constraint_deviation_degrees() -> float:
    var a := get_node_or_null(node_a) as RigidBody3D
    var b := get_node_or_null(node_b) as RigidBody3D
    if a == null or b == null:
        return 0.0
    var rel := a.global_transform.basis.get_rotation_quaternion().inverse() \
        * b.global_transform.basis.get_rotation_quaternion()
    return rad_to_deg(rel.get_angle())

func _max_impact_momentum() -> float:
    var biggest := 0.0
    for body in [get_node_or_null(node_a), get_node_or_null(node_b)]:
        if body is RigidBody3D:
            biggest = max(biggest, body.linear_velocity.length() * body.mass)
    return biggest

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
            # ⚠️ 4.x 的 RigidBody3D 没有 mode 属性与 MODE_STATIC / MODE_RIGID 枚举；
            #    对应能力是 freeze + freeze_mode。
            segment.freeze = true
            segment.freeze_mode = RigidBody3D.FREEZE_MODE_STATIC
        
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

## 11. 求解器与关节：关节多的场景为什么卡

"关节一多物理就掉帧"是最常见的物理性能问题之一，但它很少是"碰撞检测"造成的——真正吃预算的是**约束求解**。Godot 为此提供了几个直接可调的旋钮：

```gdscript
# 1) 关节两端物体默认不再互相碰撞（Joint3D.exclude_nodes_from_collision，默认 true）
#    机械连杆的两个零件本来就该贴合，额外算一次接触约束纯属浪费。
var joint := HingeJoint3D.new()
joint.exclude_nodes_from_collision = true

# 2) 求解优先级：同一空间里多个关节互相影响时，先解哪个
#    Joint3D.solver_priority 默认 1；数值越大越先被求解。
joint.solver_priority = 10

# 3) 服务器层等价接口（servers/physics_server_3d.h）
var j_rid := joint.get_rid()
PhysicsServer3D.joint_disable_collisions_between_bodies(j_rid, true)
PhysicsServer3D.joint_set_solver_priority(j_rid, 10)
```

| 旋钮 | 位置 | 典型用法 |
|------|------|----------|
| `exclude_nodes_from_collision` | `Joint3D` 节点属性（默认 `true`） | 保持默认即可；自碰撞确实无用时再关 |
| `solver_priority` | `Joint3D` 节点属性（默认 `1`） | 底盘/悬挂等"基础"关节调低，被动悬挂/软约束调高 |
| `joint_set_solver_priority()` | `PhysicsServer3D` | 代码里统一调参 |
| `joint_disable_collisions_between_bodies()` | `PhysicsServer3D` | 运行时批量开关 |

**排查顺序**（与第 32 篇一致）：

1. `Performance.get_monitor(Performance.PHYSICS_3D_COLLISION_PAIRS)` 很大 → 是**配对**太多，收窄碰撞掩码；
2. 碰撞对正常但物理帧耗时高 → 是**求解**太重，减少关节数量、放松约束刚度（限制的 `PARAM_LIMIT_RELAXATION` 调大）、调 `solver_priority`；
3. 关节连着高精度碰撞形状 → 窄相位成本被放大，给关节两端的物体换成球/盒等简单形状。

---

## 📝 本章总结

### 核心要点

1. **关节连接多个刚体**，限制或允许特定方向的运动
2. **铰链关节用于旋转**，如门轴、钟摆
3. **滑块关节用于线性运动**，如抽屉、升降机
4. **锥形扭关节用于球窝连接**，如肩膀、髋部
5. **6DOF 关节提供完全控制**，适合复杂机械
6. **关节马达提供动力**，实现速度/力矩控制
7. **关节断裂模拟破坏**，增加真实感和游戏性

### 关键术语

| 术语 | 解释 |
|------|------|
| DOF | 自由度，独立运动的方向数量 |
| Hinge Joint | 铰链关节，单轴旋转 |
| Slider Joint | 滑块关节，线性滑动 |
| Cone Twist Joint | 锥形扭关节，球窝连接 |
| 6DOF Joint | 6 自由度关节，完全控制 |
| Joint Motor | 关节马达，驱动关节运动 |
| Break Force | 断裂力，关节承受的最大力 |
| Stress Accumulation | 应力累积，疲劳损伤机制 |

---

## 🔗 延伸阅读

- **物理教程总览**: <https://docs.godotengine.org/en/stable/tutorials/physics/index.html>
- **HingeJoint3D**: <https://docs.godotengine.org/en/stable/classes/class_hingejoint3d.html>
- **Generic6DOFJoint3D**: <https://docs.godotengine.org/en/stable/classes/class_generic6dofjoint3d.html>
- **源码位置**: `servers/physics_3d/joints/`

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 26 篇：物理材质](/articles/26-physics-material.md)
**下一篇**: [第 28 篇：车辆物理](/articles/28-vehicle-physics.md)

---

## 📋 下一章预告

**第 28 篇：车辆物理**

- 车辆物理架构
- 车轮碰撞与悬挂
- 引擎和传动系统
- 车辆控制器

---

*写作时间：2026-03-20*  
*最近一次技术勘误：2026-09-12*  
*状态：✅ 完成*
