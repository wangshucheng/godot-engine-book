# 第 38 篇：动画控制器

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 37 章 动画系统基础  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

前一章讲了动画系统的地基。本章讲**驱动层**：已经有一棵配置好的动画树之后，**从脚本如何正确地驱动它**。

这一层包括三件事：

1. `AnimationTree` 与 `AnimationPlayer` 的职责边界（官方文档对此有明确告诫）
2. 参数路径字典规范——`parameters/...` 到底怎么拼、怎么读写
3. `AnimationMixer` 这个 4.x 抽象基层的正确用法（含 3.x → 4.x 迁移）

> **本卷分工**：状态机的**构建**与 transition 属性详见第 43 篇；混合树与混合空间的**构建**详见第 39 篇。
> 本章只讲"如何从脚本驱动一棵已配置好的状态机 / 混合树"，不重复讲解节点本身。

---

## 🎯 学习目标

- 理解 `AnimationTree` 与 `AnimationPlayer` 的职责边界
- 掌握 `parameters/...` 参数路径的书写规范
- 掌握条件（condition）与表达式（expression）两种驱动方式
- 掌握 `AnimationNodeStateMachinePlayback` 的运行时控制接口
- 掌握 `AnimationMixer` 的正确用法与手动驱动
- 理解动画层与输入层 / AI 层的接口设计

---

## 1. 驱动层的职责

### 1.1 官方告诫：AnimationPlayer 只用于增删改动画

`AnimationTree` 的官方类参考里写得很直白：

> When linked with an `AnimationPlayer`, several properties and methods of the corresponding
> `AnimationPlayer` will not function as expected. Playback and transitions should be handled
> using only the `AnimationTree` and its constituent `AnimationNode`(s).
> **The `AnimationPlayer` node should be used solely for adding, deleting, and editing animations.**

翻译过来：

| 节点 | 该做什么 | 不该做什么 |
|---|---|---|
| `AnimationPlayer` | 添加 / 删除 / 编辑动画资源 | 在 `AnimationTree` 接管后仍去 `play()` / `seek()` 驱动播放 |
| `AnimationTree` | 驱动播放、混合、状态切换 | —— |

同一场景里同时用两套驱动，会出现"两套系统抢同一批属性"的经典抖动：脚本刚 `play("walk")`，
下一帧 `AnimationTree` 又按自己的状态机把骨骼写回 `idle` 的姿势。

**正确姿势**：动画树接管之后，需要切换到别的动画时，**切状态 / 切参数**，而不是直接 `player.play()`。

```gdscript
# 接管后要播别的动画：切状态，而不是直接操作 AnimationPlayer
var playback := $AnimationTree.get("parameters/playback") as AnimationNodeStateMachinePlayback
playback.travel("attack")     # 让状态机去做过渡
```

### 1.2 驱动层的三层结构

```
游戏逻辑层（输入 / AI / 战斗）
        │  写入参数、调用 travel()
        ▼
驱动层（本章）
        │  AnimationTree  ── 参数路径 parameters/...
        │  AnimationNodeStateMachinePlayback
        ▼
资源层
           AnimationLibrary ── Animation ── 轨道 / 关键帧
```

驱动层的职责边界是：**把游戏逻辑翻译成"参数 + 状态"**，而不是翻译成"逐帧姿势"。

---

## 2. AnimationTree

### 2.1 正确配置 AnimationTree

```gdscript
# 基础 AnimationTree：脚本只负责装配资源，不重新声明引擎已有成员
class_name BasicAnimationTree

extends AnimationTree

# 注意：tree_root 是 AnimationTree 的原生属性（类型 AnimationRootNode），
# 在子类里重新声明会报 `Member "tree_root" redefined (original in native class 'AnimationTree')`，
# 脚本将无法加载。这里改用 root_res 作为导出名，再赋给 tree_root。
@export var animation_player: AnimationPlayer
@export var root_res: AnimationRootNode

func _ready():
    # 设置动画播放器（anim_player 是 NodePath 属性）
    if animation_player:
        anim_player = get_path_to(animation_player)

    # 设置根节点
    if root_res:
        tree_root = root_res

func play_animation(anim_name: StringName):
    # has_animation() 定义在 AnimationMixer 上，AnimationTree 继承了它
    if has_animation(anim_name):
        get_node(anim_player).play(anim_name)

func stop_animation():
    get_node(anim_player).stop()
```

