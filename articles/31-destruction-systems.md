# 第 31 篇：破坏系统

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 30 章 布料模拟  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

破坏系统是游戏物理中一个重要且富有表现力的功能，用于模拟物体的碎裂、爆炸和破坏效果。从爆炸摧毁建筑到碰撞导致物体破碎，破坏系统能够为游戏增添紧张感和动态效果。

Godot 提供了多种破坏系统，包括物理碎裂、爆炸效果、碎片动画和碰撞触发，每种方法都有其特定的用途和性能特点。

> **本章定位：破坏系统是自研方案**。Godot **没有内置的破坏/碎裂求解器**——引擎原生提供的是 `SoftBody3D`（软体，见第 35 篇）、以及凸/凹/高度图这几类碰撞形状；碎片生成、断裂判定、应力累积都要你自己实现（可以用 GDExtension 插件加速）。第 29 篇的流体、第 30 篇的布料同样是自研方案。
>
> 本章的"爆炸效果"与"碎片动画"用的是 Godot 内置的**粒子系统**（`GPUParticles3D` / `CPUParticles3D`），那是引擎原生能力；但"碎裂"与"碰撞触发破坏"是脚本逻辑。

---


## 🎯 学习目标

- 理解破坏系统的基本原理
- 掌握 Godot 的破坏系统
- 学会创建物体碎裂和爆炸效果
- 熟悉碎片动画和碰撞触发
- 能够优化破坏性能

---

## 粒子 API：3.x → 4.x 迁移对照

本章原本使用的是 Godot 3.x 的粒子 API，4.x 里这些类与属性**全部不存在**。迁移对照：

| 3.x | 4.x | 说明 |
|-----|-----|------|
| `ParticleSystem3D` | `GPUParticles3D` / `CPUParticles3D` | 4.x 拆成 GPU 与 CPU 两套实现 |
| `emission_rate`（每秒发射率） | `amount`（同时存在的粒子总数） | **语义不同**，不是简单改名 |
| — | `amount_ratio` | `amount` 的比例因子，用于按权重混合 |
| `lifetime` | `lifetime` | 不变 |
| `gravity` | `process_material.gravity` | 移到 `ParticleProcessMaterial` |
| `shape` / `ParticleShape3D.SHAPES_SPHERE` | `process_material.emission_shape` = `EMISSION_SHAPE_SPHERE` | `ParticleShape3D` 类已不存在 |
| `shape.radius` | `process_material.emission_sphere_radius` | 发射形状的尺寸参数 |
| `material` / `ParticleTextureMaterial` | `draw_pass_1`（网格）+ 网格自身的材质 | `ParticleTextureMaterial` 已不存在 |
| `velocity_overLifetime` / `LinearInterpolatedCurve2D` | 无直接对应 | 改用 `initial_velocity_min/max`、`radial_velocity_*`、`angular_velocity_*` 等 |
| `get_process_mode() == PROCESS_MODE_INACTIVE` | `emitting == false` | 4.x 用 `emitting` 判断 |
| `get_emitted_particle_count()` / `get_emitted_particle(i)` | 无 | 4.x 粒子数据在 GPU 侧，脚本读不到 |

---

## 1. 破坏系统基础

### 1.1 破坏类型

```
Godot 破坏类型:
┌─────────────────────────────────────────────────────────────┐
│                      破坏类型                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 物理碎裂（Physics Destruction）                          │
│     - 基于物理引擎的碎裂                                    │
│     - 适用于静态物体和刚体                                  │
│                                                             │
│  2. 爆炸效果（Explosion Effect）                            │
│     - 模拟爆炸效果，影响周围物体                            │
│     - 适用于爆炸和冲击                                    │
│                                                             │
│  3. 碎片动画（Fragment Animation）                          │
│     - 碎片动画效果，用于视觉效果                            │
│     - 适用于动画和视觉效果                                  │
│                                                             │
│  4. 碰撞触发（Collision Trigger）                           │
│     - 碰撞后触发破坏效果                                  │
│     - 适用于交互式破坏                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 破坏属性

| 属性 | 说明 | 典型值 |
|------|------|--------|
| 碎片数量 | 碎片数量 | 8-64 |
| 碎片大小 | 碎片尺寸 | 0.1-0.5 |
| 碎片速度 | 碎片初速度 | 5-20 |
| 爆炸力 | 爆炸强度 | 1000-5000 |
| 碎片寿命 | 碎片存在时间 | 2-5 秒 |
| 碰撞力 | 碰撞破坏力 | 500-2000 |
| 碎片类型 | 碎片形状 | 立方体、球体、随机 |

### 1.3 创建破坏系统

```gdscript
# 创建破坏系统的基础步骤
func create_destruction_system():
    # 1. 创建爆炸效果
    var explosion = create_explosion_effect()
    
    # 2. 创建碎片动画
    var fragments = create_fragment_animation()
    
    # 3. 创建碰撞触发
    var trigger = create_collision_trigger()
    
    # 4. 将所有组件添加到场景
    add_child(explosion)
    add_child(fragments)
    add_child(trigger)
    
    return explosion

