# 第 3 篇：Godot 场景树架构深度解析

> **本章导读**：场景树是 Godot 一切行为的落点——节点生命周期、信号传播、场景切换都发生在其中。
> 本章从源码层面解析三个核心类：`Node`（生命周期与父子关系）、`SceneTree`（场景管理与切换）、`PackedScene`（序列化与实例化），并给出与 Unity Transform 层级在结构、性能、体验上的对照，最后收在七条实战最佳实践与常见陷阱上。
> **前置知识**：第 2 篇《Godot vs Unity：架构设计深度对比》
> **难度**：进阶。

> **摘要**：场景树是 Godot 引擎的核心架构，所有游戏对象都组织在场景树中。本文将从源码层面深度解析 Node、SceneTree、PackedScene 三个核心类，揭示场景树的运作原理，并与 Unity Transform 层级进行对比。

---

## 一、场景树概述

### 1.1 什么是场景树

**场景树（Scene Tree）** 是 Godot 引擎的核心数据结构，它是一个**树形结构**，由节点（Node）组成。

**基本结构**：

```
SceneTree (根)
└── Main (Node)
    ├── World (Node3D)
    │   ├── Player (CharacterBody3D)
    │   ├── Enemy1 (CharacterBody3D)
    │   └── Enemy2 (CharacterBody3D)
    ├── UI (CanvasLayer)
    │   ├── Score (Label)
    │   └── HealthBar (ProgressBar)
    └── Audio (Node)
        └── BGM (AudioStreamPlayer)
```

**场景树的特点**：

1. **树形结构**：每个节点有一个父节点，零个或多个子节点
2. **根节点唯一**：场景树只有一个根节点
3. **父子关系**：子节点的位置、旋转、缩放相对于父节点
4. **自动传播**：变换、信号、通知会自动在树中传播

### 1.2 场景树的作用

**1. 组织游戏对象**

场景树提供了一种直观的方式组织游戏中的所有对象：
- 玩家、敌人、道具 → World 节点下
- UI 界面 → CanvasLayer 节点下
- 音频 → Audio 节点下

**2. 管理生命周期**

场景树自动管理节点的生命周期：
- 父节点释放时，子节点自动释放
- 节点进入/离开场景树时，自动调用生命周期方法

**3. 传递变换**

父节点的变换会自动传递给子节点：

```
父节点移动 → 子节点跟随移动
父节点旋转 → 子节点跟随旋转
父节点缩放 → 子节点跟随缩放
```

**4. 传递信号**

信号可以在场景树中传播：
- 子节点可以监听父节点的信号
- 父节点可以监听子节点的信号
- 信号可以跨层级传播

### 1.3 场景树的优势

| 优势 | 说明 |
|------|------|
| **直观** | 树形结构符合人类思维 |
| **灵活** | 可以动态添加/删除节点 |
| **可复用** | 场景可以嵌套和复用 |
| **自动管理** | 内存自动释放，无需手动管理 |
| **高效** | 树形遍历高效，查找快速 |

---

## 二、Node 类深度解析

### 2.1 Node 类结构

**Node** 是场景树中所有节点的基类。

**源码位置**: `scene/main/node.h`

**继承关系**：

```
Object (核心对象基类)
  ↓
Node (节点基类)
  ↓
Node2D (2D 节点基类)
  ↓
Sprite2D, TileMap, Camera2D, ...

Node (节点基类)
  ↓
Node3D (3D 节点基类)
  ↓
MeshInstance3D, CharacterBody3D, Camera3D, ...
```

**Node 类核心成员变量**（简化版）：

```cpp
// Godot 源码 - scene/main/node.h（Godot 4.7.2，节选）
class Node : public Object {
    // 节点树相关
    Node *parent = nullptr;                     // 父节点
    HashMap<StringName, Node *> children;       // 子节点：按节点名索引（O(1) 查找）
    mutable LocalVector<Node *> children_cache;  // 子节点：保序缓存（惰性重建）
    StringName name;                            // 节点名称

    // 场景树相关
    SceneTree *tree = nullptr;                  // 所属场景树
    bool inside_tree = false;                   // 是否在场景树中

    // 生命周期相关
    bool ready_notified = false;                // 是否已通知 _ready()
    ProcessMode process_mode : 3;               // 处理模式（见下文五态）

    // 组相关
    HashMap<StringName, GroupData> grouped;     // 所属组（GroupData 指向 SceneTree::Group）

    // 其他
    mutable NodePath *path_cache = nullptr;     // 缓存的是"本节点的路径"，不是查找结果
    // ... 更多成员
};
```

> ⚠️ 3.x 的 `Vector<Node *> children` 在 4.x 已换成 `HashMap<StringName, Node *> children` + `children_cache`：哈希表负责按名字 O(1) 查找，`children_cache` 负责保序遍历（`get_children()` / `get_child(i)` 用它）。`children_cache` 由 `children_cache_dirty` 标记失效后惰性重建。

**Node 类核心方法**：

```cpp
class Node : public Object {
    // 节点操作
    void add_child(Node *p_child, bool p_force_readable_name = false, InternalMode p_internal = INTERNAL_MODE_DISABLED);
    void remove_child(Node *p_child);
    Node *get_parent() const;
    TypedArray<Node> get_children(bool p_include_internal = true) const;
    Node *get_node(const NodePath &p_path) const;
    Node *get_node_or_null(const NodePath &p_path) const;

    // 生命周期：4.x 用 GDVIRTUAL 宏声明，没有 C++ 虚函数体
    GDVIRTUAL0(_enter_tree);
    GDVIRTUAL0(_ready);
    GDVIRTUAL0(_exit_tree);
    GDVIRTUAL1(_process, double);
    GDVIRTUAL1(_physics_process, double);

    // 组操作
    void add_to_group(const StringName &p_group, bool p_persistent = false);
    void remove_from_group(const StringName &p_group);
    bool is_in_group(const StringName &p_group) const;

    // 其他
    void queue_free();  // 标记释放（由 SceneTree 的删除队列在帧末 memdelete）
};
```

