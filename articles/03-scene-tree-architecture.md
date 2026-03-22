# 深入理解 Godot 引擎 #03 | Godot 场景树架构深度解析

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
// Godot 源码 - scene/main/node.h
class Node : public Object {
    // 节点树相关
    Node *parent = nullptr;                    // 父节点
    Vector<Node *> children;                   // 子节点列表
    StringName name;                           // 节点名称
    
    // 场景树相关
    SceneTree *scene_tree = nullptr;           // 场景树引用
    bool inside_tree = false;                  // 是否在场景树中
    
    // 生命周期相关
    bool ready_notified = false;               // 是否已通知_ready()
    bool process_enabled = true;               // 是否启用_process()
    
    // 组相关
    Vector<StringName> groups;                 // 所属组列表
    
    // 其他
    NodePath path_cache;                       // 路径缓存
    // ... 更多成员
};
```

**Node 类核心方法**：

```cpp
class Node : public Object {
    // 节点操作
    void add_child(Node *p_child, bool p_force_readable_name = false);
    void remove_child(Node *p_child);
    Node *get_parent() const;
    const Vector<Node *> &get_children() const;
    Node *get_node(const NodePath &p_path) const;
    
    // 生命周期
    virtual void _enter_tree();
    virtual void _ready();
    virtual void _process(double p_delta);
    virtual void _physics_process(double p_delta);
    virtual void _exit_tree();
    
    // 组操作
    void add_to_group(const StringName &p_group, bool p_persistent = false);
    void remove_from_group(const StringName &p_group);
    bool is_in_group(const StringName &p_group) const;
    
