# 第 19 篇：流体模拟

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 28 章 车辆物理  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

流体模拟是游戏物理中最具挑战性的领域之一，涉及液体行为、流体动力学、粒子系统等多个复杂方面。从简单的游泳池到复杂的海洋波浪，从雨滴到瀑布，流体模拟能够为游戏带来生动的视觉效果。

Godot 提供了多种流体模拟方法，包括基于粒子的流体模拟、基于网格的流体模拟、以及使用着色器的水面模拟。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解流体物理的基本原理
- 掌握基于粒子的流体模拟
- 学会创建水面和波浪效果
- 熟悉流体动力学基础
- 优化流体模拟性能

---

## 1. 流体物理基础

### 1.1 流体特性

```
流体基本特性:
┌─────────────────────────────────────────────────────────────┐
│                      流体特性                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 流动性：流体可以流动和变形                              │
│  2. 不可压缩性：液体体积基本不变                            │
│  3. 黏性：流体内部的摩擦力                                  │
│  4. 表面张力：液体表面的收缩力                              │
│  5. 浮力：物体在流体中受到的向上力                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 流体模拟方法对比

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 粒子系统 | 简单、性能好 | 不够真实 | 小雨、喷泉 |
| SPH（平滑粒子流体动力学） | 真实、灵活 | 计算量大 | 小规模液体 |
| 网格流体 | 稳定、高效 | 实现复杂 | 大规模水体 |
| 着色器模拟 | 性能极好 | 仅视觉效果 | 海洋、湖泊 |
| 物理刚体模拟 | 精确交互 | 性能最差 | 少量液体 |

---

## 2. 基于粒子的流体模拟

### 2.1 基础粒子流体

```gdscript
# 基础流体粒子
class_name FluidParticle

extends RigidBody3D

@export var particle_size: float = 0.1
@export var viscosity: float = 0.5
@export var surface_tension: float = 0.3

var neighbors = []
var pressure = 0.0
var density = 0.0

func _ready():
    mass = particle_size * 1000  # 基于体积的质量
    linear_damp = viscosity
    angular_damp = viscosity
    
    # 设置碰撞层
    collision_layer = 32  # 流体层
    collision_mask = 16 | 32  # 地面 + 流体

func update_neighbors(all_particles: Array):
    neighbors.clear()
    for particle in all_particles:
        if particle != self:
            var distance = global_transform.origin.distance_to(particle.global_transform.origin)
            if distance < particle_size * 3:
                neighbors.append(particle)

func apply_fluid_forces(delta: float):
    # 计算密度
    density = 0.0
    for neighbor in neighbors:
        var distance = global_transform.origin.distance_to(neighbor.global_transform.origin)
        density += (particle_size * 3 - distance)
    
    # 计算压力
    pressure = (density - 1000) * 10  # 简化压力公式
    
    # 应用压力力
    for neighbor in neighbors:
        var direction = (global_transform.origin - neighbor.global_transform.origin).normalized()
        var force = direction * pressure * delta
        apply_central_force(force)
    
    # 应用表面张力
    if neighbors.size() > 0:
        var center = Vector3.ZERO
        for neighbor in neighbors:
            center += neighbor.global_transform.origin
        center /= neighbors.size()
        
        var surface_force = (center - global_transform.origin).normalized() * surface_tension
        apply_central_force(surface_force)
```

### 2.2 流体发射器

```gdscript
# 流体发射器
class_name FluidEmitter

extends Node3D

@export var particle_scene: PackedScene
@export var emit_rate: int = 10  # 每秒粒子数
@export var initial_velocity: Vector3 = Vector3.DOWN
@export var max_particles: int = 1000

var particles = []
var emit_timer = 0.0

func _physics_process(delta):
    emit_timer += delta
    
    # 发射新粒子
    if emit_timer >= 1.0 / emit_rate and particles.size() < max_particles:
        emit_particle()
        emit_timer = 0.0
    
    # 更新所有粒子
    update_fluid(delta)

func emit_particle():
    if particle_scene:
        var particle = particle_scene.instantiate()
        particle.global_transform.origin = global_transform.origin
        particle.linear_velocity = initial_velocity
        get_tree().current_scene.add_child(particle)
        particles.append(particle)

func update_fluid(delta: float):
    # 更新邻居关系
    for particle in particles:
        particle.update_neighbors(particles)
    
    # 应用流体力
    for particle in particles:
        particle.apply_fluid_forces(delta)
    
    # 移除掉落的粒子
    for i in range(particles.size() - 1, -1, -1):
        if particles[i].global_transform.origin.y < -10:
            particles[i].queue_free()
            particles.remove_at(i)
