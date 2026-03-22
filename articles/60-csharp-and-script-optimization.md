# 第 60 篇：C# 集成和脚本性能优化

> **本卷定位**: 第七卷 脚本系统（高优先级篇）  
> **前置知识**: 第 55 章 GDScript 进阶  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

C# 集成为 Godot 提供了更强的类型安全和性能优势，特别适合计算密集型任务。同时，脚本性能优化是确保游戏流畅运行的关键。本章将深入探讨 C# 集成、互操作、性能分析和优化技术。

---

## 🎯 学习目标

- 理解 C# 集成原理
- 掌握 GDScript 与 C# 互操作
- 学会脚本性能分析
- 熟悉优化技巧
- 实施最佳实践

---

## 1. C# 集成基础

### 1.1 C# vs GDScript 对比

```
C# vs GDScript 对比:
┌─────────────────────────────────────────────────────────────┐
│ 特性          │ C#              │ GDScript        │ 适用场景      │
├─────────────────────────────────────────────────────────────┤
│ 性能          │ 高（JIT 编译）   │ 中（解释执行）   │ 计算密集型    │
│ 类型安全      │ 强类型          │ 动态类型        │ 大型项目      │
│ 开发速度      │ 中              │ 快              │ 原型开发      │
│ 学习曲线      │ 陡峭            │ 平缓            │ 新手友好      │
│ 内存占用      │ 高（.NET 运行时）  │ 低              │ 移动端        │
│ 启动时间      │ 慢              │ 快              │ 快速迭代      │
└─────────────────────────────────────────────────────────────┘

推荐混合使用:
- GDScript: 游戏逻辑、快速原型
- C#: 计算密集型、复杂算法、AI
```

### 1.2 C# 环境配置

```bash
# 安装.NET SDK
# Windows: 下载 .NET SDK 8.0
# macOS: brew install --cask dotnet-sdk
# Linux: 参考微软官方文档

# 验证安装
dotnet --version

# 在 Godot 中启用 C#
# 项目设置 → DotNet → 启用
# 重新生成解决方案
```

```csharp
// C# 脚本示例
using Godot;
using System;

public class PlayerController : CharacterBody2D
{
    [Export] public float Speed { get; set; } = 300.0f;
    [Export] public float JumpVelocity { get; set; } = -400.0f;
    
    private float _health = 100.0f;
    
    public override void _PhysicsProcess(double delta)
    {
        // 获取输入
        var direction = Input.GetAxis("ui_left", "ui_right");
        
        // 应用重力
        if (!IsOnFloor())
            Velocity += new Vector2(0, (float)ProjectSettings.GetSetting("physics/2d/default_gravity")) * (float)delta;
        
        // 跳跃
        if (Input.IsActionJustPressed("ui_accept") && IsOnFloor())
            Velocity = new Vector2(Velocity.X, JumpVelocity);
        
        // 移动
        Velocity.X = direction * Speed;
        MoveAndSlide();
    }
    
    public void TakeDamage(float damage)
    {
        _health -= damage;
        if (_health <= 0)
            Die();
    }
    
    private void Die()
    {
        QueueFree();
    }
}
```

---

## 2. GDScript 与 C# 互操作

### 2.1 互操作基础

```gdscript
# GDScript 调用 C#
# C# 类：PlayerController.cs

# GDScript 中调用
var player = load("res://PlayerController.cs").new()
player.Speed = 400.0

# 调用 C# 方法
player.TakeDamage(10.0)

# 连接信号
player.connect("died", _on_player_died)
```

```csharp
// C# 调用 GDScript
using Godot;

public class GameManager : Node
{
    public void CallGDScript()
    {
        var gdScript = GD.Load<GDScript>("res://GameLogic.gd");
        var instance = gdScript.New();
        
        // 调用 GDScript 方法
        instance.Call("StartGame");
        
        // 获取属性
        var score = instance.Get("score");
    }
}
```

### 2.2 数据交换

