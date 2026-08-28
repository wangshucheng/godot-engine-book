# 第 35 篇：引擎 C++ 自定义模块开发

> **本卷定位**: 引擎扩展开发卷  
> **前置知识**: C++ 基础、SCons 构建工具、Godot 对象系统（第 5 篇）、GDExtension 概念  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家

---

## 📖 本章导读

GDExtension 让我们可以用 C++ 扩展 Godot 而无需改动引擎源码，但它本质上是「引擎之外」的动态库——能做的事情受限于 GDExtension 暴露的 API 边界。当你需要更深的引擎集成时——比如绑定一个需要直接访问引擎内部结构的外部库、向引擎添加新的 Server 子系统、修改核心类型的注册顺序、或者把性能关键的系统做成引擎原生能力——就需要走进引擎源码树，编写**自定义 C++ 模块（Custom Module）**。模块是 Godot 官方提供的模块化扩展机制：GDScript 本身、GridMap、正则表达式等功能在引擎中都是以模块形式存在的。本章将完整走一遍自定义模块的开发流程：模块机制的本质、目录结构与构建系统、类型注册机制、一个可编译的完整 Summator 示例模块、编辑器集成与子系统挂接，以及重编译引擎的完整流程。

---

## 🎯 学习目标

- 理解自定义模块在引擎源码树中的位置及其与 GDExtension 的本质区别
- 掌握模块目录结构：`SCsub`、`config.py` 与 `env.add_source_files`
- 掌握 `register_types.h` / `register_types.cpp` 注册机制与模块初始化级别
- 能够从零编写一个编译进引擎二进制的完整示例模块并在 GDScript 中使用
- 学会为模块添加自定义图标、文档以及编辑器专属代码（`TOOLS_ENABLED`）
- 理解模块如何与引擎子系统（Servers、导入器等）交互
- 掌握重编译引擎及导出模板的完整流程与常见陷阱

---

## 1. 自定义模块是什么

### 1.1 模块：引擎的模块化扩展机制

Godot 引擎本身采用模块化设计。打开引擎源码仓库，你会看到一个 `modules/` 子目录，里面躺着几十个官方模块：

```
godot/                          # 引擎源码根目录
├── core/                       # 核心：对象系统、数学库、内存管理
├── servers/                    # 各类 Server 子系统
├── scene/                      # 场景树与节点体系
├── editor/                     # 编辑器
├── modules/                    # ★ 模块目录，官方与自定义模块的家
│   ├── gdscript/               # 是的，GDScript 也只是一个模块
│   ├── gridmap/                # GridMap 节点支持
│   ├── regex/                  # 正则表达式模块
│   ├── mono/                   # C# 支持
│   ├── websocket/              # WebSocket 支持
│   └── summator/               # ★ 我们要写的自定义模块放这里
└── SConstruct                  # SCons 主构建脚本
```

这带来一个重要认知：**模块不是二等公民**。GDScript 之于引擎，和你写的自定义模块之于引擎，在机制上完全平级——都是放在 `modules/` 下、由 SCons 构建系统透明地编译、链接进引擎二进制的一堆 C++ 源码。官方文档对此的表述是：Godot 允许以模块化的方式扩展引擎，新模块可以被创建、启用或禁用，从而在不修改核心（core）的前提下为引擎的各个层级添加新功能。

SCons 构建系统会自动扫描 `modules/` 下的每一个子目录，读取其中的 `config.py` 决定是否构建、执行其中的 `SCsub` 收集源文件，最后把模块的代码静态链接进最终的可执行文件。开发者要做的只是把符合约定的文件放到符合约定的位置。

### 1.2 模块的典型应用场景

官方文档列举了自定义 C++ 模块的几个典型用途：

- **绑定外部库到 Godot**：如 PhysX、FMOD 这类无法或不方便通过 GDExtension 接入的库
- **优化游戏的关键路径**：把热点代码用 C++ 写成引擎原生代码
- **为引擎或编辑器添加新功能**：新节点类型、新资源格式、新编辑器工具
- **把现有游戏移植到 Godot**：复用已有的 C++ 代码资产
- **整个游戏都用 C++ 写**：如果你就是离不开 C++

### 1.3 模块与 GDExtension 的本质区别

这是选型时最关键的问题。两者都能用 C++ 扩展 Godot，但机制完全不同：