```

### 2.3 流体容器

```gdscript
# 流体容器
class_name FluidContainer

extends Node3D

@export var container_size: Vector3 = Vector3(2, 1, 2)
@export var fluid_height: float = 0.5

var fluid_particles = []

func _ready():
    create_container()
    fill_fluid()

func create_container():
    # 创建容器壁
    var walls = [
        {"size": Vector3(container_size.x, container_size.y, 0.1), "pos": Vector3(0, container_size.y/2, container_size.z/2)},
        {"size": Vector3(container_size.x, container_size.y, 0.1), "pos": Vector3(0, container_size.y/2, -container_size.z/2)},
        {"size": Vector3(0.1, container_size.y, container_size.z), "pos": Vector3(container_size.x/2, container_size.y/2, 0)},
        {"size": Vector3(0.1, container_size.y, container_size.z), "pos": Vector3(-container_size.x/2, container_size.y/2, 0)},
        {"size": Vector3(container_size.x, 0.1, container_size.z), "pos": Vector3(0, 0, 0)}
    ]
    
    for wall_data in walls:
        var wall = StaticBody3D.new()
        wall.global_transform.origin = global_transform.origin + wall_data.pos
        
        var collision = CollisionShape3D.new()
        collision.shape = BoxShape3D.new()
        collision.shape.size = wall_data.size
        wall.add_child(collision)
        
        var mesh = MeshInstance3D.new()
        mesh.mesh = BoxMesh.new()
        mesh.mesh.size = wall_data.size
        wall.add_child(mesh)
        
        add_child(wall)

func fill_fluid():
    var particle_count = int(container_size.x * container_size.z * fluid_height * 100)
    var spacing = 0.1
    
    for i in range(particle_count):
        var x = randf_range(-container_size.x/2 + spacing, container_size.x/2 - spacing)
        var z = randf_range(-container_size.z/2 + spacing, container_size.z/2 - spacing)
        var y = randf_range(0, fluid_height)
        
        var particle = FluidParticle.new()
        particle.global_transform.origin = global_transform.origin + Vector3(x, y, z)
        add_child(particle)
        fluid_particles.append(particle)
```

---

## 3. 水面模拟

### 3.1 基础水面

```gdscript
# 基础水面
class_name WaterSurface

extends MeshInstance3D

@export var size: Vector2 = Vector2(100, 100)
@export var segments: int = 50
@export var wave_height: float = 0.5
@export var wave_speed: float = 2.0
@export var wave_frequency: float = 1.0

var mesh_data: ArrayMesh
var vertices: PackedVector3Array
var time = 0.0

func _ready():
    create_water_mesh()
    mesh = mesh_data

func create_water_mesh():
    mesh_data = ArrayMesh.new()
    vertices = PackedVector3Array()
    
    var step_x = size.x / segments
    var step_z = size.y / segments
    
    # 生成顶点
    for i in range(segments + 1):
        for j in range(segments + 1):
            var x = -size.x / 2 + i * step_x
            var z = -size.y / 2 + j * step_z
            vertices.append(Vector3(x, 0, z))
    
    # 生成索引
    var indices = PackedInt32Array()
    for i in range(segments):
        for j in range(segments):
            var i1 = i * (segments + 1) + j
            var i2 = i1 + 1
            var i3 = i1 + segments + 1
            var i4 = i3 + 1
            
            indices.append(i1)
            indices.append(i3)
            indices.append(i2)
            indices.append(i2)
            indices.append(i3)
            indices.append(i4)
    
    var arrays = []
    arrays.resize(ArrayMesh.ARRAY_MAX)
    arrays[ArrayMesh.ARRAY_VERTEX] = vertices
    arrays[ArrayMesh.ARRAY_INDEX] = indices
    
    mesh_data.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)

func _process(delta):
    time += delta * wave_speed
    update_waves()

func update_waves():
    var updated_vertices = PackedVector3Array()
    
    for i in range(vertices.size()):
        var vertex = vertices[i]
        var x = vertex.x
        var z = vertex.z
        
        # 叠加多个波
        var height = 0.0
        height += sin(x * wave_frequency + time) * wave_height
        height += sin(z * wave_frequency + time * 0.8) * wave_height * 0.5
        height += sin((x + z) * wave_frequency * 0.5 + time * 1.2) * wave_height * 0.3
        
        updated_vertices.append(Vector3(x, height, z))
    
    mesh_data.surface_set_arrays(0, [updated_vertices])
