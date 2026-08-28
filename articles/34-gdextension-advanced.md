# 第 34 篇：GDExtension 进阶开发

> **本卷定位**: 引擎扩展开发卷  
> **前置知识**: GDExtension 入门（C++、SCons 构建、基础类注册），建议先读第七卷脚本系统  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家

---

## 📖 本章导读

GDExtension 入门教程能教会你注册一个类、绑定一个方法、导出一个属性，但真实的扩展开发远不止于此。当你要开发一个可以发布到 Asset Library 的原生插件时，会立刻遇到一连串进阶问题：属性如何分组、如何加范围滑条？虚函数覆写和信号回调有什么坑？`Ref<T>`、`TypedArray`、`StringName` 这些类型的所有权归谁管？如何让扩展类在编辑器里像 `@tool` 脚本一样运行？如何打断点调试 C++ 代码？如何构建 Windows/Linux/macOS 三个平台的产物并自动发布？

本章以一个贯穿示例——`WaveEmitter`（波形发射器节点）和 `WavePreset`（波形预设资源）——系统性地回答这些问题，覆盖类绑定机制、信号进阶、类型互操作、资源子类、编辑器集成、调试技巧和多平台分发七大主题。全文基于 Godot 4.x 稳定 API 与 godot-cpp 绑定撰写。

---

## 🎯 学习目标

- 深入理解 MethodBind 与 ClassDB 绑定机制，掌握属性提示、分组与虚函数覆写
- 掌握自定义信号的定义、参数描述、连接与发射的完整流程
- 理解 Ref\<T\>、TypedArray、Dictionary、StringName 等类型的生命周期与性能特征
- 学会在 GDExtension 中定义、加载、保存自定义 Resource 子类
- 掌握 EditorPlugin、工具类注册（@tool 等价物）与 EditorExportPlugin 的编辑器集成方式
- 掌握 C++ 断点调试方法与多平台编译、CI 构建、AssetLib 发布流程

---

## 1. 深入类绑定机制

### 1.1 MethodBind 的工作原理

在 GDScript 中调用一个方法时，引擎并不需要知道这个方法用哪种语言实现——它只需要一个统一的「方法描述符」。这个描述符在引擎核心中就是 `MethodBind`。理解它的结构，是理解一切绑定行为的基础。

```
┌─────────────────────────────────────────────────────────────────┐
│                      方法调用流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GDScript / C# / 编辑器                                          │
│       │                                                         │
│       ▼  obj.call("set_speed", 2.0)                             │
│  ┌─────────────────────────────┐                                │
│  │  ClassDB（类数据库）         │  按类名 + 方法名查表           │
│  │  "WaveEmitter" ──► MethodBind│                               │
│  └─────────────────────────────┘                                │
│       │                                                         │
│       ▼  MethodBind::call(instance, args, arg_count)            │
│  ┌─────────────────────────────┐                                │
│  │  MethodBindTR<double,double> │  godot-cpp 生成的特化模板      │
│  │  ・校验参数个数与类型         │                                │
│  │  ・Variant → C++ 类型转换    │                                │
│  │  │                          │                                │
│  │  ▼                          │                                │
│  │  调用 &WaveEmitter::set_speed│  真正的 C++ 成员函数指针       │
│  └─────────────────────────────┘                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

当你在 `_bind_methods()` 中写下：

```cpp
ClassDB::bind_method(D_METHOD("set_speed", "speed"), &WaveEmitter::set_speed);
```

godot-cpp 会在编译期根据 `&WaveEmitter::set_speed` 的函数签名实例化一个 `MethodBindT` 模板特化（例如 `MethodBindTR<R, P...>`），它负责三件事：

1. **注册元信息**：方法名、参数名（来自 `D_METHOD`）、参数类型（由 C++ 签名推导）、返回值类型，写入 ClassDB。
2. **运行时调用**：把 `Variant` 参数数组解码为 C++ 原生类型，调用成员函数指针，再把返回值编码回 `Variant`。
3. **校验**：参数个数不匹配、类型无法转换时抛出错误，而不是崩溃。

由此可以得到两个重要推论：

- **绑定有固定开销**。每次跨语言调用都要经过 Variant 编解码，对每帧调用上万次的热路径（如粒子更新），应设计为批量接口（一次调用传入 `PackedVector2Array`）而非逐对象调用。
- **未绑定的方法对外不可见**。C++ 内部的 `private` 辅助函数只要不绑定，就不会出现在脚本 API 中——这是封装边界的天然划分。

### 1.2 D_METHOD 与默认参数

`D_METHOD` 宏只是帮你构造 `MethodInfo`：第一个参数是方法名，其余是参数名。参数名会显示在编辑器文档和自动补全里，务必认真填写。

带默认参数的方法使用 `DEFVAL`：

```cpp
// wave_emitter.cpp
void WaveEmitter::_bind_methods() {
    // 普通绑定
    ClassDB::bind_method(D_METHOD("set_speed", "speed"), &WaveEmitter::set_speed);
    ClassDB::bind_method(D_METHOD("get_speed"), &WaveEmitter::get_speed);

    // 带默认参数：emit_burst(count = 8)
    ClassDB::bind_method(
        D_METHOD("emit_burst", "count"),
        &WaveEmitter::emit_burst,
        DEFVAL(8)  // 对应 GDScript: emitter.emit_burst()
    );
}
```

在 GDScript 侧，这个类看起来和原生类毫无区别：

```gdscript
var emitter := WaveEmitter.new()
emitter.speed = 2.5
emitter.emit_burst()      # 使用默认参数 8
emitter.emit_burst(16)    # 显式传参
```

### 1.3 属性提示与分组

属性注册的三件套是 `PropertyInfo` + `ADD_PROPERTY`。`PropertyInfo` 的构造函数签名为：

```cpp
PropertyInfo(Variant::Type type, const StringName &name,
             PropertyHint hint = PROPERTY_HINT_NONE,
             const String &hint_string = "",
             uint32_t usage = PROPERTY_USAGE_DEFAULT);
