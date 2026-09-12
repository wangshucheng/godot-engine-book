# 第 7 篇：Godot 资源系统深度解析

> **摘要**：资源（Resource）是 Godot 的核心概念——场景、材质、音频、脚本都是资源。本文基于 `core/io/resource.cpp` 与 `resource_loader.cpp` 的真实实现，剖析 `path_cache` 与资源缓存的关系、`set_path()` 的抢占语义、`ResourceLoader.load()` 的完整管线、五种 CACHE_MODE 的差异、线程化加载的真实行为，以及 `duplicate()`/`local_to_scene` 的复制规则。

---

## 一、资源系统概述

### 1.1 什么是资源

在 Godot 中，**一切皆资源**：

- 场景是资源（`PackedScene`）
- 脚本是资源（`GDScript`）
- 纹理是资源（`Texture2D`）
- 材质是资源（`Material` 及其子类）
- 音频是资源（`AudioStream` 及其子类）
- 字体、主题、网格、动画……乃至导入器的中间产物

资源统一了三件事：**数据容器**（存配置与资产）、**可共享单例**（同路径同实例）、**可序列化文件**（.tres/.res）。

### 1.2 Resource 类的真实结构

**源码位置**: `core/io/resource.h` / `core/io/resource.cpp`

由 `resource.cpp` 的实际使用可确证的成员（Godot 4.3）：

```cpp
class Resource : public RefCounted {
    String path_cache;          // 既是 get_path() 的返回值，也是缓存键
    String name;                // resource_name
    String scene_unique_id;     // 场景内唯一 ID
    bool local_to_scene = false;// resource_local_to_scene
    Node *local_scene = nullptr;// 所属场景（local_to_scene 机制用）
    SelfList<Resource> remapped_list;  // 翻译重映射链表（set_as_translation_remapped）
};
```

静态侧是资源缓存本体（`resource.cpp` 中定义）：

```cpp
HashMap<String, Resource *> ResourceCache::resources;   // 路径 → 资源
Mutex ResourceCache::lock;                              // 全局互斥锁
```

**一个重要的版本事实**：4.x **没有** `owners` 集合、`register_owner()` 这类机制——那是 Godot 3.x 的设计，4.x 已移除。资源的生命周期完全交给 `RefCounted` 的原子引用计数，缓存的失效靠"惰性清理"（见 2.4）。

### 1.3 资源的三重身份

```
同 path_cache → 同一实例（缓存去重，全项目共享）
同一实例      → 多处持有（修改一处，处处可见——检查器里编辑材质会影响所有使用者）
```

"共享"是资源最大的威力，也是最大的陷阱：**修改共享资源会影响所有使用者**，需要独立副本时用 `duplicate()` 或 `resource_local_to_scene`（第五节）。

---

## 二、路径与缓存：set_path 的完整语义

### 2.1 path_cache：既是路径也是缓存键

`get_path()` 的返回值就是 `path_cache`，而它同时是全局 `ResourceCache::resources` 的键——**同一路径全局只注册一份实例**，这同时实现了加载去重与循环包含检测。

### 2.2 set_path() 的五步流程

```cpp
// 简化自 resource.cpp，全程持有 ResourceCache::lock
void Resource::set_path(const String &p_path, bool p_take_over) {
    if (path_cache == p_path) return;            // ① 同路径幂等
    if (p_path.is_empty()) p_take_over = false;  // ② 空路径不能抢占
    if (!path_cache.is_empty()) {                // ③ 先摘掉旧键
        ResourceCache::resources.erase(path_cache);
        path_cache = "";
    }
    if (ResourceCache::get_ref(p_path).is_valid()) {  // ④ 目标路径已被占用
        if (p_take_over) { /* 抢占：清空占用者的路径，旧资源变为"无路径" */ }
        else {
            ERR_FAIL_MSG("Another resource is loaded from path '...' "
                         "(possible cyclic resource inclusion).");
        }
    }
    path_cache = p_path;                          // ⑤ 注册进缓存
    ResourceCache::resources[p_path] = this;
}
```

两个绑定版本对应两个脚本入口：`set_path()`（`take_over = false`）与 `take_over_path()`（`take_over = true`）。**`take_over_path()` 的语义是"抢占"**——旧资源对象仍然存活，只是失去了路径与缓存注册；`PackedScene` 重新加载、编辑器保存资源时都会用到它。

注意失败路径的细节：路径被占用且未抢占时，**本资源已经处于"无路径、不在缓存"的状态**——错误发生在半途，不是无副作用的检查。

### 2.3 循环包含检测

