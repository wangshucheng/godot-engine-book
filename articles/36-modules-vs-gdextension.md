# 第 36 篇：自定义模块 vs GDExtension 选型与实战

> **本卷定位**: 引擎扩展开发卷  
> **前置知识**: C++ 基础、SCons 构建（建议先读本卷前几篇）  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家

---

## 📖 本章导读

Godot 4.x 提供了两条原生扩展路线：**自定义模块（Custom Module）** 和 **GDExtension**。前者是随引擎源码一起静态编译的传统方式，与引擎内部 API 完全互通；后者是 Godot 4.0 引入的运行时动态库机制，无需重编译引擎即可获得接近模块的扩展能力。两条路线并非互相替代，而是各有适用边界。本章先给出全景对比和决策流程图，再通过两个完整实战案例（GDExtension 集成第三方音频库、自定义模块注册自定义资源加载器）演示两条路线的工程细节，最后讨论混合架构、ABI 兼容性与团队协作等落地问题。这是本卷的最后一篇，文末将对整卷内容做收束总结。

---

## 🎯 学习目标

- 理解自定义模块与 GDExtension 在编译方式、API 覆盖面、版本兼容性上的本质差异
- 掌握选型决策矩阵，能为具体需求快速选定扩展路线
- 学会用 godot-cpp 编写 GDExtension 并集成第三方 C/C++ 库
- 学会编写自定义模块，注册自定义 ResourceFormatLoader
- 掌握「模块 + GDExtension」共存的分层架构
- 了解 ABI 兼容、引擎升级维护成本与团队协作的最佳实践

---

## 1. 两条扩展路线的全景对比

### 1.1 两条路线的本质

**自定义模块**是放在引擎源码树 `modules/` 目录下（或通过 `custom_modules` 选项指定的外部目录）、随引擎一起用 SCons 静态编译进可执行文件的 C++ 代码。引擎自带的 GDScript、GridMap、正则表达式等功能本身就是模块——模块机制是 Godot 组织自身代码的方式，自定义模块享受的是「与引擎平起平坐」的地位。

**GDExtension**是 Godot 4.x 引入的运行时扩展机制：引擎在启动时加载一个动态链接库（Windows 上是 `.dll`，Linux 上是 `.so`，macOS 上是 `.framework`），通过一套稳定的 C 接口与引擎通信。GDExtension 由三个要素构成：

- `gdextension_interface.h`：Godot 与扩展之间通信用的 C 函数集
- `extension_api.json`：引擎暴露给扩展的 API 清单（由 `godot --dump-extension-api` 生成）
- `*.gdextension` 文件：告诉引擎每个平台加载哪个动态库、入口符号是什么

绝大多数开发者不会直接操作这套 C 接口，而是使用现成的语言绑定，最常用的是官方的 **godot-cpp**。

### 1.2 架构对比图

```
两条扩展路线在引擎中的位置:
┌──────────────────────────────────────────────────────────────────┐
│                        Godot 可执行文件                          │
│                                                                  │
│  路线 A：自定义模块（静态编译进引擎）                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  core/  servers/  scene/  editor/  modules/summator/  ←──┼──┼── 你的代码
│  │       ▲ 直接 include 引擎头文件，调用任意内部 API          │  │
│  │       │ 编译产物：godot.exe（引擎 + 模块一体）             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  路线 B：GDExtension（运行时加载的动态库）                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Godot 引擎（官方二进制即可，无需重编译）                  │  │
│  │      │                                                     │  │
│  │      │ gdextension_interface.h（C ABI，稳定边界）         │  │
│  │      ▼                                                     │  │
│  │  libmyext.dll / .so  ←── godot-cpp（C++ 绑定层） ←── 你的代码 │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 五维对比表

| 维度 | 自定义模块 | GDExtension |
|------|-----------|-------------|
| **编译方式** | 与引擎一起静态编译，改动代码需重编译引擎 | 独立编译为动态库，引擎用官方二进制 |
| **API 覆盖面** | 全部内部 API：core、servers、editor、platform 任何头文件 | 仅限 `extension_api.json` 暴露的公开 API |
| **版本兼容性** | 与引擎版本强绑定，升级引擎可能要改代码 | 面向旧版本构建的扩展可在更高小版本运行（官方长期目标，4.0→4.1 曾破例） |
| **分发方式** | 必须分发整个定制引擎 + 全部导出模板 | 只分发动态库 + `.gdextension` 文件，用户放进项目即可 |
| **性能** | 零开销，直接函数调用，可内联 | 跨 ABI 边界有少量调用开销，热点路径可忽略，但高频小调用需留意 |

关于性能需要说一句公道话：GDExtension 的调用开销是一次通过 C 函数指针的间接跳转加参数装箱，量级在纳秒级。只有当你每帧调用数万次小函数（例如逐粒子回调脚本层）时才需要认真测量；把批量数据留在 C++ 一侧处理、用一次调用传数组，是两边通用的优化手法。

### 1.4 选型决策流程图

```
                         需要扩展 Godot？
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
        需要访问引擎内部 API？          只是集成第三方库 / 加速热点代码？
        （未导出到 ClassDB 的           （物理、音频、网络 SDK 等）
         core/servers/editor 内部）
                │                             │
           是 ──┤                             ├── 是
                ▼                             ▼
        ┌───────────────┐            需要频繁迭代、不想重编译引擎？
        │  自定义模块   │                    │
        └───────────────┘             是 ────┤
                │                            ▼
                │                   ┌─────────────────┐
                ▼                   │   GDExtension   │
        需要深度改编辑器 UI /       └─────────────────┘
        注册引擎级单例 / 改渲染？          │
                │                   特例：目标平台不允许动态库
           是 ──┤                   （如部分主机 SDK）→ 回到模块
                ▼
        ┌───────────────┐
        │  自定义模块   │ ──→ 同时需要分发便利性？
        └───────────────┘      考虑第 5 节的混合架构
