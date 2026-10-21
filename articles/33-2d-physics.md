# 第 33 篇：2D 物理系统

> **本卷定位**: 第三卷 物理系统（续篇）
> **前置知识**: 第 23 篇 物理架构、第 24 篇 刚体物理
> **难度等级**: ⭐⭐ 中级
> **本章导读**：2D 物理**不是** 3D 物理的简化版，而是 `PhysicsServer2D` 一套独立实现，类型与接口都不与 3D 互通。
> 本章讲清 2D 物理的独立体系与 `PhysicsBody2D` 家族、`CharacterBody2D` 的手感三件套（土狼时间 / 跳跃缓冲 / 可变跳跃）、`Area2D` 的事件模型、射线与形状查询的两种入口，以及与 3D 篇一一对应的对照关系。


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

选择依据与 3D 相同：**能被代码直接驱动的用 `CharacterBody2D`，需要真力学响应的用 `RigidBody2D`，纯碰撞体用 `StaticBody2D`，只触发事件的用 `Area2D`**。

### 1.3 2D 物理服务器：源码地图

2D 物理不是"3D 物理的 2D 版"，而是一套完全独立的实现。引擎源码在 `modules/godot_physics_2d/`，与 3D 的 `modules/godot_physics_3d/` **不共享任何代码**（第 23 篇讲的 `GodotPhysics3D` 在 2D 侧没有对应物）。4.7.2 的文件分工：

| 源码文件（`modules/godot_physics_2d/`） | 职责 |
|---|---|
| `godot_physics_server_2d.h/cpp` | `PhysicsServer2D` 实现，管理 space / body / area / shape / joint 的 RID 生命周期 |
| `godot_space_2d.h/cpp` | 一个物理世界（space）：物体表、岛屿划分、每帧步进与休眠调度 |
| `godot_broad_phase_2d.h/cpp` | 宽相位接口 `GodotBroadPhase2D`（纯抽象） |
| `godot_collision_solver_2d.h/cpp` | 窄相位求解器 `GodotCollisionSolver2D`：形状对形状的分离与流形计算 |
| `godot_body_pair_2d.h/cpp` | `GodotBodyPair2D`：一对相交物体，维护接触流形与求解状态 |
| `godot_body_2d.h/cpp` | 单个刚体在服务器侧的状态：速度、质量、阻尼、休眠 |
| `godot_area_2d.h/cpp` | 区域体，维护进入/离开的重叠表 |
| `godot_direct_space_state_2d.h/cpp` | 对外查询接口（射线、形状、点重叠） |
| `godot_direct_body_state_2d.h/cpp` | `_integrate_forces` 回调拿到的状态对象 |

宽相位在 4.3 里是**接口 + 工厂**，而不是写死的一种结构：

```cpp
// modules/godot_physics_2d/godot_broad_phase_2d.h（4.3）
class GodotBroadPhase2D {
public:
	typedef GodotBroadPhase2D *(*CreateFunction)();
	static CreateFunction create_func;

	virtual ID create(GodotCollisionObject2D *p_object_, int p_subindex = 0,
			const Rect2 &p_aabb = Rect2(), bool p_static = false) = 0;
	virtual void move(ID p_id, const Rect2 &p_aabb) = 0;
	virtual int cull_segment(const Vector2 &p_from, const Vector2 &p_to,
			GodotCollisionObject2D **p_results, int p_max_results,
			int *p_result_indices = nullptr) = 0;
	virtual int cull_aabb(const Rect2 &p_aabb, GodotCollisionObject2D **p_results,
			int p_max_results, int *p_result_indices = nullptr) = 0;
	virtual void set_pair_callback(PairCallback p_pair_callback, void *p_userdata) = 0;
	virtual void update() = 0;
};
```

也就是说：**"2D 宽相位用网格/空间划分"是实现细节，不是稳定契约**。可以依赖的公开契约只有两条——"给定 AABB 或线段，返回候选物体集合"，以及 `collision_layer` / `collision_mask` 这对开关。项目代码里不要假设某种划分方式，也不要试图用反射去读它。

窄相位的入口是 `GodotCollisionSolver2D::solve()`，它对两个形状做扫掠求解：

```cpp
// modules/godot_physics_2d/godot_collision_solver_2d.h（4.3）
static bool solve(const GodotShape2D *p_shape_A, const Transform2D &p_transform_A,
		const Vector2 &p_motion_A, const GodotShape2D *p_shape_B, const Transform2D &p_transform_B,
		const Vector2 &p_motion_B, CallbackResult p_result_callback, void *p_userdata,
		Vector2 *r_sep_axis = nullptr, real_t p_margin_A = 0, real_t p_margin_B = 0);
```

`p_motion_A` / `p_motion_B` 是"这一物理步里形状要移动多远"——这正是 2D 侧连续碰撞检测（CCD）的实现方式：**把整步位移一次性交给求解器做扫掠**，而不是先移动再纠正。

### 1.4 节点 API 与服务器 API：两种建模方式，不是两级高低

`PhysicsServer2D` 的直接 API（`body_create()` / `body_add_shape()` / `body_set_state()` …）与节点 API（`RigidBody2D` / `CharacterBody2D` / `Area2D`）都能完成同样的事，但**不是"低阶/高阶"的关系**，而是两种不同的建模方式：

