# 第 4 篇：Godot 内存管理机制深度解析

> **摘要**：Godot 有两套内存管理模型：节点（Node）随父节点一起释放，资源（Resource）使用引用计数（Reference Counting），与 Unity 的垃圾回收（GC）机制形成鲜明对比。本文将深入分析 Godot 的引用计数原理、节点树自动释放机制、资源系统内存管理，并与 Unity GC 进行全方位对比。

---

## 一、内存管理概述

### 1.1 内存管理的两种主流方案

在编程语言和游戏引擎中，内存管理主要有两种方案：

**1. 引用计数（Reference Counting）**
- 代表：Godot、Python、PHP、Swift
- 原理：每个对象维护一个计数器，记录有多少地方引用它
- 释放时机：引用计数为 0 时立即释放

**2. 垃圾回收（Garbage Collection）**
- 代表：Unity（C#）、Java、Go
- 原理：定期扫描内存，找出不再使用的对象并释放
- 释放时机：GC 运行时（非确定性）

### 1.2 为什么 Godot 选择引用计数

Godot 选择引用计数而非垃圾回收，主要基于以下考虑：

**1. 确定性**
- 引用计数：释放时机确定（计数为 0 时立即释放）
- 垃圾回收：释放时机不确定（取决于 GC 何时运行）

**2. 性能稳定性**
- 引用计数：无 GC 峰值，帧率稳定
- 垃圾回收：GC 运行时可能导致卡顿

**3. 实时性要求**
- 游戏对实时性要求高，不能容忍 GC 峰值
- 引用计数避免突发性能问题

**4. C++ 传统**
- Godot 使用 C++ 开发，引用计数更符合 C++ 习惯
- 与智能指针（`std::shared_ptr`）理念一致

### 1.3 Godot 内存模型概览

```
Godot 内存模型
├── 节点树自动释放（Node）
│   ├── 父子关系管理
│   └── queue_free()
├── 引用计数（RefCounted）
│   ├── 资源（Resource）
│   ├── 数组（Array）
│   └── 字典（Dictionary）
└── 手动管理（Object）
    ├── 独立对象
    └── 需要手动 free()
```

---

## 二、引用计数原理

### 2.1 RefCounted 类结构

**RefCounted** 是 Godot 中所有引用计数对象的基类。

**源码位置**: `core/object/ref_counted.h`

```cpp
// Godot 源码 - core/object/ref_counted.h（Godot 4.3）
class RefCounted : public Object {
	GDCLASS(RefCounted, Object);
	SafeRefCount refcount;
	SafeRefCount refcount_init;

protected:
	static void _bind_methods();

public:
	_FORCE_INLINE_ bool is_referenced() const { return refcount_init.get() != 1; }
	bool init_ref();
	bool reference();   // 返回 false 表示计数已为 0，无法再增加
	bool unreference();
	int get_reference_count() const;

	RefCounted();
	~RefCounted() {}
};
```

> ⚠️ 3.x 的 `ref()` / `unref()` / `get_refcount()` 在 4.x 里**已经不存在**，取而代之的是 `init_ref()` / `reference()` / `unreference()` / `get_reference_count()`。脚本侧对应的方法名是 `init_ref()`、`reference()`、`unreference()`、`get_reference_count()`。

**核心机制**：

1. **创建时**：`init_ref()` 把引用计数置为 1
2. **被引用时**：`reference()` 让计数 +1
3. **引用释放时**：`unreference()` 让计数 -1，返回 `true` 表示计数归零
4. **计数为 0 时**：由 `Ref<T>` 智能指针的 `unref()` 执行 `memdelete(reference)` 真正释放对象

