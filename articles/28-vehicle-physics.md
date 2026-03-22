# 第 18 篇：车辆物理

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 27 章 关节和约束  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

车辆物理是游戏物理中一个重要且复杂的领域，涉及车轮碰撞、悬挂系统、引擎传动、车辆控制器等多个方面。从简单的卡丁车到复杂的载具，车辆物理能够为游戏带来真实的驾驶体验。

Godot 提供了强大的车辆物理系统，通过刚体、关节和自定义脚本，可以创建各种类型的车辆，包括汽车、摩托车、卡车、飞机等。

---

## 🎯 学习目标

- 理解车辆物理的核心概念
- 掌握车轮碰撞和悬挂系统
- 学会配置引擎和传动系统
- 创建车辆控制器
- 优化车辆性能

---

## 1. 车辆物理架构

### 1.1 基本组件

```
车辆物理架构:
┌─────────────────────────────────────────────────────────────┐
│                      车辆物理架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 车身（刚体）                                            │
│  2. 车轮（刚体）                                            │
│  3. 悬挂系统（关节）                                        │
│  4. 引擎/传动系统（脚本）                                    │
│  5. 车轮控制器（脚本）                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 车辆类型分类

| 类型 | 特点 | 关键组件 |
|------|------|----------|
| 汽车类 | 4 轮驱动，悬挂系统 | 四个车轮，悬挂，发动机 |
| 摩托车 | 2 轮驱动，重心高 | 两个车轮，悬挂，发动机 |
| 卡车 | 重型，大轮胎 | 多个车轮，悬挂，引擎 |
| 飞机 | 空气动力学 | 翼，起落架，引擎 |
| 摩托艇 | 水上 | 舵，推进器，浮力 |

### 1.3 创建车辆的基本步骤

```gdscript
# 创建车辆的基本框架
func create_vehicle():
    # 1. 创建车身（刚体）
    var chassis = RigidBody3D.new()
    chassis.mass = 1500
    
    # 2. 创建车轮（刚体）
    var wheels = []
    for i in range(4):
        var wheel = RigidBody3D.new()
        wheel.mass = 20
        wheels.append(wheel)
    
    # 3. 创建悬挂关节
    var suspension = []
    for i in range(4):
        var joint = Generic6DOFJoint3D.new()
        joint.node_a = chassis.get_path()
        joint.node_b = wheels[i].get_path()
        suspension.append(joint)
    
    # 4. 添加到场景
    add_child(chassis)
    for wheel in wheels:
        chassis.add_child(wheel)
        chassis.add_child(suspension[i])
    
    return chassis
```

---

## 2. 车轮碰撞与悬挂

### 2.1 车轮基础

```gdscript
# 创建车轮
func create_wheel(position: Vector3, radius: float, width: float):
    var wheel = RigidBody3D.new()
    wheel.mass = 20
    
    # 车轮碰撞形状
    var wheel_collision = CollisionShape3D.new()
    wheel_collision.shape = CylinderShape3D.new()
    wheel_collision.shape.radius = radius
    wheel_collision.shape.height = width
    wheel.add_child(wheel_collision)
    
    # 车轮网格
    var wheel_mesh = MeshInstance3D.new()
    wheel_mesh.mesh = CylinderMesh.new()
    wheel_mesh.mesh.height = width
    wheel_mesh.mesh.radius_top = 0
    wheel_mesh.mesh.radius_bottom = radius
    wheel_mesh.position = Vector3(0, 0, -width/2)
    wheel.add_child(wheel_mesh)
    
    # 设置车轮为只与地面碰撞
    wheel.collision_layer = 8  # 车辆层
    wheel.collision_mask = 16  # 地面层
    
    return wheel

# 创建 4 个车轮
func create_wheels(chassis: RigidBody3D, positions: Array):
    var wheels = []
    for i in range(4):
        var wheel = create_wheel(positions[i], 0.3, 0.15)
        wheels.append(wheel)
    
    return wheels
```

### 2.2 悬挂系统

```gdscript
# 创建悬挂系统
func create_suspension(chassis: RigidBody3D, wheel: RigidBody3D):
    var joint = Generic6DOFJoint3D.new()
    joint.node_a = chassis.get_path()
    joint.node_b = wheel.get_path()
    
    # 设置 Y 轴（上下）允许移动
    joint.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, -0.2)
    joint.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0.2)
    joint.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, 50.0)
    joint.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING, 5.0)
    joint.set_param(1, Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT, 0)
    
    # 其他轴锁定
    for axis in [0, 2]:
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT, 0)
        joint.set_param(axis, Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT, 0)
    
    # 所有角轴锁定
    for axis in range(3):
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT, 0)
        joint.set_param(axis + 3, Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT, 0)
    
    return joint