```

`PROPERTY_HINT_*` 决定属性在检查器中的呈现方式。常用提示一览：

| 提示常量 | hint_string 格式 | 检查器表现 |
|----------|------------------|-----------|
| `PROPERTY_HINT_RANGE` | `"min,max,step"` | 范围滑条 |
| `PROPERTY_HINT_ENUM` | `"Slow,Normal,Fast"` | 下拉框 |
| `PROPERTY_HINT_FLAGS` | `"A,B,C"` | 复选框组 |
| `PROPERTY_HINT_FILE` | `"*.wav,*.ogg"` | 文件选择框 |
| `PROPERTY_HINT_RESOURCE_TYPE` | `"WavePreset"` | 资源槽（限定类型） |
| `PROPERTY_HINT_MULTILINE_TEXT` | （无） | 多行文本框 |
| `PROPERTY_HINT_COLOR_NO_ALPHA` | （无） | 颜色选择器（无透明度） |

属性分组使用 `ADD_GROUP` / `ADD_SUBGROUP`（对应 GDScript 的 `@export_group` / `@export_subgroup`）：

```cpp
void WaveEmitter::_bind_methods() {
    // —— 方法绑定（略）——

    // 属性分组：对应 @export_group("波形参数")
    ADD_GROUP("波形参数", "wave_");

    ClassDB::bind_method(D_METHOD("set_amplitude", "amplitude"), &WaveEmitter::set_amplitude);
    ClassDB::bind_method(D_METHOD("get_amplitude"), &WaveEmitter::get_amplitude);
    ADD_PROPERTY(
        PropertyInfo(Variant::FLOAT, "wave_amplitude",
                     PROPERTY_HINT_RANGE, "0.1,100.0,0.1"),
        "set_amplitude", "get_amplitude");

    ClassDB::bind_method(D_METHOD("set_wave_type", "type"), &WaveEmitter::set_wave_type);
    ClassDB::bind_method(D_METHOD("get_wave_type"), &WaveEmitter::get_wave_type);
    ADD_PROPERTY(
        PropertyInfo(Variant::INT, "wave_type",
                     PROPERTY_HINT_ENUM, "Sine,Square,Triangle,Sawtooth"),
        "set_wave_type", "get_wave_type");

    ADD_GROUP("高级", "");
    ClassDB::bind_method(D_METHOD("set_preset", "preset"), &WaveEmitter::set_preset);
    ClassDB::bind_method(D_METHOD("get_preset"), &WaveEmitter::get_preset);
    ADD_PROPERTY(
        PropertyInfo(Variant::OBJECT, "preset",
                     PROPERTY_HINT_RESOURCE_TYPE, "WavePreset"),
        "set_preset", "get_preset");
}
```

`ADD_GROUP` 的第二个参数是**属性名前缀过滤器**：以该前缀开头的后续属性会被归入此组。这在属性很多时能保持检查器整洁。

setter 中发出变更通知是一个好习惯——当属性影响显示或需要在编辑器中即时刷新时：

```cpp
void WaveEmitter::set_amplitude(double p_amplitude) {
    amplitude = p_amplitude;
    // 通知检查器/编辑器属性已变化（场景序列化依赖它判断脏状态）
    notify_property_list_changed();  // 仅当属性列表结构变化时才需要
    queue_redraw();                  // Node2D/Control：请求重绘
}
```

注意：`notify_property_list_changed()` 只应在**属性列表本身**（增删属性、改变提示）发生变化时调用，普通数值变化不需要它。

### 1.4 虚函数覆写：_ready、_process 与 _notification

覆写引擎虚函数的方式与普通 C++ 覆写一致——在头文件声明，用 `override` 标记，**不需要**在 `_bind_methods` 中绑定：

```cpp
// wave_emitter.h
#ifndef WAVE_EMITTER_H
#define WAVE_EMITTER_H

#include <godot_cpp/classes/node2d.hpp>
#include <godot_cpp/classes/resource.hpp>

namespace godot {

class WavePreset;  // 前向声明，见第 4 节

class WaveEmitter : public Node2D {
    GDCLASS(WaveEmitter, Node2D)

public:
    enum WaveType {
        WAVE_SINE,
        WAVE_SQUARE,
        WAVE_TRIANGLE,
        WAVE_SAWTOOTH,
    };

private:
    double time_passed = 0.0;
    double amplitude = 10.0;
    double speed = 1.0;
    WaveType wave_type = WAVE_SINE;
    Ref<WavePreset> preset;

protected:
    static void _bind_methods();

public:
    WaveEmitter();
    ~WaveEmitter();

    // 引擎虚函数：签名必须与引擎侧完全一致
    void _ready() override;
    void _process(double delta) override;
    void _notification(int p_what);  // 特殊：见下文

    void set_speed(double p_speed);
    double get_speed() const;
    void set_amplitude(double p_amplitude);
    double get_amplitude() const;
    void set_wave_type(WaveType p_type);
    WaveType get_wave_type() const;
    void set_preset(const Ref<WavePreset> &p_preset);
    Ref<WavePreset> get_preset() const;

    void emit_burst(int p_count);

    // 静态工具函数，见 1.5 节
    static double sample_wave(WaveType p_type, double p_phase);
};

// 枚举值绑定为类常量
VARIANT_ENUM_CAST(WaveEmitter::WaveType);

} // namespace godot

#endif // WAVE_EMITTER_H
```

实现文件中的虚函数：

```cpp
// wave_emitter.cpp
#include "wave_emitter.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

WaveEmitter::WaveEmitter() {
    // 显式开启 _process 回调；等价于 GDScript 的 set_process(true)
    set_process(true);
}

WaveEmitter::~WaveEmitter() {
}

void WaveEmitter::_ready() {
    // 节点进入场景树且子节点就绪后调用
    if (preset.is_valid()) {
        amplitude = preset->get_default_amplitude();
    }
}

void WaveEmitter::_process(double delta) {
    time_passed += speed * delta;
    double y = sample_wave(wave_type, time_passed) * amplitude;
    set_position(Vector2(get_position().x, y));
}
```

几个容易踩的坑：

- **签名必须精确匹配**。`_process(double delta)` 写成 `float` 会导致覆写失败（`override` 关键字会在编译期拦住这类错误，务必加上）。
- **`_notification(int)` 不是虚函数覆写**。引擎通过 `NOTIFICATION_*` 常量分发通知，子类直接定义同名方法即可，不要加 `override`：

```cpp
void WaveEmitter::_notification(int p_what) {
    switch (p_what) {
        case NOTIFICATION_ENTER_TREE:
            // 进入场景树（早于 _ready）
            break;
        case NOTIFICATION_EXIT_TREE:
            // 离开场景树，适合清理非 RAII 资源
            break;
        case NOTIFICATION_VISIBILITY_CHANGED:
            set_process(is_visible_in_tree());
            break;
    }
}
```

- **构造时机早于引擎属性赋值**。构造函数里读到的永远是 C++ 默认值，编辑器中配置的值要等场景反序列化完成后才生效——需要依赖导出值的初始化逻辑请放在 `_ready()` 中。

### 1.5 静态方法与工具函数

静态方法用 `ClassDB::bind_static_method` 绑定，绑定后可在 GDScript 中直接通过类名调用，非常适合数学工具、工厂方法：

```cpp
void WaveEmitter::_bind_methods() {
    // ... 其余绑定 ...

    // 静态方法：WaveEmitter.sample_wave(type, phase)
    ClassDB::bind_static_method("WaveEmitter",
        D_METHOD("sample_wave", "type", "phase"),
        &WaveEmitter::sample_wave);

    // 枚举常量绑定，对应 GDScript: WaveEmitter.WAVE_SINE
    BIND_ENUM_CONSTANT(WAVE_SINE);
    BIND_ENUM_CONSTANT(WAVE_SQUARE);
    BIND_ENUM_CONSTANT(WAVE_TRIANGLE);
    BIND_ENUM_CONSTANT(WAVE_SAWTOOTH);
}