> ⚠️ **析构通知不是 `unreference()` 发的**。`unreference()` 只负责维护计数并返回"是否该销毁了"；真正的 `NOTIFICATION_PREDELETE` 通知由 `Object::predelete_handler()` → `Object::_predelete()` 发出：
>
> ```cpp
> // core/object/object.cpp（Godot 4.3）
> bool predelete_handler(Object *p_object) {
>     return p_object->_predelete();
> }
>
> bool Object::_predelete() {
>     _predelete_ok = 1;
>     notification(NOTIFICATION_PREDELETE, true);
>     if (_predelete_ok) {
>         _class_name_ptr = nullptr;
>         notification(NOTIFICATION_PREDELETE_CLEANUP, true);
>     }
>     return _predelete_ok;
> }
> ```

### 2.2 引用计数增减时机

**GDScript 中的引用计数**：

```gdscript
# 1. 创建对象（引用计数 = 1）
var texture = load("res://player.png")

# 2. 赋值给另一个变量（引用计数 +1 = 2）
var texture2 = texture

# 3. 添加到节点（引用计数 +1 = 3）
$Sprite.texture = texture

# 4. 变量超出作用域（引用计数 -1 = 2）
func some_function():
    var temp = texture  # 引用计数 +1
    # ... 使用 temp
# temp 超出作用域，引用计数 -1

# 5. 手动设置为 null（引用计数 -1）
texture2 = null

# 6. 最后引用释放（引用计数 = 0，对象释放）
texture = null
$Sprite.texture = null
```

**引用计数变化过程**：

```
创建 texture         → refcount = 1
赋值给 texture2      → refcount = 2
添加到 Sprite        → refcount = 3
temp 超出作用域      → refcount = 2
texture2 = null     → refcount = 1
$Sprite.texture = null → refcount = 0 → 释放！
```

### 2.3 循环引用问题

**循环引用**是引用计数的致命弱点。

**问题示例**：

```gdscript
# ❌ 循环引用示例
class A:
    var b: B  # A 引用 B

class B:
    var a: A  # B 引用 A

func create_cycle():
    var a = A.new()  # a refcount = 1
    var b = B.new()  # b refcount = 1
    
    a.b = b  # b refcount = 2
    b.a = a  # a refcount = 2
    
    # 现在 a 和 b 互相引用
    # 即使外部不再引用，refcount 也不会为 0
    # 导致内存泄漏！
```

**解决方案**：

**方案 1：使用 WeakRef**

```gdscript
# ✅ 使用 WeakRef 打破循环
class A:
    var b: B

class B:
    var a: WeakRef  # 弱引用，不增加引用计数

func create_safe():
    var a = A.new()
    var b = B.new()
    
    a.b = b
    b.a = weakref(a)  # 弱引用
    
    # 当 a 的外部引用释放时，a 会被正确释放
```

**方案 2：手动断开引用**

```gdscript
# ✅ 手动断开循环
func cleanup():
    a.b = null
    b.a = null
    # 现在引用计数会正确归零
```

**方案 3：让弱引用一方不持有强引用（推荐）**

```gdscript
# ✅ 让 A 持有 B（强引用），B 持有 A（弱引用）
class A:
    extends Node
    var b: B

class B:
    extends Node
    var a: WeakRef

func create_safe():
    var a = A.new()
    var b = B.new()

    a.b = b          # 强引用：B 的计数 +1
    b.a = weakref(a) # 弱引用：不增加 A 的计数

    # 外部引用消失时，A 仍能正常释放
```

> ⚠️ 这里要分清两件事：
> - **节点树解决的是"释放时机"问题**：父节点 `queue_free()` 时，子节点随之被释放；
> - **它并不解决"引用计数"问题**：如果 A 和 B 互相持有**强引用**（都是 `RefCounted` 资源或普通对象），放进节点树也不会打破循环——节点树只管"谁负责 delete 谁"，管不了"谁还引用着谁"。
> - 因此真正能打破循环的是**让其中一方只持弱引用**（`WeakRef` / `weakref()`），节点树只负责随父节点一起释放。
>
> 另外注意 `add_child()` 的形参是 `Node *`——要挂进节点树的对象必须 `extends Node`。默认继承 `RefCounted` 的类（如 `class A:`）传进去会报 `Expected argument 1 of type 'Node' but got 'RefCounted'`。

