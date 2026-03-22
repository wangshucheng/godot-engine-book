# 深入理解 Godot 引擎 #09 | Godot 序列化系统深度解析

> **摘要**：Godot 的序列化系统基于 Variant 类型系统，支持场景、资源、属性的序列化。本文将深入分析 Variant 类型、属性系统、序列化格式及自定义序列化方法。

---

## 一、序列化系统概述

### 1.1 什么是序列化

序列化是将对象状态转换为可存储格式的过程，Godot 中的序列化应用包括：
- 场景保存为 `.tscn` 文件
- 资源保存为 `.tres` 文件
- 游戏存档（Save/Load）
- 网络传输

### 1.2 Godot 序列化特点

| 特点 | 说明 |
|------|------|
| **基于 Variant** | 所有可序列化类型都是 Variant |
| **文本 + 二进制** | 支持 `.tscn`（文本）和 `.res`（二进制） |
| **类型安全** | 序列化时保留类型信息 |
| **跨平台** | 序列化格式与平台无关 |

---

## 二、Variant 类型系统

### 2.1 Variant 是什么

**Variant** 是 Godot 的变体类型，可以存储任何类型的值。

**源码位置**: `core/variant/variant.h`

```cpp
// Godot 源码 - core/variant/variant.h
class Variant {
    // 类型信息
    Type type;
    
    // 数据（联合体，最大 20 字节）
    union {
        bool _bool;
        int64_t _int;
        double _float;
        Vector2 _vec2;
        Vector3 _vec3;
        Color _color;
        // ... 更多类型
        void *_object;  // 对象指针
    };
    
    // 类型枚举
    enum Type {
        NIL,
        BOOL,
        INT,
        FLOAT,
        STRING,
        VECTOR2,
        VECTOR3,
        COLOR,
        OBJECT,
        // ... 共 40+ 种类型
    };
};
```

### 2.2 Variant 支持的类型

```gdscript
# 基本类型
var a: bool = true
var b: int = 42
var c: float = 3.14
var d: String = "hello"

# 数学类型
var e: Vector2 = Vector2(1, 2)
var f: Vector3 = Vector3(1, 2, 3)
var g: Matrix4 = Transform3D()

# 引擎类型
var h: Node = Node.new()
var i: Texture2D = load("res://texture.png")
var j: Array = [1, 2, 3]
var k: Dictionary = {"key": "value"}
```

### 2.3 Variant 类型转换

```gdscript
# 自动类型转换
var a: int = 10
var b: float = a  # 自动转换为 10.0

# 显式类型转换
var c: String = str(a)  # "10"
var d: int = int("42")  # 42

# Variant 类型检查
var v: Variant = anything
if v is int:
    print("是整数")
elif v is String:
    print("是字符串")

# 获取类型
print(typeof(v))  # TYPE_INT, TYPE_STRING, etc.
```

---

## 三、属性系统

### 3.1 属性定义

Godot 使用 `@export` 注解定义可序列化属性：

```gdscript
class_name PlayerData
extends Resource

# 基本类型
@export var name: String
@export var health: int
@export var speed: float

# 引擎类型
@export var texture: Texture2D
@export var scene: PackedScene

# 数组和字典
@export var items: Array[String]
@export var stats: Dictionary

# 枚举
@export_enum("Warrior", "Mage", "Archer") var class_type: int

# 范围
@export_range(0, 100) var mana: int

# 文件路径
@export_file("*.png", "*.jpg") var icon_path: String

# 多行文本
@export_multiline var description: String
```

### 3.2 属性序列化

**源码位置**: `core/object/property_info.h`

```cpp
// Godot 源码 - core/object/property_info.h
struct PropertyInfo {
    Variant::Type type;      // 类型
    StringName name;         // 名称
    String hint_string;      // 提示字符串
    PropertyUsageFlags usage; // 使用标志
    
    // 序列化时保存的信息
    void serialize(Variant &r_value);
    void deserialize(const Variant &p_value);
};
```

### 3.3 属性访问

```gdscript
# 动态访问属性
func _ready():
    # 获取属性列表
    var props = get_property_list()
    
    for prop in props:
        print("属性：", prop.name, " 类型：", prop.type)
    
    # 动态获取/设置属性
    var health = get("health")
    set("health", 100)
    
    # 检查属性是否存在
    if has_method("get_health"):
        print("有 get_health 方法")
```

---

## 四、序列化格式

### 4.1 .tscn 格式（场景）

```ini
[gd_scene load_steps=3 format=3 uid="uid://abc123"]

[ext_resource type="Script" path="res://player.gd" id="1"]
[ext_resource type="Texture2D" path="res://player.png" id="2"]

[node name="Player" type="CharacterBody3D"]
script = ExtResource("1")
position = Vector3(0, 1, 0)

[node name="Mesh" type="MeshInstance3D" parent="."]
mesh = SubResource("SphereMesh")
material/0 = ExtResource("2")

[node name="Collision" type="CollisionShape3D" parent="."]
shape = SubResource("SphereShape")

[connection signal="hit" from="." to="Mesh" method="_on_hit"]
```

### 4.2 .tres 格式（资源）

```ini
[gd_resource type="Resource" format=3]

[resource]
resource_name = "PlayerData"
name = "Hero"
health = 100
mana = 50
level = 1
inventory = [
SubResource("Item_001"),
SubResource("Item_002")
]
```

### 4.3 .res 格式（二进制）

```
二进制格式，不可读
- 更小的文件大小
- 更快的加载速度
- 用于生产环境
```

