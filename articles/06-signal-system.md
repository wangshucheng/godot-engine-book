# 第 6 篇：Godot 信号系统深度解析

> **摘要**：信号（Signal）是 Godot 的观察者模式实现，用于节点间松耦合通信。本文基于 `core/object/object.cpp` 的真实实现，剖析 `connect()` 的三段校验、`emit_signalp()` 的六步执行管线、`CONNECT_DEFERRED` 背后的 MessageQueue、ONE_SHOT 的防重入设计、引用计数连接的判重规则，并给出生命周期与性能的实战清单。

---

## 一、信号概述

### 1.1 什么是信号

信号是 Godot 的**事件机制**，允许对象间松耦合通信。

**核心特点**：
- 发射者不需要知道监听者
- 一个信号可以连接多个处理函数
- 类型安全（Godot 4.x 支持 typed signal 参数）
- `Callable` 是一等公民——连接的双方都以它表示

### 1.2 基本用法

```gdscript
# 定义信号（4.x 支持参数类型标注）
signal health_changed(new_value: int)
signal player_died

# 发射信号
health_changed.emit(50)
player_died.emit()

# 连接与断开
$HealthComponent.health_changed.connect(_on_health_changed)
$HealthComponent.health_changed.disconnect(_on_health_changed)

# 等待信号（协程语义）
await $HealthComponent.health_changed
await get_tree().create_timer(1.0).timeout
```

### 1.3 Signal 与 Callable：两种一等公民类型

连接的两端各自被抽象成一个值类型，可以像普通变量一样传递：

```gdscript
# Signal：信号的"发送端"引用
var sig := $HealthComponent.health_changed
sig.emit(50)                          # 直接发射
sig.connect(_on_health_changed)       # 一样能连接
print(sig.get_name())                 # "health_changed"
print(sig.get_object())               # 发射者对象
for conn in sig.get_connections():    # 这条信号上的全部连接
    print(conn.signal, " -> ", conn.callable)

# Callable：信号的"接收端"引用
var cb := _on_health_changed
cb.call(50)
cb = cb.bind(100)                     # 预绑定参数，发射值排在绑定值之后
print(cb.get_object())                # 持有该方法的实例
print(cb.is_valid())                  # 目标是否仍然可调用
```

`Callable` 的 `bind()` 是解耦参数顺序的核心工具：**发射时传入的实参排在 `bind()` 绑定值的前面**。

---

## 二、数据的真实布局

### 2.1 两张表：signal_map 与 connections

**源码位置**: `core/object/object.h`（成员结构在第 5 篇已展示）

每个 Object 有两张职责不同的表：

```
signal_map: HashMap<StringName, SignalData>
    ├── "health_changed" → SignalData
    │     ├── user: MethodInfo                 # 信号原型（用户信号才有内容）
    │     └── slot_map: HashMap<Callable, Slot># 每条连接一个槽
    │           └── Slot { reference_count, Connection conn, cE }
    └── "died" → SignalData

connections: List<Connection>        # 本对象连到【别人】信号上的记录
    └── Connection { Signal signal, Callable callable, uint32_t flags }
```

- **`signal_map`**：我是发射者。键是信号名。
- **`connections`**：我是接收者。记录我订阅了谁，析构时由引擎统一摘除，避免悬垂。

```cpp
// Connection 的真实结构与连接标志
struct Connection {
    ::Signal signal;
    Callable callable;
    uint32_t flags = 0;
};
enum ConnectFlags {
    CONNECT_DEFERRED = 1,
    CONNECT_PERSIST = 2,
    CONNECT_ONE_SHOT = 4,
    CONNECT_REFERENCE_COUNTED = 8,
    CONNECT_INHERITED = 16,
};
```

### 2.2 connect() 的真实签名

```cpp
// 4.x 的公开签名（返回 Error，而不是 void）
Error Object::connect(const StringName &p_signal,
                      const Callable &p_callable,
                      uint32_t p_flags = 0);

// 变参入口（脚本侧 emit_signal("xxx", ...) 走这里）
Error Object::_emit_signal(const Variant **p_args, int p_argcount, ...);
```

**`connect()` 返回 `Error`**，"重复连接"这类错误是可以通过返回值感知的，不必靠 `is_connected()` 预判。

---

## 三、connect() 的完整校验流程

### 3.1 信号从哪来

`connect()` 时允许的信号有三种来源，按顺序校验：

1. **`signal_map` 里已有**——引擎内置信号或已连接过的信号；
2. **`ClassDB::has_signal(get_class_name(), p_signal)`**——类级内置信号（`ADD_SIGNAL` 宏注册）；
3. **脚本信号**——`signal` 关键字声明，或 `add_user_signal()` 注册。