    // 其他
    void queue_free();  // 标记释放
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
// Godot 源码 - scene/main/node.cpp

// 1. 节点进入场景树
void Node::_enter_tree() {
    // 设置场景树引用
    scene_tree = get_tree();
    inside_tree = true;
    
    // 递归调用子节点
    for (Node *child : children) {
        child->_enter_tree();
    }
    
    // 发送通知
    notify_post_enter_tree();
}

// 2. 节点准备好（只调用一次）
void Node::_ready() {
    if (ready_notified) {
        return;  // 已经调用过，不再调用
    }
    
    ready_notified = true;
    
    // 递归调用子节点
    for (Node *child : children) {
        child->_ready();
    }
}

// 3. 每帧更新（逻辑）
void Node::_process(double p_delta) {
    // 默认空实现，子类重写
}

// 4. 每帧更新（物理，固定时间步长）
void Node::_physics_process(double p_delta) {
    // 默认空实现，子类重写
}

// 5. 节点离开场景树
void Node::_exit_tree() {
    // 递归调用子节点
    for (Node *child : children) {
        child->_exit_tree();
    }
    
    inside_tree = false;
    scene_tree = nullptr;
}
```

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
// Godot 源码 - scene/main/node.cpp
void Node::add_child(Node *p_child, bool p_force_readable_name) {
    ERR_FAIL_COND(!p_child);
    ERR_FAIL_COND(p_child == this);
    ERR_FAIL_COND(p_child->parent != nullptr);
    
    // 添加到子节点列表
    children.push_back(p_child);
    p_child->parent = this;
    
    // 如果父节点在场景树中，子节点也进入场景树
    if (inside_tree) {
        p_child->_set_tree(get_tree());
    }
    
    // 发送信号
    emit_signal(SNAME("child_entered_tree"), p_child);
}
```

**移除子节点**：

```cpp
void Node::remove_child(Node *p_child) {
    ERR_FAIL_COND(!p_child);
    
    // 从子节点列表中移除
    int index = children.find(p_child);
    ERR_FAIL_COND(index == -1);
    
    children.remove_at(index);
    p_child->parent = nullptr;
    
    // 如果父节点在场景树中，子节点也离开场景树
    if (inside_tree) {
        p_child->_set_tree(nullptr);
    }
}
```

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
// Godot 源码 - scene/main/node.cpp
Node *Node::get_node(const NodePath &p_path) const {
    // 1. 检查路径缓存
    if (path_cache == p_path && path_cache_valid) {
        return path_cache_result;
    }
    
    // 2. 解析路径
    Node *current = const_cast<Node *>(this);
    
    for (int i = 0; i < p_path.get_name_count(); i++) {
        StringName name = p_path.get_name(i);
        
        // 处理 ".." （父节点）
        if (name == "..") {
            current = current->get_parent();
        } else {
            // 查找子节点
            current = current->_get_child_by_name(name);
        }
        
        if (current == nullptr) {
            ERR_FAIL_V_MSG(nullptr, "Node not found: " + p_path);
        }
    }
    
    // 3. 缓存结果
    path_cache = p_path;
    path_cache_result = current;
    path_cache_valid = true;
    
    return current;
}
```

**路径缓存优化**：

Godot 会缓存 `get_node()` 的结果，避免每次都重新查找：

```gdscript
# 第一次调用：查找并缓存
var player = get_node("World/Player")

# 后续调用：直接使用缓存（更快）
var player2 = get_node("World/Player")  # 使用缓存

# 如果节点结构改变，缓存会失效
# Godot 会自动重新查找
```

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
// Godot 源码 - scene/main/scene_tree.h
class SceneTree : public MainLoop {
    // 场景树根节点
    Node *root = nullptr;
    
    // 当前场景
    PackedScene *current_scene = nullptr;
    
    // 场景组
    HashMap<StringName, GroupData> group_map;
    
    // 信号
    SignalTreeChanged *tree_changed_signal = nullptr;
    
    // 其他
    bool paused = false;                    // 是否暂停
    int physics_frame_count = 0;           // 物理帧计数
    // ... 更多成员
};
```

### 3.2 场景树的管理

**根节点**：

```cpp
// 获取根节点
Node *SceneTree::get_root() const {
    return root;
}

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
// 设置当前场景
void SceneTree::set_current_scene(PackedScene *p_scene) {
    current_scene = p_scene;
}

// 获取当前场景
PackedScene *SceneTree::get_current_scene() const {
    return current_scene;
}
```

**场景组**：

```cpp
// 添加节点到组
void SceneTree::add_node_to_group(const StringName &p_group, Node *p_node) {
    GroupData &group = group_map[p_group];
    group.nodes.push_back(p_node);
}

// 获取组中所有节点
Vector<Node *> SceneTree::get_nodes_in_group(const StringName &p_group) const {
    if (!group_map.has(p_group)) {
        return Vector<Node *>();
    }
    return group_map[p_group].nodes;
}
```

### 3.3 场景切换

**切换场景的方法**：

```gdscript
# Godot 4.x - 场景切换

# 方式 1：通过文件路径
get_tree().change_scene_to_file("res://levels/level_2.tscn")

# 方式 2：通过资源
var level_2 = load("res://levels/level_2.tscn")
get_tree().change_scene_to_packed(level_2)

# 方式 3：重新加载当前场景
get_tree().reload_current_scene()

# 方式 4：退出游戏
get_tree().quit()
```

**源码分析**: 场景切换流程

```cpp
// Godot 源码 - scene/main/scene_tree.cpp
Error SceneTree::change_scene_to_packed(PackedScene *p_scene) {
    ERR_FAIL_COND_V(!p_scene, ERR_INVALID_PARAMETER);
    
    // 1. 实例化新场景
    Node *new_scene = p_scene->instantiate();
    ERR_FAIL_COND_V(!new_scene, ERR_CANT_CREATE);
    
    // 2. 获取当前场景
    Node *current = current_scene ? current_scene->instantiate() : nullptr;
    
    // 3. 替换场景
    if (current) {
        root->remove_child(current);
        memdelete(current);  // 释放旧场景
    }
    
    root->add_child(new_scene);
    current_scene = p_scene;
    
    // 4. 设置新的当前场景
    set_current_scene(new_scene);
    
    return OK;
}
```

**场景切换流程**：

```
1. 加载新场景资源
   ↓
2. 实例化新场景（调用 PackedScene.instantiate()）
   ↓
3. 从根节点移除旧场景
   ↓
4. 释放旧场景（触发 _exit_tree()）
   ↓
5. 添加新场景到根节点
   ↓
6. 新场景进入场景树（触发 _enter_tree() → _ready()）
```

### 3.4 场景树信号

**SceneTree 提供的信号**：

```gdscript
# 节点添加到场景树
scene_tree.node_added.connect(_on_node_added)

# 节点从场景树移除
scene_tree.node_removed.connect(_on_node_removed)

# 场景树改变
scene_tree.tree_changed.connect(_on_tree_changed)

# 场景暂停
scene_tree.scene_paused.connect(_on_scene_paused)
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
// Godot 源码 - scene/resources/packed_scene.cpp
Node *PackedScene::instantiate() {
    // 1. 创建根节点
    Node *root = _create_node(root_data);
    
    // 2. 递归创建子节点
    for (NodeData &child_data : nodes) {
        Node *parent = _find_node_by_path(root, child_data.parent);
        Node *child = _create_node(child_data);
        parent->add_child(child);
    }
    
    // 3. 恢复属性
    for (NodeData &node_data : nodes) {
        Node *node = _find_node_by_path(root, node_data.path);
        _set_properties(node, node_data.properties);
    }
    
    // 4. 恢复信号连接
    for (Connection &conn : connections) {
        Node *source = _find_node_by_path(root, conn.source);
        Node *target = _find_node_by_path(root, conn.target);
        source->connect(conn.signal, target, conn.method);
    }
    
    return root;
}
```

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

# 方式 2：使用 call_recursive
node.call_recursive("method_name", args)

# 方式 3：使用组
var all_enemies = get_tree().get_nodes_in_group("enemies")
```

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

2. **使用路径缓存**
   ```gdscript
   # ❌ 不好：每帧查找
   func _process(delta):
       $Player.update()  # 每次都查找
   
