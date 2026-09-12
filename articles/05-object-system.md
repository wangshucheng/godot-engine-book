# 第 5 篇：Godot 对象系统深度解析

> **摘要**：Object 类是 Godot 所有对象的基类，提供 RTTI、反射、通知、元数据等核心能力。本文基于 `core/object/object.h` 的真实实现，剖析对象的内存布局、两种所有权模型（手动释放 vs 引用计数）、删除流程（`_predelete`/`NOTIFICATION_PREDELETE`）、GDCLASS 宏生成的类型识别链、属性反射与 usage 标志，并与 Unity 的 Object 体系对比。

---

## 一、Object 类结构

### 1.1 对象的内存布局

**源码位置**: `core/object/object.h`

下面是 `Object` 类中真实存在的关键成员（节选自 Godot 4.3 源码，字段名与源码一致）：

```cpp
class Object {
    // GDExtension 扩展支持（GDScript/C# 之外的第三方语言走这条通道）
    ObjectGDExtension *_extension = nullptr;
    GDExtensionClassInstancePtr _extension_instance = nullptr;

    // 信号系统（第 6 篇将展开）
    struct SignalData {
        struct Slot {
            int reference_count = 0;
            Connection conn;
            List<Connection>::Element *cE = nullptr;
        };
        MethodInfo user;                                    // 用户信号的原型
        HashMap<Callable, Slot, HashableHasher<Callable>> slot_map;
        bool removable = false;
    };
    HashMap<StringName, SignalData> signal_map;   // 本对象"拥有"的信号
    List<Connection> connections;                 // 本对象"连出去"的连接

    // 生命周期与状态
    int _predelete_ok = 0;               // 删除许可标志
    ObjectID _instance_id;               // 实例 ID，全局唯一
    bool _block_signals = false;         // block_signals() 的开关
    bool _emitting = false;              // 正在发射信号
    bool type_is_reference = false;      // 是否为引用计数类型（friend class RefCounted）
    bool _is_queued_for_deletion = false;// queue_delete() 置位

    // 脚本绑定
    ScriptInstance *script_instance = nullptr;  // GDScript/C# 实例数据
    Variant script;                             // 脚本本体

    // 元数据与翻译
    HashMap<StringName, Variant> metadata;      // set_meta()/get_meta() 的存储
    bool _can_translate = true;                 // tr() 是否生效

    // 类型识别（惰性初始化的类名缓存）
    mutable const StringName *_class_name_ptr = nullptr;
};
```

三个值得注意的设计决策：

1. **没有 `property_list` 成员**。属性列表是**每次调用 `get_property_list()` 时动态拼装**的（沿继承链收集），而不是缓存在对象里——属性注册表在 `ClassDB` 中，属于类而非实例。
2. **信号表与连接表分开**：`signal_map` 存"我定义的信号"，`connections` 存"我订阅别人的连接"。删除对象时两张表都要清理，否则会产生悬垂 `Callable`。
3. **`script` 用 `Variant` 存**：源码注释写明"Reference 尚未存在，先存 Variant"——初始化顺序问题决定了这里不能用 `Ref<Resource>`。

### 1.2 Object 继承体系

```
Object（所有对象的根）
├── RefCounted（引用计数，自动释放）
│   ├── Resource（资源：可序列化、可共享）
│   │   ├── Texture2D / Material / Mesh / Animation / PackedScene ...
│   ├── SceneState / SceneTreeTimer / Tween ...
│   └── ...
├── Node（场景节点，手动管理生命周期）
│   ├── Node2D ─── Sprite2D / CharacterBody2D / TileMapLayer ...
│   ├── Node3D ─── Node3D / CharacterBody3D / Camera3D ...
│   ├── Control ── Button / Label / Panel（UI）
│   └── Viewport ── Window / SubViewport
├── Mesh / Shape3D / StyleBox ...（部分直接继承 Object 的低层类型）
└── Callable / Signal / ObjectID 以值类型存在，不是 Object
```

两个分支的本质区别只有一条：**谁负责删除**。`RefCounted` 用引用计数在最后一个引用消失时自动 `memdelete`；普通 `Object`（含 `Node`）必须显式 `free()` 或经 `queue_delete()` 延迟删除。第 4 篇已详细分析引用计数，本篇聚焦删除流程。

### 1.3 对象的创建与初始化

