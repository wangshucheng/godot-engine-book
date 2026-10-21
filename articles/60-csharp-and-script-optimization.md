# 第 60 篇：C# 集成和脚本性能优化

> **本卷定位**: 第七卷 脚本系统（5 篇）  
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
│ 特性          │ C#                 │ GDScript               │ 适用场景      │
├─────────────────────────────────────────────────────────────┤
│ 类型系统      │ 静态类型            │ 渐进式类型             │ 大型项目      │
│              │ （编译期确定）      │ （可标注静态类型；       │              │
│              │                    │   未标注处退化为 Variant）│             │
│ 性能          │ 高（JIT 编译）       │ 中（解释执行 + 静态优化） │ 计算密集型    │
│ 开发速度      │ 中                  │ 快                     │ 原型开发      │
│ 学习曲线      │ 陡峭                │ 平缓                   │ 新手友好      │
│ 内存占用      │ 高（.NET 运行时）    │ 低                     │ 移动端        │
│ 启动时间      │ 慢                  │ 快                     │ 快速迭代      │
│ 导出目标      │ 桌面 + 移动端(实验)  │ 全平台（含 Web 导出）   │ 见 1.3 节     │
└─────────────────────────────────────────────────────────────┘

推荐混合使用:
- GDScript: 游戏逻辑、快速原型
- C#: 计算密集型、复杂算法、AI
```

**关于 GDScript 的类型系统（不要再说它是"动态类型"）**

GDScript 4 是**渐进式类型（gradual typing）**：类型标注是**可选**的。

```gdscript
var a: int = 1          # 静态类型：编译器知道它是 int
var b = 1               # 无标注：推断不出确切类型时按 Variant 处理
var c: Array[Vector3] = []  # 类型化容器：元素类型也被约束
```

- 标注了类型的变量，编译器会在编译期做检查，并让运行时走更快的**特化**路径（这就是第 54 篇说的"静态类型更快"）；
- 没标注的地方退化为 `Variant`，行为与 3.x 的动态类型一致；
- 因此"用静态类型更快"这句话是**有条件的**：指的是**你标注过的那些代码路径**，而不是整个脚本。

详见第 54 篇《脚本系统》§2.1（变量和类型）与第 55 篇《GDScript 进阶》§1.1（类型化容器与类型约束）。

### 1.2 C# 环境配置

```bash
# 前置条件（官方 C# 文档 "Prerequisites"）：
# 1) 安装 .NET SDK。Godot 只捆绑了「运行已编译游戏」所需的 .NET 运行时，
#    不包含 MSBuild 与 C# 编译器，SDK 必须自己单独安装。
# 2) 使用 Godot 的 .NET 版本编辑器：标准版编辑器不含 C# 支持。
# 3) SDK 位数要和 Godot 位数一致（64 位 Godot 配 64 位 SDK）。

# 安装 .NET SDK
# Windows: 从 https://dotnet.microsoft.com/download 下载安装包
# macOS:   brew install --cask dotnet-sdk
# Linux:   参考微软官方文档

# 验证安装
dotnet --version

# 创建第一个 C# 脚本时，Godot 会自动生成：
#   <项目名>.csproj / <项目名>.sln   → 需要提交到版本控制
#   .godot/mono/                    → 可以加进 .gitignore
```

> **编辑器支持**：Godot 内置的脚本编辑器对 C# 的支持很有限，官方建议使用外部 IDE（Visual Studio 2022 / VS Code / Rider / MonoDevelop），在「编辑器设置 → Dotnet → Editor → External Editor」里指定。官方文档同时提醒：**每次新增导出变量或信号后都要重新构建程序集**（编辑器右上角的 Build 按钮），否则编辑器看不到新的成员。

```csharp
// C# 脚本示例
using Godot;
using System;

// Godot 4 的脚本类必须声明为 partial（源码生成器需要它来注入成员）
public partial class PlayerController : CharacterBody2D
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