double WaveEmitter::sample_wave(WaveType p_type, double p_phase) {
    switch (p_type) {
        case WAVE_SINE:
            return Math::sin(p_phase * Math_TAU);
        case WAVE_SQUARE:
            return Math::fmod(p_phase, 1.0) < 0.5 ? 1.0 : -1.0;
        case WAVE_TRIANGLE: {
            double t = Math::fmod(p_phase, 1.0);
            return t < 0.5 ? (4.0 * t - 1.0) : (3.0 - 4.0 * t);
        }
        case WAVE_SAWTOOTH:
            return 2.0 * Math::fmod(p_phase, 1.0) - 1.0;
    }
    return 0.0;
}
```

GDScript 侧使用：

```gdscript
var v := WaveEmitter.sample_wave(WaveEmitter.WAVE_SINE, 0.25)
print(v)  # 1.0
```

头文件中类声明之后的 `VARIANT_ENUM_CAST(WaveEmitter::WaveType);` 是必需的：它让 godot-cpp 知道该枚举与 `Variant::INT` 之间的转换关系，`bind_method` 的模板推导依赖它。缺少这一行，编译器会报出晦涩的模板错误。

---

## 2. 信号进阶

### 2.1 自定义信号定义

信号在 `_bind_methods()` 中用 `ADD_SIGNAL` 注册，参数用 `PropertyInfo` 逐项描述：

```cpp
void WaveEmitter::_bind_methods() {
    // ... 属性绑定 ...

    // 无参数信号
    ADD_SIGNAL(MethodInfo("burst_started"));

    // 带参数信号：参数名 + 类型会出现在编辑器连接对话框和文档中
    ADD_SIGNAL(MethodInfo("burst_finished",
        PropertyInfo(Variant::INT, "count"),
        PropertyInfo(Variant::VECTOR2, "origin")));

    // 携带对象参数的信号：建议补充 class_name 以便脚本侧获得类型提示
    ADD_SIGNAL(MethodInfo("preset_changed",
        PropertyInfo(Variant::OBJECT, "preset",
                     PROPERTY_HINT_RESOURCE_TYPE, "WavePreset")));
}
```

### 2.2 发射信号

C++ 侧发射信号使用 `emit_signal`，参数按注册顺序传入：

```cpp
void WaveEmitter::emit_burst(int p_count) {
    emit_signal("burst_started");

    for (int i = 0; i < p_count; i++) {
        // ... 生成波形粒子 ...
    }

    emit_signal("burst_finished", p_count, get_global_position());
}

void WaveEmitter::set_preset(const Ref<WavePreset> &p_preset) {
    if (preset == p_preset) {
        return;  // 避免重复发射
    }
    preset = p_preset;
    emit_signal("preset_changed", preset);
}
```

### 2.3 连接信号

**C++ 侧连接**——连接到本类或其他已绑定方法：

```cpp
void WaveEmitter::_ready() {
    // 连接到其他节点的信号
    Node *timer_node = get_node_or_null(NodePath("TickTimer"));
    if (timer_node) {
        // 经典写法：字符串方法名 + Callable
        timer_node->connect("timeout", Callable(this, "emit_burst"));
    }
}
```

注意 `Callable(this, "emit_burst")` 要求 `emit_burst` **已在 `_bind_methods` 中绑定**，否则运行时报错。如果想在编译期检查方法存在性，godot-cpp 提供了 `callable_mp` 模板：

```cpp
#include <godot_cpp/core/object.hpp>

// 编译期类型检查的 Callable，推荐在纯 C++ 互连时使用
timer_node->connect("timeout", callable_mp(this, &WaveEmitter::emit_burst));
```

`callable_mp` 生成的 Callable 携带强类型签名，参数不匹配会在编译期暴露，比字符串写法安全得多。

**断开连接**与**防重复连接**：

```cpp
// 防重复连接：connect 返回 Error 码
Error err = timer_node->connect("timeout", callable_mp(this, &WaveEmitter::emit_burst),
                                CONNECT_REFERENCE_COUNTED);
if (err == ERR_INVALID_PARAMETER) {
    // 通常意味着已经连接过
}

// 显式断开
if (timer_node->is_connected("timeout", callable_mp(this, &WaveEmitter::emit_burst))) {
    timer_node->disconnect("timeout", callable_mp(this, &WaveEmitter::emit_burst));
}
```

**GDScript 侧连接**（用户视角，务必在文档中给出示例）：

```gdscript
extends Node

@onready var emitter: WaveEmitter = $WaveEmitter

func _ready() -> void:
    # 方式一：直接连接
    emitter.burst_finished.connect(_on_burst_finished)
    # 方式二：带连接标志（一次性）
    emitter.burst_started.connect(_on_burst_started, CONNECT_ONE_SHOT)

func _on_burst_finished(count: int, origin: Vector2) -> void:
    print("发射完成：", count, " 个波形 @ ", origin)

func _on_burst_started() -> void:
    print("发射开始")
```

### 2.4 信号的参数设计原则

- **参数越少越好**：每个参数都是一次 Variant 装箱。高频信号（每帧发射）尽量不超过 2-3 个参数。
- **避免在信号参数中传递大型 Array/Dictionary 的频繁拷贝**：传递引用类型的 `Variant` 是引用计数传递，开销可控，但脚本侧的任何修改都会影响发送方持有的数据，文档中应说明所有权约定。
- **信号名用过去式/进行时**：`burst_finished`、`preset_changed`，与引擎内置信号命名风格（`tree_entered`、`body_entered`）保持一致。

---

## 3. 与引擎类型互操作

### 3.1 所有权模型总览

GDExtension 与引擎之间的数据交换，本质是 C++ RAII 世界与 Godot 引用计数/手动内存世界的交界。先建立一张所有权地图：

```
┌───────────────────────────────────────────────────────────────────┐
│                     Godot 类型的所有权模型                         │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  值类型（拷贝语义，无需管理）                                      │
│  ├─ int / float / bool / Vector2 / Vector3 / Color / Transform3D  │
│  └─ Rect2 / Plane / Quaternion / AABB / Basis ...                 │
│                                                                   │
│  引用计数的 Variant 内建类型（RAII 包装，自动释放）                 │
│  ├─ String / StringName / NodePath                                │
│  ├─ Array / TypedArray<T> / Dictionary                            │
│  └─ PackedByteArray / PackedVector2Array / PackedFloat32Array ... │
│                                                                   │
│  RefCounted 派生对象（用 Ref<T> 智能指针持有）                     │
│  ├─ Resource 及其子类（Texture2D、WavePreset ...）                │
│  ├─ InputEvent、Image、FileAccess ...                             │
│  └─ Ref<T> 析构时自动 unref                                       │
│                                                                   │
│  Object 派生对象（手动内存管理，不能用 Ref<T>！）                  │
│  ├─ Node 及其子类：由场景树父子关系管理，queue_free() 销毁        │
│  ├─ 游离 Object：memnew 创建，memdelete 释放                      │
│  └─ 引擎返回的裸指针所有权属于引擎，不要 delete                    │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

最致命的错误是**用 `Ref<T>` 包装非 RefCounted 对象**（如 Node）。`Ref<Node>` 可以编译通过（模板约束较松），但析构时调用 `unref()` 对非引用计数对象是未定义行为。判断准则：能放进场景树的、从 `Node` 继承的，一律裸指针 + `memnew`/`memdelete` 或交给父节点管理。

### 3.2 Ref\<T\>：引用计数对象的安全持有

`Ref<T>` 是 godot-cpp 的智能指针，语义类似 `std::shared_ptr`，但计数存在对象内部：