```

### 2.3 车轮控制

```gdscript
# 控制车轮旋转
func control_wheel(wheel: RigidBody3D, speed: float):
    wheel.apply_torque_impulse(Vector3(0, 0, speed))
    
    # 限制最大速度
    var velocity = wheel.angular_velocity.length()
    if velocity > 20:
        wheel.angular_velocity = wheel.angular_velocity.normalized() * 20

# 控制所有车轮
func control_wheels(wheels: Array, speeds: Array):
    for i in range(wheels.size()):
        control_wheel(wheels[i], speeds[i])
```

---

## 3. 引擎与传动系统

### 3.1 引擎基础

```gdscript
# 创建引擎
class_name VehicleEngine

@export var max_power: float = 200  # 最大功率
@export var torque_curve: Curve2D  # 扭矩曲线

func get_torque(rpm: float) -> float:
    # RPM 转换为 0-1 范围
    var normalized_rpm = clamp(rpm / 8000, 0, 1)
    return torque_curve.sample(normalized_rpm)

func get_power(rpm: float) -> float:
    return get_torque(rpm) * rpm / 8000  # 功率 = 扭矩 × RPM

# 使用示例
func _physics_process(delta):
    var current_rpm = get_rpm()
    var torque = get_torque(current_rpm)
    
    # 应用扭矩到车轮
    for wheel in $Wheels:
        wheel.apply_impulse(Vector3(0, 0, torque), wheel.global_transform.basis * Vector3(1, 0, 0))
```

### 3.2 传动系统

```gdscript
# 传动系统
class_name Transmission

@export var gear_ratios: Array = [3.0, 2.0, 1.5, 1.0, 0.75]  # 1-5 挡
@export var current_gear: int = 1

func set_gear(gear: int):
    if gear >= 0 and gear < gear_ratios.size():
        current_gear = gear
    else:
        current_gear = 1

func get_gear_ratio() -> float:
    return gear_ratios[current_gear]

# 转向控制
func apply_steering(wheel: RigidBody3D, angle: float):
    wheel.apply_torque_impulse(Vector3(0, angle * 5, 0))
```

### 3.3 油门控制

```gdscript
# 油门控制
class_name ThrottleController

@export var max_speed: float = 100
@export var acceleration: float = 20

func apply_throttle(engine: VehicleEngine, speed: float):
    var rpm = speed * 80  # 速度转 RPM
    rpm = clamp(rpm, 0, 8000)
    
    # 计算油门百分比
    var throttle = min(speed / max_speed, 1.0)
    
    # 应用扭矩
    var torque = engine.get_torque(rpm) * throttle
    engine.apply_torque(torque)
```

---

## 4. 车辆控制器

### 4.1 基础控制器

```gdscript
# 基础车辆控制器
class_name VehicleController

@export var max_steering_angle: float = deg_to_rad(30)
@export var max_acceleration: float = 20

func _physics_process(delta):
    # 获取输入
    var acceleration = Input.get_action_strength("accelerate") - Input.get_action_strength("brake")
    var steering = Input.get_action_strength("steer_left") - Input.get_action_strength("steer_right")
    
    # 应用控制
    apply_acceleration(acceleration)
    apply_steering(steering)
    
    # 更新速度显示
    var speed = get_linear_velocity().length()
    print("Speed: ", speed)

func apply_acceleration(accel: float):
    if acceleration > 0:
        $Engine.apply_throttle($Engine, speed)
    elif acceleration < 0:
        $Engine.apply_brake()
    else:
        $Engine.apply_brake()

func apply_steering(angle: float):
    if abs(angle) > 0.1:
        $Wheels[0].apply_torque_impulse(Vector3(0, angle * max_steering_angle, 0))
        $Wheels[3].apply_torque_impulse(Vector3(0, angle * max_steering_angle, 0))
        $Wheels[1].apply_torque_impulse(Vector3(0, -angle * max_steering_angle, 0))
        $Wheels[2].apply_torque_impulse(Vector3(0, -angle * max_steering_angle, 0))

func apply_brake():
    for wheel in $Wheels:
        wheel.apply_impulse(Vector3(0, 0, -100), wheel.global_transform.basis * Vector3(1, 0, 0))
```

### 4.2 滑胎控制

```gdscript
# 滑胎检测和处理
func check_slip():
    var slip_threshold = 0.8  # 滑胎阈值
    var speed = get_linear_velocity().length()
    
    # 检查车轮速度是否超过车身速度
    for wheel in $Wheels:
        var wheel_speed = wheel.linear_velocity.length()
        if wheel_speed > speed * slip_threshold:
            # 应用刹车
            wheel.apply_impulse(Vector3(0, 0, -50), wheel.global_transform.basis * Vector3(1, 0, 0))
            # 减少油门
            $Engine.apply_throttle($Engine, 0.3)