### 1.3 平台与版本约束

C# 不是"换个语言写 Godot"那么简单，它有一组**硬约束**。选型前必须知道，否则会做出一个导出不了的项目。

#### 1.3.1 平台支持矩阵

官方文档（`tutorials/scripting/c_sharp/index.rst`，4.3）的原文表述：

> As of Godot 4.2 projects written in C# support all desktop platforms (Windows, Linux, and macOS), as well as Android and iOS.
>
> Android support is currently experimental and has a few limitations.
>
> iOS support is currently experimental and has a few limitations.
>
> Currently, projects written in C# cannot be exported to the web platform. To use C# on that platform, consider Godot 3 instead.

| 目标平台 | 支持 | 限制 |
|----------|------|------|
| Windows / Linux / macOS | ✅ 正式支持（4.0 起可导出，4.2 起全桌面） | 无 |
| Android | ⚠️ 4.2 起**实验性** | 需 .NET **7.0+**（改 `.csproj` 的 `TargetFramework`）；仅支持 `arm64` 与 `x64` 架构 |
| iOS | ⚠️ 4.2 起**实验性** | 需 .NET **8.0+**；官方 iOS 模拟器导出模板只支持 `x64`；**只能从 macOS 导出** |
| **Web** | ❌ **不支持导出** | "projects written in C# cannot be exported to the web platform" |

**结论**：如果你的项目**必须**上 Web，C# 就是一个错误选择，只能用 GDScript（或用 GDExtension 写原生模块）。

#### 1.3.2 .NET 版本要求

- Godot 4.3 的 C# 模块在 `modules/mono/global.json` 中锁定 **.NET SDK 8.0.0**（`rollForward: latestMajor`，允许用更新的主版本）。官方 4.3 文档仍写着 "implemented with .NET 6.0"，属于文档滞后——**以你所用 Godot 版本的 `global.json` 为准**。
- Android 目标需 .NET 7.0+，需要在 `.csproj` 里加：
  ```xml
  <TargetFramework Condition=" '$(GodotTargetPlatform)' == 'android' ">net7.0</TargetFramework>
  ```
- iOS 目标需 .NET 8.0+：
  ```xml
  <TargetFramework Condition=" '$(GodotTargetPlatform)' == 'ios' ">net8.0</TargetFramework>
  ```
- Godot **只捆绑运行已编译游戏所需的 .NET 运行时**；编译工具（MSBuild、C# 编译器）必须自己装 .NET SDK。

#### 1.3.3 其他容易踩的边界

| 边界 | 说明 |
|------|------|
| **线程安全** | Godot 对象**不是线程安全**的。只能在主线程操作场景树；后台线程只能做纯计算，结果回主线程再应用 |
| **`Callable` 不支持 bind / unbind** | 官方 `c_sharp_differences` 明确列出：C# 侧只支持"用 C# 的 `Callable` 类型创建的"和"引擎基础版 `Callable`"；**带绑定信息的 `Callable`（`bind`/`unbind` 创建的）不受支持**。官方建议改用 lambda 闭包 |
| **结构体是值类型** | `Position.X = 100.0f;` 会编译失败（CS1612）。必须整体取出、修改、再赋回：`Position = Position with { X = 100.0f };` |
| **原生互操作开销** | 每次读写 `Node` 的属性（如 `Position`）都要跨 C# ↔ C++ 边界；`byte[]` / `string` 传参还要额外做封送（marshalling），成本相当可观 |
| **部分 API 仍是 snake_case** | `Get()` / `Set()` / `Call()` / `CallDeferred()` / `Connect()` 这类方法按引擎的 snake_case 约定工作。优先用 `PropertyName` / `MethodName` / `SignalName` 这类 `StringName` 常量，既避免额外分配也避开命名坑 |
| **类名必须与文件名一致** | 挂到节点上的 C# 脚本，其类名必须和 `.cs` 文件名一致，否则报 "Cannot find class XXX for script res://XXX.cs" |
| **热重载丢状态** | 热重载时除导出变量外，状态不会被保存与恢复 |
| **编辑器插件** | 用 C# 写编辑器插件目前"相当繁琐"（官方原话 "quite convoluted"） |

