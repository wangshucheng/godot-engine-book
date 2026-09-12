# 第 8 篇：Godot 文件系统与跨平台架构

> **摘要**：Godot 的文件系统用三种路径前缀（`res://`、`user://`、绝对路径）统一了跨平台文件访问，导出时再把整个项目打包进 PCK。本文基于 `core/io/file_access.cpp` 与 `dir_access.cpp` 的真实实现，剖析 FileAccess 的工厂方法与 ModeFlags、DirAccess 的遍历协议、`make_dir` 与递归版的差异，以及平台抽象层与数据目录的真实布局。

---

## 一、文件系统架构

### 1.1 三种路径空间

```
res://   游戏资源目录：编辑器里就是项目根目录；
         导出后变为 PCK 包内路径（只读！）
user://  用户数据目录：跨平台映射到各系统的可写目录（见 3.3）
绝对路径 / C:\... / ~/...  逃出沙盒，仅桌面平台有意义
```

**核心规则：`res://` 在导出后只读**。存档、配置、日志必须写 `user://`。试图以 `WRITE` 模式打开包内文件会直接失败——`open()` 的实现里，只有非 WRITE 模式才允许从打包数据（`PackedData::try_open_path`）中打开文件。

### 1.2 FileAccess：读写文件

```gdscript
# 读取（失败返回 null，错误码走线程局部变量）
var file := FileAccess.open("res://data.txt", FileAccess.READ)
if file == null:
    match FileAccess.get_open_error():
        ERR_FILE_NOT_FOUND: push_error("文件不存在")
        _: push_error("打开失败")

# 一行读取的静态便捷方法（内部就是 open + get_as_text）
var content := FileAccess.get_file_as_string("res://data.txt")
var bytes := FileAccess.get_file_as_bytes("res://data.dat")

# 写入
var save := FileAccess.open("user://save.dat", FileAccess.WRITE)
save.store_string("save data")
save.close()

# 存在性检查（静态方法，PCK 包内文件也能查到）
if FileAccess.file_exists("user://save.dat"):
    print("已有存档")
```

三个来自源码的细节：

1. **`get_open_error()` 读的是线程局部变量**——`open()` 失败后立刻取，跨线程无效；
2. `file_exists()` 的实现是"先查 PackedData，再尝试以 READ 打开"，所以包内文件同样返回 `true`；
3. 静态便捷方法 `get_file_as_string()`/`get_file_as_bytes()` 失败时返回空值，配合 `FileAccess.get_open_error()` 使用。

### 1.3 ModeFlags 与压缩、加密

```cpp
// ModeFlags（定义于 file_access.h，语义按 Godot 通行约定）
READ        // 只读
WRITE       // 写入并【截断】已有内容
READ_WRITE  // 读写打开，不截断
WRITE_READ  // 读写打开，先截断
```

```gdscript
# 压缩文件（格式魔数 "GCPF"，默认 FASTLZ）
var cf := FileAccess.open_compressed("user://data.z", FileAccess.WRITE,
        FileAccess.COMPRESSION_ZSTD)

# 加密文件（AES256）
var ef := FileAccess.open_encrypted("user://secret.dat",
        FileAccess.WRITE, key_bytes)
var ef2 := FileAccess.open_encrypted_with_pass("user://secret.dat",
        FileAccess.WRITE, "passphrase")
```

`CompressionMode` 共五种：`FASTLZ`（默认）、`DEFLATE`、`ZSTD`、`GZIP`、`BROTLI`。读写必须使用同一种压缩模式，且压缩文件**不能直接用普通 `open()` 读**。

### 1.4 读写方法速查

| 方法 | 说明 |
|------|------|
| `get_line()` / `store_line()` | 行读写（跳过 `\r`） |
| `get_csv_line(",")` / `store_csv_line()` | CSV 解析支持引号包裹与跨行字段 |
| `get_as_text(skip_cr)` | `seek(0)` 后整读并恢复原位置 |
| `get_var()` / `store_var()` | 32 位长度前缀 + Variant 编码；`full_objects` 可存完整对象 |
| `get_buffer(len)` / `store_buffer()` | 字节缓冲 |
| `get_16()/get_32()/get_64()/get_float()` | 定宽整数与浮点（受 `big_endian` 影响） |
| `get_pascal_string()` / `store_pascal_string()` | 32 位长度前缀 + UTF-8 |
| `get_position()/seek()/seek_end()/get_length()/eof_reached()` | 定位 |
| `get_error()` | 上次操作错误；`flush()` 落盘 |

