# 第 14 篇：刚体物理

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 23 章 Godot 物理架构概述  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

刚体（Rigid Body）是物理系统中最基础也是最重要的对象类型。刚体完全由物理引擎控制，受重力、力、冲量等影响，能够与其他物理对象发生真实的碰撞和交互。理解刚体物理是掌握游戏物理模拟的关键。

本章将深入探讨刚体运动学、力和冲量应用、质量和惯性、阻尼和重力设置，以及刚体优化技巧。

---

## 🎯 学习目标

- 理解刚体运动学原理
- 掌握力和冲量的应用方法
- 熟悉质量和惯性张量配置
- 了解阻尼和重力的影响
- 学会刚体性能优化技巧

---

## 1. 刚体运动学

### 1.1 刚体基本属性

```gdscript
# 创建刚体并设置基本属性
var body = RigidBody3D.new()

# 质量（kg）
body.mass = 1.0

# 线性阻尼（空气阻力）
body.linear_damp = 0.1

# 角阻尼（旋转阻力）
body.angular_damp = 0.1

# 重力缩放
body.gravity_scale = 1.0

# 最大线性速度
body.max_linear_velocity = 100.0

# 最大角速度
body.max_angular_velocity = 20.0
```

### 1.2 运动状态查询

```gdscript
# 获取刚体状态
func get_body_state(body: RigidBody3D) -> Dictionary:
    return {
        "position": body.global_transform.origin,
        "rotation": body.global_transform.basis.get_euler(),
        "linear_velocity": body.linear_velocity,
        "angular_velocity": body.angular_velocity,
        "sleeping": body.sleeping,
        "mass": body.mass
    }

# 每帧监控
func _process(delta):
    var state = get_body_state($RigidBody3D)
    print("Position: ", state.position)
    print("Velocity: ", state.linear_velocity)
```

### 1.3 运动模式

```gdscript
# 刚体模式
body.mode = RigidBody3D.MODE_RIGID          # 正常刚体模式
body.mode = RigidBody3D.MODE_STATIC         # 静态模式（不可移动）
body.mode = RigidBody3D.MODE_KINEMATIC      # 运动学模式（脚本控制）
body.mode = RigidBody3D.MODE_CHARACTER      # 角色模式（特殊碰撞）
```

---

## 2. 力和冲量

### 2.1 施加力

```gdscript
# 施加力（持续作用）
func apply_forces(body: RigidBody3D):
    # 施加向下的力（类似重力）
    body.apply_central_force(Vector3(0, -10, 0))
    
    # 在特定位置施加力（产生扭矩）
    body.apply_force(Vector3(0, -10, 0), Vector3(1, 0, 0))
    
    # 施加扭矩（旋转力）
    body.apply_torque(Vector3(0, 10, 0))
    
    # 在局部坐标系施加力
    body.apply_central_force(body.transform.basis * Vector3(0, 0, -100))
```

### 2.2 施加冲量

```gdscript
# 施加冲量（瞬间作用）
func apply_impulses(body: RigidBody3D):
    # 施加中心冲量
    body.apply_central_impulse(Vector3(0, 10, 0))
    
    # 在特定位置施加冲量
    body.apply_impulse(Vector3(0, 10, 0), Vector3(1, 0, 0))
    
    # 施加角冲量
    body.apply_torque_impulse(Vector3(0, 5, 0))
    
    # 爆炸效果
    func create_explosion(position: Vector3, force: float, radius: float):
        var bodies = get_tree().get_nodes_in_group("rigid_bodies")
        for body in bodies:
            var direction = body.global_transform.origin - position
            var distance = direction.length()
            
            if distance < radius:
                direction = direction.normalized()
                var impulse = direction * force * (1 - distance / radius)
                body.apply_central_impulse(impulse)
```

### 2.3 力和冲量对比

| 特性 | 力（Force） | 冲量（Impulse） |
|------|------------|----------------|
| 作用时间 | 持续 | 瞬间 |
| 效果 | 加速度 | 速度变化 |
| 适用场景 | 重力、风力 | 爆炸、碰撞 |
| 计算 | F = ma | J = Δmv |