> ⚠️ `extends AnimationTree` 时 **不要** 用 `@export var tree_root: AnimationRootNode` 覆盖原生成员。
> GDScript 在**解析期**就会报 `Member "tree_root" redefined`，整个脚本加载失败（不是运行时才报错）。
> 正确做法是用另一个名字（这里叫 `root_res`）导出资源，再在 `_ready()` 里赋值给 `tree_root`。

### 2.2 AnimationTree 参数：参数路径字典规范

`AnimationTree` **没有** `set_parameter()` / `get_parameter()` 这样的专用方法。
所有参数都通过 `Object.set()` / `Object.get()` 按**属性路径**读写。路径规则如下：

```
参数路径规则
──────────────────────────────────────────────────────────
树根节点自身的参数          parameters/<参数名>
  例：1D 混合空间           parameters/blend_position
  例：状态机 playback       parameters/playback

混合树内某个节点的参数      parameters/<节点名>/<参数名>
  例：Blend2 的混合量       parameters/locomotion/blend_amount
  例：Blend2 的两个混合量   parameters/upper_body/blend_amount
  例：TimeScale 的缩放      parameters/time_scale/scale
  例：OneShot 的请求        parameters/OneShot/request

状态机条件（advance_condition） parameters/conditions/<条件名>
  例：                      parameters/conditions/is_moving
──────────────────────────────────────────────────────────
```

**节点名来自哪里**：在 AnimationTree 编辑器里选中节点，节点标题就是路径里的 `<节点名>`；
也可以在运行时读 `AnimationTree.get_property_list()` 拿到全部参数路径。

```gdscript
# AnimationTree 的参数没有专用方法，统一用属性路径读写
class_name AnimationTreeParameters

extends Node

@export var tree: AnimationTree
@export var node_name: StringName = &"locomotion"

func _ready() -> void:
    set_blend_position(0.0)

# 路径规则：
#   树根节点的参数 → parameters/<参数名>
#   混合树内某节点的参数 → parameters/<节点名>/<参数名>
func set_blend_position(value: float) -> void:
    tree.set("parameters/%s/blend_position" % node_name, value)

func get_blend_position() -> float:
    return float(tree.get("parameters/%s/blend_position" % node_name))

func _process(_delta: float) -> void:
    var body := $CharacterBody2D as CharacterBody2D
    set_blend_position(body.velocity.length())
```

> **与第 39 / 43 篇保持一致**：本卷统一使用 `tree.set("parameters/...", value)`。
> `tree.set_condition()` 与 `tree.set_parameter()` **都不存在**。

### 2.3 条件与表达式驱动

状态机的过渡条件写在 `AnimationNodeStateMachineTransition.advance_condition` 里，
它只是一个**字符串名字**；真正的布尔值挂载在 `AnimationTree` 的
`parameters/conditions/<名字>` 路径上：

```gdscript
# 用条件参数驱动状态切换（与第 43 篇写法一致）
class_name AnimationTreeConditionDriver

extends Node

@export var tree: AnimationTree
@export var condition_name: StringName = &"can_walk"

func _physics_process(_delta: float) -> void:
    var body := $CharacterBody2D as CharacterBody2D
    # 条件只能通过属性路径写入，没有 set_condition() 方法
    tree.set("parameters/conditions/%s" % condition_name, body.velocity.length() > 0.5)
```

除了布尔条件，`AnimationNodeStateMachineTransition` 还有 **`advance_expression`**（4.x 新增），
可以写一段表达式直接求值。表达式的求值基准节点由
`AnimationTree.advance_expression_base_node` 指定（默认 `"."`）。

两种方式的取舍：

| 方式 | 字段 | 适用 |
|---|---|---|
| 布尔条件 | `advance_condition` | 简单开关，脚本每帧写一个 bool |
| 表达式 | `advance_expression` | 组合条件，减少每帧的脚本写入量 |

> 表达式是 4.x 才有的字段；3.x 的状态机只有 `advance_condition`。

---

## 3. 状态切换编排

本章只讲"如何从脚本驱动一棵**已配置好的**状态机"。状态节点、`add_transition`、
`switch_mode` / `xfade_time` 等 transition 属性本身见第 43 篇。