```
┌──────────────────────────────────────────────────────────────────────┐
│                    模块 vs GDExtension 架构对比                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  【自定义模块】                        【GDExtension】                │
│  ┌────────────────────┐               ┌────────────────────┐        │
│  │  godot 源码树      │               │  独立项目目录       │        │
│  │  └── modules/      │               │  ├── godot-cpp/    │        │
│  │      └── mymodule/ │               │  └── src/          │        │
│  └────────┬───────────┘               └────────┬───────────┘        │
│           │ scons 静态编译、链接                │ scons 编译为        │
│           ▼                                    │ .dll/.so/.dylib     │
│  ┌────────────────────┐                        ▼                     │
│  │ godot 可执行文件    │               ┌────────────────────┐        │
│  │ （模块代码在其中）  │               │  动态库 + .gdextension 描述文件 │
│  └────────────────────┘               └────────┬───────────┘        │
│                                                 │ 引擎运行时动态加载   │
│                                          ┌──────▼───────────┐        │
│                                          │  官方引擎二进制   │        │
│                                          └──────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
```

| 维度 | 自定义模块 | GDExtension |
|------|-----------|-------------|
| 链接方式 | 静态编译、链接进引擎二进制 | 运行时加载的动态库 |
| 分发形式 | 必须分发整个定制引擎 | 只需分发库文件，用官方引擎即可 |
| 访问能力 | 引擎全部内部 API，无边界 | 仅限 GDExtension API 暴露的部分 |
| 迭代速度 | 每次改动都要重编译引擎 | 只重编译扩展库，编辑器可热重载 |
| 与引擎版本耦合 | 紧跟引擎源码，升级需人工合并 | 跨小版本通常兼容（4.1 构建可用于 4.2，反之不行） |
| 适用场景 | 深度引擎集成、新子系统 | 游戏逻辑、外部 SDK 接入、工具库 |

官方的建议非常明确：**大多数游戏逻辑应该用脚本写，需要 C++ 时优先考虑 GDExtension**，因为它不需要每次代码改动都重编译引擎。只有当 GDExtension 不够用、确实需要更深的引擎集成时，才应该写 C++ 模块。换句话说，模块是「最后的重武器」，不是默认选项。

> **选型经验**：先问自己三个问题——(1) 我需要访问 GDExtension API 未暴露的引擎内部吗？(2) 我需要改变引擎类型的注册时机或覆盖引擎自身的回调吗？(3) 我愿意为团队维护一套定制引擎构建管线吗？三个都答「是」，才轮到模块出场。

---

## 2. 模块目录结构与构建系统

### 2.1 最小模块的文件清单

一个最小可用的模块只需要 6 个文件。以我们要写的 `summator` 模块为例：

```
godot/modules/summator/
├── config.py             # 模块配置：能否构建、如何配置
├── SCsub                 # 构建脚本：告诉 SCons 编译哪些源文件
├── summator.h            # 业务类头文件
├── summator.cpp          # 业务类实现
├── register_types.h      # 注册入口声明
└── register_types.cpp    # 注册入口实现
```

其中 `config.py`、`SCsub`、`register_types.h`、`register_types.cpp` 这四个是**构建系统约定的固定文件名**，缺一不可；业务类文件（`summator.h/.cpp`）的名字和数量则完全自由。

### 2.2 config.py：模块的「准入开关」

`config.py` 是一个 Python 脚本，构建系统在决定是否编译该模块时会调用其中的函数：

```python
# config.py

def can_build(env, platform):
    return True

def configure(env):
    pass
```

两个函数的职责：

- **`can_build(env, platform)`**：构建系统询问模块「当前平台能构建你吗」。返回 `True` 表示所有平台都构建。如果你的模块依赖某个只在特定平台存在的库，就在这里做判断，例如只在桌面平台启用：

```python
def can_build(env, platform):
    # 只在桌面平台构建本模块
    return platform in ("windows", "linux", "macos")
```

- **`configure(env)`**：模块被启用后、编译前调用，可在此检查依赖、追加构建选项。比如检测第三方库是否存在，不存在时可通过 `env.module_env` 调整或直接报错。

除了这两个必需函数，`config.py` 还支持几个可选钩子（后续章节会用到）：

```python
def get_doc_path():
    return "doc_classes"      # 模块自带文档的目录

def get_doc_classes():
    return ["Summator"]       # 本模块注册的类清单

def get_icons_path():
    return "icons"            # 自定义编辑器图标目录
```

另外，模块还可以通过构建选项被整体禁用。假设模块目录名为 `summator`，编译时传入 `module_summator_enabled=no` 即可跳过它——这是 SCons 为每个模块自动生成的开关。

### 2.3 SCsub：收集源文件

`SCsub` 是 SCons 的子构建脚本，核心工作只有一件事：把本模块的 `.cpp` 文件加入构建。

```python
# SCsub

Import('env')

# 把当前目录下所有 cpp 文件加入模块构建
env.add_source_files(env.modules_sources, "*.cpp")
```

关键点解析：

- `Import('env')`：导入引擎主构建环境对象 `env`。
- `env.add_source_files(env.modules_sources, "*.cpp")`：把匹配到的源文件追加到 `env.modules_sources` 这个列表。构建系统最后会把所有模块的 `modules_sources` 统一编译并链接进引擎。