#### 1.3.4 什么时候该选 C#

| 适合 C# | 不适合 C# |
|----------|-----------|
| 计算密集型：寻路、物理求解、程序化生成、加密 | UI 逻辑密集的项目（GDScript 迭代更快） |
| 需要强类型的大型团队项目 | 需要导出到 Web |
| 要用 .NET 生态的库（NuGet） | 需要 iOS 且团队没有 macOS |
| 已有 C# 代码资产要复用 | 小型原型（搭环境的时间就超过收益） |

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
# C# 侧的 [Signal] delegate void DiedEventHandler(); 会生成一个名为
# "Died" 的 Godot 信号（delegate 名去掉 EventHandler 后缀），
# 对应 C# 常量 SignalName.Died。
# 注意：C# 类里没有声明过的信号，在 GDScript 里 connect 会直接报
# "Invalid signal" —— 信号必须先在 C# 侧声明出来。
player.connect("Died", _on_player_died)

func _on_player_died():
    print("玩家死亡")
```

```csharp
// C# 侧：必须真的声明这个信号，否则 GDScript 连不上
using Godot;

public partial class PlayerController : CharacterBody2D
{
    // C# 信号用 [Signal] + public delegate 声明，
    // delegate 名必须以 EventHandler 结尾；
    // 生成的事件名 = delegate 名去掉 EventHandler 后缀（即 "Died"），
    // 同时生成 C# 常量 SignalName.Died。
    [Signal]
    public delegate void DiedEventHandler();

    private void Die()
    {
        // 发射信号：必须用 SignalName 常量，不能写字符串
        EmitSignal(SignalName.Died);
        QueueFree();
    }
}
```

> ⚠️ **跨语言连接信号的规则**：C# 自定义信号**必须**用 `[Signal]` 声明才会被 GDScript 看见；而且用 `+=` 连接的**自定义信号**在接收方被释放时**不会自动断开**（引擎内置信号会，C# 自定义信号不会）。需要自动断开时改用 `Connect()`：
> ```csharp
> target.Connect(MyClass.SignalName.MySignal, Callable.From(OnMySignal));
> ```

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

### 2.3 互操作的边界

C# 与 GDScript 之间的一切数据都要经过 **`Variant`**。这一节把"哪些值能过边界、过界的代价是什么、回调有哪些限制"讲清楚。

#### 2.3.1 Variant 装箱与精度

- Godot 的 `Variant` 内部是 **64 位整数**和 **64 位浮点**。C# 的 `int` / `short` / `float` 都能塞进去，但**转换时可能丢精度**（例如 `float` → Variant 是 `double`，`int` → Variant 是 `long`）。传参时统一用 `long` / `double` 对应的 Variant 语义更安全。
- `Variant` 在 C# 里是**结构体**，不能为 `null`；要表示"空"用 `default` 或 `new Variant()`。
- **枚举不能隐式转换**。C# 的 `enum` 必须先转成底层整数再进 Variant：
  ```csharp
  Variant v = (int)MyEnum.A;
  MyEnum back = (MyEnum)(int)v;
  // 或者
  Variant v2 = Variant.From(MyEnum.A);
  MyEnum back2 = v2.As<MyEnum>();
  ```
- **装箱发生在每一次跨界调用**。把值放进 `object` 或 `Variant` 就会产生一次装箱；高频路径上应尽量用强类型参数，让 C# 的重载直接选中，避免走 `Variant` 路径。

#### 2.3.2 `Godot.Collections` 与 `System.Collections`

| | `Godot.Collections.Array` / `Dictionary` | `System.Collections.Generic.List<T>` / `Dictionary<K,V>` |
|---|---|---|
| 实现 | C++ 侧实现，C# 只是包装 | 纯 C# 实现 |
| 元素类型 | `Variant`（或类型化包装 `Array<T>` / `Dictionary<K,V>`） | 任意 .NET 类型 |
| 能否直接传给 Godot API | ✅ 可以 | ❌ **不可以**（不是 Variant 兼容类型） |
| 单次操作的代价 | 每次操作都要**封送（marshalling）** | 纯托管，**快得多** |
| 适用 | 需要和引擎交互时（导出属性、调用引擎方法） | 纯 C# 内部逻辑，尤其是循环里 |

**选择原则（官方文档原话大意）**：

> Godot 只理解它自己的集合类型，所以和引擎打交道时必须用 Godot 集合；但**不需要**传给引擎的集合，用 .NET 集合性能更好。

```csharp
// ❌ 传给引擎 API 会失败：List<T> 不是 Variant 兼容类型
var list = new List<int> { 1, 2, 3 };
GetNode("Sprite").Set("some_array", list);   // 报错