### 2.2 节点的生命周期

Godot 节点有完整的生命周期，每个阶段都有对应的方法。

**生命周期流程**：

```
节点创建
  ↓
_enter_tree()      // 节点进入场景树
  ↓
_ready()           // 节点准备好（只调用一次）
  ↓
_process()         // 每帧调用（逻辑更新）
_physics_process() // 每帧调用（物理更新）
  ↓
_exit_tree()       // 节点离开场景树
  ↓
节点销毁
```

**源码分析**: 生命周期调用时机

```cpp
// Godot 源码 - scene/main/node.cpp（Godot 4.7.2，节选）
// 注意：4.x 里**没有** Node::_enter_tree() / Node::_ready() / Node::_exit_tree() 这些 C++ 虚函数。
// 脚本回调由 GDVIRTUAL 宏注册，引擎侧通过 _propagate_* 系列函数转发。

// 1. 进入场景树：_propagate_enter_tree()
void Node::_propagate_enter_tree() {
    if (data.parent) {
        data.tree = data.parent->data.tree;
        data.depth = data.parent->data.depth + 1;
    } else {
        data.depth = 1;
    }
    data.viewport = Object::cast_to<Viewport>(this);
    data.inside_tree = true;

    // 加入场景树里的各个组
    for (KeyValue<StringName, GroupData> &E : data.grouped) {
        E.value.group = data.tree->add_to_group(E.key, this);
    }

    notification(NOTIFICATION_ENTER_TREE);
    GDVIRTUAL_CALL(_enter_tree);              // ← 脚本的 _enter_tree() 在这里被调用
    emit_signal(SceneStringName(tree_entered));
    data.tree->node_added(this);

    data.blocked++;
    for (KeyValue<StringName, Node *> &K : data.children) {
        if (!K.value->is_inside_tree()) {
            K.value->_propagate_enter_tree();  // 先递归子节点
        }
    }
    data.blocked--;
}

// 2. 节点准备好：_propagate_ready()
void Node::_propagate_ready() {
    data.ready_notified = true;
    data.blocked++;
    for (KeyValue<StringName, Node *> &K : data.children) {
        K.value->_propagate_ready();           // 子节点先 ready
    }
    data.blocked--;

    notification(NOTIFICATION_POST_ENTER_TREE);
    if (data.ready_first) {
        data.ready_first = false;
        notification(NOTIFICATION_READY);
        emit_signal(SceneStringName(ready));
    }
}

// 3. 每帧更新：在 Node::_notification() 里转发
void Node::_notification(int p_notification) {
    switch (p_notification) {
        case NOTIFICATION_PROCESS: {
            GDVIRTUAL_CALL(_process, get_process_delta_time());
        } break;
        case NOTIFICATION_PHYSICS_PROCESS: {
            GDVIRTUAL_CALL(_physics_process, get_physics_process_delta_time());
        } break;
        // ...
    }
}

// 4. 离开场景树：_propagate_exit_tree()
void Node::_propagate_exit_tree() {
    data.blocked++;
    for (HashMap<StringName, Node *>::Iterator I = data.children.last(); I; --I) {
        I->value->_propagate_exit_tree();       // 先递归子节点
    }
    data.blocked--;

    GDVIRTUAL_CALL(_exit_tree);                 // ← 脚本的 _exit_tree() 在这里被调用
    emit_signal(SceneStringName(tree_exiting));
    notification(NOTIFICATION_EXIT_TREE, true);
    if (data.tree) {
        data.tree->node_removed(this);
    }

    for (KeyValue<StringName, GroupData> &E : data.grouped) {
        data.tree->remove_from_group(E.key, this);
        E.value.group = nullptr;
    }

    data.inside_tree = false;
    data.ready_notified = false;
    data.tree = nullptr;
}
```

**这张表要记住的三件事**：

1. **顺序是"父先子后"**——父节点先进树，子节点再进树；`_ready()` 也是子节点先于父节点；
2. **脚本回调与 C++ 通知是两条通道**——`GDVIRTUAL_CALL(_enter_tree)` 调脚本，`notification(NOTIFICATION_ENTER_TREE)` 调 C++ 侧的 `NOTIFICATION_ENTER_TREE` 处理器，二者互不替代；
3. **`_process()` / `_physics_process()` 不是"每帧遍历整棵树"**——引擎把节点登记进 `SceneTree` 的 ProcessGroup，每帧只遍历"需要处理"的那一批。

**GDScript 使用示例**：

```gdscript
extends Node3D

# 1. 节点进入场景树时调用
func _enter_tree():
    print("[", name, "] 进入场景树")
    # 适合：初始化信号连接、设置初始状态

# 2. 节点准备好后调用（只调用一次）
func _ready():
    print("[", name, "] 准备好")
    # 适合：获取节点引用、初始化数据

# 3. 每帧调用（用于逻辑更新）
func _process(delta: float):
    # 适合：输入处理、逻辑更新、动画
    pass

# 4. 每帧调用（用于物理更新，固定时间步长）
func _physics_process(delta: float):
    # 适合：物理运动、碰撞检测
    pass

# 5. 节点离开场景树时调用
func _exit_tree():
    print("[", name, "] 离开场景树")
    # 适合：清理资源、断开信号
```