### 2.4 实用力场

```gdscript
# 重力场
class_name GravityField

extends Area3D

@export var gravity_strength: float = 9.8
@export var gravity_direction: Vector3 = Vector3.DOWN

func _ready():
    body_entered.connect(_on_body_entered)
    body_exited.connect(_on_body_exited)

func _on_body_entered(body):
    if body is RigidBody3D:
        body.add_central_force(gravity_direction * gravity_strength * body.mass)

func _on_body_exited(body):
    if body is RigidBody3D:
        # 移除力（需要自己跟踪）
        pass

# 风力场
class_name WindZone

extends Area3D

@export var wind_force: Vector3 = Vector3(10, 0, 0)
@export var noise: float = 0.5

func _physics_process(delta):
    var bodies = get_overlapping_bodies()
    for body in bodies:
        if body is RigidBody3D:
            var wind = wind_force + Vector3(
                randf_range(-noise, noise),
                randf_range(-noise, noise),
                randf_range(-noise, noise)
            )
            body.add_central_force(wind)
```

---

## 3. 质量和惯性

### 3.1 质量设置

```gdscript
# 设置质量
body.mass = 5.0

# 基于体积自动计算质量
func set_mass_from_volume(body: RigidBody3D, density: float):
    var collision_shapes = body.get_children().filter(func(child): 
        return child is CollisionShape3D 
    )
    
    var total_volume = 0.0
    for shape_node in collision_shapes:
        var shape = shape_node.shape
        if shape is BoxShape3D:
            total_volume += shape.size.x * shape.size.y * shape.size.z
        elif shape is SphereShape3D:
            total_volume += (4.0/3.0) * PI * pow(shape.radius, 3)
        elif shape is CylinderShape3D:
            total_volume += PI * pow(shape.radius, 2) * shape.height
    
    body.mass = total_volume * density
```

### 3.2 惯性张量

```gdscript
# 设置惯性张量
body.custom_inertia_vector = Vector3(1, 1, 1)

# 计算盒体的惯性张量
func calculate_box_inertia(mass: float, size: Vector3) -> Vector3:
    var x = (mass / 12.0) * (size.y * size.y + size.z * size.z)
    var y = (mass / 12.0) * (size.x * size.x + size.z * size.z)
    var z = (mass / 12.0) * (size.x * size.x + size.y * size.y)
    return Vector3(x, y, z)

# 计算球体的惯性张量
func calculate_sphere_inertia(mass: float, radius: float) -> Vector3:
    var inertia = (2.0/5.0) * mass * radius * radius
    return Vector3(inertia, inertia, inertia)

# 应用惯性张量
func setup_inertia(body: RigidBody3D, shape_type: String, mass: float, size: Vector3):
    match shape_type:
        "box":
            body.custom_inertia_vector = calculate_box_inertia(mass, size)
        "sphere":
            body.custom_inertia_vector = calculate_sphere_inertia(mass, size.x)
```

---

## 4. 阻尼和重力

### 4.1 线性阻尼

```gdscript
# 线性阻尼（空气阻力）
body.linear_damp = 0.1  # 0 = 无阻尼，1 = 强阻尼

# 不同介质的阻尼
func set_medium_damping(body: RigidBody3D, medium: String):
    match medium:
        "air":
            body.linear_damp = 0.05
        "water":
            body.linear_damp = 1.0
        "honey":
            body.linear_damp = 5.0
        "vacuum":
            body.linear_damp = 0.0
```

### 4.2 角阻尼

```gdscript
# 角阻尼（旋转阻力）
body.angular_damp = 0.1

# 设置角阻尼
func setup_angular_damping(body: RigidBody3D, damping: float):
    body.angular_damp = damping
```

### 4.3 重力配置