### 3.1 取到 playback 对象

```gdscript
# 取到状态机的运行时控制器
var playback := $AnimationTree.get("parameters/playback") as AnimationNodeStateMachinePlayback
```

`parameters/playback` 是 `AnimationTree` 在状态机根节点下自动暴露的参数。
`AnimationNodeStateMachinePlayback` 的完整接口（4.3 官方类参考）：

| 方法 | 说明 |
|---|---|
| `travel(to_node, reset_on_teleport = true)` | 沿最短路径（A\*）前往目标状态 |
| `start(node, reset = true)` | 立即开始播放指定状态，不走过渡 |
| `next()` | 若存在 travel / auto advance 的下一路径，立刻切到下一状态 |
| `stop()` | 停止当前状态机 |
| `is_playing()` | 是否正在播放 |
| `get_current_node()` | 当前状态名 |
| `get_current_play_position()` | 当前状态内的播放位置（秒） |
| `get_current_length()` | 当前状态的长度（秒） |
| `get_fading_from_node()` | 正在淡出的源状态名 |
| `get_travel_path()` | A\* 算法算出的当前旅行路径（`StringName[]`） |

### 3.2 切换与查询

```gdscript
# 用 travel() 走最短路径，用 start() 硬切
class_name StateMachineDriver

extends Node

@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback

func _ready() -> void:
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback

func travel_to(state_name: StringName) -> void:
    playback.travel(state_name)

func hard_cut_to(state_name: StringName) -> void:
    # 跳过过渡直接进入目标状态
    playback.start(state_name, true)

func current_state() -> StringName:
    return playback.get_current_node()

func is_fading_from(state_name: StringName) -> bool:
    return playback.get_fading_from_node() == state_name

func pending_path() -> PackedStringArray:
    # travel 途中可以查询即将经过的状态序列
    return PackedStringArray(playback.get_travel_path())
```

> **`travel()` 属于 `AnimationNodeStateMachinePlayback`，不属于 `AnimationTree`。**
> `animation_tree.travel("run")` 会报 `Invalid call. Nonexistent function 'travel' in base 'AnimationTree'`。
> 正确写法：`animation_tree.get("parameters/playback").travel("run")`。

### 3.3 状态切换没有信号

状态机**没有** "状态变了" 的信号（`AnimationNodeStateMachinePlayback` 只有上表那些方法）。
常规做法是轮询 `get_current_node()`：

```gdscript
# 轮询当前状态，检测变化
func _process(_delta: float) -> void:
    var current := playback.get_current_node()
    if current != _last_state:
        _last_state = current
        _on_state_changed(current)

func _on_state_changed(state_name: StringName) -> void:
    print("State changed to: ", state_name)
```

---

## 4. 动画事件与状态编排

### 4.1 用 `animation_finished` 串起状态

`AnimationMixer.animation_finished(anim_name: StringName)` 在动画播完时触发。
状态机里的状态通常对应一条动画，因此可以在动画结束时做"收尾"工作：

```gdscript
# 动画播完后的收尾编排
class_name AnimationFinishOrchestrator

extends Node

@export var tree: AnimationTree
@export var player: AnimationPlayer

var playback: AnimationNodeStateMachinePlayback

func _ready() -> void:
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    # 参数类型是 StringName
    player.animation_finished.connect(_on_animation_finished)

func _on_animation_finished(anim_name: StringName) -> void:
    match anim_name:
        &"attack":
            # 攻击结束 → 交回移动状态
            playback.travel("idle")
        &"death":
            player.stop()
```

> **循环动画不会触发 `animation_finished`**（官方类参考明确说明）。
> 所以"等待 idle 播完再切走"这种逻辑对循环动画无效。

### 4.2 `queue()`：排队播下一条

```gdscript
# 用 queue() 串接动画
func play_sequence() -> void:
    player.play(&"walk")
    player.queue(&"idle")
```

`queue()` 的语义（`AnimationPlayer` 官方类参考）：等当前动画**以及此前排队的动画**都播完后播放目标动画。
若当前动画在循环，排队动画永远不会播放，除非循环被停止。

### 4.3 `AnimationNodeOneShot` 的一次性播放

状态机之外，"攻击 / 受击 / 吟唱"这类一次性动作通常用 `AnimationNodeOneShot`：