# 在 _integrate_forces 中调用
func _integrate_forces(state: PhysicsDirectBodyState3D):
    check_slip()
```

### 4.3 离合器控制

```gdscript
# 离合器控制
class_name ClutchController

@export var clutch_pressure: float = 0.0  # 0 = 完全接合，1 = 完全分离

func set_clutch(percentage: float):
    clutch_pressure = percentage
    
    # 根据离合器压力调整传动比
    if clutch_pressure > 0.5:
        $Transmission.set_gear(1)  # 1 挡
    elif clutch_pressure > 0.2:
        $Transmission.set_gear(2)  # 2 挡
    elif clutch_pressure > 0:
        $Transmission.set_gear(3)  # 3 挡
    else:
        $Transmission.set_gear(4)  # 4 挡

# 在油门控制中调用
func _physics_process(delta):
    var acceleration = Input.get_action_strength("accelerate") - Input.get_action_strength("brake")
    
    # 根据油门控制离合器
    if acceleration > 0:
        set_clutch(max(0, 1 - acceleration * 0.5))
    else:
        set_clutch(min(1, acceleration * 2))
```

---

## 5. 车辆性能优化

### 5.1 车轮优化

```gdscript
# 车轮性能优化
func optimize_wheels():
    # 减少车轮数量（如果性能不足）
    if get_tree().get_nodes_in_group("wheels").size() > 4:
        var wheels = get_tree().get_nodes_in_group("wheels")
        for i in range(wheels.size() - 4):
            wheels[i].queue_free()
    
    # 调整车轮质量
    for wheel in get_tree().get_nodes_in_group("wheels"):
        wheel.mass = 15  # 降低质量

# 在游戏开始时调用
func _ready():
    optimize_wheels()
```

### 5.2 悬挂优化

```gdscript
# 悬挂性能优化
func optimize_suspension():
    # 减少悬挂关节数量（如果性能不足）
    var joints = get_tree().get_nodes_in_group("suspension")
    if joints.size() > 4:
        for i in range(joints.size() - 4):
            joints[i].queue_free()
    
    # 调整悬挂参数
    for joint in joints:
        joint.set_param(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS, 30.0)  # 降低刚度

# 在游戏开始时调用
func _ready():
    optimize_suspension()
```

### 5.3 引擎优化

```gdscript
# 引擎性能优化
func optimize_engine():
    # 调整引擎参数
    $Engine.max_power = 150  # 降低功率
    $Engine.torque_curve = Curve2D.new()
    $Engine.torque_curve.add_point(0, 0)
    $Engine.torque_curve.add_point(0.5, 100)
    $Engine.torque_curve.add_point(1.0, 150)

# 在游戏开始时调用
func _ready():
    optimize_engine()
```

---

## 6. 实践：不同类型车辆

### 6.1 简易汽车

```gdscript
# 创建简易汽车
func create_simple_car():
    # 车身
    var car = RigidBody3D.new()
    car.mass = 1500
    
    # 车轮位置
    var wheel_positions = [
        Vector3(-1.2, 0, 0.8),   # 左前
        Vector3(1.2, 0, 0.8),    # 右前
        Vector3(-1.2, 0, -0.8),  # 左后
        Vector3(1.2, 0, -0.8)    # 右后
    ]
    
    # 创建车轮
    var wheels = []
    for pos in wheel_positions:
        var wheel = create_wheel(pos, 0.3, 0.15)
        wheels.append(wheel)
    
    # 创建悬挂
    var suspensions = []
    for i in range(4):
        var joint = create_suspension(car, wheels[i])
        suspensions.append(joint)
    
    # 添加到场景
    add_child(car)
    for wheel in wheels:
        car.add_child(wheel)
        car.add_child(suspensions[i])
    
    # 引擎和控制器
    var engine = VehicleEngine.new()
    car.add_child(engine)
    
    var transmission = Transmission.new()
    car.add_child(transmission)
    
    var controller = VehicleController.new()
    car.add_child(controller)
    
    return car
```

### 6.2 摩托车

```gdscript
# 创建摩托车
func create_motorcycle():
    # 车身（简化为刚体）
    var bike = RigidBody3D.new()
    bike.mass = 200
    
    # 车轮位置
    var wheel_positions = [
        Vector3(-0.5, 0, 0.6),   # 前轮
        Vector3(0.5, 0, -0.6)    # 后轮
    ]
    
    # 创建车轮
    var wheels = []
    for pos in wheel_positions:
        var wheel = create_wheel(pos, 0.25, 0.1)
        wheels.append(wheel)
    
    # 创建悬挂
    var suspensions = []
    for i in range(2):
        var joint = create_suspension(bike, wheels[i])
        suspensions.append(joint)
    
    # 添加到场景
    add_child(bike)
    for wheel in wheels:
        bike.add_child(wheel)
        bike.add_child(suspensions[i])
    
    # 引擎和控制器
    var engine = VehicleEngine.new()
    bike.add_child(engine)
    
    var transmission = Transmission.new()
    bike.add_child(transmission)
    
    var controller = VehicleController.new()
    bike.add_child(controller)
    
    return bike
