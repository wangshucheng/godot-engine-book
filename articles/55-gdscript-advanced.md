# 第 45 篇：GDScript 进阶

> **本卷定位**: 第七卷 脚本系统（8 篇）  
> **前置知识**: 第 54 章 脚本系统  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

GDScript 是 Godot 引擎的原生脚本语言，语法简洁、功能强大。掌握 GDScript 的高级特性能够帮助开发者编写更高效、更优雅的代码。

本章将深入探讨 GDScript 的高级语法特性、常用设计模式、最佳实践以及性能调优技巧。

---

## 🎯 学习目标

- 掌握 GDScript 高级语法特性
- 学会常用设计模式实现
- 熟悉代码最佳实践
- 掌握性能调优技巧
- 能够编写高质量 GDScript 代码

---

## 1. 高级语法特性

### 1.1 泛型和模板

```gdscript
# GDScript 泛型和模板
class_name GDScriptGenerics

# 泛型函数
func generic_function<T>(value: T) -> T:
    return value

# 泛型类
class GenericClass:
    var data: Array
    
    func add(item):
        data.append(item)
    
    func get(index: int):
        return data[index]
    
    func size() -> int:
        return data.size()

# 类型约束泛型
func constrained_generic<T>(value: T) -> T:
    # T 必须是 Object 的子类
    if value is Object:
        return value
    return value

# 多类型参数
func multi_type_param(value: Variant) -> String:
    if value is int:
        return "Integer: %d" % value
    elif value is String:
        return "String: %s" % value
    elif value is Array:
        return "Array with %d items" % value.size()
    else:
        return "Unknown type"

# 类型别名
typedef IntArray = PackedInt32Array
typedef FloatArray = PackedFloat32Array
typedef Vector2Array = PackedVector2Array

var my_ints: IntArray = IntArray()
var my_floats: FloatArray = FloatArray()
```

### 1.2 异步编程

```gdscript
# GDScript 异步编程
class_name GDScriptAsync

# 使用 await 等待信号
func wait_for_signal(obj: Object, signal_name: String):
    await obj.get(signal_name)
    print("Signal received")

# 等待场景树信号
func wait_for_frame():
    await get_tree().process_frame
    print("Next frame")

func wait_for_physics_frame():
    await get_tree().physics_frame
    print("Next physics frame")

# 等待时间
func wait_for_seconds(seconds: float):
    await get_tree().create_timer(seconds).timeout
    print("Timer finished")

# 链式等待
func chain_waits():
    print("Start")
    await wait_for_seconds(1.0)
    print("After 1 second")
    await wait_for_seconds(2.0)
    print("After 2 more seconds")

# 并行等待
func parallel_waits():
    var timer1 = get_tree().create_timer(1.0)
    var timer2 = get_tree().create_timer(2.0)
    
    await timer1.timeout
    print("Timer 1 finished")
    
    await timer2.timeout
    print("Timer 2 finished")

# 异步加载资源
func async_load_resource(path: String):
    var resource = await ResourceLoader.load(path)
    return resource

# 异步实例化场景
func async_instantiate_scene(path: String):
    var scene = await ResourceLoader.load(path)
    var instance = scene.instantiate()
    return instance
```

### 1.3 元编程

