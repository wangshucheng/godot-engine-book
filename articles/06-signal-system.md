# 深入理解 Godot 引擎 #06 | Godot 信号系统深度解析

> **摘要**：信号（Signal）是 Godot 的观察者模式实现，用于节点间松耦合通信。本文将深入分析信号的底层实现、连接机制、性能优化。

---

## 一、信号概述

### 1.1 什么是信号

信号是 Godot 的**事件机制**，允许节点间松耦合通信。

**核心特点**：
- 发射者不需要知道监听者
- 一个信号可以连接多个处理函数
- 类型安全（Godot 4.x 增强）

### 1.2 信号使用示例

```gdscript
# 定义信号
signal health_changed(new_value: int)
signal player_died

# 发射信号
health_changed.emit(50)
player_died.emit()

# 连接信号
$HealthComponent.health_changed.connect(_on_health_changed)

# 断开连接
$HealthComponent.health_changed.disconnect(_on_health_changed)
```

---

## 二、信号底层实现

### 2.1 源码结构

**源码位置**: `core/object/object.h`

```cpp
class Object {
    // 信号连接列表
    HashMap<StringName, SignalConnectionList> signal_connections;
    
    // 连接信号
    Error connect(
        const StringName &p_signal,
        Callable p_callable,
        bitfield<ConnectFlags> p_flags = 0
    );
    
    // 发射信号
    void emit_signal(const StringName &p_name, const Variant **p_args, int p_argcount);
};
```

### 2.2 连接机制

```cpp
// 信号连接流程
void Object::connect(...) {
    // 1. 检查信号是否存在
    if (!has_signal(p_signal)) {
        ERR_FAIL_MSG("Signal not found");
    }
    
    // 2. 添加到连接列表
    signal_connections[p_signal].add(p_callable);
    
    // 3. 如果是 DEFERRED 标志，使用延迟调用
    if (p_flags & CONNECT_DEFERRED) {
        MessageQueue::push_call(...);
    }
}
```

---

## 三、高级特性

### 3.1 信号标志

```gdscript
# 普通连接
signal.connect(handler)

# 一次性连接（触发后自动断开）
signal.connect(handler, CONNECT_ONE_SHOT)

# 延迟调用（下一帧执行）
signal.connect(handler, CONNECT_DEFERRED)

# 弱引用（不阻止对象释放）
signal.connect(handler, CONNECT_REFERENCE_COUNTED)
```

### 3.2 信号组

```gdscript
# 连接到组中所有节点
get_tree().connect("node_added", self, "_on_node_added")

# 组信号广播
get_tree().call_group("enemies", "take_damage", 10)
```

---

## 四、性能优化

### 4.1 连接 vs 轮询

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

### 4.2 避免信号泄漏

```gdscript
# ✅ 正确做法
func _ready():
    some_node.connect("signal", self, "_on_signal")

func _exit_tree():
    # 节点离开场景树时自动断开
    # 但手动断开更安全
    some_node.disconnect("signal", self, "_on_signal")
```

---

## 五、与 Unity UnityEvent 对比

| 维度 | Godot Signal | Unity UnityEvent |
|------|-------------|------------------|
| 语法 | 内置语言支持 | 需要 delegate |
| 类型安全 | ✅ 强类型 | ⚠️ 部分类型 |
| 性能 | 高 | 中 |
| Inspector 配置 | ❌ 代码 | ✅ 可视化 |
| 异步支持 | ✅ 内置 | ⚠️ 需额外处理 |

---

## 六、总结

信号系统优势：
- ✅ 松耦合通信
- ✅ 类型安全
- ✅ 性能优秀
- ✅ 易于维护

**下一篇**: Godot 资源系统
