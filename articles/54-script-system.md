# 第 44 篇：脚本系统

> **本卷定位**: 第七卷 脚本系统（8 篇）  
> **前置知识**: 第 53 章 输入系统  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

脚本系统是 Godot 引擎的核心功能之一，允许开发者使用 GDScript、C# 等语言编写游戏逻辑。脚本系统提供了灵活的代码组织方式、强大的继承机制和高效的执行性能。

本章将深入探讨 Godot 脚本系统的基础知识、GDScript 语法、脚本生命周期以及优化技巧。

---

## 🎯 学习目标

- 理解脚本系统的基本概念
- 掌握 GDScript 语法基础
- 学会脚本生命周期管理
- 熟悉脚本优化技术
- 掌握脚本系统实践

---

## 1. 脚本系统基础

### 1.1 脚本系统类型

```
脚本系统类型:
┌─────────────────────────────────────────────────────────────┐
│                      脚本系统类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GDScript：Godot 原生脚本语言                           │
│  2. C#：.NET 支持，适合大型项目                            │
│  3. VisualScript：可视化脚本（已废弃）                     │
│  4. GDExtension：C++ 扩展，高性能                          │
│  5. 第三方语言：通过 GDExtension 支持                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 脚本系统组件

```
脚本系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      脚本系统组件                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Script：脚本资源基类                                   │
│  2. GDScript：GDScript 脚本资源                            │
│  3. ScriptInstance：脚本实例                               │
│  4. Object：对象基类，可附加脚本                           │
│  5. Node：节点类，继承自 Object                            │
│  6. ScriptEditor：脚本编辑器                               │
│  7. ScriptLanguage：脚本语言接口                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 脚本系统流程

```
脚本系统处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      脚本系统处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 创建脚本资源（.gd 文件）                               │
│  2. 将脚本附加到节点或对象                                 │
│  3. 引擎创建脚本实例                                       │
│  4. 调用生命周期方法（_ready, _process 等）                │
│  5. 脚本执行游戏逻辑                                       │
│  6. 对象销毁时清理脚本实例                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. GDScript 语法基础

### 2.1 变量和类型

```gdscript
# GDScript 变量和类型
class_name GDScriptVariables

# 动态类型（不推荐）
var dynamic_var

# 静态类型（推荐）
var int_var: int = 0
var float_var: float = 0.0
var string_var: String = ""
var bool_var: bool = false
var array_var: Array = []
var dict_var: Dictionary = {}
var vector2_var: Vector2 = Vector2.ZERO
var vector3_var: Vector3 = Vector3.ZERO
var color_var: Color = Color.WHITE

# 类型推断
var inferred_int = 10  # 推断为 int
var inferred_float = 3.14  # 推断为 float
var inferred_string = "hello"  # 推断为 String

# 常量
const MAX_VALUE = 100
const GAME_TITLE = "My Game"
const PI = 3.14159

# 枚举
enum Direction { NORTH, SOUTH, EAST, WEST }
enum Status { IDLE = 0, RUNNING = 1, JUMPING = 2 }

# 类型转换
var int_to_float: float = float(10)
var float_to_int: int = int(3.14)
var string_to_int: int = int("100")
var variant_to_type: int = int(some_variant)

# 类型检查
if some_var is int:
    print("Is int")
if some_var is String:
    print("Is String")
```

### 2.2 函数和方法

```gdscript
# GDScript 函数和方法
class_name GDScriptFunctions

# 基础函数
func basic_function():
    print("Basic function")

# 带参数函数
func function_with_params(param1: int, param2: String):
    print(param1, " ", param2)

# 带默认参数
func function_with_defaults(param1: int = 10, param2: String = "default"):
    print(param1, " ", param2)

# 返回值函数
func function_with_return() -> int:
    return 42

# 多返回值
func function_with_multiple_returns() -> Dictionary:
    return {"x": 10, "y": 20}

# 可变参数
func function_with_varargs(args: Array):
    for arg in args:
        print(arg)

# 命名参数
func function_with_named_params(name: String, age: int):
    print(name, " is ", age)

# 调用示例
# function_with_named_params(age: 25, name: "John")