```

### 6.3 卡车

```gdscript
# 创建卡车
func create_truck():
    # 车身（更大）
    var truck = RigidBody3D.new()
    truck.mass = 5000
    
    # 车轮位置（更多车轮）
    var wheel_positions = [
        Vector3(-1.5, 0, 1.0),   # 左前
        Vector3(1.5, 0, 1.0),    # 右前
        Vector3(-1.5, 0, -1.0),  # 左后
        Vector3(1.5, 0, -1.0),   # 右后
        Vector3(-1.0, 0, -1.5),  # 左后边
        Vector3(1.0, 0, -1.5)    # 右后边
    ]
    
    # 创建车轮
    var wheels = []
    for pos in wheel_positions:
        var wheel = create_wheel(pos, 0.4, 0.2)
        wheels.append(wheel)
    
    # 创建悬挂
    var suspensions = []
    for i in range(6):
        var joint = create_suspension(truck, wheels[i])
        suspensions.append(joint)
    
    # 添加到场景
    add_child(truck)
    for wheel in wheels:
        truck.add_child(wheel)
        truck.add_child(suspensions[i])
    
    # 引擎和控制器
    var engine = VehicleEngine.new()
    truck.add_child(engine)
    
    var transmission = Transmission.new()
    truck.add_child(transmission)
    
    var controller = VehicleController.new()
    truck.add_child(controller)
    
    return truck
```

---

## 7. 高级特性

### 7.1 空气动力学

```gdscript
# 空气阻力
func apply_air_resistance():
    var speed = get_linear_velocity().length()
    var drag = 0.5 * speed * speed  # 简单的平方阻力
    
    # 应用阻力
    var force = -get_linear_velocity() * drag
    apply_central_force(force)

# 在 _integrate_forces 中调用
func _integrate_forces(state: PhysicsDirectBodyState3D):
    apply_air_resistance()
```

### 7.2 轮胎摩擦

```gdscript
# 轮胎摩擦
func apply_tire_friction():
    var speed = get_linear_velocity().length()
    var friction = 0.5 * speed  # 简单的线性摩擦
    
    # 应用摩擦力
    var force = -get_linear_velocity() * friction
    apply_central_force(force)

# 在 _integrate_forces 中调用
func _integrate_forces(state: PhysicsDirectBodyState3D):
    apply_tire_friction()
```

### 7.3 转向辅助

```gdscript
# 转向辅助（ABS）
func apply_steer_assist():
    var speed = get_linear_velocity().length()
    var angle = get_angular_velocity().length()
    
    # 高速时减少转向角度
    if speed > 50:
        var assist = 1 - (speed / 100)
        var max_angle = deg_to_rad(30 * assist)
        
        # 调整转向角度
        var steering = Input.get_action_strength("steer_left") - Input.get_action_strength("steer_right")
        steering = clamp(steering, -max_angle, max_angle)
        
        apply_steering(steering)

# 在 _integrate_forces 中调用
func _integrate_forces(state: PhysicsDirectBodyState3D):
    apply_steer_assist()
```

---

## 📝 本章总结

### 核心要点

1. **车辆物理由多个组件组成**，包括车身、车轮、悬挂和引擎
2. **悬挂系统通过关节连接**，控制车轮的上下运动
3. **引擎通过扭矩控制车轮旋转**，模拟动力
4. **控制器处理用户输入**，实现驾驶体验
5. **性能优化**包括减少车轮数量、调整参数等

### 关键术语

| 术语 | 解释 |
|------|------|
| Chassis | 车身，车辆的主刚体 |
| Wheel | 车轮，独立的刚体 |
| Suspension | 悬挂系统，连接车身和车轮的关节 |
| Engine | 引擎，提供动力的组件 |
| Transmission | 传动系统，控制齿轮和扭矩 |
| Vehicle Controller | 车辆控制器，处理用户输入 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Vehicle Physics](https://docs.godotengine.org/en/stable/tutorials/physics/vehicle_physics.html)
- **源码位置**: `servers/physics_3d/`, `scene/3d/vehicle_physics.cpp`
- **技术博客**: [Godot Car Physics Implementation](https://godotengine.org/article/car-physics-implementation/)

---

## 📋 下一章预告

**第 29 篇：流体模拟**

- 液体物理基础
- 水体模拟
- 流体动力学
- 粒子系统模拟
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 8,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*

---

## 8. 引擎和传动系统（新增）

### 8.1 引擎扭矩曲线

真实车辆的引擎输出不是恒定的，而是随 RPM（转速）变化的曲线。

```
典型引擎扭矩曲线:
┌─────────────────────────────────────────────────────────────┐
│ RPM    │ 0    │ 2000 │ 4000 │ 6000 │ 8000 │ 峰值          │
├─────────────────────────────────────────────────────────────┤
│ 扭矩   │ 0%   │ 60%  │ 100% │ 85%  │ 50%  │ 4000 RPM      │
│ 功率   │ 0%   │ 40%  │ 75%  │ 100% │ 90%  │ 7000 RPM      │
└─────────────────────────────────────────────────────────────┘