```gdscript
# 重力缩放
body.gravity_scale = 1.0  # 1 = 正常重力，0 = 无重力，-1 = 反重力

# 月球重力
func set_moon_gravity(body: RigidBody3D):
    body.gravity_scale = 0.165  # 月球重力是地球的 16.5%

# 火星重力
func set_mars_gravity(body: RigidBody3D):
    body.gravity_scale = 0.378  # 火星重力是地球的 37.8%

# 零重力
func set_zero_gravity(body: RigidBody3D):
    body.gravity_scale = 0.0

# 反重力
func set_antigravity(body: RigidBody3D):
    body.gravity_scale = -1.0
```

### 4.4 自定义重力

```gdscript
# 全局自定义重力
func _physics_process(delta):
    var custom_gravity = Vector3(0, -20, 0)  # 2 倍重力
    
    for body in get_tree().get_nodes_in_group("rigid_bodies"):
        if body is RigidBody3D and body.gravity_scale != 0:
            body.apply_central_force(custom_gravity * body.mass * body.gravity_scale)
```

---

## 5. 碰撞和接触

### 5.1 碰撞信号

```gdscript
# 连接碰撞信号
func _ready():
    $RigidBody3D.body_entered.connect(_on_body_entered)
    $RigidBody3D.body_exited.connect(_on_body_exited)
    $RigidBody3D.contact_monitor = true
    $RigidBody3D.max_contacts_reported = 4

# 碰撞进入
func _on_body_entered(other_body):
    print("Collision with: ", other_body.name)
    
    # 获取碰撞信息
    var contact_count = $RigidBody3D.get_contact_count()
    for i in range(contact_count):
        var contact_pos = $RigidBody3D.get_contact_local_position(i)
        var contact_normal = $RigidBody3D.get_contact_local_normal(i)
        var contact_collider = $RigidBody3D.get_contact_collider(i)
        
        print("Contact ", i, ": ", contact_pos, " Normal: ", contact_normal)

# 碰撞退出
func _on_body_exited(other_body):
    print("Exited collision with: ", other_body.name)
```

### 5.2 碰撞响应

```gdscript
# 自定义碰撞响应
func _integrate_forces(state: PhysicsDirectBodyState3D):
    # 获取碰撞信息
    for i in range(state.get_contact_count()):
        var collider = state.get_contact_collider(i)
        var velocity = state.get_contact_local_velocity(i)
        
        # 根据碰撞速度做出反应
        if velocity.length() > 5.0:
            # 高速碰撞，播放效果
            _play_impact_effect(collider, velocity)
```

---

## 6. 睡眠和激活

### 6.1 睡眠配置

```gdscript
# 睡眠设置
body.can_sleep = true  # 允许睡眠
body.sleeping = false  # 强制唤醒
body.sleep_threshold = 0.1  # 睡眠阈值
```

### 6.2 睡眠状态监控

```gdscript
# 监控睡眠状态
func _process(delta):
    if $RigidBody3D.sleeping:
        print("Body is sleeping")
    else:
        print("Body is active")

# 强制唤醒
func wake_up_body(body: RigidBody3D):
    body.sleeping = false
    body.apply_central_impulse(Vector3(0, 1, 0))  # 轻微冲量唤醒
```

---

## 7. 连续碰撞检测（CCD）

### 7.1 CCD 配置

```gdscript
# 启用 CCD
body.cd_mode = RigidBody3D.CCD_MODE_CAST_RAY
# body.cd_mode = RigidBody3D.CCD_MODE_CAST_SHAPE
# body.cd_mode = RigidBody3D.CCD_MODE_DISABLED

# CCD 运动阈值
body.ccd_motion_threshold = 0.01
```

### 7.2 CCD 使用场景

```
何时使用 CCD:
✅ 高速移动物体（子弹、投掷物）
✅ 小物体穿过大物体
✅ 精确碰撞要求
❌ 静态或慢速物体（性能开销）
```

---

## 8. 实践：刚体应用

### 8.1 可投掷物体