```

### 3.2 浮力系统

```gdscript
# 浮力系统
class_name BuoyancySystem

extends Node3D

@export var water_level: float = 0.0
@export var fluid_density: float = 1000.0  # kg/m³
@export var gravity: float = 9.81

func apply_buoyancy(body: RigidBody3D, delta: float):
    # 计算物体在水下的体积
    var submerged_volume = calculate_submerged_volume(body)
    
    if submerged_volume > 0:
        # 阿基米德原理：浮力 = 排开液体的重量
        var buoyancy_force = Vector3.UP * fluid_density * submerged_volume * gravity
        
        # 应用浮力到物体中心
        body.apply_central_force(buoyancy_force)
        
        # 应用阻尼（水的阻力）
        body.linear_damp = 0.5
        body.angular_damp = 0.3

func calculate_submerged_volume(body: RigidBody3D) -> float:
    # 简化：基于物体位置计算 submerged 体积
    var body_height = body.global_transform.origin.y
    var body_size = get_body_size(body)
    
    if body_height < water_level:
        var submerged_depth = min(water_level - body_height, body_size.y)
        return body_size.x * body_size.z * submerged_depth
    
    return 0.0

func get_body_size(body: RigidBody3D) -> Vector3:
    # 获取物体的包围盒大小
    var aabb = body.get_global_aabb()
    return aabb.size
```

### 3.3 波浪交互

```gdscript
# 波浪交互
class_name WaveInteraction

extends Node3D

@export var wave_amplitude: float = 0.5
@export var wave_wavelength: float = 5.0
@export var wave_speed: float = 2.0

func get_wave_height(position: Vector3, time: float) -> float:
    var height = 0.0
    
    # 主波
    height += sin(position.x / wave_wavelength * PI * 2 + time * wave_speed) * wave_amplitude
    
    # 次要波
    height += sin(position.z / (wave_wavelength * 0.7) * PI * 2 + time * wave_speed * 1.1) * wave_amplitude * 0.5
    
    # 随机波
    height += sin((position.x + position.z) / (wave_wavelength * 1.5) * PI * 2 + time * wave_speed * 0.8) * wave_amplitude * 0.3
    
    return height

func get_wave_normal(position: Vector3, time: float) -> Vector3:
    var epsilon = 0.1
    var height_center = get_wave_height(position, time)
    var height_x = get_wave_height(position + Vector3(epsilon, 0, 0), time)
    var height_z = get_wave_height(position + Vector3(0, 0, epsilon), time)
    
    var tangent = Vector3(1, 0, (height_x - height_center) / epsilon)
    var bitangent = Vector3(0, 1, (height_z - height_center) / epsilon)
    
    return tangent.cross(bitangent).normalized()
```

---

## 4. 流体动力学

### 4.1 Navier-Stokes 方程简化

```gdscript
# 简化的流体动力学
class_name SimplifiedFluidDynamics

@export var viscosity: float = 0.001  # 黏度
@export var density: float = 1000.0  # 密度
@export var gravity: Vector3 = Vector3(0, -9.81, 0)

func calculate_pressure(velocity: Vector3, position: Vector3) -> float:
    # 简化伯努利方程
    var dynamic_pressure = 0.5 * density * velocity.length_squared()
    var hydrostatic_pressure = density * gravity.dot(position)
    return dynamic_pressure + hydrostatic_pressure

func calculate_viscous_force(velocity_gradient: Vector3) -> Vector3:
    # 黏性力 = 黏度 × 速度梯度
    return viscosity * velocity_gradient

func update_velocity(velocity: Vector3, pressure_gradient: Vector3, delta: float) -> Vector3:
    # 动量方程简化
    var acceleration = gravity - pressure_gradient / density
    return velocity + acceleration * delta
```

### 4.2 流体网格

```gdscript
# 流体网格模拟
class_name FluidGrid

extends Node3D

@export var grid_size: Vector3i = Vector3i(50, 20, 50)
@export var cell_size: float = 0.1
@export var time_step: float = 0.01

var velocity_grid: Array
var pressure_grid: Array
var density_grid: Array

func _ready():
    initialize_grids()

func initialize_grids():
    var total_cells = grid_size.x * grid_size.y * grid_size.z
    
    velocity_grid = []
    pressure_grid = []
    density_grid = []
    
    for i in range(total_cells):
        velocity_grid.append(Vector3.ZERO)
        pressure_grid.append(0.0)
        density_grid.append(0.0)

