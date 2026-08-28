# 第 33 篇：GDExtension 架构与入门

> **本卷定位**: 引擎扩展开发卷  
> **前置知识**: 第五篇 对象系统、第六篇 信号系统、C++ 基础语法  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

GDScript 写起来快，C++ 跑起来快。当游戏逻辑中出现性能热点（大规模数值计算、物理采样、音视频编解码），或者你需要把 FMOD、PhysX、自研网络库这样的原生库接进引擎时，GDScript 就不够用了。Godot 4.x 给出的答案是 **GDExtension**：一套让引擎在运行时加载原生动态库（`.dll` / `.so` / `.dylib`）的扩展机制。借助它，你可以用 C++（以及 Rust、Zig、Swift 等社区绑定）编写与引擎内置类几乎平起平坐的自定义类，而**不需要重新编译引擎本体**。本章将从架构原理讲起，带你完成环境搭建、编写第一个 GDExtension 类、理解 `.gdextension` 配置文件，最后通过一个完整的实战示例走通「代码 → 编译 → 编辑器中使用」的全流程。

---

## 🎯 学习目标

- 理解 GDExtension 的定位，以及它与 GDScript、C++ 模块（Module）的取舍
- 掌握 GDExtension 的架构原理：C API 桥接、ABI 兼容、动态库加载机制
- 学会搭建 godot-cpp 开发环境，使用 SCons 构建系统
- 掌握 `GDCLASS` 宏、`_bind_methods`、`register_types.cpp` 入口的写法
- 读懂并编写 `.gdextension` 配置文件
- 独立完成一个自定义节点的开发、编译与编辑器内使用
- 掌握属性导出、方法绑定、信号绑定的基础用法

---

## 1. GDExtension 是什么

### 1.1 定位：运行时加载的原生扩展

GDExtension 是 Godot 特有的技术，它让引擎在**运行时**与原生共享库（native shared library）交互。你可以把它理解为一个「官方认可的动态插件 ABI」：引擎暴露出稳定的 C 接口，你的动态库通过这个接口注册新类、调用引擎 API，整个过程不需要改动或重编引擎源码。

GDExtension 技术由三个核心部分组成：

1. **`gdextension_interface.h`**：一组纯 C 函数声明，是引擎与扩展之间通信的唯一通道；
2. **`extension_api.json`**：一份机器可读的 API 清单，描述引擎向扩展暴露的所有类、方法、枚举与单例；
3. **`*.gdextension` 配置文件**：告诉引擎「为哪个平台加载哪个动态库、入口符号是什么」。

绝大多数开发者不会直接面对裸 C 接口，而是使用现成的语言绑定：官方的 **godot-cpp**（C++），或社区维护的 Rust（gdext）、Zig、Swift、Go 等绑定。本章以 godot-cpp 为准。

### 1.2 与 GDScript、C++ 模块的对比

Godot 官方文档对三者的定位非常明确：游戏的大部分逻辑应该用脚本写（开发效率优先）；只有当 GDExtension 不够用、需要更深度的引擎集成时，才应该写 C++ 模块。

```
扩展方式对比:
┌──────────────┬────────────────────┬────────────────────┬────────────────────┐
│              │     GDScript       │    GDExtension     │    C++ 模块        │
├──────────────┼────────────────────┼────────────────────┼────────────────────┤
│ 运行性能     │ 中（解释执行）     │ 高（原生代码）     │ 高（原生代码）     │
│ 开发迭代速度 │ 极快（保存即生效） │ 较快（重编动态库） │ 慢（重编整个引擎） │
│ 需要引擎源码 │ 否                 │ 否                 │ 是                 │
│ 分发形式     │ 随项目导出         │ 动态库 + 配置文件  │ 定制引擎 + 模板    │
│ 引擎内部访问 │ 公开 API           │ 公开 API（受接口   │ 几乎任意内部代码   │
│              │                    │ 暴露范围限制）     │                    │
│ 适用场景     │ 游戏逻辑、原型     │ 性能热点、绑定     │ 引擎级功能、深度   │
│              │                    │ 第三方原生库       │ 定制、平台移植     │
└──────────────┴────────────────────┴────────────────────┴────────────────────┘
```

几个关键结论：

- **迭代成本**：改一行 GDExtension 代码只需重编几兆字节的动态库；改一行模块代码需要重编整个引擎（分钟级起步）。
- **导出成本**：模块会被静态链接进引擎，因此必须**为每个导出平台重新编译导出模板**；GDExtension 只需为各平台提供对应的动态库，官方导出模板原样可用。
- **能力边界**：GDExtension 只能访问通过 GDExtension 接口暴露的 API（覆盖面已接近模块能用的公共 API）；模块可以调用引擎内部任意代码，包括未公开的实现细节。

经验法则：**默认用 GDScript；遇到性能或原生库需求用 GDExtension；只有要动引擎本身时才写模块。**

### 1.3 架构原理：C API 桥接

GDExtension 的全部魔法建立在一个朴素的设计上：**引擎与动态库之间只通过纯 C 接口通信**，不跨边界传递任何 C++ 对象。

为什么必须是 C？因为 C++ 没有稳定的 ABI——不同编译器（甚至同一编译器的不同版本）对类布局、名称修饰（name mangling）、`std::string` 等标准库类型的实现都可能不同。如果引擎用 MSVC 编译而扩展用 MinGW 编译，直接传递 C++ 对象几乎必然崩溃。C 语言的调用约定在各平台上是稳定统一的，因此成为天然的「外交语言」。