### 2.4 源码分析：引用计数实现

```cpp
// Godot 源码 - core/object/ref_counted.cpp（Godot 4.3，节选）

// 初始化引用：计数置 1
bool RefCounted::init_ref() {
	if (reference()) {
		if (!is_referenced() && refcount_init.unref()) {
			unreference(); // first referencing is already 1, so compensate for the ref above
		}
		return true;
	} else {
		return false;
	}
}

// 增加引用
bool RefCounted::reference() {
	uint32_t rc_val = refcount.refval();
	bool success = rc_val != 0;

	if (success && rc_val <= 2 /* higher is not relevant */) {
		if (get_script_instance()) {
			get_script_instance()->refcount_incremented();
		}
		if (_get_extension() && _get_extension()->reference) {
			_get_extension()->reference(_get_extension_instance());
		}
	}
	return success;
}

// 减少引用：返回 true 表示计数归零，应当销毁
bool RefCounted::unreference() {
	uint32_t rc_val = refcount.unrefval();
	bool die = rc_val == 0;

	if (rc_val <= 1 /* higher is not relevant */) {
		if (get_script_instance()) {
			bool script_ret = get_script_instance()->refcount_decremented();
			die = die && script_ret;
		}
		if (_get_extension() && _get_extension()->unreference) {
			_get_extension()->unreference(_get_extension_instance());
		}
	}
	return die;
}

// 读取当前计数
int RefCounted::get_reference_count() const {
	return refcount.get();
}
```

**智能指针 `Ref<T>` 的关键片段**（`core/object/ref_counted.h`）：

```cpp
template <typename T>
class Ref {
	T *reference = nullptr;

	// 增加引用
	void ref(const Ref &p_from) {
		if (p_from.reference == reference) {
			return;
		}
		unref();
		reference = p_from.reference;
		if (reference) {
			reference->reference();
		}
	}

public:
	// 析构：计数归零就 memdelete
	void unref() {
		if (reference && reference->unreference()) {
			memdelete(reference);
		}
		reference = nullptr;
	}

	~Ref() {
		unref();
	}
};
```

> **要点**：`unreference()` 只管计数；真正"通知对象即将被销毁 + 释放内存"的是 `Ref::unref()` 里的 `memdelete(reference)`，而 `NOTIFICATION_PREDELETE` 通知由 `Object::predelete_handler()` 发出（见 2.1 节）。

---

## 三、节点树自动释放

### 3.1 父子关系与内存管理

Godot 的节点树具有**自动内存管理**特性：

**核心规则**：
1. 父节点释放时，所有子节点自动释放
2. 子节点从父节点移除时，如果没有其他引用，会被释放
3. 节点添加到场景树后，由场景树管理生命周期

**示例**：

```gdscript
# 创建节点树
var parent = Node.new()
var child1 = Node.new()
var child2 = Node.new()

# 建立父子关系
parent.add_child(child1)  # child1 的父节点是 parent
parent.add_child(child2)  # child2 的父节点是 parent

# 释放父节点
parent.queue_free()

# 结果：child1 和 child2 也会自动释放
# 无需手动管理子节点！
```

### 3.2 queue_free() 原理

**queue_free()** 是 Godot 中释放节点的标准方法。

**源码位置**: `scene/main/node.cpp`