**生命周期的调用顺序**：

```
父节点._enter_tree()
  └→ 子节点._enter_tree()
      └→ 孙节点._enter_tree()

父节点._ready()
  └→ 子节点._ready()
      └→ 孙节点._ready()

每帧：
父节点._process()
  └→ 子节点._process()
      └→ 孙节点._process()

父节点._physics_process()
  └→ 子节点._physics_process()
      └→ 孙节点._physics_process()

父节点._exit_tree()
  └→ 子节点._exit_tree()
      └→ 孙节点._exit_tree()
```

### 2.3 节点的父子关系

**添加子节点**：

```cpp
// Godot 源码 - scene/main/node.cpp（Godot 4.7.2，节选）
void Node::add_child(Node *p_child, bool p_force_readable_name, InternalMode p_internal) {
    ERR_FAIL_NULL(p_child);
    ERR_FAIL_COND_MSG(p_child == this, "Can't add child to itself.");
    ERR_FAIL_COND_MSG(p_child->data.parent, "Can't add child, it already has a parent.");
    ERR_FAIL_COND_MSG(data.blocked > 0, "Parent node is busy setting up children, use add_child.call_deferred(child).");

    _validate_child_name(p_child, p_force_readable_name);
    _add_child_nocheck(p_child, p_child->data.name, p_internal);
}
```

其中 `_add_child_nocheck()` 负责真正落位：写入 `data.children` 哈希表、设置 `p_child->data.parent = this`、置脏 `children_cache_dirty`，并在父节点已在树中时调用 `p_child->_set_tree(data.tree)`——由 `_set_tree()` 触发 `_propagate_enter_tree()` / `_propagate_ready()`。

**移除子节点**：

```cpp
void Node::remove_child(Node *p_child) {
    ERR_FAIL_NULL(p_child);
    ERR_FAIL_COND(p_child->data.parent != this);

    data.blocked++;
    p_child->_set_tree(nullptr);            // 离开场景树（触发 _propagate_exit_tree）
    remove_child_notify(p_child);
    p_child->notification(NOTIFICATION_UNPARENTED);
    data.blocked--;

    data.children_cache_dirty = true;
    bool success = data.children.erase(p_child->data.name);
    ERR_FAIL_COND_MSG(!success, "Children name does not match parent name in hashtable, this is a bug.");
    p_child->data.parent = nullptr;
    p_child->data.index = -1;

    notification(NOTIFICATION_CHILD_ORDER_CHANGED);
    emit_signal(SNAME("child_order_changed"));
}
```

> ⚠️ 4.x 的子节点存储是**按名字索引的哈希表**（`data.children`），所以"按名字添加"和"按名字删除"是一对；同名子节点在 `add_child()` 时会被自动改名（`@2`、`@3` …）而不是被拒绝。

**GDScript 使用示例**：

```gdscript
# 创建节点
var enemy = Enemy.new()

# 添加到父节点
add_child(enemy)

# 从父节点移除
remove_child(enemy)

# 获取父节点
var parent = get_parent()

# 获取所有子节点
var children = get_children()

# 获取子节点数量
var count = get_child_count()

# 获取指定索引的子节点
var child = get_child(0)
```

### 2.4 节点的路径系统

**NodePath** 是 Godot 中用于定位节点的类。

**路径语法**：

```gdscript
# 绝对路径（从根节点开始）
$"/Main/World/Player"

# 相对路径（从当前节点开始）
$"../Enemy"      # 父节点的同级节点
$"../../World"   # 祖父节点的子节点
$"Child"         # 直接子节点
$"Child/GrandChild"  # 孙子节点

# $ 语法糖（等价于 get_node()）
$Player          # 等价于 get_node("Player")
$Player/Sprite   # 等价于 get_node("Player/Sprite")
```

**源码分析**: `get_node()` 实现

```cpp
// Godot 源码 - scene/main/node.cpp（Godot 4.7.2，节选）
Node *Node::get_node(const NodePath &p_path) const {
    Node *node = get_node_or_null(p_path);
    if (unlikely(!node)) {
        // 找不到：区分绝对路径 / 相对路径给出不同错误信息
        ERR_FAIL_V_MSG(nullptr, vformat(R"(Node not found: "%s" ...)", p_path));
    }
    return node;
}

Node *Node::get_node_or_null(const NodePath &p_path) const {
    if (p_path.is_empty()) {
        return nullptr;
    }
    ERR_FAIL_COND_V_MSG(!data.inside_tree && p_path.is_absolute(), nullptr,
            "Can't use get_node() with absolute paths from outside the active scene tree.");

    Node *current = nullptr;
    Node *root = nullptr;
    if (!p_path.is_absolute()) {
        current = const_cast<Node *>(this);        // 相对路径：从自己出发
    } else {
        root = const_cast<Node *>(this);
        while (root->data.parent) {
            root = root->data.parent;             // 绝对路径：从根节点出发
        }
    }

    for (int i = 0; i < p_path.get_name_count(); i++) {
        StringName name = p_path.get_name(i);
        Node *next = nullptr;

        if (name == SNAME(".")) {
            next = current;
        } else if (name == SNAME("..")) {
            if (current == nullptr || !current->data.parent) {
                return nullptr;
            }
            next = current->data.parent;
        } else if (current == nullptr) {
            if (name == root->get_name()) {
                next = root;
            }
        } else if (name.is_node_unique_name()) {
            // %UniqueName 语法：先查自己，再查 owner
            Node **unique = current->data.owned_unique_nodes.getptr(name);
            if (!unique && current->data.owner) {
                unique = current->data.owner->data.owned_unique_nodes.getptr(name);
            }
            if (!unique) {
                return nullptr;
            }
            next = *unique;
        } else {
            // 普通名字：哈希表查找，O(1)
            const Node *const *node = current->data.children.getptr(name);
            if (node) {
                next = const_cast<Node *>(*node);
            } else {
                return nullptr;
            }
        }
        current = next;
    }
    return current;
}
```