当源文件较多时，也可以显式列出，甚至利用 Python 的循环和条件语句动态构造文件列表：

```python
Import('env')

# 显式列出源文件
src_list = ["summator.cpp", "other.cpp", "etc.cpp"]
env.add_source_files(env.modules_sources, src_list)

# 也可以按子目录组织
env.add_source_files(env.modules_sources, "core/*.cpp")
env.add_source_files(env.modules_sources, "editor/*.cpp")
```

### 2.4 头文件路径与自定义编译选项

如果模块绑定了第三方库，需要告诉编译器去哪里找头文件：

```python
Import('env')

env.add_source_files(env.modules_sources, "*.cpp")

# 相对路径：相对于本 SCsub 所在目录
env.Append(CPPPATH=["mylib/include"])
# 以 # 开头：相对于引擎源码根目录的"绝对"路径
env.Append(CPPPATH=["#myotherlib/include"])
```

如果需要给模块加自定义编译选项（比如 `-O2`），**必须先克隆 env**，否则这些选项会污染整个引擎的构建，可能引发难以排查的错误：

```python
Import('env')

# 克隆构建环境，避免污染全局引擎构建
module_env = env.Clone()
module_env.add_source_files(env.modules_sources, "*.cpp")

# CCFLAGS 同时作用于 C 和 C++
module_env.Append(CCFLAGS=['-O2'])
# 如需区分：
# module_env.Append(CFLAGS=[...])   # 仅 C
# module_env.Append(CXXFLAGS=[...]) # 仅 C++
```

注意一个细节：即使使用了克隆的 `module_env`，`add_source_files` 的第一个参数依然是全局的 `env.modules_sources`——我们改的是「用什么选项编译」，而源文件清单始终汇总到全局。

### 2.5 把模块放在引擎源码树之外

直接把模块丢进 `godot/modules/` 是最简单的方式，但有两个现实问题：

1. 引擎源码树的 Git 工作区会被模块文件「弄脏」，提交时需要小心过滤；
2. 想在「带模块」和「不带模块」两种构建间切换时，得来回拷贝目录或手动传 `module_xxx_enabled=no`。

为此，构建系统提供了 `custom_modules` 编译选项，接受一个逗号分隔的目录路径列表，路径下的所有模块都会被当作自定义模块编译：

```bash
# 把模块移到引擎源码树之外
mkdir ../modules
mv modules/summator ../modules

# 编译时指定外部模块目录
scons custom_modules=../modules
```

> **注意**：传给 `custom_modules` 的路径会在构建系统内部被转换为绝对路径，用于区分自定义模块与内置模块。这意味着模块文档生成等功能可能依赖你机器上的特定路径结构。

---

## 3. 类型注册机制

### 3.1 引擎启动时的类型注册流水线

模块代码被静态链接进引擎后，引擎怎么知道模块里有哪些类？答案是约定的注册入口函数。引擎启动时会按固定顺序调用各级注册函数，一个粗略的顺序如下：

```
引擎启动类型注册顺序（简化）：
┌────────────────────────────────────────────┐
│  preregister_module_types()     ← 模块预注册 │
│  preregister_server_types()                  │
│  register_core_singletons()                  │
│  register_server_types()                     │
│  register_scene_types()                      │
│  EditorNode::register_editor_types()         │
│  register_platform_apis()                    │
│  register_module_types()          ← 模块注册 │
│  initialize_physics()                        │
│  initialize_navigation_server()              │
│  register_server_singletons()                │
│  register_driver_types()                     │
│  ScriptServer::init_languages()              │
└────────────────────────────────────────────┘
```

我们的 `Summator` 类就是在 `register_module_types()` 阶段被注册的。理解这个顺序很重要：如果你想让模块中的某些类型**早于**引擎内置类型注册（比如要覆盖引擎自身的回调、或满足单例依赖），就需要用到预注册钩子（见 3.4 节）。

### 3.2 register_types.h / register_types.cpp

Godot 4.x 中，模块通过一对名为 `initialize_<模块名>_module` / `uninitialize_<模块名>_module` 的函数完成注册与反注册。构建系统会根据模块目录名自动生成调用代码，因此**函数名中间的词必须与模块文件夹名完全一致**。

这两个文件必须放在模块的顶层目录（与 `SCsub`、`config.py` 同级），否则模块无法被正确注册。

`register_types.h`：

```cpp
#include "modules/register_module_types.h"

void initialize_summator_module(ModuleInitializationLevel p_level);
void uninitialize_summator_module(ModuleInitializationLevel p_level);
/* 是的，函数名中间的词必须和模块文件夹名相同 */
```

`register_types.cpp`：

```cpp
#include "register_types.h"

#include "core/object/class_db.h"
#include "summator.h"

void initialize_summator_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ClassDB::register_class<Summator>();
}

void uninitialize_summator_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 本例无需清理
}
```