| 维度 | 节点 API | `PhysicsServer2D` 直接 API |
|---|---|---|
| 对象生命周期 | 随场景树自动创建/销毁 | 手动 `free_rid()`，忘了释放就是泄漏 |
| 变换同步 | 引擎每物理步把服务器状态写回节点 | 无回写，你要自己维护 `Transform2D` |
| 事件 | 有信号（`body_entered` 等） | 有回调（`area_set_monitor_callback` 等），语义更原始 |
| 适用场景 | 绝大多数项目 | 特殊玩法：自建"多世界"、运行时批量生成临时体、不需要节点的独立物理体 |

节点 API 的内部实现就是"创建 RID → 调服务器方法 → 注册回调"，所以两者能力等价，区别只在谁替你管理 RID 和回写。

用服务器 API 手搓一个最小刚体：

```gdscript
# 直接使用 PhysicsServer2D：创建刚体并挂一个矩形形状
var server := PhysicsServer2D

var body_rid := server.body_create()
server.body_set_mode(body_rid, PhysicsServer2D.BODY_MODE_RIGID)
server.body_set_space(body_rid, get_world_2d().get_space())

var shape_rid := server.rectangle_shape_create()
server.shape_set_data(shape_rid, Vector2(16, 16))     # 半尺寸
server.body_add_shape(body_rid, shape_rid, Transform2D.IDENTITY)

server.body_set_state(body_rid, PhysicsServer2D.BODY_STATE_TRANSFORM,
		Transform2D(0, Vector2(100, 100)))
server.body_set_state(body_rid, PhysicsServer2D.BODY_STATE_LINEAR_VELOCITY, Vector2(50, 0))

# 用完必须释放
server.free_rid(body_rid)
```

> ⚠️ 这段代码没有接 `_integrate_forces` 回调、没有碰撞事件、没有自动回写节点变换，只是演示"服务器 API 能做什么"。**除非你在做工具/编辑器插件或特殊的自建世界，否则请用节点 API**——第 23 篇 9.3 节的选型结论在 2D 侧同样成立。

服务器 API 真正不可替代的地方有两个：**运行时批量生成/销毁成千上万个临时碰撞体**（对象池式子弹、粒子碰撞），以及**一个逻辑对象由多个独立刚体组成**（一条蛇的每一节）。

### 1.5 `AnimatableBody2D` 与 `sync_to_physics`

`AnimatableBody2D` 是"不能被外力推动、只能被代码/动画移动，但移动时会推动沿途其他物体"的体——移动平台、电梯、传送带都靠它。

```gdscript
extends AnimatableBody2D

func _ready() -> void:
	# 默认就是 true：把节点变换同步到物理帧
	sync_to_physics = true
```

`sync_to_physics`（4.3 默认 `true`）的语义：

| 取值 | 行为 | 适用 |
|---|---|---|
| `true` | 节点的变换在**物理帧边界**被同步进物理世界；配合 `AnimationMixer` 的 `callback_mode_process = ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS` 播放动画时最稳 | 由动画驱动的移动平台 |
| `false` | 变换**立即**生效（每个渲染帧都推给物理服务器） | 由代码逐帧驱动的平台；或需要"看到的位��"与"碰撞位置"完全一致 |

关键约束（4.3 类参考原文）：**`sync_to_physics = true` 时不要同时使用 `PhysicsBody2D.move_and_collide()`**——一个把位移交给物理步处理，一个把位移立刻写进世界，两者会打架，表现为平台上的角色被弹飞或抖动。

移动平台还要注意**速度估计**：`AnimatableBody2D` 被移动时，引擎会估算它的线速度与角速度并传给沿途的物体，从而让站在上面的 `CharacterBody2D` 被带着走。速度估计基于两帧之间的位移差，所以平台**瞬移**（而不是连续移动）会算出极大的速度把角色弹飞；平台做**圆周运动**则只有切向分量被估算出来，角色会被"甩"而不是"转"。

这就是 `CharacterBody2D.platform_floor_layers` / `platform_wall_layers` 存在的原因：前者（默认全开）决定"哪些碰撞层上的物体算作会被跟随的地板"，后者（默认关闭）决定"哪些层上的物体算作会被跟随的墙"。默认关闭墙跟随是有意的——大多数游戏里角色撞到墙应该停住，而不是贴着墙被拖着走。

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

> **`get_gravity()` 从哪来**：`get_gravity()` **不在 `CharacterBody2D` 类参考里**，但它**确实可用**——它继承自父类 `PhysicsBody2D`（`CharacterBody2D` → `PhysicsBody2D` → `CollisionObject2D`）。它的作用是返回"作用于本体的总重力矢量"，**已包含 `Area2D` 的重力覆盖**与项目全局重力，比自己读 `physics/2d/default_gravity` 更准确。
>
> 3D 侧对应的是 `PhysicsBody3D.get_gravity()`（`CharacterBody3D` 同样继承自它）。
>
> 如果你的脚本基类不是 `PhysicsBody2D`（例如自己继承 `Node2D`），`get_gravity()` 就不存在，这时才需要退回到：
>
> ```gdscript
> var g := ProjectSettings.get_setting("physics/2d/default_gravity", 980.0)
> ```
>
> 注意 `physics/2d/default_gravity` 是**标量**（每帧施加的加速度，不是加速度平方），而 `get_gravity()` 返回的是**矢量**。

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