```

一个快速心算口诀：**「能用 GDExtension 就不用模块」**。官方文档也明确写道：虽然可以用模块写游戏逻辑，但 GDExtension 通常更合适，因为它不需要每次改代码都重编译引擎；只有当 GDExtension 不够用、需要更深的引擎集成时，模块才是必需品。

---

## 2. 选型决策矩阵

### 2.1 何时用 GDExtension

以下四个典型场景，GDExtension 是压倒性的正确选择：

**场景一：第三方库集成。** 这是官方文档列举的头号用途之一——把 PhysX、FMOD、各类 SDK 绑定给 Godot 用。第三方库本身是编译好的二进制，GDExtension 的动态库形态与之天然契合：你编译一个 `.dll` 把第三方库包进去，项目里放一个 `.gdextension` 文件就完工。用户不需要会编译引擎。

**场景二：不改动引擎。** 团队没有引擎程序员、不想维护引擎 fork、希望随时升级到官方新版本编辑器——GDExtension 让你完全停留在「引擎用户」的身份上。

**场景三：快速迭代。** GDExtension 编译一次通常以秒计（只编译你自己的代码 + 增量链接），而重编译引擎是以十分钟计的。配合 `.gdextension` 文件中的 `reloadable = true`，调试构建下编辑器还能在重新编译后自动热重载扩展，无需重启编辑器。

**场景四：跨版本兼容分发。** 官方的长期目标是：面向 Godot 4.x 旧小版本构建的 GDExtension 可以在更高小版本上运行（例如面向 4.1 构建的扩展可在 4.2 运行，反之不行）。这意味着你发布的插件可以服务一个版本区间的用户，而不是锁死某个精确版本。需要注意 GDExtension 仍带有实验性质，官方保留为修复重大问题而破坏兼容的权利——4.0 构建的扩展就无法在 4.1 上运行，升级时需要按官方迁移指南调整。

### 2.2 何时用自定义模块

以下场景，模块是无可替代的选择：

**场景一：需要引擎内部 API。** GDExtension 只能看到 `extension_api.json` 里导出的类和方法。凡是没导出到 ClassDB 的东西——例如直接操作 `RenderingServer` 的内部实现类、访问 `core/os` 里的平台原语、改动物理服务器的步进逻辑——只有模块做得到。判断方法很简单：打开 `extension_api.json` 搜你要用的类名和方法名，搜不到，就走模块。

**场景二：编辑器深度集成。** 要往编辑器里加全新的 dock、改主循环、注册自定义导入器（EditorImportPlugin 级别的深度）、给资源系统加新的格式加载器（ResourceFormatLoader），这些需要在引擎启动早期就介入的能力，模块的 `MODULE_INITIALIZATION_LEVEL_*` 分级注册机制（core / servers / scene / editor）提供了精确的挂载点。GDExtension 也有初始化级别概念，但能碰到的编辑器内部面仍然受公开 API 限制。

**场景三：平台特定优化与定制端口。** 主机平台（需要厂商 SDK 和静态链接）、嵌入式平台、给引擎加自定义平台端口（Custom platform ports）——这些场景动态库机制本身就不存在或不被允许，只能静态编译。

**场景四：发布定制引擎。** 你的商业模式就是交付一个「XX 行业定制版 Godot」，里面预装了你们的一整套功能。这时模块随引擎分发的特性不是缺点而是优点：用户拿到的是一个开箱即用的整体。

### 2.3 决策矩阵速查表

| 需求特征 | GDExtension | 自定义模块 |
|---------|:-----------:|:---------:|
| 集成第三方闭源 SDK | ✅ 首选 | 可以 |
| 游戏热点代码 C++ 化 | ✅ 首选 | 可以 |
| 不重编译引擎 | ✅ | ❌ |
| 编辑器里热重载 | ✅（debug 构建） | ❌ |
| 访问未导出的内部 API | ❌ | ✅ 必须 |
| 注册自定义资源格式加载器 | ⚠️ 受公开 API 限制 | ✅ 首选 |
| 深度定制编辑器 | ⚠️ 受公开 API 限制 | ✅ 首选 |
| 主机 / 静态链接平台 | ❌ | ✅ 必须 |
| 分发给不懂编译的用户 | ✅ | ❌（需分发整引擎） |
| 跨引擎小版本兼容 | ✅（有约束） | ❌ |

---

## 3. 实战案例一：用 GDExtension 集成第三方音频库

假设我们要把一个第三方音频引擎（这里以虚构的 `libsoundfx` 为例，其 API 为示意性质，真实项目中替换为 FMOD、miniaudio 等库的实际调用即可）封装成 Godot 节点，让 GDScript 能像用普通节点一样播放带 DSP 效果的音频。

### 3.1 工程结构

```
audio_fx_ext/
├── godot-cpp/                # godot-cpp 绑定（git submodule，分支与目标引擎版本对应）
├── thirdparty/
│   └── libsoundfx/           # 第三方库：头文件 + 预编译二进制
│       ├── include/soundfx.h
│       └── lib/
├── src/
│   ├── audio_fx_player.h     # 我们封装的节点
│   ├── audio_fx_player.cpp
│   ├── register_types.h      # 扩展入口
│   └── register_types.cpp
├── SConstruct                # 构建脚本
└── demo/
    └── bin/
        └── audio_fx.gdextension   # 引擎加载描述文件