### 3.3 模块初始化级别（ModuleInitializationLevel）

注意上面两个函数都带一个 `ModuleInitializationLevel` 参数。引擎的初始化是分阶段推进的，模块的初始化函数会在**每个阶段都被调用一次**，模块自己判断「这个阶段有没有我的事」：

```
┌──────────────────────────────┬────────────────────────────────────┐
│ 初始化级别                    │ 适合注册的内容                      │
├──────────────────────────────┼────────────────────────────────────┤
│ MODULE_INITIALIZATION_LEVEL_CORE   │ 核心类型、核心单例            │
│ MODULE_INITIALIZATION_LEVEL_SERVERS│ Server 相关类型               │
│ MODULE_INITIALIZATION_LEVEL_SCENE  │ 场景节点、资源等常规游戏类型   │
│ MODULE_INITIALIZATION_LEVEL_EDITOR │ 编辑器专属类型（仅编辑器构建） │
└──────────────────────────────┴────────────────────────────────────┘
```

绝大多数游戏逻辑类（像 `Summator`）应该在 `MODULE_INITIALIZATION_LEVEL_SCENE` 级别注册，所以惯用法就是开头那个 `if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) return;` 守卫。

`ClassDB::register_class<Summator>()` 是注册的核心：它把类的构造方法、`_bind_methods()` 中绑定的方法/属性/信号录入 ClassDB 数据库，之后脚本系统、编辑器、序列化系统才能「看见」这个类。

### 3.4 预注册钩子：preregister_XXX_types

如果模块需要在**一切内置类型注册之前**行动——典型场景是满足单例运行时依赖、或抢在引擎自身赋值之前覆盖某个方法回调——可以定义可选的预注册函数。

这需要显式声明一个宏，告诉构建系统在编译期生成对应的调用代码：

`register_types.h`：

```cpp
#define MODULE_SUMMATOR_HAS_PREREGISTER
void preregister_summator_types();

void initialize_summator_module(ModuleInitializationLevel p_level);
void uninitialize_summator_module(ModuleInitializationLevel p_level);
```

`register_types.cpp`：

```cpp
#include "register_types.h"

#include "core/object/class_db.h"
#include "summator.h"

void preregister_summator_types() {
    // 在任何其他核心类型注册之前被调用。
    // 本例无需操作。
}

void initialize_summator_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ClassDB::register_class<Summator>();
}

void uninitialize_summator_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 本例无需清理。
}
```

要点：

- 宏名规则是 `MODULE_<模块名大写>_HAS_PREREGISTER`，模块名必须转为大写；
- 与其他注册函数不同，预注册不会自动生成——必须显式定义这个宏，构建系统才知道要包含相关调用；
- 预注册函数不带初始化级别参数，它只在 `preregister_module_types()` 阶段被调用一次。

---

## 4. 完整示例：Summator 模块

现在把所有零件组装起来，从零写一个完整、可编译的 Summator 模块。这个例子来自官方文档，是模块开发的「Hello World」。

### 4.1 前提：获取并编译引擎源码

在创建模块之前，必须先下载 Godot 源码并成功编译一次原版引擎，确保构建环境（Python、SCons、C++ 工具链）工作正常：

```bash
git clone https://github.com/godotengine/godot.git
cd godot

# 先编译一次原版引擎验证环境（以 Windows 为例）
scons platform=windows target=editor -j8
```

首次完整编译视机器性能需要十几分钟到一小时以上。确认 `bin/` 目录下生成了可运行的编辑器二进制后，再开始写模块。

### 4.2 编写业务类

创建目录 `godot/modules/summator/`，先写头文件：

```cpp
// godot/modules/summator/summator.h
#pragma once

#include "core/object/ref_counted.h"

class Summator : public RefCounted {
    GDCLASS(Summator, RefCounted);  // 必需宏：让 Godot 对象系统识别本类

    int count;  // 内部累加值

protected:
    // 静态绑定函数：向 ClassDB 注册方法、属性、信号
    static void _bind_methods();

public:
    void add(int p_value);
    void reset();
    int get_total() const;

    Summator();
};
```

实现文件：

```cpp
// godot/modules/summator/summator.cpp
#include "summator.h"

void Summator::add(int p_value) {
    count += p_value;
}

void Summator::reset() {
    count = 0;
}

int Summator::get_total() const {
    return count;
}

void Summator::_bind_methods() {
    // 把 C++ 方法绑定到脚本系统，D_METHOD 声明方法名与参数名
    ClassDB::bind_method(D_METHOD("add", "value"), &Summator::add);
    ClassDB::bind_method(D_METHOD("reset"), &Summator::reset);
    ClassDB::bind_method(D_METHOD("get_total"), &Summator::get_total);
}

Summator::Summator() {
    count = 0;
}
```

三条铁律（官方文档反复强调）：

