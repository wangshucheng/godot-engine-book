# 第 9 篇：Godot 序列化系统深度解析

> **本章导读**：Godot 的序列化建立在 **Variant** 这个动态类型系统上，理解 Variant 就理解了场景文件、`.tres`、`.res` 与网络字节流。
> 本章讲清 Variant 的类型表与转换规则、属性系统与 `PropertyInfo`、场景与资源的两种存储格式的差别、如何用 `_get_property_list` / `_set` / `_get` 实现自定义序列化，以及自定义 `ResourceFormatLoader` / `ResourceFormatSaver` 的入口。
> **前置知识**：第 7 篇《Godot 资源系统深度解析》
> **难度**：进阶。

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
// Godot 源码 - core/variant/variant.h（Godot 4.3，节选）
class Variant {
public:
	// If this changes the table in variant_op must be updated
	enum Type {
		NIL,

		// atomic types
		BOOL,
		INT,
		FLOAT,
		STRING,

		// math types
		VECTOR2,
		VECTOR2I,
		RECT2,
		RECT2I,
		VECTOR3,
		VECTOR3I,
		TRANSFORM2D,
		VECTOR4,
		VECTOR4I,
		PLANE,
		QUATERNION,
		AABB,
		BASIS,
		TRANSFORM3D,
		PROJECTION,

		// misc types
		COLOR,
		STRING_NAME,
		NODE_PATH,
		RID,
		OBJECT,
		CALLABLE,
		SIGNAL,
		DICTIONARY,
		ARRAY,

		// typed arrays
		PACKED_BYTE_ARRAY,
		PACKED_INT32_ARRAY,
		PACKED_INT64_ARRAY,
		PACKED_FLOAT32_ARRAY,
		PACKED_FLOAT64_ARRAY,
		PACKED_STRING_ARRAY,
		PACKED_VECTOR2_ARRAY,
		PACKED_VECTOR3_ARRAY,
		PACKED_COLOR_ARRAY,
		PACKED_VECTOR4_ARRAY,

		VARIANT_MAX
	};

private:
	Type type = NIL;

	struct ObjData {
		ObjectID id;
		Object *obj = nullptr;
	};

	union {
		bool _bool;
		int64_t _int;
		double _float;
		Transform2D *_transform2d;
		::AABB *_aabb;
		Basis *_basis;
		Transform3D *_transform3d;
		Projection *_projection;
		PackedArrayRefBase *packed_array;
		void *_ptr;                                        // 泛型指针
		uint8_t _mem[sizeof(ObjData) > (sizeof(real_t) * 4)
				? sizeof(ObjData) : (sizeof(real_t) * 4)]{ 0 };
	} _data alignas(8);
	// ...
};
```

共 **39 种类型 + `VARIANT_MAX` 哨兵**。几个容易漏的：

- **`VECTOR4` / `VECTOR4I` / `PLANE` / `PROJECTION`** —— 4.x 新增或补齐的数学类型；
- **`CALLABLE` / `SIGNAL`** —— 可调用对象与信号本身也是 Variant；
- **`RID`** —— 渲染服务器等服务器层的资源句柄；
- **10 种 `PACKED_*_ARRAY`** —— 与 `Array` 语义相同但内存连续的打包数组。

> ⚠️ **Variant 不是"最大 20 字节"**。4.3 源码里的原话是：
> *"Variant takes 24 bytes when real_t is float, and 40 bytes if double. It only allocates extra memory for AABB/Transform2D (24, 48 if double), Basis/Transform3D (48, 96 if double), Projection (64, 128 if double), and PackedArray/Array/Dictionary (platform-dependent)."*
>
> 也就是说：小的类型直接内联在联合体里，大类型（AABB / Transform / Projection）与容器（Array / Dictionary / Packed*Array）则改为**堆上分配 + 联合体里存指针**。

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
var g: Transform3D = Transform3D()   # 4.x 没有 Matrix4 类型
var h: Basis = Basis()                # 3.x 的 Matrix3 在 4.x 里对应 Basis

# 引擎类型
var i: Node = Node.new()
var j: Texture2D = load("res://texture.png")
var k: Array = [1, 2, 3]
var l: Dictionary = {"key": "value"}
```

> ⚠️ **4.x 没有 `Matrix4` / `Matrix3` 这两个类型**（4.7.2 实测仍无）。写 `var g: Matrix4 = Transform3D()` 会直接报 `Could not find type "Matrix4"`——4.7.2 的 `Variant::Type` 枚举里只有 `BASIS` 和 `TRANSFORM3D`，没有 `MATRIX3` / `MATRIX4`。3.x → 4.x 的对应关系是：
>
> | 3.x | 4.x |
> |-----|-----|
> | `Matrix3` | `Basis` |
> | `Matrix4` | `Transform3D` |
> | `Quat` | `Quaternion` |
> | `PoolVector3` 等 | `PackedVector3Array` 等 |

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

**源码位置**: `core/object/object.h`