# 匿名函数（Lambda）
var lambda_func = func(x: int) -> int:
    return x * 2

# 闭包
func create_counter() -> Callable:
    var count = 0
    return func() -> int:
        count += 1
        return count

# 静态函数
static func static_function():
    print("Static function")

# 私有函数（约定）
func _private_function():
    print("Private function")
```

### 2.3 类和继承

```gdscript
# GDScript 类和继承
class_name GDScriptClasses

# 基础类
class BaseClass:
    var base_var: int = 0
    
    func base_method():
        print("Base method")
    
    func virtual_method():
        pass  # 虚方法

# 继承类
class DerivedClass:
    extends BaseClass
    
    var derived_var: String = ""
    
    func derived_method():
        print("Derived method")
    
    func virtual_method():  # 重写虚方法
        print("Derived virtual method")

# 内部类
class OuterClass:
    var outer_var: int = 0
    
    class InnerClass:
        var inner_var: String = ""

# 使用类
func use_classes():
    var base = BaseClass.new()
    base.base_method()
    
    var derived = DerivedClass.new()
    derived.base_method()  # 继承的方法
    derived.derived_method()  # 自己的方法
    derived.virtual_method()  # 重写的方法
    
    var outer = OuterClass.new()
    var inner = OuterClass.InnerClass.new()
```

### 2.4 信号和连接

```gdscript
# GDScript 信号和连接
class_name GDScriptSignals

# 定义信号
signal value_changed(new_value: int)
signal completed
signal data_received(data: Dictionary)

# 发射信号
func change_value(new_value: int):
    value_changed.emit(new_value)
    # 或者使用旧语法：emit_signal("value_changed", new_value)

func finish():
    completed.emit()

func receive_data(data: Dictionary):
    data_received.emit(data)

# 连接信号
func connect_signals(other_object: Object):
    # 现代语法
    other_object.value_changed.connect(_on_value_changed)
    other_object.completed.connect(_on_completed)
    
    # 带绑定参数
    other_object.data_received.connect(_on_data_received.bind("extra_param"))
    
    # 一次性连接
    other_object.completed.connect(_on_completed, CONNECT_ONE_SHOT)
    
    # 延迟连接
    other_object.value_changed.connect(_on_value_changed, CONNECT_DEFERRED)

# 断开信号
func disconnect_signals(other_object: Object):
    other_object.value_changed.disconnect(_on_value_changed)
    other_object.completed.disconnect(_on_completed)

# 信号处理函数
func _on_value_changed(new_value: int):
    print("Value changed to: ", new_value)

func _on_completed():
    print("Completed")

func _on_data_received(data: Dictionary, extra_param: String):
    print("Data received: ", data, " Extra: ", extra_param)

# 检查连接
func is_connected_to_signal(other_object: Object) -> bool:
    return other_object.value_changed.is_connected(_on_value_changed)
```

---

## 3. 脚本生命周期

### 3.1 节点生命周期

```gdscript
# 节点生命周期
class_name NodeLifecycle

extends Node

# 1. 初始化阶段
func _init():
    # 构造函数，最早调用
    # 此时节点还未添加到场景树
    print("_init called")

func _enter_tree():
    # 节点进入场景树
    # 可以访问父节点和场景
    print("_enter_tree called")

func _ready():
    # 第一次进入场景树后调用
    # 所有节点都已就绪
    print("_ready called")

# 2. 处理阶段
func _process(delta: float):
    # 每帧调用（依赖渲染帧率）
    # delta: 上一帧到当前帧的时间
    pass

func _physics_process(delta: float):
    # 每物理帧调用（固定帧率）
    # 用于物理相关更新
    pass

func _input(event: InputEvent):
    # 处理输入事件
    # 在所有 _input 之前调用
    pass

func _input_event(viewport: Viewport, event: InputEvent, shape_idx: int):
    # 处理 GUI 输入事件
    pass

func _unhandled_input(event: InputEvent):
    # 处理未处理的输入事件
    # 在其他 _input 之后调用
    pass