第 ④ 步的错误信息里藏着 `set_path()` 的另一个身份：**循环资源包含的检测器**。A 资源引用 B、B 又引用 A 时，A 的加载会尝试把 B 注册到 A 已占用的路径上，触发 `possible cyclic resource inclusion` 报错。看到这条错误，正确排查方向是检查两个 .tres/.tscn 之间的相互引用。

### 2.4 惰性清理取代 owners 注册表

3.x 时代每个资源维护一份"谁在引用我"的 `owners` 集合；4.x 把它换成了更轻的**惰性清理**：

- `ResourceCache::has()/get_ref()` 命中后检查 `get_reference_count() == 0`（正在析构）→ 就地清空条目；
- 析构函数只在缓存键仍指向自己时注销（`CACHE_MODE_IGNORE` 加载的同路径别名资源不会被误删）。

---

## 三、加载管线：ResourceLoader.load

### 3.1 四种加载入口

```gdscript
# 1. 运行时加载（有缓存）
var texture = load("res://player.png")

# 2. 编译期加载（最稳：路径在解析时校验，无运行时开销）
const PlayerTexture: Texture2D = preload("res://player.png")

# 3. 显式调用（与 load() 等价，可带类型提示与缓存模式）
var data = ResourceLoader.load("res://data.tres", "ItemData")

# 4. 后台线程加载
ResourceLoader.load_threaded_request("res://large_level.scn")
```

### 3.2 load() 的完整流程

调用链（真实函数名）：`load()` → `_load_start()` → `_run_load_task()` → `_path_remap()` → `_load()` → `loader[i]->load()`。

```
① _validate_local_path()   uid://xxx → 还原文件路径；相对路径 → res:// 前缀
② 缓存查询                 仅 CACHE_MODE_REUSE时；发生在重映射【之前】
③ _path_remap()            翻译重映射 → path_remaps → .remap 文件
④ _load()                  线性扫描已注册的 ResourceFormatLoader，
                           第一个 recognize_path() 通过者执行加载，失败试下一个
⑤ 收尾                     按 cache_mode 写缓存 / 注册路径
```

两个反直觉的细节：

- **`uid://` 的解析发生在缓存查询之前**：`ResourceUID::text_to_id()` 把 `uid://xxx` 还原成文件路径，之后的缓存键与重映射都基于还原后的路径；
- **类型提示只参与 loader 筛选，加载完成后没有类型校验**——`load("x.png", "Texture2D")` 只是挑选能处理 Texture2D 的 loader，并不会检查结果真的是 Texture2D。

找不到任何 loader 时报 `ERR_FILE_UNRECOGNIZED`（"No loader found for resource"）；工具构建下文件不存在则报 `ERR_FILE_NOT_FOUND`。

### 3.3 CACHE_MODE：五种模式对比

| 模式 | 加载前查缓存 | 完成后 | 典型场景 |
|------|:---:|------|----------|
| `CACHE_MODE_REUSE`（默认） | ✅ 命中直接返回 | 注册进缓存 | 一般游戏加载 |
| `CACHE_MODE_REPLACE` | ❌ | 若缓存已有同路径实例：`old_res->copy_from(新数据)`，**返回旧实例** | 编辑器热重载 |
| `CACHE_MODE_IGNORE` | ❌ | 仅记录路径（`set_path_cache`），**不进缓存** | 需要同路径多份独立实例 |
| `IGNORE_DEEP` / `REPLACE_DEEP` | 同上 | 模式传播到全部子资源 | 嵌套资源整体重载 |

`REPLACE` 的语义值得展开：外部已持有的 `Ref<Resource>` 会**原地看到新内容**——这就是编辑器"保存资源后所有引用者自动刷新"的实现方式。

### 3.4 线程化加载

```gdscript
ResourceLoader.load_threaded_request("res://large_level.scn")

# 每帧轮询状态与进度（进度由子任务递归折算，且保证单调不减）
match ResourceLoader.load_threaded_get_status("res://large_level.scn", progress):
    ResourceLoader.THREAD_LOAD_IN_PROGRESS: pass  # progress[0] ∈ [0,1]
    ResourceLoader.THREAD_LOAD_LOADED:
        var level = ResourceLoader.load_threaded_get("res://large_level.scn")
    ResourceLoader.THREAD_LOAD_FAILED: push_error("加载失败")
    ResourceLoader.THREAD_LOAD_INVALID_RESOURCE: pass  # 未请求/已取走
```

源码里的三个关键行为：

1. **`load_threaded_get()` 在主线程调用且未完成时会阻塞等待**（1ms 轮询）——想不卡顿就在 `_process` 里轮询状态，不要直接 `get`；
2. 重复 `load_threaded_request()` 同一路径**不会重复加载**：令牌复用（内部引用计数），多次 `get` 依次取走；
3. **循环加载返回 `ERR_BUSY`**：加载任务里同步去加载同一资源，当前线程正是任务执行者时会被检测到。