```gdscript
class_name ThrowableObject

extends RigidBody3D

@export var throw_force: float = 20.0
@export var is_held: bool = false

var held_position: Vector3
var held_rotation: Quaternion

func _ready():
    mode = MODE_KINEMATIC
    contact_monitor = true
    max_contacts_reported = 4

func throw(direction: Vector3):
    mode = MODE_RIGID
    sleeping = false
    apply_central_impulse(direction.normalized() * throw_force)
    
    # 添加随机旋转
    apply_torque_impulse(Vector3(
        randf_range(-5, 5),
        randf_range(-5, 5),
        randf_range(-5, 5)
    ))

func hold(position: Vector3, rotation: Quaternion):
    is_held = true
    held_position = position
    held_rotation = rotation
    mode = MODE_KINEMATIC

func release():
    is_held = false
    mode = MODE_RIGID

func _physics_process(delta):
    if is_held:
        global_transform.origin = held_position
        global_transform.basis = Basis(held_rotation)
```

### 8.2 多米诺骨牌

```gdscript
# 创建多米诺骨牌
func create_domino_line(start_pos: Vector3, count: int, spacing: float):
    for i in range(count):
        var domino = RigidBody3D.new()
        domino.mass = 0.5
        domino.linear_damp = 0.1
        domino.angular_damp = 0.5
        
        # 碰撞形状
        var collision = CollisionShape3D.new()
        var shape = BoxShape3D.new()
        shape.size = Vector3(0.1, 0.5, 0.3)
        collision.shape = shape
        domino.add_child(collision)
        
        # 网格
        var mesh = MeshInstance3D.new()
        var box_mesh = BoxMesh.new()
        box_mesh.size = shape.size
        mesh.mesh = box_mesh
        domino.add_child(mesh)
        
        # 位置
        domino.global_transform.origin = start_pos + Vector3(i * spacing, 0.25, 0)
        
        add_child(domino)
```

### 8.3 保龄球瓶

```gdscript
# 创建保龄球瓶阵列
func create_bowling_pins(origin: Vector3):
    var positions = [
        Vector3(0, 0, 0),      # 1
        Vector3(-0.3, 0, 0.3), # 2
        Vector3(0.3, 0, 0.3),  # 3
        Vector3(-0.6, 0, 0.6), # 4
        Vector3(0, 0, 0.6),    # 5
        Vector3(0.6, 0, 0.6),  # 6
        Vector3(-0.9, 0, 0.9), # 7
        Vector3(-0.3, 0, 0.9), # 8
        Vector3(0.3, 0, 0.9),  # 9
        Vector3(0.9, 0, 0.9)   # 10
    ]
    
    for pos in positions:
        var pin = RigidBody3D.new()
        pin.mass = 1.5
        pin.linear_damp = 0.2
        pin.angular_damp = 0.5
        
        # 使用胶囊体模拟保龄球瓶
        var collision = CollisionShape3D.new()
        var shape = CapsuleShape3D.new()
        shape.radius = 0.15
        shape.height = 0.6
        collision.shape = shape
        pin.add_child(collision)
        
        pin.global_transform.origin = origin + pos + Vector3(0, 0.3, 0)
        add_child(pin)
```

---

## 9. 性能优化

### 9.1 优化策略

```
✅ 刚体优化清单:
□ 使用简单的碰撞形状
□ 合理设置质量（避免极端值）
□ 启用睡眠
□ 使用碰撞层过滤
□ 避免过多活动刚体
□ 使用 LOD 物理
□ 合并静态刚体
□ 调整物理更新频率
```

### 9.2 刚体池

```gdscript
# 刚体对象池
class_name RigidBodyPool

var pool = []
var body_scene: PackedScene

func _init(scene: PackedScene, initial_count: int):
    body_scene = scene
    for i in range(initial_count):
        var body = body_scene.instantiate()
        body.set_process(false)
        pool.append(body)

func get_body(position: Vector3) -> RigidBody3D:
    var body: RigidBody3D
    
    if pool.size() > 0:
        body = pool.pop_back()
    else:
        body = body_scene.instantiate()
    
    body.global_transform.origin = position
    body.sleeping = false
    body.set_process(true)
    return body

func return_body(body: RigidBody3D):
    body.set_process(false)
    body.sleeping = true
    body.linear_velocity = Vector3.ZERO
    body.angular_velocity = Vector3.ZERO
    pool.append(body)
```