```
GDExtension 桥接架构:
┌──────────────────────────────────────────────────────────────────────┐
│                        Godot 引擎（已编译的二进制）                  │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────────────┐  │
│  │  ClassDB       │  │  SceneTree     │  │  Servers(Rendering/   │  │
│  │  类数据库      │  │  场景树        │  │  Physics/Audio...)    │  │
│  └───────┬────────┘  └───────┬────────┘  └───────────┬───────────┘  │
│          │                   │                       │              │
│  ┌───────▼───────────────────▼───────────────────────▼───────────┐  │
│  │        GDExtension 接口层（gdextension_interface.h）         │  │
│  │        纯 C 函数表 + 不透明指针（opaque pointer）            │  │
│  └──────────────────────────────▲───────────────────────────────┘  │
└─────────────────────────────────│──────────────────────────────────┘
            ║ 唯一的通信通道：C 函数调用 + 不透明指针
┌─────────────────────────────────│──────────────────────────────────┐
│  ┌──────────────────────────────┴───────────────────────────────┐  │
│  │        语言绑定层（godot-cpp / gdext / ...）                 │  │
│  │   把 C 接口包装成本语言的类、方法、Variant 类型              │  │
│  └──────────────────────────────▲───────────────────────────────┘  │
│  ┌──────────────────────────────┴───────────────────────────────┐  │
│  │        你的扩展代码（自定义 Node / Resource / ...）          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                  GDExtension 动态库（.dll / .so / .dylib）          │
└──────────────────────────────────────────────────────────────────────┘
```

这张图的要点：

- **不透明指针**：引擎把一个 `Object` 传给扩展时，给的不是 `Object*`，而是一个不透明的句柄。扩展只能把这个句柄连同「想调用的方法」一起交回给引擎，由引擎在自己一侧完成真正的调用。
- **函数表而非符号链接**：加载时，引擎把 `get_proc_address` 函数指针交给扩展，扩展通过它逐一查询所需的接口函数地址。这意味着扩展二进制**不依赖引擎的导出符号**，两者解耦。
- **Variant 是通用货币**：脚本与原生代码之间的参数、返回值都通过 `Variant`（及其对应的 C 结构）传递，与 GDScript 的世界完全打通。

### 1.4 ABI 兼容与版本策略

`extension_api.json` 描述了某个 Godot 版本暴露的完整 API 表面。godot-cpp 仓库内置了一份当前发布版本的 API 元数据；如果你的目标引擎版本更新，可以用引擎自己导出生成：

```bash
# 在 Godot 可执行文件所在目录生成 extension_api.json
godot --dump-extension-api
```

官方的长期目标是：**针对较早小版本编译的 GDExtension 可以在较晚的小版本上运行，反之则不行**。例如针对 Godot 4.1 编译的扩展应能在 4.2 中运行，而针对 4.2 编译的扩展不保证能在 4.1 中加载。需要注意的是，GDExtension 目前仍标记为 **experimental**，官方保留为修复重大问题而打破兼容的权利——事实上 4.0 与 4.1 之间就发生过一次 ABI 变更。因此实践中应牢记两条规则：

1. **godot-cpp 的分支必须与目标引擎版本匹配**（目标 4.2 就用 `4.2` 分支）；
2. 在 `.gdextension` 配置中用 `compatibility_minimum` 声明最低兼容版本（详见第 4 节）。

### 1.5 动态库加载机制

引擎加载 GDExtension 的流程如下：

```
GDExtension 加载流程:
┌─────────────────────────────────────────────────────────────────────┐
│  1. 项目扫描：引擎在项目文件系统中发现 *.gdextension 文件           │
│                          │                                          │
│                          ▼                                          │
│  2. 解析配置：读取 [configuration] 的 entry_symbol、                │
│     compatibility_minimum，检查引擎版本是否满足要求                 │
│                          │                                          │
│                          ▼                                          │
│  3. 选择动态库：根据当前平台 / 构建类型 / CPU 架构，                │
│     在 [libraries] 中匹配键（如 windows.debug.x86_64），            │
│     用 OS 的动态加载器（LoadLibrary / dlopen）加载                  │
│                          │                                          │
│                          ▼                                          │
│  4. 定位入口：在动态库中查找 entry_symbol 指定的导出函数            │
│                          │                                          │
│                          ▼                                          │
│  5. 初始化：调用入口函数，传入 get_proc_address 与 library 句柄；   │
│     扩展按初始化等级（core/servers/scene/editor）回调注册类         │
│                          │                                          │
│                          ▼                                          │
│  6. 就绪：扩展注册的类进入 ClassDB，脚本与编辑器立即可用            │
└─────────────────────────────────────────────────────────────────────┘
```

编辑器还提供了一项开发期福利：当 `.gdextension` 中设置 `reloadable = true` 且扩展以 debug 构建时，**每次重新编译动态库后编辑器会自动重载扩展**，无需重启编辑器。

---

## 2. 开发环境搭建

### 2.1 准备工具

开始前需要四样东西：