扭矩曲线类型:
- 线性型：电动车、电动机
- 峰值型：汽油发动机
- 平台型：柴油发动机（低转高扭）
```

```gdscript
# 引擎扭矩曲线
class_name EngineTorqueCurve

@export var max_rpm: float = 8000.0
@export var peak_torque: float = 400.0  # Nm
@export var peak_torque_rpm: float = 4000.0
@export var idle_rpm: float = 800.0

# 扭矩曲线数据点（RPM, 扭矩百分比）
var torque_curve = [
    Vector2(0, 0.0),
    Vector2(1000, 0.5),
    Vector2(2000, 0.75),
    Vector2(3000, 0.9),
    Vector2(4000, 1.0),  # 峰值扭矩
    Vector2(5000, 0.95),
    Vector2(6000, 0.85),
    Vector2(7000, 0.7),
    Vector2(8000, 0.5)
]

# 根据 RPM 获取扭矩
func get_torque(rpm: float) -> float:
    rpm = clamp(rpm, 0, max_rpm)
    
    # 查找曲线区间
    for i in range(torque_curve.size() - 1):
        var point_a = torque_curve[i]
        var point_b = torque_curve[i + 1]
        
        if rpm >= point_a.x and rpm <= point_b.x:
            # 线性插值
            var t = (rpm - point_a.x) / (point_b.x - point_a.x)
            var torque_percent = lerp(point_a.y, point_b.y, t)
            return peak_torque * torque_percent
    
    return 0.0

# 根据油门和 RPM 计算实际扭矩
func calculate_engine_torque(throttle: float, rpm: float) -> float:
    var base_torque = get_torque(rpm)
    return base_torque * throttle

# RPM 计算
func calculate_rpm(vehicle_speed: float, gear_ratio: float, final_drive: float, wheel_radius: float) -> float:
    # RPM = (车速 * 传动比 * 终传比) / (2π * 轮半径)
    var wheel_angular_velocity = vehicle_speed / wheel_radius
    var rpm = wheel_angular_velocity * gear_ratio * final_drive * 60.0 / (2.0 * PI)
    return clamp(rpm, idle_rpm, max_rpm)
```

### 8.2 变速箱模拟

```gdscript
# 手动变速箱
class_name ManualTransmission

@export var gear_ratios: Array[float] = [3.5, 2.0, 1.4, 1.0, 0.8, 0.6]  # 6 速
@export var final_drive: float = 3.5
@export var shift_time: float = 0.3  # 换挡时间（秒）
@export var clutch_friction: float = 0.9

var current_gear: int = 0  # 0 = 空挡
var engine_rpm: float = 800.0
var is_clutch_pressed: bool = false
var is_shifting: bool = false
var shift_timer: float = 0.0

func _physics_process(delta):
    if is_shifting:
        shift_timer += delta
        if shift_timer >= shift_time:
            is_shifting = false
    
    # 更新 RPM
    _update_rpm()

func shift_up():
    if current_gear < gear_ratios.size() - 1 and not is_shifting:
        is_shifting = true
        shift_timer = 0.0
        current_gear += 1
        print("Shifted up to gear ", current_gear)

func shift_down():
    if current_gear > 0 and not is_shifting:
        is_shifting = true
        shift_timer = 0.0
        current_gear -= 1
        print("Shifted down to gear ", current_gear)

func set_gear(gear: int):
    if gear >= 0 and gear < gear_ratios.size() and not is_shifting:
        current_gear = gear

func get_total_ratio() -> float:
    if current_gear == 0 or is_shifting:
        return 0.0  # 空挡或换挡中
    return gear_ratios[current_gear] * final_drive

func _update_rpm():
    # RPM 会根据车速和档位计算
    # 这里简化处理
    pass

# 自动变速箱
class_name AutomaticTransmission

extends ManualTransmission