```gdscript
# 触发一次性动画
func fire_one_shot() -> void:
    tree.set("parameters/OneShot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)

func abort_one_shot() -> void:
    tree.set("parameters/OneShot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)

func is_one_shot_active() -> bool:
    return bool(tree.get("parameters/OneShot/active"))
```

`request` 在下一次 process 帧会被引擎自动清回 `ONE_SHOT_REQUEST_NONE`，所以每帧重复写 `FIRE` 不会连发。

---

## 5. AnimationMixer 的正确用法

### 5.1 基类关系

```
AnimationMixer  ←  AnimationPlayer
      ↑
AnimationTree
```

`AnimationMixer` 是 `AnimationPlayer` 与 `AnimationTree` 的**共同基类**，负责动画列表管理、
播放推进与混合计算。**不要为了"混合"去继承 `AnimationMixer`**——它是引擎内部的混合实现，
官方描述是 "Base class for AnimationPlayer and AnimationTree to manage animation lists"。

```gdscript
# AnimationMixer 是 AnimationPlayer 与 AnimationTree 的共同基类
class_name AnimMixerNotes

extends Node

@export var player: AnimationPlayer
@export var tree: AnimationTree

# 直接播放单个动画：走 AnimationPlayer，名字可以是 "库名/动画名"
func play_direct(anim_name: StringName) -> void:
    if player and player.has_animation(anim_name):
        player.play(anim_name)

# 需要真正混合时改用 AnimationTree
func travel(state_name: StringName) -> void:
    var playback := tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    if playback:
        playback.travel(state_name)

# current_animation 由 AnimationMixer 提供，两者通用
func current_animation() -> StringName:
    return player.current_animation if player else &""

func stop_animation():
    if player:
        player.stop()
```

### 5.2 动画库与 `root_node`

```gdscript
# AnimationMixer 提供的两项通用能力：root_node 与动画库
class_name AnimMixerBasics

extends Node

@export var mixer: AnimationMixer

func _ready() -> void:
    # 1) root_node 是轨道路径的解析起点，轨道路径形如 "Skeleton3D:Root"
    if mixer.root_node.is_empty():
        mixer.root_node = mixer.get_path_to(mixer.get_parent())

    # 2) 动画按「库」组织（Godot 4 起取代了 3.x 的扁平动画列表），
    #    库名为空字符串时是默认库，播放时可直接用 "idle"
    var lib := AnimationLibrary.new()
    var anim := Animation.new()
    anim.length = 1.0
    lib.add_animation(&"idle", anim)
    mixer.add_animation_library(&"", lib)

    print("当前动画：%s" % mixer.current_animation)
```

**动画键名规则**（`AnimationPlayer` 官方类参考）：

```
"库名/动画名"      例如 "movement/run"
"动画名"            默认库（键名为空字符串）时省略前导斜杠
```

因此 `player.play("run")` 与 `player.play("movement/run")` 是两种不同的动画，
写错库名会静默播放失败（`has_animation()` 返回 false）。

### 5.3 手动驱动

`AnimationMixer` 提供两个成员配合手动驱动：

| 成员 | 作用 |
|---|---|
| `callback_mode_process` | 设为 `ANIMATION_CALLBACK_MODE_PROCESS_MANUAL` 后，引擎不再自动推进动画 |
| `advance(delta)` | 手动推进指定秒数 |

`AnimationMixer` **没有** `process()` 方法——在 `extends AnimationTree` 的脚本里写
`func _process(delta): process(delta)` 会在运行时报
`Invalid call. Nonexistent function 'process' in base 'AnimationTree'`。

最小示例见第 37 篇第 3.2 节；本章第 7.2 节给出固定步长（与物理步对齐）的工程写法。

### 5.4 离散属性的插值策略

多个动画混合时，`Animation.UPDATE_DISCRETE` 轨道（整数、布尔、枚举等）的取值可能冲突。
`AnimationMixer.callback_mode_discrete` 决定冲突时听谁的：