### 3.4 `CharacterBody2D` 完整属性面（4.3 逐项核实）

下面这张表来自 4.3 的 `doc/classes/CharacterBody2D.xml`，属性名、类型、默认值逐项核对过：

| 属性 | 类型 | 默认值 | 作用 |
|---|---|---|---|
| `velocity` | `Vector2` | `(0, 0)` | 当前速度（像素/秒），`move_and_slide()` 会读取并可能改写它 |
| `motion_mode` | `int` | `0`（`MOTION_MODE_GROUNDED`） | `GROUNDED` = 有地面/墙/天花板概念；`FLOATING` = 一切碰撞都算墙（俯视/太空） |
| `up_direction` | `Vector2` | `(0, -1)` | "上"的方向，用来区分墙 / 地板 / 天花板；会被归一化，不能是零向量 |
| `floor_max_angle` | `float` | `0.785398`（45°） | 坡度小于该角度才算地板，否则算墙 |
| `floor_snap_length` | `float` | `1.0` | 贴地吸附距离；下坡时不脱离地面。**沿"上"方向移动时不吸附**（所以跳跃能离地） |
| `floor_stop_on_slope` | `bool` | `true` | 静止在斜坡上时是否继续下滑 |
| `floor_block_on_wall` | `bool` | `true` | 只允许在地板上行走，避免"爬墙"；撞墙时仍可沿墙下滑 |
| `floor_constant_speed` | `bool` | `false` | 关闭时上坡慢下坡快；开启后地面速度恒定（需配合 `floor_snap_length` 才能贴坡） |
| `platform_on_leave` | `int` | `0` | 离开移动平台时的行为：`ADD_VELOCITY` / `ADD_UPWARD_VELOCITY` / `DO_NOTHING` |
| `platform_floor_layers` | `int` | `4294967295`（全开） | 哪些碰撞层上的物体会被当作"会跟随的地板" |
| `platform_wall_layers` | `int` | `0`（全关） | 哪些碰撞层上的物体会被当作"会跟随的墙" |
| `safe_margin` | `float` | `0.08` | 碰撞恢复用的额外余量；越大越容易判定为接触，越小越精确 |
| `slide_on_ceiling` | `bool` | `true` | 撞天花板时是滑动还是直接停住垂直下落 |
| `wall_min_slide_angle` | `float` | `0.261799`（15°） | 撞到坡面时允许滑动的最小夹角；**仅在 `MOTION_MODE_FLOATING` 下生效** |
| `max_slides` | `int` | `4` | 单次 `move_and_slide()` 最多分解几次滑动 |

> ⚠️ **没有 `wall_stop_slide` 这个属性**。4.3 与 4.7 的 `CharacterBody2D` 类参考里都没有它——很多教程把 3D 的直觉照搬过来写了 `wall_stop_slide = true`，在 2D 上会报 `Invalid set index 'wall_stop_slide'`。2D 里"撞墙后停住 vs 沿墙下滑"由 `floor_block_on_wall` 与 `slide_on_ceiling` 承担，"在斜坡上停住 vs 下滑"由 `floor_stop_on_slope` 承担。

方法面（4.3 完整列表）：

| 方法 | 说明 |
|---|---|
| `move_and_slide()` | **无参数**。按 `velocity` 移动并处理滑动；返回 `true` 表示本次发生了碰撞 |
| `get_last_slide_collision()` | 最近一次碰撞的 `KinematicCollision2D` |
| `get_slide_collision(i)` / `get_slide_collision_count()` | 逐个取出本次移动中的所有滑动碰撞 |
| `get_platform_velocity()` | 最后接触点的平台线速度（仅在 `move_and_slide()` 之后有效） |
| `get_real_velocity()` | 实际位移速度（上坡时是斜向的），与 `velocity`（请求的速度）不同 |
| `get_position_delta()` / `get_last_motion()` | 本次移动的位移 / 最后一段滑动位移 |
| `get_floor_normal()` / `get_floor_angle(up_direction)` | 地面法线与地面倾角（仅 `is_on_floor()` 为真时有效） |
| `get_wall_normal()` | 墙面法线（仅 `is_on_wall()` 为真时有效） |
| `is_on_floor()` / `is_on_ceiling()` / `is_on_wall()` | 三类接触状态 |
| `is_on_floor_only()` / `is_on_ceiling_only()` / `is_on_wall_only()` | "只接触了某一面"（用于区分"贴墙落地"与"落地"） |
| `apply_floor_snap()` | 忽略速度强制吸附到地面（`is_on_floor()` 为真时无效） |

> 注意 `get_floor_normal()` 的官方警告：**碰撞法线不一定等于表面法线**。角色站在两个面交界处时，返回的法线可能是折中的结果，不能直接当作"地面朝向"用。

### 3.5 手感调参表

手感三件套（3.3 节）解决的是"输入时机"，这一张表解决"运动参数"。默认值是 Godot 的初始值，**不是推荐值**——每个项目的像素尺度、帧率、角色尺寸都不同，必须实测。