// ✅ 需要和引擎交互时用 Godot 集合
var godotList = new Godot.Collections.Array<int> { 1, 2, 3 };
GetNode("Sprite").Set("some_array", godotList);

// ✅ 纯 C# 内部计算用 .NET 集合（循环里快得多）
var scores = new List<int>();
for (int i = 0; i < 10000; i++) { /* ... */ }
```

其他坑：

- 两者可以互转，但**转换本身要逐元素封送 + 复制**，在热路径上别做。
- `Godot.Collections.Array` 的 `Sort()` / `Reverse()` 是**单次互操作调用**实现的（不逐元素封送），比 LINQ 的等价写法快；反过来，**任何接受 `IEnumerable<T>` 的 LINQ 方法都会逐元素迭代、逐元素封送**。
- `Godot.Collections.Dictionary<string, Variant>` 用来表达"键有类型、值任意"的字典。

#### 2.3.3 跨语言的信号与回调

| 方向 | 做法 | 限制 |
|------|------|------|
| GDScript → C# 方法 | `load("res://X.cs").new()` 后直接调用 | C# 类必须 `partial`；类名必须与 `.cs` 文件名一致 |
| GDScript → C# 信号 | `player.connect("Died", _on_died)` | C# 侧必须 `[Signal]` 声明过，否则 `Invalid signal` |
| C# → GDScript 方法 | `GD.Load<GDScript>("res://X.gd").New()` + `instance.Call("Method", args)` | `Call` 走 `Variant` 路径，比 C# 内部调用慢 |
| C# → GDScript 信号 | `gdscript.Connect("signal_name", Callable.From(OnSignal))` | 必须用 `Connect()`（`+=` 只能接 C# 事件） |
| C# → C# 回调 | `Callable.From(() => ...)` | **`bind` / `unbind` 在 C# 侧不支持**，用 lambda 闭包代替 |

```csharp
// C# 里创建带参数的回调：C# 侧没有 bind，用闭包
string playerName = "John Doe";
Callable onGreet = Callable.From(() => SayHello(playerName));