### 4.4 格式对比

| 格式 | 扩展名 | 可读性 | 大小 | 加载速度 | 使用场景 |
|------|--------|--------|------|---------|---------|
| 文本场景 | .tscn | ✅ 可读 | 较大 | 较慢 | 开发环境 |
| 文本资源 | .tres | ✅ 可读 | 较大 | 较慢 | 开发环境 |
| 二进制场景 | .scn | ❌ 不可读 | 小 | 快 | 生产环境 |
| 二进制资源 | .res | ❌ 不可读 | 小 | 快 | 生产环境 |

---

## 五、自定义序列化

### 5.1 实现 _to_string()

```gdscript
class_name CustomData
extends Resource

@export var name: String
@export var value: int

# 自定义字符串表示
func _to_string() -> String:
    return "CustomData(name=%s, value=%d)" % [name, value]
```

### 5.2 使用 _set 和 _get

```gdscript
class_name AdvancedData
extends Resource

var _internal_data = {}

# 自定义属性获取
func _get(property: StringName) -> Variant:
    if property in _internal_data:
        return _internal_data[property]
    return null

# 自定义属性设置
func _set(property: StringName, value: Variant) -> bool:
    _internal_data[property] = value
    return true

# 列出可用属性
func _get_property_list() -> Array[Dictionary]:
    var props = []
    for key in _internal_data:
        props.append({
            "name": key,
            "type": typeof(_internal_data[key]),
            "usage": PROPERTY_USAGE_DEFAULT
        })
    return props
```

### 5.3 序列化到 JSON

```gdscript
# 序列化为 JSON
func save_to_json(path: String) -> Error:
    var data = {
        "name": name,
        "health": health,
        "inventory": inventory
    }
    
    var json_string = JSON.stringify(data, "  ")
    
    var file = FileAccess.open(path, FileAccess.WRITE)
    file.store_string(json_string)
    file.close()
    
    return OK

# 从 JSON 反序列化
func load_from_json(path: String) -> Error:
    var file = FileAccess.open(path, FileAccess.READ)
    var json_string = file.get_as_text()
    file.close()
    
    var json = JSON.new()
    var error = json.parse(json_string)
    
    if error != OK:
        return error
    
    var data = json.get_data()
    name = data["name"]
    health = data["health"]
    inventory = data["inventory"]
    
    return OK
```

---

## 六、与 Unity 序列化对比

### 6.1 Unity 序列化

```csharp
// Unity - 序列化
[System.Serializable]
public class PlayerData {
    public string name;
    public int health;
    public float speed;
}

// 保存到 JSON
string json = JsonUtility.ToJson(playerData);
File.WriteAllText(path, json);

// 从 JSON 加载
PlayerData data = JsonUtility.FromJson<PlayerData>(json);
```

### 6.2 对比表

| 维度 | Godot | Unity |
|------|-------|-------|
| **类型系统** | Variant（40+ 类型） | System.Type |
| **序列化格式** | .tscn/.tres（文本）<br/>.scn/.res（二进制） | .prefab（YAML）<br/>.json（JSON） |
| **属性注解** | @export | [SerializeField] |
| **自定义序列化** | _set/_get/_to_string | ISerializationCallbackReceiver |
| **JSON 支持** | 内置 JSON 类 | JsonUtility |
| **二进制序列化** | 内置支持 | 需要 BinaryFormatter |

### 6.3 Godot 序列化优势

- ✅ Variant 类型丰富（40+ 内置类型）
- ✅ 文本格式可读性强
- ✅ 二进制格式高效
- ✅ 序列化/反序列化一致性好
- ✅ 跨平台兼容性好

---

## 七、序列化最佳实践

### 7.1 使用 Resource 保存数据

```gdscript
# ✅ 推荐：使用 Resource
class_name SaveData
extends Resource

@export var player_name: String
@export var level: int
@export var inventory: Array

# 保存
func save(path: String):
    ResourceSaver.save(self, path)

# 加载
static func load(path: String) -> SaveData:
    return ResourceLoader.load(path) as SaveData
```

### 7.2 版本控制

```gdscript
class_name SaveData
extends Resource

@export var version: int = 1
@export var player_name: String
@export var level: int

# 版本迁移
func migrate():
    if version < 2:
        # 版本 1 到 2 的迁移逻辑
        pass
    version = 2
```

### 7.3 数据验证

```gdscript
func validate() -> bool:
    if health < 0 or health > 100:
        print("Invalid health value")
        return false
    
    if inventory.size() > MAX_INVENTORY_SIZE:
        print("Inventory too large")
        return false
    
    return true
```

---

## 八、总结

### 核心要点

1. **Variant 类型系统**是 Godot 序列化的基础
2. **@export 注解**定义可序列化属性
3. **多种格式**支持（.tscn/.tres/.scn/.res）
4. **自定义序列化**通过 _set/_get 实现
5. **JSON 序列化**用于跨平台数据交换

### 与 Unity 对比

| 特性 | Godot | Unity |
|------|-------|-------|
| 类型系统 | Variant | System.Type |
| 格式 | 文本 + 二进制 | YAML + JSON |
| 易用性 | ✅ 高 | ✅ 高 |

### 下一篇文章

**第一卷最后一篇**：Godot 跨平台架构详解

敬请期待！

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #08 | Godot 文件系统](#)  
**下一篇**: [深入理解 Godot 引擎 #10 | Godot 跨平台架构详解](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