```csharp
// C# 与 GDScript 数据交换
using Godot;
using System.Collections.Generic;

public class DataExchange : Node
{
    // 传递基本类型
    public void PassPrimitives()
    {
        int number = 42;
        float pi = 3.14f;
        string text = "Hello";
        Vector3 position = new Vector3(1, 2, 3);
        
        var gdScript = GD.Load<GDScript>("res://Receiver.gd").New();
        gdScript.Call("ReceiveData", number, pi, text, position);
    }
    
    // 传递数组
    public void PassArrays()
    {
        int[] numbers = new int[] { 1, 2, 3, 4, 5 };
        string[] names = new string[] { "Alice", "Bob", "Charlie" };
        
        var gdScript = GD.Load<GDScript>("res://Receiver.gd").New();
        gdScript.Call("ReceiveArrays", numbers, names);
    }
    
    // 传递字典
    public void PassDictionary()
    {
        var dict = new Godot.Collections.Dictionary
        {
            ["name"] = "Player",
            ["level"] = 5,
            ["health"] = 100.0f
        };
        
        var gdScript = GD.Load<GDScript>("res://Receiver.gd").New();
        gdScript.Call("ReceiveDictionary", dict);
    }
    
    // 传递 Godot 对象
    public void PassObjects()
    {
        var player = GetNode<CharacterBody2D>("Player");
        
        var gdScript = GD.Load<GDScript>("res://Receiver.gd").New();
        gdScript.Call("ReceiveObject", player);
    }
}
```

---

## 3. 脚本性能优化

### 3.1 性能分析工具

```gdscript
# 脚本性能分析器
class_name ScriptProfiler

extends Node

var function_times: Dictionary = {}
var frame_count: int = 0

func _ready():
    set_process(true)

func _process(delta):
    frame_count += 1
    
    if frame_count >= 60:
        _print_statistics()
        frame_count = 0
        function_times.clear()

func start_profile(function_name: String):
    if not function_times.has(function_name):
        function_times[function_name] = {
            "total_time": 0.0,
            "calls": 0
        }
    
    function_times[function_name]["start"] = Time.get_ticks_usec()

func end_profile(function_name: String):
    if function_times.has(function_name):
        var elapsed = Time.get_ticks_usec() - function_times[function_name]["start"]
        function_times[function_name]["total_time"] += elapsed
        function_times[function_name]["calls"] += 1

func _print_statistics():
    print("\n=== Script Performance ===")
    
    var sorted = function_times.keys()
    sorted.sort_custom(func(a, b): 
        return function_times[a]["total_time"] > function_times[b]["total_time"]
    )
    
    for func_name in sorted:
        var data = function_times[func_name]
        var avg = data["total_time"] / max(1, data["calls"])
        print("%s: %.2f μs (calls: %d, total: %.2f ms)" % [
            func_name, 
            avg, 
            data["calls"],
            data["total_time"] / 1000.0
        ])

# 使用示例
func update_game_logic():
    $ScriptProfiler.start_profile("update_enemies")
    _update_enemies()
    $ScriptProfiler.end_profile("update_enemies")
    
    $ScriptProfiler.start_profile("update_physics")
    _update_physics()
    $ScriptProfiler.end_profile("update_physics")
```

### 3.2 常见性能陷阱

```
常见性能陷阱:
┌─────────────────────────────────────────────────────────────┐
│ 陷阱              │ 影响          │ 优化建议                │
├─────────────────────────────────────────────────────────────┤
│ 每帧创建对象      │ 高 GC 压力     │ 对象池、预分配         │
│ get_node 每帧调用 │ 字符串查找    │ 缓存节点引用            │
│ 信号频繁连接      │ 内存泄漏      │ 及时断开                │
│ 大量字符串操作    │ 内存分配      │ 使用 StringName         │
│ 深度循环嵌套      │ CPU 负载       │ 优化算法、提前退出      │
│ 不必要的物理查询  │ 性能开销      │ 缓存结果、空间划分      │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# ❌ 错误示例：每帧创建对象
func _process(delta):
    var temp_array = []  # 每帧创建
    for i in range(100):
        temp_array.append(i)
    
    var temp_string = "Result: " + str(temp_array.size())  # 字符串拼接

# ✅ 正确示例：复用对象
var cached_array: Array = []
var cached_string: String = ""

func _process(delta):
    cached_array.clear()  # 复用数组
    for i in range(100):
        cached_array.append(i)
    
    cached_string = "Result: %d" % cached_array.size()  # 格式化字符串

# ❌ 错误示例：每帧 get_node
func _process(delta):
    var player = get_node("Player")
    player.position += Vector2.RIGHT

# ✅ 正确示例：缓存节点引用
var player: Node2D

func _ready():
    player = $Player  # 缓存引用

func _process(delta):
    player.position += Vector2.RIGHT  # 直接使用

# ❌ 错误示例：信号泄漏
func _ready():
    some_node.connect("signal", _on_signal)  # 未断开

# ✅ 正确示例：管理信号生命周期
func _ready():
    some_node.connect("signal", _on_signal)

func _exit_tree():
    some_node.disconnect("signal", _on_signal)  # 断开连接
```

### 3.3 优化技巧