### 3.5 导出项目的加载错误

导出后的项目最常见加载错误是：

```
Failed loading resource: xxx. Make sure resources have been imported by
opening the project in the editor at least once.
```

原因：非导入类资源（.png 等）在导出包里是**导入产物**，没经过编辑器导入就没有对应产物——CI 打包前必须先跑一次编辑器导入。

---

## 四、序列化：.tres 与 .res

### 4.1 .tres 文本格式剖析

```ini
[gd_resource type="ItemData" script_class="ItemData" load_steps=3 format=3]

[ext_resource type="Script" path="res://items/item_data.gd" id="1_item"]
[ext_resource type="Texture2D" path="res://assets/icons/sword.png" id="2_icon"]

[sub_resource type="AtlasTexture" id="AtlasTexture_frame0"]
atlas = ExtResource("2_icon")
region = Rect2(0, 0, 32, 32)

[resource]
script = ExtResource("1_item")
item_name = "铁剑"
item_value = 120
icon = SubResource("AtlasTexture_frame0")
```

结构规则：

- `[gd_resource]` 头声明资源类型、格式版本（4.x 为 `format=3`）与 `uid`；
- `[ext_resource]` 是**外部依赖**（按 `id` 引用，4.3 起携带 `uid` 属性防路径漂移）；
- `[sub_resource]` 是**内嵌子资源**（只在文件内部可见，无路径）；
- `[resource]` 是根资源本体，属性按 `PROPERTY_USAGE_STORAGE` 过滤后写出。

### 4.2 二进制 .res/.scn 与导入

`.res`（二进制资源）与 `.tres` 内容等价：更小、更快、不可读。场景的对应物是 `.tscn`/`.scn`。图片、音频等**不可直接序列化**的资源走导入系统：源文件 + `.import` 元数据 → 产物资源，源文件与产物分离（第八篇展开导入系统）。

### 4.3 复制规则：duplicate() 拷什么

```cpp
Ref<Resource> Resource::duplicate(bool p_subresources = false) const;
```

源码规则：

1. **只复制 `PROPERTY_USAGE_STORAGE` 的属性**——`resource_path` 注册为 `EDITOR` 用法（非 STORAGE），所以**副本不携带路径、也不进缓存**；
2. `Array`/`Dictionary`/`Packed*Array` 随 `p_subresources` 深拷贝；
3. OBJECT 属性：带 `NEVER_DUPLICATE` 的共享、带 `ALWAYS_DUPLICATE` 的必复制，其余看 `p_subresources`。

```gdscript
var shared := load("res://materials/fire.tres")
var copy := shared.duplicate()          # 浅复制：内部子资源仍共享
var deep := shared.duplicate(true)      # 深复制：子资源一并复制
```

---

## 五、local_to_scene：每个实例一份

### 5.1 机制

勾选 `resource_local_to_scene` 后，**每次实例化场景**时该资源会被复制成场景内唯一副本：

```cpp
Ref<Resource> Resource::duplicate_for_local_scene(Node *p_for_scene,
        HashMap<Ref<Resource>, Ref<Resource>> &p_remap_cache);
```

`p_remap_cache` 保证**同一资源在同一个场景里只复制一次**（场景内仍然共享），且会递归处理嵌套子资源。

### 5.2 脚本接口

```gdscript
@export var local_to_scene := true     # 对应 resource_local_to_scene

func _setup_local_to_scene() -> void:
    # 每个场景实例拿到独立副本后被调用，用于把副本初始化成"独立"状态
    reset()   # 例如把修改过的属性重置回默认
```

`setup_local_to_scene()` 内部先发出 `setup_local_to_scene_requested` 信号，再调用脚本可覆盖的 `_setup_local_to_scene()`；`get_local_scene()` 可查副本所属场景。

---

## 六、changed 信号与线程安全

### 6.1 emit_changed 的加载线程延迟

```cpp
void Resource::emit_changed();
```

资源数据变化时发出 `changed` 信号（`set_name()` 内部就会调用它）。实现里有一个线程细节：**如果在加载线程中（非主线程）**，发射会被转交给 `ResourceLoader` 延迟处理，避免加载中途触发监听者造成重入。其余情况直接 `emit_signal("changed")`。

### 6.2 实战：让依赖方跟随资源刷新

```gdscript
# 材质变了 → 重绘预览
material.changed.connect(_refresh_preview)

func _refresh_preview() -> void:
    queue_redraw()
```

编辑器的检查器实时刷新、粒子材质的即时预览，都建立在这条信号上。

---

## 七、自定义资源与自定义加载器

