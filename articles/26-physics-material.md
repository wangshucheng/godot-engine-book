# 第 26 篇：物理材质

> **本卷定位**: 第三卷 物理系统（10 篇）  
> **前置知识**: 第 25 章 碰撞检测  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

物理材质（Physics Material）定义了物体表面的物理属性，包括摩擦力、弹性、吸收性等。合理的物理材质配置能让游戏世界更加真实，从光滑的冰面到粗糙的砂纸，从弹性十足的橡胶到坚硬的金属，物理材质影响着物体之间的交互效果。

本章将深入探讨物理材质属性、摩擦力和弹性计算、材质预设和混合规则、表面效果以及性能优化技巧。

---

## 🎯 学习目标

- 理解物理材质的核心属性
- 掌握摩擦力和弹性的配置
- 熟悉材质预设和混合规则
- 学会创建自定义表面效果
- 了解物理材质性能优化

---

## 1. 物理材质属性

### 1.1 PhysicsMaterial 基础

```gdscript
# 创建物理材质
var material = PhysicsMaterial.new()

# 核心属性
material.friction = 0.8        # 摩擦力 (0-1)，官方默认值是 1.0
material.bounce = 0.3          # 弹性/反弹 (0-1)
material.absorbent = false     # 吸收性：bool，语义是"相减对方的弹性而非相加"
material.rough = false         # false 时取双方较小的摩擦值

# 应用到刚体
var body = RigidBody3D.new()
body.physics_material_override = material
```

### 1.2 属性详解

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| friction | float (0-1) | **1.0** | 摩擦力，0=无摩擦，1=最大摩擦 |
| bounce | float (0-1) | 0.0 | 弹性，0=无弹性，1=完全弹性 |
| absorbent | **bool** | false | 为 true 时**相减**对方的弹性，而不是相加 |
| rough | bool | false | 为 true 时直接采用本方摩擦值，否则取双方较小值 |

> ⚠️ **`absorbent` 是布尔值，不是 0~1 的浮点**。官方文档原文：*"If true, subtracts the bounciness from the colliding object's bounciness instead of adding it."* 把它当浮点用（如 `absorbent = 0.8`）在 GDScript 4 里会直接报类型错误。

---

## 2. 摩擦力和弹性

### 2.1 摩擦力配置

```gdscript
# 不同表面的摩擦力预设
class_name FrictionPresets

static func create_ice() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.05  # 非常滑
    mat.bounce = 0.0
    return mat

static func create_wood() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.6
    mat.bounce = 0.1
    return mat

static func create_concrete() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.8
    mat.bounce = 0.1
    return mat

static func create_rubber() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.9  # 高摩擦
    mat.bounce = 0.5
    return mat

static func create_sandpaper() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 1.0  # 最大摩擦
    mat.bounce = 0.0
    return mat
```

### 2.2 弹性配置

```gdscript
# 不同材料的弹性预设
class_name BouncePresets

static func create_clay() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.5
    mat.bounce = 0.0  # 无弹性（黏土）
    return mat

static func create_tennis_ball() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.3
    mat.bounce = 0.7  # 高弹性
    return mat

static func create_basketball() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.4
    mat.bounce = 0.8  # 很高弹性
    return mat

static func create_super_ball() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.2
    mat.bounce = 0.95  # 接近完全弹性
    return mat
```

### 2.3 摩擦力和弹性计算

```
碰撞时的材质混合（依据 PhysicsMaterial.rough / absorbent 的官方语义）:
┌─────────────────────────────────────────────────────────────┐
│                      材质混合规则                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  摩擦力：由 rough 决定取哪一方的值                          │
│    双方都是 rough    → 取【较高】的摩擦                     │
│    只有一方 rough    → 取【那一方】的摩擦                   │
│    双方都不是 rough  → 取【较低】的摩擦                     │
│                                                             │
│  弹性：由 absorbent 决定相加还是相减                        │
│    absorbent = false（默认）→ bounce_a + bounce_b（相加）   │
│    absorbent = true         → bounce_a - bounce_b（相减）   │
│                                                             │
│  示例:                                                      │
│    橡胶 (friction=0.9, bounce=0.5)                          │
│      + 冰 (friction=0.05, bounce=0)                         │
│    摩擦：两边都不 rough → 取较小值 = 0.05                   │
│    弹性：两边都不 absorbent → 相加 = 0.5                    │
│                                                             │
│  ⚠️ 摩擦【不是取平均值】。官方原文：                        │
│     "use the lowest friction of all colliding objects"      │
│     （双方都 rough 时才取 highest）                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 材质预设库

### 3.1 完整材质预设

```gdscript
# 完整物理材质预设库
class_name PhysicsMaterialLibrary