**关于"路径缓存"**：

4.x 的 `Node` 里确实有一个 `mutable NodePath *path_cache = nullptr;`，但它缓存的是**本节点自身的路径**（`get_path()` 的结果，惰性分配、节点改名时失效），**不是 `get_node()` 的查找结果**。`get_node()` 每次都会真正走一遍路径解析——正因为逐段查找是 O(1) 哈希表命中，整体开销很小，但**每帧反复 `get_node()` 仍不划算**，因为每段路径都要做一次字符串比较与哈希。

所以正确的优化姿势是**把节点引用缓存下来**，而不是指望引擎帮你缓存查找：

```gdscript
extends Node

# ✅ 第一次查找后把引用存下来，后续直接用
# 不写死成 Node：update() 是 Player 自己的方法，写成 Node 的话静态检查直接报错。
var player = get_node("World/Player")

func _ready() -> void:
    player = get_node("World/Player")

func _process(_delta: float) -> void:
    player.update()          # 直接用缓存的引用，不再走路径解析

# ❌ 每帧重新走一遍路径解析
func _process_bad(_delta: float) -> void:
    get_node("World/Player").update()
```

> 节点被释放后，缓存的引用会变成"已失效对象"，访问它会报 `Attempt to call function 'update' in base 'previously freed'`，必要时用 `is_instance_valid(player)` 判断。

---

## 三、SceneTree 类深度解析

### 3.1 SceneTree 类结构

**SceneTree** 是场景树的管理类，继承自 `MainLoop`。

**源码位置**: `scene/main/scene_tree.h`

**继承关系**：

```
MainLoop (主循环基类)
  ↓
SceneTree (场景树)
```

**SceneTree 核心成员**：

```cpp
// Godot 源码 - scene/main/scene_tree.h（Godot 4.7.2，节选）
class SceneTree : public MainLoop {
    // 场景树根节点（4.x 根节点是 Window）
    Window *root = nullptr;

    // 当前场景：注意是**节点实例**，不是 PackedScene 资源
    Node *current_scene = nullptr;
    ObjectID pending_new_scene_id;      // 4.7.2 起是 ObjectID，不再是裸指针   // 等待挂载的新场景
    ObjectID prev_scene_id;             // 4.7.2 起是 ObjectID，不再是裸指针          // 等待释放的旧场景

    // 场景组
    struct Group {
        Vector<Node *> nodes;
        bool changed = false;
    };
    HashMap<StringName, Group> group_map;

    // 其他
    bool paused = false;                  // 是否暂停
    int64_t current_frame = 0;            // 物理帧计数
    List<ObjectID> delete_queue;          // queue_free() 的删除队列
    // ... 更多成员
};
```

> ⚠️ 3.x 的 `PackedScene *current_scene` 与 `HashMap<StringName, GroupData> group_map` 在 4.x 都变了：
> - `current_scene` 是 `Node *`（已挂载的实例），要拿资源得自己另外保存 `PackedScene`；
> - 组的类型名是 `Group`（结构体里带 `changed` 标记），**不是** `GroupData`；`GroupData` 是 `Node` 内部用来反向索引组的结构。

### 3.2 场景树的管理

**根节点**：

```cpp
// 获取根节点
_FORCE_INLINE_ Window *SceneTree::get_root() const { return root; }

// 根节点是所有场景节点的祖先
// 结构：
// root (Window)
//  └── Main (当前场景)
//      ├── World
//      ├── UI
//      └── Audio
```

**当前场景**：

```cpp
// 设置当前场景（注意是节点实例，不是 PackedScene）
void SceneTree::set_current_scene(Node *p_scene) {
    ERR_FAIL_COND_MSG(!Thread::is_main_thread(), "Changing scene can only be done from the main thread.");
    ERR_FAIL_COND(p_scene && p_scene->get_parent() != root);
    current_scene = p_scene;
}

// 获取当前场景
Node *SceneTree::get_current_scene() const {
    return current_scene;
}
```

**场景组**：

```cpp
// 添加节点到组（由 Node::add_to_group() 内部调用）
SceneTree::Group *SceneTree::add_to_group(const StringName &p_group, Node *p_node) {
    HashMap<StringName, Group>::Iterator E = group_map.find(p_group);
    if (!E) {
        E = group_map.insert(p_group, Group());
    }
    ERR_FAIL_COND_V_MSG(E->value.nodes.has(p_node), &E->value, "Already in group: " + p_group + ".");
    E->value.nodes.push_back(p_node);
    E->value.changed = true;      // 标记需要重新排序
    return &E->value;
}

// 脚本侧：获取组中所有节点（返回 TypedArray<Node>）
TypedArray<Node> SceneTree::_get_nodes_in_group(const StringName &p_group) {
    TypedArray<Node> ret;
    HashMap<StringName, Group>::Iterator E = group_map.find(p_group);
    if (!E) {
        return ret;
    }
    _update_group_order(E->value);
    int nc = E->value.nodes.size();
    ret.resize(nc);
    Node **ptr = E->value.nodes.ptrw();
    for (int i = 0; i < nc; i++) {
        ret[i] = ptr[i];
    }
    return ret;
}
```