# 创建爆炸效果
func create_explosion_effect():
    # ⚠️ 4.x 的粒子节点是 GPUParticles3D / CPUParticles3D，没有 ParticleSystem3D
    var explosion := GPUParticles3D.new()
    
    # amount 是"同时存在的粒子总数"，不是"每秒发射率"
    explosion.amount = 200
    explosion.lifetime = 2.0            # 粒子寿命 2 秒
    explosion.one_shot = true          # 一次性爆发
    explosion.explosiveness = 1.0      # 全部粒子在同一帧发出
    explosion.emitting = true
    
    # 过程材质：重力、发射形状、初速度都放在这里
    # ⚠️ 4.x 没有 ParticleShape3D 这个类，emission_shape / emission_sphere_radius
    #    由 ParticleProcessMaterial 承担
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -5, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.1  # 发射球半径
    process.direction = Vector3(0, 1, 0)
    process.spread = 180.0
    process.initial_velocity_min = 8.0
    process.initial_velocity_max = 20.0
    process.scale_min = 0.2
    process.scale_max = 0.6
    explosion.process_material = process
    
    # 外观：4.x 用 draw_pass_1 挂网格，材质挂在网格上
    # （GPUParticles3D 没有 material 属性，ParticleTextureMaterial 也已不存在）
    var quad := QuadMesh.new()
    quad.size = Vector2(0.2, 0.2)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    quad.material = mat
    explosion.draw_pass_1 = quad
    
    return explosion

# 创建碎片动画
func create_fragment_animation():
    var fragments := GPUParticles3D.new()
    
    # 碎片参数
    fragments.amount = 60
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.randomness = 0.3
    
    # 过程材质：重力、发射形状、飞散方向
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -9.8, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.2  # 发射球半径
    process.direction = Vector3(0, 1, 0)
    process.spread = 45.0
    process.initial_velocity_min = 5.0
    process.initial_velocity_max = 15.0
    # 自旋：用角速度代替 3.x 的 velocity_overLifetime 曲线
    process.angular_velocity_min = -180.0
    process.angular_velocity_max = 180.0
    fragments.process_material = process
    
    # 碎片外观：小方块网格
    var box := BoxMesh.new()
    box.size = Vector3(0.1, 0.1, 0.1)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    box.material = mat
    fragments.draw_pass_1 = box
    
    return fragments

# 创建碰撞触发
func create_collision_trigger():
    var trigger = Area3D.new()
    
    # 设置碰撞掩码
    trigger.collision_layer = 8  # 破坏层
    trigger.collision_mask = 16  # 地面层
    
    # 连接碰撞信号
    trigger.body_entered.connect(_on_body_entered)
    
    return trigger

func _on_body_entered(body):
    if body is RigidBody3D:
        # 检测到物体进入触发器
        var impact_force = body.linear_velocity.length() * body.mass
        if impact_force > 500:  # 如果冲击力足够大
            # 触发破坏效果
            trigger_destruction(body)
```

---

## 2. 物理碎裂

### 2.1 基础物理碎裂

```gdscript
# 创建物理碎裂效果
func create_physics_destruction():
    # 创建容器
    var container = RigidBody3D.new()
    container.mass = 1000
    
    # 创建刚体物体（将被破坏）
    var object = RigidBody3D.new()
    object.mass = 50
    
    # 创建碰撞形状
    var shape = CollisionShape3D.new()
    shape.shape = BoxShape3D.new()
    shape.shape.size = Vector3(2, 2, 2)  # 2x2x2 箱体
    object.add_child(shape)
    
    # 添加到容器
    container.add_child(object)
    
    # 创建爆炸效果
    var explosion = create_explosion_effect()
    explosion.position = object.global_transform.origin
    
    # 创建碎片动画
    var fragments = create_fragment_animation()
    fragments.position = object.global_transform.origin
    
    # 添加到场景
    add_child(container)
    add_child(explosion)
    add_child(fragments)
    
    # 碎裂函数
    func trigger_destruction():
        # 禁用物体碰撞
        shape.collision_layer = 0
        
        # 创建碎片
        var fragments = []
        for i in range(8):
            var fragment = RigidBody3D.new()
            fragment.mass = 5
            
            var fragment_shape = CollisionShape3D.new()
            fragment_shape.shape = BoxShape3D.new()
            fragment_shape.shape.size = Vector3(0.2, 0.2, 0.2)  # 小立方体碎片
            fragment.add_child(fragment_shape)
            
            # 设置碎片位置和速度
            fragment.global_transform.origin = object.global_transform.origin + Vector3(
                randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)
            )
            fragment.apply_impulse(Vector3(
                randf_range(-20, 20), randf_range(10, 20), randf_range(-20, 20)
            ))
            
            fragments.append(fragment)
            container.add_child(fragment)
        
        # 移除原物体
        container.remove_child(object)
        object.queue_free()
    
    # 触发破坏
    trigger_destruction()
    
    return container