```cpp
// Godot 源码 - core/object/object.h（Godot 4.3）
struct PropertyInfo {
	Variant::Type type = Variant::NIL;
	String name;
	StringName class_name;      // For classes
	PropertyHint hint = PROPERTY_HINT_NONE;
	String hint_string;
	uint32_t usage = PROPERTY_USAGE_DEFAULT;

	// If you are thinking about adding another member to this class, ask the maintainer (Juan) first.

	_FORCE_INLINE_ PropertyInfo added_usage(uint32_t p_fl) const {
		PropertyInfo pi = *this;
		pi.usage |= p_fl;
		return pi;
	}

	operator Dictionary() const;
	static PropertyInfo from_dict(const Dictionary &p_dict);

	PropertyInfo() {}

	PropertyInfo(const Variant::Type p_type, const String &p_name,
			const PropertyHint p_hint = PROPERTY_HINT_NONE,
			const String &p_hint_string = "",
			const uint32_t p_usage = PROPERTY_USAGE_DEFAULT,
			const StringName &p_class_name = StringName()) :
			type(p_type),
			name(p_name),
			hint(p_hint),
			hint_string(p_hint_string),
			usage(p_usage) {
		if (hint == PROPERTY_HINT_RESOURCE_TYPE) {
			class_name = hint_string;
		} else {
			class_name = p_class_name;
		}
	}
	// ...
};
```

> ⚠️ 4.x 里**没有 `core/object/property_info.h` 这个文件**——`PropertyInfo` 就定义在 `core/object/object.h` 里，而且它**没有** `serialize()` / `deserialize()` 方法（序列化由 `ResourceFormatSaver` / `ResourceFormatLoader` 那一层负责）。成员也和对的版本不同：`name` 是 `String` 而不是 `StringName`，`usage` 是 `uint32_t` 位标志而不是 `PropertyUsageFlags` 枚举，另外还有 `class_name` 与 `hint` 两个成员。

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
[gd_scene load_steps=5 format=3 uid="uid://abc123"]

[ext_resource type="Script" path="res://player.gd" id="1_script"]
[ext_resource type="Texture2D" path="res://player.png" id="2_tex"]

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_body"]
albedo_texture = ExtResource("2_tex")

[sub_resource type="SphereMesh" id="SphereMesh_body"]
material = SubResource("StandardMaterial3D_body")

[sub_resource type="SphereShape3D" id="SphereShape3D_body"]
radius = 0.5

[node name="Player" type="CharacterBody3D"]
script = ExtResource("1_script")
position = Vector3(0, 1, 0)

[node name="Mesh" type="MeshInstance3D" parent="."]
mesh = SubResource("SphereMesh_body")

[node name="HitBox" type="Area3D" parent="."]

[node name="Collision" type="CollisionShape3D" parent="HitBox"]
shape = SubResource("SphereShape3D_body")

[connection signal="body_entered" from="HitBox" to="." method="_on_body_entered"]
```

> ⚠️ 这个示例里有三处很容易写错的地方：
>
> 1. **`SubResource()` 引用必须先有定义**。`mesh = SubResource("SphereMesh")` 只有在文件里存在 `[sub_resource type="SphereMesh" id="SphereMesh"]` 块时才有效，否则加载会直接失败。
> 2. **`material/0` 是"属性路径"写法，表示数组的第 0 个元素**，它的类型由属性本身决定——`MeshInstance3D.material` 是 `Material` 数组，**不能**塞进一个 `Texture2D`。把纹理挂到网格上，正确路径是"先建一个 `StandardMaterial3D` 子资源，用它的 `albedo_texture` 引用纹理，再让 `SphereMesh.material` 指向这个材质子资源"。
> 3. **`load_steps` 是给加载器看的资源计数提示**。4.3 的 `ResourceFormatSaverTextInstance::save()` 里写得很直白：`int load_steps = saved_resources.size() + external_resources.size();`——即**子资源数 + 外部资源数**，并且只有 `load_steps > 1` 时才会写进文件头。上面这个示例是 2 个外部资源 + 3 个子资源 = 5。

### 4.2 .tres 格式（资源）

```ini
[gd_resource type="ItemData" script_class="ItemData" load_steps=3 format=3]

[ext_resource type="Script" path="res://items/item_data.gd" id="1_item"]

[sub_resource type="Resource" id="Item_001"]
resource_name = "铁剑"
value = 120

[sub_resource type="Resource" id="Item_002"]
resource_name = "火把"
value = 30

[resource]
script = ExtResource("1_item")
resource_name = "Hero"
health = 100
mana = 50
level = 1
inventory = [SubResource("Item_001"), SubResource("Item_002")]
```

> ⚠️ **资源没有 `name` 属性**。4.x 的 `Resource` 只暴露三个内置属性：`resource_name`（`set_name()` / `get_name()`）、`resource_path`、`resource_scene_unique_id`；`resource_local_to_scene` 另有其物。写 `name = "Hero"` 会报 `Invalid assignment of property or key 'name' with value of type 'String'`——正确的写法是 `resource_name = "Hero"`。

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
class_name VersionedSaveData
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
const MAX_INVENTORY_SIZE := 50   # 上限必须先定义，否则运行时报 "Identifier not found"

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

## 🔗 延伸阅读

- **官方文档**: [保存与加载资源](https://docs.godotengine.org/en/stable/tutorials/io/saving_and_loading_resources.html)、[自定义资源格式](https://docs.godotengine.org/en/stable/tutorials/io/custom_resource_formats.html)
- **类参考**: [ResourceSaver](https://docs.godotengine.org/en/stable/classes/class_resourcesaver.html)、[ResourceLoader](https://docs.godotengine.org/en/stable/classes/class_resourceloader.html)、[ResourceFormatLoader](https://docs.godotengine.org/en/stable/classes/class_resourceformatloader.html)
- **源码位置**: `core/io/resource_saver.cpp`、`core/io/resource_loader.cpp`

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 8 篇：Godot 文件系统与跨平台架构](/articles/08-filesystem-platform.md)
**下一篇**: [第 10 篇：Godot 跨平台架构详解](/articles/10-cross-platform-architecture.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