> ⚠️ 3.x 里叫 `add_node_to_group()` 的函数在 4.x 叫 `add_to_group()`，且是**私有**的（`friend class Node;`）——脚本侧不要直接调它，用 `Node.add_to_group()` / `Node.remove_from_group()`。

### 3.3 场景切换

**切换场景的方法**：

```gdscript
# Godot 4.x - 场景切换

# 方式 1：通过文件路径
get_tree().change_scene_to_file("res://levels/level_2.tscn")

# 方式 2：通过资源
var level_2: PackedScene = load("res://levels/level_2.tscn")
get_tree().change_scene_to_packed(level_2)

# 方式 3：重新加载当前场景
get_tree().reload_current_scene()

# 方式 4：退出游戏
get_tree().quit()
```

**源码分析**: 场景切换流程

```cpp
// Godot 源码 - scene/main/scene_tree.cpp（Godot 4.7.2）
Error SceneTree::change_scene_to_packed(const Ref<PackedScene> &p_scene) {
    ERR_FAIL_COND_V_MSG(p_scene.is_null(), ERR_INVALID_PARAMETER,
            "Can't change to a null scene. Use unload_current_scene() if you wish to unload it.");

    Node *new_scene = p_scene->instantiate();
    ERR_FAIL_NULL_V(new_scene, ERR_CANT_CREATE);

    // 如果已经有一次切换待完成，把上一次挂起的场景删掉
    if (pending_new_scene) {
        queue_delete(pending_new_scene);
        pending_new_scene = nullptr;
    }

    prev_scene = current_scene;

    if (current_scene) {
        // 让尽可能多的副作用先发生或排队，以便在场景真正被删除前执行
        root->remove_child(current_scene);
    }
    DEV_ASSERT(!current_scene);

    pending_new_scene = new_scene;   // ← 注意：这里只是"挂起"，还没挂到树上
    return OK;
}

// 帧末才真正挂载新场景
void SceneTree::_flush_scene_change() {
    if (prev_scene) {
        memdelete(prev_scene);       // 释放旧场景
        prev_scene = nullptr;
    }
    current_scene = pending_new_scene;
    root->add_child(pending_new_scene);   // ← 新场景此刻才进入场景树
    pending_new_scene = nullptr;
    root->update_mouse_cursor_state();
}
```

**场景切换是延迟的**——这是最容易踩的坑：

`change_scene_to_file()` / `change_scene_to_packed()` 只做两件事：把**旧场景从根节点摘下**，把**新场景实例放进 `pending_new_scene`**。真正把新场景挂到树上，要等到本帧的 `SceneTree::process()` 末尾调用 `_flush_scene_change()` 才发生。

也就是说，**在调用切换的那一帧内**：

```gdscript
get_tree().change_scene_to_file("res://levels/level_2.tscn")

# ⚠️ 此刻 current_scene 仍然是旧场景（已被置空），新场景还没进树
print(get_tree().current_scene)          # 不是 level_2
print(get_tree().root.get_child_count())  # 新场景不在里面
```

由此产生的三条实践规则：

1. **不要在切换后立刻查询 `current_scene` 或 `root` 的子节点**——要等下一帧，或者 `await get_tree().process_frame`；
2. **旧场景的 `_exit_tree()` 早于新场景的 `_enter_tree()`**，但旧场景的**真正销毁**（`memdelete`）发生在帧末 `_flush_scene_change()` 里；`queue_free()` 排队的节点则由 `SceneTree::_flush_delete_queue()` 统一在帧末 `memdelete`；
3. **连续调用两次切换是安全的**：第二次调用会把第一次挂起的 `pending_new_scene` 通过 `queue_delete()` 排队删除，只保留最后一次的结果。

**场景切换流程**：

```
1. 加载新场景资源（`change_scene_to_file()` 内部走 `ResourceLoader::load()`）
   ↓
2. 实例化新场景（调用 `PackedScene::instantiate()`）
   ↓
3. 旧场景从根节点移除（`root->remove_child(current_scene)`，触发 `_exit_tree()`）
   ↓
4. 新场景放进 `pending_new_scene`（**尚未**进入场景树）
   ↓
5. ——本帧结束——
   ↓
6. 帧末 `_flush_scene_change()`：释放旧场景 → `root->add_child(new_scene)` → 触发 `_enter_tree()` → `_ready()`
```

### 3.4 场景树信号

**SceneTree 提供的信号**（4.7.2 `SceneTree::_bind_methods()` 的全集）：

```gdscript
# 节点添加到场景树
scene_tree.node_added.connect(_on_node_added)

# 节点从场景树移除
scene_tree.node_removed.connect(_on_node_removed)

# 节点被重命名
scene_tree.node_renamed.connect(_on_node_renamed)

# 场景树结构改变
scene_tree.tree_changed.connect(_on_tree_changed)

# 树的处理模式改变（编辑器内使用）
scene_tree.tree_process_mode_changed.connect(_on_tree_process_mode_changed)

# 配置警告变化
scene_tree.node_configuration_warning_changed.connect(_on_warning_changed)

# 当前场景切换完成
scene_tree.scene_changed.connect(_on_scene_changed)

# 每帧 / 每个物理帧
scene_tree.process_frame.connect(_on_process_frame)
scene_tree.physics_frame.connect(_on_physics_frame)
```

> ⚠️ **没有 `scene_paused` 这个信号**。4.7.2 的 `SceneTree` 信号只有上面这 9 个（4.3 时只有 8 个，4.7 新增了 `scene_changed`），暂停状态是一个**属性**（`paused`），不是信号。

**暂停状态：用属性轮询，而不是信号**