func get_cell_index(pos: Vector3i) -> int:
    if pos.x < 0 or pos.x >= grid_size.x or \
       pos.y < 0 or pos.y >= grid_size.y or \
       pos.z < 0 or pos.z >= grid_size.z:
        return -1
    return pos.x + pos.y * grid_size.x + pos.z * grid_size.x * grid_size.y

func simulate_step(delta: float):
    # 1. 应用外力
    apply_external_forces()
    
    # 2. 计算对流
    advect_velocity(delta)
    
    # 3. 计算压力
    solve_pressure()
    
    # 4. 应用压力梯度
    apply_pressure_gradient()
    
    # 5. 更新密度
    update_density()

func apply_external_forces():
    # 重力和其他外力
    for i in range(velocity_grid.size()):
        velocity_grid[i] += gravity * time_step
```

---

## 5. 粒子系统流体

### 5.1 GPUParticles3D 流体

```gdscript
# GPU 粒子流体
class_name GPUParticleFluid

extends GPUParticles3D

@export var particle_count: int = 1000
@export var lifetime: float = 5.0
@export var initial_velocity: Vector3 = Vector3.DOWN

func _ready():
    setup_particles()

func setup_particles():
    amount = particle_count
    lifetime = lifetime
    emitting = true
    
    # 设置初始速度
    initial_velocity_min = initial_velocity
    initial_velocity_max = initial_velocity
    
    # 设置重力
    gravity = Vector3(0, -9.81, 0)
    
    # 设置碰撞
    collision_mode = GPUParticles3D.COLLISION_HIDE_ON_CONTACT
```

### 5.2 粒子碰撞

```gdscript
# 粒子碰撞处理
class_name ParticleCollision

extends Node3D

@export var bounce_factor: float = 0.5
@export var friction_factor: float = 0.8

func handle_collision(particle: RigidBody3D, collider: Node3D):
    # 反弹
    var normal = get_collision_normal(particle, collider)
    var velocity = particle.linear_velocity
    
    # 反射速度
    var reflected = velocity - 2 * velocity.dot(normal) * normal
    particle.linear_velocity = reflected * bounce_factor
    
    # 摩擦力
    particle.linear_velocity *= friction_factor

func get_collision_normal(particle: RigidBody3D, collider: Node3D) -> Vector3:
    # 获取碰撞法线
    if collider is StaticBody3D:
        return (particle.global_transform.origin - collider.global_transform.origin).normalized()
    return Vector3.UP
```

---

## 6. 性能优化

### 6.1 空间划分

```gdscript
# 空间网格划分
class_name SpatialHashGrid

@export var cell_size: float = 1.0

var grid = {}

func clear():
    grid.clear()

func insert(position: Vector3, object):
    var cell = get_cell(position)
    if not grid.has(cell):
        grid[cell] = []
    grid[cell].append(object)

func get_cell(position: Vector3) -> Vector3i:
    return Vector3i(
        floor(position.x / cell_size),
        floor(position.y / cell_size),
        floor(position.z / cell_size)
    )

func query_range(position: Vector3, radius: float) -> Array:
    var results = []
    var min_cell = get_cell(position - Vector3(radius, radius, radius))
    var max_cell = get_cell(position + Vector3(radius, radius, radius))
    
    for x in range(min_cell.x, max_cell.x + 1):
        for y in range(min_cell.y, max_cell.y + 1):
            for z in range(min_cell.z, max_cell.z + 1):
                var cell = Vector3i(x, y, z)
                if grid.has(cell):
                    results.append_array(grid[cell])
    
    return results
```

### 6.2 LOD 系统

```gdscript
# 流体 LOD 系统
class_name FluidLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_particle_counts: Array = [1000, 500, 100]

func update_lod(camera_position: Vector3, emitter: FluidEmitter):
    var distance = camera_position.distance_to(emitter.global_transform.origin)
    
    if distance < lod_distances[0]:
        emitter.emit_rate = lod_particle_counts[0]
    elif distance < lod_distances[1]:
        emitter.emit_rate = lod_particle_counts[1]
    else:
        emitter.emit_rate = lod_particle_counts[2]
```

### 6.3 时间步长优化

```gdscript
# 自适应时间步长
class_name AdaptiveTimeStep

@export var max_time_step: float = 0.01
@export var min_time_step: float = 0.001
@export var target_fps: float = 60.0

func calculate_time_step(delta: float) -> float:
    var target_step = 1.0 / target_fps
    return clamp(delta, min_time_step, max_time_step)