- **Godot 4 可执行文件**（编辑器，用于测试扩展）；
- **C++ 编译器**（Windows 用 MSVC，Linux 用 GCC/Clang，macOS 用 Xcode 工具链）；
- **SCons 构建工具**（Python 编写，与编译 Godot 本体用的是同一套）；
- **godot-cpp 仓库**（C++ 绑定）。

安装 SCons：

```bash
pip install scons
```

### 2.2 获取 godot-cpp

推荐的目录布局如下（后续所有示例都以此为准）：

```
gdextension_demo/
│
├── demo/          # Godot 演示项目，用于测试扩展
│
├── godot-cpp/     # C++ 绑定（官方仓库）
│
└── src/           # 我们的扩展源码
```

用 Git 克隆 godot-cpp，注意分支必须匹配目标引擎版本：

```bash
mkdir gdextension_demo
cd gdextension_demo

# 以 4.x 为例；实际使用时替换为目标版本，如 4.2、4.3
git clone -b 4.x https://github.com/godotengine/godot-cpp
```

如果项目本身用 Git 管理，官方建议以 submodule 方式引入：

```bash
git submodule add -b 4.x https://github.com/godotengine/godot-cpp
cd godot-cpp
git submodule update --init
```

> **注意**：`master` 分支是开发分支，跟随引擎 `master` 变动，生产项目应使用与目标版本对应的分支。

### 2.3 编译 C++ 绑定

godot-cpp 本身需要先用 SCons 编译成静态库，同时它会根据 `extension_api.json` 生成大量绑定代码：

```bash
cd godot-cpp
scons platform=windows    # 替换为 windows / linux / macos
cd ..
```

如需为新版本引擎生成绑定，先执行 `godot --dump-extension-api`，把生成的 `extension_api.json` 复制到项目目录，然后加上 `custom_api_file` 参数：

```bash
cd godot-cpp
scons platform=windows custom_api_file=../extension_api.json
cd ..
```

这一步耗时较长（要生成并编译上千个类的绑定）。完成后，静态库位于 `godot-cpp/bin/`。

### 2.4 SCons 关键参数

godot-cpp 及你的扩展项目共用同一套构建参数，最常用的有：

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `platform` | `windows` `linux` `macos` `android` `ios` `web` | 目标平台 |
| `target` | `editor` `template_debug` `template_release` | 构建类型：编辑器 / 调试导出模板 / 发布导出模板 |
| `arch` | `x86_64` `x86_32` `arm64` `rv64` `universal` 等 | CPU 架构（多数情况自动检测） |
| `-jN` | 数字 | 并行编译线程数（默认自动检测 CPU 线程数） |
| `custom_api_file` | 文件路径 | 自定义 `extension_api.json` |
| `debug_symbols` | `yes` / `no` | 是否生成调试符号 |

几点说明：

- **target 的含义**：`editor` 对应在编辑器中运行的构建；`template_debug` 与 `template_release` 对应导出项目时使用的调试 / 发布构建。godot-cpp 默认 target 为 `template_debug`。
- **发布项目时务必同时构建 release 版本**：`scons platform=<platform> target=template_release`，并在 `.gdextension` 的 `[libraries]` 中登记（见第 4 节）。
- 在部分平台 / 版本上可能需要显式加 `arch=x86_64` 或（旧版写法）`bits=64`。

---

## 3. 第一个 GDExtension 类

本节实现官方教程中的经典示例：一个继承 `Sprite2D`、沿正弦/余弦轨迹摆动的 `GDExample` 节点。通过它讲清四个核心概念：`GDCLASS` 宏、`_bind_methods`、注册入口、初始化等级。

### 3.1 头文件：继承引擎类与 GDCLASS 宏

在 `src/` 下创建 `gdexample.h`：

```cpp
// src/gdexample.h
#ifndef GDEXAMPLE_H
#define GDEXAMPLE_H

#include <godot_cpp/classes/sprite2d.hpp>

namespace godot {

// 继承 Sprite2D，让它成为一个可在编辑器中创建的 2D 节点
class GDExample : public Sprite2D {
	// GDCLASS 宏：为类注入 Godot 对象系统所需的内部设施
	// 第一个参数是本类名，第二个参数是父类名
	GDCLASS(GDExample, Sprite2D)

private:
	double time_passed; // 累计经过的时间

protected:
	// 静态方法：Godot 调用它来了解本类暴露了哪些方法/属性/信号
	static void _bind_methods();

public:
	GDExample();
	~GDExample();

	// 与 GDScript 中的 _process 完全等价
	void _process(double delta) override;
};

}

#endif
```

几个要点：

- 头文件包含 `godot_cpp/classes/sprite2d.hpp`，即引擎 `Sprite2D` 类的 C++ 绑定。godot-cpp 为每个引擎类生成一个对应的绑定头文件。
- 所有 godot-cpp 类型都位于 `namespace godot` 中，必须置身该命名空间（或显式限定）。
- **`GDCLASS(m_class, m_inherits)` 宏**是接入 Godot 对象系统的钥匙。它展开后会注入类型信息、父类指针、`get_class()` 等基础设施。凡是要暴露给引擎的类都必须写这个宏——也因此它不支持多重继承（暴露给 Godot 的类请坚持单继承）。
- `protected` 区的 `static void _bind_methods()` 是固定的签名约定，下一小节展开。
- `_process(double delta)` 用 `override` 覆写虚方法，行为与 GDScript 中定义 `_process` 完全一致。

### 3.2 实现文件与 _bind_methods