```cpp
#include <godot_cpp/classes/resource_loader.hpp>

void WaveEmitter::load_preset_from_path(const String &p_path) {
    // ResourceLoader::load 返回 Ref<Resource>，需要向下转型
    Ref<Resource> res = ResourceLoader::get_singleton()->load(p_path);
    if (res.is_null()) {
        UtilityFunctions::push_error("加载失败: ", p_path);
        return;
    }
    // 安全的动态向下转型，失败返回空 Ref
    preset = Object::cast_to<WavePreset>(res.ptr());
    // 离开作用域时 res 自动 unref；preset 持有的拷贝使引用计数 +1，
    // 资源不会被释放
}
```

要点：

- **`is_valid()` / `is_null()`** 判空，不要直接和 `nullptr` 比较裸语义。
- **避免临时 `Ref` 悬垂**：`res->method()` 在 `res` 是临时对象时（如 `ResourceLoader::load(...)->get_x()`）是安全的，因为临时对象活到语句结束；但不要把 `res.ptr()` 存成裸指针长期持有——引用计数释放后裸指针即悬垂。需要长期持有就存 `Ref<T>` 拷贝。
- **循环引用**：Resource A 持有 `Ref<B>`，B 又持有 `Ref<A>`，两者永不释放。资源间互相引用时注意打破环（弱引用可用 `ObjectID` + `ObjectDB::get_instance()` 模式，但设计上是坏味道，优先调整依赖方向）。

### 3.3 TypedArray 与 Array

`TypedArray<T>` 向脚本侧暴露元素类型约束，编辑器数组属性因此能获得正确的元素编辑器和校验：

```cpp
// 头文件
#include <godot_cpp/variant/typed_array.hpp>

private:
    TypedArray<WavePreset> preset_chain;

// _bind_methods 中
ClassDB::bind_method(D_METHOD("set_preset_chain", "chain"), &WaveEmitter::set_preset_chain);
ClassDB::bind_method(D_METHOD("get_preset_chain"), &WaveEmitter::get_preset_chain);
ADD_PROPERTY(
    PropertyInfo(Variant::ARRAY, "preset_chain",
                 PROPERTY_HINT_ARRAY_TYPE, "WavePreset"),
    "set_preset_chain", "get_preset_chain");
```

要点：

- **Array/Dictionary 是引用语义**。`Array b = a;` 之后 `b.push_back(x)` 会修改同一份底层数据（除非先 `duplicate()`）。把成员数组的拷贝返回给脚本侧时，如果不希望脚本改动影响内部状态，返回 `array.duplicate()`。
- **读取安全**：脚本可以塞进错误类型的元素（尤其非 TypedArray），消费前用 `arr[i].get_type()` 或 `Object::cast_to` 校验。
- **热路径用 Packed 数组**。`PackedFloat32Array`、`PackedVector2Array` 等是连续内存布局，赋值一次即完成数据移交，遍历性能远优于 `Array`。凡是「大量同质数值」的接口（顶点、采样点、物理数据）都应使用 Packed 数组：

```cpp
// 批量接口：一次调用传输全部采样点，避免逐点跨语言调用
PackedFloat32Array WaveEmitter::sample_range(double p_from, double p_to, int p_steps) const {
    PackedFloat32Array result;
    result.resize(p_steps);
    for (int i = 0; i < p_steps; i++) {
        double phase = p_from + (p_to - p_from) * i / Math::max(1, p_steps - 1);
        result.set(i, sample_wave(wave_type, phase));
    }
    return result;
}
```

### 3.4 Dictionary 的取舍

`Dictionary` 灵活但开销大：键是 `Variant`，哈希 + 装箱成本不低。绑定 API 时优先考虑：

1. 参数固定的接口 → 用普通方法参数，不用 Dictionary；
2. 结构化数据 → 定义 Resource 子类（见第 4 节），类型安全且可序列化；
3. 真正动态的键值对（JSON 桥接、调试转储）→ 才用 Dictionary。

### 3.5 String 与 StringName 的性能差异

这是 GDExtension 性能优化中最立竿见影的一条：

| 类型 | 内部表示 | 比较成本 | 适用场景 |
|------|----------|----------|----------|
| `String` | 动态 UTF-32 字符串 | O(n) 逐字符比较 | 文本内容、路径显示 |
| `StringName` | 全局字符串池中的驻留指针 | O(1) 指针比较 | 方法名、信号名、属性名、节点组名 |

引擎内部所有「标识符」——方法查找、信号发射、组判断——都以 `StringName` 进行。每当你写：

```cpp
// 每帧执行：隐式从 "body_entered" 字面量构造临时 StringName
// 字面量 → String（UTF-8 解码）→ StringName（全局池查找 + 哈希）
emit_signal("burst_finished", count);
```

如果这行代码在热路径上，应把 `StringName` 缓存为静态变量：

```cpp
void WaveEmitter::emit_burst(int p_count) {
    // 静态局部变量只初始化一次，后续发射零构造开销
    static const StringName burst_finished_sn = "burst_finished";
    emit_signal(burst_finished_sn, p_count, get_global_position());
}
```

同理，频繁调用的 `has_group("enemy")`、`get_node(NodePath("..."))` 中的字符串参数都值得静态化。godot-cpp 对字符串字面量有 `SNAME()` 宏（`SNAME("burst_finished")`）可达到同样效果，内部正是缓存静态 `StringName`。

### 3.6 对象生命周期检查清单

- 引擎 API 返回的 `Node *`、`Object *` 裸指针——**所有权归引擎**，永远不要 `delete`。
- 自己 `memnew(Node)` 的节点——加入场景树（`add_child`）后归场景树管理；未加入则须 `memdelete`。
- `Object::cast_to<T>(ptr)` 不产生新引用，只是带类型检查的指针转换。
- 判断对象是否还活着：裸指针可能已失效，安全做法是从一开始就用 `ObjectID` 记录，再 `ObjectDB::get_instance(id)` 取回（取回为 `nullptr` 即已销毁）。

---

## 4. 使用资源与 Resource 子类

### 4.1 定义自定义 Resource

Resource 子类是 GDExtension 中传递结构化配置数据的最佳载体：类型安全、可被编辑器序列化、支持 `.tres` 文件保存与检查器编辑。

```cpp
// wave_preset.h
#ifndef WAVE_PRESET_H
#define WAVE_PRESET_H

#include <godot_cpp/classes/resource.hpp>

namespace godot {

class WavePreset : public Resource {
    GDCLASS(WavePreset, Resource)

private:
    double default_amplitude = 10.0;
    double default_speed = 1.0;
    String preset_name = "New Preset";
    PackedFloat32Array envelope;  // 包络采样点

protected:
    static void _bind_methods();

public:
    void set_default_amplitude(double p_value);
    double get_default_amplitude() const;
    void set_default_speed(double p_value);
    double get_default_speed() const;
    void set_preset_name(const String &p_name);
    String get_preset_name() const;
    void set_envelope(const PackedFloat32Array &p_envelope);
    PackedFloat32Array get_envelope() const;
};

} // namespace godot

#endif // WAVE_PRESET_H
```