```gdscript
extends Node

var _was_paused := false

func _process(_delta: float) -> void:
    var now_paused := get_tree().paused
    if now_paused != _was_paused:
        _was_paused = now_paused
        if now_paused:
            _on_paused()
        else:
            _on_resumed()

func _on_paused() -> void:
    print("游戏已暂停")

func _on_resumed() -> void:
    print("游戏已恢复")
```

> ⚠️ 轮询的前提是**你自己的节点仍在处理**。默认的 `process_mode` 是 `PROCESS_MODE_PAUSABLE`——暂停时它自己也会停摆，轮询自然也就停了。如果暂停菜单要继续响应输入，得把自己的 `process_mode` 改成 `PROCESS_MODE_WHEN_PAUSED`（或 `PROCESS_MODE_ALWAYS`）。

**`Node.process_mode` 的五种状态**（4.x，`scene/main/node.h`）：

| 取值 | 含义 |
|------|------|
| `PROCESS_MODE_INHERIT` | 继承父节点的处理模式（默认） |
| `PROCESS_MODE_PAUSABLE` | 仅在**未暂停**时处理（根节点的默认模式） |
| `PROCESS_MODE_WHEN_PAUSED` | **仅在暂停时**处理（暂停菜单常用） |
| `PROCESS_MODE_ALWAYS` | 始终处理，忽略 `paused` |
| `PROCESS_MODE_DISABLED` | 完全不处理，忽略 `paused` |

```gdscript
# 暂停菜单：只在暂停时处理
pause_menu.process_mode = Node.PROCESS_MODE_WHEN_PAUSED

# HUD：暂停时也要继续刷新
hud.process_mode = Node.PROCESS_MODE_ALWAYS
```

**使用示例**：

```gdscript
extends Node

func _ready():
    # 监听节点添加
    get_tree().node_added.connect(_on_node_added)
    
    # 监听节点移除
    get_tree().node_removed.connect(_on_node_removed)

func _on_node_added(node: Node):
    print("节点添加：", node.name)

func _on_node_removed(node: Node):
    print("节点移除：", node.name)
```

---

## 四、PackedScene 类深度解析

### 4.1 PackedScene 是什么

**PackedScene** 是 Godot 中场景的资源表示形式。

**源码位置**: `scene/resources/packed_scene.h`

**本质**：
- PackedScene 是一个资源（Resource）
- 它保存了场景树的序列化数据
- 可以实例化为实际的节点树

**文件扩展名**：`.tscn`（文本格式）、`.scn`（二进制格式）

### 4.2 场景序列化

**.tscn 文件格式示例**：

```ini
[gd_scene load_steps=3 format=3 uid="uid://xxx"]

[ext_resource type="Script" path="res://player.gd" id="1"]

[node name="Player" type="CharacterBody3D"]
script = ExtResource("1")

[node name="Mesh" type="MeshInstance3D" parent="."]
mesh = SubResource("MeshResource")

[node name="Camera" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0)
```

**序列化内容**：

1. **节点信息**：名称、类型、父节点
2. **属性值**：位置、旋转、缩放、材质等
3. **资源引用**：脚本、纹理、模型等
4. **连接关系**：信号连接

### 4.3 场景实例化

**实例化方法**：

```gdscript
# 加载场景资源
var scene = load("res://enemy.tscn")

# 实例化场景
var enemy = scene.instantiate()

# 添加到场景树
add_child(enemy)
```

**源码分析**: 实例化流程

```cpp
// Godot 源码 - scene/resources/packed_scene.cpp（Godot 4.7.2）
Node *PackedScene::instantiate(GenEditState p_edit_state) const {
    // 真正的实例化工作交给 SceneState（它持有了打包好的节点数据）
    Node *s = state->instantiate((SceneState::GenEditState)p_edit_state);
    if (!s) {
        return nullptr;
    }

    if (p_edit_state != GEN_EDIT_STATE_DISABLED) {
        s->set_scene_instance_state(state);
    }

    if (!is_built_in()) {
        s->set_scene_file_path(get_path());
    }

    s->notification(Node::NOTIFICATION_SCENE_INSTANTIATED);

    return s;
}
```

> 4.x 把"创建节点 / 恢复属性 / 恢复信号连接"这些细节都收进了 `SceneState::instantiate()`（`scene/resources/packed_scene.cpp`），`PackedScene` 自己只负责持有 `SceneState` 并派发通知。想知道属性和连接具体怎么恢复，去看 `SceneState`。

**实例化流程**：

```
1. 创建根节点
   ↓
2. 递归创建所有子节点
   ↓
3. 设置节点属性
   ↓
4. 恢复信号连接
   ↓
5. 返回实例化的节点树
```

---

## 五、场景树的高级特性

### 5.1 场景嵌套

**场景嵌套**是 Godot 的强大特性，允许在一个场景中嵌入另一个场景。

**示例**：

```
Main.tscn (主场景)
├── World (Node3D)
│   └── Terrain (TerrainScene 实例)  # 嵌套场景
├── Player (PlayerScene 实例)         # 嵌套场景
└── Enemies (Node3D)
    ├── Enemy1 (EnemyScene 实例)      # 嵌套场景
    └── Enemy2 (EnemyScene 实例)      # 嵌套场景
```

**使用示例**：

```gdscript
# 在编辑器中右键场景文件 → "实例化子场景"
# 或者代码方式：

# 加载子场景
var enemy_scene = load("res://enemy.tscn")

# 实例化并添加
var enemy1 = enemy_scene.instantiate()
var enemy2 = enemy_scene.instantiate()

$Enemies.add_child(enemy1)
$Enemies.add_child(enemy2)
```

