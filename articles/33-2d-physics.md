# 第 33 篇：2D 物理系统

> **本卷定位**: 第三卷 物理系统（续篇）
> **前置知识**: 第 23 篇 物理架构、第 24 篇 刚体物理
> **难度等级**: ⭐⭐ 中级

---

## 一、2D 物理架构

### 1.1 一套独立的物理引擎

Godot 的 2D 与 3D 物理是**两套并行的实现**：`PhysicsServer2D` 与 `PhysicsServer3D` 各自独立，类型不互通（`Vector2` vs `Vector3`、`Transform2D` vs `Transform3D`）。前几篇讲的宽相位/窄相位/求解器流程在 2D 同样成立，但类名、属性与能力集合不同。

### 1.2 物理体层级

```
CollisionObject2D（抽象：承载形状、层/掩码、区域监测）
├── Area2D                 只检测、不产生物理响应
├── StaticBody2D           静态体（墙壁、地面）
├── AnimatableBody2D       可动画体（sync_to_physics 推动其他物体）
├── CharacterBody2D        角色体（move_and_slide() 驱动）
└── RigidBody2D            刚体（力/冲量驱动）
每个 CollisionObject2D 挂载一个或多个：
    ├── CollisionShape2D   （单个形状资源）
    └── CollisionPolygon2D （多边形轮廓）
```

选择依据与 3D 相同：**能被代码直接驱动的用 `CharacterBody2D`，需要真实力学响应的用 `RigidBody2D`，纯碰撞体用 `StaticBody2D`，只触发事件的用 `Area2D`**。

---

## 二、碰撞形状

### 2.1 形状资源选型

| 形状资源 | 开销 | 适用 |
|----------|------|------|
| `RectangleShape2D` | 最低 | 箱子、墙体、平台 |
| `CircleShape2D` | 最低 | 滚动体、球形角色（天然无角卡边） |
| `CapsuleShape2D` | 低 | 人形角色（避免楼梯边卡顿） |
| `SegmentShape2D` | 低 | 单段线（激光、边界） |
| `WorldBoundaryShape2D` | 低 | 无限地面/天花板 |
| `ConvexPolygonShape2D` | 中 | 凸多边形（动态体可用） |
| `ConcavePolygonShape2D` | 高 | **仅静态体**；凹多边形轮廓 |

与 3D 相同的规则：**动态体避免凹多边形**，凹形碰撞需求用多个凸形状组合表达。

### 2.2 一个 CollisionShape2D 只承载一个形状

需要复合形状时，往物理体下挂多个 `CollisionShape2D` 节点，而不是让一个节点承载多个形状。形状资源在节点间是共享的，修改前先 `duplicate()`（与第 26 篇 3D 的结论一致）。

---

## 三、CharacterBody2D：角色移动

### 3.1 move_and_slide 的参数即属性

4.x 的 `move_and_slide()` **没有参数**：所有行为都由属性控制。

```gdscript
extends CharacterBody2D

@export var speed := 300.0
@export var jump_velocity := -420.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity += get_gravity() * delta

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    var direction := Input.get_axis("move_left", "move_right")
    velocity.x = direction * speed

    move_and_slide()
```

常用行为属性：

| 属性 | 作用 |
|------|------|
| `up_direction` | "地面"的方向（默认 `UP`，可做重力翻转关卡） |
| `floor_snap_length` | 贴地距离，下坡不悬空 |
| `floor_max_angle` | 算作地面的最大坡角 |
| `floor_stop_on_slope` | 停在坡上是否滑动 |
| `wall_min_slide_angle` | 撞墙开始滑动的最小夹角 |
| `max_slides` | 单次移动最多分解的滑动次数 |
| `motion_mode` | `GROUNDED`（平台） / `FLOATING`（俯视/太空） |

### 3.2 碰撞状态查询

```gdscript
move_and_slide()
if is_on_floor():   ...   # 必须在 move_and_slide() 之后调用
if is_on_wall():
    var normal := get_wall_normal()
if is_on_ceiling(): ...
var platform_velocity := get_platform_velocity()   # 站上移动平台时的平台速度
```

**顺序敏感**：`is_on_floor()` 等状态由 `move_and_slide()` 写入，必须在其后读取。

### 3.3 手感三件套：土狼时间、跳跃缓冲、可变跳跃

```gdscript
@export var coyote_time := 0.12
@export var jump_buffer := 0.12

var _coyote := 0.0
var _buffer := 0.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity += get_gravity() * delta
        _coyote -= delta
        _buffer -= delta
    else:
        _coyote = coyote_time

    if Input.is_action_just_pressed("jump"):
        _buffer = jump_buffer

    if _buffer > 0.0 and _coyote > 0.0:
        velocity.y = jump_velocity
        _coyote = 0.0
        _buffer = 0.0

    # 可变跳跃高度：松开跳跃键提前截断上升
    if Input.is_action_just_released("jump") and velocity.y < 0.0:
        velocity.y *= 0.5

    var direction := Input.get_axis("move_left", "move_right")
    velocity.x = direction * speed
    move_and_slide()
```

土狼时间与跳跃缓冲不改变物理参数，只是把"输入时机"与"物理时机"解耦——这是 2D 角色手感的两个最高性价比改进。

---

## 四、RigidBody2D