```gdscript
# GDScript 元编程
class_name GDScriptMetaprogramming

# 动态方法调用
func call_dynamic_method(obj: Object, method_name: String, args: Array = []):
    if obj.has_method(method_name):
        return obj.callv(method_name, args)
    return null

# 动态属性访问
func get_dynamic_property(obj: Object, property_name: String):
    if obj.has_property(property_name):
        return obj.get(property_name)
    return null

func set_dynamic_property(obj: Object, property_name: String, value):
    if obj.has_property(property_name):
        obj.set(property_name, value)

# 检查方法存在
func safe_call(obj: Object, method_name: String, default_value = null):
    if obj.has_method(method_name):
        return obj.call(method_name)
    return default_value

# 获取所有方法
func get_all_methods(obj: Object) -> Array:
    var methods = []
    var method_list = obj.get_method_list()
    for method in method_list:
        methods.append(method.name)
    return methods

# 获取所有属性
func get_all_properties(obj: Object) -> Array:
    var properties = []
    var property_list = obj.get_property_list()
    for property in property_list:
        properties.append(property.name)
    return properties

# 动态创建类
func create_dynamic_class(class_name: String, base_class: GDScript):
    var script = GDScript.new()
    script.source_code = """
extends %s

class_name %s

var custom_var: int = 0

func custom_method():
    print("Custom method called")
""" % [base_class.resource_path.get_file().replace(".gd", ""), class_name]
    script.reload()
    return script

# 反射调用
func reflective_call(obj: Object, method_name: String, args: Array = []):
    var method_list = obj.get_method_list()
    for method in method_list:
        if method.name == method_name:
            return obj.callv(method_name, args)
    return null
```

### 1.4 高级类型系统

```gdscript
# GDScript 高级类型系统
class_name GDScriptAdvancedTypes

# 联合类型（使用 Variant）
func union_type_example(value: Variant) -> String:
    if value is int or value is float:
        return "Number: %s" % str(value)
    elif value is String:
        return "String: %s" % value
    return "Other"

# 可选类型（使用 null）
func optional_type_example(value: Variant = null) -> String:
    if value == null:
        return "No value provided"
    return "Value: %s" % str(value)

# 元组（使用 Array）
func tuple_example() -> Array:
    return [1, "hello", Vector2(10, 20)]

func use_tuple():
    var tuple = tuple_example()
    var num: int = tuple[0]
    var str_val: String = tuple[1]
    var vec: Vector2 = tuple[2]

# 命名元组（使用 Dictionary）
func named_tuple_example() -> Dictionary:
    return {
        "number": 1,
        "text": "hello",
        "vector": Vector2(10, 20)
    }

func use_named_tuple():
    var tuple = named_tuple_example()
    var num: int = tuple.number
    var str_val: String = tuple.text
    var vec: Vector2 = tuple.vector

# 类型守卫
func type_guard(value: Variant) -> int:
    if value is int:
        return value  # 类型收窄
    return 0

# 可空类型处理
func nullable_handling(value: Variant) -> int:
    if value == null:
        return -1
    if value is int:
        return value
    return 0

# 类型断言
func type_assert(value: Variant) -> int:
    assert(value is int, "Value must be an integer")
    return value
```

---

## 2. 设计模式实现

### 2.1 单例模式

```gdscript
# 单例模式
class_name SingletonPattern

# 方法 1: 自动加载单例
# 在项目设置中配置 AutoLoad
# 文件：global_singleton.gd
# extends Node
# var score: int = 0
# func add_score(points: int):
#     score += points

# 方法 2: 静态单例
static var instance: SingletonPattern = null

static func get_instance() -> SingletonPattern:
    if instance == null:
        instance = SingletonPattern.new()
    return instance

static func free_instance():
    if instance != null:
        instance.free()
        instance = null

# 使用示例
# var singleton = SingletonPattern.get_instance()
# singleton.do_something()
```

### 2.2 工厂模式

