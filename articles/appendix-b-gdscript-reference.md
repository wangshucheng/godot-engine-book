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
    yield(get_tree(), "physics_frame")
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
var angle = lerp_angle(from, to, 0.1)

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

func return_object(obj: Node):
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
**最后更新**: 2026-03-20