- **使用 `GDCLASS` 宏**：这是 Godot 对象系统的入场券，提供类型信息、虚表挂钩等基础设施；
- **使用 `_bind_methods` 绑定方法**：只有绑定过的方法才能被脚本调用、才能作为信号的回调；
- **暴露给 Godot 的类避免多重继承**：`GDCLASS` 不支持多重继承。不暴露给脚本 API 的内部类可以随意用。

### 4.3 编写注册入口

按第 3 节的内容创建 `register_types.h` 和 `register_types.cpp`，文件名固定，放在模块顶层目录。

### 4.4 编写构建文件

创建 `SCsub` 与 `config.py`（内容见第 2 节，最简版本各几行即可）。

### 4.5 最终目录结构

```
godot/modules/summator/config.py
godot/modules/summator/summator.h
godot/modules/summator/summator.cpp
godot/modules/summator/register_types.h
godot/modules/summator/register_types.cpp
godot/modules/summator/SCsub
```

六文件齐备后，这个目录甚至可以打包成 zip 分享给别人——对方解压到自己引擎源码树的 `modules/` 下重新编译即可使用。这正是模块机制的美妙之处：它天然是自包含、可分发的单元。

### 4.6 编译并在 GDScript 中使用

重新编译引擎：

```bash
scons platform=windows target=editor -j8
```

编译完成后打开新项目，在任意 GDScript 中直接使用 `Summator`，就像它是引擎内置类一样：

```gdscript
extends Node

func _ready():
    var s = Summator.new()
    s.add(10)
    s.add(20)
    s.add(30)
    print(s.get_total())  # 输出 60
    s.reset()
```

没有 `class_name` 声明、没有插件启用步骤、没有 `.gdextension` 文件——类直接存在，因为它本来就编译在引擎二进制里。

### 4.7 继承不同基类的连锁反应

`Summator` 继承的是 `RefCounted`，所以它只是一个可通过脚本使用的普通对象。但只要改换基类，模块类就会自动获得编辑器的各种原生集成，这是模块开发中最「惊喜」的部分：

```
┌────────────────────────────┬──────────────────────────────────────────┐
│ 基类                        │ 自动获得的能力                            │
├────────────────────────────┼──────────────────────────────────────────┤
│ RefCounted / Object        │ 脚本可实例化、可被信号连接                │
│ Node（含 Sprite2D 等派生）  │ 出现在编辑器「添加节点」对话框的继承树中   │
│ Resource                   │ 出现在资源列表；暴露的属性可随场景/资源    │
│                            │ 保存与加载（序列化）                       │
│ EditorPlugin 等编辑器类     │ 可扩展编辑器本身的几乎任何区域            │
└────────────────────────────┴──────────────────────────────────────────┘
```

换言之，模块类与引擎内置类在编辑器中的待遇完全一致——这正是 GDExtension 难以完全企及的深度集成。

---

## 5. 自定义图标、文档与编辑器相关类

### 5.1 为模块类添加编辑器图标

默认情况下，自定义类在编辑器的「添加节点」对话框里显示的是基类的图标。模块可以自带 SVG 图标，让自定义类拥有与内置类一致的视觉体验：

1. 在模块根目录新建 `icons/` 文件夹（这是引擎查找模块图标的默认路径）；
2. 把优化过的 SVG 图标放进去，**文件名必须与类名一致**，如 `Summator.svg`；
3. 重新编译引擎并运行编辑器，图标即会出现在编辑器界面的相应位置。

想换图标目录的话，在 `config.py` 中覆盖默认路径：

```python
def get_icons_path():
    return "path/to/icons"
```

图标制作本身的规范（尺寸、颜色、优化）请参考官方文档的 Editor icons 页面，这里不展开。

### 5.2 编辑器专属代码：TOOLS_ENABLED

模块代码同时会被编译进编辑器构建和导出模板构建，但很多类（比如自定义的编辑器插件、导入器）只在编辑器里有意义。引擎通过 `TOOLS_ENABLED` 宏区分：编辑器构建（`target=editor`）定义了它，导出模板没有。

惯用法是把编辑器专属代码包在 `#ifdef TOOLS_ENABLED` 中：

```cpp
// godot/modules/summator/register_types.cpp
#include "register_types.h"

#include "core/object/class_db.h"
#include "summator.h"

#ifdef TOOLS_ENABLED
#include "editor/summator_editor_plugin.h"
#endif

void initialize_summator_module(ModuleInitializationLevel p_level) {
    if (p_level == MODULE_INITIALIZATION_LEVEL_SCENE) {
        ClassDB::register_class<Summator>();
    }
#ifdef TOOLS_ENABLED
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        // 编辑器专属类在 EDITOR 级别注册
        ClassDB::register_class<SummatorEditorPlugin>();
    }
#endif
}

void uninitialize_summator_module(ModuleInitializationLevel p_level) {
    // 与注册对称地清理
}
```