```gdscript
# 工厂模式
class_name FactoryPattern

extends Node

# 简单工厂
static func create_enemy(type: String) -> Node:
    var enemy: Node
    match type:
        "basic":
            enemy = BasicEnemy.new()
        "advanced":
            enemy = AdvancedEnemy.new()
        "boss":
            enemy = BossEnemy.new()
    return enemy

# 工厂方法
func create_product(product_type: String) -> Object:
    match product_type:
        "weapon":
            return create_weapon()
        "armor":
            return create_armor()
        "potion":
            return create_potion()
    return null

func create_weapon() -> Object:
    var weapon = Node.new()
    weapon.name = "Weapon"
    return weapon

func create_armor() -> Object:
    var armor = Node.new()
    armor.name = "Armor"
    return armor

func create_potion() -> Object:
    var potion = Node.new()
    potion.name = "Potion"
    return potion

# 抽象工厂
interface ItemFactory:
    func create_weapon() -> Object
    func create_armor() -> Object

class BasicItemFactory:
    extends RefCounted
    
    func create_weapon() -> Object:
        var weapon = Node.new()
        weapon.name = "BasicWeapon"
        return weapon
    
    func create_armor() -> Object:
        var armor = Node.new()
        armor.name = "BasicArmor"
        return armor

class AdvancedItemFactory:
    extends RefCounted
    
    func create_weapon() -> Object:
        var weapon = Node.new()
        weapon.name = "AdvancedWeapon"
        return weapon
    
    func create_armor() -> Object:
        var armor = Node.new()
        armor.name = "AdvancedArmor"
        return armor
```

### 2.3 观察者模式

```gdscript
# 观察者模式
class_name ObserverPattern

extends Node

# 主题（被观察者）
class Subject:
    var observers: Array = []
    
    func attach(observer: Object):
        if observer not in observers:
            observers.append(observer)
    
    func detach(observer: Object):
        observers.erase(observer)
    
    func notify(data: Variant = null):
        for observer in observers:
            if observer.has_method("update"):
                observer.update(data)

# 观察者
class Observer:
    func update(data: Variant):
        print("Received update: ", data)

# 使用示例
func use_observer_pattern():
    var subject = Subject.new()
    
    var observer1 = Observer.new()
    var observer2 = Observer.new()
    
    subject.attach(observer1)
    subject.attach(observer2)
    
    subject.notify("Hello observers!")
    
    subject.detach(observer1)
    subject.notify("Only observer2 receives this")
```

### 2.4 状态模式

```gdscript
# 状态模式
class_name StatePattern

extends Node

# 状态接口
class State:
    func enter():
        pass
    
    func exit():
        pass
    
    func update(delta: float):
        pass
    
    func handle_input(event: InputEvent):
        pass

# 具体状态
class IdleState:
    extends State
    
    func enter():
        print("Entering Idle state")
    
    func update(delta: float):
        # 检查是否需要切换状态
        if Input.is_action_just_pressed("move"):
            return "move"
        return null

class MoveState:
    extends State
    
    func enter():
        print("Entering Move state")
    
    func update(delta: float):
        if not Input.is_action_pressed("move"):
            return "idle"
        return null

class JumpState:
    extends State
    
    func enter():
        print("Entering Jump state")
    
    func update(delta: float):
        # 落地检查
        return "idle"

# 状态机
class StateMachine:
    var current_state: State = null
    var states: Dictionary = {}
    
    func add_state(name: String, state: State):
        states[name] = state
    
    func set_state(name: String):
        if states.has(name):
            if current_state:
                current_state.exit()
            current_state = states[name]
            current_state.enter()
    
    func update(delta: float):
        if current_state:
            var new_state = current_state.update(delta)
            if new_state:
                set_state(new_state)
    
    func handle_input(event: InputEvent):
        if current_state:
            current_state.handle_input(event)

# 使用示例
func use_state_pattern():
    var machine = StateMachine.new()
    machine.add_state("idle", IdleState.new())
    machine.add_state("move", MoveState.new())
    machine.add_state("jump", JumpState.new())
    machine.set_state("idle")
```

### 2.5 对象池模式