private void SayHello(string name)
{
    GD.Print($"Hello {name}!");
}
```

#### 2.3.4 性能建议

- **热循环里把引擎属性缓存到局部变量**。每次读 `Position` 都是一次跨 C# ↔ C++ 的原生互操作：
  ```csharp
  // ❌ 每次循环都跨边界
  for (int i = 0; i < 10; i++) { Position += new Vector3(i, i); }
  
  // ✅ 读一次，改完再写回
  var p = Position;
  for (int i = 0; i < 10; i++) { p += new Vector3(i, i); }
  Position = p;
  ```
- **`byte[]` / `string` 传参要封送**，成本相当可观；能传 `PackedByteArray`（即 `byte[]`）就别传 `string` 再让引擎解析。
- **`string` → `NodePath` / `StringName` 的隐式转换**同样要付互操作 + 封送；把 `NodePath` / `StringName` 存成字段复用，别在循环里现转。
- 频繁跨语言调用时，考虑把整段计算搬到**一侧**完成（要么全 C#、要么全 GDScript），而不是每帧来回传数据。

> ⚠️ **性能论断的标注**：本节关于"互操作更贵""Godot 集合循环更慢"的结论来自官方文档的定性描述（"requires marshaling which can be expensive especially inside a loop"），**没有附本项目的实测数据**。定量结论请用第 3 节的分析器在自己的项目里量。

---

## 3. 脚本性能优化

> ⚠️ **关于本章的性能结论**：本章列出的"常见性能陷阱"与"优化技巧"来自 Godot 官方文档与社区经验的**定性总结**，**未附本项目的实测数据**（没有给出 CPU 型号、场景规模、对象数量、测量时长等条件）。它们指出的是**值得优先验证的方向**，不是"优化后一定快 X%"的承诺。
>
> **可复现的测量方法**（本章自带的工具就能做）：
> 1. 用 3.1 节的 `ScriptProfiler` 包住被怀疑的函数，跑一段固定时长（例如 60 秒）。
> 2. 记录三组数据：**未优化版本**、**优化版本**、**同一台机器上的空循环基线**。
> 3. 报告时必须同时写明：Godot 版本（含是否用 .NET 版编辑器）、CPU 型号、是否 Debug 构建、场景对象数、测量时长、帧率。
> 4. 只有第 3 步的信息齐了，"快了多少"才是可复现的结论；否则一律标为示意数据。
>
> 官方也提供了一份跨语言的性能对比说明（Godot FAQ "Which programming language is fastest"），需要定量结论时请以它和自己的实测为准。

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
    some_node.signal_name.disconnect(_on_signal)  # 断开连接
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

# 5. 预分配 + 一次遍历
# ⚠️ GDScript 4 **没有** Python 式的数组推导式（list comprehension）。
# 写成 `var result = [i * 2 for i in range(100) if i % 2 == 0]`
# 是**语法错误**（GDScript 解析器里根本没有产生这种表达式的节点），
# 照抄会直接报 Parse Error。
# ❌ 错误：动态增长 + 反复扩容
var result = []
for i in range(100):
    if i % 2 == 0:
        result.append(i * 2)

# ✅ 正确：预分配上界 + 按下标写入 + 最后裁剪
var result: Array[int] = []
result.resize(50)  # 预分配，避免 Array 在扩容时反复拷贝
var n := 0
for i in range(100):
    if i % 2 == 0:
        result[n] = i * 2
        n += 1
result.resize(n)   # 裁掉未使用的空位
```

---

## 4. C# 性能优势场景

> ⚠️ **不要把"C# 更快"当成结论**。C# 的优势来自 JIT（AOT 场景例外）与静态类型带来的特化，但 Godot 侧的成本同样存在：**每次访问 `Node` 属性都是一次 C# ↔ C++ 的原生互操作**，`byte[]` / `string` 传参还要额外封送。也就是说：
> - **纯计算**（寻路、噪声生成、矩阵运算、加密）：C# 优势明显；
> - **每帧大量读写节点属性**：C# 的互操作开销可能吃掉全部优势；
> - **每帧跨语言传数组 / 字符串**：C# 未必更快。
>
> 本节的两个示例分别对应"计算密集"和"数据结构复杂"两种典型收益场景，但**没有附实测数据（未附测试环境）**。请用 3.1 节的工具在自己的项目里量一遍再决定。

### 4.1 计算密集型任务

