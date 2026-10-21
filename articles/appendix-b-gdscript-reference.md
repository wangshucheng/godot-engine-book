# 附录 B：GDScript 快速参考

## 📖 语法速查表

### 基础语法

```gdscript
# 变量声明
var name: String = "Godot"
var age: int = 5
var pi: float = 3.14159
var is_active: bool = true

# 常量
const MAX_SPEED = 100
enum State { IDLE, RUNNING, JUMPING }

# 数组和字典
var arr: Array[int] = [1, 2, 3]
var dict: Dictionary = {"key": "value", "num": 42}

# 类型转换
var num_str: String = str(42)
var num_int: int = int("42")
var num_float: float = float("3.14")
```

### 控制流程

```gdscript
# 条件语句
if health <= 0:
    die()
elif health < 30:
    play_low_health_sound()
else:
    pass

# 匹配语句（switch）
match state:
    State.IDLE:
        idle_animation()
    State.RUNNING:
        run_animation()
    State.JUMPING:
        jump_animation()
    _:
        pass

# 循环
for i in range(10):
    print(i)

for item in inventory:
    item.use()

for key in dict:
    print(key, dict[key])

while is_playing:
    await get_tree().physics_frame  # 4.x 用 await 等待信号
```

### 函数

```gdscript
# 函数定义
func add(a: int, b: int) -> int:
    return a + b

# 默认参数
func greet(name: String = "Player") -> void:
    print("Hello, ", name)

# 可变参数
func sum_all(numbers: Array[int]) -> int:
    var total = 0
    for n in numbers:
        total += n
    return total

# Lambda 表达式
var double = func(x): return x * 2
var result = double.call(5)
```

### 信号

```gdscript
# 定义信号
signal health_changed(new_value)
signal player_died

# 发射信号
emit_signal("health_changed", 50)
player_died.emit()

# 连接信号
health_changed.connect(_on_health_changed)

# 断开信号
health_changed.disconnect(_on_health_changed)

# 回调函数
func _on_health_changed(new_value):
    update_health_bar(new_value)
```

### 类与继承

```gdscript
# 类定义
class_name Player
extends CharacterBody2D

@export var speed: float = 200.0
@onready var sprite = $Sprite2D

# 构造函数
func _init():
    print("Player created")

# 虚函数
func _ready():
    pass

func _process(delta: float):
    pass

func _physics_process(delta: float):
    pass

# 继承
class Warrior:
    extends Player
    
    func attack():
        print("Warrior attacks!")
```

### 数学与向量

```gdscript
# 向量运算
var v1 = Vector2(1, 2)
var v2 = Vector2(3, 4)

var sum = v1 + v2
var dot = v1.dot(v2)
var cross = v1.cross(v2)
var length = v1.length()
var normalized = v1.normalized()
var angle = v1.angle()
var rotated = v1.rotated(PI / 4)

# 插值
var pos = lerp(start, end, 0.5)
var target_angle = lerp_angle(from, to, 0.1)

# 三角函数
var sin_val = sin(PI / 6)
var cos_val = cos(PI / 6)
var tan_val = tan(PI / 4)
var atan2_val = atan2(y, x)
```

### 字符串

```gdscript
# 字符串操作
var text = "Hello, Godot!"
var len = text.length()
var sub = text.substr(0, 5)  # "Hello"
var upper = text.to_upper()  # "HELLO, GODOT!"
var lower = text.to_lower()  # "hello, godot!"
var replaced = text.replace("Godot", "World")

# 格式化
var name = "Player"
var score = 100
var msg = "%s scored %d points" % [name, score]
var msg2 = "{0} scored {1} points".format([name, score])

# 分割与连接
var parts = "a,b,c".split(",")  # ["a", "b", "c"]
var joined = parts.join("-")    # "a-b-c"
```

### 时间与日期

```gdscript
# 时间获取
var unix_time = Time.get_unix_time_from_system()
var datetime = Time.get_datetime_dict_from_system()
var string = Time.get_datetime_string_from_system()

# 格式化
var formatted = Time.get_datetime_string_from_unix_time(unix_time)

# 计时器
var timer = get_tree().create_timer(2.0)
timer.timeout.connect(func(): print("2 秒后"))

# 帧时间
func _process(delta):
    print("帧时间：", delta)
```

### 文件操作

