# 深入理解 Godot 引擎 #05 | Godot 对象系统深度解析

> **摘要**：Object 类是 Godot 所有对象的基类，提供 RTTI、反射、属性系统等核心功能。本文将深入分析 Object 类结构、类型识别机制、反射系统实现。

---

## 一、Object 类结构

### 1.1 Object 类定义

**源码位置**: `core/object/object.h`

```cpp
class Object : public RefCounted {
    // 对象 ID（唯一标识）
    ObjectID _instance_id;
    
    // 元数据
    HashMap<StringName, Variant> metadata;
    
    // 用户数据
    void *_user_data = nullptr;
    
    // 信号连接
    SignalConnectionList signal_connections;
    
    // 属性
    PropertyInfoList property_list;
};
```

### 1.2 Object 继承体系

```
Object (所有对象基类)
├── RefCounted (引用计数对象)
│   ├── Resource (资源)
│   ├── Material (材质)
│   └── ...
└── Node (场景节点)
    ├── Node2D (2D 节点)
    ├── Node3D (3D 节点)
    └── ...
```

---

## 二、RTTI 与类型识别

### 2.1 类型系统

Godot 使用 **Variant** 类型系统支持动态类型：

```gdscript
var a: int = 10
var b: String = "hello"
var c: Node = Node.new()
var d: Variant = anything  # 可以是任何类型
```

### 2.2 类型识别方法

```gdscript
# 1. 获取类型
print(typeof(a))  # TYPE_INT
print(typeof(c))  # TYPE_OBJECT

# 2. 类型检查
if c is Node:
    print("是 Node 类型")

# 3. 获取类名
print(c.get_class())  # "Node"

# 4. 类型转换
var node = c as Node
```

---

## 三、反射机制

### 3.1 动态调用方法

```gdscript
# 1. 调用方法
node.call("set_position", Vector2(100, 100))

# 2. 检查方法是否存在
if node.has_method("shoot"):
    node.call("shoot")

# 3. 获取方法列表
var methods = node.get_method_list()
```

### 3.2 动态属性访问

```gdscript
# 1. 设置属性
node.set("position", Vector2(100, 100))

# 2. 获取属性
var pos = node.get("position")

# 3. 获取属性列表
var props = node.get_property_list()
```

---

## 四、ClassDB 类注册系统

### 4.1 类注册

```cpp
// Godot 源码 - core/object/class_db.cpp
void ClassDB::register_class<T>() {
    // 注册类到 ClassDB
    ClassInfo info;
    info.name = T::get_class_static();
    info.parent = T::get_parent_class_static();
    
    // 注册方法
    for (auto &method : T::get_method_list()) {
        info.method_list.push_back(method);
    }
    
    class_map[info.name] = info;
}
```

### 4.2 动态创建对象

```gdscript
# 通过类名创建对象
var node = ClassDB.instantiate("Sprite2D")

# 等价于
var node = Sprite2D.new()
```

---

## 五、与 Unity Object 对比

| 维度 | Godot Object | Unity Object |
|------|-------------|--------------|
| 基类 | Object | UnityEngine.Object |
| 类型系统 | Variant | System.Type |
| 反射 | 内置 | System.Reflection |
| 动态调用 | call() | SendMessage() |
| 类注册 | ClassDB | 特性标记 |

---

## 六、总结

Object 类提供：
- RTTI 类型识别
- 反射机制
- 属性系统
- 信号系统基础

**下一篇**: Godot 信号系统