```

准备工作与官方教程一致：克隆 godot-cpp（**分支必须对应目标引擎版本**，例如面向 Godot 4.3 就用 `4.3` 分支），先构建一次绑定库：

```bash
git submodule add -b 4.3 https://github.com/godotengine/godot-cpp
cd godot-cpp
scons platform=windows -j8      # 生成 godot-cpp/bin/ 下的静态库
cd ..
```

如需比 godot-cpp 自带元数据更新的 API，可运行 `godot --dump-extension-api` 生成 `extension_api.json`，再以 `custom_api_file=<路径>` 传给 SCons。

### 3.2 封装节点：audio_fx_player.h

```cpp
#ifndef AUDIO_FX_PLAYER_H
#define AUDIO_FX_PLAYER_H

#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/audio_stream.hpp>

namespace godot {

// 封装第三方音频引擎的播放器节点
class AudioFXPlayer : public Node {
    GDCLASS(AudioFXPlayer, Node)

private:
    // 第三方引擎的实例句柄（libsoundfx 为 C 接口，用不透明指针）
    void *sfx_handle = nullptr;
    bool playing = false;
    float volume = 1.0f;

    void _ensure_engine();      // 惰性初始化第三方引擎
    void _shutdown_engine();    // 释放资源

protected:
    static void _bind_methods();
    void _notification(int p_what);

public:
    AudioFXPlayer();
    ~AudioFXPlayer();

    void play_stream(const Ref<AudioStream> &p_stream);
    void stop();
    bool is_playing() const;

    void set_volume(float p_volume);
    float get_volume() const;
};

} // namespace godot

#endif // AUDIO_FX_PLAYER_H
```

几个要点：

- 所有 godot-cpp 代码都在 `namespace godot` 中；`GDCLASS` 宏与模块写法相同，负责注册所需的内部样板。
- 第三方引擎的句柄用不透明指针保存，**避免在头文件里直接 include 第三方库的头**，这样 Godot 侧的头文件保持干净，编译依赖清晰。

### 3.3 实现：audio_fx_player.cpp

```cpp
#include "audio_fx_player.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/classes/audio_stream_wav.hpp>

// 第三方库头文件只在 .cpp 中引入（示意 API，替换为真实库调用）
#include "soundfx.h"

using namespace godot;

void AudioFXPlayer::_bind_methods() {
    ClassDB::bind_method(D_METHOD("play_stream", "stream"), &AudioFXPlayer::play_stream);
    ClassDB::bind_method(D_METHOD("stop"), &AudioFXPlayer::stop);
    ClassDB::bind_method(D_METHOD("is_playing"), &AudioFXPlayer::is_playing);
    ClassDB::bind_method(D_METHOD("set_volume", "volume"), &AudioFXPlayer::set_volume);
    ClassDB::bind_method(D_METHOD("get_volume"), &AudioFXPlayer::get_volume);

    // 暴露属性，编辑器检查器中可直接调节，范围 0~2，步长 0.01
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "volume",
            PROPERTY_HINT_RANGE, "0,2,0.01"), "set_volume", "get_volume");

    // 注册一个信号：播放结束时通知脚本层
    ADD_SIGNAL(MethodInfo("playback_finished"));
}

AudioFXPlayer::AudioFXPlayer() {
}

AudioFXPlayer::~AudioFXPlayer() {
    _shutdown_engine();
}

void AudioFXPlayer::_notification(int p_what) {
    switch (p_what) {
        case NOTIFICATION_ENTER_TREE:
            _ensure_engine();
            break;
        case NOTIFICATION_EXIT_TREE:
            _shutdown_engine();
            break;
    }
}

void AudioFXPlayer::_ensure_engine() {
    if (sfx_handle == nullptr) {
        // 示意：sfx_create 为第三方库 API，实际换成对应初始化函数
        sfx_handle = sfx_create(44100, 2);
    }
}

void AudioFXPlayer::_shutdown_engine() {
    if (sfx_handle != nullptr) {
        sfx_destroy(sfx_handle);
        sfx_handle = nullptr;
    }
    playing = false;
}

void AudioFXPlayer::play_stream(const Ref<AudioStream> &p_stream) {
    ERR_FAIL_COND(p_stream.is_null());
    _ensure_engine();

    // 实际项目中：从 AudioStream 取解码后的 PCM 数据（如 AudioStreamWAV::get_data），
    // 交给第三方引擎的解码/混音管线。此处为示意。
    Ref<AudioStreamWAV> wav = p_stream;
    if (wav.is_valid()) {
        PackedByteArray data = wav->get_data();
        sfx_play_pcm(sfx_handle, data.ptr(), data.size(), volume);
        playing = true;
    } else {
        WARN_PRINT("AudioFXPlayer 示例仅处理 AudioStreamWAV");
    }
}

void AudioFXPlayer::stop() {
    if (sfx_handle != nullptr && playing) {
        sfx_stop(sfx_handle);
        playing = false;
        // 通知脚本层播放已结束
        emit_signal("playback_finished");
    }
}

bool AudioFXPlayer::is_playing() const {
    return playing;
}

void AudioFXPlayer::set_volume(float p_volume) {
    volume = CLAMP(p_volume, 0.0f, 2.0f);
    if (sfx_handle != nullptr) {
        sfx_set_volume(sfx_handle, volume);
    }
}

float AudioFXPlayer::get_volume() const {
    return volume;
}
```

### 3.4 入口注册：register_types

GDExtension 与模块一样有 `register_types.cpp`，但入口形态完全不同——模块是被构建系统收集的静态函数，GDExtension 是一个 `extern "C"` 导出符号：

```cpp
// register_types.h
#ifndef AUDIO_FX_REGISTER_TYPES_H
#define AUDIO_FX_REGISTER_TYPES_H

