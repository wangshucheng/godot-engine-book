# 第 21 篇：破坏系统

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 30 章 布料模拟  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

破坏系统是游戏物理中一个重要且富有表现力的功能，用于模拟物体的碎裂、爆炸和破坏效果。从爆炸摧毁建筑到碰撞导致物体破碎，破坏系统能够为游戏增添紧张感和动态效果。

Godot 提供了多种破坏系统，包括物理碎裂、爆炸效果、碎片动画和碰撞触发，每种方法都有其特定的用途和性能特点。

---

## 🎯 学习目标

- 理解破坏系统的基本原理
- 掌握 Godot 的破坏系统
- 学会创建物体碎裂和爆炸效果
- 熟悉碎片动画和碰撞触发
- 能够优化破坏性能

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
    var explosion = ParticleSystem3D.new()
    
    # 设置爆炸参数
    explosion.emission_rate = 2000  # 每秒发射 2000 个粒子
    explosion.lifetime = 2.0  # 粒子寿命 2 秒
    explosion.gravity = Vector3(0, -5, 0)  # 重力
    
    # 设置爆炸外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    explosion.material = material
    
    # 设置粒子形状
    explosion.shape = ParticleShape3D.new()
    explosion.shape.shape = ParticleShape3D.SHAPES_SPHERE
    explosion.shape.radius = 0.1  # 粒子半径
    
    # 设置粒子速度（爆炸向外扩散）
    explosion.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    explosion.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    explosion.velocity_overLifetime.add_point(0.5, Vector3(20, 10, 20))
    explosion.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
    return explosion

# 创建碎片动画
func create_fragment_animation():
    var fragments = ParticleSystem3D.new()
    
    # 设置碎片参数
    fragments.emission_rate = 50  # 每秒发射 50 个碎片
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.gravity = Vector3(0, -9.8, 0)  # 重力
    
    # 设置碎片外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    fragments.material = material
    
    # 设置碎片形状
    fragments.shape = ParticleShape3D.new()
    fragments.shape.shape = ParticleShape3D.SHAPES_CUBE
    fragments.shape.radius = 0.2  # 碎片半径
    
    # 设置碎片速度（碎片向不同方向飞散）
    fragments.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    fragments.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    fragments.velocity_overLifetime.add_point(0.5, Vector3(10, 15, 10))
    fragments.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
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
    # 创建爆炸粒子系统
    var explosion = ParticleSystem3D.new()
    explosion.position = position
    
    # 设置爆炸参数
    explosion.emission_rate = 2000  # 每秒发射 2000 个粒子
    explosion.lifetime = 2.0  # 粒子寿命 2 秒
    explosion.gravity = Vector3(0, -5, 0)  # 重力
    
    # 设置爆炸外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    explosion.material = material
    
    # 设置粒子形状
    explosion.shape = ParticleShape3D.new()
    explosion.shape.shape = ParticleShape3D.SHAPES_SPHERE
    explosion.shape.radius = 0.1  # 粒子半径
    
    # 设置粒子速度（爆炸向外扩散）
    explosion.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    explosion.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    explosion.velocity_overLifetime.add_point(0.5, Vector3(20, 10, 20))
    explosion.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
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
        if explosion.get_process_mode() == ParticleSystem3D.PROCESS_MODE_INACTIVE:
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
    # 创建爆炸粒子系统
    var explosion = ParticleSystem3D.new()
    explosion.position = position
    
    # 设置爆炸参数
    explosion.emission_rate = 2000  # 每秒发射 2000 个粒子
    explosion.lifetime = 2.0  # 粒子寿命 2 秒
    explosion.gravity = Vector3(0, -5, 0)  # 重力
    
    # 设置爆炸外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(1.0, 0.5, 0.0, 0.7)  # 橙色半透明
    explosion.material = material
    
    # 设置粒子形状
    explosion.shape = ParticleShape3D.new()
    explosion.shape.shape = ParticleShape3D.SHAPES_SPHERE
    explosion.shape.radius = 0.1  # 粒子半径
    
    # 设置粒子速度（爆炸向外扩散）
    explosion.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    explosion.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    explosion.velocity_overLifetime.add_point(0.5, Vector3(20, 10, 20))
    explosion.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
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
        if explosion.get_process_mode() == ParticleSystem3D.PROCESS_MODE_INACTIVE:
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
func optimize_explosion(explosion: ParticleSystem3D):
    # 减少发射率（如果性能不足）
    if explosion.emission_rate > 1500:
        explosion.emission_rate = 1500
    
    # 减少粒子寿命（如果性能不足）
    if explosion.lifetime > 1.5:
        explosion.lifetime = 1.5
    
    # 减少粒子数量（如果性能不足）
    if explosion.shape.radius > 0.08:
        explosion.shape.radius = 0.08
    
    # 调整粒子颜色（降低亮度）
    if explosion.material:
        explosion.material.color = explosion.material.color * 0.8

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
    # 创建粒子系统
    var fragments = ParticleSystem3D.new()
    
    # 设置碎片参数
    fragments.emission_rate = 50  # 每秒发射 50 个碎片
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.gravity = Vector3(0, -9.8, 0)  # 重力
    
    # 设置碎片外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    fragments.material = material
    
    # 设置碎片形状
    fragments.shape = ParticleShape3D.new()
    fragments.shape.shape = ParticleShape3D.SHAPES_CUBE
    fragments.shape.radius = 0.2  # 碎片半径
    
    # 设置碎片速度（碎片向不同方向飞散）
    fragments.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    fragments.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    fragments.velocity_overLifetime.add_point(0.5, Vector3(10, 15, 10))
    fragments.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
    # 添加到场景
    add_child(fragments)
    
    # 碎片动画函数
    func animate_fragments():
        # 在每帧更新时调用
        var time = Time.get_ticks_msec() * 0.001
        
        # 模拟碎片旋转
        for i in range(fragments.get_emitted_particle_count()):
            var particle = fragments.get_emitted_particle(i)
            particle.rotation = particle.rotation * 0.99  # 缓慢旋转
    
    # 添加到场景
    add_child(fragments)
    
    return fragments