| 常量 | 行为 |
|---|---|
| `ANIMATION_CALLBACK_MODE_DISCRETE_DOMINANT` | 离散轨道的值优先 |
| `ANIMATION_CALLBACK_MODE_DISCRETE_RECESSIVE` | 连续 / capture 轨道的值优先（`AnimationPlayer` 默认） |
| `ANIMATION_CALLBACK_MODE_DISCRETE_FORCE_CONTINUOUS` | 把离散轨道当作 `INTERPOLATION_NEAREST` 的连续轨道，每帧都更新（`AnimationTree` 默认，混合时最不易出现跳变） |

### 5.5 `active` 开关与不可见角色的停机方式

`AnimationMixer.active` 为 `false` 时不再推进动画。但要注意：
**停机后姿势会"回弹"**——因为引擎不再写入任何值，被动画驱动的属性会保持上一次写入的值，
而不是回到静止姿势；若属性同时被其它逻辑（如物理）驱动，则会跳到那个逻辑的值。

正确的停机方式：

```gdscript
# 不可见角色的正确停机方式
class_name MixerLODController

extends Node

@export var mixer: AnimationMixer

func set_visible_active(is_visible: bool) -> void:
    if is_visible:
        mixer.active = true
    else:
        # 先停，再把姿势显式写回静止值，避免"回弹"
        mixer.active = false
        mixer.advance(0.0)
```

---

## 6. 与输入层 / AI 层的接口

驱动层不直接读输入，也不直接跑 AI；它只接收"语义化的状态量"。
推荐把"游戏逻辑量"与"动画参数"之间加一层转换，避免物理量直接污染动画树：

```gdscript
# 输入层 / AI 层 → 驱动层的接口
class_name AnimationIntent

extends Node

@export var tree: AnimationTree
@export var player: AnimationPlayer

## 由输入层或 AI 层每帧写入
@export var intent_move_speed: float = 0.0
@export var intent_move_direction: Vector2 = Vector2.ZERO
@export var intent_is_grounded: bool = true
@export var intent_wants_attack: bool = false

func _physics_process(_delta: float) -> void:
    # 1) 连续量 → 混合参数
    tree.set("parameters/locomotion/blend_position", intent_move_speed)
    tree.set("parameters/locomotion/blend_direction", intent_move_direction)

    # 2) 离散量 → 条件参数
    tree.set("parameters/conditions/is_grounded", intent_is_grounded)
    tree.set("parameters/conditions/wants_attack", intent_wants_attack)
```

这样做的收益：

- 输入层改键位 / 改 AI 策略时，动画树不用动
- 动画参数可以直接被 AnimationPlayer 反向驱动（参数本身也是属性）
- 便于录制 / 回放 / 联机同步（只同步 intent，不同步姿势）

---

## 7. 实践：驱动层

> 本章的实践章节只演示**驱动层**本身。
> `AnimationPlayer` / `Skeleton3D` / `AnimatedSprite2D` 的基础用法见第 37 篇；
> 状态机的构建与 transition 属性见第 43 篇；混合树见第 39 篇。

### 7.1 角色动画驱动器（输入 → 参数 → 状态机）

```gdscript
# 角色动画驱动器：把游戏逻辑翻译成"参数 + 状态"
class_name CharacterAnimationDriver

extends Node3D

@export var tree: AnimationTree
@export var body: CharacterBody3D

var playback: AnimationNodeStateMachinePlayback
var _last_state: StringName

func _ready() -> void:
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    playback.travel(&"Idle")

func _physics_process(_delta: float) -> void:
    _drive_continuous_parameters()
    _drive_conditions()
    _drive_state()

# 1) 连续量 → 混合参数
func _drive_continuous_parameters() -> void:
    var speed := body.velocity.length()
    tree.set("parameters/locomotion/blend_position", speed)

# 2) 离散量 → 条件参数（没有 set_condition() 这种方法）
func _drive_conditions() -> void:
    tree.set("parameters/conditions/is_grounded", body.is_on_floor())
    tree.set("parameters/conditions/is_moving", body.velocity.length() > 0.1)

# 3) 状态切换：状态机没有"状态变了"的信号，靠轮询
func _drive_state() -> void:
    var current := playback.get_current_node()
    if current != _last_state:
        _last_state = current
        on_state_changed(current)

func on_state_changed(state_name: StringName) -> void:
    print("State changed to: ", state_name)

# 一次性动作走 OneShot，不要去抢 AnimationPlayer
func fire_one_shot() -> void:
    tree.set("parameters/OneShot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
```