# 自然材料
static func create_water() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.1
    mat.bounce = 0.0
    # absorbent 是 bool：置 true 表示"相减对方的弹性"
    mat.absorbent = true
    return mat

static func create_grass() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.7
    mat.bounce = 0.1
    return mat

static func create_dirt() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.6
    mat.bounce = 0.05
    return mat

static func create_snow() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.15
    mat.bounce = 0.1
    return mat

# 建筑材料
static func create_brick() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.7
    mat.bounce = 0.1
    return mat

static func create_glass() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.2
    mat.bounce = 0.3
    return mat

static func create_steel() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.4
    mat.bounce = 0.3
    return mat

# 人造材料
static func create_plastic() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.4
    mat.bounce = 0.4
    return mat

static func create_foam() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.5
    mat.bounce = 0.2
    mat.absorbent = true
    return mat

static func create_carpet() -> PhysicsMaterial:
    var mat = PhysicsMaterial.new()
    mat.friction = 0.8
    mat.bounce = 0.1
    mat.absorbent = true
    return mat
```

### 3.2 材质变体

```gdscript
# 材质变体生成器
class_name PhysicsMaterialVariants

static func create_rough_variant(base: PhysicsMaterial, roughness: float) -> PhysicsMaterial:
    var mat = base.duplicate()
    mat.friction = clamp(base.friction + roughness * 0.3, 0, 1)
    return mat

static func create_worn_variant(base: PhysicsMaterial, wear: float) -> PhysicsMaterial:
    var mat = base.duplicate()
    mat.friction = clamp(base.friction - wear * 0.2, 0, 1)
    mat.bounce = clamp(base.bounce + wear * 0.1, 0, 1)
    return mat

static func create_wet_variant(base: PhysicsMaterial) -> PhysicsMaterial:
    var mat = base.duplicate()
    mat.friction = mat.friction * 0.5  # 湿滑
    return mat
```

---

## 4. 材质混合规则

### 4.1 自定义混合规则

```gdscript
# 自定义材质混合
# ⚠️ 注意：absorbent 是 bool，不能参与加减乘除；
#    混合 bool 属性的语义是"任一方为 true 即为 true"（相减弹性）。
class_name CustomMaterialBlender

enum BlendMode {
    AVERAGE,      # 平均
    MINIMUM,      # 取最小
    MAXIMUM,      # 取最大
    MULTIPLY,     # 相乘
    WEIGHTED      # 加权
}

static func blend_materials(mat_a: PhysicsMaterial, mat_b: PhysicsMaterial, 
                           mode: BlendMode = BlendMode.AVERAGE) -> PhysicsMaterial:
    var result = PhysicsMaterial.new()
    
    match mode:
        BlendMode.AVERAGE:
            result.friction = (mat_a.friction + mat_b.friction) / 2
            result.bounce = (mat_a.bounce + mat_b.bounce) / 2
            result.absorbent = mat_a.absorbent or mat_b.absorbent
            
        BlendMode.MINIMUM:
            result.friction = min(mat_a.friction, mat_b.friction)
            result.bounce = min(mat_a.bounce, mat_b.bounce)
            result.absorbent = mat_a.absorbent and mat_b.absorbent
            
        BlendMode.MAXIMUM:
            result.friction = max(mat_a.friction, mat_b.friction)
            result.bounce = max(mat_a.bounce, mat_b.bounce)
            result.absorbent = mat_a.absorbent or mat_b.absorbent
            
        BlendMode.MULTIPLY:
            result.friction = mat_a.friction * mat_b.friction
            result.bounce = mat_a.bounce * mat_b.bounce
            result.absorbent = mat_a.absorbent or mat_b.absorbent
    
    return result
```

> 提示：上面这个混合器是**你自己写的工具函数**，产出的是一个新 `PhysicsMaterial` 资源；引擎在碰撞时**不会**调用它。引擎真正使用的是 2.3 节那张表里的 `rough` / `absorbent` 规则。想让引擎按你的规则混合，就把 `rough` / `absorbent` 配好，然后把这份混合好的材质赋给 `physics_material_override`。

### 4.2 表面类型混合

```gdscript
# 基于表面类型的智能混合
func get_combined_material(surface_a: String, surface_b: String) -> PhysicsMaterial:
    var mat_a = _get_base_material(surface_a)
    var mat_b = _get_base_material(surface_b)
    
    # 特殊情况处理
    if surface_a == "ice" or surface_b == "ice":
        # 冰面总是降低摩擦
        var result = PhysicsMaterialLibrary.create_ice()
        result.friction = min(mat_a.friction, mat_b.friction) * 0.5
        return result
    
    if surface_a == "rubber" or surface_b == "rubber":
        # 橡胶增加摩擦
        var result = PhysicsMaterialLibrary.create_rubber()
        result.friction = max(mat_a.friction, mat_b.friction)
        return result
    
    # 默认平均混合
    return CustomMaterialBlender.blend_materials(mat_a, mat_b)