```cpp
// Godot 源码 - scene/main/node.cpp（Godot 4.3）
void Node::queue_free() {
	// 优先用节点自己所属的 SceneTree（有些项目会创建多个场景树）
	if (is_inside_tree()) {
		get_tree()->queue_delete(this);
	} else {
		SceneTree *tree = SceneTree::get_singleton();
		ERR_FAIL_NULL_MSG(tree, "Can't queue free a node when no SceneTree is available.");
		tree->queue_delete(this);
	}
}

// Godot 源码 - scene/main/scene_tree.cpp（Godot 4.3）
void SceneTree::queue_delete(Object *p_object) {
	_THREAD_SAFE_METHOD_
	ERR_FAIL_NULL(p_object);
	p_object->_is_queued_for_deletion = true;
	delete_queue.push_back(p_object->get_instance_id());   // 只记 ObjectID
}

void SceneTree::_flush_delete_queue() {
	_THREAD_SAFE_METHOD_
	while (delete_queue.size()) {
		Object *obj = ObjectDB::get_instance(delete_queue.front()->get());
		if (obj) {
			memdelete(obj);        // 真正释放
		}
		delete_queue.pop_front();
	}
}
```

**释放时机**：`SceneTree::process()`（以及 `physics_process()`）在每帧末尾调用 `_flush_delete_queue()`，把队列里的对象逐个 `memdelete`。所以 `queue_free()` 的准确说法是：**由 SceneTree 的删除队列在帧末统一 `memdelete`**，而不是"发一条消息到帧末执行 free"。队列里存的是 `ObjectID` 而不是裸指针，因此即使对象在排队期间已经失效，flush 时也能安全地跳过。

**queue_free() vs free()**：

| 方法 | 释放时机 | 安全性 | 使用场景 |
|------|---------|--------|---------|
| `queue_free()` | 帧末由 SceneTree 删除队列统一 `memdelete` | 安全 | 推荐，大多数场景 |
| `free()` | 立即 | 危险 | 仅用于独立对象 |

**为什么使用 queue_free()**：

```gdscript
# ❌ 危险：立即释放可能导致问题
func _process(delta):
    if should_die:
        free()  # 立即释放
        # 但 _process() 还在继续执行！崩溃！

# ✅ 安全：延迟释放
func _process(delta):
    if should_die:
        queue_free()  # 标记释放
        # 当前帧继续执行，帧结束时真正释放
```

### 3.3 节点释放流程

**节点释放的完整流程**：

```
调用 queue_free()
    ↓
加入 SceneTree 的 delete_queue（只记 ObjectID）
    ↓
——本帧结束——
    ↓
SceneTree::_flush_delete_queue() → memdelete(node)
    ↓
Object::predelete_handler() → NOTIFICATION_PREDELETE
    ↓
Node 的 PREDELETE 处理：从父节点移除（触发 _exit_tree()）→ 递归 memdelete 子节点
    ↓
Object 析构：断开全部信号连接、ObjectDB 注销
    ↓
内存释放
```

**源码分析**（Godot 4.3，`scene/main/node.cpp`）：

```cpp
case NOTIFICATION_PREDELETE: {
    // 在场景树中的节点不允许从其他线程释放
    if (data.inside_tree && !Thread::is_main_thread()) {
        cancel_free();
        ERR_PRINT("Attempted to free a node that is currently added to the SceneTree from a thread. "
                  "This is not permitted, use queue_free() instead. Node has not been freed.");
        return;
    }

    if (data.owner) {
        _clean_up_owner();
    }

    while (!data.owned.is_empty()) {
        Node *n = data.owned.back()->get();
        n->_clean_up_owner();   // 这里会修改 data.owned，不能按常规方式遍历
    }

    if (data.parent) {
        data.parent->remove_child(this);   // 触发 _exit_tree()
    }

    // 尽可能干净地释放子节点
    while (data.children.size()) {
        Node *child = data.children.last()->value;  // 从尾部开始，更快也更符合创建顺序
        memdelete(child);
    }
} break;
```