---

## 10. 刚体插值与平滑（新增）

### 10.1 插值模式

```gdscript
# 刚体插值配置
var body = RigidBody3D.new()

# 插值模式
body.physics_material_override = null

# Godot 4.x 插值设置
# 默认启用插值，使视觉表现更平滑

# 检查插值状态
func is_interpolation_enabled(body: RigidBody3D) -> bool:
    # 在 Godot 4.x 中，插值自动处理
    # 可通过 _process 和 _physics_process 的差异观察
    return true

# 手动插值（可选）
var previous_transform: Transform3D
var current_transform: Transform3D
var interpolation_alpha: float = 0.0

func _physics_process(delta):
    previous_transform = current_transform
    current_transform = $RigidBody3D.global_transform

func _process(delta):
    # 计算插值 alpha（0-1）
    interpolation_alpha = Engine.get_physics_interpolation_fraction()
    
    # 插值变换
    var interpolated = previous_transform.interpolate_with(
        current_transform, 
        interpolation_alpha
    )
    
    # 应用到视觉网格
    $VisualMesh.global_transform = interpolated
```

### 10.2 避免刚体抖动

```gdscript
# 常见问题：刚体在斜坡或表面上抖动
# 原因：物理更新与渲染不同步

# 解决方案 1：增加线性阻尼
func reduce_jitter(body: RigidBody3D):
    body.linear_damp = 0.5  # 增加阻尼
    body.angular_damp = 0.5

# 解决方案 2：降低睡眠阈值
func enable_aggressive_sleep(body: RigidBody3D):
    body.sleep_threshold = 0.05  # 更低的阈值
    body.can_sleep = true

# 解决方案 3：使用 AnimatableBody
# 对于需要脚本控制但又要物理交互的物体
func use_animatable_body():
    # AnimatableBody3D 不会抖动
    # 适合移动平台、动画物体
    pass

# 解决方案 4：增加物理更新频率
func increase_physics_rate():
    Engine.physics_ticks_per_second = 120
    # 更频繁的物理更新 = 更平滑的运动
```

### 10.3 网络同步刚体

```gdscript
# 多人游戏中同步刚体位置
class_name NetworkedRigidBody

extends RigidBody3D

@export var is_owner: bool = true
@export var sync_rate: float = 10.0  # 每秒同步 10 次

var last_sync_time: float = 0.0
var remote_transform: Transform3D
var interpolation_target: Transform3D

func _ready():
    if not is_owner:
        # 远程物体：禁用物理模拟
        mode = MODE_KINEMATIC
        physics_material_override = PhysicsMaterial.new()
        physics_material_override.friction = 0.0
        physics_material_override.bounce = 0.0

func _physics_process(delta):
    if is_owner:
        # 本地物体：发送状态
        _sync_state()
    else:
        # 远程物体：插值位置
        _interpolate_remote()

func _sync_state():
    var current_time = Time.get_ticks_msec() / 1000.0
    
    if current_time - last_sync_time >= 1.0 / sync_rate:
        # 发送网络消息
        var state = {
            "position": global_transform.origin,
            "rotation": global_transform.basis,
            "linear_velocity": linear_velocity,
            "angular_velocity": angular_velocity
        }
        
        # 使用 RPC 或其他网络方式发送
        # rpc("_receive_state", state)
        
        last_sync_time = current_time

func _receive_state(state: Dictionary):
    # 接收远程状态
    interpolation_target = Transform3D(state["rotation"], state["position"])
    
    # 直接设置速度（可选）
    linear_velocity = state["linear_velocity"]
    angular_velocity = state["angular_velocity"]

func _interpolate_remote():
    if interpolation_target:
        # 平滑插值到目标位置
        global_transform.origin = global_transform.origin.lerp(
            interpolation_target.origin, 
            0.2  # 插值速度
        )
        global_transform.basis = global_transform.basis.slerp(
            interpolation_target.basis, 
            0.2
        )
```

---

## 11. _integrate_forces 深度解析（新增）