# 3. 通知阶段
func _notification(what: int):
    # 处理各种通知
    match what:
        NOTIFICATION_ENTER_TREE:
            print("Enter tree notification")
        NOTIFICATION_READY:
            print("Ready notification")
        NOTIFICATION_EXIT_TREE:
            print("Exit tree notification")

# 4. 退出阶段
func _exit_tree():
    # 节点即将离开场景树
    # 清理资源
    print("_exit_tree called")

func _exit():
    # 脚本实例即将销毁
    pass
```

### 3.2 脚本生命周期管理

```gdscript
# 脚本生命周期管理
class_name ScriptLifecycleManager

extends Node

var managed_scripts: Array = []

func register_script(script_instance: Object):
    # 注册脚本实例
    if script_instance not in managed_scripts:
        managed_scripts.append(script_instance)

func unregister_script(script_instance: Object):
    # 注销脚本实例
    managed_scripts.erase(script_instance)

func notify_all(notification: int):
    # 通知所有管理的脚本
    for script_instance in managed_scripts:
        if is_instance_valid(script_instance):
            script_instance._notification(notification)

func cleanup_all():
    # 清理所有脚本
    for script_instance in managed_scripts:
        if is_instance_valid(script_instance):
            if script_instance.has_method("_cleanup"):
                script_instance._cleanup()
    managed_scripts.clear()

func get_active_script_count() -> int:
    var count = 0
    for script_instance in managed_scripts:
        if is_instance_valid(script_instance):
            count += 1
    return count

func print_script_stats():
    print("Active scripts: ", get_active_script_count())
    print("Total registered: ", managed_scripts.size())
```

### 3.3 脚本实例化

```gdscript
# 脚本实例化
class_name ScriptInstantiation

extends Node

func instantiate_script(script_path: String, parent: Node = null) -> Node:
    # 实例化脚本
    var script = load(script_path)
    if script:
        var instance = script.new()
        if parent:
            parent.add_child(instance)
        return instance
    return null

func instantiate_scene(scene_path: String, parent: Node = null) -> Node:
    # 实例化场景
    var scene = load(scene_path)
    if scene:
        var instance = scene.instantiate()
        if parent:
            parent.add_child(instance)
        return instance
    return null

func instantiate_with_params(script_path: String, params: Dictionary) -> Node:
    # 带参数实例化
    var script = load(script_path)
    if script:
        var instance = script.new()
        for key in params:
            if instance.has_property(key):
                instance.set(key, params[key])
        return instance
    return null

func clone_node(node: Node, parent: Node = null) -> Node:
    # 克隆节点
    var clone = node.duplicate()
    if parent:
        parent.add_child(clone)
    return clone

func deep_clone_node(node: Node) -> Node:
    # 深度克隆节点
    return node.duplicate(DUPLICATE_USE_INSTANCING)
```

---

## 4. 脚本优化

### 4.1 性能优化

```gdscript
# 脚本性能优化
class_name ScriptPerformanceOptimization

extends Node

# 1. 使用静态类型
func optimized_function():
    # 好：静态类型
    var count: int = 0
    var result: float = 0.0
    
    # 避免：动态类型
    # var count = 0
    # var result = 0.0

# 2. 缓存节点引用
var cached_node: Node
var cached_node_path: NodePath = @"NodePath"

func _ready():
    # 好：缓存引用
    cached_node = get_node(cached_node_path)

func _process(delta):
    # 好：使用缓存
    cached_node.do_something()
    
    # 避免：每次查找
    # get_node(cached_node_path).do_something()

# 3. 避免不必要的分配
func optimized_loop():
    # 好：预分配数组
    var result: Array = []
    result.resize(100)
    for i in range(100):
        result[i] = i
    
    # 避免：动态增长
    # var result = []
    # for i in range(100):
    #     result.append(i)

# 4. 使用合适的容器
func use_proper_containers():
    # 数组：有序列表
    var array: Array = []
    
    # 字典：键值对
    var dict: Dictionary = {}
    
    # 固定类型数组（更快）
    var int_array: PackedInt32Array = PackedInt32Array()
    var float_array: PackedFloat32Array = PackedFloat32Array()
    var vector_array: PackedVector3Array = PackedVector3Array()