func simulate_with_adaptive_step(fluid: FluidGrid, delta: float):
    var time_step = calculate_time_step(delta)
    var accumulated_time = 0.0
    
    while accumulated_time < delta:
        fluid.simulate_step(time_step)
        accumulated_time += time_step
```

---

## 7. 实践：水体效果

### 7.1 游泳池

```gdscript
# 创建游泳池
func create_swimming_pool():
    var pool_size = Vector3(10, 2, 5)
    
    # 池底
    var bottom = StaticBody3D.new()
    var bottom_collision = CollisionShape3D.new()
    bottom_collision.shape = BoxShape3D.new()
    bottom_collision.shape.size = Vector3(pool_size.x, 0.5, pool_size.z)
    bottom.add_child(bottom_collision)
    
    # 池壁
    var walls = [
        {"size": Vector3(pool_size.x, 2, 0.5), "pos": Vector3(0, 1, pool_size.z/2)},
        {"size": Vector3(pool_size.x, 2, 0.5), "pos": Vector3(0, 1, -pool_size.z/2)},
        {"size": Vector3(0.5, 2, pool_size.z), "pos": Vector3(pool_size.x/2, 1, 0)},
        {"size": Vector3(0.5, 2, pool_size.z), "pos": Vector3(-pool_size.x/2, 1, 0)}
    ]
    
    for wall_data in walls:
        var wall = StaticBody3D.new()
        wall.position = wall_data.pos
        var wall_collision = CollisionShape3D.new()
        wall_collision.shape = BoxShape3D.new()
        wall_collision.shape.size = wall_data.size
        wall.add_child(wall_collision)
        bottom.add_child(wall)
    
    # 水面
    var water = WaterSurface.new()
    water.size = Vector2(pool_size.x, pool_size.z)
    water.position = Vector3(0, 1.5, 0)
    bottom.add_child(water)
    
    # 浮力系统
    var buoyancy = BuoyancySystem.new()
    buoyancy.water_level = 1.5
    bottom.add_child(buoyancy)
    
    return bottom
```

### 7.2 喷泉

```gdscript
# 创建喷泉
func create_fountain():
    var fountain = Node3D.new()
    
    # 基座
    var base = StaticBody3D.new()
    var base_collision = CollisionShape3D.new()
    base_collision.shape = CylinderShape3D.new()
    base_collision.shape.radius = 2
    base_collision.shape.height = 0.5
    base.add_child(base_collision)
    fountain.add_child(base)
    
    # 发射器
    var emitter = FluidEmitter.new()
    emitter.position = Vector3(0, 0.5, 0)
    emitter.emit_rate = 50
    emitter.initial_velocity = Vector3(0, 10, 0)
    emitter.max_particles = 500
    fountain.add_child(emitter)
    
    # 水池
    var pool = create_swimming_pool()
    pool.position = Vector3(0, -0.5, 0)
    fountain.add_child(pool)
    
    return fountain
```

### 7.3 河流

```gdscript
# 创建河流
func create_river(length: float, width: float):
    var river = Node3D.new()
    
    # 河床
    var riverbed = StaticBody3D.new()
    var riverbed_collision = CollisionShape3D.new()
    riverbed_collision.shape = BoxShape3D.new()
    riverbed_collision.shape.size = Vector3(width, 1, length)
    riverbed.add_child(riverbed_collision)
    river.add_child(riverbed)
    
    # 水流
    var water = WaterSurface.new()
    water.size = Vector2(width, length)
    water.wave_speed = 3.0
    water.wave_height = 0.2
    river.add_child(water)
    
    # 水流力
    var current = Node3D.new()
    river.add_child(current)
    
    return river