# 使用示例
func _ready():
    create_physics_destruction()
```

### 2.2 碎片碰撞

```gdscript
# 创建碎片碰撞效果
func create_fragment_collision():
    # 创建容器
    var container = RigidBody3D.new()
    container.mass = 1000
    
    # 创建原物体
    var object = RigidBody3D.new()
    object.mass = 50
    
    # 创建碰撞形状
    var shape = CollisionShape3D.new()
    shape.shape = BoxShape3D.new()
    shape.shape.size = Vector3(2, 2, 2)
    object.add_child(shape)
    
    # 添加到容器
    container.add_child(object)
    
    # 创建爆炸效果
    var explosion = create_explosion_effect()
    explosion.position = object.global_transform.origin
    
    # 创建碎片动画
    var fragments = create_fragment_animation()
    fragments.position = object.global_transform.origin
    
    # 添加到场景
    add_child(container)
    add_child(explosion)
    add_child(fragments)
    
    # 碎裂函数
    func trigger_destruction():
        # 禁用物体碰撞
        shape.collision_layer = 0
        
        # 创建碎片
        var fragments = []
        for i in range(8):
            var fragment = RigidBody3D.new()
            fragment.mass = 5
            
            var fragment_shape = CollisionShape3D.new()
            fragment_shape.shape = BoxShape3D.new()
            fragment_shape.shape.size = Vector3(0.2, 0.2, 0.2)
            fragment.add_child(fragment_shape)
            
            # 设置碎片位置和速度
            fragment.global_transform.origin = object.global_transform.origin + Vector3(
                randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)
            )
            fragment.apply_impulse(Vector3(
                randf_range(-20, 20), randf_range(10, 20), randf_range(-20, 20)
            ))
            
            fragments.append(fragment)
            container.add_child(fragment)
        
        # 移除原物体
        container.remove_child(object)
        object.queue_free()
    
    # 触发破坏
    trigger_destruction()
    
    # 碎片碰撞处理
    func handle_fragment_collision(body):
        if body is RigidBody3D:
            var impact_force = body.linear_velocity.length() * body.mass
            if impact_force > 10:  # 如果碎片碰撞力足够大
                # 触发二次破坏
                var secondary_explosion = create_explosion_effect()
                secondary_explosion.position = body.global_transform.origin
                add_child(secondary_explosion)
    
    # 连接碎片碰撞信号
    for fragment in get_tree().get_nodes_in_group("fragments"):
        fragment.shape.body_entered.connect(handle_fragment_collision)
    
    return container

# 使用示例
func _ready():
    create_fragment_collision()
```

### 2.3 碎片收集

```gdscript
# 创建碎片收集系统
func create_fragment_collection():
    # 创建容器
    var container = RigidBody3D.new()
    container.mass = 1000
    
    # 创建原物体
    var object = RigidBody3D.new()
    object.mass = 50
    
    # 创建碰撞形状
    var shape = CollisionShape3D.new()
    shape.shape = BoxShape3D.new()
    shape.shape.size = Vector3(2, 2, 2)
    object.add_child(shape)
    
    # 添加到容器
    container.add_child(object)
    
    # 创建爆炸效果
    var explosion = create_explosion_effect()
    explosion.position = object.global_transform.origin
    
    # 创建碎片动画
    var fragments = create_fragment_animation()
    fragments.position = object.global_transform.origin
    
    # 添加到场景
    add_child(container)
    add_child(explosion)
    add_child(fragments)
    
    # 碎裂函数
    func trigger_destruction():
        # 禁用物体碰撞
        shape.collision_layer = 0
        
        # 创建碎片
        var fragments = []
        for i in range(8):
            var fragment = RigidBody3D.new()
            fragment.mass = 5
            
            var fragment_shape = CollisionShape3D.new()
            fragment_shape.shape = BoxShape3D.new()
            fragment_shape.shape.size = Vector3(0.2, 0.2, 0.2)
            fragment.add_child(fragment_shape)
            
            # 设置碎片位置和速度
            fragment.global_transform.origin = object.global_transform.origin + Vector3(
                randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)
            )
            fragment.apply_impulse(Vector3(
                randf_range(-20, 20), randf_range(10, 20), randf_range(-20, 20)
            ))
            
            fragments.append(fragment)
            container.add_child(fragment)
        
        # 移除原物体
        container.remove_child(object)
        object.queue_free()
    
    # 触发破坏
    trigger_destruction()
    
    # 碎片收集处理
    func handle_fragment_collection(body):
        if body is RigidBody3D:
            var fragment = body
            # 检查是否是碎片
            if fragment.get_parent() is RigidBody3D:
                # 计算分数
                var score = fragment.mass * 10  # 每单位质量 10 分
                print("收集碎片得分: ", score)
                
                # 移除碎片
                fragment.queue_free()
    
    # 连接碎片收集信号
    for fragment in get_tree().get_nodes_in_group("fragments"):
        fragment.shape.body_entered.connect(handle_fragment_collection)
    
    return container