创建 `src/gdexample.cpp`：

```cpp
// src/gdexample.cpp
#include "gdexample.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void GDExample::_bind_methods() {
	// 暂时为空；后续在此绑定方法、属性、信号
}

GDExample::GDExample() {
	// 在此初始化成员变量
	time_passed = 0.0;
}

GDExample::~GDExample() {
	// 在此做清理工作
}

void GDExample::_process(double delta) {
	time_passed += delta;

	// 用正弦/余弦函数计算新位置，让图标沿李萨如轨迹摆动
	Vector2 new_position = Vector2(
		10.0 + (10.0 * sin(time_passed * 2.0)),
		10.0 + (10.0 * cos(time_passed * 1.5))
	);

	set_position(new_position);
}
```

`_bind_methods` 是 Godot 对象系统的「登记窗口」：引擎在注册类时调用它，类把希望暴露给脚本、编辑器、序列化系统的方法、属性、信号逐条登记进去。**没有在这里登记的东西，GDScript 看不见，检查器看不见，信号也连不上**。具体的绑定语法（`ClassDB::bind_method`、`ADD_PROPERTY`、`ADD_SIGNAL`）将在第 6 节系统介绍。

### 3.3 注册入口：register_types.cpp

一个 GDExtension 库可以包含任意多个类，每个类都有自己的头文件和实现文件。但动态库必须有一个**统一的入口**，告诉 Godot「我这个库里有哪些类」。这就是 `register_types.cpp` / `register_types.h` 的职责。

```cpp
// src/register_types.h
#ifndef GDEXAMPLE_REGISTER_TYPES_H
#define GDEXAMPLE_REGISTER_TYPES_H

#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void initialize_example_module(ModuleInitializationLevel p_level);
void uninitialize_example_module(ModuleInitializationLevel p_level);

#endif // GDEXAMPLE_REGISTER_TYPES_H
```

```cpp
// src/register_types.cpp
#include "register_types.h"

#include "gdexample.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

// 初始化回调：引擎加载扩展时按等级调用
void initialize_example_module(ModuleInitializationLevel p_level) {
	// 只在 Scene 等级注册我们的类
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}

	// GDREGISTER_RUNTIME_CLASS：注册类，仅在游戏运行时可用
	// （与 GDScript 默认行为一致；另有 GDREGISTER_CLASS 供编辑器工具类使用）
	GDREGISTER_RUNTIME_CLASS(GDExample);
}

// 反初始化回调：引擎卸载扩展时按等级调用
void uninitialize_example_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
}

extern "C" {
	// 库入口函数：名字必须与 .gdextension 配置中的 entry_symbol 一致
	GDExtensionBool GDE_EXPORT example_library_init(
			GDExtensionInterfaceGetProcAddress p_get_proc_address,
			const GDExtensionClassLibraryPtr p_library,
			GDExtensionInitialization *r_initialization) {
		// 创建初始化对象，绑定引擎传来的三个关键参数
		godot::GDExtensionBinding::InitObject init_obj(
				p_get_proc_address, p_library, r_initialization);

		// 登记初始化 / 反初始化回调
		init_obj.register_initializer(initialize_example_module);
		init_obj.register_terminator(uninitialize_example_module);

		// 设置本库要求的最低初始化等级
		init_obj.set_minimum_library_initialization_level(
				MODULE_INITIALIZATION_LEVEL_SCENE);

		return init_obj.init();
	}
}
```

这段代码的三个角色：

- `initialize_example_module` / `uninitialize_example_module`：分别在引擎加载、卸载扩展时被回调。每个类通过 `GDREGISTER_RUNTIME_CLASS`（或 `GDREGISTER_CLASS`）宏注册进 `ClassDB`。
- `example_library_init`：**真正的动态库入口**，用 `extern "C"` 阻止 C++ 名称修饰，保证引擎能按符号名找到它。它接收引擎递过来的 `get_proc_address`（查询接口函数的钥匙）和 `library` 句柄，包装进 `GDExtensionBinding::InitObject`，最后调用 `init()` 完成握手。
- `GDE_EXPORT` 是 godot-cpp 提供的跨平台导出宏（对应 `__declspec(dllexport)` / `__attribute__((visibility("default")))`）。

### 3.4 初始化等级（Initialization Level）

引擎启动不是一步完成的，而是分层初始化：核心类型 → 服务器 → 场景系统 → 编辑器。GDExtension 沿用同一模型，注册回调会被**每个等级各调用一次**，由扩展自己判断「我的类属于哪一层」：

| 等级常量 | 含义 | 典型用途 |
|----------|------|----------|
| `MODULE_INITIALIZATION_LEVEL_CORE` | 核心层 | 基础数据类型、核心工具类 |
| `MODULE_INITIALIZATION_LEVEL_SERVERS` | 服务器层 | 渲染/物理/音频等服务器相关扩展 |
| `MODULE_INITIALIZATION_LEVEL_SCENE` | 场景层 | **绝大多数节点类、资源类**（默认选择） |
| `MODULE_INITIALIZATION_LEVEL_EDITOR` | 编辑器层 | 仅在编辑器中存在的工具类 |

典型写法就是上面看到的模式：

```cpp
void initialize_example_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return; // 其他等级直接忽略
	}
	// 在本等级注册类……
}
```