```cpp
// wave_preset.cpp
#include "wave_preset.h"

using namespace godot;

void WavePreset::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_default_amplitude", "value"), &WavePreset::set_default_amplitude);
    ClassDB::bind_method(D_METHOD("get_default_amplitude"), &WavePreset::get_default_amplitude);
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "default_amplitude",
                              PROPERTY_HINT_RANGE, "0.1,100.0,0.1"),
                 "set_default_amplitude", "get_default_amplitude");

    ClassDB::bind_method(D_METHOD("set_default_speed", "value"), &WavePreset::set_default_speed);
    ClassDB::bind_method(D_METHOD("get_default_speed"), &WavePreset::get_default_speed);
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "default_speed"),
                 "set_default_speed", "get_default_speed");

    ClassDB::bind_method(D_METHOD("set_preset_name", "name"), &WavePreset::set_preset_name);
    ClassDB::bind_method(D_METHOD("get_preset_name"), &WavePreset::get_preset_name);
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "preset_name"),
                 "set_preset_name", "get_preset_name");

    ClassDB::bind_method(D_METHOD("set_envelope", "envelope"), &WavePreset::set_envelope);
    ClassDB::bind_method(D_METHOD("get_envelope"), &WavePreset::get_envelope);
    ADD_PROPERTY(PropertyInfo(Variant::PACKED_FLOAT32_ARRAY, "envelope"),
                 "set_envelope", "get_envelope");
}

void WavePreset::set_default_amplitude(double p_value) { default_amplitude = p_value; }
double WavePreset::get_default_amplitude() const { return default_amplitude; }
void WavePreset::set_default_speed(double p_value) { default_speed = p_value; }
double WavePreset::get_default_speed() const { return default_speed; }
void WavePreset::set_preset_name(const String &p_name) { preset_name = p_name; }
String WavePreset::get_preset_name() const { return preset_name; }
void WavePreset::set_envelope(const PackedFloat32Array &p_envelope) { envelope = p_envelope; }
PackedFloat32Array WavePreset::get_envelope() const { return envelope; }
```

注册方式与普通类相同（`GDREGISTER_RUNTIME_CLASS(WavePreset)`）。注册后，用户在编辑器「新建资源」对话框中就能看到 `WavePreset`，保存为 `.tres` 文件时所有 `ADD_PROPERTY` 注册过的属性自动序列化——**不需要你写任何序列化代码**，这是复用引擎资源系统的最大红利。

### 4.2 加载与保存

```cpp
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/classes/resource_saver.hpp>

// 加载（加载结果带缓存，同一路径返回同一实例）
Ref<WavePreset> load_wave_preset(const String &p_path) {
    Ref<Resource> res = ResourceLoader::get_singleton()->load(p_path, "WavePreset");
    return Object::cast_to<WavePreset>(res.ptr());
}

// 保存
Error save_wave_preset(const Ref<WavePreset> &p_preset, const String &p_path) {
    if (p_preset.is_null()) {
        return ERR_INVALID_PARAMETER;
    }
    // FLAG_REPLACE_SUBRESOURCE_PATHS 等标志按需添加
    return ResourceSaver::get_singleton()->save(p_preset, p_path);
}
```

要点：

- `load()` 的第二个参数是**类型提示**，填写后引擎会校验资源类型，传错类型返回空。
- 资源默认**全局缓存**：`load("res://a.tres")` 两次返回同一实例。需要独立副本时调用 `res->duplicate(true)`（深拷贝）。
- `p_preset->take_over_path(p_path)` 可以让一个内存中新建的资源「认领」某个路径，使后续 `load` 命中它——编辑器工具批量生成资源时常用。

### 4.3 节点持有资源：一个完整闭环

回到 `WaveEmitter`，资源属性通过 `PROPERTY_HINT_RESOURCE_TYPE` 暴露后，检查器中会出现限定 `WavePreset` 类型的资源槽，支持拖入 `.tres` 文件、内嵌编辑、新建子资源：

```cpp
void WaveEmitter::set_preset(const Ref<WavePreset> &p_preset) {
    if (preset == p_preset) {
        return;
    }
    preset = p_preset;
    if (preset.is_valid()) {
        amplitude = preset->get_default_amplitude();
        speed = preset->get_default_speed();
    }
    emit_signal("preset_changed", preset);
}
```

整个数据流形成闭环：

```
┌──────────────────────────────────────────────────────────────┐
│              自定义资源的数据流                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  编辑器「新建资源」──► WavePreset 实例                        │
│         │                     │ 检查器编辑属性                │
│         ▼                     ▼                              │
│  ResourceSaver::save() ──► wave_default.tres（文本序列化）   │
│                                     │                        │
│  游戏运行: ResourceLoader::load() ◄─┘（缓存 + 引用计数）     │
│                     │                                        │
│                     ▼                                        │
│  WaveEmitter.preset ──► 影响 amplitude / speed               │
│                     │                                        │
│                     ▼                                        │
│  preset_changed 信号 ──► GDScript UI 同步刷新                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 编辑器集成

### 5.1 初始化层级：工具类的开关

GDExtension 没有 `@tool` 关键字，等价机制由两部分组成：**注册层级**与**注册宏**。入口函数中设置的最低初始化层级决定扩展何时加载：

```cpp
// register_types.cpp
#include "register_types.h"
#include "wave_emitter.h"
#include "wave_preset.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_wave_module(ModuleInitializationLevel p_level) {
    // SCENE 层级：运行时类，编辑器和游戏中都可用
    if (p_level == MODULE_INITIALIZATION_LEVEL_SCENE) {
        GDREGISTER_CLASS(WaveEmitter);        // 编辑器中也可实例化（≈ @tool）
        GDREGISTER_RUNTIME_CLASS(WavePreset); // 仅运行时可用
    }
    // EDITOR 层级：纯编辑器类，导出游戏时不加载
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        GDREGISTER_CLASS(WaveEmitterEditorPlugin);  // 见 5.3
    }
}

void uninitialize_wave_module(ModuleInitializationLevel p_level) {
    // 通常无需反注册，引擎退出时统一清理
}

extern "C" {
GDExtensionBool GDE_EXPORT wave_library_init(
        GDExtensionInterfaceGetProcAddress p_get_proc_address,
        const GDExtensionClassLibraryPtr p_library,
        GDExtensionInitialization *r_initialization) {
    GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);
    init_obj.register_initializer(initialize_wave_module);
    init_obj.register_terminator(uninitialize_wave_module);
    // 最低层级设为 SCENE：扩展在场景系统就绪后加载
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
    return init_obj.init();
}
}
```

四个初始化层级按顺序为：`CORE` → `SERVERS` → `SCENE` → `EDITOR`。绝大多数扩展用 `SCENE` 即可。

### 5.2 @tool 等价物：GDREGISTER_CLASS vs GDREGISTER_RUNTIME_CLASS

| 注册宏 | 编辑器中可实例化 | 游戏运行时可用 | 类比 |
|--------|:---:|:---:|------|
| `GDREGISTER_CLASS` | ✅ | ✅ | `@tool` 脚本 |
| `GDREGISTER_RUNTIME_CLASS` | ❌（灰色显示，提示不可在编辑器创建） | ✅ | 普通脚本 |

让 `WaveEmitter` 在编辑器中实时运行，除了用 `GDREGISTER_CLASS` 注册，还要处理一个经典问题——**区分编辑器与游戏运行环境**：

```cpp
#include <godot_cpp/classes/engine.hpp>