```gdscript
# 读写文件
var file = FileAccess.open("user://data.txt", FileAccess.WRITE)
file.store_line("Line 1")
file.store_line("Line 2")
file.close()

file = FileAccess.open("user://data.txt", FileAccess.READ)
while not file.eof_reached():
    var line = file.get_line()
    print(line)
file.close()

# 目录操作
var dir = DirAccess.open("user://")
dir.list_dir_begin()
var file_name = dir.get_next()
while file_name != "":
    print(file_name)
    file_name = dir.get_next()

# JSON
var json = JSON.stringify({"key": "value"})
var data = JSON.parse_string(json)
```

### 网络

```gdscript
# HTTP 请求
var http = HTTPRequest.new()
add_child(http)
http.request_completed.connect(_on_request_completed)
http.request("https://api.example.com/data")

# WebSocket
var ws = WebSocketPeer.new()
ws.connect_to_url("ws://localhost:8080")

func _process(delta):
    ws.poll()
    while ws.get_available_packet_count() > 0:
        var packet = ws.get_packet()
        print(packet.get_string_from_utf8())
```

### 调试

```gdscript
# 打印调试
print("Value: ", value)
print_rich("[color=red]Error[/color]")
push_warning("Warning message")
push_error("Error message")

# 断言
assert(value > 0, "Value must be positive")

# 性能分析
var start = Time.get_ticks_usec()
# ... 代码
var elapsed = Time.get_ticks_usec() - start
print("耗时：", elapsed / 1000.0, " ms")

# 调用栈
print_stack()
```

---

## 三类引擎标识符（StringName / Callable / NodePath）

这三类在 4.x 里承担了"引擎内部比较快"的职责，**新手最常见的坑是混用 `String` 与 `StringName`**。

```gdscript
# StringName：引擎内部驻留字符串，O(1) 比较；方法名/信号名/属性名都用它
var action_name: StringName = &"move_left"          # & 前缀是 StringName 字面量
var plain := "move_left"                              # String
print(action_name == &"move_left")                    # true
print(plain == "move_left")                           # true
var n: StringName = StringName("move_left")           # 显式转换

# Callable：可调用引用（对象 + 方法），可 bind 追加参数
var cb := Callable(self, "_on_button_pressed")
cb.call()
cb.bind(42).call()                                   # 追加参数后再调
var cb2 := func(x: int) -> int: return x * 2
cb2.call(21)
cb.is_valid()                                        # 目标是否还存在
cb.get_object()                                      # 被调用者

# NodePath：指向场景中节点的路径
var p: NodePath = ^"Player/Camera3D"                  # ^ 前缀是 NodePath 字面量
get_node(^"Player/Camera3D")
get_node_or_null(p)                                   # 安全版，找不到返回 null
```

## 数组与字典常用方法

```gdscript
var arr: Array[int] = [3, 1, 2]
arr.append(4)
arr.push_back(5)                                     # append 的别名
arr.push_front(0)
arr.pop_back()
arr.pop_front()
arr.insert(1, 9)
arr.erase(9)
arr.remove_at(0)
arr.find(2)                                          # 找不到返回 -1
arr.has(2)
arr.count(2)
arr.sort()
arr.reverse()
arr.shuffle()
arr.slice(0, 2)
var doubled: Array[int] = arr.map(func(x: int) -> int: return x * 2)
var evens: Array[int] = arr.filter(func(x: int) -> bool: return x % 2 == 0)
print(arr.duplicate())                               # 深拷贝（嵌套容器也拷贝）

var d := {"hp": 100, "mp": 50}
d.get("hp", 0)                                       # 键不存在时返回默认值
d.get("hp")                                          # 不存在则返回 null
d.has("hp")
d.keys()                                             # PackedStringArray
d.values()
d.erase("mp")
d.merge({"atk": 10}, true)                            # true = 覆盖已有键
for key in d:
    print(key, " = ", d[key])
```

## 打包数组

```gdscript
var bytes := PackedByteArray()
bytes.append(1)
bytes.append_array(PackedByteArray([2, 3]))
bytes.resize(16)
print(bytes.size())

var floats := PackedFloat32Array([1.0, 2.0, 3.0])
var ints := PackedInt32Array([1, 2, 3])
var vecs := PackedVector3Array([Vector3.ONE, Vector3.ZERO])
# 打包数组是值类型（赋值即拷贝），内存连续，比 Array 快
```