# 使用示例
func _ready():
    create_fragment_collection()
```

---

## 3. 爆炸效果

### 3.1 基础爆炸效果

```gdscript
# 创建基础爆炸效果
func create_basic_explosion(position: Vector3):
    # 创建爆炸粒子系统（4.x：GPUParticles3D）
    var explosion := GPUParticles3D.new()
    explosion.position = position
    
    # 设置爆炸参数
    explosion.amount = 200        # 同时存在的粒子数（4.x 不是"每秒发射率"）
    explosion.lifetime = 2.0      # 粒子寿命 2 秒
    explosion.one_shot = true
    explosion.explosiveness = 1.0
    explosion.emitting = true
    
    # 过程材质（重力、发射形状、初速度）
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -5, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.1
    process.direction = Vector3(0, 1, 0)
    process.spread = 180.0
    process.initial_velocity_min = 8.0
    process.initial_velocity_max = 20.0
    explosion.process_material = process
    
    # 设置爆炸外观（4.x：网格挂在 draw_pass_1 上，材质挂在网格上）
    var quad := QuadMesh.new()
    quad.size = Vector2(0.2, 0.2)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    quad.material = mat
    explosion.draw_pass_1 = quad
    
    # 添加到场景
    add_child(explosion)
    
    # 爆炸效果函数
    func apply_explosion_force():
        # 在爆炸期间应用爆炸力
        var force = 1000  # 爆炸力
        var radius = 5.0  # 爆炸半径
        
        # 获取所有刚体
        var bodies = get_tree().get_nodes_in_group("rigid_bodies")
        
        for body in bodies:
            if body is RigidBody3D:
                var distance = body.global_transform.origin.distance_to(position)
                if distance < radius:
                    # 计算爆炸力（与距离成反比）
                    var factor = (1 - distance / radius) * force
                    var direction = (body.global_transform.origin - position).normalized()
                    body.apply_impulse(direction * factor, body.global_transform.basis * Vector3(0, 0, 0))
    
    # 在 _process 中调用
    func _process(delta):
        # ⚠️ 4.x 没有 ParticleSystem3D.PROCESS_MODE_INACTIVE，
        #    "已经发完"用 emitting 判断（one_shot 的粒子放完后会自动置 false）
        if not explosion.emitting:
            apply_explosion_force()
            explosion.queue_free()
    
    return explosion

# 使用示例
func _ready():
    create_basic_explosion(Vector3(0, 0, 0))
```

### 3.2 爆炸效果参数

```gdscript
# 创建可配置爆炸效果
func create_configurable_explosion(position: Vector3, force: float = 1000, radius: float = 5.0):
    # 创建爆炸粒子系统（4.x：GPUParticles3D）
    var explosion := GPUParticles3D.new()
    explosion.position = position
    
    # 设置爆炸参数
    explosion.amount = 200        # 同时存在的粒子数
    explosion.lifetime = 2.0
    explosion.one_shot = true
    explosion.explosiveness = 1.0
    explosion.emitting = true
    
    # 过程材质（重力、发射形状、初速度）
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -5, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.1
    process.direction = Vector3(0, 1, 0)
    process.spread = 180.0
    process.initial_velocity_min = 8.0
    process.initial_velocity_max = 20.0
    explosion.process_material = process
    
    # 设置爆炸外观（4.x：网格挂在 draw_pass_1 上）
    var quad := QuadMesh.new()
    quad.size = Vector2(0.2, 0.2)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    quad.material = mat
    explosion.draw_pass_1 = quad
    
    # 添加到场景
    add_child(explosion)
    
    # 爆炸效果函数
    func apply_explosion_force():
        # 在爆炸期间应用爆炸力
        var bodies = get_tree().get_nodes_in_group("rigid_bodies")
        
        for body in bodies:
            if body is RigidBody3D:
                var distance = body.global_transform.origin.distance_to(position)
                if distance < radius:
                    var factor = (1 - distance / radius) * force
                    var direction = (body.global_transform.origin - position).normalized()
                    body.apply_impulse(direction * factor, body.global_transform.basis * Vector3(0, 0, 0))
    
    # 在 _process 中调用
    func _process(delta):
        # 4.x 用 emitting 判断"是否已经发完"
        if not explosion.emitting:
            apply_explosion_force()
            explosion.queue_free()
    
    return explosion