每个对象构造完成后都会经历统一的初始化管线：

```cpp
// 构造完成后，由文件级友元函数触发
void postinitialize_handler(Object *p_object);   // → Object::_postinitialize()
```

`_postinitialize()` 做两件事：把对象登记进 **ObjectDB**（从此拥有全局唯一的 `_instance_id`），并发出 `NOTIFICATION_POSTINITIALIZE = 0`——这是对象收到的第一条通知，也是 `GDCLASS` 宏初始化类信息缓存的位置。

---

## 二、生命周期：谁删除对象？

### 2.1 两种所有权模型

| 模型 | 释放方式 | 典型类型 | 错误用法 |
|------|----------|----------|----------|
| 引用计数 | 最后一个 `Ref<T>` 消失时自动释放 | RefCounted 及其子类 | 对它调用 `free()` |
| 手动管理 | 必须显式 `free()` 或 `queue_delete()` | Object / Node 及其子类 | 只置 `= null` 就以为释放了 |

### 2.2 删除流程：三步走

`free()` 并不会直接析构，源码中是一条有"否决权"的管线：

```cpp
// 简化自 core/object/object.cpp
bool Object::_predelete() {
    _predelete_ok = 1;
    notification(NOTIFICATION_PREDELETE, true);   // 逆序通知
    if (_predelete_ok) {
        _class_name_ptr = nullptr;                // 释放惰性类名缓存
        return true;
    }
    return false;                                 // 有对象否决了删除
}

// 文件级入口（memdelete 调用它，而不是直接 delete）
bool predelete_handler(Object *p_object) {
    return p_object->_predelete();
}
```

流程分解：

1. `memdelete(obj)`（定义于 `core/os/memory.h`）调用 `predelete_handler(obj)`；
2. `_predelete()` 广播 `NOTIFICATION_PREDELETE = 1`，`_predelete_ok` 记录是否允许删除；
3. 允许则继续析构 → `~Object()` 中断开全部 `connections`、清理 `signal_map`、从 ObjectDB 注销；
4. `NOTIFICATION_PREDELETE_CLEANUP = 3` 是紧随其后的**内部**通知，不绑定到脚本（源码注释明确说明），用于引擎在脚本已卸载后做最后清理。

`_predelete_ok` 的存在意味着**删除可以被否决**——`RefCounted` 正是利用它：引用计数不为 0 时拒绝删除。

### 2.3 free()、queue_free() 与 cancel_free()

```gdscript
# 手动管理类型：立即删除
var node := Node.new()
node.free()                    # 立即析构；若此刻还有代码持有引用，之后访问会崩溃

# 延迟删除：排入本帧末尾的删除队列，等当前逻辑跑完再释放
node.queue_free()              # Node 提供；内部走 SceneTree 的 queue_delete()
print(node.is_queued_for_deletion())   # true

# 后悔药：在真正析构前都可以取消
node.cancel_free()

# RefCounted：永远不要 free()，引用计数会处理
var res := Resource.new()      # 引用计数 = 1
res = null                     # 归零，自动释放
```

**为什么要 `queue_free()`？** 在信号回调或物理回调里 `free()` 一个节点，可能让调用栈上层的代码继续访问已释放的内存。延迟到帧末删除是唯一的安全解法。

### 2.4 悬垂引用的防护

```gdscript
# 1. 弱引用：不阻止释放，用 get_ref() 取回（可能为 null）
var weak := weakref(node)
if weak.get_ref() != null:
    weak.get_ref().queue_free()

# 2. 有效性检查：比 weakref 更常用的守卫
if is_instance_valid(node):
    node.position = Vector2.ZERO
```

`is_instance_valid()` 与 `weakref()` 是全局函数，配合延迟删除使用，可以消除绝大多数"已释放实例访问"崩溃。

---

## 三、RTTI 与类型识别

### 3.1 Variant 类型系统

Godot 使用 **Variant** 类型系统支持动态类型：

```gdscript
var a: int = 10
var b: String = "hello"
var c: Node = Node.new()
var d: Variant = anything  # 可以是任何类型
```

`Variant` 在引擎侧是一个带类型标签的 union，`typeof()` 读的就是这个标签；`Object` 在 Variant 中只占 `TYPE_OBJECT` 一个槽位，具体类型靠 RTTI 判断。