| 参数 | 典型起点 | 调大的表现 | 调小的表现 | 常见踩坑 |
|---|---|---|---|---|
| `speed`（水平速度，px/s） | 200–300 | 角色更"飘"、更难停 | 更"黏"、手感更稳 | 与跳跃初速度不匹配时会显得"飘" |
| `acceleration`（加速度，px/s²） | 1500–3000 | 起步慢、停得也慢 | 起停更脆 | 太大时角色像"踩了刹车"起步 |
| `friction`（减速度，px/s²） | 2000–4000 | 滑步长 | 立刻停住 | 若小于 `acceleration` 会感觉"打滑" |
| `jump_velocity`（起跳初速度，px/s） | -350 ~ -500 | 跳得高、滞空久 | 跳得矮 | 高度 ≈ `v²/(2g)`，`g` 取 `get_gravity().y` |
| `coyote_time`（土狼时间，s） | 0.08–0.15 | 走出平台后仍可跳 | 刚离开平台就跳不了 | 太大（>0.2）会让玩家产生"空中二段跳"的错觉 |
| `jump_buffer`（跳跃缓冲，s） | 0.08–0.15 | 落地前按跳也能生效 | 落地后按跳必须立刻 | 与 `coyote_time` 同时开大会让手感"过于宽容" |
| 跳跃截断系数 | 0.3–0.5 | 松键后上升更长 | 松键几乎立刻下坠 | 系数直接乘在 `velocity.y` 上，**符号要为负**才截断上升 |
| `floor_snap_length`（px） | 4–12 | 下坡更稳 | 下坡容易"跳起来" | 太大会在上坡时"吸"住角色 |
| `safe_margin`（px） | 0.08（默认） | 更不容易漏判接触 | 更容易"卡"在缝隙 | 改小是精确派，改大是鲁棒派，别乱调 |

> ⚠️ 上表给出的是**参数关系与调参方向**，不是实测数值；具体数值必须在目标分辨率、目标帧率下用固定测试场景对比（本卷第 32 篇的基准测试流程）。

---

## 四、RigidBody2D

### 4.1 属性与冻结模式

| 属性 | 类型 | 说明 |
|------|------|------|
| `freeze` | `bool` | 冻结后不再响应物理；`freeze_mode` 决定它还算不算"静态体" |
| `freeze_mode` | `int` | `FREEZE_MODE_STATIC`（当作静态体）/ `FREEZE_MODE_KINEMATIC`（当作运动学体） |
| `lock_rotation` | `bool` | 锁定旋转（顶视角色常用） |
| `continuous_cd` | `int` | `CCD_MODE_DISABLED` / `CCD_MODE_CAST_RAY` / `CCD_MODE_CAST_SHAPE` |
| `contact_monitor` | `bool` | **默认 `false`**；关闭时 `body_entered` / `body_exited` 永不触发 |
| `max_contacts_reported` | `int` | 最多报告多少个接触点；`contact_monitor` 开启后生效 |
| `gravity_scale` | `float` | 重力倍率 |
| `linear_damp` / `angular_damp` | `float` | 线性 / 角阻尼 |
| `mass` | `float` | 质量（服务器层对应 `BODY_PARAM_MASS`） |

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

### 4.2 `PhysicsDirectBodyState2D`：`_integrate_forces` 的状态对象

`RigidBody2D._integrate_forces(state)` 收到的 `state` 是 `PhysicsDirectBodyState2D`，它同时提供**读**（当前状态）与**写**（改写状态）两类接口。4.3 的完整字段如下。

**成员属性（可直接读写）**

| 成员 | 类型 | 说明 |
|------|------|------|
| `linear_velocity` | `Vector2` | 线速度（像素/秒）；**没有 `get_velocity()` 这个方法**，只有 `get_linear_velocity()` |
| `angular_velocity` | `float` | 角速度（弧度/秒） |
| `transform` | `Transform2D` | 本体的变换矩阵（可写） |
| `sleeping` | `bool` | 是否处于休眠 |
| `step` | `float` | 本次模拟的步长（delta） |
| `total_gravity` | `Vector2` | 当前作用在本体的**总**重力矢量（已包含 `Area2D` 的重力覆盖） |
| `total_linear_damp` / `total_angular_damp` | `float` | 实际生效的阻尼（含 `Area2D` 覆盖） |
| `inverse_mass` | `float` | 质量倒数；**为 0 表示无限质量（静态）** |
| `inverse_inertia` | `float` | 惯性矩倒数；为 0 表示无限惯性 |
| `center_of_mass` | `Vector2` | 质心位置（全局坐标） |
| `center_of_mass_local` | `Vector2` | 质心位置（本体局部坐标） |

**方法**