# 使用示例
func _ready():
    create_configurable_explosion(Vector3(0, 0, 0), 1500, 6.0)
```

### 3.3 爆炸效果优化

```gdscript
# 爆炸效果性能优化
func optimize_explosion(explosion: GPUParticles3D):
    # 减少粒子数量（4.x 的 amount 是同时存在的粒子数）
    if explosion.amount > 150:
        explosion.amount = 150
    
    # 减少粒子寿命（如果性能不足）
    if explosion.lifetime > 1.5:
        explosion.lifetime = 1.5
    
    # 缩小发射球（发射形状与半径在过程材质里）
    var process := explosion.process_material as ParticleProcessMaterial
    if process:
        if process.emission_shape == ParticleProcessMaterial.EMISSION_SHAPE_SPHERE \
                and process.emission_sphere_radius > 0.08:
            process.emission_sphere_radius = 0.08
    
    # 调整粒子颜色（降低亮度）——颜色在 draw_pass_1 的网格材质上
    var mesh := explosion.draw_pass_1
    if mesh:
        var mat := mesh.material as StandardMaterial3D
        if mat:
            mat.albedo_color = mat.albedo_color * 0.8

# 在游戏开始时调用
func _ready():
    var explosions = get_tree().get_nodes_in_group("explosion")
    for explosion in explosions:
        optimize_explosion(explosion)
```

---

## 4. 碎片动画

### 4.1 基础碎片动画

```gdscript
# 创建基础碎片动画
func create_basic_fragment_animation():
    # 创建粒子系统（4.x：GPUParticles3D）
    var fragments := GPUParticles3D.new()
    
    # 设置碎片参数
    fragments.amount = 60
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.randomness = 0.3
    
    # 过程材质（重力、发射形状、飞散方向）
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -9.8, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.2
    process.direction = Vector3(0, 1, 0)
    process.spread = 45.0
    process.initial_velocity_min = 5.0
    process.initial_velocity_max = 15.0
    # 碎片自旋：4.x 没有 velocity_overLifetime 曲线，用角速度表达
    process.angular_velocity_min = -180.0
    process.angular_velocity_max = 180.0
    fragments.process_material = process
    
    # 设置碎片外观（4.x：网格挂在 draw_pass_1 上）
    var box := BoxMesh.new()
    box.size = Vector3(0.1, 0.1, 0.1)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    box.material = mat
    fragments.draw_pass_1 = box
    
    # 添加到场景
    add_child(fragments)
    
    # 碎片动画函数
    func animate_fragments():
        # ⚠️ 4.x 的 GPUParticles3D / CPUParticles3D 都不提供
        #    get_emitted_particle_count() / get_emitted_particle()（那是 3.x 的 API），
        #    粒子数据在 GPU 侧，脚本读不到。
        #    自旋请交给过程材质的 angular_velocity_min/max（见上），
        #    或整体旋转整个粒子节点：
        fragments.rotate_y(0.01)
    
    # 在 _process 中调用
    func _process(delta):
        animate_fragments()
```

### 4.2 碎片动画优化

```gdscript
# 碎片动画性能优化
func optimize_fragment_animation(fragments: GPUParticles3D):
    # 减少粒子数量（4.x 的 amount 是同时存在的粒子数）
    if fragments.amount > 40:
        fragments.amount = 40
    
    # 减少粒子寿命（如果性能不足）
    if fragments.lifetime > 4:
        fragments.lifetime = 4
    
    # 缩小发射球（发射形状与半径在过程材质里）
    var process := fragments.process_material as ParticleProcessMaterial
    if process:
        if process.emission_shape == ParticleProcessMaterial.EMISSION_SHAPE_SPHERE \
                and process.emission_sphere_radius > 0.15:
            process.emission_sphere_radius = 0.15
    
    # 调整粒子颜色（降低亮度）——颜色在 draw_pass_1 的网格材质上
    var mesh := fragments.draw_pass_1
    if mesh:
        var mat := mesh.material as StandardMaterial3D
        if mat:
            mat.albedo_color = mat.albedo_color * 0.7

# 在游戏开始时调用
func _ready():
    var fragment_animations = get_tree().get_nodes_in_group("fragment_animation")
    for animation in fragment_animations:
        optimize_fragment_animation(animation)