读写定宽数值时注意 `set_big_endian(true)` 的字节序影响——跨引擎共享文件时尤其重要。

### 1.5 DirAccess：目录操作

```gdscript
# 打开目录（失败返回 null，错误码同走 get_open_error）
var dir := DirAccess.open("user://saves")

# 现代写法：get_files()/get_directories() 返回【排序后】的列表，
# 内部走 _get_next()，自动跳过 "."/".." 与隐藏项
for file in dir.get_files():
    print("存档：", file)

# 经典写法：三段式迭代器
dir.list_dir_begin()
var name := dir.get_next()
while not name.is_empty():
    if dir.current_is_dir():
        print("目录：", name)
    else:
        print("文件：", name)
    name = dir.get_next()
dir.list_dir_end()
```

源码细节：`get_next()` 本身**没有**过滤参数，`.`/`..` 与隐藏项的过滤由包装方法 `_get_next()` 完成，行为受两个属性控制——`set_include_navigational(true)`（保留 `.`/`..`）与 `set_include_hidden(true)`（保留隐藏项）。

目录维护的完整工具箱：

```gdscript
dir.make_dir("new_folder")            # 单级创建（已存在返回 ERR_ALREADY_EXISTS）
dir.make_dir_recursive("a/b/c")       # 递归创建，容忍 ERR_ALREADY_EXISTS
dir.rename("old.txt", "new.txt")      # 重命名/移动
dir.remove("old.txt")                 # 删除文件或空目录
dir.copy("from.dat", "to.dat")        # 复制文件（64KB 缓冲，可带 chmod）
dir.copy_dir("from_dir", "to_dir")    # 递归复制目录
dir.erase_contents_recursive()        # 递归清空目录内容
dir.dir_exists("saves")               # 目录存在性
```

跨空间操作用静态 `_absolute` 变体——它们内部先 `globalize_path()`，因此**支持在 `res://` 与 `user://` 之间复制**：`DirAccess.copy_absolute(from, to)`、`rename_absolute(from, to)`、`remove_absolute(path)`、`make_dir_recursive_absolute(path)`。

---

## 二、资源打包（PCK）

### 2.1 打包后 res:// 的透明读取

导出时全部资源被打进 `.pck` 包，但**代码无需任何改动**：`FileAccess.open()` 的实现会在非 WRITE 模式下优先调用 `PackedData::try_open_path(path)`——包内有该路径就直接从包内读取，没有才落到真实文件系统。`FileAccess.file_exists()` 同样先查包。

这意味着：

- 读包内文件与读磁盘文件代码完全一致；
- 包内**永远不可写**；
- `DirAccess` 在导出后遍历 `res://` 也能列出包内条目（PackedData 支持目录枚举）。

### 2.2 PCKPacker 与导出配置

```gdscript
# 手工构建 PCK（常用于资源热更新流程）
var packer := PCKPacker.new()
packer.pck_start("user://patch.pck")
packer.add_file("res://mods/new_scene.tscn", "res://mods/new_scene.tscn")
packer.flush()

# 运行时加载补丁包（加载后其中的资源立即可用）
ProjectSettings.load_resource_pack("user://patch.pck")
```

常规导出走「项目 → 导出」预设；导出选项决定哪些文件进入 PCK（过滤器、是否打包源资源、PCK 与可执行文件分离等）。

---

## 三、跨平台架构

### 3.1 平台抽象层

```
platform/                      # 每个平台一个子目录
├── windows/     # Windows
├── linuxbsd/    # Linux 与 *BSD（同一套显示后端）
├── macos/       # macOS
├── android/     # Android
├── ios/         # iOS
└── web/         # Web（WebAssembly）
```

每个平台目录实现同一组 C++ 抽象基类（显示、音频、文件、线程、时间），引擎其余部分只面向抽象层编程——这就是"一次编写、多平台导出"在源码层的支撑。**注意 4.x 中 Linux 平台目录是 `linuxbsd/`，Web 平台是 `web/`**，老资料里的 `platform/linux/`、`platform/javascript/` 已不存在。

### 3.2 平台检测

```gdscript
# 方式一：OS.get_name()
match OS.get_name():
    "Windows": pass
    "macOS":   pass
    "Linux":   pass
    "Android": pass
    "iOS":     pass
    "Web":     pass

# 方式二：feature 标签（可同时命中多个，语义更细）
if OS.has_feature("mobile"):      # Android 与 iOS 同为 true
    pass
if OS.has_feature("web"):         # 浏览器导出
    pass
if OS.has_feature("pc"):          # 桌面三平台
    pass
if OS.has_feature("web_android"): # 浏览器中运行在 Android 设备
    pass
if OS.is_debug_build():
    pass
```