`set_minimum_library_initialization_level()` 告诉引擎：低于这个等级时**不要加载本库**。节点类选择 `SCENE` 即可；只有当你注册的类会被编辑器本身使用（如自定义 `EditorPlugin` 的底层支撑类）时才需要 `EDITOR`。

### 3.5 编写 SConstruct

在扩展根目录（与 `godot-cpp/`、`src/`、`demo/` 同级）创建 `SConstruct`，把项目的构建挂到 godot-cpp 的构建系统上：

```python
# SConstruct
import os
import sys

# 引入 godot-cpp 的构建环境（platform/target/arch 等参数全部继承）
env = SConscript("godot-cpp/SConstruct")

# 添加头文件搜索路径与源文件
env.Append(CPPPATH=["src/"])
sources = Glob("src/*.cpp")

# 输出路径：demo/bin/libgdexample.<platform>.<target>.<arch>.<后缀>
# env["suffix"] 由 godot-cpp 生成，形如 ".windows.template_debug.x86_64"
library = env.SharedLibrary(
    "demo/bin/libgdexample{}{}".format(env["suffix"], env["SHLIBSUFFIX"]),
    source=sources,
)

Default(library)
```

然后编译：

```bash
scons platform=windows
```

产物会出现在 `demo/bin/` 下，例如 `libgdexample.windows.template_debug.x86_64.dll`。

---

## 4. .gdextension 配置文件详解

编译出动态库后，还需要一个配置文件告诉引擎如何加载它。在 `demo/bin/` 中创建 `gdexample.gdextension`：

```ini
; demo/bin/gdexample.gdextension

[configuration]

; 动态库的入口符号，必须与 register_types.cpp 中的 extern "C" 函数同名
entry_symbol = "example_library_init"

; 最低兼容的 Godot 版本：低于此版本的引擎将拒绝加载本扩展
compatibility_minimum = "4.1"

; 允许编辑器在重新编译后自动热重载本扩展（仅 debug 构建有效）
reloadable = true

[libraries]

; 键的格式：<platform>.<feature>[.<arch>]
; 值是动态库在项目内的路径
macos.debug = "res://bin/libgdexample.macos.template_debug.framework"
macos.release = "res://bin/libgdexample.macos.template_release.framework"
windows.debug.x86_64 = "res://bin/libgdexample.windows.template_debug.x86_64.dll"
windows.release.x86_64 = "res://bin/libgdexample.windows.template_release.x86_64.dll"
linux.debug.x86_64 = "res://bin/libgdexample.linux.template_debug.x86_64.so"
linux.release.x86_64 = "res://bin/libgdexample.linux.template_release.x86_64.so"

[dependencies]

; 额外的依赖动态库，随项目一起导出（本例无第三方依赖，留空）
```

逐节说明：

### 4.1 [configuration]

- **`entry_symbol`**：必填。引擎加载动态库后查找的入口函数名，必须与 `register_types.cpp` 里 `extern "C"` 函数的名字**逐字一致**。
- **`compatibility_minimum`**：声明扩展兼容的最低引擎版本。引擎版本低于它时直接拒绝加载，避免出现难以排查的 ABI 崩溃。结合第 1.4 节的版本策略，把它设为你编译时使用的 godot-cpp 分支对应版本。
- **`reloadable`**：设为 `true` 后，编辑器检测到动态库更新会自动卸载旧库、加载新库，开发期不用反复重启编辑器。注意只对 debug（`template_debug` / `editor`）构建有效。

### 4.2 [libraries]

这是配置文件的核心。键的格式为：

```
<platform>.<feature>[.<arch>]
```

- `platform`：`windows` / `linux` / `macos` / `android` / `ios` / `web` 等；
- `feature`：`debug` 或 `release`，分别对应 `template_debug` / `editor` 构建和 `template_release` 构建；
- `arch`：可选，`x86_64` / `x86_32` / `arm64` / `rv64` 等。

引擎按「当前平台 + 构建类型 + 架构」选出最精确的匹配项加载。这个设计还有一个重要的导出语义：**导出项目时，只有匹配目标平台的那个动态库会被打入导出包**，不会把 Windows 的 `.dll` 塞进 Linux 包里。

macOS 上通常把动态库打包成 `.framework`；iOS 则需要将模拟器与真机的静态库组装成 `.xcframework`（用 `xcodebuild -create-xcframework`），这些属于平台进阶话题，本章不展开。

### 4.3 [dependencies]

如果你的扩展依赖第三方动态库（例如 FMOD 的 `.dll`），在这里登记，引擎导出时会一并带上：

```ini
[dependencies]
windows.debug.x86_64 = {
    "res://bin/third_party/fmod.dll": ""
}
windows.release.x86_64 = {
    "res://bin/third_party/fmod.dll": ""
}
```

键同样是 `<platform>.<feature>[.<arch]]` 格式，值是一个字典：键为依赖库路径，值为可选的存放子目录（空字符串表示与扩展库同目录）。

### 4.4 最终目录结构

```
gdextension_demo/
│
├── demo/                     # Godot 演示项目
│   │
│   ├── main.tscn
│   │
│   └── bin/
│       ├── gdexample.gdextension
│       └── libgdexample.windows.template_debug.x86_64.dll
│
├── godot-cpp/                # C++ 绑定
│
├── src/                      # 扩展源码
│   ├── gdexample.h
│   ├── gdexample.cpp
│   ├── register_types.h
│   └── register_types.cpp
│
└── SConstruct
```