### 11.1 PhysicsDirectBodyState3D 详解

`_integrate_forces` 是刚体物理计算的核心回调，在每次物理更新时调用。

```gdscript
# 完整的 _integrate_forces 实现
func _integrate_forces(state: PhysicsDirectBodyState3D):
    # 1. 获取当前状态
    var transform = state.transform
    var linear_velocity = state.linear_velocity
    var angular_velocity = state.angular_velocity
    
    # 2. 获取时间步长
    var step = state.step  # 固定时间步长（如 1/60）
    
    # 3. 获取重力
    var gravity = state.total_gravity
    
    # 4. 获取角重力（较少用）
    var angular_gravity = Vector3.ZERO
    
    # 5. 获取碰撞信息
    var contact_count = state.get_contact_count()
    for i in range(contact_count):
        var local_pos = state.get_contact_local_position(i)
        var local_normal = state.get_contact_local_normal(i)
        var collider_id = state.get_contact_collider_id(i)
        var collider_velocity = state.get_contact_collider_velocity_at_position(i)
        
        # 处理碰撞
        _handle_contact(local_pos, local_normal, collider_id)
    
    # 6. 获取施加的力
    var total_force = state.total_applied_force
    var total_torque = state.total_applied_torque
    
    # 7. 修改物理状态（可选）
    # state.linear_velocity = Vector3.ZERO  # 停止线性运动
    # state.angular_velocity = Vector3.ZERO  # 停止旋转
    
    # 8. 添加自定义力
    # apply_custom_forces(state, step)
```

### 11.2 自定义力积分

```gdscript
# 在 _integrate_forces 中添加自定义力
func _integrate_forces(state: PhysicsDirectBodyState3D):
    # 示例：添加向心力（模拟轨道运动）
    var center = Vector3.ZERO
    var to_center = center - state.transform.origin
    var distance = to_center.length()
    
    if distance > 0.1:
        # F = G * m1 * m2 / r^2
        var gravity_constant = 100.0
        var force_magnitude = gravity_constant / (distance * distance)
        var force = to_center.normalized() * force_magnitude
        
        # 应用到刚体
        state.apply_central_force(force)
    
    # 示例：添加阻力（与速度平方成正比）
    var velocity = state.linear_velocity
    var speed = velocity.length()
    
    if speed > 0.1:
        var drag_coefficient = 0.5
        var drag_force = -velocity.normalized() * speed * speed * drag_coefficient
        state.apply_central_force(drag_force)

# 自定义力应用函数
func apply_custom_forces(state: PhysicsDirectBodyState3D, step: float):
    # 示例：弹簧力（胡克定律 F = -kx）
    var rest_position = Vector3.ZERO
    var displacement = state.transform.origin - rest_position
    var spring_constant = 50.0
    var spring_force = -displacement * spring_constant
    
    state.apply_central_force(spring_force)
    
    # 示例：阻尼力 F = -cv
    var damping_constant = 5.0
    var damping_force = -state.linear_velocity * damping_constant
    
    state.apply_central_force(damping_force)
```

### 11.3 碰撞数据访问

```gdscript
# 详细的碰撞信息处理
func _integrate_forces(state: PhysicsDirectBodyState3D):
    var contact_count = state.get_contact_count()
    
    for i in range(contact_count):
        # 碰撞点（局部坐标）
        var local_pos = state.get_contact_local_position(i)
        
        # 碰撞法线（局部坐标）
        var local_normal = state.get_contact_local_normal(i)
        
        # 碰撞点（全局坐标）
        var global_pos = state.transform * local_pos
        
        # 碰撞物体 ID
        var collider_id = state.get_contact_collider_id(i)
        
        # 碰撞物体（如果可访问）
        var collider = instance_from_id(collider_id)
        
        # 碰撞点的相对速度
        var relative_velocity = state.get_contact_local_velocity(i)
        
        # 碰撞冲量
        var impulse = state.get_contact_impulse(i)
        
        # 碰撞形状
        var shape_idx = state.get_contact_local_shape(i)
        
        # 处理碰撞
        _process_collision({
            "local_position": local_pos,
            "global_position": global_pos,
            "normal": local_normal,
            "collider_id": collider_id,
            "collider": collider,
            "relative_velocity": relative_velocity,
            "impulse": impulse,
            "shape_index": shape_idx
        })

# 碰撞处理示例
func _process_collision(data: Dictionary):
    # 高速碰撞检测
    if data.impulse.length() > 10.0:
        print("High impact collision!")
        _play_impact_sound(data.global_position)
        _spawn_particles(data.global_position)
    
    # 根据碰撞物体类型响应
    if data.collider and data.collider.is_in_group("destructible"):
        var damage = data.impulse.length() * 0.1
        data.collider.take_damage(damage)
```