| 方法 | 签名要点 | 说明 |
|------|----------|------|
| `apply_impulse(impulse, position = Vector2.ZERO)` | `position` 是相对本体原点的**全局偏移** | 施加位置冲量，会同时影响旋转。冲量**时间无关**，每帧施加等于每帧不同的力 |
| `apply_central_impulse(impulse)` | 无位置参数 | 施加中心冲量，**不影响旋转** |
| `apply_force(force, position = Vector2.ZERO)` / `apply_central_force(force)` | — | 施加力；力**时间相关**，必须每个物理步重复施加 |
| `apply_torque(torque)` / `apply_torque_impulse(impulse)` | 需要 `inverse_inertia != 0` | 施加扭矩 / 角冲量 |
| `add_constant_force(force, position)` / `add_constant_central_force(force)` / `add_constant_torque(torque)` | — | 持续施力，直到用 `set_constant_force(Vector2.ZERO)` 清零 |
| `get_contact_count()` | — | 接触点数量；**默认返回 0**，除非刚体开启了 `contact_monitor` |
| `get_contact_local_position(idx)` | 返回 `Vector2` | 接触点在本体上的位置（4.3 类参考写的是全局坐标系） |
| `get_contact_collider_position(idx)` | 返回 `Vector2` | 接触点在碰撞对象上的位置（全局坐标） |
| `get_contact_local_normal(idx)` | 返回 `Vector2` | 接触点法线 |
| `get_contact_collider(idx)` | 返回 `RID` | 碰撞对象的 RID |
| `get_contact_collider_id(idx)` | 返回 `int` | 碰撞对象的 object id |
| `get_contact_collider_object(idx)` | 返回 `Object` | 碰撞对象节点（由场景创建时才有意义） |
| `get_contact_collider_shape(idx)` | 返回 `int` | 碰撞对象的形状索引 |
| `get_contact_local_shape(idx)` | 返回 `int` | 本体的形状索引 |
| `get_contact_impulse(idx)` | 返回 `Vector2` | 该接触点产生的冲量 |
| `get_contact_collider_velocity_at_position(idx)` / `get_contact_local_velocity_at_position(idx)` | 返回 `Vector2` | 接触点处的相对速度 |
| `get_velocity_at_local_position(local_position)` | 返回 `Vector2` | 本体在该相对位置处的速度（含旋转贡献） |
| `get_space_state()` | 返回 `PhysicsDirectSpaceState2D` | 在回调里做查询 |
| `integrate_forces()` | — | 手动推进一次积分（等价于"这一帧我替你积分了"） |

最常见的两个坑：

1. **`get_velocity()` 不存在**。`PhysicsDirectBodyState2D` 在 4.3 里只有 `get_linear_velocity()`（成员 `linear_velocity` 的 getter）。写 `state.get_velocity()` 会报 `Invalid call. Nonexistent function 'get_velocity'`。想拿"某一点的速度"用 `get_velocity_at_local_position()`。
2. **力与冲量别混用**。`apply_impulse()` 是"一瞬间的推"，`apply_force()` 是"持续推"，后者必须每物理步重复调用。把 `apply_force()` 写在 `_physics_process` 里、或反过来每帧都 `apply_impulse()`，都会得到与帧率相关的错误手感。

```gdscript
extends RigidBody2D

@export var thrust := 0.0
var _pending_jump := false

# 正确示范：冲量用于一次性事件，力用于持续推力
func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
	# 持续推力：每步都要重新施加
	state.apply_central_force(Vector2.RIGHT * thrust)

	# 一次性冲量：只在需要的那一帧调用
	if _pending_jump:
		state.apply_central_impulse(Vector2.UP * jump_impulse)
		_pending_jump = false

	# 越界保护：直接改写状态
	if state.transform.origin.y > 1000.0:
		state.transform.origin = Vector2.ZERO
		state.linear_velocity = Vector2.ZERO
```

> ⚠️ `state.transform.origin` 是**全局坐标**下的位置。做"离场重置"时请用它与全局阈值比较，不要拿它当局部坐标。

### 4.3 刚体的常见误配

刚体的"不动 / 抖动 / 穿透 / 旋转不停"这四类症状，根因往往在配置而不是代码——完整排查表（现象 → 可能原因 → 验证方法）见**第 36 篇 物理调试与问题排查**的 3.4 节速查表。这里只列最常中的两条：**刚体完全不动**（已被 `freeze = true` 冻结，或已休眠 → 检查 `freeze` / `sleeping` / `can_sleep`）；**刚体"抖"**（每帧都施加了微小力/速度，阻止了休眠 → 只在有输入时施加，不要写 `velocity.x = velocity.x` 这种空操作）。另外两条同样高频：**刚体穿过薄墙**（单帧位移大于墙厚 → 开 `continuous_cd` 或加厚墙体）、**角色被旋转**（用 `RigidBody2D` 做角色 → 改 `CharacterBody2D` 或 `lock_rotation = true`）。

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

### 5.1 `monitoring` 与 `monitorable`：最容易搞反的两个开关

这两个开关的方向性完全不同，是 2D 物理里最高频的概念混淆：

| 属性 | 默认 | 含义 | 典型误用 |
|---|---|---|---|
| `monitoring` | `true` | **我**是否去检测别人的进入/离开 | 想让"别人检测到我"却去关 `monitoring` —— 关了以后 `body_entered` 在自己身上永远不触发 |
| `monitorable` | `true` | **别人**能否检测到我 | 想让"自己不被别人检测到"却去关 `monitoring` —— 应该是关 `monitorable` |

一句话记忆：

- `monitoring` 管**输出**（我发信号）；
- `monitorable` 管**输入**（我被信号）。

最典型的配对场景是"伤害区 + 玩家"：

```gdscript
# 伤害区（Area2D）
extends Area2D

func _ready() -> void:
	monitoring = true      # 我要检测玩家进来
	monitorable = false    # 但我不想被别的 Area2D 检测到（防止重复结算）
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		body.take_damage(damage)
```

```gdscript
# 玩家（Area2D）
extends Area2D

func _ready() -> void:
	monitoring = false     # 我不主动检测
	monitorable = true     # 但允许伤害区检测我
```

