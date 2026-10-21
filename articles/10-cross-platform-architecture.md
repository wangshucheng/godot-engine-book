# 第 10 篇：Godot 跨平台架构详解

> **摘要**：Godot 支持一键导出到桌面、移动、Web 等多个平台。本文将深入分析 Godot 的跨平台架构、平台抽象层、导出系统，并与 Unity 进行对比。这是第一卷的最后一篇。

---

## 一、跨平台架构概述

### 1.1 支持的平台

Godot 支持以下平台：

| 平台 | 状态 | 备注 |
|------|------|------|
| **Windows** | ✅ 完全支持 | 64 位/32 位 |
| **macOS** | ✅ 完全支持 | Intel/Apple Silicon |
| **Linux** | ✅ 完全支持 | x86_64/ARM |
| **Android** | ✅ 完全支持 | API 21+ |
| **iOS** | ✅ 完全支持 | iOS 11+ |
| **Web** | ✅ 支持 | HTML5/WebAssembly |
| **主机** | ⚠️ 第三方支持 | 通过第三方公司 |

### 1.2 跨平台架构设计

```
Godot 跨平台架构
├── 游戏代码（GDScript/C#）
│   └── 跨平台，无需修改
├── 引擎层
│   ├── 场景系统
│   ├── 渲染系统
│   └── 物理系统
├── 平台抽象层
│   ├── OS（操作系统，core/os/）
│   ├── DisplayServer（显示与窗口，servers/display_server/）
│   ├── AudioServer（音频，servers/audio/）
│   └── InputServer（输入，servers/input/）
└── 平台实现
    ├── Windows
    ├── macOS
    ├── Linux
    ├── Android
    ├── iOS
    └── Web
```

---

## 二、平台抽象层

### 2.1 OS 类

**OS 类**提供操作系统相关的抽象：

```gdscript
# 获取操作系统信息
print(OS.get_name())  # "Windows", "macOS", "Linux", "Android", "iOS", "Web"
print(OS.get_version())  # 系统版本
print(OS.get_processor_count())  # 逻辑 CPU 核心数
print(OS.get_processor_name())  # CPU 型号

# 内存信息
print(OS.get_static_memory_usage())       # 引擎静态内存占用（字节）
print(OS.get_static_memory_peak_usage())  # 静态内存占用峰值
print(OS.get_memory_info())               # 系统内存：{"physical", "free", "available", "stack"}

# 获取系统目录
print(OS.get_executable_path())  # 可执行文件路径
print(OS.get_user_data_dir())  # 用户数据目录

# 系统功能
DisplayServer.clipboard_set("copy text")  # 复制到剪贴板
OS.alert("message")  # 显示系统对话框
OS.request_permissions()  # 请求 Android 危险权限（仅 Android 有效）
```

> ⚠️ **4.x 没有 `OS.get_memory_size()`**，也不存在 `OS.set_clipboard()`。要区分三种不同的"内存"：
>
> | 需求 | 正确 API | 说明 |
> |------|---------|------|
> | 引擎自己占了多少静态内存 | `OS.get_static_memory_usage()` | **不是系统总内存**，而且只在 debug 构建下有意义（release 下返回 0） |
> | 静态内存峰值 | `OS.get_static_memory_peak_usage()` | 同上 |
> | 系统物理内存 / 可用内存 | `OS.get_memory_info()` | 返回字典，含 `physical` / `free` / `available` / `stack`，单位字节 |
> | 写剪贴板 | `DisplayServer.clipboard_set(text)` | 4.x 把剪贴板从 `OS` 迁到了 `DisplayServer` |

### 2.2 DisplayServer

**DisplayServer** 处理显示和窗口：

```gdscript
# 窗口管理
DisplayServer.window_set_title("My Game")
DisplayServer.window_set_size(Vector2i(1280, 720))
DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)

# 屏幕信息
var screen_count = DisplayServer.get_screen_count()
var screen_size = DisplayServer.screen_get_size()

# 键盘
if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
    DisplayServer.virtual_keyboard_show()
```

### 2.3 Input 类

**Input 类**提供统一的输入处理：