**场景嵌套的优势**：

1. **模块化**：每个场景独立开发
2. **可复用**：同一场景可以多次使用
3. **易维护**：修改子场景，所有实例自动更新
4. **协作友好**：不同开发者可以并行工作

### 5.2 场景组（Groups）

**组（Group）** 是节点的逻辑分组，可以跨场景组织节点。

**使用示例**：

```gdscript
# 添加节点到组
func _ready():
    add_to_group("enemies")
    add_to_group("hostile")

# 从组移除
remove_from_group("enemies")

# 检查是否在组中
if is_in_group("enemies"):
    print("我是敌人")

# 获取组中所有节点
var enemies = get_tree().get_nodes_in_group("enemies")

# 调用组中所有节点的方法
get_tree().call_group("enemies", "take_damage", 10)
```

**组的典型用途**：

1. **敌人管理**：`"enemies"` 组
2. **可交互对象**：`"interactables"` 组
3. **UI 元素**：`"ui"` 组
4. **音频源**：`"audio"` 组

### 5.3 场景树迭代

**遍历场景树**：

```gdscript
# 方式 1：递归遍历
func traverse_tree(node: Node):
    print("节点：", node.name)

    for child in node.get_children():
        traverse_tree(child)  # 递归

# 方式 2：自己写递归调用（4.x 没有 call_recursive）
func call_recursive(node: Node, method: StringName, args: Array = []) -> void:
    if node.has_method(method):
        node.callv(method, args)
    for child in node.get_children():
        call_recursive(child, method, args)

# 方式 3：使用组
var all_enemies = get_tree().get_nodes_in_group("enemies")
```

> ⚠️ **`call_recursive()` 是 Godot 3 的 API，4.x 已移除**。4.x 保留的动态调用只有：
>
> | 方法 | 说明 |
> |------|------|
> | `Object.call(method, ...)` | 变长参数调用 |
> | `Object.callv(method, arg_array)` | 用数组传参 |
> | `Object.callp(method, arg_array)` | C++ 侧指针版，脚本不可见 |
> | `Object.call_deferred(method, ...)` | 延迟到空闲时执行 |
>
> 4.3 的 `Node.xml` 里 `call_recursive` 出现 **0 次**。需要"对子树调用同一个方法"时，要么像上面那样自己递归，要么用组（`call_group()`）一次性覆盖。

**性能考虑**：

- 深度优先遍历适合大多数场景
- 避免在遍历中修改树结构
- 使用组代替遍历（更快）

### 5.4 场景树性能优化

**优化技巧**：

1. **避免过深的层级**
   ```
   # ❌ 不好：层级过深
   Root → World → Level1 → Area1 → Enemy1 → Mesh
   
   # ✅ 好：扁平结构
   Root → Enemies → Enemy1 → Mesh
   ```

2. **缓存节点引用（而不是路径）**
   ```gdscript
   # ❌ 不好：每帧查找
   func _process(delta):
       $Player.update()  # 每次都重新解析路径
   
   # ✅ 好：缓存引用
   var player = $Player   # 不要标注成 Node：update() 是 Player 自己的方法
   func _ready():
       player = $Player
   
   func _process(delta):
       player.update()  # 直接使用缓存
   ```
   > 4.x 的 `get_node()` **不缓存查找结果**（`path_cache` 缓存的是节点自身路径），所以"引擎帮你缓存了"这个假设不成立——省下来的开销要靠自己缓存引用。

3. **延迟加载大型场景**
   ```gdscript
   # 使用 ResourceLoader.load_threaded_request()
   # 后台线程加载 + 分帧轮询进度，避免卡顿
   ```

---

## 六、场景树 vs Unity Transform 层级

### 6.1 结构对比

| 维度 | Godot 场景树 | Unity Transform |
|------|-------------|-----------------|
| **基本单元** | Node | Transform |
| **组织方式** | 树形 | 树形 |
| **路径访问** | `get_node()` | `Transform.Find()` |
| **场景嵌套** | 原生支持（PackedScene） | Prefab 嵌套（2018.3+，含 Prefab Variant） |
| **内存管理** | 节点：随父节点释放（`queue_free()`）<br/>资源：引用计数 | 垃圾回收 |
| **生命周期** | `_enter_tree` → `_ready` | `Awake` → `Start` |

### 6.2 性能对比

**遍历性能**：

| 操作 | Godot | Unity |
|------|-------|-------| 
| 获取子节点 | O(1)（`children` 哈希表 / `children_cache` 数组） | O(1)（Transform 子节点数组） |
| 路径查找 | O(路径段数)，每段一次哈希查找 | O(路径段数)，逐段线性查找 |
| 递归遍历 | O(n) | O(n) |
| 组查找 | O(1)（哈希表 → 成员数组） | O(n)（无组机制，只能自行维护） |

**内存占用**：

| 指标 | Godot | Unity |
|------|-------|-------|
| 空节点 | ⚠️ 示意数据：~100 bytes | ⚠️ 示意数据：~200 bytes |
| 3D 节点 | ⚠️ 示意数据：~300 bytes | ⚠️ 示意数据：~500 bytes |
| 场景树 overhead | 较低 | 较高 |

> ⚠️ **本表整体为示意数据（未附测试环境）**：未标注引擎版本、构建配置（debug/release）、节点实际携带的组件数量与测量工具。Godot 侧的实际占用随 `children` 哈希表、`children_cache`、`owned` 列表等成员数变化很大，Unity 侧还会随 `GameObject` + `Transform` + `MonoBehaviour` 的组合而变。**请以自有项目的 `ObjectDB` 快照或内存分析器结果为准**，不要把这张表当作选型依据。