优先用 **feature 标签**做能力判断（`"mobile"` 同时覆盖 Android/iOS），`get_name()` 只在需要区分具体平台时使用。

### 3.3 user:// 的真实位置

| 平台 | `user://` 映射到 |
|------|------------------|
| Windows | `%APPDATA%\Godot\app_userdata\<项目名>` |
| macOS | `~/Library/Application Support/Godot/app_userdata/<项目名>` |
| Linux | `~/.local/share/godot/app_userdata/<项目名>` |

调试用户数据时直接去这些目录看文件即可。编辑器内还可用 `ProjectSettings.globalize_path("user://save.dat")` 换算出真实路径（**仅运行中的项目有效**；导出后 `res://` 已打包成 PCK，`globalize_path` 对包内路径无意义）。

---

## 四、实践：安全的配置与存档

```gdscript
const SAVE_PATH := "user://settings.cfg"

func load_settings() -> Dictionary:
    var cfg := ConfigFile.new()
    if cfg.load(SAVE_PATH) != OK:
        return {}                       # 文件不存在/损坏 → 返回默认值
    return {
        "volume": cfg.get_value("audio", "volume", 1.0),
        "fullscreen": cfg.get_value("video", "fullscreen", false),
    }

func save_settings(values: Dictionary) -> void:
    # 防止写一半崩溃损坏存档：先写临时文件，再重命名覆盖
    var tmp := SAVE_PATH + ".tmp"
    var cfg := ConfigFile.new()
    cfg.set_value("audio", "volume", values["volume"])
    cfg.set_value("video", "fullscreen", values["fullscreen"])
    if cfg.save(tmp) != OK:
        push_error("存档写入失败")
        return
    var dir := DirAccess.open("user://")
    if dir:
        if dir.file_exists(SAVE_PATH):
            dir.remove(SAVE_PATH)
        dir.rename(tmp, SAVE_PATH)
```

要点：`ConfigFile`/`JSON` 只负责格式，**崩溃安全靠"写临时文件 + 重命名"**——重命名在同一文件系统内是接近原子的操作。

---

## 五、与 Unity 对比

| 维度 | Godot | Unity |
|------|-------|-------|
| 文件访问 | `FileAccess`（静态工厂 + 句柄） | `File.ReadAllText` 等 .NET API |
| 路径空间 | `res://` / `user://` 双空间 | `Application.dataPath` / `persistentDataPath` |
| 资源打包 | PCK（可运行时追加加载） | AssetBundle / Addressables |
| 平台抽象 | 源码级 `platform/` 目录，统一导出 | Build Settings + 平台宏 |
| Web 支持 | WebAssembly 导出 | WebGL 导出 |

最值得注意的差异在**路径模型**：Godot 的 `res://` 在编辑器与导出后表现一致（读），`user://` 自动跨平台映射，代码里几乎不需要出现真实路径；Unity 则需要按平台拼接 `persistentDataPath`。

---

## 六、总结

Godot 文件系统的核心是"三种路径、两个类、一层打包"：

```
res://（只读，导出后 = PCK 包内）   user://（可写，跨平台映射）   绝对路径
FileAccess：open → 读写 → close（get_open_error 报告失败）
DirAccess ：open → list_dir_begin/get_next → 目录维护
PCK       ：导出打包 + load_resource_pack 运行时追加
```

- **`res://` 导出后只读**，一切可写数据走 `user://`
- **`user://` 自动映射**到各系统标准数据目录
- **FileAccess 的静态方法族**（`open/open_compressed/open_encrypted/get_file_as_*`）覆盖绝大多数场景
- **DirAccess 的迭代协议**：`list_dir_begin → get_next → list_dir_end`，现代代码优先用 `get_files()/get_directories()`
- **崩溃安全**靠自己实现：写临时文件 + `rename()`

---

## 🔗 延伸阅读

- **DirAccess**: <https://docs.godotengine.org/en/stable/classes/class_diraccess.html>
- **FileAccess**: <https://docs.godotengine.org/en/stable/classes/class_fileaccess.html>
- **数据路径（官方文档）**: <https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html>
- **源码位置**: `core/io/dir_access.cpp`, `core/io/file_access.cpp`, `platform/`

---

**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 7 篇：Godot 资源系统深度解析](/articles/07-resource-system.md)
**下一篇**: [第 9 篇：Godot 序列化系统深度解析](/articles/09-serialization-system.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