#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void initialize_audio_fx_module(ModuleInitializationLevel p_level);
void uninitialize_audio_fx_module(ModuleInitializationLevel p_level);

#endif
```

```cpp
// register_types.cpp
#include "register_types.h"

#include "audio_fx_player.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_audio_fx_module(ModuleInitializationLevel p_level) {
    // 只在场景级初始化时注册节点类
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 运行时类：游戏中可用（与 GDScript 默认行为一致）
    GDREGISTER_RUNTIME_CLASS(AudioFXPlayer);
}

void uninitialize_audio_fx_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 本例无需清理
}

extern "C" {

// GDExtension 入口：库被加载时由引擎调用
GDExtensionBool GDE_EXPORT audio_fx_library_init(
        GDExtensionInterfaceGetProcAddress p_get_proc_address,
        const GDExtensionClassLibraryPtr p_library,
        GDExtensionInitialization *r_initialization) {

    godot::GDExtensionBinding::InitObject init_obj(
            p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_audio_fx_module);
    init_obj.register_terminator(uninitialize_audio_fx_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}
}
```

### 3.5 构建脚本：SConstruct

```python
#!/usr/bin/env python
import os
import sys

# 引入 godot-cpp 的构建环境（平台、架构、target 等参数全部由它处理）
env = SConscript("godot-cpp/SConstruct")

# 我们的源码与头文件路径
env.Append(CPPPATH=["src/", "thirdparty/libsoundfx/include/"])

# 链接第三方库（按平台选择预编译二进制）
if env["platform"] == "windows":
    env.Append(LIBPATH=["thirdparty/libsoundfx/lib/windows/"])
elif env["platform"] == "linux":
    env.Append(LIBPATH=["thirdparty/libsoundfx/lib/linux/"])
env.Append(LIBS=["soundfx"])

sources = Glob("src/*.cpp")

# 输出到 demo/bin/，命名遵循 <平台>.<target>.<架构> 约定，
# 与 .gdextension 文件中的 [libraries] 键一一对应
if env["platform"] == "macos":
    library = env.SharedLibrary(
        "demo/bin/libaudiofx.{}.{}.framework/libaudiofx.{}.{}".format(
            env["platform"], env["target"], env["platform"], env["target"]),
        source=sources,
    )
else:
    library = env.SharedLibrary(
        "demo/bin/libaudiofx{}{}".format(env["suffix"], env["SHLIBSUFFIX"]),
        source=sources,
    )

Default(library)
```

编译命令（发布构建记得加 `target=template_release`）：

```bash
scons platform=windows target=template_debug -j8
```

### 3.6 加载描述文件：audio_fx.gdextension

```ini
[configuration]

entry_symbol = "audio_fx_library_init"
compatibility_minimum = "4.1"
reloadable = true

[libraries]

windows.debug.x86_64 = "res://bin/libaudiofx.windows.template_debug.x86_64.dll"
windows.release.x86_64 = "res://bin/libaudiofx.windows.template_release.x86_64.dll"
linux.debug.x86_64 = "res://bin/libaudiofx.linux.template_debug.x86_64.so"
linux.release.x86_64 = "res://bin/libaudiofx.linux.template_release.x86_64.so"

[dependencies]

; 第三方动态库随项目一起导出
windows.debug.x86_64 = { "res://bin/soundfx.dll": "" }
windows.release.x86_64 = { "res://bin/soundfx.dll": "" }
```

三个字段值得强调：

- `compatibility_minimum`：声明扩展要求的最低 Godot 版本，防止旧版本引擎误载新扩展。
- `reloadable = true`：debug 构建下，重新编译后编辑器自动热重载扩展，免重启——这是 GDExtension 迭代效率高的关键一环。
- `[dependencies]`：声明随扩展一起打包的第三方动态库，导出项目时引擎只会带出当前平台需要的文件，不会把 Windows 的 `.dll` 塞进 Linux 包。

### 3.7 在 GDScript 中使用

```gdscript
extends Node

func _ready() -> void:
    var player := AudioFXPlayer.new()
    add_child(player)
    player.volume = 0.8
    player.playback_finished.connect(_on_playback_finished)

    var stream := load("res://assets/explosion.wav")
    player.play_stream(stream)

func _on_playback_finished() -> void:
    print("播放结束")
```

至此，一个完整的「第三方库 → GDExtension → 脚本层」链路就打通了。整个过程中我们没有碰过一行引擎源码，用的是官方发布的编辑器二进制。

---

## 4. 实战案例二：用自定义模块注册自定义资源加载器

这个案例做一件 GDExtension 做起来受限的事：给引擎的资源管线添加一种全新的文件格式。我们假设游戏使用一种自定义的二进制地图格式 `.bmap`（示意格式），目标是让 `ResourceLoader::load("res://maps/level1.bmap")` 和 GDScript 的 `load()` 直接返回一个 `Resource`，就像引擎原生支持这种格式一样。

### 4.1 模块目录与最小骨架

在引擎源码的 `modules/` 下创建 `bmap` 目录（或者用外部目录 + `scons custom_modules=<路径>`，见 4.6 节）：

```
godot/modules/bmap/
├── config.py             # 模块配置：能否构建、文档路径
├── SCsub                 # 构建脚本
├── register_types.h      # 注册入口（必须在模块顶层）
├── register_types.cpp
├── bmap_resource.h       # 自定义 Resource：承载地图数据
├── bmap_resource.cpp
├── resource_loader_bmap.h   # 自定义 ResourceFormatLoader
└── resource_loader_bmap.cpp
```

### 4.2 自定义资源类型

```cpp
// bmap_resource.h
#pragma once

#include "core/io/resource.h"

// 承载 .bmap 文件解码后的数据
class BMapResource : public Resource {
    GDCLASS(BMapResource, Resource);

    int width = 0;
    int height = 0;
    Vector<int> tiles;      // 按行存储的瓦片索引

protected:
    static void _bind_methods();

public:
    void set_size(int p_width, int p_height);
    int get_width() const;
    int get_height() const;

    void set_tiles(const Vector<int> &p_tiles);
    Vector<int> get_tiles() const;

    BMapResource();
};
```

```cpp
// bmap_resource.cpp
#include "bmap_resource.h"

void BMapResource::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_size", "width", "height"), &BMapResource::set_size);
    ClassDB::bind_method(D_METHOD("get_width"), &BMapResource::get_width);
    ClassDB::bind_method(D_METHOD("get_height"), &BMapResource::get_height);
    ClassDB::bind_method(D_METHOD("set_tiles", "tiles"), &BMapResource::set_tiles);
    ClassDB::bind_method(D_METHOD("get_tiles"), &BMapResource::get_tiles);

    ADD_PROPERTY(PropertyInfo(Variant::INT, "width"), "", "get_width");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "height"), "", "get_height");
}