```gdscript
# 键盘输入
if Input.is_key_pressed(KEY_SPACE):
    jump()

# 鼠标输入
if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
    shoot()

# 游戏手柄
if Input.is_joy_button_pressed(0, JOY_BUTTON_A):
    action()

# 触摸输入
if Input.is_action_pressed("touch"):
    var pos = Input.get_touch_position()
```

---

## 三、导出系统

### 3.1 导出预设

**导出预设**配置导出参数：

```ini
# export_presets.cfg
[preset.0]
name="Windows Desktop"
platform="Windows Desktop"
runnable=true
advanced_options=false
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="build/game.exe"
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false
script_export_mode=2

[preset.0.options]
custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=false
```

> ⚠️ **不要照抄网上流传的 `texture_format/etc2`、`texture_format/s3tc`、`texture_format/bptc` 这几行**——4.x 的导出预设里没有 `texture_format/etc2` 这个开关（ETC2/ASTC 的开关是**纹理导入**侧的 `etc2_astc` 选项，由 `ResourceImporterTextureSettings::should_import_etc2_astc()` 控制，属于导入设置而不是导出预设）。
>
> 另外要记住：**导出预设的 `[preset.N.options]` 是按平台插件动态生成的**——Windows、macOS、Linux、Android、Web 各有一套不同的键名，而且会随引擎版本增删。**以编辑器「项目 → 导出」面板当前显示的选项为准**，不要凭记忆手写这个文件；确实需要精确对齐时，先在编辑器里配好一次预设，再把生成的 `export_presets.cfg` 提交进版本库。

### 3.2 导出流程

```
1. 选择导出预设
   ↓
2. 配置导出选项
   ↓
3. 打包资源（PCK）
   ↓
4. 复制引擎二进制
   ↓
5. 签名（移动平台）
   ↓
6. 生成最终包
```

### 3.3 导出命令

```gdscript
# 命令行导出
# Windows
godot --export-release "Windows Desktop" build/game.exe

# macOS
godot --export-release "macOS" build/game.app

# Linux
godot --export-release "Linux/X11" build/game.x86_64

# Android
godot --export-debug "Android" build/game.apk

# iOS
godot --export-release "iOS" build/game.ipa

# Web
godot --export-release "Web" build/index.html
```

---

## 四、各平台特性

### 4.1 Windows

**Godot 不提供注册表 / COM 的内建绑定**——4.3 的 `OS` 类里既没有 `Registry`，也没有 `COM` 这两个符号（`OS.xml` 的方法全集里查无此名）。要访问 Windows 特有的系统 API，有三条路：

```gdscript
# 路线 A：GDExtension 调 Win32 API（推荐，功能完整）
#   用 C++ 写一个 GDExtension，内部调用 RegOpenKeyEx / CoCreateInstance，
#   再把能力以方法或单例的形式暴露给 GDScript。
#   详见第 69–72 篇（GDExtension 与自定义模块）。

# 路线 B：借助外部进程（轻量，适合一次性读取）
if OS.get_name() == "Windows":
    var output: Array = []
    var exit_code := OS.execute("reg.exe", ["query", r"HKCU\Software\Godot"], output)
    if exit_code == 0:
        print(output[0])   # 完整输出作为单个 String 元素返回

# 路线 C：写配置文件（最省事）
#   把需要持久化的数据存到 user:// 下的配置文件或 JSON，由游戏自己管理。
```

> ⚠️ `OS.execute()` 是**阻塞**调用（主线程会等子进程结束），别在每帧里调；`OS.create_process()` 则是异步的，返回 PID 而不等待。
>
> 顺带一提：Windows 上的**渲染后端**由 `OS.get_video_adapter_driver_info()` 与 `RenderingServer` 决定，4.3 提供 `RENDERING_DRIVER_VULKAN` / `RENDERING_DRIVER_OPENGL3` / `RENDERING_DRIVER_D3D12` 三种（DirectX 12 后端在 4.3 才加入，仍较新），这与注册表/COM 是两回事——**引擎没有为它们提供脚本绑定**。

### 4.2 macOS