```csharp
// C# 示例：路径查找（A* 算法）
//
// 注意两个 Godot 4 C# API 的细节：
// 1. 整数向量类型叫 Vector2I（不是 Godot 3 时代的 Vector2Int）；
// 2. PriorityQueue<TElement, TPriority> 需要 .NET 6+（Godot 4.3 要求 .NET 8 SDK）。
using Godot;
using System.Collections.Generic;

// 这是一个纯 C# 辅助类（不继承 Node），由游戏逻辑自行管理生命周期
public class PathFinder
{
    /// <summary>
    /// 四方向 A*。grid[x, y] == true 表示该格子可通行。
    /// 找不到路径时返回空列表。
    /// </summary>
    public List<Vector2I> FindPath(Vector2I start, Vector2I end, bool[,] grid)
    {
        // openSet：按 f 值排序的待扩展节点
        var openSet = new PriorityQueue<Node, int>();
        // cameFrom：记录每个节点是从哪个节点扩展出来的（用于回溯路径）
        var cameFrom = new Dictionary<Vector2I, Node>();

        var startNode = new Node(start, 0, Heuristic(start, end), null);
        openSet.Enqueue(startNode, startNode.FCost);

        while (openSet.Count > 0)
        {
            var current = openSet.Dequeue();

            if (current.Position == end)
                return RetracePath(cameFrom, current);

            foreach (var neighbor in GetNeighbors(current.Position, grid))
            {
                // 已经从更优的路径到达过这个格子就跳过
                if (cameFrom.TryGetValue(neighbor, out var known) && known.GCost <= current.GCost + 1)
                    continue;

                cameFrom[neighbor] = current;
                // g = 从起点走到这里花的步数；h = 到终点的估计步数
                var newNode = new Node(neighbor, current.GCost + 1, Heuristic(neighbor, end), current);
                openSet.Enqueue(newNode, newNode.FCost);
            }
        }

        return new List<Vector2I>();
    }

    // 从终点沿 cameFrom 回溯出完整路径
    private List<Vector2I> RetracePath(Dictionary<Vector2I, Node> cameFrom, Node current)
    {
        var path = new List<Vector2I> { current.Position };
        while (current.Parent != null)
        {
            current = current.Parent;
            path.Add(current.Position);
        }
        path.Reverse();
        return path;
    }

    // 四方向邻居（越界或不可通行的格子直接跳过）
    private IEnumerable<Vector2I> GetNeighbors(Vector2I position, bool[,] grid)
    {
        int x = position.X;
        int y = position.Y;

        if (x > 0 && grid[x - 1, y]) yield return new Vector2I(x - 1, y);
        if (x < grid.GetLength(0) - 1 && grid[x + 1, y]) yield return new Vector2I(x + 1, y);
        if (y > 0 && grid[x, y - 1]) yield return new Vector2I(x, y - 1);
        if (y < grid.GetLength(1) - 1 && grid[x, y + 1]) yield return new Vector2I(x, y + 1);
    }

    // 曼哈顿距离：四方向移动下的可采纳启发式
    private int GetDistance(Vector2I a, Vector2I b)
    {
        return Mathf.Abs(a.X - b.X) + Mathf.Abs(a.Y - b.Y);
    }

    private int Heuristic(Vector2I a, Vector2I b)
    {
        return GetDistance(a, b);
    }

    private class Node
    {
        public Vector2I Position { get; }
        public Node Parent { get; }
        public int GCost { get; }
        public int HCost { get; }
        public int FCost => GCost + HCost;

        public Node(Vector2I position, int gCost, int hCost, Node parent)
        {
            Position = position;
            GCost = gCost;
            HCost = hCost;
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

// —— 最小类型定义 ——
// ItemCategory：物品分类
public class ItemCategory
{
    public string Id { get; }
    public string DisplayName { get; }

    public ItemCategory(string id, string displayName)
    {
        Id = id;
        DisplayName = displayName;
    }
}

// Item：物品
public class Item
{
    public string Id { get; }
    public string Name { get; }
    public ItemCategory Category { get; }
    public int Price { get; set; }

    public Item(string id, string name, ItemCategory category, int price)
    {
        Id = id;
        Name = name;
        Category = category;
        Price = price;
    }
}

public class InventorySystem
{
    // 纯 C# 内部逻辑用 .NET 集合（比 Godot.Collections 快，见 2.3.2 节）
    private readonly Dictionary<string, Item> _items = new();
    private readonly List<ItemCategory> _categories = new();

    public IReadOnlyCollection<ItemCategory> Categories => _categories;

    public void AddCategory(ItemCategory category)
    {
        _categories.Add(category);
    }

    public void AddItem(string id, Item item)
    {
        // 原来的 ContainsKey + 索引器写法可以简化成索引器的取值即写入
        _items[id] = item;
    }

    public IEnumerable<Item> GetItemsByCategory(string categoryId)
    {
        return _items.Values.Where(i => i.Category.Id == categoryId);
    }

    public Item FindBestItem(Func<Item, bool> predicate)
    {
        return _items.Values.FirstOrDefault(predicate);
    }

    public bool RemoveItem(string id)
    {
        return _items.Remove(id);
    }
}
```