### 3.2 GDCLASS 宏与 is_class 链

`get_class()`/`is_class()` 的实现由 `GDCLASS(m_class, m_inherits)` 宏为每个子类生成：

```cpp
// GDCLASS 展开后的核心逻辑（简化）
virtual String get_class() const {
    if (_extension) {
        return _extension->class_name.operator String();  // GDExtension 类名优先
    }
    return String(#m_class);            // 编译期字符串化："Node2D"
}

virtual bool is_class(const String &p_class) const {
    if (_extension && _extension->is_class(p_class)) {
        return true;
    }
    if (p_class == #m_class) {
        return true;
    }
    return m_inherits::is_class(p_class);   // 沿继承链向上递归
}
```

这就是 `is_class("Object")` 能对任何对象返回 `true` 的原因：**没有成员变量记录继承链，匹配靠宏递归逐级向上比对字符串**。C++ 侧的类型安全转换同样由宏提供：

```cpp
template <typename T>
static T *cast_to(Object *p_object) {
    return dynamic_cast<T *>(p_object);
}
```

GDScript 侧对应的是 `is` 运算符与 `as` 转换，语义一致但走的是脚本层的快速路径。

### 3.3 ObjectID 与 instance_from_id

```gdscript
var id := node.get_instance_id()          # 64 位整数，进程内唯一
# ……即使 node 已被释放，id 依然有效（只是查不到对象了）
var obj := instance_from_id(id)           # 释放后返回 null
if obj:
    obj.queue_free()
```

`ObjectID` 是跨帧安全持有"对象引用"的**唯一**合法方式——不阻止释放、也不悬垂。它底层对应 ObjectDB 中的哈希表条目，常用于网络同步、编辑器工具与回调的"迟到访问"场景。

---

## 四、反射机制

### 4.1 属性列表与 usage 标志

`get_property_list()` 每次调用都动态拼装一份 `Array[Dictionary]`，每个元素是一个 `PropertyInfo`。其中最关键的是 `usage` 位标志（节选自源码 `PropertyUsageFlags`）：

| 标志 | 含义 |
|------|------|
| `STORAGE` (1<<1) | 参与序列化（保存场景/资源时写入） |
| `EDITOR` (1<<2) | 在检查器中显示 |
| `INTERNAL` (1<<3) | 内部属性，检查器默认隐藏 |
| `GROUP` / `SUBGROUP` / `CATEGORY` (1<<6/8/7) | 检查器分组 |
| `RESTART_IF_CHANGED` (1<<11) | 修改后提示重启（如项目设置项） |
| `ALWAYS_DUPLICATE` / `NEVER_DUPLICATE` (1<<19/20) | 复制节点时是否深拷贝该资源 |
| `READ_ONLY` (1<<28) | 检查器只读 |
| `SECRET` (1<<29) | 导出时单独存储凭据（如密钥） |

组合常量：`PROPERTY_USAGE_DEFAULT = STORAGE | EDITOR`；`PROPERTY_USAGE_NO_EDITOR = STORAGE`。

**这组标志解释了很多"奇怪现象"**：为什么有的属性保存了有的没保存（`STORAGE`）、为什么脚本变量能在检查器里看到（`SCRIPT_VARIABLE`）、为什么导出后的密钥不在场景文件里（`SECRET`）。

### 4.2 set/get 的路径语义

```gdscript
node.set("position", Vector2(100, 100))
var pos = node.get("position")

# 支持用冒号取"属性的内嵌分量"
node.set("position:x", 200)              # 等价于取 position 再改 x 分量
var x = node.get("position:x")

# 属性列表按继承链聚合：Object 的 + 各级父类的 + 脚本的 + _get_property_list() 提供的
var props: Array[Dictionary] = node.get_property_list()
for prop in props:
    print(prop.name, " usage=", prop.usage)
```

### 4.3 动态方法调用

```gdscript
# 1. 调用方法
node.call("set_position", Vector2(100, 100))

# 2. 检查方法是否存在
if node.has_method("shoot"):
    node.call("shoot")

# 3. 带参数数组调用 / 获取方法列表
node.callv("set_position", [Vector2(100, 100)])
var methods = node.get_method_list()
```

引擎侧每个可调用方法都包着一层 `MethodBind`（`core/object/method_bind.h`），负责参数校验与 Variant 转换——`call()` 的开销主要在这里，热点路径应改为直接调用。