```gdscript
# macOS 特定功能
if OS.get_name() == "macOS":
    # 菜单栏
    # 通知中心
    # Touch Bar（如果支持）
    
    # Apple Silicon 优化
    # Godot 4.x 支持 ARM64
```

### 4.3 Android

```gdscript
# Android 特定功能
if OS.get_name() == "Android":
    # 危险权限请求（相机、麦克风、位置等）
    var granted = OS.request_permissions()      # 返回 bool
    print("已授权权限：", OS.get_granted_permissions())

    # 设备标识（Android 实现的是 ANDROID_ID）
    var device_id := OS.get_unique_id()

    # 触摸和多点触控
    # 传感器（加速度计、陀螺仪）—— 需 Android 插件
```

> ⚠️ **4.x 没有 `OS.get_native_handle()`**，`core/os/os.h` 里也没有这个虚函数。Android 侧要拿到 Java 层的 `Activity` / `Context`，**必须**通过 Android 插件（Godot Android Plugin）用 `@JavaClass` 绑定：
>
> ```gdscript
> # 需要在 Android 导出配置里启用 "Gradle Build" 并添加插件
> var activity = JavaClassWrapper.wrap("com.godot.game.GodotApp", "getActivity")()
> ```
>
> 引擎暴露给 GDScript 的 Android 相关能力仅限这些：`OS.request_permissions()` / `OS.get_granted_permissions()` / `OS.get_unique_id()` / `OS.get_model_name()` / `OS.get_distribution_name()`，以及 `DisplayServer` 的 `screen_get_*`、`tts_*` 等。

### 4.4 iOS

```gdscript
# iOS 特定功能
if OS.get_name() == "iOS":
    # iOS 没有内建的权限请求 API：
    # OS.request_permissions() 只在 Android 上实现。
    # 相机/麦克风/相册等权限需要写 iOS 插件（Godot iOS Plugin），
    # 用 @JavaClassWrapper 等价物（Objective-C 侧）去请求。

    # 内购（StoreKit）—— 同样需要 iOS 插件
    # Game Center —— 需要 iOS 插件

    # 触觉反馈
    Input.start_joy_vibration(0, 0.5, 0.5, 1.0)
```

> ⚠️ `OS.request_permission(name)` 在 4.3 里**只有 Android 实现**，而且仅用于 `"RECORD_AUDIO"`（`AudioDriverOpenSL`）；`OS.request_permissions()` 才是"请求全部危险权限"的 Android 接口。iOS 侧的权限必须走插件。

### 4.5 Web

```gdscript
# Web 特定功能
if OS.get_name() == "Web":
    # JavaScript 互操作
    await JavaScriptBridge.eval("alert('Hello from Godot!')")
    
    # 限制
    # - 无多线程（WebAssembly 限制）
    # - 文件大小限制
    # - 无直接文件系统访问
```

---

## 五、与 Unity 跨平台对比

### 5.1 平台支持对比

| 平台 | Godot | Unity |
|------|-------|-------|
| Windows | ✅ | ✅ |
| macOS | ✅ | ✅ |
| Linux | ✅ | ✅ |
| Android | ✅ | ✅ |
| iOS | ✅ | ✅ |
| Web | ✅ (WebAssembly) | ✅ (WebGL) |
| 主机 | ⚠️ (第三方) | ✅ (官方支持) |
| AR/VR | ✅ | ✅ |

### 5.2 导出对比

| 维度 | Godot | Unity |
|------|-------|-------|
| **导出大小** | ⚠️ 示意数据：~50MB | ⚠️ 示意数据：~200MB+ |
| **导出速度** | ⚠️ 示意数据：秒级 | ⚠️ 示意数据：分钟级 |
| **配置复杂度** | 简单 | 中等 |
| **命令行导出** | ✅ 内置 | ✅ 需要 CLI |
| **批量导出** | ⚠️ 有限 | ✅ 完善 |