> ⚠️ 3.x 时代的伪代码（`data.children[0]` + `set_parent(nullptr)` + `_disconnect_all_signals()`）在 4.x 里**站不住脚**：
> - `data.children` 是 `HashMap<StringName, Node *>`，**不能**用下标 `[]` 取元素，也没有 `size()` 语义上的"第一个"——只能 `last()->value` / `getptr(name)`；
> - `Node` **没有** `set_parent()` 这个方法，解除父子关系只能通过 `parent->remove_child(this)`；
> - 信号连接的清理发生在 `Object` 的析构流程里，不在 `Node` 的 PREDELETE 分支中。

### 3.4 节点释放示例

```gdscript
# 完整的节点生命周期示例
extends Node

func _ready():
    # 创建子节点
    var child = Node.new()
    add_child(child)  # 添加到父节点
    
    # 子节点会自动管理，无需手动释放
    print("子节点已添加：", child.name)

func _on_button_pressed():
    # 释放子节点
    var child = get_node("Child")
    child.queue_free()  # 子节点会在帧结束时释放
    
    # 安全：子节点释放后不会立即访问
    # 因为 queue_free() 是延迟释放

func _exit_tree():
    # 节点离开场景树时自动调用
    # 所有子节点会自动释放
    print("节点离开场景树，子节点自动释放")
```

---

## 四、资源系统内存管理

### 4.1 Resource 类

**Resource** 是所有资源类的基类，继承自 `RefCounted`。

**源码位置**: `core/io/resource.h`

```cpp
// Godot 源码 - core/io/resource.h（Godot 4.3，节选）
class Resource : public RefCounted {
	GDCLASS(Resource, RefCounted);

private:
	String name;                 // 资源名（脚本侧属性名是 resource_name）
	String path_cache;           // 资源在缓存中的路径
	String scene_unique_id;
	bool local_to_scene = false;
	Node *local_scene = nullptr;

public:
	// 变更通知
	void emit_changed();
	void connect_changed(const Callable &p_callable, uint32_t p_flags = 0);
	void disconnect_changed(const Callable &p_callable);

	void set_name(const String &p_name);
	String get_name() const;

	virtual void set_path(const String &p_path, bool p_take_over = false);
	String get_path() const;

	virtual Ref<Resource> duplicate(bool p_subresources = false) const;
	virtual Error copy_from(const Ref<Resource> &p_resource);
	virtual void reload_from_file();
	// ...
};
```

> ⚠️ **保存 / 加载资源不在 `Resource` 上**，而是在两个独立的单例里：
>
> | 操作 | 正确写法 | 说明 |
> |------|---------|------|
> | 保存 | `ResourceSaver.save(res, "res://x.tres")` | 返回 `Error` |
> | 加载 | `ResourceLoader.load("res://x.tres")` | 返回 `Resource` |
> | 存字节 | `var_to_bytes(res)` + `FileAccess.store_buffer()` | 内存中的二进制 |
>
> `Resource` 上**没有** `save_to_file()` / `load_from_file()` 这两个方法。

**常见资源类型**：

```gdscript
# 所有这些都继承自 Resource，使用引用计数
var texture: Texture2D      # 纹理资源
var mesh: Mesh              # 网格资源
var material: Material      # 材质资源
var script: GDScript        # 脚本资源
var scene: PackedScene      # 场景资源
var audio: AudioStream      # 音频资源
```

### 4.2 资源引用计数

**资源加载和引用**：

```gdscript
# 1. 加载资源（引用计数 = 1）
var texture = load("res://player.png")

# 2. 多个地方使用同一资源（引用计数增加）
$Sprite1.texture = texture  # 引用计数 +1
$Sprite2.texture = texture  # 引用计数 +1
$Sprite3.texture = texture  # 引用计数 +1

# 3. 移除引用（引用计数减少）
$Sprite1.texture = null  # 引用计数 -1
$Sprite2.texture = null  # 引用计数 -1

# 4. 最后一个引用释放（引用计数 = 0，资源释放）
$Sprite3.texture = null  # 引用计数 -1 = 0 → 释放！
texture = null
```

**资源缓存**：