void BMapResource::set_size(int p_width, int p_height) {
    width = p_width;
    height = p_height;
    tiles.resize(width * height);
}

int BMapResource::get_width() const { return width; }
int BMapResource::get_height() const { return height; }

void BMapResource::set_tiles(const Vector<int> &p_tiles) { tiles = p_tiles; }
Vector<int> BMapResource::get_tiles() const { return tiles; }

BMapResource::BMapResource() {
}
```

### 4.3 自定义 ResourceFormatLoader

`ResourceFormatLoader` 是资源管线的扩展点。引擎加载资源时遍历所有已注册的 loader，按扩展名和类型匹配找到能处理该文件的 loader。我们需要实现四个核心虚函数：

```cpp
// resource_loader_bmap.h
#pragma once

#include "core/io/resource_loader.h"

class ResourceFormatLoaderBMap : public ResourceFormatLoader {
public:
    // 实际加载：读取文件、解码、返回 Resource
    virtual Ref<Resource> load(const String &p_path,
            const String &p_original_path = "",
            Error *r_error = nullptr,
            bool p_use_sub_threads = false,
            float *r_progress = nullptr,
            CacheMode p_cache_mode = CACHE_MODE_REUSE) override;

    // 声明本 loader 能识别的扩展名
    virtual void get_recognized_extensions(List<String> *p_extensions) const override;

    // 声明本 loader 能产出什么类型
    virtual bool handles_type(const String &p_type) const override;

    // 根据路径推断资源类型（编辑器做类型提示用）
    virtual String get_resource_type(const String &p_path) const override;
};
```

```cpp
// resource_loader_bmap.cpp
#include "resource_loader_bmap.h"

#include "bmap_resource.h"
#include "core/io/file_access.h"

Ref<Resource> ResourceFormatLoaderBMap::load(const String &p_path,
        const String &p_original_path, Error *r_error,
        bool p_use_sub_threads, float *r_progress, CacheMode p_cache_mode) {

    Ref<FileAccess> f = FileAccess::open(p_path, FileAccess::READ);
    if (f.is_null()) {
        if (r_error) {
            *r_error = ERR_CANT_OPEN;
        }
        return Ref<Resource>();
    }

    // 示意格式：4 字节 magic "BMAP"，随后两个 uint32 宽高，再是 int32 瓦片数组
    uint32_t magic = f->get_32();
    ERR_FAIL_COND_V_MSG(magic != 0x50414D42, Ref<Resource>(),
            "不是合法的 .bmap 文件: " + p_path);  // "BMAP" 小端

    Ref<BMapResource> bmap;
    bmap.instantiate();

    int w = (int)f->get_32();
    int h = (int)f->get_32();
    bmap->set_size(w, h);

    Vector<int> tiles;
    tiles.resize(w * h);
    for (int i = 0; i < w * h; i++) {
        tiles.write[i] = (int)f->get_32();
    }
    bmap->set_tiles(tiles);

    if (r_error) {
        *r_error = OK;
    }
    return bmap;
}

void ResourceFormatLoaderBMap::get_recognized_extensions(List<String> *p_extensions) const {
    p_extensions->push_back("bmap");
}

bool ResourceFormatLoaderBMap::handles_type(const String &p_type) const {
    return p_type == "BMapResource" || p_type == "Resource";
}

String ResourceFormatLoaderBMap::get_resource_type(const String &p_path) const {
    String ext = p_path.get_extension().to_lower();
    if (ext == "bmap") {
        return "BMapResource";
    }
    return "";
}
```

### 4.4 注册入口

模块的注册文件必须放在模块顶层目录，函数名中间的单词必须与模块文件夹名一致：

```cpp
// register_types.h
#pragma once

#include "modules/register_module_types.h"

void initialize_bmap_module(ModuleInitializationLevel p_level);
void uninitialize_bmap_module(ModuleInitializationLevel p_level);
```

```cpp
// register_types.cpp
#include "register_types.h"

#include "bmap_resource.h"
#include "resource_loader_bmap.h"

#include "core/io/resource_loader.h"
#include "core/object/class_db.h"

// loader 用 Ref 持有，注册进全局 ResourceLoader
static Ref<ResourceFormatLoaderBMap> bmap_loader;