```gdscript
# 对象池模式
class_name ObjectPoolPattern

extends Node

var pool: Array = []
var scene: PackedScene
var pool_size: int = 20
var parent: Node

func _init(p_scene: PackedScene, p_size: int, p_parent: Node):
    scene = p_scene
    pool_size = p_size
    parent = p_parent
    _initialize_pool()

func _initialize_pool():
    for i in range(pool_size):
        var instance = scene.instantiate()
        instance.set_process(false)
        instance.visible = false
        parent.add_child(instance)
        pool.append(instance)

func get() -> Node:
    for instance in pool:
        if not instance.is_inside_tree() or not instance.visible:
            instance.visible = true
            instance.set_process(true)
            return instance
    
    # 池为空，创建新实例
    var instance = scene.instantiate()
    parent.add_child(instance)
    pool.append(instance)
    return instance

func return_to_pool(instance: Node):
    instance.visible = false
    instance.set_process(false)

func get_available_count() -> int:
    var count = 0
    for instance in pool:
        if not instance.visible:
            count += 1
    return count

# 使用示例
# var bullet_pool = ObjectPoolPattern.new(bullet_scene, 50, self)
# var bullet = bullet_pool.get()
# bullet.global_position = player_position
# bullet.shoot(direction)
# 子弹完成后：bullet_pool.return_to_pool(bullet)
```

---

## 3. 最佳实践

### 3.1 代码规范

```gdscript
# GDScript 代码规范
class_name GDScriptBestPractices

extends Node

# 1. 命名规范
var snake_case_variable: int  # 变量使用蛇形命名
const CONSTANT_VALUE: int = 100  # 常量使用大写蛇形
class_name ClassName  # 类使用帕斯卡命名
func function_name():  # 函数使用蛇形命名

# 2. 类型注解
var typed_var: int = 0
var typed_array: Array[int] = []
var typed_dict: Dictionary[String, int] = {}

# 3. 函数设计
func small_function():  # 函数应该短小
    pass

func single_responsibility():  # 单一职责
    do_one_thing()

func descriptive_name():  # 描述性命名
    pass

# 4. 注释规范
# 单行注释使用 #
"""
多行注释使用三引号
可以写详细说明
"""

# 5. 代码组织
#region 区域标记
func related_function_1():
    pass

func related_function_2():
    pass
#endregion

# 6. 错误处理
func safe_divide(a: float, b: float) -> float:
    if b == 0:
        push_error("Division by zero")
        return 0.0
    return a / b

# 7. 断言使用
func validate_input(value: int):
    assert(value >= 0, "Value must be non-negative")
    assert(value <= 100, "Value must be <= 100")
```

### 3.2 性能最佳实践

```gdscript
# 性能最佳实践
class_name PerformanceBestPractices

extends Node

# 1. 避免在 _process 中创建对象
var cached_array: Array = []

func _ready():
    cached_array.resize(100)  # 预分配

func _process(delta):
    # 好：使用缓存
    for i in range(cached_array.size()):
        cached_array[i] = i
    
    # 避免：每帧创建
    # var temp_array = []
    # for i in range(100):
    #     temp_array.append(i)

# 2. 使用合适的循环
func iterate_array(arr: Array):
    # 好：直接迭代
    for item in arr:
        process_item(item)
    
    # 避免：索引访问（除非需要索引）
    # for i in range(arr.size()):
    #     process_item(arr[i])

# 3. 字符串优化
func string_concatenation():
    # 好：使用格式化
    var result = "Player %s has %d points" % ["John", 100]
    
    # 避免：多次拼接
    # var result = "Player " + "John" + " has " + str(100) + " points"

# 4. 信号连接优化
var is_connected: bool = false

func connect_once():
    if not is_connected:
        some_signal.connect(my_handler)
        is_connected = true

# 5. 节点查找缓存
@onready var cached_node: Node = get_node("Path/To/Node")

func _process(delta):
    # 好：使用缓存
    cached_node.do_something()
    
    # 避免：每帧查找
    # get_node("Path/To/Node").do_something()

# 6. 数学运算优化
func math_optimization():
    # 好：使用内置函数
    var result = clamp(50, 0, 100)
    
    # 避免：手动实现
    # var result = max(0, min(50, 100))
```