Godot 会缓存已加载的资源：

```gdscript
# 第一次加载
var texture1 = load("res://player.png")  # 从磁盘加载

# 第二次加载（使用缓存）
var texture2 = load("res://player.png")  # 从缓存获取

# texture1 和 texture2 指向同一个对象
print(texture1 == texture2)  # true
```

### 4.3 资源加载和卸载

**手动卸载资源**：

```gdscript
# Godot 4 没有 ResourceLoader.unload()，也没有 ResourceQueue
# 资源是引用计数的：最后一个引用消失即自动回收
var tex := ResourceLoader.load("res://large_texture.png")  # 默认 CACHE_MODE_REUSE
# ... 使用资源
tex = null  # 引用计数归零，资源被释放

# 若不想被全局缓存长期占用内存，显式忽略缓存
var temp := ResourceLoader.load(
    "res://large_texture.png", "", ResourceLoader.CACHE_MODE_IGNORE)
```

**资源预加载**：

```gdscript
# 用 preload() 在编译期加载，必须以常量接收
const PlayerTexture: Texture2D = preload("res://player.png")

# 优点：加载快，无运行时开销
# 缺点：增加初始加载时间
```

---

## 五、与 Unity GC 对比

### 5.1 引用计数 vs 垃圾回收

| 维度 | Godot（引用计数） | Unity（垃圾回收） |
|------|-----------------|------------------|
| **释放时机** | 资源：确定性（计数为 0 时）<br/>节点：帧末由删除队列统一释放 | 非确定性（GC 运行时） |
| **性能影响** | 稳定，无峰值 | GC 峰值被摊平（2019.3+ 默认增量 GC） |
| **内存开销** | ⚠️ 示意数据：每个对象额外 4–8 字节（`SafeRefCount` 为 4 字节，`RefCounted` 内含 `refcount` + `refcount_init` 两个计数） | GC 需要额外内存池 |
| **循环引用** | 需手动处理 | 自动处理 |
| **实时性** | 好（适合游戏） | 一般（需优化） |
| **调试难度** | 容易（立即释放） | 较难（延迟释放） |

### 5.2 性能对比

**Godot 引用计数性能**：

```
优点：
✅ 无 GC 峰值，帧率稳定
✅ 释放及时，内存占用低
✅ 适合实时性要求高的场景

缺点：
❌ 每次赋值都有引用计数操作（轻微开销）
❌ 循环引用需手动处理
```

**Unity GC 性能**：

```
优点：
✅ 自动处理循环引用
✅ 开发者心智负担小
✅ 批量释放效率高

缺点：
❌ GC 峰值可能导致卡顿（2019.3 起默认启用增量 GC，峰值被摊平）
❌ 释放时机不确定
❌ 需要手动优化（对象池等）
```

### 5.3 使用体验对比

**Godot 内存管理体验**：

```gdscript
# Godot - 简单直观
func _ready():
    var enemy = Enemy.new()
    add_child(enemy)  # 自动管理

func defeat_enemy():
    enemy.queue_free()  # 自动释放子节点
    # 无需手动管理内存！
```

**Unity 内存管理体验**：

```csharp
// Unity - 需要注意 GC
void Start() {
    GameObject enemy = new GameObject();
    // 需要手动 Destroy
}

void DefeatEnemy() {
    Destroy(enemy);  // 延迟释放
    // 注意：不要创建过多临时对象（会导致 GC）
}

void Update() {
    // ❌ 不好：每帧分配新对象
    string msg = "Health: " + health;  // GC 分配
    
    // ✅ 好：使用 StringBuilder
    sb.Clear();
    sb.Append("Health: ");
    sb.Append(health);  // 无 GC 分配
}
```

---

## 六、内存管理最佳实践

### 6.1 避免循环引用

**❌ 不好的做法**：