> 服务器层的默认值与节点层不同：`PhysicsServer2D.area_create()` 创建的区域，`monitorable` 默认为 **`false`**（4.3 类参考原文）。节点 `Area2D` 会把默认的 `true` 写下去，所以只有直接用服务器 API 时才会遇到"新建的区域检测不到别人"这种反直觉现象。

### 5.2 信号触发条件全表

| 信号 | 参数 | 触发条件 |
|---|---|---|
| `body_entered(body)` | `Node2D` | 一个**物理体**（`PhysicsBody2D`）或 `TileMap` 的形状进入本区域；要求本区域 `monitoring = true` |
| `body_exited(body)` | `Node2D` | 上述对象离开本区域 |
| `body_shape_entered(body_rid, body, body_shape_index, local_shape_index)` | 4 个 | 对方某个**具体形状**进入本区域的某个形状 |
| `body_shape_exited(...)` | 4 个 | 对方形状离开 |
| `area_entered(area)` | `Area2D` | 另一个 `Area2D` 进入本区域；要求本区域 `monitoring = true` |
| `area_exited(area)` | `Area2D` | 另一个 `Area2D` 离开 |
| `area_shape_entered(area_rid, area, area_shape_index, local_shape_index)` | 4 个 | 对方区域的具体形状进入 |
| `area_shape_exited(...)` | 4 个 | 对方区域的具体形状离开 |

三条容易踩的规则：

1. **`body_entered` 的对方可以是 `TileMap`**：`Area2D` 类参考明确写着 body 可以是 `PhysicsBody2D` 或 `TileMap`，前提是该 `TileMap` 的 `TileSet` 配了碰撞形状。
2. **形状级信号给的是索引，不是节点**：拿到 `body_shape_index` 后，用 `body.shape_find_owner(idx)` → `body.shape_owner_get_owner(owner)` 才能取到 `CollisionShape2D` 节点。
3. **`get_overlapping_bodies()` 不是即时结果**：4.3 类参考写明重叠列表"每个物理步更新一次"，而不是物体移动后立刻更新。**要精确就发信号，不要轮询。**

### 5.3 区域内的重力与阻尼覆盖

`Area2D` 不只是触发器，它还能在区域内**改写重力与阻尼**。覆盖方式由 `gravity_space_override` / `linear_damp_space_override` / `angular_damp_space_override` 决定，4.3 有 5 档（`Area2D.SpaceOverride`）：

| 常量 | 值 | 行为 |
|---|---|---|
| `SPACE_OVERRIDE_DISABLED` | 0 | 不影响重力/阻尼（纯检测区） |
| `SPACE_OVERRIDE_COMBINE` | 1 | 在已有结果上**叠加**自己的值（按 `priority` 顺序） |
| `SPACE_OVERRIDE_COMBINE_REPLACE` | 2 | 叠加自己的值，并**忽略更低优先级的区域** |
| `SPACE_OVERRIDE_REPLACE` | 3 | 完全**替换**重力/阻尼，忽略其他所有区域 |
| `SPACE_OVERRIDE_REPLACE_COMBINE` | 4 | 替换已算出的部分，其余区域继续参与计算 |

配套属性：`gravity`（强度，默认 `980.0`，单位是像素/秒²）、`gravity_direction`（默认 `(0, 1)`）、`gravity_point` / `gravity_point_center` / `gravity_point_unit_distance`（点重力，按距离平方反比衰减）、`priority`（区域处理顺序，越大越先）。

> 注意两处"重力"的量纲差异：节点 `Area2D.gravity` 默认 `980.0`（像素/秒²），而服务器层 `PhysicsServer2D.AREA_PARAM_GRAVITY` 的默认值是 `9.80665`（米制）。节点层已经把它换算成像素制了，用代码直接读服务器参数时记得做单位转换。

反过来，角色想知道"我现在受到的重力是多少"，应该问 `PhysicsBody2D.get_gravity()`——它返回的是**综合了所有 `Area2D` 覆盖之后的总重力矢量**（见 3.1 节），比手读 `physics/2d/default_gravity` 准确。

### 5.4 空间查询

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

### 6.1 `@export_flags_2d_physics` 与完整注解族

4.3 的 `@GDScript` 类参考里，用于导出位标志的注解共 8 个：

| 注解 | 用途 | 对应的项目设置分组 |
|---|---|---|
| `@export_flags` | 通用位标志（自定义字符串列表） | — |
| `@export_flags_2d_physics` | **2D 物理碰撞层** | `layer_names/2d_physics/layer_1 … layer_32` |
| `@export_flags_2d_render` | 2D 渲染层 | `layer_names/2d_render/layer_1 … layer_32` |
| `@export_flags_2d_navigation` | 2D 导航层 | `layer_names/2d_navigation/layer_1 … layer_32` |
| `@export_flags_3d_physics` | 3D 物理碰撞层 | `layer_names/3d_physics/layer_1 … layer_32` |
| `@export_flags_3d_render` | 3D 渲染层 | `layer_names/3d_render/layer_1 … layer_32` |
| `@export_flags_3d_navigation` | 3D 导航层 | `layer_names/3d_navigation/layer_1 … layer_32` |
| `@export_flags_avoidance` | 导航避障层 | `layer_names/avoidance/layer_1 … layer_32` |

每个 `*_flags_*` 注解都支持两种导出形态（4.3 类参考给了两组示例）：