---

## 5. 完整实战：Summator 与运动节点

本节做两个互补的完整示例：**Summator**（继承 `RefCounted` 的纯数据类，演示「无节点」类的完整链路）和 **MotionSprite**（继承 `Sprite2D` 的运动节点，带导出属性与信号，演示编辑器集成）。两者放在同一个扩展库里。

### 5.1 Summator：一个 RefCounted 数据类

`RefCounted` 是引用计数的对象基类，适合不进入场景树的工具类、数据类。

```cpp
// src/summator.h
#ifndef SUMMATOR_H
#define SUMMATOR_H

#include <godot_cpp/classes/ref_counted.hpp>

namespace godot {

class Summator : public RefCounted {
	GDCLASS(Summator, RefCounted)

	int count; // 累计值

protected:
	static void _bind_methods();

public:
	void add(int p_value);   // 累加一个整数
	void reset();            // 清零
	int get_total() const;   // 读取当前累计值

	Summator();
};

}

#endif
```

```cpp
// src/summator.cpp
#include "summator.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

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
	// D_METHOD 宏：声明方法名及其参数名，供引擎生成文档与调用元数据
	ClassDB::bind_method(D_METHOD("add", "value"), &Summator::add);
	ClassDB::bind_method(D_METHOD("reset"), &Summator::reset);
	ClassDB::bind_method(D_METHOD("get_total"), &Summator::get_total);
}

Summator::Summator() {
	count = 0;
}
```

`ClassDB::bind_method(D_METHOD(...), &类::方法)` 是方法绑定的基本公式。`D_METHOD` 的第一个参数是暴露给引擎的方法名，其后是参数名列表（仅作元数据，真正的类型检查由 C++ 签名完成）。

### 5.2 MotionSprite：带属性和信号的运动节点

这个节点沿可配置的轨迹运动，支持在检查器中调整振幅与速度，并每秒发射一次位置信号。

```cpp
// src/motion_sprite.h
#ifndef MOTION_SPRITE_H
#define MOTION_SPRITE_H

#include <godot_cpp/classes/sprite2d.hpp>

namespace godot {

class MotionSprite : public Sprite2D {
	GDCLASS(MotionSprite, Sprite2D)

private:
	double time_passed; // 累计时间
	double time_emit;   // 信号发射计时
	double amplitude;   // 运动振幅（导出属性）
	double speed;       // 运动速度（导出属性）

protected:
	static void _bind_methods();

public:
	MotionSprite();
	~MotionSprite();

	void _process(double delta) override;

	void set_amplitude(const double p_amplitude);
	double get_amplitude() const;

	void set_speed(const double p_speed);
	double get_speed() const;
};

}

#endif
```

```cpp
// src/motion_sprite.cpp
#include "motion_sprite.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void MotionSprite::_bind_methods() {
	// —— 绑定属性的 getter / setter ——
	ClassDB::bind_method(D_METHOD("get_amplitude"), &MotionSprite::get_amplitude);
	ClassDB::bind_method(D_METHOD("set_amplitude", "p_amplitude"), &MotionSprite::set_amplitude);
	ClassDB::bind_method(D_METHOD("get_speed"), &MotionSprite::get_speed);
	ClassDB::bind_method(D_METHOD("set_speed", "p_speed"), &MotionSprite::set_speed);

	// —— 导出属性：ADD_PROPERTY(属性信息, setter 名, getter 名) ——
	ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "amplitude"), "set_amplitude", "get_amplitude");
	// PROPERTY_HINT_RANGE 让检查器显示为滑条，参数为 "最小值,最大值,步长"
	ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "speed", PROPERTY_HINT_RANGE, "0,20,0.01"), "set_speed", "get_speed");

	// —— 声明信号：每秒发出一次，携带本节点与新位置 ——
	ADD_SIGNAL(MethodInfo("position_changed",
			PropertyInfo(Variant::OBJECT, "node"),
			PropertyInfo(Variant::VECTOR2, "new_pos")));
}

MotionSprite::MotionSprite() {
	// 初始化成员变量
	time_passed = 0.0;
	time_emit = 0.0;
	amplitude = 10.0;
	speed = 1.0;
}

MotionSprite::~MotionSprite() {
	// 清理工作
}

void MotionSprite::_process(double delta) {
	time_passed += speed * delta;

	// 李萨如轨迹：横纵坐标频率不同
	Vector2 new_position = Vector2(
			amplitude + (amplitude * sin(time_passed * 2.0)),
			amplitude + (amplitude * cos(time_passed * 1.5)));

	set_position(new_position);

	// 每过一秒发射一次信号
	time_emit += delta;
	if (time_emit > 1.0) {
		emit_signal("position_changed", this, new_position);
		time_emit = 0.0;
	}
}

void MotionSprite::set_amplitude(const double p_amplitude) {
	amplitude = p_amplitude;
}

double MotionSprite::get_amplitude() const {
	return amplitude;
}

void MotionSprite::set_speed(const double p_speed) {
	speed = p_speed;
}

double MotionSprite::get_speed() const {
	return speed;
}
```

### 5.3 更新注册入口

把两个新类登记进 `register_types.cpp`（头文件同步声明，此处省略）：