func _get_base_material(surface: String) -> PhysicsMaterial:
    match surface:
        "ice": return PhysicsMaterialLibrary.create_ice()
        "wood": return PhysicsMaterialLibrary.create_wood()
        "metal": return PhysicsMaterialLibrary.create_steel()
        "rubber": return PhysicsMaterialLibrary.create_rubber()
        "grass": return PhysicsMaterialLibrary.create_grass()
        _: return PhysicsMaterial.new()
```

---

## 5. 表面效果

### 5.1 粒子效果

```gdscript
# 碰撞粒子效果
class_name CollisionParticleEffect

@export var particle_scene: PackedScene
@export var min_velocity: float = 5.0

func _ready():
    $RigidBody3D.contact_monitor = true
    $RigidBody3D.max_contacts_reported = 4

func _integrate_forces(state: PhysicsDirectBodyState3D):
    for i in range(state.get_contact_count()):
        var impulse = state.get_contact_impulse(i)
        
        if impulse.length() > min_velocity:
            var contact_pos = state.get_contact_local_position(i)
            var contact_normal = state.get_contact_local_normal(i)
            
            _spawn_particles(contact_pos, contact_normal)

func _spawn_particles(position: Vector3, normal: Vector3):
    if particle_scene:
        var particles = particle_scene.instantiate()
        particles.global_transform.origin = position
        particles.look_at(position + normal)
        get_tree().current_scene.add_child(particles)
```

### 5.2 音效效果

```gdscript
# 碰撞音效
class_name CollisionSoundEffect

@export var audio_stream: AudioStream
@export var min_velocity: float = 3.0
@export var max_velocity: float = 20.0

var audio_player: AudioStreamPlayer3D

func _ready():
    audio_player = AudioStreamPlayer3D.new()
    audio_player.stream = audio_stream
    audio_player.volume_db = -20
    add_child(audio_player)
    
    $RigidBody3D.contact_monitor = true
    $RigidBody3D.max_contacts_reported = 4

func _integrate_forces(state: PhysicsDirectBodyState3D):
    for i in range(state.get_contact_count()):
        var impulse = state.get_contact_impulse(i)
        var velocity = impulse.length()
        
        if velocity >= min_velocity:
            # 根据碰撞速度调整音量
            var volume = remap(velocity, min_velocity, max_velocity, -20, 0)
            audio_player.volume_db = volume
            audio_player.play()
```

### 5.3 痕迹效果

```gdscript
# 碰撞痕迹（如弹孔、划痕）
class_name CollisionDecal

@export var decal_scene: PackedScene
@export var min_velocity: float = 10.0

func _integrate_forces(state: PhysicsDirectBodyState3D):
    for i in range(state.get_contact_count()):
        var impulse = state.get_contact_impulse(i)
        
        if impulse.length() > min_velocity:
            var contact_pos = state.get_contact_local_position(i)
            var contact_normal = state.get_contact_local_normal(i)
            # get_contact_collider 返回 RID；要拿节点对象用 get_contact_collider_object
            var collider = state.get_contact_collider_object(i) as Node
            
            _spawn_decal(contact_pos, contact_normal, collider)

func _spawn_decal(position: Vector3, normal: Vector3, collider: Node):
    if decal_scene and collider:
        var decal = decal_scene.instantiate()
        decal.global_transform.origin = position
        # ⚠️ Basis 没有单个 Vector3 的构造函数（Basis(normal) 是非法的）。
        #    让贴花朝向法线，用 look_at_from_position：
        decal.look_at_from_position(position, position + normal)
        collider.add_child(decal)
```

---

## 6. 动态材质

### 6.1 条件材质变化

```gdscript
# 根据条件改变材质
class_name DynamicPhysicsMaterial

extends RigidBody3D

@export var wet_material: PhysicsMaterial
@export var dry_material: PhysicsMaterial

var is_wet: bool = false

func set_wet(wet: bool):
    is_wet = wet
    physics_material_override = wet_material if wet else dry_material

func _on_area_entered(area):
    if area.is_in_group("water"):
        set_wet(true)

func _on_area_exited(area):
    if area.is_in_group("water"):
        set_wet(false)
```

### 6.2 温度影响

```gdscript
# 温度影响的材质
class_name TemperaturePhysicsMaterial

extends RigidBody3D

@export var frozen_material: PhysicsMaterial
@export var normal_material: PhysicsMaterial
@export var melted_material: PhysicsMaterial

var temperature: float = 20.0  # 摄氏度