```

---

## 📝 本章总结

### 核心要点

1. **流体模拟有多种方法**，粒子、网格、着色器各有优劣
2. **SPH 方法适合小规模真实流体**，计算量大
3. **水面模拟使用着色器**，性能好效果佳
4. **浮力基于阿基米德原理**，排开液体重量
5. **性能优化关键**：空间划分、LOD、时间步长

### 关键术语

| 术语 | 解释 |
|------|------|
| SPH | 平滑粒子流体动力学 |
| Navier-Stokes | 流体动力学基本方程 |
| Buoyancy | 浮力，物体在流体中受到的向上力 |
| Viscosity | 黏度，流体内部摩擦力 |
| Surface Tension | 表面张力，液体表面收缩力 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Particles](https://docs.godotengine.org/en/stable/tutorials/particles/particles.html)
- **源码位置**: `servers/rendering/renderer_rd/storage_rd/particles.cpp`
- **技术博客**: [Godot Fluid Simulation](https://godotengine.org/article/fluid-simulation/)

---

## 📋 下一章预告

**第 30 篇：布料模拟**

- 布料物理基础
- 质点弹簧系统
- 碰撞检测
- 风力影响
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 8,500 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*

---

## 8. 流体粘度控制（新增）

### 8.1 粘度物理基础

粘度（Viscosity）是流体内部摩擦力的度量，决定了流体的"粘稠"程度。

```
常见流体的粘度对比:
┌─────────────────────────────────────────────────────────────┐
│ 流体            │ 粘度 (Pa·s)    │ 相对粘度 │ 特性         │
├─────────────────────────────────────────────────────────────┤
│ 空气            │ 0.000018       │ 0.00002    │ 极低         │
│ 水 (20°C)       │ 0.001          │ 1          │ 低           │
│ 血液            │ 0.004          │ 4          │ 低 - 中       │
│ 橄榄油          │ 0.08           │ 80         │ 中           │
│ 蜂蜜            │ 10             │ 10,000     │ 高           │
│ 糖浆            │ 25             │ 25,000     │ 很高         │
│ 沥青            │ 100000+        │ 100,000,000+ | 极高（似固体）│
└─────────────────────────────────────────────────────────────┘

粘度类型:
- 动力粘度（Dynamic Viscosity）: μ，单位 Pa·s
- 运动粘度（Kinematic Viscosity）: ν = μ/ρ，单位 m²/s
- 相对粘度：相对于水的粘度比值
```

```gdscript
# 粘度配置预设
class_name FluidViscosityPresets

# 水（低粘度）
static func water() -> Dictionary:
    return {
        "density": 1000.0,  # kg/m³
        "dynamic_viscosity": 0.001,  # Pa·s
        "kinematic_viscosity": 0.000001,  # m²/s
        "flow_speed": 1.0,
        "damping": 0.05
    }

# 蜂蜜（高粘度）
static func honey() -> Dictionary:
    return {
        "density": 1420.0,
        "dynamic_viscosity": 10.0,
        "kinematic_viscosity": 0.007,
        "flow_speed": 0.1,
        "damping": 0.5
    }

# 岩浆（极高粘度）
static func lava() -> Dictionary:
    return {
        "density": 3100.0,
        "dynamic_viscosity": 1000.0,
        "kinematic_viscosity": 0.32,
        "flow_speed": 0.01,
        "damping": 0.9
    }

# 自定义粘度
static func custom(density: float, viscosity: float) -> Dictionary:
    return {
        "density": density,
        "dynamic_viscosity": viscosity,
        "kinematic_viscosity": viscosity / density,
        "flow_speed": 1.0 / (viscosity + 0.001),
        "damping": clamp(viscosity / 10.0, 0.01, 0.99)
    }
```

### 8.2 SPH 中的粘度实现

```gdscript
# SPH 粘度力计算
class_name SPHViscosity

extends Node

@export var viscosity_coefficient: float = 0.001  # 动力粘度
@export var rest_density: float = 1000.0  # 静止密度
@export var smoothing_length: float = 0.5  # 平滑长度

# 计算粘度力（简化版）
func calculate_viscosity_force(particle_i: Dictionary, neighbors: Array) -> Vector3:
    var viscosity_force = Vector3.ZERO
    
    for neighbor in neighbors:
        if neighbor == particle_i:
            continue
        
        var r = particle_i.position - neighbor.position
        var distance = r.length()
        
        if distance < smoothing_length and distance > 0.001:
            # 粘度力公式（基于 Navier-Stokes）
            # F_viscosity = μ * ∇²v
            var direction = r.normalized()
            
            # 简化粘度力（与速度差成正比）
            var velocity_diff = particle_i.velocity - neighbor.velocity
            var viscosity_contrib = viscosity_coefficient * velocity_diff
            
            # 应用平滑核函数
            var kernel = viscosity_kernel(distance)
            viscosity_force += viscosity_contrib * kernel
    
    return viscosity_force

# 粘度核函数
func viscosity_kernel(distance: float) -> float:
    var h = smoothing_length
    var q = distance / h
    
    if q < 1.0:
        # 三次样条核函数
        return (2.0/3.0) - q*q + 0.5*q*q*q
    elif q < 2.0:
        return 0.5 * (2.0 - q)*(2.0 - q)*(2.0 - q) / 6.0
    else:
        return 0.0

# 雷诺数计算（判断层流/湍流）
func calculate_reynolds_number(velocity: float, characteristic_length: float, 
                                density: float, viscosity: float) -> float:
    # Re = ρvL/μ
    return (density * velocity * characteristic_length) / viscosity