void WaveEmitter::_process(double delta) {
    // is_editor_hint() 在编辑器中返回 true，游戏运行时返回 false
    if (Engine::get_singleton()->is_editor_hint()) {
        // 编辑器预览模式：慢速播放，避免干扰场景编辑
        time_passed += delta * 0.25;
    } else {
        time_passed += speed * delta;
    }
    double y = sample_wave(wave_type, time_passed) * amplitude;
    set_position(Vector2(get_position().x, y));
}
```

注意事项：

- 工具类的 `_ready`、`_process` 会在**编辑器打开场景时**执行，代码必须对编辑器环境健壮（例如不要假设游戏单例存在）。
- 工具类造成的场景修改会被保存进 `.tscn`，预览逻辑里产生的临时子节点记得设置 `owner = nullptr`（默认即不归档）并在退出时清理。

### 5.3 EditorPlugin：C++ 版编辑器插件

GDExtension 可以直接继承 `EditorPlugin` 编写编辑器插件，享受 C++ 的性能与类型安全：

```cpp
// wave_emitter_editor_plugin.h
#ifndef WAVE_EMITTER_EDITOR_PLUGIN_H
#define WAVE_EMITTER_EDITOR_PLUGIN_H

#include <godot_cpp/classes/editor_plugin.hpp>

namespace godot {

class WaveEmitterEditorPlugin : public EditorPlugin {
    GDCLASS(WaveEmitterEditorPlugin, EditorPlugin)

private:
    Button *preview_button = nullptr;

protected:
    static void _bind_methods();

public:
    void _enter_tree() override;
    void _exit_tree() override;

    void _on_preview_pressed();
};

} // namespace godot

#endif
```

```cpp
// wave_emitter_editor_plugin.cpp
#include "wave_emitter_editor_plugin.h"
#include "wave_emitter.h"

#include <godot_cpp/classes/button.hpp>
#include <godot_cpp/classes/editor_interface.hpp>
#include <godot_cpp/classes/scene_tree.hpp>

using namespace godot;

void WaveEmitterEditorPlugin::_bind_methods() {
    ClassDB::bind_method(D_METHOD("_on_preview_pressed"),
                         &WaveEmitterEditorPlugin::_on_preview_pressed);
}

void WaveEmitterEditorPlugin::_enter_tree() {
    // 插件启用：向 2D 主屏工具栏注入一个预览按钮
    preview_button = memnew(Button);
    preview_button->set_text("预览波形");
    preview_button->connect("pressed", Callable(this, "_on_preview_pressed"));
    add_control_to_container(CONTAINER_CANVAS_EDITOR_MENU, preview_button);
}

void WaveEmitterEditorPlugin::_exit_tree() {
    // 插件禁用：务必移除注入的 UI 并释放
    if (preview_button) {
        remove_control_from_container(CONTAINER_CANVAS_EDITOR_MENU, preview_button);
        memdelete(preview_button);
        preview_button = nullptr;
    }
}

void WaveEmitterEditorPlugin::_on_preview_pressed() {
    // 获取当前编辑的场景根节点，遍历找到 WaveEmitter 并触发预览
    Node *edited_root = EditorInterface::get_singleton()->get_edited_scene_root();
    if (!edited_root) {
        return;
    }
    TypedArray<Node> nodes = edited_root->find_children("*", "WaveEmitter", true, false);
    for (int i = 0; i < nodes.size(); i++) {
        WaveEmitter *emitter = Object::cast_to<WaveEmitter>(nodes[i]);
        if (emitter) {
            emitter->emit_burst(8);
        }
    }
}
```

与 GDScript 插件的关键差异在于**注册与激活方式**。GDScript 插件靠 `plugin.cfg` + 项目设置里的开关；C++ 的 EditorPlugin 则需要在注册后手动加入编辑器的插件列表：

```cpp
#include <godot_cpp/classes/editor_plugin_registration.hpp>

void initialize_wave_module(ModuleInitializationLevel p_level) {
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        GDREGISTER_CLASS(WaveEmitterEditorPlugin);
        // 将插件类注册到编辑器（插件随编辑器启动即激活）
        EditorPlugins::add_by_type<WaveEmitterEditorPlugin>();
    }
}

void uninitialize_wave_module(ModuleInitializationLevel p_level) {
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        EditorPlugins::remove_by_type<WaveEmitterEditorPlugin>();
    }
}
```

常用的 EditorPlugin 虚函数与辅助方法：

- `_enter_tree()` / `_exit_tree()`：插件启用/禁用；
- `add_control_to_container()` / `remove_control_from_container()`：向编辑器各区域注入 UI；
- `add_custom_type()` / `remove_custom_type()`：为类型注册带图标的「创建节点」条目；
- `_handles(object)` + `_edit(object)`：接管某类对象的编辑（自定义主屏插件的核心）；
- `EditorInterface::get_singleton()`：访问选区、文件系统、编辑中的场景根等编辑器状态。

### 5.4 EditorExportPlugin：导出期干预

`EditorExportPlugin` 让你在导出项目时注入自定义逻辑——添加文件、修改资源、按平台裁剪内容：

```cpp
// wave_export_plugin.h / .cpp（节选）
class WaveExportPlugin : public EditorExportPlugin {
    GDCLASS(WaveExportPlugin, EditorExportPlugin)

protected:
    static void _bind_methods() {}

public:
    // 导出开始时回调，可在此读取导出预设信息
    void _export_begin(const PackedStringArray &features, bool is_debug,
                       const String &path, uint32_t flags) override {
        UtilityFunctions::print("导出开始，平台特性: ", features);
    }

    // 每个被导出的文件都会经过这里
    void _export_file(const String &path, const String &type,
                      const PackedStringArray &features) override {
        // 示例：导出 release 包时跳过调试配置资源
        if (!get_export_preset().is_null() && path.ends_with(".debug.tres")) {
            skip();  // 该文件不进入导出包
        }
    }
};
```

在 EditorPlugin 中挂载：

```cpp
void WaveEmitterEditorPlugin::_enter_tree() {
    // ... 工具栏按钮 ...
    export_plugin.instantiate();          // export_plugin 为 Ref<WaveExportPlugin>
    add_export_plugin(export_plugin);
}

void WaveEmitterEditorPlugin::_exit_tree() {
    remove_export_plugin(export_plugin);
    export_plugin.unref();
    // ...
}
```

`_export_file` 中可调用的干预方法包括 `skip()`（跳过文件）、`add_file(path, data, remap)`（注入额外文件）、`add_shared_object()` 等。常见用途：按导出平台裁剪 GDExtension 依赖、注入授权文件、对特定资源做后处理。

---

## 6. 调试技巧

### 6.1 构建可调试的二进制

调试的前提是带符号的 debug 构建。godot-cpp 的 SCons 目标对应关系：

```bash
# Debug 构建：带调试符号、无优化，对应引擎的 template_debug
scons platform=windows target=template_debug dev_build=yes