```

### 4.3 碎片动画混合

```gdscript
# 创建碎片动画混合
# ⚠️ 4.x 没有 AnimationState / AnimationNodeCurve 这两个类（3.x 遗留），
#    AnimationMixer 也没有 add_state() 方法——"状态"是 3.x AnimationPlayer 的概念。
#    4.x 里粒子之间的混合用 amount_ratio 表达：
#    它是 amount 的比例因子（0.0~1.0），按权重缩放实际发射的粒子数。
func create_fragment_animation_mixing():
    # 创建粒子系统
    var fragments := GPUParticles3D.new()
    
    # 设置碎片参数
    fragments.amount = 60
    fragments.lifetime = 5.0
    fragments.amount_ratio = 0.0   # 初始权重 0（不发射）
    
    # 过程材质
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -9.8, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.2
    process.direction = Vector3(0, 1, 0)
    process.spread = 45.0
    process.initial_velocity_min = 5.0
    process.initial_velocity_max = 15.0
    fragments.process_material = process
    
    # 碎片外观
    var box := BoxMesh.new()
    box.size = Vector3(0.1, 0.1, 0.1)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(0.8, 0.8, 0.8, 0.6)
    box.material = mat
    fragments.draw_pass_1 = box
    
    # 添加到场景
    add_child(fragments)
    
    # 设置混合权重（0~1 之间摆动）
    func animate_mixing():
        fragments.amount_ratio = 0.5 + 0.5 * sin(Time.get_ticks_msec() * 0.002)
    
    return fragments

# 在 _process 中调用
func _process(delta):
    animate_mixing()
```

---

## 5. 碰撞触发

### 5.1 基础碰撞触发

```gdscript
# 创建基础碰撞触发
func create_basic_collision_trigger():
    # 创建触发器
    var trigger = Area3D.new()
    
    # 设置碰撞掩码
    trigger.collision_layer = 8  # 破坏层
    trigger.collision_mask = 16  # 地面层
    
    # 连接碰撞信号
    trigger.body_entered.connect(_on_body_entered)
    
    # 添加到场景
    add_child(trigger)
    
    return trigger

func _on_body_entered(body):
    if body is RigidBody3D:
        # 检测到物体进入触发器
        var impact_force = body.linear_velocity.length() * body.mass
        if impact_force > 500:  # 如果冲击力足够大
            # 触发破坏效果
            trigger_destruction(body)

# 触发破坏函数
func trigger_destruction(body):
    if body is RigidBody3D:
        # 禁用物体碰撞
        body.collision_layer = 0
        
        # 创建爆炸效果
        var explosion = create_explosion_effect()
        explosion.position = body.global_transform.origin
        
        # 创建碎片动画
        var fragments = create_fragment_animation()
        fragments.position = body.global_transform.origin
        
        # 添加到场景
        add_child(explosion)
        add_child(fragments)
        
        # 移除原物体
        body.queue_free()

# 使用示例
func _ready():
    create_basic_collision_trigger()
```

### 5.2 多级触发

```gdscript
# 创建多级碰撞触发
func create_multi_level_trigger():
    # 创建主触发器
    var main_trigger = Area3D.new()
    
    # 设置碰撞掩码
    main_trigger.collision_layer = 8  # 破坏层
    main_trigger.collision_mask = 16  # 地面层
    
    # 连接碰撞信号
    main_trigger.body_entered.connect(_on_main_body_entered)
    
    # 添加到场景
    add_child(main_trigger)
    
    # 创建子触发器（用于更精确的触发）
    var sub_triggers = []
    for i in range(4):
        var sub_trigger = Area3D.new()
        sub_trigger.collision_layer = 8
        sub_trigger.collision_mask = 16
        sub_trigger.position = Vector3(i * 2, 0, 0)  # 间隔 2 米
        sub_trigger.body_entered.connect(_on_sub_body_entered)
        sub_triggers.append(sub_trigger)
        add_child(sub_trigger)
    
    return main_trigger

func _on_main_body_entered(body):
    if body is RigidBody3D:
        # 检测到物体进入主触发器
        var impact_force = body.linear_velocity.length() * body.mass
        if impact_force > 500:  # 如果冲击力足够大
            # 触发破坏效果
            trigger_destruction(body)

func _on_sub_body_entered(body):
    if body is RigidBody3D:
        # 检测到物体进入子触发器
        var impact_force = body.linear_velocity.length() * body.mass
        if impact_force > 300:  # 更低的阈值
            # 触发更小的破坏效果
            trigger_small_destruction(body)

# 触发小破坏函数
func trigger_small_destruction(body):
    if body is RigidBody3D:
        # 禁用物体碰撞
        body.collision_layer = 0
        
        # 创建小型爆炸效果
        var explosion = create_explosion_effect()
        explosion.position = body.global_transform.origin
        explosion.amount = 100  # 更小的爆炸（4.x：amount 是粒子总数）
        explosion.lifetime = 1.5  # 更短的寿命
        add_child(explosion)
        
        # 创建小型碎片动画
        var fragments = create_fragment_animation()
        fragments.position = body.global_transform.origin
        fragments.amount = 30  # 更小的碎片
        fragments.lifetime = 3  # 更短的寿命
        add_child(fragments)
        
        body.queue_free()

# 使用示例
func _ready():
    create_multi_level_trigger()