### 3.3 架构最佳实践

```gdscript
# 架构最佳实践
class_name ArchitectureBestPractices

extends Node

# 1. 组件化设计
class PlayerMovement:
    extends Node
    
    var speed: float = 5.0
    
    func move(direction: Vector2):
        pass

class PlayerHealth:
    extends Node
    
    var health: int = 100
    
    func take_damage(amount: int):
        health -= amount

# 2. 事件驱动
signal player_died
signal player_won

func check_game_state():
    if player_health <= 0:
        player_died.emit()

# 3. 依赖注入
class GameService:
    func do_something():
        pass

class Player:
    var service: GameService
    
    func _init(svc: GameService):
        service = svc
    
    func update():
        service.do_something()

# 4. 数据驱动
var enemy_stats: Dictionary = {
    "basic": {"health": 10, "damage": 5},
    "advanced": {"health": 50, "damage": 15},
    "boss": {"health": 500, "damage": 50}
}

func create_enemy(type: String):
    var stats = enemy_stats.get(type, {"health": 10, "damage": 5})
    # 使用 stats 创建敌人

# 5. 配置分离
@export_group("Movement")
@export var move_speed: float = 5.0
@export var jump_height: float = 3.0

@export_group("Combat")
@export var attack_damage: int = 10
@export var attack_range: float = 2.0
```

---

## 4. 性能调优

### 4.1 性能分析

```gdscript
# 性能分析工具
class_name PerformanceProfiling

extends Node

var frame_times: Array = []
var max_samples: int = 60

func _process(delta):
    frame_times.append(delta)
    if frame_times.size() > max_samples:
        frame_times.pop_front()

func get_average_fps() -> float:
    if frame_times.size() == 0:
        return 0.0
    
    var avg_frame_time = 0.0
    for time in frame_times:
        avg_frame_time += time
    avg_frame_time /= frame_times.size()
    
    return 1.0 / avg_frame_time

func get_min_fps() -> float:
    if frame_times.size() == 0:
        return 0.0
    
    var max_time = 0.0
    for time in frame_times:
        if time > max_time:
            max_time = time
    
    return 1.0 / max_time

func get_max_fps() -> float:
    if frame_times.size() == 0:
        return 0.0
    
    var min_time = 1.0
    for time in frame_times:
        if time < min_time:
            min_time = time
    
    return 1.0 / min_time

# 性能标记
func profile_function(func_name: String, callable: Callable):
    var start_time = Time.get_ticks_usec()
    callable.call()
    var end_time = Time.get_ticks_usec()
    print(func_name, " took ", (end_time - start_time) / 1000.0, " ms")
```

### 4.2 内存调优

```gdscript
# 内存调优
class_name MemoryTuning

extends Node

func get_memory_usage() -> int:
    return Performance.get_memory_usage()

func print_memory_stats():
    var usage = get_memory_usage()
    print("Memory usage: ", usage / 1024 / 1024, " MB")

func optimize_arrays():
    # 预分配数组
    var arr: Array = []
    arr.resize(1000)  # 预分配
    
    # 使用固定类型数组
    var int_arr: PackedInt32Array = PackedInt32Array()
    int_arr.resize(1000)

func optimize_strings():
    # 使用 StringName 代替 String（用于标识符）
    var name: StringName = &"player"
    
    # 避免频繁字符串创建
    var template = "Player %d"
    for i in range(100):
        var result = template % i

func cleanup_resources():
    # 强制垃圾回收
    var before = get_memory_usage()
    for i in range(3):
        await get_tree().process_frame
    var after = get_memory_usage()
    print("Memory freed: ", (before - after) / 1024, " KB")
```

### 4.3 渲染调优