### 11.4 状态修改

```gdscript
# 在 _integrate_forces 中修改刚体状态
func _integrate_forces(state: PhysicsDirectBodyState3D):
    # 示例 1：速度限制
    var max_speed = 50.0
    if state.linear_velocity.length() > max_speed:
        state.linear_velocity = state.linear_velocity.normalized() * max_speed
    
    # 示例 2：角速度限制
    var max_angular_speed = 10.0
    if state.angular_velocity.length() > max_angular_speed:
        state.angular_velocity = state.angular_velocity.normalized() * max_angular_speed
    
    # 示例 3：强制静止（条件触发）
    if should_stop():
        state.linear_velocity = Vector3.ZERO
        state.angular_velocity = Vector3.ZERO
    
    # 示例 4：修改重力
    var custom_gravity = Vector3(0, -20, 0)  # 2 倍重力
    state.total_gravity = custom_gravity
    
    # 示例 5：添加持续力
    state.apply_central_force(Vector3(0, 10, 0))  # 持续向上的力
```

### 11.5 性能注意事项

```
_integrate_forces 性能提示:
┌─────────────────────────────────────────────────────────────┐
│ ✅ 推荐做法              │ ❌ 避免做法                      │
├─────────────────────────────────────────────────────────────┤
│ 只处理必要计算          │ 每帧创建新对象                  │
│ 缓存碰撞结果            │ 访问场景树（get_node）          │
│ 使用接触数据代替信号    │ 网络请求                        │
│ 批量处理力              │ 复杂算法（每帧调用）            │
│ 简单数学运算            │ 文件 I/O                        │
└─────────────────────────────────────────────────────────────┘

性能对比:
- 简单 _integrate_forces: ~0.01ms/刚体
- 复杂 _integrate_forces: ~0.1ms/刚体
- 包含场景访问：~1.0ms/刚体（避免！）
```

---

## 📝 本章总结

---

## 📝 本章总结

### 核心要点

1. **刚体完全由物理引擎控制**，通过力和冲量影响运动
2. **质量和惯性决定运动特性**，合理设置很重要
3. **阻尼模拟介质阻力**，影响物体停止速度
4. **睡眠机制优化性能**，静止物体进入睡眠
5. **CCD 防止穿模**，但增加性能开销

### 关键术语

| 术语 | 解释 |
|------|------|
| Force | 力，持续作用的物理量 |
| Impulse | 冲量，瞬间作用的速度变化 |
| Damping | 阻尼，模拟阻力的参数 |
| CCD | 连续碰撞检测，防止高速穿模 |
| Inertia | 惯性，物体抵抗运动变化的属性 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot RigidBody3D](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html)
- **物理教程**: [Godot Physics Tutorial](https://docs.godotengine.org/en/stable/tutorials/physics/using_kinematic_body_3d.html)
- **源码位置**: `servers/physics_3d/`, `scene/3d/physics_body_3d.cpp`
- **技术博客**: [Godot Physics Deep Dive](https://godotengine.org/article/godot-physics-deep-dive/)

---

## 📋 下一章预告

**第 25 篇：碰撞检测**

- 碰撞检测原理
- 碰撞形状优化
- 射线投射技术
- 碰撞回调处理
- 碰撞性能优化

---

*写作时间：2026-03-20*  
*字数：约 6,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*