# 在 _process 中调用
func _process(delta):
    animate_fragments()
```

### 4.2 碎片动画优化

```gdscript
# 碎片动画性能优化
func optimize_fragment_animation(fragments: ParticleSystem3D):
    # 减少发射率（如果性能不足）
    if fragments.emission_rate > 30:
        fragments.emission_rate = 30
    
    # 减少粒子寿命（如果性能不足）
    if fragments.lifetime > 4:
        fragments.lifetime = 4
    
    # 减少粒子数量（如果性能不足）
    if fragments.shape.radius > 0.15:
        fragments.shape.radius = 0.15
    
    # 调整粒子颜色（降低亮度）
    if fragments.material:
        fragments.material.color = fragments.material.color * 0.7

# 在游戏开始时调用
func _ready():
    var fragment_animations = get_tree().get_nodes_in_group("fragment_animation")
    for animation in fragment_animations:
        optimize_fragment_animation(animation)
```

### 4.3 碎片动画混合

```gdscript
# 创建碎片动画混合
func create_fragment_animation_mixing():
    # 创建粒子系统
    var fragments = ParticleSystem3D.new()
    
    # 设置碎片参数
    fragments.emission_rate = 50  # 每秒发射 50 个碎片
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.gravity = Vector3(0, -9.8, 0)  # 重力
    
    # 设置碎片外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    fragments.material = material
    
    # 设置碎片形状
    fragments.shape = ParticleShape3D.new()
    fragments.shape.shape = ParticleShape3D.SHAPES_CUBE
    fragments.shape.radius = 0.2  # 碎片半径
    
    # 设置粒子速度（碎片向不同方向飞散）
    fragments.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    fragments.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    fragments.velocity_overLifetime.add_point(0.5, Vector3(10, 15, 10))
    fragments.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
    # 添加到场景
    add_child(fragments)
    
    # 创建动画混合器
    var animation_mixer = AnimationMixer.new()
    add_child(animation_mixer)
    
    # 创建动画状态
    var animation = AnimationState.new()
    animation_mixer.add_state("fragment_animation", animation)
    
    # 添加动画曲线
    var curve = Curve2D.new()
    curve.add_point(0, Vector3(0, 0, 0))
    curve.add_point(1, Vector3(0, 0.2, 0))
    curve.add_point(2, Vector3(0, 0, 0))
    curve.add_point(3, Vector3(0, -0.2, 0))
    curve.add_point(4, Vector3(0, 0, 0))
    
    # 添加动画节点
    var node = AnimationNodeCurve.new()
    node.curve = curve
    animation.add_track(AnimationNodeCurve.TRACK_POSITION, node)
    
    # 设置动画混合权重
    func animate_mixing():
        # 在每帧更新时调用
        animation_mixer["fragment_animation"].track(0).value = sin(Time.get_ticks_msec() * 0.002) * 0.5  # 0-0.5 之间变化
    
    # 添加到场景
    add_child(fragments)
    
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
        explosion.emission_rate = 1000  # 更小的爆炸
        explosion.lifetime = 1.5  # 更短的寿命
        add_child(explosion)
        
        # 创建小型碎片动画
        var fragments = create_fragment_animation()
        fragments.position = body.global_transform.origin
        fragments.emission_rate = 30  # 更小的碎片
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
# 创建碎片动画混合
func create_fragment_animation_mixing():
    # 创建粒子系统
    var fragments = ParticleSystem3D.new()
    
    # 设置碎片参数
    fragments.emission_rate = 50  # 每秒发射 50 个碎片
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.gravity = Vector3(0, -9.8, 0)  # 重力
    
    # 设置碎片外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    fragments.material = material
    
    # 设置碎片形状
    fragments.shape = ParticleShape3D.new()
    fragments.shape.shape = ParticleShape3D.SHAPES_CUBE
    fragments.shape.radius = 0.2  # 碎片半径
    
    # 设置粒子速度（碎片向不同方向飞散）
    fragments.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    fragments.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    fragments.velocity_overLifetime.add_point(0.5, Vector3(10, 15, 10))
    fragments.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
    # 添加到场景
    add_child(fragments)
    
    # 创建动画混合器
    var animation_mixer = AnimationMixer.new()
    add_child(animation_mixer)
    
    # 创建动画状态
    var animation = AnimationState.new()
    animation_mixer.add_state("fragment_animation", animation)
    
    # 添加动画曲线
    var curve = Curve2D.new()
    curve.add_point(0, Vector3(0, 0, 0))
    curve.add_point(1, Vector3(0, 0.2, 0))
    curve.add_point(2, Vector3(0, 0, 0))
    curve.add_point(3, Vector3(0, -0.2, 0))
    curve.add_point(4, Vector3(0, 0, 0))
    
    # 添加动画节点
    var node = AnimationNodeCurve.new()
    node.curve = curve
    animation.add_track(AnimationNodeCurve.TRACK_POSITION, node)
    
    # 设置动画混合权重
    func animate_mixing():
        # 在每帧更新时调用
        animation_mixer["fragment_animation"].track(0).value = sin(Time.get_ticks_msec() * 0.002) * 0.5  # 0-0.5 之间变化
    
    # 添加到场景
    add_child(fragments)
    
    return fragments