@export var upshift_rpm: float = 6000.0
@export var downshift_rpm: float = 2000.0
@export var kickdown_rpm: float = 7000.0

var auto_mode: bool = true

func _physics_process(delta):
    super._physics_process(delta)
    
    if auto_mode:
        _auto_shift()

func _auto_shift():
    # 升档
    if engine_rpm > upshift_rpm and current_gear < gear_ratios.size() - 1:
        shift_up()
    
    # 降档
    elif engine_rpm < downshift_rpm and current_gear > 0:
        shift_down()
    
    # 强制降档（Kickdown）
    elif engine_rpm > kickdown_rpm and current_gear > 0:
        shift_down()
        if current_gear > 1:
            shift_down()
```

### 8.3 差速器模拟

```gdscript
# 开放式差速器
class_name OpenDifferential

@export var torque_split: float = 0.5  # 默认 50:50 分配

var left_wheel_speed: float = 0.0
var right_wheel_speed: float = 0.0
var input_torque: float = 0.0

# 计算左右轮扭矩
func calculate_wheel_torques() -> Dictionary:
    return {
        "left": input_torque * torque_split,
        "right": input_torque * (1.0 - torque_split)
    }

# 限滑差速器（LSD）
class_name LimitedSlipDifferential

extends OpenDifferential

@export var lock_factor: float = 0.3  # 0 = 开放，1 = 完全锁止

func calculate_wheel_torques() -> Dictionary:
    var speed_diff = abs(left_wheel_speed - right_wheel_speed)
    var avg_speed = (left_wheel_speed + right_wheel_speed) / 2.0
    
    # 根据速度差调整扭矩分配
    var lock_amount = clamp(speed_diff / 10.0, 0, lock_factor)
    
    var fast_wheel_torque = input_torque * (0.5 - lock_amount * 0.5)
    var slow_wheel_torque = input_torque * (0.5 + lock_amount * 0.5)
    
    if left_wheel_speed > right_wheel_speed:
        return {
            "left": fast_wheel_torque,
            "right": slow_wheel_torque
        }
    else:
        return {
            "left": slow_wheel_torque,
            "right": fast_wheel_torque
        }

# 全轮驱动（AWD）
class_name AllWheelDrive

@export var front_torque_split: float = 0.4  # 前轮 40%，后轮 60%
@export var center_diff_lock: bool = false

func calculate_axle_torques(input_torque: float) -> Dictionary:
    if center_diff_lock:
        return {
            "front": input_torque * 0.5,
            "rear": input_torque * 0.5
        }
    else:
        return {
            "front": input_torque * front_torque_split,
            "rear": input_torque * (1.0 - front_torque_split)
        }
```

---

## 9. 抓地力和漂移模型（新增）

### 9.1 轮胎摩擦模型

```
轮胎摩擦力组成:
┌─────────────────────────────────────────────────────────────┐
│ 纵向力（加速/刹车）                                          │
│   - 取决于：垂直载荷、滑移率、路面摩擦系数                   │
│                                                             │
│ 侧向力（转向）                                               │
│   - 取决于：侧偏角、垂直载荷、轮胎特性                       │
│                                                             │
│ 摩擦力椭圆（Friction Circle）                                │
│   - 纵向力和侧向力的合力不能超过极限                         │
│   - F_total² = F_longitudinal² + F_lateral²                 │
└─────────────────────────────────────────────────────────────┘

Pacejka 魔术公式（简化版）:
F = D * sin(C * arctan(B * x - E * (B * x - arctan(B * x))))

其中:
- B: 刚度因子
- C: 形状因子
- D: 峰值因子
- E: 曲率因子
- x: 滑移率或侧偏角
```

```gdscript
# 简化的轮胎摩擦模型
class_name TireFrictionModel

@export var friction_coefficient: float = 1.0  # 路面摩擦系数
@export var peak_friction: float = 1.2
@export var sliding_friction: float = 0.8

# 摩擦系数表（不同路面）
var surface_friction = {
    "dry_asphalt": 1.0,
    "wet_asphalt": 0.7,
    "ice": 0.2,
    "snow": 0.4,
    "gravel": 0.6,
    "dirt": 0.5,
    "grass": 0.45
}

# 计算纵向力（简化 Pacejka）
func calculate_longitudinal_force(slip_ratio: float, vertical_load: float) -> float:
    # 简化版本：线性 + 饱和
    var b = 10.0  # 刚度
    var d = peak_friction * vertical_load
    
    var force = d * sin(1.5 * atan(b * slip_ratio))
    
    # 限制在摩擦力椭圆内
    var max_force = friction_coefficient * vertical_load
    return clamp(force, -max_force, max_force)