void initialize_bmap_module(ModuleInitializationLevel p_level) {
    // 资源系统属于场景级，注册在 SCENE 级别
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ClassDB::register_class<BMapResource>();

    bmap_loader.instantiate();
    ResourceLoader::add_resource_format_loader(bmap_loader);
}

void uninitialize_bmap_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ResourceLoader::remove_resource_format_loader(bmap_loader);
    bmap_loader.unref();
}
```

### 4.5 构建配置：SCsub 与 config.py

```python
# SCsub
Import('env')

# 把模块的所有 .cpp 加入引擎构建
env.add_source_files(env.modules_sources, "*.cpp")

# 如需自定义编译选项，先 Clone 环境，避免污染整个引擎构建：
# module_env = env.Clone()
# module_env.Append(CCFLAGS=['-O2'])
```

```python
# config.py
def can_build(env, platform):
    # 本模块纯逻辑解码，所有平台可用
    return True

def configure(env):
    pass

def get_doc_path():
    return "doc_classes"

def get_doc_classes():
    return ["BMapResource"]
```

`get_doc_path()` / `get_doc_classes()` 让模块支持内置文档：在模块下建 `doc_classes/` 目录，运行 `bin/<godot_binary> --doctool .` 生成 XML 模板，填写描述后重编译，编辑器内置帮助里就能查到 `BMapResource` 的文档。

### 4.6 编译与使用

把模块目录放进引擎源码 `modules/` 后正常编译引擎即可；若想模块独立维护（单独的 git 仓库），用外部目录：

```bash
scons platform=windows custom_modules=../my_modules -j8
```

**一个必须记住的警告**（官方文档特别强调）：如果模块要在运行时使用而不只是编辑器，你必须**重新编译每一个要用的导出模板**，并在导出预设里指定自定义模板路径。否则导出后的游戏里没有你的模块代码，运行直接报错。

编译完成后，GDScript 侧的使用与原生格式毫无二致：

```gdscript
func _ready() -> void:
    var map: BMapResource = load("res://maps/level1.bmap")
    print("地图尺寸: ", map.width, "x", map.height)
```

这就是模块路线的威力：你扩展的不是「脚本可见的 API」，而是**资源管线本身**。加载器注册之后，编辑器导入、`load()`、依赖跟踪、缓存全部自动生效。

---

## 5. 混合方案：模块 + GDExtension 共存架构

成熟项目常常两边都要：核心能力做成模块（改引擎、深入内部），面向项目/用户的部分做成 GDExtension（好分发、好迭代）。关键问题是：**两者如何通信？**

答案是模块注册的东西（类、单例）对 GDExtension 同样可见——因为模块走 ClassDB 注册，而 GDExtension 看到的公开 API 就是 ClassDB 的内容。

### 5.1 分层架构图

```
┌──────────────────────────────────────────────────────────────┐
│                         游戏项目                             │
│  ┌────────────────────┐        ┌──────────────────────────┐  │
│  │  GDScript 游戏逻辑 │◄──────►│  GDExtension（动态库）   │  │
│  └────────────────────┘        │  - 项目专属玩法节点       │  │
│            │                   │  - 第三方 SDK 封装        │  │
│            │                   └───────────┬──────────────┘  │
│            │ ClassDB / Engine 单例          │                │
│            ▼                                ▼                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              定制引擎（官方源码 + 自定义模块）         │  │
│  │  模块 A：自定义渲染特性（改 RenderingServer 内部）     │  │
│  │  模块 B：引擎级单例 NetCoreServer（注册到 Engine）     │  │
│  │  模块 C：自定义资源格式加载器                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 通信实例：模块注册单例，GDExtension 调用

模块侧（引擎内），注册一个引擎单例：

```cpp
// modules/netcore/register_types.cpp（节选）
#include "net_core_server.h"
#include "core/config/engine.h"

static NetCoreServer *net_core_singleton = nullptr;

void initialize_netcore_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SERVERS) {
        return;
    }
    ClassDB::register_class<NetCoreServer>();

    net_core_singleton = memnew(NetCoreServer);
    // 注册为引擎单例，脚本与 GDExtension 均可通过名字拿到
    Engine::get_singleton()->register_singleton("NetCoreServer", net_core_singleton);
}

void uninitialize_netcore_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SERVERS) {
        return;
    }
    Engine::get_singleton()->unregister_singleton("NetCoreServer");
    memdelete(net_core_singleton);
}
```

GDExtension 侧（独立动态库），通过 `Engine::get_singleton()` 拿到它：

```cpp
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/object.hpp>

using namespace godot;

void NetClient::connect_to_server(const String &p_url) {
    // 模块注册的单例对 GDExtension 可见
    Object *server = Engine::get_singleton()->get_singleton("NetCoreServer");
    ERR_FAIL_NULL_MSG(server, "NetCoreServer 单例不存在，请确认使用了定制引擎");

    // 通过 ClassDB 暴露的方法跨边界调用（Variant 级别，有少量开销）
    server->call("connect_to", p_url);
}
```

### 5.3 职责划分原则

```
职责划分检查清单:
┌────────────────────────────────────────────────────────────┐
│ 放进模块（引擎层）:                                        │
│   ✓ 修改引擎行为的代码（渲染、物理步进、导入管线）        │
│   ✓ 基础设施级单例（网络核心、日志、平台抽象）            │
│   ✓ 被多个项目复用、改动频率低的代码                       │
│                                                            │
│ 放进 GDExtension（项目层）:                                │
│   ✓ 项目专属玩法节点与资源                                 │
│   ✓ 第三方 SDK 封装（授权可能不允许静态链接进引擎）       │
│   ✓ 改动频率高、需要热重载快速迭代的代码                   │
│                                                            │
│ 划分口诀:                                                  │
│   「改动引擎的进模块，使用引擎的进 GDExtension」          │
└────────────────────────────────────────────────────────────┘
```