# Release 构建：优化，对应 template_release
scons platform=windows target=template_release
```

`dev_build=yes` 进一步开启 godot-cpp 的调试检查（如绑定一致性断言），开发期建议常开。注意 `.gdextension` 文件中 `debug`/`release` 键与构建产物的对应关系必须一致——编辑器以 debug 配置运行时加载 `*.debug.*` 条目。

### 6.2 C++ 断点调试

**核心思路：调试器附加到 Godot 编辑器进程**。GDExtension 是被编辑器（或游戏进程）动态加载的共享库，断点打在扩展代码里，由宿主进程触发。

**Visual Studio（Windows）**：

1. 用 debug 配置构建扩展（生成 `.pdb` 符号文件；MSVC 构建时确保未关闭 `/Zi`）。
2. 打开 Godot 编辑器加载你的项目。
3. `调试 → 附加到进程`（Ctrl+Alt+P），选择 `Godot_v4.x-stable_win64.exe`。
4. 在 `wave_emitter.cpp` 中打断点，在编辑器里触发对应操作（如运行场景），断点命中。

也可以反过来：在 VS 中把调试启动命令设为 Godot 可执行文件、参数设为 `--editor --path <项目路径>`，F5 直接启动编辑器调试。

**gdb / lldb（Linux / macOS）**：

```bash
# 直接以调试器启动编辑器
gdb --args godot --editor --path /path/to/project

# 或附加到已运行的编辑器
gdb -p $(pidof godot)
```

lldb（macOS）同理：`lldb -- godot --editor --path ...`。动态库加载后符号自动可用；若断点显示为 pending，确认扩展二进制确实是 debug 构建且路径与 `.gdextension` 中一致。

### 6.3 与编辑器联调的实用技巧

- **`reloadable = true`**：`.gdextension` 中开启后，编辑器检测到库文件更新会自动热重载扩展（需要 debug 构建），免重启编辑器。重载时已存在的实例保留，但 C++ 侧对象内存布局变化可能导致状态错乱，涉及成员变量增减时仍建议重启。
- **日志分级**：`UtilityFunctions::print()` 走引擎输出面板；`push_warning()` / `push_error()` 会进入调试器面板并带堆栈，优先于 `printf`。
- **命令行参数**：启动编辑器加 `--verbose` 可看到 GDExtension 加载细节（哪个库文件被加载、入口符号解析结果），排查「扩展没生效」类问题的第一步。
- **断言而非崩溃**：对外部输入（脚本传来的参数、加载的资源）用 `ERR_FAIL_NULL_V`、`ERR_FAIL_COND_V` 宏做防御——它们按 Godot 风格打印错误并优雅返回，而不是让编辑器整个崩溃：

```cpp
#include <godot_cpp/core/error_macros.hpp>

void WaveEmitter::apply_preset_to(WaveEmitter *p_target) {
    ERR_FAIL_NULL(p_target);  // 等价于 if (!p_target) { 报错; return; }
    ERR_FAIL_COND(preset.is_null());
    p_target->set_preset(preset);
}
```

---

## 7. 多平台编译与打包分发

### 7.1 目标矩阵

一个可发布的 GDExtension 通常需要覆盖以下构建组合：

```
┌──────────────────────────────────────────────────────────────────┐
│                        构建目标矩阵                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│              template_debug          template_release            │
│            ┌─────────────────────┬─────────────────────┐         │
│  Windows   │ x86_64 (MSVC/MinGW) │ x86_64              │         │
│            ├─────────────────────┼─────────────────────┤         │
│  Linux     │ x86_64              │ x86_64              │         │
│            ├─────────────────────┼─────────────────────┤         │
│  macOS     │ universal (arm64 +  │ universal           │         │
│            │ x86_64 → .framework)│                     │         │
│            ├─────────────────────┼─────────────────────┤         │
│  Android   │ arm64 / x86_64 .so  │ arm64 / x86_64      │         │
│            ├─────────────────────┼─────────────────────┤         │
│  iOS       │ .xcframework        │ .xcframework        │         │
│            └─────────────────────┴─────────────────────┘         │
│                                                                  │
│  godot-cpp 版本必须与目标 Godot 小版本分支匹配（4.1 / 4.2 ...）  │
└──────────────────────────────────────────────────────────────────┘
```

各平台构建命令：

```bash
# Windows（在装了 MSVC 或 MinGW 的机器上）
scons platform=windows target=template_debug arch=x86_64
scons platform=windows target=template_release arch=x86_64

# Linux
scons platform=linux target=template_release arch=x86_64

# macOS：分别构建两个架构，再合成 universal
scons platform=macos target=template_release arch=arm64
scons platform=macos target=template_release arch=x86_64
# godot-cpp 的 SConstruct 通常直接支持 universal 框架打包，
# 或用 lipo 手动合成后放进 .framework 目录结构
```

**交叉编译的现实**：Windows → MinGW 可以在 Linux 上交叉编译；Linux 目标最省事的方式是 Docker/Ubuntu 容器；macOS 与 iOS **必须**在 macOS + Xcode 环境构建（无法交叉）。这正是 CI 矩阵存在的意义（见 7.3）。

### 7.2 .gdextension 文件：多平台清单

`.gdextension` 文件是扩展的分发清单，Godot 按当前平台、架构、debug/release 精确匹配条目，并且**导出游戏时只打包匹配目标平台的库**：

```ini
[configuration]

entry_symbol = "wave_library_init"
compatibility_minimum = "4.1"
reloadable = true

[libraries]

windows.debug.x86_64   = "res://addons/wave/bin/libwave.windows.template_debug.x86_64.dll"
windows.release.x86_64 = "res://addons/wave/bin/libwave.windows.template_release.x86_64.dll"
linux.debug.x86_64     = "res://addons/wave/bin/libwave.linux.template_debug.x86_64.so"
linux.release.x86_64   = "res://addons/wave/bin/libwave.linux.template_release.x86_64.so"
macos.debug            = "res://addons/wave/bin/libwave.macos.template_debug.framework"
macos.release          = "res://addons/wave/bin/libwave.macos.template_release.framework"

[dependencies]

; 第三方动态库依赖：导出时随扩展一起打包
; windows.release.x86_64 = { "res://addons/wave/bin/thirdparty.dll" : "" }
```

要点：

- `compatibility_minimum` 防止过旧版本的 Godot 加载你的扩展（版本不兼容会崩溃，不如优雅拒绝）。GDExtension 的兼容承诺是**向后兼容**：针对 4.1 构建的扩展可在 4.2+ 运行，反之不行。
- 键的格式为 `<platform>.<debug|release>[.<arch>]`；macOS 因使用 universal 二进制通常不写架构段。
- 路径必须以 `res://` 开头，指向项目内位置——这也是 AssetLib 分发的布局基础。

### 7.3 CI 构建（GitHub Actions）

跨平台构建的标准做法是用 CI 矩阵在三套 runner 上并行构建：

```yaml
# .github/workflows/build.yml
name: Build GDExtension

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - { os: windows-latest, platform: windows, arch: x86_64 }
          - { os: ubuntu-latest,  platform: linux,   arch: x86_64 }
          - { os: macos-latest,   platform: macos,   arch: universal }

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive   # godot-cpp 作为子模块拉取

      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: 安装 SCons
        run: pip install scons

      - name: 构建（debug + release）
        run: |
          scons platform=${{ matrix.platform }} arch=${{ matrix.arch }} target=template_debug
          scons platform=${{ matrix.platform }} arch=${{ matrix.arch }} target=template_release

      - name: 上传产物
        uses: actions/upload-artifact@v4
        with:
          name: wave-${{ matrix.platform }}
          path: |
            demo/bin/**/*${{ matrix.platform }}*
            demo/bin/*.gdextension
```