# 计算侧向力
func calculate_lateral_force(slip_angle: float, vertical_load: float) -> float:
    var b = 8.0  # 侧向刚度
    var d = peak_friction * vertical_load
    
    var force = d * sin(1.4 * atan(b * slip_angle))
    
    var max_force = friction_coefficient * vertical_load
    return clamp(force, -max_force, max_force)

# 摩擦力椭圆检查
func check_friction_circle(longitudinal: float, lateral: float, max_force: float) -> Vector2:
    var total = Vector2(longitudinal, lateral)
    
    if total.length() > max_force:
        # 超出摩擦力椭圆，缩减到边界
        total = total.normalized() * max_force
    
    return total
```

### 9.2 漂移检测

```gdscript
# 漂移状态检测
class_name DriftDetector

extends Node

@export var drift_threshold: float = 0.3  # 滑移率阈值
@export var min_speed: float = 10.0  # 最小速度（km/h）

var is_drifting: bool = false
var drift_angle: float = 0.0
var drift_duration: float = 0.0

signal drift_started
signal drift_ended
signal drift_scored

func check_drift(vehicle_speed: float, slip_angle: float, slip_ratio: float) -> bool:
    # 速度检查
    if vehicle_speed < min_speed:
        if is_drifting:
            _end_drift()
        return false
    
    # 滑移角检查（侧滑）
    var abs_slip_angle = abs(slip_angle)
    
    # 滑移率检查（后轮空转）
    var abs_slip_ratio = abs(slip_ratio)
    
    # 漂移条件
    var drift_condition = (abs_slip_angle > drift_threshold) or (abs_slip_ratio > drift_threshold)
    
    if drift_condition and not is_drifting:
        _start_drift(abs_slip_angle)
    elif not drift_condition and is_drifting:
        _end_drift()
    elif is_drifting:
        _update_drift(abs_slip_angle)
    
    return is_drifting

func _start_drift(slip_angle: float):
    is_drifting = true
    drift_angle = slip_angle
    drift_duration = 0.0
    emit_signal("drift_started")
    print("Drift started! Angle: ", rad_to_deg(drift_angle))

func _end_drift():
    is_drifting = false
    emit_signal("drift_ended")
    print("Drift ended. Duration: ", drift_duration)

func _update_drift(slip_angle: float):
    drift_duration += 0.016  # 假设 60 FPS
    drift_angle = slip_angle
    
    # 计算漂移分数
    var score = calculate_drift_score()
    emit_signal("drift_scored", score)

func calculate_drift_score() -> int:
    # 分数 = 角度 * 持续时间 * 速度系数
    var angle_deg = rad_to_deg(drift_angle)
    var speed_factor = 1.0 + (drift_duration / 10.0)
    return int(angle_deg * drift_duration * speed_factor * 10)
```

### 9.3 漂移控制

```gdscript
# 漂移辅助控制
class_name DriftAssist

extends Node

@export var assist_strength: float = 0.5  # 0 = 无辅助，1 = 完全辅助
@export var auto_throttle: bool = true
@export var auto_steer: bool = false

var target_drift_angle: float = 0.0

func apply_drift_assist(vehicle: Node3D, input: Dictionary) -> Dictionary:
    var output = input.duplicate()
    
    # 自动油门（保持漂移）
    if auto_throttle:
        output.throttle = maintain_drift_throttle(vehicle)
    
    # 自动转向（控制漂移角度）
    if auto_steer:
        output.steer = control_drift_angle(vehicle, target_drift_angle)
    
    # 混合辅助
    if assist_strength < 1.0:
        output.throttle = lerp(input.throttle, output.throttle, assist_strength)
        output.steer = lerp(input.steer, output.steer, assist_strength)
    
    return output

func maintain_drift_throttle(vehicle: Node3D) -> float:
    # 根据当前滑移率调整油门
    var slip_ratio = vehicle.get("rear_slip_ratio") if vehicle.has_method("get") else 0.0
    
    if slip_ratio < 0.2:
        return 1.0  # 增加油门
    elif slip_ratio > 0.5:
        return 0.3  # 减少油门
    else:
        return 0.7  # 保持

func control_drift_angle(vehicle: Node3D, target_angle: float) -> float:
    var current_angle = vehicle.get("slip_angle") if vehicle.has_method("get") else 0.0
    var error = target_angle - current_angle
    
    # 简单的 P 控制器
    var steer = error * 0.5
    return clamp(steer, -1.0, 1.0)

# 漂移模式切换
func set_drift_mode(mode: String):
    match mode:
        "off":
            assist_strength = 0.0
            auto_throttle = false
            auto_steer = false
        "beginner":
            assist_strength = 0.7
            auto_throttle = true
            auto_steer = true
        "advanced":
            assist_strength = 0.3
            auto_throttle = true
            auto_steer = false
        "pro":
            assist_strength = 0.0
            auto_throttle = false
            auto_steer = false