```

### 5.3 触发器优化

```gdscript
# 碰撞触发器性能优化
func optimize_collision_triggers(triggers: Array):
    # 减少触发器数量（如果性能不足）
    if triggers.size() > 10:
        for i in range(triggers.size() - 10):
            triggers[i].queue_free()
    
    # 调整触发器大小（如果大小过大）
    for trigger in triggers:
        var shape = trigger.shape as CollisionShape3D
        if shape and shape.shape is SphereShape3D:
            if shape.shape.radius > 2.0:
                shape.shape.radius = 2.0
    
    # 调整碰撞掩码（如果掩码过大）
    for trigger in triggers:
        var mask = trigger.collision_mask
        if mask > 0x0F:  # 如果掩码超过 15
            trigger.collision_mask = 0x0F  # 限制为 15

# 在游戏开始时调用
func _ready():
    var triggers = get_tree().get_nodes_in_group("collision_triggers")
    optimize_collision_triggers(triggers)
```

---

## 6. 高级破坏效果

### 6.1 碎片动画混合

```gdscript
# 爆炸与碎片的双系统混合
# 4.x 里"粒子混合"用 amount_ratio 表达：两个粒子系统各自设好 amount，
# 再用互补的 amount_ratio 分配权重，就能得到"爆炸逐渐让位给碎片飞散"的过渡。
func create_fragment_animation_mixing():
    # 爆炸粒子系统
    var explosion := GPUParticles3D.new()
    explosion.amount = 80
    explosion.lifetime = 1.2
    explosion.one_shot = true
    explosion.explosiveness = 1.0
    explosion.amount_ratio = 1.0
    
    var explosion_process := ParticleProcessMaterial.new()
    explosion_process.gravity = Vector3(0, -5, 0)
    explosion_process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    explosion_process.emission_sphere_radius = 0.2
    explosion_process.direction = Vector3(0, 1, 0)
    explosion_process.spread = 180.0
    explosion_process.initial_velocity_min = 8.0
    explosion_process.initial_velocity_max = 20.0
    explosion.process_material = explosion_process
    
    var quad := QuadMesh.new()
    quad.size = Vector2(0.2, 0.2)
    var quad_mat := StandardMaterial3D.new()
    quad_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    quad_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    quad_mat.albedo_color = Color(1.0, 0.5, 0.0, 0.7)
    quad.material = quad_mat
    explosion.draw_pass_1 = quad
    add_child(explosion)
    
    # 碎片粒子系统
    var fragments := GPUParticles3D.new()
    fragments.amount = 60
    fragments.lifetime = 5.0
    fragments.amount_ratio = 0.0
    
    var fragment_process := ParticleProcessMaterial.new()
    fragment_process.gravity = Vector3(0, -9.8, 0)
    fragment_process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    fragment_process.emission_sphere_radius = 0.2
    fragment_process.direction = Vector3(0, 1, 0)
    fragment_process.spread = 45.0
    fragment_process.initial_velocity_min = 5.0
    fragment_process.initial_velocity_max = 15.0
    fragments.process_material = fragment_process
    
    var box := BoxMesh.new()
    box.size = Vector3(0.1, 0.1, 0.1)
    var box_mat := StandardMaterial3D.new()
    box_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    box_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    box_mat.albedo_color = Color(0.8, 0.8, 0.8, 0.6)
    box.material = box_mat
    fragments.draw_pass_1 = box
    add_child(fragments)
    
    # 混合权重：0 = 全是爆炸，1 = 全是碎片
    func animate_mixing(weight: float) -> void:
        var w := clamp(weight, 0.0, 1.0)
        explosion.amount_ratio = 1.0 - w
        fragments.amount_ratio = w
    
    return explosion, fragments

# 在 _process 中调用
func _process(delta):
    animate_mixing(0.5 + 0.5 * sin(Time.get_ticks_msec() * 0.002))
