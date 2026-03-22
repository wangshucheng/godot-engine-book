# 深入理解 Godot 引擎 #07 | Godot 资源系统深度解析

> **摘要**：资源（Resource）是 Godot 的核心概念，一切皆资源。本文将深入分析资源系统架构、序列化机制、资源管理最佳实践。

---

## 一、资源系统概述

### 1.1 什么是资源

在 Godot 中，**一切皆资源**：
- 场景是资源（PackedScene）
- 脚本是资源（GDScript）
- 纹理是资源（Texture）
- 材质是资源（Material）
- 音频是资源（AudioStream）

### 1.2 Resource 类结构

**源码位置**: `core/resource.h`

```cpp
class Resource : public RefCounted {
    String path;          // 资源路径
    String uid;           // 唯一 ID
    String local_name;    // 本地化名称
    
    // 保存到文件
    Error save_to_file(const String &p_path);
    
    // 从文件加载
    static Ref<Resource> load_from_file(const String &p_path);
};
```

---

## 二、资源加载机制

### 2.1 加载方式

```gdscript
# 1. 使用 load()（缓存）
var texture = load("res://player.png")

# 2. 使用 preload()（编译时加载）
@preload("res://player.png")
var PlayerTexture: Texture2D

# 3. 使用 ResourceLoader
var resource = ResourceLoader.load("res://data.tres")

# 4. 异步加载
var loader = ResourceLoader.load_interactive("res://large.tres")
```

### 2.2 资源缓存

```gdscript
# 第一次加载（从磁盘）
var tex1 = load("res://player.png")

# 第二次加载（从缓存）
var tex2 = load("res://player.png")

# 指向同一个对象
print(tex1 == tex2)  # true
```

---

## 三、资源序列化

### 3.1 资源格式

**.tres 格式**（文本）：
```ini
[gd_resource type="Resource" load_steps=2 format=3]

[sub_resource type="Vector2" id="Vector2_0"]
x = 100.0
y = 200.0

[resource]
position = SubResource("Vector2_0")
name = "MyResource"
```

**.res 格式**（二进制）：
- 更小的文件大小
- 更快的加载速度
- 不可读

---

## 四、自定义资源

### 4.1 创建自定义资源

```gdscript
class_name ItemData
extends Resource

@export var item_name: String
@export var item_value: int
@export var icon: Texture2D

func get_display_name() -> String:
    return item_name.to_upper()
```

### 4.2 使用自定义资源

```gdscript
# 在编辑器中创建资源文件
# 右键 → Create New → ItemData

# 代码中加载
var item = load("res://items/sword.tres") as ItemData
print(item.get_display_name())
```

---

## 五、资源管理最佳实践

### 5.1 资源组织

```
resources/
├── textures/
├── audio/
├── scenes/
├── scripts/
└── data/
    ├── items/
    └── enemies/
```

### 5.2 内存管理

```gdscript
# 卸载未使用的资源
ResourceLoader.unload("res://unused.tres")

# 清理缓存
ResourceQueue.unload_unused_resources()
```

---

## 六、总结

资源系统核心：
- ✅ 一切皆资源
- ✅ 引用计数管理
- ✅ 支持序列化
- ✅ 可自定义

**下一篇**: Godot 文件系统