# 判断流动状态
func get_flow_state(reynolds_number: float) -> String:
    if reynolds_number < 2000:
        return "laminar"  # 层流
    elif reynolds_number < 4000:
        return "transitional"  # 过渡流
    else:
        return "turbulent"  # 湍流
```

### 8.3 粘度对流体行为的影响

```gdscript
# 粘度影响控制器
class_name ViscosityEffectController

extends Node

@export var current_viscosity: float = 0.001  # 默认水
@export var temperature: float = 20.0  # 摄氏度

# 温度对粘度的影响（Andrade 方程简化版）
func viscosity_at_temperature(temp: float, base_viscosity: float, 
                               reference_temp: float = 20.0) -> float:
    # 简化：温度每升高 10°C，粘度降低约 20%
    var temp_diff = temp - reference_temp
    var factor = pow(0.8, temp_diff / 10.0)
    return base_viscosity * factor

# 设置流体类型
func set_fluid_type(type: String):
    match type:
        "water":
            current_viscosity = 0.001
            _apply_viscosity()
        "oil":
            current_viscosity = 0.08
            _apply_viscosity()
        "honey":
            current_viscosity = 10.0
            _apply_viscosity()
        "lava":
            current_viscosity = 1000.0
            _apply_viscosity()

func _apply_viscosity():
    # 应用到流体粒子
    var particles = get_tree().get_nodes_in_group("fluid_particles")
    for particle in particles:
        if particle.has_method("set_viscosity"):
            particle.set_viscosity(current_viscosity)
        
        # 调整阻尼
        if particle is RigidBody3D:
            particle.linear_damp = current_viscosity * 10.0

# 粘度渐变
func lerp_viscosity(target_viscosity: float, duration: float):
    var tween = create_tween()
    tween.tween_property(self, "current_viscosity", target_viscosity, duration)

# 示例：水变蜂蜜效果
func water_to_honey_transition():
    lerp_viscosity(10.0, 5.0)  # 5 秒内从水变成蜂蜜
    print("Viscosity increasing...")
```

### 8.4 密度变化模拟

```gdscript
# 密度分层效果（不同密度的流体分层）
class_name FluidDensityStratification

extends Node

@export var layers: Array[Dictionary] = [
    {"density": 1000.0, "color": Color.BLUE, "height": 1.0},   # 水
    {"density": 1030.0, "color": Color.DARK_BLUE, "height": 0.5}, # 盐水
    {"density": 1200.0, "color": Color.PURPLE, "height": 0.5}    # 糖浆
]

func _ready():
    _create_density_layers()

func _create_density_layers():
    var current_height = 0.0
    
    for layer in layers:
        _create_fluid_layer(layer, current_height)
        current_height += layer["height"]

func _create_fluid_layer(layer: Dictionary, height: float):
    # 创建粒子发射器
    var emitter = GPUParticles3D.new()
    var particles = ParticleProcessMaterial.new()
    
    # 设置粒子密度
    particles.custom_a_validators = [layer["density"]]
    
    # 设置颜色
    var colors = [layer["color"]]
    particles.color_curve = _create_color_curve(colors)
    
    # 设置浮力（密度大的下沉）
    particles.gravity = Vector3(0, -9.8 * (layer["density"] / 1000.0 - 1.0), 0)
    
    emitter.process_material = particles
    add_child(emitter)

# 物体在不同密度层中的浮力
func calculate_buoyancy(object_density: float, fluid_density: float, 
                        submerged_volume: float) -> float:
    # 阿基米德原理：F = ρ_fluid * g * V
    var gravity = 9.8
    return fluid_density * gravity * submerged_volume

# 检查物体是否漂浮
func is_floating(object_density: float, fluid_density: float) -> bool:
    return object_density < fluid_density
```

### 8.5 温度影响的粘度变化

```gdscript
# 温度 - 粘度关系
class_name TemperatureViscosityModel

@export var reference_viscosity: float = 0.001  # 参考温度下的粘度
@export var reference_temperature: float = 20.0  # 参考温度（°C）
@export var temperature_coefficient: float = -0.02  # 每°C 的变化率

# 计算任意温度下的粘度
func get_viscosity(temperature: float) -> float:
    # 简化线性模型
    var delta_t = temperature - reference_temperature
    var viscosity = reference_viscosity * (1.0 + temperature_coefficient * delta_t)
    return max(viscosity, 0.0001)  # 最小粘度