```cpp
// 简化自 object.cpp
SignalData *s = signal_map.getptr(p_signal);
if (!s) {
    bool signal_is_valid = ClassDB::has_signal(get_class_name(), p_signal);
    // ……脚本信号检查；编辑器下脚本无效时也允许连接（issue #17070，
    //    支持"先连后写"的工作流）
    ERR_FAIL_COND_V_MSG(!signal_is_valid, ERR_INVALID_PARAMETER,
        "Attempt to connect nonexistent signal ...");
    signal_map[p_signal] = SignalData();   // 信号存在但首次连接 → 建表
    s = &signal_map[p_signal];
}
```

**关键点：连接一个"存在但尚无连接"的信号，会现场在 `signal_map` 里创建条目**——所以发射端的 `signal_map` 不只包含定义，还包含"被连接过"的痕迹。

### 3.2 重复连接：按"基础 Callable"判重

```cpp
if (s->slot_map.has(*p_callable.get_base_comparator())) {
    if (p_flags & CONNECT_REFERENCE_COUNTED) {
        s->slot_map[...].reference_count++;   // 引用计数连接：重复连接只 +1
        return OK;
    }
    return ERR_INVALID_PARAMETER;             // 普通连接：报"already connected"
}
```

`get_base_comparator()` 返回**剥掉 `bind()` 参数后的基础 Callable**——这意味着 `cb.bind(1)` 与 `cb.bind(2)` 被视为**同一条连接**，重复连接第二条会报错。这是很多"为什么我的 bind 连不上两次"问题的根源。

### 3.3 标志的存储与反向链接

```cpp
Connection conn;
conn.callable = p_callable;
conn.signal = ::Signal(this, p_signal);
conn.flags = p_flags;                        // 所有标志都存进 conn.flags
slot.conn = conn;
if (target_object) {
    slot.cE = target_object->connections.push_back(conn);  // 反向登记
}
if (p_flags & CONNECT_REFERENCE_COUNTED) {
    slot.reference_count = 1;
}
s->slot_map[*p_callable.get_base_comparator()] = slot;
```

**CONNECT_DEFERRED 在 connect() 阶段什么也不做**——它只是被存进 `conn.flags`，真正的延迟发生在发射时（下一节）。

---

## 四、emit_signal 的执行管线

### 4.1 六步流程

```cpp
// 简化自 Error Object::emit_signalp(...)
Error Object::emit_signalp(const StringName &p_name, const Variant **p_args, int p_argcount) {
    if (_block_signals) {
        return ERR_CANT_ACQUIRE_RESOURCE;    // ① 发射被阻塞，直接返回
    }
    SignalData *s = signal_map.getptr(p_name);
    if (!s) {
        // ② 信号不存在（DEBUG 下报错）或存在但无人连接 → 静默返回
        return ERR_UNAVAILABLE;
    }
    // ③ 防止发射期间自身被释放
    Ref<RefCounted> rc = Ref<RefCounted>(Object::cast_to<RefCounted>(this));
    // ④ 把槽快照拷到栈上，防止发射过程中连接表被修改
    Callable *slot_callables = (Callable *)alloca(sizeof(Callable) * s->slot_map.size());
    // ……
    // ⑤ ONE_SHOT 连接在发射前统一断开（防递归重入）
    for (...) {
        if (slot_flags[i] & CONNECT_ONE_SHOT) { _disconnect(p_name, slot_callables[i]); }
    }
    // ⑥ 逐个调用：DEFERRED 入队，同步调用直接执行
    for (...) {
        if (!callable.is_valid()) {
            continue;   // "Target might have been deleted during signal callback"
        }
        if (flags & CONNECT_DEFERRED) {
            MessageQueue::get_singleton()->push_callablep(callable, args, argc, true);
        } else {
            _emitting = true;
            callable.callp(args, argc, ret, ce);
            _emitting = false;
        }
    }
}
```

六个步骤各自解决一个真实问题：

| 步骤 | 解决的问题 |
|------|-----------|
| ① 阻塞检查 | `block_signals()` 期间的批量操作不想触发任何监听者 |
| ② 静默返回 | "发了一个没人听的信号"是正常业务，不该报错 |
| ③ keep-alive | 槽函数里把发射者释放掉（issue #73889）导致后续访问悬垂 |
| ④ 栈上快照 | 槽函数里连接/断开同一条信号，遍历时表被改 |
| ⑤ 预先断开 ONE_SHOT | 槽函数里再次发射同一信号导致无限递归 |
| ⑥ is_valid 检查 | 前一个槽把后一个槽的宿主删了 |