### 7.1 创建自定义资源

```gdscript
class_name ItemData
extends Resource

@export_range(0, 9999) var item_value: int = 100
@export var item_name: String = ""
@export var icon: Texture2D
@export var tags: PackedStringArray = []

func get_display_name() -> String:
    return item_name.to_upper()
```

保存为 `.tres` 后即可在检查器中编辑、在导出面板中共享，并作为"配置数据 + 引用"的标准载体。

### 7.2 自定义 ResourceFormatLoader

让引擎识别自定义扩展名（`.lvldata`）：

```gdscript
class_name LevelDataLoader
extends ResourceFormatLoader

func _get_recognized_extensions() -> PackedStringArray:
    return PackedStringArray(["lvldata"])

func _handles_type(type: StringName) -> bool:
    return type == &"LevelData"

func _get_resource_type(path: String) -> String:
    return "LevelData" if path.get_extension() == "lvldata" else ""

func _load(path: String, original_path: String,
           use_sub_threads: bool, cache_mode: int) -> Resource:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return null
    var level := LevelData.new()
    level.data = file.get_as_text()
    return level
```

在插件或 autoload 中注册（第二个参数决定是否插到队首）：

```gdscript
ResourceLoader.add_resource_format_loader(LevelDataLoader.new(), true)
```

此后 `load("res://levels/01.lvldata")` 就会返回 `LevelData` 实例。可覆盖的完整接口还包括 `_recognize_path`、`_get_resource_uid`、`_get_dependencies`、`_rename_dependencies`、`_exists` 等。

### 7.3 资源组织

```
res://
├── assets/          # 美术与音频等源资产
├── scenes/          # 场景
├── scripts/
└── data/            # .tres 配置数据
    ├── items/
    └── enemies/
```

---

## 八、管理最佳实践

### 8.1 内存管理

```gdscript
# 4.x 没有 ResourceLoader.unload() 与 ResourceQueue：
# 资源是引用计数的，最后一个引用释放后自动回收
var res := ResourceLoader.load("res://unused.tres")
res = null  # 引用计数归零，资源被释放（缓存条目被惰性清理）

# 不想进入全局缓存：同路径需要多份独立实例时
ResourceLoader.load("res://grid.tres", "", ResourceLoader.CACHE_MODE_IGNORE)
```

### 8.2 何时用哪种 CACHE_MODE

- 默认 `REUSE`：绝大多数场景；
- 编辑器热重载 / 需要"已有引用者原地看到新数据"：`REPLACE`；
- 同路径需要多份独立实例（网格数据、临时配置）：`IGNORE`；
- 嵌套资源也要独立/重载：对应的 `_DEEP` 变体。

### 8.3 常见错误速查

| 错误 | 含义与对策 |
|------|-----------|
| `possible cyclic resource inclusion` | A/B 资源相互引用，检查双向 `ext_resource` |
| `No loader found for resource` | 扩展名无对应 loader；自定义 loader 未注册 |
| `Make sure resources have been imported...` | 导出包缺导入产物，CI 先跑一次编辑器导入 |
| `ERR_BUSY`（线程加载） | 循环加载：加载任务里同步加载同一资源 |
| `Another resource is loaded from path ...` | 路径被占用且未抢占；需要覆盖用 `take_over_path()` |

---

## 九、总结

资源系统的核心是一条主线加三个机制：

```
load("res://x") → uid 解析 → (REUSE)查缓存 → remap → loader 加载
              → set_path 注册进 ResourceCache（同路径同实例）
```

- **path_cache 双重身份**：路径 + 缓存键，`set_path` 的抢占语义支撑编辑器的资源替换
- **CACHE_MODE**：REUSE/REPLACE/IGNORE 及 _DEEP 变体，覆盖"共享、原地刷新、多实例"三种需求
- **复制规则**：`duplicate()` 只拷 STORAGE 属性、副本不携带路径；`local_to_scene` 是独立的场景级复制机制
- **changed 信号**：资源变化的统一出口，连加载线程都会被妥善处理

---

## 🔗 延伸阅读

- **Resource**: <https://docs.godotengine.org/en/stable/classes/class_resource.html>
- **ResourceLoader**: <https://docs.godotengine.org/en/stable/classes/class_resourceloader.html>
- **ResourceFormatLoader**: <https://docs.godotengine.org/en/stable/classes/class_resourceformatloader.html>
- **源码位置**: `core/io/resource.cpp`, `core/io/resource_loader.cpp`, `core/io/resource_uid.cpp`

---

**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 6 篇：Godot 信号系统深度解析](/articles/06-signal-system.md)
**下一篇**: [第 8 篇：Godot 文件系统与跨平台架构](/articles/08-filesystem-platform.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