### 6.3 使用体验对比

**编辑体验**：

| 维度 | Godot | Unity |
|------|-------|-------|
| 场景编辑 | 直观（场景树视图） | 直观（Hierarchy 视图） |
| 场景嵌套 | 自然（拖拽即可） | 较复杂（Prefab 系统） |
| 多场景编辑 | 支持（标签页） | 支持（Additive 加载） |

**代码访问**：

```gdscript
# Godot
var player = $World/Player  # 简洁
var enemy = get_node("Enemies/Enemy1")
```

```csharp
// Unity
Transform player = transform.Find("World/Player");  // 较繁琐
GameObject enemy = GameObject.Find("Enemies/Enemy1");
```

---

## 七、实战：场景树最佳实践

### 7.1 场景组织建议

**合理的节点层级**：

```
Main (Node)
├── World (Node3D)
│   ├── Terrain (Node3D)
│   ├── Props (Node3D)
│   └── Enemies (Node3D)
├── Player (CharacterBody3D)
├── UI (CanvasLayer)
│   ├── HUD (Control)
│   └── PauseMenu (Control)
└── Audio (Node)
    ├── BGM (AudioStreamPlayer)
    └── SFX (AudioStreamPlayer)
```

**命名规范**：

- 使用有意义的名称：`Player` 而不是 `Node1`
- 使用类型后缀：`Player/CharacterBody3D`
- 使用组来组织：`Enemies/Enemy1`、`Enemies/Enemy2`

**场景拆分**：

- 主场景：`Main.tscn`
- 玩家场景：`Player.tscn`
- 敌人场景：`Enemy.tscn`
- UI 场景：`HUD.tscn`、`PauseMenu.tscn`

### 7.2 性能优化技巧

**1. 避免过深的层级**

> 层级过深的例子与扁平化建议见 [5.4 场景树性能优化](#54-场景树性能优化)，此处不重复。

**2. 使用组代替遍历**

```gdscript
# ❌ 不好：遍历查找
func find_enemies():
    var enemies = []
    for child in get_tree().root.get_children():
        if child.is_in_group("enemies"):
            enemies.append(child)
    return enemies

# ✅ 好：直接使用组
func get_enemies():
    return get_tree().get_nodes_in_group("enemies")
```

**3. 延迟加载大型场景**

```gdscript
# 使用 ResourceLoader 后台线程加载（4.x 取代 3.x 的 load_interactive）
func load_level_async(path: String) -> void:
    ResourceLoader.load_threaded_request(path)
    var progress: Array = []
    while true:
        var status := ResourceLoader.load_threaded_get_status(path, progress)
        match status:
            ResourceLoader.THREAD_LOAD_IN_PROGRESS:
                await get_tree().process_frame
            ResourceLoader.THREAD_LOAD_LOADED:
                var level: PackedScene = ResourceLoader.load_threaded_get(path)
                add_child(level.instantiate())
                return
            _:
                push_error("场景加载失败：%s" % path)
                return
```

### 7.3 常见陷阱

**1. 循环引用**

```gdscript
# ❌ 不好：循环引用
class A:
    var b: B

class B:
    var a: A

# ✅ 好：使用弱引用
class A:
    var b: WeakRef

class B:
    var a: A
```

**2. 内存泄漏**

```gdscript
# ❌ 不好：忘记断开信号
func _ready():
    some_node.signal_name.connect(_on_signal)

# ✅ 好：在 _exit_tree 断开
func _exit_tree():
    some_node.signal_name.disconnect(_on_signal)
```

**3. 路径错误**

```gdscript
# ❌ 不好：硬编码路径
var player = get_node("/root/Main/World/Player")

# ✅ 好：使用相对路径或组
var player = get_node("../../World/Player")
var player = get_tree().get_nodes_in_group("player")[0]
```

---

## 八、总结

### 核心概念回顾

1. **场景树**：Godot 的核心架构，树形结构组织所有节点
2. **Node**：场景树的基本单元，有完整的生命周期
3. **SceneTree**：场景树的管理类，提供场景切换、组管理等功能
4. **PackedScene**：场景的资源表示，可以实例化为节点树

### Node、SceneTree、PackedScene 的关系

```
PackedScene (资源)
    ↓ instantiate()
Node 树 (实例)
    ↓ 添加到
SceneTree (管理)
```

### 场景树的优势

- ✅ 直观易理解
- ✅ 灵活的组合
- ✅ 自动内存管理
- ✅ 高效的查找和遍历
- ✅ 强大的场景嵌套

### 下一篇文章

下一篇文章，我们将深入分析 **Godot 内存管理机制**，从源码层面解析引用计数、对象树自动释放、循环引用处理等核心主题。

敬请期待！

---

## 🔗 延伸阅读

- **官方文档**: [场景树](https://docs.godotengine.org/en/stable/tutorials/scripting/scene_tree.html)、[节点](https://docs.godotengine.org/en/stable/tutorials/scripting/scene_tree.html)
- **类参考**: [Node](https://docs.godotengine.org/en/stable/classes/class_node.html)、[SceneTree](https://docs.godotengine.org/en/stable/classes/class_scenetree.html)、[PackedScene](https://docs.godotengine.org/en/stable/classes/class_packedscene.html)
- **源码位置**: `scene/main/scene_tree.cpp`、`scene/main/node.cpp`

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 2 篇：Godot vs Unity：架构设计深度对比](/articles/02-godot-vs-unity-architecture.md)
**下一篇**: [第 4 篇：Godot 内存管理机制深度解析](/articles/04-memory-management.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