```gdscript
# 形态一：单个 int（位掩码）
@export_flags_2d_physics var physics_layers: int = 1

# 形态二：Array[int]（一个 int 数组，每项是一个位掩码）
@export_flags_2d_physics var physics_layers_array: Array[int] = []
```

用 `Array[int]` 形态时，编辑器会给一个"层选择器"下拉框，比手写位运算友好得多。

### 6.2 位运算的正确写法

```gdscript
@export_flags_2d_physics var interact_layers: int = 1

func _ready() -> void:
    collision_layer = 1 << 1          # 我在第 2 层
    collision_mask = 1 | (1 << 2)     # 我检测第 1、3 层
```

三个必须记住的点：

1. **位序号从 0 开始，层号从 1 开始**。第 N 层对应 `1 << (N - 1)`。写 `1 << 2` 是"第 3 层"，不是"第 2 层"。编辑器里显示的层号是 1–32。
2. **`collision_layer` 是"我在哪"，`collision_mask` 是"我找谁"**。A 能与 B 碰撞，当且仅当 `A.collision_mask & B.collision_layer != 0`。**两个方向都要检查**——只检查单向是最常见的"明明设了层却不碰"的原因。
3. **不要用十进制硬编码层号**。`collision_layer = 2` 指的是第 2 层（即位 1），而不是"2 号位"；用 `1 << n` 并配好 `layer_names/2d_physics/layer_N` 命名，改层时才不会全盘返工。

层命名在项目设置 `layer_names/2d_physics/layer_1 … layer_32`。收窄 mask 是 2D 物理优化的第一优先级——宽相位配对越少，窄相位与求解器负担越小（结论与第 32 篇一致）。

---

## 七、性能优化

### 7.1 物理插值：2D 与 3D 的版本分界

物理插值把"物理步"与"渲染帧"解耦，在两次物理步之间插值出渲染位置，消除抖动。

| 维度 | 2D | 3D |
|---|---|---|
| 支持起始版本 | **4.3** | **4.4** |
| 项目设置 | `physics/common/physics_interpolation`（4.3 起，两种维度共用一个开关） | 同左 |
| 节点级覆盖 | `CanvasItem.physics_interpolation_mode` | `Node3D.physics_interpolation_mode` |

> 依据：Godot 4.4 官方发布页在"3D physics interpolation"一节写明——"With Godot 4.3, we introduced physics interpolation for your 2D projects. In this release, the long-awaited 3D counterpart has been merged as well!"。即 **2D 是 4.3 引入、3D 是 4.4 引入**。

启用方式：

```gdscript
# 项目级：项目设置 → 物理 → 通用 → Physics Interpolation
# 或代码：
ProjectSettings.set_setting("physics/common/physics_interpolation", true)
```

配套的相关设置（4.4 `ProjectSettings.xml` 逐项核实）：

| 设置键 | 默认 | 作用 |
|---|---|---|
| `physics/common/physics_interpolation` | `false` | 总开关 |
| `physics/common/physics_jitter_fix` | `0.5` | 插值时向"上一物理位置"偏移的比例，用于消除运动模糊类残影；`0` = 纯插值，`1` = 完全不插值 |
| `physics/common/physics_ticks_per_second` | `60` | 物理频率 |
| `physics/common/max_physics_steps_per_frame` | `8` | 单帧最多补跑的物理步数 |

节点级覆盖用于"某些物体不插值"：

```gdscript
extends Node2D

func _ready() -> void:
	# 该节点的插值模式：继承 / 开 / 关
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
```

### 7.2 TileMapLayer 的物理层

4.3 起 2D 瓦片地图拆成了 `TileMapLayer`（每个节点只管一层瓦片），旧的 `TileMap` 节点在 4.3 被**标记为 deprecated**（类参考原文："Unlike the TileMap node, which is deprecated, TileMapLayer has only one layer of tiles"）。两者都能承载物理，区别在工程结构：

| 维度 | `TileMap`（4.3 已废弃） | `TileMapLayer`（4.3 起推荐） |
|---|---|---|
| 层数 | 一个节点含多层 | 一个节点 = 一层，多层用多个节点 |
| 物理 | 每层瓦片可各自带碰撞形状 | 同左，但可整层开关 |
| 整层开关碰撞 | 需要遍历内部结构 | `collision_enabled`（默认 `true`）一个属性搞定 |
| 动态平台 | 需自行改造 | `use_kinematic_bodies`（默认 `false`）可把碰撞体建成运动学体 |
| 调试可见性 | 受全局调试开关控制 | `collision_visibility_mode` 可按层强制显示/隐藏 |
| 编辑器更新 | 帧末批量 | 帧末批量；`update_internals()` 可强制立即更新 |

物理相关的关键属性（4.3 逐项核实）：

| 属性 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `collision_enabled` | `bool` | `true` | 关掉后整层不参与碰撞（比逐格处理快得多） |
| `use_kinematic_bodies` | `bool` | `false` | `true` 时碰撞体实例化为运动学体，**移动 `TileMapLayer`（如移动平台）时才需要** |
| `collision_visibility_mode` | `int` | `0`（`DEBUG_VISIBILITY_MODE_DEFAULT`） | `DEFAULT` / `FORCE_SHOW` / `FORCE_HIDE` |
| `enabled` | `bool` | `true` | 关掉后渲染、碰撞、导航、场景瓦片全部停用 |
| `navigation_enabled` | `bool` | `true` | 导航区域开关 |