同时建议在 `SCsub` 中把编辑器专属源文件也做条件编译，避免它们进入导出模板：

```python
Import('env')

env.add_source_files(env.modules_sources, "*.cpp")

# 编辑器专属代码仅在 tools 构建中编译
if env["tools"]:
    env.add_source_files(env.modules_sources, "editor/*.cpp")
```

这样导出模板中既不会有编辑器类的代码体积，也不会有「注册了但不存在」的链接错误。

### 5.3 为模块编写文档

模块可以自带类参考文档，让自定义类出现在引擎内置的文档系统（F1 搜索）中。步骤：

1. 在模块根目录创建 `doc_classes/` 目录；
2. 在 `config.py` 中声明：

```python
def get_doc_path():
    return "doc_classes"

def get_doc_classes():
    return [
        "Summator",
    ]
```

- `get_doc_path()` 告诉构建系统文档目录的位置（不定义则回落到引擎主 `doc/classes/`）；
- `get_doc_classes()` 列出本模块注册的所有类——没列出的类的文档会被生成到主 `doc/classes/` 目录，造成文档散落。

3. 用 doctool 生成 XML 骨架文档：

```bash
bin/<godot_binary> --doctool .
```

之后 `modules/summator/doc_classes/` 下会出现 `Summator.xml`，按照官方类参考文档的格式编辑它，重新编译引擎，文档就内嵌进引擎的帮助系统了。以后每次修改模块 API 后重新运行 doctool 更新 XML 即可。

> **技巧**：可以用 `git status` 检查是否有类的文档被漏列——漏掉的类会以未跟踪文件的形式出现在主 `doc/classes/` 目录下。

### 5.4 为模块编写单元测试

模块还能携带自包含的单元测试，使用引擎内置的 doctest 测试框架：

1. 在模块根目录创建 `tests/` 目录；
2. 新建测试套件文件 `tests/test_summator.h`（文件名必须以 `test_` 开头，构建系统靠此前缀收集）：

```cpp
// godot/modules/summator/tests/test_summator.h
#pragma once

#include "tests/test_macros.h"

#include "modules/summator/summator.h"

namespace TestSummator {

TEST_CASE("[Modules][Summator] Adding numbers") {
    Ref<Summator> s = memnew(Summator);
    CHECK(s->get_total() == 0);

    s->add(10);
    CHECK(s->get_total() == 10);

    s->add(20);
    CHECK(s->get_total() == 30);

    s->add(30);
    CHECK(s->get_total() == 60);

    s->reset();
    CHECK(s->get_total() == 0);
}

} // namespace TestSummator
```

3. 带测试编译引擎并运行：

```bash
scons tests=yes -j8
./bin/<godot_binary> --test --source-file="*test_summator*" --success
```

即可看到测试断言通过的输出。对于绑定外部库的复杂模块，这套机制非常有价值——它让模块质量可以随引擎 CI 一起保障。

---

## 6. 模块与引擎子系统的交互

模块的真正威力在于它能挂接到引擎的各个角落。本节概览几个最常见的挂接点。

### 6.1 挂接总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     模块可挂接的引擎子系统                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   模块 (modules/mymodule/)                                      │
│        │                                                        │
│        ├── ClassDB::register_class<T>()  ──► 类型系统/脚本/序列化 │
│        │                                                        │
│        ├── Engine::get_singleton()->add_singleton()             │
│        │                                  ──► 全局单例（脚本可达）│
│        │                                                        │
│        ├── EditorPlugins::add_by_type<T>() ──► 编辑器插件体系     │
│        │                                                        │
│        ├── ResourceFormatImporter::add_importer()               │
│        │                                  ──► 资源导入管线        │
│        │                                                        │
│        ├── 继承 EditorImportPlugin ──────► 自定义资源导入器       │
│        │                                                        │
│        └── 在 SERVERS 级别注册新 Server ──► servers/ 子系统       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 注册全局单例

如果模块提供一个全局服务（类似 `Engine`、`ProjectSettings` 那样的单例），可以在注册时把它加进 `Engine` 单例表：

```cpp
void initialize_mymodule_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ClassDB::register_class<MyGlobalService>();

    // 创建实例并注册为全局单例，GDScript 中可直接用名字访问
    my_service = memnew(MyGlobalService);
    Engine::get_singleton()->add_singleton(
        Engine::Singleton("MyGlobalService", my_service));
}

void uninitialize_mymodule_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 引擎关闭时对称地释放
    Engine::get_singleton()->remove_singleton("MyGlobalService");
    memdelete(my_service);
}
```

之后 GDScript 中可以直接写 `MyGlobalService.do_something()`，与访问 `Engine`、`Input` 等内置单例的体验一致。

### 6.3 注册编辑器插件