### 4.4 自定义属性列表：_get_property_list()

让自定义类暴露"虚拟属性"（不占成员变量、由 get/set 计算得出）：

```gdscript
class_name ShapedObject
extends Object

var _radius: float = 1.0

# 追加到检查器与 get_property_list() 的属性
func _get_property_list() -> Array[Dictionary]:
    return [{
        "name": "radius",
        "type": TYPE_FLOAT,
        "hint": PROPERTY_HINT_RANGE,
        "hint_string": "0.1,10.0,0.1",
        "usage": PROPERTY_USAGE_EDITOR,     # 只在编辑器可见，不参与序列化
    }]

# 检查器读写时会回调这一对
func _get(property: StringName) -> Variant:
    if property == &"radius":
        return _radius
    return null

func _set(property: StringName, value: Variant) -> bool:
    if property == &"radius":
        _radius = value
        return true
    return false
```

`usage` 不带 `STORAGE` 时该属性不会写进场景文件——这是"编辑器辅助字段"的标准做法。

### 4.5 元数据：set_meta / get_meta

```gdscript
node.set_meta("spawn_time", Time.get_ticks_msec())
print(node.get_meta("spawn_time"))
print(node.has_meta("spawn_time"))       # true
node.remove_meta("spawn_time")
for meta_name in node.get_meta_list():
    print(meta_name)
```

元数据存在对象的 `metadata` 哈希表里，随场景一起序列化——适合给节点挂"路点编号""生成批次"这类不配写脚本的标记。编辑器中的"分组/排序"等节点状态也用它实现。

---

## 五、通知系统

### 5.1 通知常量

`Object` 层定义了 4 条基础通知（数值来自源码枚举）：

| 常量 | 值 | 语义 |
|------|----|------|
| `NOTIFICATION_POSTINITIALIZE` | 0 | 构造后发出，仅引擎内部使用 |
| `NOTIFICATION_PREDELETE` | 1 | 删除前发出，脚本可响应做清理 |
| `NOTIFICATION_EXTENSION_RELOADED` | 2 | GDExtension 热重载后发出 |
| `NOTIFICATION_PREDELETE_CLEANUP` | 3 | PREDELETE 之后的内部通知，不绑定脚本 |

```gdscript
func _notification(what: int) -> void:
    match what:
        NOTIFICATION_PREDELETE:
            print("即将被删除，做最后清理")
```

### 5.2 通知不会自动传播

`Object.notification()` 只作用于对象自身。子节点的 `NOTIFICATION_ENTER_TREE`/`EXIT_TREE` 等能"广播"，是 `Node`/`SceneTree` 层显式递归转发的结果，不是 Object 的能力——自定义的普通 `Object` 子类想广播通知，需要自己写循环。

---

## 六、信号的数据结构（第 6 篇导论）

### 6.1 一张表看清信号存储

源码中每个对象的信号体系由三部分组成（结构名与源码一致）：

```
signal_map: HashMap<StringName, SignalData>   # 我定义的信号
    └── SignalData
        ├── user: MethodInfo                  # 信号原型（参数列表）
        └── slot_map: HashMap<Callable, Slot> # 每个连接的槽
connections: List<Connection>                 # 我连到别人信号上的连接
```

**区分这两张表是理解信号内存行为的关键**：`_exit_tree` 断不开 `signal_map`（那是自己的信号定义），但 `connections` 里的悬垂连接会在对象析构时由引擎统一清理。

### 6.2 ConnectFlags 的真实语义

```cpp
enum ConnectFlags {
    CONNECT_DEFERRED = 1,           // 延迟到帧末才调用槽
    CONNECT_PERSIST = 2,            // 随场景序列化保存连接
    CONNECT_ONE_SHOT = 4,           // 触发一次后自动断开
    CONNECT_REFERENCE_COUNTED = 8,  // 计入目标对象引用计数
    CONNECT_INHERITED = 16,         // 内部使用
};
```

```gdscript
timer.timeout.connect(_on_timeout, CONNECT_DEFERRED)
# 一次性连接：CONNECT_ONE_SHOT 配合 disconnect 使用
# 注意 CONNECT_PERSIST：随场景保存的连接如果目标脚本改名，加载时会报"目标方法不存在"
```