# 5. 减少函数调用开销
func inline_optimization():
    # 好：简单逻辑内联
    var result = 10 + 20
    
    # 避免：不必要的函数调用
    # var result = add(10, 20)

# 6. 使用 const 代替 var
const MAX_COUNT = 100  # 好：常量

# 7. 避免字符串拼接
func string_optimization():
    # 好：使用格式化
    var result = "%s is %d years old" % ["John", 25]
    
    # 避免：多次拼接
    # var result = "John" + " is " + str(25) + " years old"
```

### 4.2 内存优化

```gdscript
# 脚本内存优化
class_name ScriptMemoryOptimization

extends Node

# 1. 及时释放资源
func cleanup_resources():
    var temp_object = Node.new()
    # 使用
    temp_object.queue_free()  # 好：及时释放

# 2. 对象池模式
var object_pool: Array = []
var pool_size: int = 10

func _ready():
    # 预分配对象池
    for i in range(pool_size):
        var obj = Node.new()
        obj.set_process(false)
        object_pool.append(obj)

func get_from_pool() -> Node:
    # 从池中获取对象
    if object_pool.size() > 0:
        var obj = object_pool.pop_back()
        obj.set_process(true)
        return obj
    return Node.new()

func return_to_pool(obj: Node):
    # 归还对象到池
    obj.set_process(false)
    if object_pool.size() < pool_size:
        object_pool.append(obj)
    else:
        obj.queue_free()

# 3. 避免内存泄漏
var connected_signals: Array = []

func connect_with_tracking(signal_source: Object, signal_name: String, callback: Callable):
    # 跟踪连接以便清理
    signal_source.connect(signal_name, callback)
    connected_signals.append({"source": signal_source, "signal": signal_name, "callback": callback})

func cleanup_connections():
    # 清理所有连接
    for connection in connected_signals:
        if is_instance_valid(connection.source):
            connection.source.disconnect(connection.signal, connection.callback)
    connected_signals.clear()

# 4. 使用弱引用
var weak_ref: WeakRef

func set_weak_reference(obj: Object):
    weak_ref = weakref(obj)

func get_weak_reference() -> Object:
    if weak_ref:
        return weak_ref.get_ref()
    return null
```

### 4.3 代码组织优化

```gdscript
# 代码组织优化
class_name ScriptOrganization

extends Node

# 1. 使用常量定义魔法数字
const PLAYER_SPEED = 5.0
const MAX_HEALTH = 100
const GRAVITY = 9.8

# 2. 使用枚举代替魔法字符串
enum GameState { MENU, PLAYING, PAUSED, GAME_OVER }
var current_state: GameState = GameState.MENU

# 3. 分组相关函数
#region Movement Functions

func move_forward():
    pass

func move_backward():
    pass

func move_left():
    pass

func move_right():
    pass

#endregion

#region Combat Functions

func attack():
    pass

func defend():
    pass

func use_skill():
    pass

#endregion

# 4. 使用工具函数
class_name Utils:
    static func clamp_value(value: float, min_val: float, max_val: float) -> float:
        return clamp(value, min_val, max_val)
    
    static func lerp_value(from: float, to: float, t: float) -> float:
        return lerp(from, to, t)

# 5. 导出变量用于编辑器配置
@export var speed: float = 5.0
@export var jump_height: float = 3.0
@export var health: int = 100

# 6. 使用注解
@onready var cached_node = get_node("NodePath")
@export_group("Movement")
@export_subgroup("Speed Settings")
```

---

## 5. 实践：完整脚本系统

### 5.1 脚本管理器

```gdscript
# 脚本管理器
class_name ScriptManager

extends Node

var loaded_scripts: Dictionary = {}
var script_cache: Dictionary = {}

func load_script(script_path: String) -> Script:
    # 加载脚本
    if script_cache.has(script_path):
        return script_cache[script_path]
    
    var script = load(script_path)
    if script:
        script_cache[script_path] = script
        return script
    return null

func unload_script(script_path: String):
    # 卸载脚本
    script_cache.erase(script_path)

func clear_cache():
    # 清空缓存
    script_cache.clear()

func reload_script(script_path: String) -> Script:
    # 重新加载脚本
    script_cache.erase(script_path)
    return load_script(script_path)