> ⚠️ **`Item` 是纯 C# 类，不能直接交给引擎**。Godot 只接受 **Variant 兼容类型**（见 2.3.1 节），而普通 C# 类不是——它不能作为导出属性，也不能放进 `Godot.Collections.Dictionary` 传给引擎 API。
>
> 如果物品数据需要进编辑器、保存成资源、或传给引擎 API，就要让它继承 `Resource`（并把类声明为 `partial`）：
> ```csharp
> using Godot;
>
> public partial class Item : Resource
> {
>     [Export] public string Id { get; set; } = "";
>     [Export] public string Name { get; set; } = "";
>     [Export] public int Price { get; set; }
> }
> ```
> 此时容器也要换成 Godot 集合：
> ```csharp
> var items = new Godot.Collections.Dictionary<string, Item>();
> items["sword"] = new Item { Id = "sword", Name = "长剑", Price = 100 };
> ```

---

## 📝 本章总结

### 核心要点

1. **C# 适合计算密集型任务**，GDScript 适合游戏逻辑
2. **GDScript 是渐进式类型**，不是"动态类型"；静态标注过的路径才是性能收益所在
3. **C# 有硬约束**：Web 不可导出、移动端实验性、需要 .NET SDK
4. **互操作有边界**：`Variant` 装箱、集合选型、`Callable` 不支持 bind/unbind
5. **性能分析指导优化**，先测量再优化
6. **避免常见陷阱**，如每帧创建对象、get_node 调用

### 关键术语

| 术语 | 解释 |
|------|------|
| JIT | 即时编译，C# 性能优势来源 |
| GC | 垃圾回收，注意减少压力 |
| StringName | 唯一字符串，快速比较 |
| Object Pool | 对象池，复用对象 |
| Signal | 信号，注意内存泄漏 |
| Variant | Godot 的动态类型容器，跨语言边界的一切数据都要经过它 |
| Marshalling | 封送，C# 与 Godot C++ 之间搬运数据的成本 |
| Progressive Typing | 渐进式类型，GDScript 4 的类型系统 |

---

## 🔗 延伸阅读

- **官方文档**: [C# 与 .NET](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/index.html)
- **官方文档**: [C# API 与 GDScript 的差异](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_differences.html)
- **配套篇目**: 第 54 篇《脚本系统》（GDScript 类型系统）、第 55 篇《GDScript 进阶》（类型化容器与性能调优）

---

## 📋 下一章预告

**第 61 篇：高级编辑器扩展**

- `EditorPlugin` 的完整生命周期
- 自定义节点与 Inspector
- 导入 / 导出插件
- 与 GDExtension 的配合


**上一篇**: [第 56 篇：资源加载与缓存实战](/articles/56-resource-system.md)
**下一篇**: [第 58 篇：插件开发](/articles/58-plugin-development.md)
---

*写作时间：2026-03-21*  
*字数：约 2,700 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*  

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）