# 在 _process 中调用
func _process(delta):
    animate_mixing()
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
# 创建碎片动画混合
func create_fragment_animation_mixing():
    # 创建粒子系统
    var fragments = ParticleSystem3D.new()
    
    # 设置碎片参数
    fragments.emission_rate = 50  # 每秒发射 50 个碎片
    fragments.lifetime = 5.0  # 碎片寿命 5 秒
    fragments.gravity = Vector3(0, -9.8, 0)  # 重力
    
    # 设置碎片外观
    var material = ParticleTextureMaterial.new()
    material.color = Color(0.8, 0.8, 0.8, 0.6)  # 灰色半透明
    fragments.material = material
    
    # 设置碎片形状
    fragments.shape = ParticleShape3D.new()
    fragments.shape.shape = ParticleShape3D.SHAPES_CUBE
    fragments.shape.radius = 0.2  # 碎片半径
    
    # 设置粒子速度（碎片向不同方向飞散）
    fragments.velocity_overLifetime = LinearInterpolatedCurve2D.new()
    fragments.velocity_overLifetime.add_point(0, Vector3(0, 0, 0))
    fragments.velocity_overLifetime.add_point(0.5, Vector3(10, 15, 10))
    fragments.velocity_overLifetime.add_point(1, Vector3(0, 0, 0))
    
    # 添加到场景
    add_child(fragments)
    
    # 创建动画混合器
    var animation_mixer = AnimationMixer.new()
    add_child(animation_mixer)
    
    # 创建动画状态
    var animation = AnimationState.new()
    animation_mixer.add_state("fragment_animation", animation)
    
    # 添加动画曲线
    var curve = Curve2D.new()
    curve.add_point(0, Vector3(0, 0, 0))
    curve.add_point(1, Vector3(0, 0.2, 0))
    curve.add_point(2, Vector3(0, 0, 0))
    curve.add_point(3, Vector3(0, -0.2, 0))
    curve.add_point(4, Vector3(0, 0, 0))
    
    # 添加动画节点
    var node = AnimationNodeCurve.new()
    node.curve = curve
    animation.add_track(AnimationNodeCurve.TRACK_POSITION, node)
    
    # 设置动画混合权重
    func animate_mixing():
        # 在每帧更新时调用
        animation_mixer["fragment_animation"].track(0).value = sin(Time.get_ticks_msec() * 0.002) * 0.5  # 0-0.5 之间变化
    
    # 添加到场景
    add_child(fragments)
    
    return fragments

# 在 _process 中调用
func _process(delta):
    animate_mixing()
```

---

## 📝 本章总结

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
*字数：约 9,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*