在模块中实现一个继承 `EditorPlugin` 的类后，在 `EDITOR` 初始化级别把它交给编辑器的插件系统：

```cpp
#ifdef TOOLS_ENABLED
#include "editor/plugins/editor_plugin.h"

void initialize_mymodule_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_EDITOR) {
        return;
    }
    ClassDB::register_class<MyEditorPlugin>();
    EditorPlugins::add_by_type<MyEditorPlugin>();
}
#endif
```

与 GDScript 插件的区别在于：模块注册的编辑器插件**默认启用、不可被用户在项目设置里禁用**，且随引擎二进制分发——适合团队级的内置工具链。

### 6.4 自定义资源导入器

让引擎支持一种新的文件格式（比如自定义的 `.mymesh`），经典做法是继承 `EditorImportPlugin`：

```cpp
#ifdef TOOLS_ENABLED
class MyImportPlugin : public EditorImportPlugin {
    GDCLASS(MyImportPlugin, EditorImportPlugin);

public:
    // 实现各虚函数：声明导入器名称、识别的扩展名、
    // 资源类型、导入选项，以及真正的 import() 导入逻辑
    virtual String _get_importer_name() const override;
    virtual String _get_visible_name() const override;
    virtual void _get_recognized_extensions(List<String> *p_extensions) const override;
    virtual String _get_resource_type() const override;
    virtual String _get_save_extension() const override;
    virtual Error _import(const String &p_source_file, const String &p_save_path,
            const HashMap<StringName, Variant> &p_options,
            List<String> *p_platform_variants, List<String> *p_gen_files,
            Variant *r_metadata) override;
    // ... 其余必需虚函数略
};
#endif
```

注册时在 `EDITOR` 级别用 `ClassDB::register_class` 注册该类，并在插件初始化处调用 `add_import_plugin()` 挂入导入管线。此后把 `.mymesh` 文件拖进项目，编辑器就会自动调用你的导入逻辑，将其转换为引擎原生资源。

> **提示**：`EditorImportPlugin` 的虚函数签名随引擎版本演进，实现时请以你所用引擎版本的 `editor/import/editor_import_plugin.h` 头文件为准。

### 6.5 新增 Server 子系统

最深度的集成是仿照 `PhysicsServer`、`RenderingServer` 添加自己的 Server。要点：

- 在 `MODULE_INITIALIZATION_LEVEL_SERVERS` 级别注册类型与单例；
- 参考 3.4 节的预注册钩子，如果你的 Server 需要早于内置类型就位；
- Server 基类通常设计成「抽象接口 + 具体实现」两层，便于不同平台替换实现——这是 `servers/` 目录下所有官方 Server 的统一架构。

这一层面已接近引擎核心开发，建议先通读 `servers/` 下某个简单 Server（如 `camera_server`）的完整实现再动手。

---

## 7. 重编译引擎的完整流程与注意事项

### 7.1 完整流程

```
┌──────────────────────────────────────────────────────────────────┐
│                     自定义模块开发全流程                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 克隆引擎源码      git clone godotengine/godot               │
│         │                                                        │
│  2. 编译原版引擎      scons platform=xxx target=editor -jN      │
│         │            （验证工具链，建立编译缓存）                 │
│         ▼                                                        │
│  3. 创建模块目录      modules/mymodule/（六文件齐备）             │
│         │                                                        │
│  4. 增量编译          scons platform=xxx target=editor -jN      │
│         │            （只编译改动部分，速度快很多）               │
│         ▼                                                        │
│  5. 测试使用          打开项目，在 GDScript 中使用新类            │
│         │                                                        │
│  6. 如需发布游戏 ──►  重新编译所有导出模板！                      │
│                       并在导出预设中指定自定义模板路径            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 常用编译命令速查

```bash
# 编辑器构建（调试信息完整，开发期使用）
scons platform=windows target=editor -j8

# 导出模板：调试版
scons platform=windows target=template_debug -j8

# 导出模板：发布版（性能优化，无调试信息）
scons platform=windows target=template_release -j8

# 禁用某个模块
scons platform=windows target=editor module_summator_enabled=no

# 使用引擎源码树之外的模块
scons platform=windows target=editor custom_modules=../modules