---

## 6. 常见坑与最佳实践

### 6.1 ABI 兼容问题

```
ABI 兼容三定律:
┌──────────────────────────────────────────────────────────────┐
│ 1. godot-cpp 分支必须对应目标引擎版本                        │
│    面向 Godot 4.3 就用 godot-cpp 的 4.3 分支。               │
│    用 master 分支构建的扩展不保证能在稳定版引擎上运行。     │
│                                                              │
│ 2. 向后兼容是单向的，且有实验性保留                          │
│    官方长期目标：面向 4.1 构建 → 能在 4.2 运行；反向不行。  │
│    但 GDExtension 仍处实验状态，官方可为大修复破坏兼容——    │
│    4.0 构建的扩展就无法在 4.1 运行，升级需按迁移指南调整。  │
│                                                              │
│ 3. 编译器与 CRT 要匹配                                       │
│    Windows 上用 MSVC 构建的扩展，尽量与官方构建链保持一致； │
│    混用 MinGW/MSVC、Debug/Release CRT 是崩溃的高发来源。    │
└──────────────────────────────────────────────────────────────┘
```

配套工程实践：

- 在 `.gdextension` 中始终设置 `compatibility_minimum`，让版本不匹配时失败得明明白白，而不是神秘崩溃。
- CI 里对每个目标引擎版本跑一次「加载冒烟测试」：无头启动 `godot --headless --quit`，能加载不报错即通过。
- 发布扩展时明确标注「面向 Godot 4.x 构建」，这是用户判断兼容性的唯一依据。

### 6.2 引擎升级维护成本

两条路线的升级成本结构完全不同，这是选型时最容易被低估的因素：

| 维护事项 | 自定义模块 | GDExtension |
|---------|-----------|-------------|
| 引擎升小版本（4.2→4.3） | rebase 你的引擎 fork，解决冲突，全量重编译 | 通常无需动作（向后兼容区间内） |
| 内部 API 变动 | 直接编译错误，逐个修 | 不受影响（公开 API 稳定性高得多） |
| 导出模板 | 每个平台每个模板都要重编译 | 不需要管模板，用官方模板 |
| 团队构建环境 | 每人都要配引擎编译环境 | 只有扩展开发者需要 |

模块路线的真实成本不在「写代码」而在「**长期背着一个引擎 fork**」。给模块团队的一条硬建议：把自定义代码全部隔离在 `modules/` 自己的目录里，**绝不在引擎现有文件中打补丁**——每往引擎本体改一行，未来每次升级就多一处冲突。实在必须改引擎本体时，把改动拆成独立的、带说明的 commit，方便 rebase 时逐条移植。

### 6.3 团队协作流程

一个被验证过的协作模式：

```
推荐团队结构（模块 + GDExtension 混合项目）:
┌────────────────────────────────────────────────────────────┐
│  引擎组（1-2 人）                                          │
│   └─ 维护引擎 fork + 模块，定期 rebase 上游，发布内部      │
│      引擎构建（编辑器 + 各平台模板）给全团队               │
│                                                            │
│  扩展组（若干）                                            │
│   └─ 开发 GDExtension，针对引擎组发布的「内部引擎版本」    │
│      构建；godot-cpp 用 submodule 锁定版本                 │
│                                                            │
│  策划 / 程序（多数）                                       │
│   └─ 只用编辑器 + 已编译扩展，写 GDScript，零 C++ 环境     │
│                                                            │
│  版本对齐规则:                                             │
│   - 引擎版本、godot-cpp 分支、扩展 compatibility_minimum   │
│     三者写入仓库根的 VERSIONS.md，升级时一起改             │
│   - 引擎组发布新构建 → 扩展组 re-tag → CI 重新出全部平台包 │
└────────────────────────────────────────────────────────────┘
```

几个落地细节：

- **godot-cpp 用 git submodule 管理**，并在 CI 中校验 submodule 指向的分支与目标引擎版本一致——这是新手团队最常踩的坑。
- 模块仓库与引擎仓库分离（`custom_modules` 选项就是为此而生），引擎目录保持 pristine，升级引擎 = 换引擎目录，模块原封不动。
- 模块的单测可以随引擎跑：在模块下建 `tests/` 目录，写 `test_*.h`，用 `scons tests=yes` 编译后以 `godot --test --source-file="*test_xxx*" --success` 执行，纳入引擎组的 CI。

### 6.4 其他高频坑

- **忘记重编译导出模板**：模块在编辑器里跑得好好的，导出后报「class not found」——因为官方模板里没有你的模块。模块路线下「编辑器 + N 个平台模板」是一个不可分割的发布单元。
- **GDCLASS 不支持多继承**：暴露给 Godot 的类必须单继承；多继承只能用在纯 C++ 内部类上。
- **GDExtension 中信号回调的方法必须先 bind**：`connect` 一个没在 `_bind_methods()` 里注册的方法会静默失败，排查时先查这里。
- **iOS 需要静态打包**：iOS 上 GDExtension 要编成 `.xcframework`（模拟器 + 真机两个 slice 用 `xcodebuild -create-xcframework` 合并），并在 `.gdextension` 的 `[libraries]`/`[dependencies]` 中指向它。

---

## 7. 本卷总结与全书收束

### 7.1 一句话选型回顾