| 属性 | 说明 |
|------|------|
| `freeze` + `freeze_mode` | 冻结为静态/运动学（取代 3.x 的 `mode`） |
| `lock_rotation` | 锁定旋转（顶视角色常用） |
| `continuous_cd` | 连续碰撞检测，防高速穿透 |
| `contact_monitor` + `max_contacts_reported` | 开启后 `body_entered` 才会触发 |

**`contact_monitor = false`（默认）时 `body_entered` 永远不触发**——这是 2D 刚体最高频的"为什么没反应"问题。

```gdscript
func _ready() -> void:
    contact_monitor = true
    max_contacts_reported = 4
    body_entered.connect(_on_body_entered)

# 力与冲量；需要绕过积分直接改状态时用 _integrate_forces
func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
    if state.transform.origin.y > 1000.0:
        state.transform.origin = Vector2.ZERO   # 跌出边界则重置
        state.linear_velocity = Vector2.ZERO
```

---

## 五、Area2D 与空间查询

```gdscript
extends Area2D

func _ready() -> void:
    body_entered.connect(_on_body_entered)   # 物理体进入
    area_entered.connect(_on_area_entered)   # 其他区域进入
```

| 属性 | 说明 |
|------|------|
| `monitoring` | 是否监测别的物体进入自己 |
| `monitorable` | 是否允许别的区域监测到自己 |
| `gravity_space_override` / `gravity` | 区域内自定义重力（反重力区、水上） |

一次性查询走 `PhysicsDirectSpaceState2D`（`get_world_2d().direct_space_state`），**必须在 `_physics_process` 中使用**：

```gdscript
func _physics_process(_delta: float) -> void:
    var space := get_world_2d().direct_space_state
    var ray := PhysicsRayQueryParameters2D.create(from, to, collision_mask, [self])
    var hit := space.intersect_ray(ray)
    if hit:
        print("命中：", hit.collider, " @ ", hit.position)
```

持续检测用节点形态：`RayCast2D`（`is_colliding()` + `get_collider()`）与 `ShapeCast2D`（扫掠形状）。

---

## 六、碰撞层与掩码

```gdscript
@export_flags_2d_physics var interact_layers: int = 1

func _ready() -> void:
    collision_layer = 1 << 1          # 我在第 2 层
    collision_mask = 1 | (1 << 2)     # 我检测第 1、3 层
```

层命名在项目设置 `layer_names/2d_physics/layer_1 … layer_32`。收窄 mask 是 2D 物理优化的第一优先级——宽相位配对越少，窄相位与求解器负担越小（结论与第 32 篇一致）。

---

## 七、性能优化

- **形状选型**：圆/矩形/胶囊优先，多边形只用于轮廓必要处；
- **休眠**：静止的 `RigidBody2D` 自动休眠，不要每帧给它微小扰动；
- **物理插值**：物理帧率低于渲染帧率时开启 `physics/common/physics_interpolation`（4.3 起支持 2D），消除抖动；节点级用 `physics_interpolation_mode` 覆盖；
- **TileMap 物理**：瓦片碰撞走 `TileSet` 物理层（4.3 用 `TileMapLayer`），整块地图合并为少量内部体，远优于逐格放置 `StaticBody2D`。

---

## 八、实践：完整平台角色

```gdscript
extends CharacterBody2D

@export var speed := 300.0
@export var jump_velocity := -420.0
@export var acceleration := 2400.0
@export var friction := 3000.0

var _coyote := 0.0
var _buffer := 0.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity += get_gravity() * delta
        _coyote -= delta
        _buffer -= delta
    else:
        _coyote = coyote_time

    if Input.is_action_just_pressed("jump"):
        _buffer = jump_buffer

    if _buffer > 0.0 and _coyote > 0.0:
        velocity.y = jump_velocity
        _coyote = 0.0
        _buffer = 0.0

    var direction := Input.get_axis("move_left", "move_right")
    if direction != 0.0:
        velocity.x = move_toward(velocity.x, direction * speed, acceleration * delta)
    else:
        velocity.x = move_toward(velocity.x, 0.0, friction * delta)

    move_and_slide()
```

> 注：完整工程建议把手感参数（土狼时间/缓冲/截断系数）做成 `@export`，见 3.3 节的分项实现。

---

## 九、总结

2D 物理与 3D 共享同一套设计语言，但类型独立：

- **选型**：`CharacterBody2D` 驱动角色、`RigidBody2D` 做力学响应、`StaticBody2D`/`AnimatableBody2D` 做场景碰撞、`Area2D` 做事件区
- **手感**：土狼时间 + 跳跃缓冲 + 可变跳跃是 2D 角色的标准三件套
- **查询**：持续监测用 `RayCast2D`/`ShapeCast2D`，一次性判定用 `direct_space_state`
- **性能**：收窄 mask、控制形状数量、开启物理插值

---

## 🔗 延伸阅读

- **CharacterBody2D**: <https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html>
- **RigidBody2D**: <https://docs.godotengine.org/en/stable/classes/class_rigidbody2d.html>
- **PhysicsDirectSpaceState2D**: <https://docs.godotengine.org/en/stable/classes/class_physicsdirectspacestate2d.html>
- **源码位置**: `servers/physics_2d/`, `scene/2d/physics/`

---

**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 32 篇：物理性能优化](/articles/32-physics-performance-optimization.md)
**下一篇**: [第 34 篇：Jolt Physics](/articles/34-jolt-physics.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