## 场景树与节点操作

```gdscript
var tree := get_tree()
tree.current_scene                                    # 当前场景
tree.change_scene_to_file("res://levels/level_2.tscn")
tree.change_scene_to_packed(preload("res://levels/level_2.tscn"))
tree.paused = true
tree.create_timer(1.5).timeout                        # 配合 await

get_node("Player")                                   # 找不到会报错
get_node_or_null("Player")                           # 找不到返回 null
get_node("%UniqueName")                              # 场景内唯一名（需标记 unique_name_in_owner）
get_node_or_null(^"Player/Weapon")

is_instance_valid(obj)                                # 对象是否还活着
queue_free()                                          # 延迟释放，帧末执行
remove_child(child)
add_child(child)
child.reparent(new_parent)                            # 4.x 的重新挂载
child.get_parent()
child.get_tree()
child.call_deferred("set_process", false)             # 延迟到空闲帧调用
```

## Tween 补间

```gdscript
var tween := create_tween()
tween.tween_property(self, "position", Vector3(100, 0, 0), 0.5)
tween.parallel().tween_property(self, "modulate:a", 0.0, 0.5)
tween.set_trans(Tween.TRANS_BOUNCE)
tween.set_ease(Tween.EASE_OUT)
tween.tween_callback(func(): print("完成"))
tween.tween_interval(0.2)
await tween.finished
```

## 输入

```gdscript
Input.is_action_pressed("move_left")
Input.is_action_just_pressed("jump")
Input.get_action_strength("move_left")                # 0.0~1.0，带模拟量
Input.get_vector("move_left", "move_right", "move_up", "move_down")

InputMap.add_action("attack", 0.2)                    # 0.2 = 死区
InputMap.action_set_deadzone("attack", 0.2)
InputMap.action_add_event("attack", ev)
InputMap.erase_action("attack")
InputMap.get_actions()
var ev := InputEventKey.new()
ev.keycode = KEY_A
var mb := InputEventMouseButton.new()
mb.button_index = MOUSE_BUTTON_LEFT
Input.get_connected_joypads()
```

## 引擎与系统 API

```gdscript
Engine.get_version_info()                             # Dictionary
Engine.get_frames_per_second()
Engine.get_process_frames()
Engine.time_scale = 0.5
Engine.max_fps = 60

OS.get_unique_id()
OS.get_static_memory_usage()                          # 引擎静态内存（非系统总内存）
OS.get_memory_info()                                  # 系统内存字典
OS.get_user_data_dir()
OS.get_cache_dir()                              # 可写的缓存/临时目录
OS.get_environment()
DisplayServer.window_set_size(Vector2i(1280, 720))
DisplayServer.screen_get_size()
Time.get_ticks_msec()
Time.get_datetime_string_from_system()
ProjectSettings.get_setting("physics/3d/default_gravity")
Performance.get_monitor(Performance.TIME_PROCESS)
Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
```

## 并发

```gdscript
var t := Thread.new()
t.start(func(): print("子线程"))
t.wait_to_finish()

var m := Mutex.new()
m.lock()
# 临界区
m.unlock()

var sem := Semaphore.new()
sem.post()
sem.wait()

WorkerThreadPool.add_task(func(): print("任务"))
WorkerThreadPool.wait_for_task_completion()
```

> **注意**：Godot 对象**不是线程安全的**。子线程里不要直接操作场景树节点；用 `call_deferred` 把操作投递回主线程。

## 资源加载与配置

```gdscript
var tex := load("res://art/hero.png")                 # 走缓存
var tex2 := preload("res://art/hero.png")             # 编译期加载，运行更快
ResourceLoader.load_threaded_request("res://big.tscn")
ResourceLoader.load_threaded_get_status("res://big.tscn", progress)   # progress 是 Array 输出参数
ResourceLoader.load_threaded_get("res://big.tscn")
ResourceLoader.load("res://a.tres", "", ResourceLoader.CACHE_MODE_REPLACE)
ResourceSaver.save(resource, "user://save.tres")

var cfg := ConfigFile.new()
cfg.set_value("graphics", "quality", 2)
cfg.save("user://settings.cfg")
cfg.load("user://settings.cfg")
print(cfg.get_value("graphics", "quality", 1))

var re := RegEx.new()
re.compile("(\\d+)")
for m in re.search_all("a1 b22 c333"):
    print(m.get_string(1))

JSON.stringify({"a": 1})
JSON.parse_string('{"a": 1}')
```