# 更精确的 Arrhenius 模型
func get_viscosity_arrhenius(temperature: float, activation_energy: float) -> float:
    # μ = A * exp(Ea/RT)
    var R = 8.314  # 气体常数
    var T = temperature + 273.15  # 转换为开尔文
    var A = reference_viscosity
    
    return A * exp(activation_energy / (R * T))

# 温度场中的流体
class_name ThermalFluidField

extends Node3D

@export var grid_size: Vector3i = Vector3i(20, 10, 20)
@export var cell_size: float = 0.5

var temperature_grid: Array = []
var viscosity_grid: Array = []

func _ready():
    _initialize_grids()

func _initialize_grids():
    # 初始化温度网格
    for x in range(grid_size.x):
        for y in range(grid_size.y):
            for z in range(grid_size.z):
                temperature_grid.append(20.0)  # 初始 20°C
                viscosity_grid.append(0.001)   # 初始水粘度

func update_temperature(x: int, y: int, z: int, temp: float):
    var index = x * grid_size.y * grid_size.z + y * grid_size.z + z
    temperature_grid[index] = temp
    
    # 更新粘度
    viscosity_grid[index] = get_viscosity(temp)

func get_local_viscosity(position: Vector3) -> float:
    var grid_pos = (position / cell_size).floor()
    
    if _is_in_bounds(grid_pos):
        var index = grid_pos.x * grid_size.y * grid_size.z + \
                    grid_pos.y * grid_size.z + grid_pos.z
        return viscosity_grid[index]
    
    return reference_viscosity

func _is_in_bounds(pos: Vector3i) -> bool:
    return pos.x >= 0 and pos.x < grid_size.x and \
           pos.y >= 0 and pos.y < grid_size.y and \
           pos.z >= 0 and pos.z < grid_size.z
```

### 8.6 非牛顿流体（可选扩展）

```gdscript
# 剪切增稠流体（如玉米淀粉 + 水）
class_name ShearThickeningFluid

extends Node

@export var base_viscosity: float = 0.5
@export var thickening_rate: float = 2.0

# 粘度随剪切速率增加
func get_viscosity(shear_rate: float) -> float:
    # μ = μ_0 * (1 + k * shear_rate)
    return base_viscosity * (1.0 + thickening_rate * shear_rate)

# 剪切稀化流体（如油漆、血液）
class_name ShearThinningFluid

extends Node

@export var base_viscosity: float = 1.0
@export var thinning_power: float = 0.5

# 粘度随剪切速率减小
func get_viscosity(shear_rate: float) -> float:
    # μ = μ_0 * shear_rate^(n-1)
    if shear_rate < 0.001:
        return base_viscosity
    return base_viscosity * pow(shear_rate, thinning_power - 1.0)

# 宾汉流体（如牙膏，需要屈服应力才能流动）
class_name BinghamFluid

extends Node

@export var yield_stress: float = 10.0  # 屈服应力
@export var plastic_viscosity: float = 0.5

func get_viscosity(shear_stress: float, shear_rate: float) -> float:
    if abs(shear_stress) < yield_stress:
        return INF  # 不流动（似固体）
    
    # μ = μ_p + τ_y / shear_rate
    return plastic_viscosity + yield_stress / max(shear_rate, 0.001)
```

---

## 📝 本章总结（更新）

### 核心要点（更新）

1. **流体模拟有多种方法**，粒子、网格、着色器各有优劣
2. **SPH 方法适合小规模真实流体**，计算量大
3. **水面模拟使用着色器**，性能好效果佳
4. **浮力基于阿基米德原理**，排开液体重量
5. **性能优化关键**：空间划分、LOD、时间步长
6. **粘度控制流体流动特性**，从水到蜂蜜（新增）
7. **温度影响粘度变化**，热胀冷缩（新增）
8. **密度分层实现多层流体**，油水分层（新增）

### 关键术语（更新）

| 术语 | 解释 |
|------|------|
| SPH | 平滑粒子流体动力学 |
| Navier-Stokes | 流体动力学基本方程 |
| Buoyancy | 浮力，物体在流体中受到的向上力 |
| Viscosity | 黏度，流体内部摩擦力 |
| Surface Tension | 表面张力，液体表面收缩力 |
| Dynamic Viscosity | 动力粘度，单位 Pa·s（新增） |
| Kinematic Viscosity | 运动粘度，单位 m²/s（新增） |
| Reynolds Number | 雷诺数，判断层流/湍流（新增） |
| Density Stratification | 密度分层，不同密度流体分层（新增） |
| Non-Newtonian | 非牛顿流体，粘度随剪切变化（新增） |