### 7.2 手动驱动的角色（固定步长 / 回放）

需要让动画跟着自己的时钟走（网络回放、录像、确定性模拟）时，
把 `AnimationMixer` 切到手动模式：

```gdscript
# 手动驱动的角色：动画由外部时钟按固定步长推进
class_name ManualDriveCharacterAnimator

extends Node3D

@export var mixer: AnimationMixer
@export var fixed_step: float = 1.0 / 60.0

var _accumulator: float = 0.0

func enable_manual_mode() -> void:
    # 关闭引擎自动推进（手动驱动的开关说明见第 37 篇第 3.2 节）
    mixer.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL

func advance(delta: float) -> void:
    # 固定步长累加，保证与物理步一致
    _accumulator += delta
    while _accumulator >= fixed_step:
        # AnimationMixer 没有 process()，手动推进用 advance()
        mixer.advance(fixed_step)
        _accumulator -= fixed_step
```

### 7.3 动画事件与状态编排

```gdscript
# 动画事件编排：把"动画播完"翻译成"状态切换"
class_name AnimationEventOrchestrator

extends Node

@export var tree: AnimationTree
@export var player: AnimationPlayer

var playback: AnimationNodeStateMachinePlayback

func setup() -> void:
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    # 参数类型是 StringName
    player.animation_finished.connect(_on_animation_finished)

func _on_animation_finished(anim_name: StringName) -> void:
    match anim_name:
        &"attack":
            playback.travel(&"idle")
        &"death":
            player.stop()
```

> `queue()` 串接动画的写法见第 37 篇第 4.1 节；
> 本节关注的是"动画结束 → 状态切换"这一层编排。
> 注意：**循环动画不会触发 `animation_finished`**，
> 所以"等 idle 播完再切走"这类逻辑对循环动画无效。

---

## 📝 本章总结

### 核心要点

1. **AnimationTree 接管后，AnimationPlayer 只用于增删改动画**
2. **参数一律走 `parameters/...` 属性路径**，没有 `set_condition()` / `set_parameter()`
3. **条件写 `parameters/conditions/<名字>`**，与第 43 篇写法一致
4. **`travel()` 属于 `AnimationNodeStateMachinePlayback`**，不是 `AnimationTree`
5. **`AnimationMixer` 是两者的共同基类**；手动驱动用 `advance()` + `callback_mode_process = MANUAL`
6. **动画键名遵循 `"库名/动画名"`**
7. **状态切换没有信号**，靠轮询 `get_current_node()`

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationTree | 动画树，基于节点的动画控制器 |
| AnimationMixer | 动画混合器，`AnimationPlayer` 与 `AnimationTree` 的共同基类 |
| 参数路径 | `parameters/<节点名>/<参数名>` 形式的属性路径 |
| advance_condition | 过渡上的布尔条件名（写入 `parameters/conditions/<名字>`） |
| advance_expression | 4.x 新增的过渡表达式 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档 · Using AnimationTree**: <https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html>
- **官方文档 · AnimationTree**: <https://docs.godotengine.org/en/stable/classes/class_animationtree.html>
- **官方文档 · AnimationMixer**: <https://docs.godotengine.org/en/stable/classes/class_animationmixer.html>
- **官方文档 · AnimationPlayer**: <https://docs.godotengine.org/en/stable/classes/class_animationplayer.html>
- **官方文档 · AnimationNodeStateMachinePlayback**: <https://docs.godotengine.org/en/stable/classes/class_animationnodestatemachineplayback.html>
- **官方文档 · AnimationNodeOneShot**: <https://docs.godotengine.org/en/stable/classes/class_animationnodeoneshot.html>
- **源码位置**: `scene/animation/`（`animation_tree.cpp`、`animation_mixer.cpp`、`animation_player.cpp`、
  `animation_node_state_machine.cpp`）、`scene/resources/animation_library.cpp`

> **注意**：Godot 4.3 的 `servers/` 目录下没有 `animation/` 子目录；动画实现全部位于 `scene/animation/`。

---

## 📋 上下篇导航

**上一篇**: [第 37 篇：动画系统基础](/articles/37-animation-system-basics.md)
**下一篇**: [第 39 篇：动画混合](/articles/39-animation-blending.md)

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

*写作时间：2026-03-20*  
*字数：约 2,200 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