> ⚠️ **"导出大小 / 导出速度"两行为示意数据（未附测试环境）**。两列的体积受**引擎模板本身**主导：Godot 侧的 ~50MB 是官方 Windows 导出模板 + 空工程的量级，Unity 侧的 ~200MB+ 是 2022 LTS 模板 + 空工程的量级——项目资源、导入设置、是否勾选"嵌入 PCK"、是否做纹理压缩都会显著改变结果。速度同理，取决于 CPU、磁盘、是否首次导入资源（冷缓存与热缓存差一个数量级）。**请以自有项目的实测数据为准**。

### 5.3 代码示例对比

**Godot 导出**：

```bash
# 一行命令导出
godot --export-release "Windows Desktop" build/game.exe
```

**Unity 导出**：

```bash
# 需要 Unity 命令行工具
Unity -batchmode -quit -projectPath . \
  -executeMethod BuildScript.PerformBuild \
  -buildTarget Windows64 \
  -buildPath build/game.exe
```

---

## 六、第一卷总结

### 6.1 已完成内容

✅ **01**: Godot 引擎概述  
✅ **02**: Godot vs Unity 架构对比  
✅ **03**: Godot 场景树架构  
✅ **04**: Godot 内存管理机制  
✅ **05**: Godot 对象系统  
✅ **06**: Godot 信号系统  
✅ **07**: Godot 资源系统  
✅ **08**: Godot 文件系统  
✅ **09**: Godot 序列化系统  
✅ **10**: Godot 跨平台架构  

### 6.2 核心知识点

| 主题 | 核心概念 |
|------|---------|
| **架构** | 场景树、五层架构、服务器抽象 |
| **内存** | 节点随父节点释放、资源引用计数 |
| **对象** | Object 类、RTTI、反射 |
| **通信** | 信号系统、观察者模式 |
| **资源** | 一切皆资源、引用计数 |
| **文件** | 文件访问、PCK 打包 |
| **序列化** | Variant 类型、@export |
| **跨平台** | 平台抽象层、一键导出 |

### 6.3 与 Unity 对比总结

| 维度 | Godot | Unity |
|------|-------|-------|
| **架构** | 场景树（组合） | GameObject-Component |
| **内存** | 节点随父节点释放 / 资源引用计数 | 垃圾回收 |
| **脚本** | GDScript + C# | C# |
| **渲染** | RenderingServer | SRP/URP/HDRP |
| **大小** | ⚠️ 示意数据：~100MB | ⚠️ 示意数据：~10GB |
| **启动** | ⚠️ 示意数据：<3 秒 | ⚠️ 示意数据：30-60 秒 |
| **开源** | ✅ 完全开源 | ⚠️ 部分开源 |
| **许可** | MIT（免费） | 订阅制 |

---

## 七、第二卷预告

### 第二卷：渲染系统（12 篇）

| 编号 | 标题 |
|------|------|
| 11 | Godot 渲染架构概述 |
| 12 | Vulkan 渲染后端 |
| 13 | Godot vs Unity 渲染对比 |
| 14 | 场景渲染流程 |
| 15 | 光照系统 |
| 16 | 材质系统 |
| 17 | GDShader 语言 |
| 18 | 2D 渲染 |
| 19 | 后处理效果 |
| 20 | 粒子渲染 |
| 21 | 性能优化 |
| 22 | 渲染调试工具 |

---

## 八、总结

### Godot 跨平台优势

- ✅ 真正的跨平台（Linux 原生支持）
- ✅ 轻量级（导出文件小）
- ✅ 快速导出
- ✅ 统一的 API
- ✅ 开源免费

### 第一卷完成！

恭喜！你已经完成了《深入理解 Godot 引擎》第一卷的全部 10 篇文章！

**下一步**：第二卷 渲染系统

---

## 🔗 延伸阅读

- **官方文档**: [跨平台发布](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_different.html)、[命令行参数](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)
- **类参考**: [OS](https://docs.godotengine.org/en/stable/classes/class_os.html)、[DisplayServer](https://docs.godotengine.org/en/stable/classes/class_displayserver.html)、[ProjectSettings](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html)
- **源码位置**: `core/os/os.cpp`、`servers/display_server.cpp`

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 9 篇：Godot 序列化系统深度解析](/articles/09-serialization-system.md)
**下一篇**: [第 53 篇：输入系统](/articles/53-input-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*

**第一卷 完**