```gdscript
class Player:
    var inventory: Inventory

class Inventory:
    var owner: Player  # 循环引用！

func create_player():
    var player = Player.new()
    var inventory = Inventory.new()
    
    player.inventory = inventory
    inventory.owner = player  # 循环！
```

**✅ 好的做法**：

```gdscript
class Player:
    var inventory: Inventory

class Inventory:
    var owner: WeakRef  # 弱引用

func create_player():
    var player = Player.new()
    var inventory = Inventory.new()
    
    player.inventory = inventory
    inventory.owner = weakref(player)  # 弱引用，不增加计数
```

### 6.2 正确释放资源

**✅ 推荐做法**：

```gdscript
# 1. 使用节点树
var enemy = Enemy.new()
add_child(enemy)  # 自动管理

# 2. 使用 queue_free()
enemy.queue_free()  # 安全释放

# 3. 断开信号连接
func _exit_tree():
    if some_signal.is_connected(my_handler):
        some_signal.disconnect(my_handler)

# 4. 清理临时资源
func cleanup():
    temp_texture = null
    temp_data.clear()
```

### 6.3 内存泄漏排查

**常见内存泄漏场景**：

1. **循环引用**
2. **未断开的信号连接**
3. **全局变量持有引用**
4. **未释放的资源**

**排查工具**：

```gdscript
# 使用 Godot 内置的内存分析器
# 菜单：Debugger → Memory → Take Snapshot

# 查看引用计数（4.x 的方法名是 get_reference_count，不是 3.x 的 get_refcount）
print(texture.get_reference_count())

# 查看场景树节点数
print(get_tree().get_node_count())
```

---

## 七、总结

### 核心要点

1. **Godot 有两套所有权模型**：节点随父节点释放（`queue_free()`），资源用引用计数
2. **节点树自动释放**：父节点释放时，子节点自动释放
3. **RefCounted 类**是所有引用计数对象的基类，4.x 的接口是 `init_ref()` / `reference()` / `unreference()` / `get_reference_count()`
4. **循环引用**是引用计数的弱点，需使用 WeakRef 避免（节点树只解决释放时机，不解决引用计数）
5. **queue_free()** 是安全的节点释放方法：由 SceneTree 的删除队列在帧末统一 `memdelete`

### 与 Unity GC 对比

| 特性 | Godot | Unity |
|------|-------|-------|
| 机制 | 节点：父子释放<br/>资源：引用计数 | 垃圾回收 |
| 确定性 | ✅ 是（资源侧） | ❌ 否 |
| 性能稳定 | ✅ 是 | ⚠️ 有峰值（2019.3+ 默认增量 GC） |
| 循环引用 | ⚠️ 需手动 | ✅ 自动 |

### 最佳实践

- ✅ 使用节点树管理对象
- ✅ 使用 queue_free() 释放节点
- ✅ 使用 WeakRef 避免循环引用
- ✅ 及时断开信号连接
- ✅ 定期使用内存分析器检查

### 下一篇文章

下一篇文章，我们将深入分析 **Godot 对象系统**，从源码层面解析 Object 类、RTTI、反射机制等核心主题。

敬请期待！

---

## 🔗 延伸阅读

- **官方文档**: [内存使用](https://docs.godotengine.org/en/stable/tutorials/performance/using_servers.html)、[优化内存使用](https://docs.godotengine.org/en/stable/tutorials/performance/optimizing_memory_usage.html)
- **类参考**: [RefCounted](https://docs.godotengine.org/en/stable/classes/class_refcounted.html)、[WeakRef](https://docs.godotengine.org/en/stable/classes/class_weakref.html)、[Resource](https://docs.godotengine.org/en/stable/classes/class_resource.html)
- **源码位置**: `core/object/ref_counted.h`、`core/object/weak_ref.h`

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 3 篇：Godot 场景树架构深度解析](/articles/03-scene-tree-architecture.md)
**下一篇**: [第 5 篇：Godot 对象系统深度解析](/articles/05-object-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