   # ✅ 好：缓存引用
   var player: Node
   func _ready():
       player = $Player
   
   func _process(delta):
       player.update()  # 直接使用缓存
   ```

3. **延迟加载大型场景**
   ```gdscript
   # 使用 ResourceLoader.load_interactive()
   # 分帧加载，避免卡顿
   ```

---

## 六、场景树 vs Unity Transform 层级

### 6.1 结构对比

| 维度 | Godot 场景树 | Unity Transform |
|------|-------------|-----------------|
| **基本单元** | Node | Transform |
| **组织方式** | 树形 | 树形 |
| **路径访问** | `get_node()` | `Transform.Find()` |
| **场景嵌套** | 原生支持（PackedScene） | Prefab 嵌套（2019+） |
| **内存管理** | 引用计数 | 垃圾回收 |
| **生命周期** | `_enter_tree` → `_ready` | `Awake` → `Start` |

### 6.2 性能对比

**遍历性能**：

| 操作 | Godot | Unity |
|------|-------|-------|
| 获取子节点 | O(1) | O(1) |
| 路径查找 | O(n) + 缓存 | O(n) |
| 递归遍历 | O(n) | O(n) |
| 组查找 | O(1) | O(n) |

**内存占用**：

| 指标 | Godot | Unity |
|------|-------|-------|
| 空节点 | ~100 bytes | ~200 bytes |
| 3D 节点 | ~300 bytes | ~500 bytes |
| 场景树 overhead | 较低 | 较高 |

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
- 使用组组织：`Enemies/Enemy1`、`Enemies/Enemy2`

**场景拆分**：

- 主场景：`Main.tscn`
- 玩家场景：`Player.tscn`
- 敌人场景：`Enemy.tscn`
- UI 场景：`HUD.tscn`、`PauseMenu.tscn`

### 7.2 性能优化技巧

**1. 避免过深的层级**

```gdscript
# ❌ 不好：5 层嵌套
Root → World → Level1 → Area1 → Enemy1 → Mesh

# ✅ 好：3 层
Root → Enemies → Enemy1 → Mesh
```

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
# 使用 ResourceLoader 分帧加载
func load_level_async(path: String):
    var loader = ResourceLoader.load_interactive(path)
    
    func _process(delta):
        var err = loader.poll()
        if err == ERR_FILE_EOF:
            var level = loader.get_resource()
            add_child(level)
            set_process(false)
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
    some_node.connect("signal", self, "_on_signal")

# ✅ 好：在 _exit_tree 断开
func _exit_tree():
    some_node.disconnect("signal", self, "_on_signal")
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

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #02 | Godot vs Unity：架构对比](#)  
**下一篇**: [深入理解 Godot 引擎 #04 | Godot 内存管理机制深度解析](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