# 带单元测试编译
scons platform=windows target=editor tests=yes -j8
```

`-jN` 指定并行编译的线程数，一般设为 CPU 物理核心数；不传 `-j` 时 SCons 默认只用单线程，编译会慢非常多。

### 7.3 注意事项与常见陷阱

**（1）最大的坑：忘记重编译导出模板。** 官方文档对此有专门警告：如果模块要在运行的项目中使用（而不只是编辑器），你必须重新编译计划使用的**每一个导出模板**，并在每个导出预设中指定自定义模板的路径。否则导出后的游戏一运行就会报错——因为模块没有编译进官方导出模板。这是模块相对 GDExtension 最重的维护负担：每个目标平台（Windows/Linux/macOS/Android/Web…）都要维护一套定制模板。

**（2）函数名与目录名必须严格一致。** `initialize_summator_module` 中的 `summator` 必须等于模块文件夹名。改名目录忘了改函数，或反之，链接阶段会报「未定义的符号」错误。

**（3）register_types 文件必须放顶层。** `register_types.h/.cpp` 必须紧邻 `SCsub` 和 `config.py`，放进子目录会导致模块注册失败。

**（4）自定义编译选项必须克隆 env。** 直接 `env.Append(CCFLAGS=...)` 会把选项泄漏到整个引擎构建，官方明确警告这「can cause errors」。

**（5）多重继承禁区。** 暴露给 Godot 的类不能用多重继承，`GDCLASS` 宏不支持。内部辅助类不受此限。

**（6）善用增量编译。** 首次全量编译后，日常迭代只重编译改动的模块（几十秒级）。只有当改动了引擎核心头文件或升级引擎版本时才会触发大规模重编。

**（7）版本升级要合并。** 模块代码与引擎源码深度耦合，升级引擎版本（如 4.2 → 4.3）时引擎内部 API 可能有破坏性变更，模块需要相应调整。这也是官方建议「优先 GDExtension」的原因之一。

**（8）团队协作的基础设施。** 一旦采用自定义模块，团队每个人（以及 CI）都需要完整的引擎编译环境，且要同步引擎版本与模块版本。建议把「引擎 fork + 模块」纳入统一的版本管理，并把编译好的编辑器与模板作为内部构件分发，减轻非程序岗位的负担。

---

## 📝 本章总结

### 核心要点

1. **模块是引擎的一等扩展机制**：GDScript、GridMap 都是模块，自定义模块与它们机制平级，静态编译进引擎二进制
2. **模块与 GDExtension 的本质区别在于链接方式**：静态 vs 动态、无 API 边界 vs 受 API 约束、定制引擎 vs 官方引擎
3. **六文件构成最小模块**：`config.py`、`SCsub`、业务类、`register_types.h/.cpp`，文件名与目录名有严格约定
4. **注册机制基于初始化级别**：`initialize_XXX_module()` 按 `ModuleInitializationLevel` 分阶段调用，常规类在 `SCENE` 级别注册
5. **基类决定编辑器集成度**：继承 Node 出现在「添加节点」对话框，继承 Resource 可序列化，编辑器类用 `TOOLS_ENABLED` 隔离
6. **模块可挂接引擎全部子系统**：单例、编辑器插件、导入器乃至新的 Server，但代价是必须为每个平台重编译导出模板

### 关键术语

| 术语 | 解释 |
|------|------|
| Module | 引擎 C++ 模块，位于 `modules/` 下、静态链接进引擎的扩展单元 |
| SCsub | SCons 子构建脚本，负责收集模块源文件 |
| config.py | 模块配置文件，含 `can_build`/`configure` 等钩子 |
| `env.add_source_files` | 把源文件加入模块构建列表的 SCons 方法 |
| `env.modules_sources` | 全局模块源文件汇总列表 |
| register_types.h/.cpp | 模块注册入口文件，必须位于模块顶层目录 |
| `initialize_XXX_module` | 模块初始化函数，XXX 必须与目录名一致 |
| ModuleInitializationLevel | 模块初始化级别（CORE/SERVERS/SCENE/EDITOR） |
| `ClassDB::register_class` | 把类注册进 Godot 类数据库 |
| `GDCLASS` | 让 C++ 类接入 Godot 对象系统的必需宏 |
| `_bind_methods` | 向脚本系统绑定方法/属性/信号的静态函数 |
| `TOOLS_ENABLED` | 区分编辑器构建与导出模板的预处理宏 |
| custom_modules | 指定外部模块目录的 SCons 编译选项 |
| 导出模板 (Export Template) | 用于导出游戏的引擎二进制，使用模块时必须重编译 |

---

## 🔗 延伸阅读

- **官方文档（本章主要事实来源）**: [Custom modules in C++](https://docs.godotengine.org/en/latest/engine_details/engine_api/custom_modules_in_cpp.html)
- **官方文档**: [What is GDExtension?](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/what_is_gdextension.html)
- **官方文档**: [GDExtension C++ example](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/gdextension_cpp_example.html)
- **官方文档**: [Binding to external libraries](https://docs.godotengine.org/en/latest/engine_details/engine_api/binding_to_external_libraries.html)
- **源码位置**: `godot/modules/`（官方模块集合，最好的学习素材）
- **源码位置**: `godot/modules/register_module_types.h`、`godot/modules/gdscript/`（一个完整的复杂模块范例）
- **源码位置**: `godot/servers/`（Server 子系统架构参考）

---

*写作时间：2026-08-27*  
*字数：约 13,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-08-27 19:30*