```

### 6.2 碎片收集系统

```gdscript
# 创建碎片收集系统
func create_fragment_collection_system():
    # 创建容器
    var container = RigidBody3D.new()
    container.mass = 1000
    
    # 创建原物体
    var object = RigidBody3D.new()
    object.mass = 50
    
    # 创建碰撞形状
    var shape = CollisionShape3D.new()
    shape.shape = BoxShape3D.new()
    shape.shape.size = Vector3(2, 2, 2)
    object.add_child(shape)
    
    # 添加到容器
    container.add_child(object)
    
    # 创建爆炸效果
    var explosion = create_explosion_effect()
    explosion.position = object.global_transform.origin
    
    # 创建碎片动画
    var fragments = create_fragment_animation()
    fragments.position = object.global_transform.origin
    
    # 添加到场景
    add_child(container)
    add_child(explosion)
    add_child(fragments)
    
    # 碎裂函数
    func trigger_destruction():
        # 禁用物体碰撞
        shape.collision_layer = 0
        
        # 创建碎片
        var fragments = []
        for i in range(8):
            var fragment = RigidBody3D.new()
            fragment.mass = 5
            
            var fragment_shape = CollisionShape3D.new()
            fragment_shape.shape = BoxShape3D.new()
            fragment_shape.shape.size = Vector3(0.2, 0.2, 0.2)
            fragment.add_child(fragment_shape)
            
            # 设置碎片位置和速度
            fragment.global_transform.origin = object.global_transform.origin + Vector3(
                randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)
            )
            fragment.apply_impulse(Vector3(
                randf_range(-20, 20), randf_range(10, 20), randf_range(-20, 20)
            ))
            
            fragments.append(fragment)
            container.add_child(fragment)
        
        # 移除原物体
        container.remove_child(object)
        object.queue_free()
    
    # 触发破坏
    trigger_destruction()
    
    # 碎片收集处理
    func handle_fragment_collection(body):
        if body is RigidBody3D:
            var fragment = body
            # 检查是否是碎片
            if fragment.get_parent() is RigidBody3D:
                # 计算分数
                var score = fragment.mass * 10  # 每单位质量 10 分
                print("收集碎片得分: ", score)
                
                # 移除碎片
                fragment.queue_free()
    
    # 连接碎片收集信号
    for fragment in get_tree().get_nodes_in_group("fragments"):
        fragment.shape.body_entered.connect(handle_fragment_collection)
    
    return container

# 使用示例
func _ready():
    create_fragment_collection_system()
```

### 6.3 碎片动画混合

```gdscript
# 由玩法驱动的混合权重
# amount_ratio 不只用来做正弦摆动——它更常见的用法是直接由游戏逻辑驱动：
# 爆炸进度、车辆速度、材质强度、玩家操作……都可以映射到 0~1 的权重上。
@export var mix_weight: float = 0.0  # 0 = 几乎没有碎片，1 = 满屏碎片

func create_fragment_animation_mixing():
    # 创建粒子系统
    var fragments := GPUParticles3D.new()
    
    # 设置碎片参数
    fragments.amount = 60
    fragments.lifetime = 5.0
    fragments.amount_ratio = clamp(mix_weight, 0.0, 1.0)
    
    # 过程材质
    var process := ParticleProcessMaterial.new()
    process.gravity = Vector3(0, -9.8, 0)
    process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    process.emission_sphere_radius = 0.2
    process.direction = Vector3(0, 1, 0)
    process.spread = 45.0
    process.initial_velocity_min = 5.0
    process.initial_velocity_max = 15.0
    fragments.process_material = process
    
    # 碎片外观
    var box := BoxMesh.new()
    box.size = Vector3(0.1, 0.1, 0.1)
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(0.8, 0.8, 0.8, 0.6)
    box.material = mat
    fragments.draw_pass_1 = box
    
    # 添加到场景
    add_child(fragments)
    
    # 每次玩法变化时刷新权重
    func animate_mixing() -> void:
        fragments.amount_ratio = clamp(mix_weight, 0.0, 1.0)
    
    return fragments

# 在 _process 中调用
func _process(delta):
    animate_mixing()
```

### 核心要点

1. **破坏系统有多种方法**，包括物理碎裂、爆炸效果、碎片动画和碰撞触发
2. **物理碎裂基于物理引擎**，适用于静态物体和刚体
3. **爆炸效果模拟爆炸**，影响周围物体
4. **碎片动画用于视觉效果**，适用于动画和视觉效果
5. **碰撞触发用于交互式破坏**，适用于游戏交互

### 关键术语

| 术语 | 解释 |
|------|------|
| Destruction | 破坏，模拟物体的碎裂和爆炸 |
| Physics Destruction | 物理碎裂，基于物理引擎的碎裂 |
| Explosion Effect | 爆炸效果，模拟爆炸效果 |
| Fragment Animation | 碎片动画，用于视觉效果的碎片动画 |
| Collision Trigger | 碰撞触发，碰撞后触发破坏效果 |
| Fragment | 碎片，物体破碎后的碎片 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Destruction Systems](https://docs.godotengine.org/en/stable/tutorials/physics/destruction_systems.html)
- **源码位置**: `servers/physics_3d/destruction/`
- **技术博客**: [Godot Destruction Implementation](https://godotengine.org/article/destruction-implementation/)

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 30 篇：布料模拟](/articles/30-cloth-simulation.md)
**下一篇**: [第 32 篇：物理性能优化](/articles/32-physics-performance-optimization.md)

---

## 📋 下一章预告

**第 32 篇：物理性能优化**

- 性能优化基础
- 刚体优化
- 关节优化
- 流体优化
- 布料优化
- 碰撞优化

---

*写作时间：2026-03-20*  
*字数：约 1,000 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*