第 6 篇将从 `emit_signal()` 的调用路径继续深入。

---

## 七、ClassDB 类注册系统

### 7.1 注册机制（示意）

所有内置类与 `class_name` 脚本类都登记在 `ClassDB`（`core/object/class_db.cpp`）中：

```cpp
// 简化示意：真实实现是宏生成的模板注册
ClassDB::register_class<T>();          // 可实例化（有 new()）
ClassDB::register_abstract_class<T>(); // 抽象类（无 new()）
ClassDB::register_virtual_class<T>();  // 虚拟类（仅作基类）
```

### 7.2 动态创建与查询

```gdscript
# 通过类名字符串创建对象（4.x 用 instantiate()，3.x 的 instance() 已移除）
var node = ClassDB.instantiate("Sprite2D")
# 等价于
var node = Sprite2D.new()

# 查询继承链与属性（编辑器插件、序列化工具的常用手段）
print(ClassDB.get_parent_class("Node2D"))          # Node
var plist := ClassDB.class_get_property_list("Sprite2D")
print(ClassDB.class_has_method("Sprite2D", "set_texture"))
```

`ClassDB.instantiate()` 是"数据驱动创建节点"的基石——关卡编辑器、插件安装器、存档系统都靠它把字符串变成对象。

---

## 八、与 Unity Object 对比

| 维度 | Godot Object | Unity Object |
|------|-------------|--------------|
| 基类 | `Object`（非 GC，手动/引用计数） | `UnityEngine.Object`（C# 侧由 GC + 原生双重管理） |
| 值对象 | Callable/Signal/ObjectID 为独立类型 | 一切皆 System.Object |
| 生命周期 | `free()` / `queue_free()` / 引用计数 | `Destroy()` / 延迟 Destroy / GC |
| 类型识别 | `is_class()` + GDCLASS 字符串链 | `is` / `GetType()`（CLR 反射） |
| 反射 | `get_property_list()` + usage 标志，序列化内建 | System.Reflection + 特性标记，序列化需 SerializeField |
| 动态调用 | `call()` 直接定位 MethodBind | `SendMessage()` 广播全组件 |
| 类注册 | ClassDB 集中注册 | 程序集扫描 |
| 资源对应 | Resource（RefCounted，自动共享） | ScriptableObject |

最有实操意义的差异是**删除语义**：Unity 依赖 GC，忘记 `Destroy` 只是内存压力；Godot 的 `Object` 不参与 GC，忘记 `free` 就是泄漏，`free` 早了就是悬垂——所以引擎才同时提供 `queue_free()`、`is_instance_valid()`、`weakref()` 这一套防护工具。

---

## 九、总结

Object 类提供：

- **唯一标识**：`ObjectID` + ObjectDB，跨帧安全引用的基石
- **两种所有权**：RefCounted 自动释放 / Object 手动释放，删除流程带否决机制
- **RTTI**：GDCLASS 宏生成字符串比对链，`is_class`/`cast_to` 零注册成本
- **反射**：`get_property_list()` + usage 标志驱动检查器、序列化与复制
- **通知**：`_notification` 是引擎事件的总入口（0/1/2/3 四条基础通知）
- **元数据**：`set_meta` 给任意对象挂运行时标记，随场景序列化
- **信号地基**：`signal_map`/`connections` 两张表，第 6 篇展开

一图速查：

```
创建 → _postinitialize() → ObjectDB 登记 → POSTINITIALIZE(0)
使用 → is_class / get_property_list / set_meta / 信号
删除 → free()/queue_delete() → _predelete() → PREDELETE(1)
     → PREDELETE_CLEANUP(3，内部) → ~Object() → 断开全部连接
```

---

## 🔗 延伸阅读

- **Object**: <https://docs.godotengine.org/en/stable/classes/class_object.html>
- **RefCounted**: <https://docs.godotengine.org/en/stable/classes/class_refcounted.html>
- **ClassDB**: <https://docs.godotengine.org/en/stable/classes/class_classdb.html>
- **源码位置**: `core/object/object.cpp`, `core/object/ref_counted.cpp`, `core/object/class_db.cpp`

---

**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 4 篇：Godot 内存管理机制深度解析](/articles/04-memory-management.md)
**下一篇**: [第 6 篇：Godot 信号系统深度解析](/articles/06-signal-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