**逐格碰撞体合并**是 2D 地图物理的核心优化点：瓦片的碰撞形状定义在 `TileSet` 里（`TileData` 的多边形），引擎会为整张地图生成**少量虚拟静态体**，而不是"每格一个 `StaticBody2D`"：

- 一张地图 ≈ 1~几个内部体，而不是"1000 格 = 1000 个刚体节点"；
- 逐格放置 `StaticBody2D` 是最常见的 2D 物理性能事故：节点数、变换通知、场景树开销全部爆炸；
- 需要"玩家踩到了哪一格"时，用 `TileMapLayer.get_coords_for_body_rid(body_rid)` 从碰撞体的 RID 反查瓦片坐标（先用 `has_body_rid(body_rid)` 判断归属）。

```gdscript
# 玩家踩到瓦片上时，反查是哪一格（4.3 TileMapLayer API）
extends CharacterBody2D

func _physics_process(_delta: float) -> void:
	move_and_slide()
	var collision := get_last_slide_collision()
	if collision == null:
		return
	var body_rid := collision.get_collider_rid()
	var tile_layer := $TileMapLayer
	if tile_layer.has_body_rid(body_rid):
		var coords := tile_layer.get_coords_for_body_rid(body_rid)
		print("踩到了格子：", coords)
```

> `TileMapLayer` 的更新是**帧末批量**的（类参考原文："all TileMap updates are batched at the end of a frame"）。如果同一帧里改格子又立刻读格子，可能读到旧值；需要立即生效时调用 `update_internals()`（类参考同时提醒：这个调用"computationally expensive"，别每帧调）。

### 7.3 其他性能要点

- **形状选型**：圆/矩形/胶囊优先，多边形只用于轮廓必要处；
- **休眠**：静止的 `RigidBody2D` 自动休眠，不要每帧给它微小扰动（`can_sleep` 默认开启）；
- **`collision_mask` 收窄**：见 6.2；
- **形状数量**：一个 `CollisionShape2D` 只承载一个形状，复合形状用多个节点；
- **物理插值**：见 7.1。

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

2D 物理与 3D 共享同一套设计语言，但类型独立、源码独立（`modules/godot_physics_2d/` vs `modules/godot_physics_3d/`）：

- **选型**：`CharacterBody2D` 驱动角色、`RigidBody2D` 做力学响应、`StaticBody2D`/`AnimatableBody2D` 做场景碰撞、`Area2D` 做事件区
- **手感**：土狼时间 + 跳跃缓冲 + 可变跳跃是 2D 角色的标准三件套；运动参数见 3.5 调参表
- **方向性**：`monitoring` 管输出、`monitorable` 管输入——搞反就是"信号不触发"的第一原因
- **查询**：持续监测用 `RayCast2D`/`ShapeCast2D`，一次性判定用 `direct_space_state`
- **状态**：`PhysicsDirectBodyState2D` 是改写刚体状态的唯一入口，注意"力 vs 冲量"的区别
- **性能**：收窄 mask、控制形状数量、瓦片碰撞交给 `TileMapLayer`、开启物理插值（2D 自 4.3 起）

三条最容易记错的 API：

| 错误写法 | 正确写法 | 后果 |
|---|---|---|
| `state.get_velocity()` | `state.get_linear_velocity()` | `Nonexistent function 'get_velocity'` |
| `wall_stop_slide = true` | 用 `floor_block_on_wall` / `floor_stop_on_slope` / `slide_on_ceiling` | `Invalid set index 'wall_stop_slide'` |
| 关 `monitoring` 来"不被检测" | 关 `monitorable` | 自己的信号反而不触发 |

---

## 🔗 延伸阅读

- **CharacterBody2D**: <https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html>
- **RigidBody2D**: <https://docs.godotengine.org/en/stable/classes/class_rigidbody2d.html>
- **PhysicsDirectBodyState2D**: <https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate2d.html>
- **PhysicsDirectSpaceState2D**: <https://docs.godotengine.org/en/stable/classes/class_physicsdirectspacestate2d.html>
- **PhysicsServer2D**: <https://docs.godotengine.org/en/stable/classes/class_physicsserver2d.html>
- **Area2D**: <https://docs.godotengine.org/en/stable/classes/class_area2d.html>
- **TileMapLayer**: <https://docs.godotengine.org/en/stable/classes/class_tilemaplayer.html>
- **AnimatableBody2D**: <https://docs.godotengine.org/en/stable/classes/class_animatablebody2d.html>
- **源码位置**: `modules/godot_physics_2d/`（`godot_broad_phase_2d.h`、`godot_collision_solver_2d.h`、`godot_body_pair_2d.cpp`）、`scene/2d/physics/`

---

## 📋 下一章预告

**第 34 篇：Jolt Physics**

- Jolt 是什么、4.4 起的内置化与 4.6 的默认化
- 编译开关与启用方式
- 与 Godot Physics 的逐项行为差异对照（含版本标注）
- `physics/jolt_physics_3d/*` 项目设置的真实键名
- `PhysicsServer3DExtension`：第三方物理后端的接入点
- 迁移检查清单

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 32 篇：物理性能优化](/articles/32-physics-performance-optimization.md)
**下一篇**: [第 34 篇：Jolt Physics](/articles/34-jolt-physics.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