## 脚本级注解

```gdscript
@tool                                          # 脚本在编辑器内也执行
@export var speed: float = 100.0
@export_range(0, 100, 1) var hp: int = 100
@export_enum("Easy", "Normal", "Hard") var difficulty: int = 1
@export_group("Movement")
@export_category("Visuals")
@export_multiline var notes: String = ""
@export_file("*.png") var icon: Texture2D
@export_node_path("Sprite2D") var target: NodePath
@onready var sprite := $Sprite2D
@warning_ignore("unused_variable")
static func make() -> Node: return null
```

## 类型系统要点

```gdscript
var a := 1                 # := 推断类型（静态）
var b = 1                  # = 动态，运行时决定（退化为 Variant）
var c: int = 1             # 显式静态类型
var d: float = 1           # int → float 属允许的隐式转换
# var e: int = 1.5        # float → int 报错，需显式 int(1.5)

var f: String = "x" + "y"  # 静态类型下字符串拼接会报错，需用 "%s" % 或 str_concat
var g := StringName("x")
var h := str(g)            # StringName → String
var i := NodePath("x")
```

## await 与协程

```gdscript
func _ready() -> void:
    await get_tree().process_frame          # 等下一帧
    await get_tree().create_timer(1.0).timeout
    await some_signal
    var result = await do_async()
    # 协程函数在 await 处返回，调用方也需 await

func do_async() -> int:
    await get_tree().create_timer(0.5).timeout
    return 42
```

> **`yield` 已在 Godot 4 移除**，从 3.x 迁移的代码请全部改为 `await`。

## 3.x → 4.x 迁移对照

| Godot 3.x | Godot 4.x |
|---|---|
| `yield(obj, "signal")` | `await obj.signal` |
| `export(int) var x` | `@export var x: int` |
| `onready var x = $A` | `@onready var x = $A` |
| `setget set_x` | `var x: int: set(value): ...` |
| `var inst = scene.instance()` | `var inst = scene.instantiate()` |
| `connect("sig", self, "method")` | `sig.connect(self.method)` |
| `is_connected("sig", self, "method")` | `sig.is_connected(self.method)` |
| `PoolStringArray` / `PoolIntArray` | `PackedStringArray` / `PackedInt32Array` |
| `Spatial` / `KinematicBody` | `Node3D` / `CharacterBody3D` |
| `OS.get_ticks_msec()` 作为帧时间 | `Performance.TIME_PROCESS`（前者是启动以来总毫秒） |
| `set_shader_param(...)` | `set_shader_parameter(...)` |
| `KinematicBody2D.move_and_slide(...)` | `CharacterBody2D.move_and_slide()`（参数改为 `velocity`） |

---

## 🎯 常用模式

### 单例模式

```gdscript
# GameManager.gd
extends Node

static var instance: GameManager

func _ready():
    instance = self

static func get_instance() -> GameManager:
    return instance
```

### 对象池

```gdscript
# ObjectPool.gd
extends Node

var pool: Array[Node] = []
var scene: PackedScene

func get_object() -> Node:
    if pool.is_empty():
        return scene.instantiate()
    return pool.pop_back()

func return_object(obj: CanvasItem):
    obj.visible = false
    pool.append(obj)
```

### 状态机

```gdscript
# StateMachine.gd
extends Node

var current_state: State
var states: Dictionary = {}

func add_state(name: String, state: State):
    states[name] = state
    add_child(state)

func change_state(new_state_name: String):
    if current_state:
        current_state.exit()
    current_state = states[new_state_name]
    current_state.enter()

func _process(delta):
    if current_state:
        current_state.update(delta)
```

### 事件总线

```gdscript
# EventBus.gd
extends Node

static var instance: EventBus

signal player_died
signal enemy_defeated
signal item_collected

func _ready():
    instance = self
```

---

**版本**: Godot 4.x  
**最后更新**: 2026-10-20

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

**上一篇**: [附录 A：术语表](/articles/appendix-a-glossary.md)
**下一篇**: [附录 C：Godot 与 Unity 对照表](/articles/appendix-c-unity-migration.md)