### 4.2 未连接信号的静默语义

```gdscript
signal never_connected
never_connected.emit()      # 返回 ERR_UNAVAILABLE，但不报错——没人听是合法业务

undefined_signal.emit()     # 信号本身不存在：DEBUG 构建报错，release 静默返回
```

**`emit_signal()` 是有返回值的**，返回 `OK` / `ERR_UNAVAILABLE` / `ERR_CANT_ACQUIRE_RESOURCE` / `ERR_METHOD_NOT_FOUND`。需要确认"确实有人收到"时，检查返回值而不是靠感觉。

### 4.3 CONNECT_DEFERRED 的真实实现

DEFERRED 与 `connect()` 无关，它的全部逻辑在发射那一刻：

```cpp
if (flags & CONNECT_DEFERRED) {
    MessageQueue::get_singleton()->push_callablep(callable, args, argc, true);
}
```

即**把调用推进引擎的全局 MessageQueue，帧末统一执行**。由此推导出三条实用规则：

1. 延迟槽拿到的是**帧末的世界状态**，不是发射瞬间的状态；
2. 若对象在帧末前被删除，入队的调用因 `Callable` 失效而自动跳过（不会再崩）；
3. DEFERRED 改变的是"何时执行"，不改变"参数是什么"——需要快照状态请自己传值。

### 4.4 发射期间的自我保护

两处容易被忽略的防御设计：

```cpp
// ① 槽函数执行期间释放发射者：引用保活
Ref<RefCounted> rc = Ref<RefCounted>(Object::cast_to<RefCounted>(this)); // issue #73889

// ② 在发射中释放/销毁发射者：析构函数会给出诊断
if (_emitting) {
    ERR_PRINT("Object ... was freed or unreferenced while a signal is being emitted from it.");
}
```

`_emitting` **不阻止任何事**，它只是诊断标志——但它把"在信号回调里删除发射者"这个错误从"随机崩溃"变成了"明确的错误日志"。

### 4.5 调用失败的宽容策略

```cpp
if (ce.error != Callable::CallError::CALL_OK) {
    // 编辑器中非 tool 脚本的持久连接失败 → 静默跳过（场景逐个加载时方法可能还没就绪）
    // 目标类尚未注册 → 静默跳过（"most likely object is not initialized yet"）
    // 其余 → ERR_PRINT + 返回 ERR_METHOD_NOT_FOUND
}
```

---

## 五、断开与阻塞

### 5.1 disconnect 的细节

```cpp
bool Object::_disconnect(const StringName &p_signal, const Callable &p_callable, bool p_force)
```

- 断开不存在的连接会**报错**（想安全断开先用 `is_connected()` 判断）；
- `CONNECT_REFERENCE_COUNTED` 连接需要断开**相应次数**才真正解除（每次 `-1`），`p_force = true` 可跳过计数（析构清理用）；
- 断开时同步摘除**目标对象** `connections` 列表里的反向记录；
- **内置信号**的连接数归零后条目会从 `signal_map` 删除，**用户信号**（`add_user_signal`/`signal` 声明）则保留定义。

### 5.2 block_signals 的边界

```gdscript
block_signals(true)      # 之后本对象 emit_signal 全部返回错误码，不调用任何槽
# ……批量修改状态……
block_signals(false)
```

三条精确边界：

1. **只管发射端**：不影响该对象作为接收方收到的信号；
2. **返回错误码而非崩溃**：`ERR_CANT_ACQUIRE_RESOURCE`，调用方可感知被 block；
3. **管不住已入队的延迟调用**：DEFERRED 调用在发射时已入 MessageQueue，block 不会撤回它们。

---

## 六、实战模式与陷阱

### 6.1 连接 vs 轮询

```gdscript
# ❌ 不好：每帧轮询
func _process(delta):
    if health != last_health:
        _on_health_changed(health)

# ✅ 好：使用信号
signal health_changed
func take_damage(amount):
    health -= amount
    health_changed.emit(health)
```

### 6.2 生命周期与泄漏

```gdscript
# ✅ 正确做法
func _ready():
    some_node.signal_name.connect(_on_signal)

func _exit_tree():
    # 连接不会阻止接收方（自己）释放，但会让发射方一直持有 Callable；
    # 显式断开让发射方的 connections 表保持干净
    some_node.signal_name.disconnect(_on_signal)
```

希望"监听者被发射者保活"时，用引用计数连接：

```gdscript
some_node.signal_name.connect(_on_signal, CONNECT_REFERENCE_COUNTED)
# 重复 connect 只会 +1，需要 disconnect 相同次数才真正解除
```

### 6.3 常见陷阱清单

