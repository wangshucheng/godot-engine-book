# 深入理解 Godot 引擎 #08 | Godot 文件系统与跨平台架构

> **摘要**：Godot 的文件系统和跨平台架构确保游戏可以一键导出到多个平台。本文将分析文件访问、资源打包、平台抽象层。

---

## 一、文件系统架构

### 1.1 文件访问

```gdscript
# 读取文件
var file = FileAccess.open("res://data.txt", FileAccess.READ)
var content = file.get_as_text()
file.close()

# 写入文件
var file = FileAccess.open("user://save.dat", FileAccess.WRITE)
file.store_string("save data")
file.close()

# 检查文件是否存在
if FileAccess.file_exists("res://data.txt"):
    print("文件存在")
```

### 1.2 目录结构

```
res://  (游戏资源目录)
├── scenes/
├── scripts/
├── assets/
└── icon.svg

user:// (用户数据目录)
├── saves/
├── settings.cfg
└── logs/
```

---

## 二、资源打包（PCK）

### 2.1 PCK 文件格式

Godot 使用 **.pck** 格式打包游戏资源：

```
game.pck
├── scenes/
│   └── main.tscn
├── scripts/
│   └── player.gd
└── assets/
    └── textures/
```

### 2.2 导出配置

```gdscript
# 导出时自动打包所有资源
# 菜单：Project → Export → 选择平台 → Export Project

# 自定义打包
var packer = PCKPacker.new()
packer.pck_start("game.pck")
packer.add_directory("res://")
packer.flush()
```

---

## 三、跨平台架构

### 3.1 平台抽象层

```cpp
// Godot 源码 - platform/
platform/
├── windows/    # Windows 平台
├── linux/      # Linux 平台
├── macos/      # macOS 平台
├── android/    # Android 平台
├── ios/        # iOS 平台
├── web/        # Web 平台 (HTML5)
└── javascript/ # JavaScript 绑定
```

### 3.2 平台检测

```gdscript
# 检测当前平台
if OS.get_name() == "Windows":
    print("运行在 Windows")
elif OS.get_name() == "macOS":
    print("运行在 macOS")
elif OS.get_name() == "Linux":
    print("运行在 Linux")
elif OS.get_name() == "Android":
    print("运行在 Android")
elif OS.get_name() == "iOS":
    print("运行在 iOS")
```

---

## 四、与 Unity 对比

| 维度 | Godot | Unity |
|------|-------|-------|
| 文件访问 | FileAccess | File.ReadAllText |
| 资源打包 | PCK | AssetBundle |
| 平台支持 | 内置导出 | 需要 Build Settings |
| 导出大小 | ~50MB | ~200MB+ |
| Web 支持 | HTML5 | WebGL |

---

## 五、第一卷总结

### 已完成内容

✅ 01: Godot 引擎概述  
✅ 02: Godot vs Unity 架构对比  
✅ 03: Godot 场景树架构  
✅ 04: Godot 内存管理机制  
✅ 05: Godot 对象系统  
✅ 06: Godot 信号系统  
✅ 07: Godot 资源系统  
✅ 08: Godot 文件系统  

### 下一步

**第二卷：渲染系统**（12 篇）
- 渲染架构概述
- Vulkan 后端
- 与 Unity SRP 对比
- 光照、材质、Shader
- 2D/3D 渲染
- 性能优化

---

## 六、总结

Godot 文件系统特点：
- ✅ 统一的文件访问 API
- ✅ PCK 资源打包
- ✅ 跨平台抽象层
- ✅ 一键导出多平台

**第一卷完成！进入第二卷：渲染系统**