func get_loaded_script_count() -> int:
    return script_cache.size()

func print_script_stats():
    print("Loaded scripts: ", get_loaded_script_count())
    for path in script_cache:
        print("- ", path)
```

### 5.2 脚本热重载

```gdscript
# 脚本热重载
class_name ScriptHotReload

extends Node

var watched_scripts: Array = []
var reload_queue: Array = []

func watch_script(script_path: String):
    # 监视脚本
    if script_path not in watched_scripts:
        watched_scripts.append(script_path)

func unwatch_script(script_path: String):
    # 取消监视
    watched_scripts.erase(script_path)

func check_for_changes():
    # 检查脚本变化
    for script_path in watched_scripts:
        if ResourceLoader.exists(script_path):
            var resource = load(script_path)
            if resource and resource.has_changed():
                reload_queue.append(script_path)

func process_reload_queue():
    # 处理重载队列
    for script_path in reload_queue:
        _reload_script(script_path)
    reload_queue.clear()

func _reload_script(script_path: String):
    # 重新加载脚本
    var resource = load(script_path)
    if resource:
        ResourceLoader.load(script_path, "GDScript", ResourceLoader.CACHE_MODE_REPLACE)
        print("Reloaded script: ", script_path)

func _process(delta):
    check_for_changes()
    if reload_queue.size() > 0:
        process_reload_queue()
```

### 5.3 完整脚本系统

```gdscript
# 完整脚本系统
class_name FullScriptSystem

extends Node

var script_manager: ScriptManager
var hot_reload: ScriptHotReload
var lifecycle_manager: ScriptLifecycleManager

func _ready():
    script_manager = ScriptManager.new()
    add_child(script_manager)
    
    hot_reload = ScriptHotReload.new()
    add_child(hot_reload)
    
    lifecycle_manager = ScriptLifecycleManager.new()
    add_child(lifecycle_manager)

func load_and_attach_script(node: Node, script_path: String) -> bool:
    # 加载并附加脚本
    var script = script_manager.load_script(script_path)
    if script:
        node.set_script(script)
        lifecycle_manager.register_script(node)
        hot_reload.watch_script(script_path)
        return true
    return false

func reload_all_scripts():
    # 重新加载所有脚本
    for script_path in hot_reload.watched_scripts:
        script_manager.reload_script(script_path)

func get_script_stats() -> Dictionary:
    return {
        "loaded_scripts": script_manager.get_loaded_script_count(),
        "watched_scripts": hot_reload.watched_scripts.size(),
        "managed_scripts": lifecycle_manager.get_active_script_count()
    }

func print_system_stats():
    var stats = get_script_stats()
    print("Script System Statistics:")
    print("- Loaded Scripts: ", stats.loaded_scripts)
    print("- Watched Scripts: ", stats.watched_scripts)
    print("- Managed Scripts: ", stats.managed_scripts)
```

---

## 📝 本章总结

### 核心要点

1. **GDScript 是 Godot 原生语言**，易学易用
2. **脚本生命周期管理**，理解各阶段方法
3. **性能优化关键**，静态类型、缓存引用
4. **内存管理重要**，对象池、弱引用
5. **代码组织提升可维护性**，常量、枚举、分组

### 关键术语

| 术语 | 解释 |
|------|------|
| GDScript | Godot 原生脚本语言 |
| Script Instance | 脚本实例 |
| Lifecycle | 生命周期，脚本各阶段 |
| Signal | 信号，事件通知机制 |
| Object Pool | 对象池，复用对象 |
| Hot Reload | 热重载，运行时更新脚本 |
| Weak Reference | 弱引用，不阻止释放 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Scripting](https://docs.godotengine.org/en/stable/tutorials/scripting/index.html)
- **源码位置**: `modules/gdscript/`
- **技术博客**: [Godot GDScript Guide](https://godotengine.org/article/gdscript-guide/)

---

## 📋 下一章预告

**第 55 篇：GDScript 进阶**

- 高级语法特性
- 设计模式
- 最佳实践
- 性能调优

---

*写作时间：2026-03-20*  
*字数：约 12,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*