func _process(delta):
    # 更新材质基于温度
    if temperature < 0:
        physics_material_override = frozen_material
    elif temperature < 50:
        physics_material_override = normal_material
    else:
        physics_material_override = melted_material

func change_temperature(delta_temp: float):
    temperature = clamp(temperature + delta_temp, -50, 200)
```

---

## 7. 性能优化

### 7.1 材质缓存

```gdscript
# 材质缓存管理器
class_name PhysicsMaterialCache

static var cache = {}

static func get_cached_material(name: String) -> PhysicsMaterial:
    if not cache.has(name):
        cache[name] = _create_material(name)
    return cache[name]

static func _create_material(name: String) -> PhysicsMaterial:
    match name:
        "ice": return PhysicsMaterialLibrary.create_ice()
        "rubber": return PhysicsMaterialLibrary.create_rubber()
        "wood": return PhysicsMaterialLibrary.create_wood()
        _: return PhysicsMaterial.new()
```

### 7.2 材质共享

```gdscript
# 共享材质实例
func setup_shared_materials():
    # 创建共享材质
    var ice_material = PhysicsMaterialLibrary.create_ice()
    var wood_material = PhysicsMaterialLibrary.create_wood()
    
    # 多个物体共享同一材质实例
    for body in get_tree().get_nodes_in_group("ice_objects"):
        body.physics_material_override = ice_material
    
    for body in get_tree().get_nodes_in_group("wood_objects"):
        body.physics_material_override = wood_material
```

### 7.3 材质与求解器的关系

材质属性（摩擦、弹性）是在**约束求解阶段**被读取并合成的，因此它和求解器本身的参数是同一层的东西。关节多的场景卡顿，除了"关节太多"这个直观原因，还经常来自求解器配置：

| 旋钮 | 位置 | 作用 |
|------|------|------|
| `exclude_nodes_from_collision` | `Joint3D` 节点属性（默认 `true`） | 关节两端物体互相碰撞会额外产生接触约束，关掉可省一轮窄相位 |
| `solver_priority` | `Joint3D` 节点属性（默认 `1`） | 多关节互相影响时的求解顺序，数值越大越先解 |
| `joint_disable_collisions_between_bodies()` / `joint_set_solver_priority()` | `PhysicsServer3D`（`servers/physics_server_3d.h`） | 服务器层的等价接口，便于批量调参 |

```gdscript
var joint := HingeJoint3D.new()
joint.exclude_nodes_from_collision = true
joint.solver_priority = 10

# 服务器层写法
var j_rid := joint.get_rid()
PhysicsServer3D.joint_disable_collisions_between_bodies(j_rid, true)
PhysicsServer3D.joint_set_solver_priority(j_rid, 10)
```

> 摩擦/弹性越"硬"，求解器为保持约束收敛所需的迭代就越多。材质参数（尤其 `bounce` 接近 1、`friction` 接近 1）与关节刚度叠加时，才会显著拖慢物理帧——这是"关节多的场景卡顿"里最容易被忽略的一半原因。完整排查流程见第 32 篇。

---

## 📝 本章总结

### 核心要点

1. **物理材质定义表面属性**，包括摩擦、弹性、吸收性（布尔开关）
2. **摩擦力影响滑动**，弹性影响反弹
3. **材质混合由 `rough` / `absorbent` 决定**：摩擦取较小值（双方都 rough 时取较大值），弹性默认相加、`absorbent` 为 true 时相减
4. **预设材质库提高效率**，避免重复创建
5. **动态材质响应环境变化**，增加真实感

### 关键术语

| 术语 | 解释 |
|------|------|
| Friction | 摩擦力，抵抗相对运动的力 |
| Bounce | 弹性，碰撞后反弹的能力 |
| Restitution | 恢复系数，碰撞后速度保持比例 |
| Material Blending | 材质混合，两个材质碰撞时的属性计算 |
| Physics Material | 物理材质，定义表面物理属性 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot PhysicsMaterial](https://docs.godotengine.org/en/stable/classes/class_physicsmaterial.html)
- **材质参考**: [Physics Material Properties](https://docs.godotengine.org/en/stable/tutorials/physics/physics_introduction.html)
- **源码位置**: `scene/resources/physics_material.cpp`
- **技术博客**: [Godot Physics Materials Guide](https://godotengine.org/article/physics-materials-guide/)

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 25 篇：碰撞检测](/articles/25-collision-detection.md)
**下一篇**: [第 27 篇：关节和约束](/articles/27-joints-and-constraints.md)

---

## 📋 下一章预告

**第 27 篇：关节和约束**

- 关节类型详解
- 铰链关节
- 滑块关节
- 锥形扭关节
- 通用关节
- 约束优化

---

*写作时间：2026-03-20*  
*字数：约 1,000 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 13:00*