```

### 9.4 漂移物理效果

```gdscript
# 漂移粒子效果
class_name DriftEffects

extends Node

@export var smoke_particles: PackedScene
@export var skid_marks: PackedScene
@export var spark_particles: PackedScene

var active_smoke: Array = []
var skid_mark_points: PackedVector3Array = []

func _ready():
    pass

func update_effects(is_drifting: bool, wheel_positions: Array):
    if is_drifting:
        _spawn_smoke(wheel_positions)
        _add_skid_mark(wheel_positions)
    else:
        _cleanup_effects()

func _spawn_smoke(wheel_positions: Array):
    # 在后轮位置生成烟雾
    for i in range(2, wheel_positions.size()):  # 假设后 2 个是后轮
        var pos = wheel_positions[i]
        
        var smoke = smoke_particles.instantiate()
        smoke.global_transform.origin = pos
        get_parent().add_child(smoke)
        active_smoke.append(smoke)
        
        # 限制数量
        if active_smoke.size() > 10:
            var old_smoke = active_smoke.pop_front()
            old_smoke.queue_free()

func _add_skid_mark(wheel_positions: Array):
    for i in range(2, wheel_positions.size()):
        skid_mark_points.append(wheel_positions[i])
        
        # 每 10 点生成一个胎痕
        if skid_mark_points.size() >= 10:
            _create_skid_mark_segment()

func _create_skid_mark_segment():
    if skid_marks and skid_mark_points.size() >= 2:
        var mark = skid_marks.instantiate()
        # 设置胎痕的曲线点
        # mark.set_points(skid_mark_points)
        get_parent().add_child(mark)
        skid_mark_points.clear()

func _cleanup_effects():
    for smoke in active_smoke:
        smoke.queue_free()
    active_smoke.clear()
```

### 9.5 漂移评分系统

```gdscript
# 漂移评分系统
class_name DriftScoring

extends Node

var current_combo: int = 0
var total_score: int = 0
var best_drift_angle: float = 0.0
var longest_drift_duration: float = 0.0

signal score_updated
signal new_record

func add_drift_score(angle: float, duration: float, speed: float) -> int:
    # 基础分数
    var base_score = int(angle * 100)
    
    # 持续时间加成
    var duration_bonus = int(duration * 50)
    
    # 速度加成
    var speed_bonus = int(speed * 10)
    
    # 连击加成
    var combo_multiplier = 1.0 + (current_combo * 0.1)
    
    # 总分
    var score = int((base_score + duration_bonus + speed_bonus) * combo_multiplier)
    
    total_score += score
    current_combo += 1
    
    # 更新记录
    if angle > best_drift_angle:
        best_drift_angle = angle
        emit_signal("new_record", "best_angle", angle)
    
    if duration > longest_drift_duration:
        longest_drift_duration = duration
        emit_signal("new_record", "longest_drift", duration)
    
    emit_signal("score_updated", total_score, score)
    
    return score

func reset_combo():
    current_combo = 0

func get_score_summary() -> Dictionary:
    return {
        "total": total_score,
        "combo": current_combo,
        "best_angle": rad_to_deg(best_drift_angle),
        "longest_drift": longest_drift_duration
    }
```

---

## 📝 本章总结（更新）

### 核心要点（更新）

1. **车辆物理由多个组件组成**，包括车身、车轮、悬挂和引擎
2. **悬挂系统通过关节连接**，控制车轮的上下运动
3. **引擎通过扭矩控制车轮旋转**，模拟动力
4. **控制器处理用户输入**，实现驾驶体验
5. **性能优化**包括减少车轮数量、调整参数等
6. **引擎扭矩曲线模拟真实动力输出**（新增）
7. **变速箱和差速器完善传动系统**（新增）
8. **抓地力和漂移模型增强驾驶乐趣**（新增）

### 关键术语（更新）

| 术语 | 解释 |
|------|------|
| Chassis | 车身，车辆的主刚体 |
| Wheel | 车轮，独立的刚体 |
| Suspension | 悬挂系统，连接车身和车轮的关节 |
| Engine | 引擎，提供动力的组件 |
| Transmission | 传动系统，控制齿轮和扭矩 |
| Vehicle Controller | 车辆控制器，处理用户输入 |
| Torque Curve | 扭矩曲线，引擎输出随 RPM 变化（新增） |
| Differential | 差速器，分配左右轮扭矩（新增） |
| Grip | 抓地力，轮胎与路面的摩擦力（新增） |
| Drift | 漂移，车辆侧滑状态（新增） |
| Slip Ratio | 滑移率，车轮空转程度（新增） |
| Slip Angle | 侧偏角，轮胎行进方向与指向的夹角（新增） |