```gdscript
# 1. 使用 StringName 代替 String
var action_name = StringName("ui_accept")  # 只创建一次

func _process(delta):
    if Input.is_action_pressed(action_name):  # 快速比较
        pass

# 2. 对象池
class_name ObjectPool

var pool: Array = []
var scene: PackedScene

func _init(scene: PackedScene, size: int):
    self.scene = scene
    for i in range(size):
        var obj = scene.instantiate()
        obj.set_process(false)
        pool.append(obj)

func get() -> Node:
    if pool.size() > 0:
        var obj = pool.pop_back()
        obj.set_process(true)
        return obj
    return scene.instantiate()

func return(obj: Node):
    obj.set_process(false)
    pool.append(obj)

# 3. 批量处理
func update_all_enemies(delta):
    var enemies = get_tree().get_nodes_in_group("enemies")
    
    # ❌ 错误：逐个处理
    for enemy in enemies:
        enemy.update(delta)
    
    # ✅ 正确：批量处理
    _batch_update_enemies(enemies, delta)

# 4. 避免不必要的信号
# ❌ 错误：每帧发射信号
func _process(delta):
    emit_signal("health_changed", health)

# ✅ 正确：只在变化时发射
var last_health: float = -1

func take_damage(amount: float):
    health -= amount
    if health != last_health:
        emit_signal("health_changed", health)
        last_health = health

# 5. 使用数组推导式
# ❌ 错误：传统循环
var result = []
for i in range(100):
    if i % 2 == 0:
        result.append(i * 2)

# ✅ 正确：数组推导式
var result = [i * 2 for i in range(100) if i % 2 == 0]
```

---

## 4. C# 性能优势场景

### 4.1 计算密集型任务

```csharp
// C# 示例：路径查找（A*算法）
using Godot;
using System.Collections.Generic;

public class PathFinder
{
    public List<Vector2Int> FindPath(Vector2Int start, Vector2Int end, bool[,] grid)
    {
        var openSet = new PriorityQueue<Node, float>();
        var closedSet = new HashSet<Vector2Int>();
        
        openSet.Enqueue(new Node(start, null), 0);
        
        while (openSet.Count > 0)
        {
            var current = openSet.Dequeue();
            
            if (current.Position == end)
                return RetracePath(current);
            
            closedSet.Add(current.Position);
            
            foreach (var neighbor in GetNeighbors(current.Position, grid))
            {
                if (closedSet.Contains(neighbor))
                    continue;
                
                var newCost = current.GCost + GetDistance(current.Position, neighbor);
                
                // ... A* 算法实现
            }
        }
        
        return new List<Vector2Int>();
    }
    
    private class Node
    {
        public Vector2Int Position { get; }
        public Node Parent { get; }
        public int GCost { get; set; }
        public int HCost { get; set; }
        public int FCost => GCost + HCost;
        
        public Node(Vector2Int position, Node parent)
        {
            Position = position;
            Parent = parent;
        }
    }
}
```

### 4.2 复杂数据结构

```csharp
// C# 示例：复杂数据结构
using Godot;
using System.Collections.Generic;
using System.Linq;

public class InventorySystem
{
    private Dictionary<string, Item> _items;
    private List<ItemCategory> _categories;
    
    public InventorySystem()
    {
        _items = new Dictionary<string, Item>();
        _categories = new List<ItemCategory>();
    }
    
    public void AddItem(string id, Item item)
    {
        if (!_items.ContainsKey(id))
            _items[id] = item;
    }
    
    public IEnumerable<Item> GetItemsByCategory(string category)
    {
        return _items.Values.Where(i => i.Category == category);
    }
    
    public Item FindBestItem(Func<Item, bool> predicate)
    {
        return _items.Values.FirstOrDefault(predicate);
    }
}
```

---

## 📝 本章总结

### 核心要点

1. **C# 适合计算密集型任务**，GDScript 适合游戏逻辑
2. **互操作简单高效**，可以混合使用
3. **性能分析指导优化**，先测量再优化
4. **避免常见陷阱**，如每帧创建对象、get_node 调用
5. **使用对象池和缓存**，减少内存分配

### 关键术语

| 术语 | 解释 |
|------|------|
| JIT | 即时编译，C# 性能优势来源 |
| GC | 垃圾回收，注意减少压力 |
| StringName | 唯一字符串，快速比较 |
| Object Pool | 对象池，复用对象 |
| Signal | 信号，注意内存泄漏 |

---

*写作时间：2026-03-21*  
*字数：约 8,000 字*  
*状态：✅ 完成*