```cpp
// src/register_types.cpp
#include "register_types.h"

#include "summator.h"
#include "motion_sprite.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_example_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}

	// 注册本扩展包含的所有类
	GDREGISTER_RUNTIME_CLASS(Summator);
	GDREGISTER_RUNTIME_CLASS(MotionSprite);
}

void uninitialize_example_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
}

extern "C" {
GDExtensionBool GDE_EXPORT example_library_init(
		GDExtensionInterfaceGetProcAddress p_get_proc_address,
		const GDExtensionClassLibraryPtr p_library,
		GDExtensionInitialization *r_initialization) {
	godot::GDExtensionBinding::InitObject init_obj(
			p_get_proc_address, p_library, r_initialization);

	init_obj.register_initializer(initialize_example_module);
	init_obj.register_terminator(uninitialize_example_module);
	init_obj.set_minimum_library_initialization_level(
			MODULE_INITIALIZATION_LEVEL_SCENE);

	return init_obj.init();
}
}
```

### 5.4 编译

```bash
# 在扩展根目录（SConstruct 所在目录）执行
scons platform=windows            # debug 构建，编辑器内开发用
scons platform=windows target=template_release   # release 构建，导出项目用
```

由于 `SConstruct` 中用了 `Glob("src/*.cpp")`，新增的源文件会被自动纳入编译。产物输出到 `demo/bin/`，文件名与第 4 节 `.gdextension` 中登记的路径对应即可。

> 提示：`reloadable = true` 生效时，重新编译后切回编辑器即自动热重载；若改了类结构（增删类/属性）发现异常，重启一次编辑器是最可靠的排障手段。

### 5.5 在编辑器中使用

**使用 Summator**：它的用法与 GDScript 类完全一致——`new()` 创建、调用方法：

```gdscript
# demo/main.gd（挂在场景根节点上）
extends Node

func _ready():
	var s = Summator.new()
	s.add(10)
	s.add(20)
	s.add(30)
	print(s.get_total())  # 输出 60
	s.reset()
```

**使用 MotionSprite**：因为继承了 `Sprite2D`，它会出现在「添加节点」对话框的继承树里（就在 Sprite2D 分支下）：

1. 在场景中点击「+」添加节点，搜索 `MotionSprite`，创建实例；
2. 为其 `texture` 属性指定一张图片（例如 `icon.svg`），并把 `centered` 关掉便于观察轨迹；
3. 在检查器中可以看到 `amplitude` 与 `speed` 两个属性，`speed` 是 0~20 的滑条；
4. 运行项目，图标开始沿轨迹摆动。

**连接信号**：选中 `MotionSprite` 节点，在「节点」面板中找到 `position_changed` 信号，连接到主节点脚本：

```gdscript
# demo/main.gd
extends Node

func _on_motion_sprite_position_changed(node, new_pos):
	print("节点 ", node.get_class(), " 当前位置：", new_pos)
```

运行后，控制台每秒打印一次位置。至此，从 C++ 代码到编辑器集成再到脚本交互的完整链路已经走通。

---

## 6. 属性、方法与信号绑定速查

### 6.1 方法绑定

```cpp
// 基本公式：bind_method(D_METHOD(方法名, 参数名...), &类::方法指针)
ClassDB::bind_method(D_METHOD("add", "value"), &Summator::add);

// 带默认值的写法（从最后一个参数开始，依次向前）
ClassDB::bind_method(D_METHOD("move", "offset", "snap"), &MyNode::move,
		DEFVAL(Vector2()), DEFVAL(false));
```

绑定后的方法可以被 GDScript 调用、可以出现在文档中、也可以作为信号回调。反过来，**任何想被信号回调的 C++ 方法，都必须先在这里绑定**。

### 6.2 属性导出

GDScript 用 `@export` 导出属性；GDExtension 中的等价物是「绑定 getter/setter + `ADD_PROPERTY`」：

```cpp
// 第一步：绑定 getter 与 setter 方法
ClassDB::bind_method(D_METHOD("set_speed", "p_speed"), &MotionSprite::set_speed);
ClassDB::bind_method(D_METHOD("get_speed"), &MotionSprite::get_speed);

// 第二步：注册属性（属性类型 + 名称 [+ 提示 + 提示字符串]）
ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "speed",
		PROPERTY_HINT_RANGE, "0,20,0.01"),   // 检查器显示为 0~20、步长 0.01 的滑条
		"set_speed", "get_speed");
```

`PropertyInfo` 的构造参数依次是：Variant 类型、属性名、（可选）`PropertyHint` 提示、（可选）提示字符串。常用提示包括：

| PropertyHint | 效果 | 提示字符串示例 |
|--------------|------|----------------|
| `PROPERTY_HINT_NONE` | 无提示（默认输入框） | 不需要 |
| `PROPERTY_HINT_RANGE` | 数值滑条 | `"0,20,0.01"`（最小，最大，步长） |
| `PROPERTY_HINT_ENUM` | 枚举下拉框 | `"慢速,中速,快速"` |
| `PROPERTY_HINT_FILE` | 文件选择框 | `"*.txt,*.json"` |
| `PROPERTY_HINT_MULTILINE_TEXT` | 多行文本框 | 不需要 |

导出属性会自动获得序列化能力：在检查器里修改的值会随场景/资源一起保存，与 GDScript 的 `@export` 行为一致。

更高级的用法是覆写 `_get_property_list` / `_get` / `_set` 动态生成属性，适合属性集合不固定的场景，本章不展开。