| 陷阱 | 原因（源码依据） | 对策 |
|------|------------------|------|
| 场景重载后连接报"already connected" | `slot_map` 按基础 Callable 判重，编辑器保存的 PERSIST 连接还在 | 检查 `is_connected()` 再连，或改用 `CONNECT_REFERENCE_COUNTED` |
| 槽函数参数不匹配 | 发射时逐槽校验，失败走 `ERR_PRINT` 并返回 `ERR_METHOD_NOT_FOUND` | 参数不足的槽用 `Callable.bind()` 补齐 |
| 在信号回调里删除发射者 | 有 keep-alive 保护不会立刻崩，但析构时会打印错误 | 改用 `queue_free()` 或 DEFERRED 连接 |
| `await` 一个永远不发的信号 | 协程永久挂起，其后的代码不再执行 | 配套设计"完成/失败"双信号，或加超时 |
| 同一信号接了几十个槽 | 每次发射都同步遍历全部槽 | 高频事件改轮询/直接调用，或合并信号 |
| 编辑器里连的场景连接运行时报方法不存在 | PERSIST + 非 tool 脚本的调用失败在编辑器中被静默跳过 | 场景连接的目标脚本加 `@tool` 或改代码连接 |

### 6.4 实用 API 速查

```gdscript
# 检查与枚举
if some_node.is_connected("health_changed", _on_health_changed):
    some_node.disconnect("health_changed", _on_health_changed)

for sig_info in some_node.get_signal_list():          # 全部信号（含继承）
    print(sig_info.name, sig_info.args)
for conn in some_node.get_signal_connection_list("health_changed"):
    print(conn.callable)                              # 这条信号现有的连接
for conn in some_node.get_incoming_connections():     # 我订阅了谁
    print(conn.signal, " -> ", conn.callable)

# 实例级自定义信号（无需 signal 关键字，逐实例注册）
add_user_signal("leveled_up", [{"name": "level", "type": TYPE_INT}])
emit_signal("leveled_up", 3)
```

`add_user_signal()` 注册的是**实例级**信号（区别于 `signal` 关键字的类级信号），名称不能与内置信号冲突，且只有它注册的信号可被 `remove_user_signal` 移除。

---

## 七、与 Unity UnityEvent 对比

| 维度 | Godot Signal | Unity UnityEvent |
|------|-------------|------------------|
| 语法 | 内置语言支持 + `Callable` 一等公民 | 需要 delegate / UnityEvent 字段 |
| 类型安全 | ✅ typed signal 编译期校验 | ⚠️ 部分类型 |
| 性能 | 同步调用直达 Callable，无反射 | 中（内部走反射/序列化） |
| 编辑器配置 | ✅ 节点面板可视化连接（存为 PERSIST 连接） | ✅ 可视化 |
| 延迟执行 | ✅ `CONNECT_DEFERRED`（MessageQueue 帧末） | ⚠️ 需自行排队 |
| 发射返回值 | ✅ `Error` 可感知"没人听/失败" | ❌ void |
| 动态参数绑定 | ✅ `Callable.bind()` | ⚠️ 需闭包 |

---

## 八、总结

信号系统的全部行为都由两张表和一条发射管线决定：

```
connect  → 校验信号来源（ClassDB/脚本）→ 建槽（按基础 Callable 判重）→ 反向登记
emit     → block? → 查表（无人连接则静默）→ 保活 + 快照
         → 断开 ONE_SHOT → 逐槽调用（DEFERRED 入 MessageQueue）
disconnect → 计数递减 → 摘除双向记录 → 空表清理（内置信号）
```

设计上值得学习的三处：

- **"无人监听"是合法状态**：发射静默返回错误码，把"广播"与"点名"分开；
- **发射期间的防御是成体系的**：保活、快照、预断开 ONE_SHOT、逐槽 `is_valid`，各挡一类竞态；
- **一切皆 Callable**：bind/unbind 与引用语义让"信号 + 部分参数"无需闭包语法糖。

---

## 🔗 延伸阅读

- **Signal**: <https://docs.godotengine.org/en/stable/classes/class_signal.html>
- **Callable**: <https://docs.godotengine.org/en/stable/classes/class_callable.html>
- **Object.connect()**: <https://docs.godotengine.org/en/stable/classes/class_object.html#class-object-method-connect>
- **源码位置**: `core/object/object.cpp`（`emit_signalp`/`connect`/`_disconnect`）, `core/object/message_queue.cpp`（DEFERRED 派发）

---

**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 5 篇：Godot 对象系统深度解析](/articles/05-object-system.md)
**下一篇**: [第 7 篇：Godot 资源系统深度解析](/articles/07-resource-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