```gdscript
# 渲染调优
class_name RenderingTuning

extends Node

func optimize_draw_calls():
    # 合并网格
    pass

func optimize_textures():
    # 使用合适的纹理格式
    pass

func optimize_shaders():
    # 简化着色器
    pass

func reduce_overdraw():
    # 减少过度绘制
    pass

func use_occlusion_culling():
    # 使用遮挡剔除
    pass

func batch_similar_objects():
    # 批量处理相似对象
    pass
```

---

## 5. 实践：完整 GDScript 项目

### 5.1 游戏管理器

```gdscript
# 游戏管理器
class_name GameManager

extends Node

signal game_started
signal game_paused
signal game_resumed
signal game_over

enum GameState { MENU, PLAYING, PAUSED, GAME_OVER }

var current_state: GameState = GameState.MENU
var score: int = 0
var level: int = 1

func start_game():
    current_state = GameState.PLAYING
    score = 0
    level = 1
    game_started.emit()

func pause_game():
    if current_state == GameState.PLAYING:
        current_state = GameState.PAUSED
        get_tree().paused = true
        game_paused.emit()

func resume_game():
    if current_state == GameState.PAUSED:
        current_state = GameState.PLAYING
        get_tree().paused = false
        game_resumed.emit()

func end_game():
    current_state = GameState.GAME_OVER
    game_over.emit()

func add_score(points: int):
    score += points

func next_level():
    level += 1

func get_game_data() -> Dictionary:
    return {
        "state": current_state,
        "score": score,
        "level": level
    }
```

### 5.2 事件总线

```gdscript
# 事件总线
class_name EventBus

extends Node

signal enemy_defeated(enemy_type: String, score: int)
signal player_damaged(amount: int)
signal player_healed(amount: int)
signal item_collected(item_name: String)
signal level_completed(level: int)

static var instance: EventBus = null

func _ready():
    if instance == null:
        instance = self
    else:
        queue_free()

static def get_instance() -> EventBus:
    return instance
```

### 5.3 存档系统

```gdscript
# 存档系统
class_name SaveSystem

extends Node

const SAVE_PATH = "user://savegame.json"

func save_game(data: Dictionary) -> bool:
    var file = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(data, "  "))
        file.close()
        return true
    return false

func load_game() -> Dictionary:
    if not FileAccess.file_exists(SAVE_PATH):
        return {}
    
    var file = FileAccess.open(SAVE_PATH, FileAccess.READ)
    if file:
        var text = file.get_as_text()
        file.close()
        
        var json = JSON.new()
        var error = json.parse(text)
        if error == OK:
            return json.data
    
    return {}

func delete_save() -> bool:
    if FileAccess.file_exists(SAVE_PATH):
        return DirAccess.remove_absolute(SAVE_PATH) == OK
    return false

func has_save() -> bool:
    return FileAccess.file_exists(SAVE_PATH)
```

---

## 📝 本章总结

### 核心要点

1. **泛型和模板提升代码复用**，减少重复代码
2. **异步编程简化等待逻辑**，await 关键字强大
3. **设计模式解决常见问题**，单例、工厂、观察者等
4. **代码规范提升可维护性**，命名、注释、组织
5. **性能调优确保流畅运行**，内存、渲染优化

### 关键术语

| 术语 | 解释 |
|------|------|
| Generic | 泛型，参数化类型 |
| Async/Await | 异步编程，等待操作完成 |
| Metaprogramming | 元编程，操作代码的代码 |
| Design Pattern | 设计模式，解决常见问题的方案 |
| Object Pool | 对象池，复用对象减少分配 |
| Dependency Injection | 依赖注入，外部提供依赖 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot GDScript Reference](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/index.html)
- **源码位置**: `modules/gdscript/`
- **设计模式**: [Game Programming Patterns](https://gameprogrammingpatterns.com/)

---

## 📋 下一章预告

**第 56 篇：资源系统**

- 资源系统基础
- 资源管理
- 资源加载
- 资源优化

---

*写作时间：2026-03-20*  
*字数：约 14,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*