发布阶段再聚合三个平台的 artifact 打成一个 zip。要点：

- `submodules: recursive` 别忘了，否则 godot-cpp 是空目录；
- macOS runner 上构建 universal 时 godot-cpp 与扩展都要用 `arch=universal`；
- 版本号注入：用 tag 名生成 `.gdextension` 旁边的版本说明，或在 SConstruct 中读取环境变量定义宏。

### 7.4 分发：zip 打包与 Asset Library

GDExtension 是纯文件分发，没有编译步骤，打包即是把产物按约定布局压缩：

```
wave-plugin.zip
└── addons/
    └── wave/
        ├── wave.gdextension          # 分发清单
        ├── bin/
        │   ├── libwave.windows.template_debug.x86_64.dll
        │   ├── libwave.windows.template_release.x86_64.dll
        │   ├── libwave.linux.template_debug.x86_64.so
        │   ├── libwave.linux.template_release.x86_64.so
        │   ├── libwave.macos.template_debug.framework/...
        │   └── libwave.macos.template_release.framework/...
        ├── icons/
        │   └── wave_emitter.svg      # 节点图标（见下）
        └── README.md
```

**节点图标**：GDExtension 注册的类型会自动出现在「创建节点」对话框中。若要为类型挂自定义图标，常见做法是随插件附带一个轻量的 `plugin.cfg` + GDScript `EditorPlugin` 壳，只做 `add_custom_type` 注册这一件事，重逻辑仍留在 C++：

```gdscript
# addons/wave/plugin.gd —— 仅负责图标注册的编辑器壳
@tool
extends EditorPlugin

func _enter_tree() -> void:
    var icon := preload("res://addons/wave/icons/wave_emitter.svg")
    # add_custom_type 需要 Script 参数，因此用极简 GDScript 类承接图标展示
    add_custom_type("WaveEmitter", "Node2D", preload("res://addons/wave/wave_emitter_alias.gd"), icon)

func _exit_tree() -> void:
    remove_custom_type("WaveEmitter")
```

> **说明**：`add_custom_type` 的第三个参数要求一个 `Script` 对象，无法直接指向 GDExtension 注册的原生类，因此「GDScript 壳 + C++ 实现」是当前版本下为原生类型挂图标的务实方案。随引擎版本演进请关注官方文档的变化。

发布到 **Godot Asset Library** 的清单：

1. GitHub 公开仓库，release 中上传上述 zip；
2. 仓库根包含 `LICENSE`（AssetLib 要求明确许可证，常用 MIT）；
3. 在 AssetLib 提交页填写仓库地址、下载 zip 的 release 链接、Godot 版本（4.1+）、分类（Scripts/Tools）；
4. `.gdextension` 中 `compatibility_minimum` 如实填写——用户版本不符时引擎会拒绝加载并提示；
5. 提供最小示例场景（demo 目录可标记为不随插件安装）。

整个分发流水线：

```
┌──────────────────────────────────────────────────────────────────┐
│                     发布流水线                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  git tag v1.0.0                                                  │
│      │                                                           │
│      ▼                                                           │
│  CI 矩阵构建（win / linux / macos × debug / release）            │
│      │                                                           │
│      ▼                                                           │
│  聚合 artifacts ──► 按 addons/wave/ 布局打包 wave-plugin.zip     │
│      │                                                           │
│      ▼                                                           │
│  GitHub Release（zip + sha256 校验和）                            │
│      │                                                           │
│      ▼                                                           │
│  Asset Library 提交审核 ──► 用户编辑器内一键下载安装              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📝 本章总结

### 核心要点

1. **MethodBind 是一切绑定的核心**，`bind_method` 在编译期生成 Variant 编解码模板，跨语言调用有固定开销，热路径应设计批量接口
2. **属性系统三件套**（PropertyInfo + ADD_PROPERTY + ADD_GROUP）配合 `PROPERTY_HINT_*` 提示，可实现与 GDScript `@export` 完全等价的检查器体验
3. **虚函数覆写签名必须精确**，`_notification` 不是虚函数；工具类（@tool 等价物）= `GDREGISTER_CLASS` + `Engine::is_editor_hint()` 环境判断
4. **类型互操作的关键是所有权**：RefCounted 用 `Ref<T>`，Node 用裸指针交给场景树，标识符一律缓存为 `StringName`
5. **Resource 子类是结构化数据的最佳载体**，序列化、编辑器编辑、缓存全部由引擎免费托管
6. **编辑器集成覆盖三个层级**：注册层级控制加载时机，EditorPlugin 注入 UI，EditorExportPlugin 干预导出
7. **调试 = debug 构建 + 附加宿主进程**；分发 = `.gdextension` 清单 + CI 矩阵 + AssetLib

### 关键术语

| 术语 | 解释 |
|------|------|
| MethodBind | 引擎统一的方法描述符，负责 Variant 与 C++ 类型间的编解码 |
| D_METHOD | 构造方法元信息（名称 + 参数名）的宏 |
| PropertyInfo | 属性描述结构：类型、名称、提示、usage 标志 |
| PROPERTY_HINT_RANGE / ENUM | 属性提示，决定检查器控件形态 |
| ADD_GROUP | 属性分组，对应 @export_group |
| VARIANT_ENUM_CAST | 让 C++ 枚举参与 Variant 转换的宏，必须紧跟类声明 |
| StringName | 全局驻留字符串，O(1) 比较，用于一切标识符 |
| Ref\<T\> | RefCounted 派生对象的智能指针，自动引用计数 |
| GDREGISTER_CLASS | 注册编辑器可用的工具类（@tool 等价物） |
| GDREGISTER_RUNTIME_CLASS | 注册仅运行时可用的类 |
| EditorPlugin | 编辑器插件基类，可注入 UI、注册自定义类型 |
| EditorExportPlugin | 导出插件，导出项目时干预文件与资源 |
| .gdextension | GDExtension 分发清单文件：入口符号、平台库表、依赖 |
| reloadable | 允许编辑器热重载扩展库的开关（需 debug 构建） |

---

## 🔗 延伸阅读

- **官方文档**: [What is GDExtension?](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/what_is_gdextension.html)
- **官方文档**: [GDExtension C++ example](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/gdextension_cpp_example.html)
- **官方文档**: [Extending Godot with C++（模块与 GDExtension 总览）](https://docs.godotengine.org/en/latest/engine_details/engine_api/index.html)
- **源码位置**: `core/object/class_db.cpp`（ClassDB 与 MethodBind）、`godot-cpp/include/godot_cpp/core/class_db.hpp`（绑定模板）、`godot-cpp/include/godot_cpp/classes/editor_plugin_registration.hpp`
- **绑定仓库**: [godotengine/godot-cpp](https://github.com/godotengine/godot-cpp)

---

## 📋 下一章预告

**第 35 篇：GDExtension 与外部库集成**

- 链接第三方 C/C++ 库（静态/动态）
- dependencies 配置与跨平台依赖打包
- 外部库与 Godot 类型的桥接层设计
- 许可证与合规注意事项

---

*写作时间：2026-08-27*  
*字数：约 15,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-08-27 19:30*