### 6.3 信号：声明与发射

声明信号在 `_bind_methods` 中完成：

```cpp
ADD_SIGNAL(MethodInfo("position_changed",
		PropertyInfo(Variant::OBJECT, "node"),      // 第一个参数：节点对象
		PropertyInfo(Variant::VECTOR2, "new_pos"))); // 第二个参数：新位置
```

`ADD_SIGNAL` 接受一个 `MethodInfo`：首个参数是信号名，其余 `PropertyInfo` 描述每个参数的类型与名字（名字会显示在编辑器的信号连接对话框和生成的文档里）。

发射信号用 `emit_signal`，参数值按声明顺序跟在信号名后面：

```cpp
emit_signal("position_changed", this, new_position);
```

### 6.4 信号：在 C++ 中连接

让扩展对象响应其他对象的信号，使用 `connect` + `Callable`：

```cpp
// 把 other_node 的 "the_signal" 连接到本对象的 "my_method"
some_other_node->connect("the_signal", Callable(this, "my_method"));
```

`Callable` 把「对象实例 + 方法名」打包成一个可调用的引用。再次强调：`my_method` 必须已经在 `_bind_methods` 中通过 `bind_method` 登记过，否则引擎不知道它的存在，连接会失败。

在 GDScript 一侧连接扩展类的信号则没有任何特殊之处，与内置节点完全相同：

```gdscript
motion_sprite.position_changed.connect(_on_motion_sprite_position_changed)
```

---

## 📝 本章总结

### 核心要点

1. **GDExtension 是运行时加载的原生扩展机制**，由 `gdextension_interface.h`（C 接口）、`extension_api.json`（API 清单）、`*.gdextension`（加载配置）三部分组成，介于 GDScript 与 C++ 模块之间，兼顾性能与迭代效率。
2. **C API 桥接是架构基石**：引擎与动态库之间只传递 C 函数指针与不透明句柄，规避了 C++ ABI 不稳定的问题，任何能提供 C FFI 的语言都能写绑定。
3. **版本兼容有方向性**：针对旧小版本编译的扩展可在新小版本运行，反之不行；godot-cpp 分支必须匹配目标引擎版本，并用 `compatibility_minimum` 兜底。
4. **开发四件套固定不变**：继承引擎类 → `GDCLASS` 宏 → `_bind_methods` 登记 → `register_types.cpp` 入口按初始化等级注册；构建用 SCons，产物按 `platform/target/arch` 命名。
5. **`.gdextension` 文件掌管加载与导出**：`[libraries]` 的键格式 `<platform>.<feature>[.<arch]]` 决定各平台加载哪个库，同时保证导出时只打包匹配平台的二进制。
6. **绑定三件套**：方法用 `ClassDB::bind_method`，属性用「getter/setter + `ADD_PROPERTY`」，信号用「`ADD_SIGNAL` 声明 + `emit_signal` 发射 + `connect`/`Callable` 连接」。

### 关键术语

| 术语 | 解释 |
|------|------|
| GDExtension | Godot 的运行时原生扩展机制，加载动态库扩展引擎功能 |
| godot-cpp | 官方 C++ 语言绑定，基于 GDExtension C API 封装 |
| gdextension_interface.h | 引擎与扩展通信的纯 C 接口头文件 |
| extension_api.json | 引擎 API 的机器可读清单，由绑定层用于代码生成 |
| ABI | 应用二进制接口，决定不同编译产物能否互相链接调用 |
| GDCLASS | 把 C++ 类接入 Godot 对象系统的宏（单继承） |
| _bind_methods | 静态注册函数，登记类暴露的方法/属性/信号 |
| ClassDB | Godot 的类数据库，所有可脚本化的类在此注册 |
| D_METHOD | 声明方法名与参数名的宏，配合 bind_method 使用 |
| ADD_PROPERTY | 注册导出属性的宏（需先绑定 getter/setter） |
| ADD_SIGNAL | 声明信号的宏，参数由 MethodInfo 描述 |
| Callable | 封装「对象 + 方法」的可调用引用，用于信号连接 |
| entry_symbol | .gdextension 中指定的动态库入口函数名 |
| ModuleInitializationLevel | 扩展初始化等级（core/servers/scene/editor） |
| SCons | Godot 及 godot-cpp 使用的 Python 构建系统 |

---

## 🔗 延伸阅读

- **官方文档**: [What is GDExtension?](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/what_is_gdextension.html)
- **官方文档**: [GDExtension C++ example](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/gdextension_cpp_example.html)
- **官方文档**: [Custom modules in C++（对比模块开发）](https://docs.godotengine.org/en/stable/engine_details/engine_api/custom_modules_in_cpp.html)
- **源码位置**: godot-cpp 仓库 `https://github.com/godotengine/godot-cpp`（含 `test/` 目录下的官方示例）
- **源码位置**: Godot 引擎源码 `core/extension/gdextension_interface.h`、`core/extension/extension_api_dump.cpp`

---

## 📋 下一章预告

**第 34 篇：GDExtension 进阶**

- 绑定外部第三方库
- 自定义 Resource 与资源格式加载器
- 用 GDExtension 扩展编辑器
- 调试、热重载与跨平台分发

---

*写作时间：2026-08-27*  
*字数：约 15,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-08-27 19:30*