走到本卷终点，回顾两条路线的关系：**GDExtension 是默认答案，自定义模块是当默认答案失效时的终极手段**。前者用 ABI 边界换来了迭代速度与分发便利，后者用编译耦合换来了对引擎的无限制访问。成熟的工程组织会让两者各守其界——基础设施沉到模块，业务变化浮在 GDExtension。

### 7.2 本卷知识地图

```
引擎扩展开发卷 知识地图:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  扩展手段光谱（侵入性从低到高）:                             │
│                                                              │
│  GDScript ──► 编辑器插件 ──► GDExtension ──► 自定义模块     │
│  （纯脚本）   （EditorPlugin）（动态库）      （引擎 fork）  │
│      │            │               │               │          │
│      └────────────┴───────┬───────┴───────────────┘          │
│                           ▼                                  │
│                  共同点：ClassDB 注册体系                     │
│             （GDCLASS / _bind_methods / ADD_PROPERTY /       │
│               ADD_SIGNAL 在两条 C++ 路线上写法一致）        │
│                                                              │
│  关键分水岭:                                                 │
│   ① 能否忍受重编译引擎？                                     │
│   ② 需要的 API 在 extension_api.json 里吗？                 │
│   ③ 目标平台允许动态链接吗？                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 全书收束

从引擎基础的对象模型与场景树，到渲染、物理、资源、序列化各子系统，再到本卷的扩展开发，全书的主线其实只有一条：**Godot 的一切能力都建立在同一套注册与反射体系之上**。你写的 GDScript 类、编辑器插件、GDExtension 类、模块类，最终都汇入 ClassDB 这同一张表；区别只在于代码住在哪里、什么时候被加载、能看到多少内部世界。

理解了这一点，选型就不再是信仰之争，而是一组清晰的工程权衡：迭代速度、分发成本、维护负担、能力边界，四项摆上桌面，答案自然浮现。愿你在自己的项目里，永远用刚好够用的那条路线——既不为省事而硬闯 API 的死胡同，也不为完美而背上不必要的引擎 fork。

---

## 📝 本章总结

### 核心要点

1. **GDExtension 是默认选择**，动态库形态带来免重编译、热重载、易分发三大优势，适合第三方库集成与业务代码
2. **自定义模块是终极手段**，只有需要引擎内部 API、深度编辑器集成、静态链接平台时才必须使用
3. **两条路线共享同一套注册体系**，`GDCLASS` / `_bind_methods` / `ClassDB` 的写法在两边一致，学习成本可复用
4. **混合架构的关键在通信**，模块注册的类和单例通过 ClassDB / Engine 对 GDExtension 可见
5. **维护成本决定长期选型**，模块意味着背着引擎 fork，升级成本必须计入决策
6. **ABI 兼容有明确规则**，godot-cpp 分支对齐引擎版本、向后兼容单向、`compatibility_minimum` 兜底

### 关键术语

| 术语 | 解释 |
|------|------|
| GDExtension | Godot 4.x 的运行时原生扩展机制，以动态库形式加载 |
| godot-cpp | GDExtension 的官方 C++ 绑定库，分支对应引擎版本 |
| gdextension_interface.h | 引擎与扩展通信的 C ABI 接口 |
| extension_api.json | 引擎导出给扩展的 API 清单，`godot --dump-extension-api` 生成 |
| .gdextension 文件 | 扩展加载描述文件，声明入口符号、各平台库路径、依赖 |
| compatibility_minimum | 扩展要求的最低引擎版本，防止旧引擎误载 |
| reloadable | debug 构建下编辑器自动热重载扩展的开关 |
| Module | 静态编译进引擎的 C++ 扩展单元，位于引擎 `modules/` 目录 |
| custom_modules | SCons 构建选项，指定引擎树外的模块目录 |
| ResourceFormatLoader | 资源格式加载器扩展点，让 `load()` 支持新文件格式 |
| ModuleInitializationLevel | 初始化级别（core / servers / scene / editor），控制注册时机 |
| ABI | 应用程序二进制接口，GDExtension 兼容性的技术基础 |

---

## 🔗 延伸阅读

- **官方文档**: [What is GDExtension?](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/what_is_gdextension.html)
- **官方文档**: [GDExtension C++ example](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/gdextension_cpp_example.html)
- **官方文档**: [Custom modules in C++](https://docs.godotengine.org/en/latest/engine_details/engine_api/custom_modules_in_cpp.html)
- **官方文档**: [Extending the engine API（引擎 API 扩展总览）](https://docs.godotengine.org/en/latest/engine_details/engine_api/index.html)
- **源码位置**: 引擎模块目录 `godot/modules/`；资源加载器 `godot/core/io/resource_loader.h`；godot-cpp 绑定 [github.com/godotengine/godot-cpp](https://github.com/godotengine/godot-cpp)

---

## 📋 本卷总结

**引擎扩展开发卷 至此完结**

本卷从插件开发讲到 GDExtension 与自定义模块，覆盖了 Godot 扩展体系的全部层次。三条收尾建议送给即将动手实践的你：

- **先证明 GDExtension 不够用，再动模块**——把「需要内部 API」的判断落到 `extension_api.json` 的具体搜索结果上，而不是直觉
- **把引擎 fork 当负债管理**——每一行对引擎本体的修改都是未来的升级冲突，隔离、文档化、最小化
- **为升级日做准备**——版本对齐写进仓库、CI 跑加载冒烟测试、模块改动拆成可移植的 commit，升级那天你会感谢现在的自己

扩展开发是 Godot 工程能力的分水岭：跨过去，引擎对你来说不再是一个黑盒工具，而是一个可以自由塑造的平台。愿本卷成为你跨越它的桥。

---

*写作时间：2026-08-27*  
*字数：约 15,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-08-27 22:00*
