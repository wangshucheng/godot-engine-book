# 第 61 篇：高级编辑器扩展

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 58 章 插件开发  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

本章是**第八卷的 API 参考**：把 Godot 提供的四类扩展点——Inspector 检查器、
Dock 面板、资源导入器、导出器——逐一讲清楚「有哪些官方入口、签名长什么样、
什么时候用哪个」。

> **卷内边界**：本章只讲**扩展点 API 本身**。
> 「编辑器里有什么能改的」是第 63 篇；「编辑器怎么快」是第 64 篇；
> 「怎么批量干活 / CI 怎么跑」是第 65 篇；「怎么写才不出错」是第 67 篇；
> 「插件怎么打包发布」是第 58 篇。

---

## 🎯 学习目标

- 掌握 EditorInspector 插件的完整回调链
- 学会把自定义属性挂到任意节点上
- 掌握 Dock / 底部面板 / 工具栏三类 UI 挂载点
- 打通资源导入的完整闭环（`.import` 文件 + 导入器钩子）
- 掌握 `EditorExportPlugin` 的导出钩子
- 了解 `EditorPlugin` 其余的官方扩展点

---

## 1. EditorInspector 插件

### 1.1 自定义属性编辑器

```gdscript
# 自定义 Inspector 插件
# ⚠️ 面向编辑器的脚本必须加 @tool，否则不会在编辑器进程内实例化
@tool
class_name CustomInspectorPlugin
extends EditorInspectorPlugin

# 支持的类型：这里用类名判断，项目里换成你自己的资源类
func _can_handle(object: Object) -> bool:
    return object is Resource and object.get_class() == "PlayerData"

# 解析属性：为特定属性创建自定义编辑器
func _parse_property(object: Object, type: int, name: String,
        hint_type: int, hint_string: String, usage_flags: int, wide: bool) -> bool:
    if name == "health" and object is Resource:
        var label := Label.new()
        label.text = "玩家生命值"
        add_custom_control(label)

        var slider := HSlider.new()
        slider.min_value = 0
        slider.max_value = 100
        slider.value = object.get("health")
        slider.custom_minimum_size.x = 200

        # 4.x 推荐用 Signal.connect()
        slider.value_changed.connect(
            func(value: float) -> void:
                object.set("health", value)
                object.notify_property_list_changed()
        )

        add_custom_control(slider)
        # 返回 true 表示「顶掉内建编辑器」；返回 false 则插在内建编辑器之前
        return true

    return false

# 添加分类标题
func _parse_category(object: Object, category: String) -> void:
    if category == "Combat":
        var label := Label.new()
        label.text = "=== 战斗属性 ==="
        add_custom_control(label)

# 在属性列表末尾追加内容
func _parse_end(object: Object) -> void:
    var btn := Button.new()
    btn.text = "重置数值"
    btn.pressed.connect(func() -> void:
        object.set("health", 100)
        object.notify_property_list_changed()
    )
    add_custom_control(btn)
```

**注册方式**（这是 Godot 唯一的 Inspector 插件注册入口）：

```gdscript
# 注册检查器插件
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

var _inspector_plugin: EditorInspectorPlugin

func _enter_tree() -> void:
    _inspector_plugin = CustomInspectorPlugin.new()
    add_inspector_plugin(_inspector_plugin)

func _exit_tree() -> void:
    # 必须注销，否则会泄漏并产生难以定位的异常行为
    if _inspector_plugin:
        remove_inspector_plugin(_inspector_plugin)
        _inspector_plugin = null
```

> **机制说明**：Godot **没有** `_get_plugins()` 这样的回调让你返回插件列表。
> `EditorPlugin.add_inspector_plugin(plugin)` 必须传入一个**已经 new 出来的实例**，
> 并在 `_exit_tree()` 里用 `remove_inspector_plugin()` 对称注销。
> `EditorInspectorPlugin` 的回调顺序是
> `_can_handle()` → `_parse_begin()` → `_parse_group()` / `_parse_category()` /
> `_parse_property()`（逐个属性）→ `_parse_end()`。

### 1.2 自定义属性提示（tooltip）

```gdscript
# 自定义属性提示
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name TooltipPlugin
extends EditorInspectorPlugin

func _parse_begin(object: Object) -> void:
    # 在属性列表最前面插一个说明块
    var tooltip := "伤害值：\n"
    tooltip += "- 基础伤害\n"
    tooltip += "- 受力量加成\n"
    tooltip += "- 可被暴击放大"

    var label := Label.new()
    label.text = tooltip
    label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_custom_control(label)

    # 同时把提示写进对象的 metadata，供其它系统读取
    object.set_meta("_tooltip", tooltip)

func _parse_property(object: Object, type: int, name: String,
        hint_type: int, hint_string: String, usage_flags: int, wide: bool) -> bool:
    if name == "damage":
        # 从 metadata 读回提示（证明 set_meta 确实写进去了）
        var tip: String = object.get_meta("_tooltip", "")
        if not tip.is_empty():
            var label := Label.new()
            label.text = tip
            add_custom_control(label)
    return false
```

> **机制说明**：`EditorInspectorPlugin` 没有「设置属性 tooltip」的方法。
> 要把额外信息传给检查器，官方路径是 **对象 metadata**
> （`Object.set_meta()` / `get_meta()`），再用 `add_custom_control()` 把它显示出来。
> metadata 名字以 `_` 开头时被视为**仅编辑器可见**，不会出现在 Inspector 里。

### 1.3 自定义节点属性（`_get_property_list` / `_set` / `_get`）

上面两节改的是「编辑器怎么显示已有属性」。这一节反过来：**让任意对象
多出属性**，这是 61 §1 的另一半，也是编辑器插件最常被问到的能力。

```gdscript
# 自定义属性：让节点在 Inspector 里多出可编辑的字段
# ⚠️ 面向编辑器的脚本必须加 @tool，否则 _get_property_list() 不会在编辑器里被调用
@tool
class_name CustomPropertyNode
extends Node2D

# 真实数据存在普通成员里
var _stats: Dictionary = {"hp": 100, "mp": 50}

func _get_property_list() -> Array[Dictionary]:
    # 返回额外的属性列表；每项至少要有 name 与 type
    return [
        {
            "name": "hp",
            "type": TYPE_INT,
            "hint": PROPERTY_HINT_RANGE,
            "hint_string": "0,999,1",
            "usage": PROPERTY_USAGE_DEFAULT,
        },
        {
            "name": "mp",
            "type": TYPE_INT,
            "hint": PROPERTY_HINT_RANGE,
            "hint_string": "0,999,1",
            "usage": PROPERTY_USAGE_DEFAULT,
        },
    ]

func _get(property: StringName) -> Variant:
    # 只有当属性出现在 get_property_list() 里时，这个回调才会被调用
    if property in _stats:
        return _stats[property]
    return null

func _set(property: StringName, value: Variant) -> bool:
    # 返回 true 表示「这个属性我已经处理了」，返回 false 交给引擎默认逻辑
    if property in _stats:
        _stats[property] = value
        return true
    return false

func _property_can_revert(property: StringName) -> bool:
    # 告诉检查器这个属性有「默认值」，从而显示还原箭头
    return property in _stats

func _property_get_revert(property: StringName) -> Variant:
    # 返回该属性的默认值
    if property in _stats:
        return 100
    return null
```

> **机制说明**：
> - `_get_property_list()` 返回的数组会被**追加**到 `get_property_list()` 的结果里；
>   每项至少要含 `name` 与 `type`。
> - `_get()` / `_set()` 只有在属性**确实出现在属性列表里**时才会被调用，
>   否则 `set("hp", 1)` 会静默失败。
> - `_property_can_revert()` 与 `_property_get_revert()` 必须**成对实现**：
>   只有前者返回 `true`，后者才会被调用；两者都实现后，检查器才会显示还原箭头。
> - 属性列表的结构变化后要调用 `notify_property_list_changed()` 通知编辑器刷新。
> - 4.3 的 `Object.xml` 明确写着：脚本不是 `@tool` 时，`_get_property_list()`
>   **不会在编辑器里被调用**。

---

## 2. 自定义 Dock 面板

### 2.1 创建 Dock 面板

`add_control_to_dock()` / `remove_control_from_docks()` 是 **`EditorPlugin` 的成员
函数**，`Control` 上并没有它们；`DOCK_SLOT_RIGHT_UL` 同样是 `EditorPlugin`
的常量。所以正确做法是拆成两个类：**插件负责挂载，纯控件只负责 UI**。

```gdscript
# 纯 UI 控件：只负责界面，不碰任何 EditorPlugin API
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name CustomDock
extends Control

var dock_name: String = "My Dock"

var vbox: VBoxContainer
var tree: Tree

func _ready() -> void:
    _setup_ui()

func _setup_ui() -> void:
    vbox = VBoxContainer.new()
    add_child(vbox)

    var title := Label.new()
    title.text = dock_name
    title.add_theme_font_size_override("font_size", 16)
    vbox.add_child(title)

    var toolbar := HBoxContainer.new()
    vbox.add_child(toolbar)

    var refresh_btn := Button.new()
    refresh_btn.text = "刷新"
    refresh_btn.pressed.connect(_on_refresh)
    toolbar.add_child(refresh_btn)

    var settings_btn := Button.new()
    settings_btn.text = "设置"
    settings_btn.pressed.connect(_on_settings)
    toolbar.add_child(settings_btn)

    tree = Tree.new()
    tree.columns = 2
    vbox.add_child(tree)

    _populate_tree()

func _populate_tree() -> void:
    tree.clear()
    var root := tree.create_item()
    root.set_text(0, "项目资源")

    var item := tree.create_item(root)
    item.set_text(0, "玩家预制体")
    item.set_text(1, "5 个")
    item.set_icon(0, get_editor_icon("Node2D"))

    item = tree.create_item(root)
    item.set_text(0, "敌人预制体")
    item.set_text(1, "10 个")
    item.set_icon(0, get_editor_icon("CharacterBody2D"))

func get_editor_icon(icon_name: String) -> Texture2D:
    # 编辑器图标要从「编辑器主题」里取，不是项目主题
    return EditorInterface.get_editor_theme().get_icon(icon_name, "EditorIcons")

func _on_refresh() -> void:
    _populate_tree()

func _on_settings() -> void:
    pass
```

```gdscript
# 插件：只负责把控件挂到 Dock 上，以及对称清理
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name CustomDockPlugin
extends EditorPlugin

var _dock: CustomDock

func _enter_tree() -> void:
    _dock = CustomDock.new()
    # slot 是 EditorPlugin.DockSlot 枚举，共 8 个槽位
    add_control_to_dock(EditorPlugin.DOCK_SLOT_RIGHT_UL, _dock)

func _exit_tree() -> void:
    if _dock:
        # 先从 Dock 摘掉，再释放；对已在场景树中的节点用 queue_free()
        remove_control_from_docks(_dock)
        _dock.queue_free()
        _dock = null
```

> **机制说明**：`EditorPlugin.DockSlot` 枚举只有 8 个槽位
> （`DOCK_SLOT_LEFT_UL` / `LEFT_BL` / `LEFT_UR` / `LEFT_BR` /
> `RIGHT_UL` / `RIGHT_BL` / `RIGHT_UR` / `RIGHT_BR`）加一个
> `DOCK_SLOT_MAX`（表示枚举大小，**不是可用槽位**）。
> 4.3 **没有** `DOCK_SLOT_BOTTOM_DRAG` 这样的值。
> 底部面板不是 Dock 槽位，用 `add_control_to_bottom_panel()`（见 §5.3）。

### 2.2 资源浏览器

```gdscript
# 自定义资源浏览器
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name ResourceBrowserDock
extends CustomDock

var file_filter: String = "*.tres,*.res,*.tscn"

var search_box: LineEdit
var file_list: ItemList

func _setup_ui() -> void:
    super._setup_ui()

    search_box = LineEdit.new()
    search_box.placeholder_text = "搜索资源..."
    search_box.text_changed.connect(_on_search)
    vbox.add_child(search_box)

    file_list = ItemList.new()
    file_list.icon_mode = ItemList.ICON_MODE_TOP
    file_list.max_columns = 4
    vbox.add_child(file_list)

    _load_resources()

func _load_resources() -> void:
    file_list.clear()
    var dir := DirAccess.open("res://")
    if dir:
        _scan_directory(dir, "res://")

func _scan_directory(dir: DirAccess, path: String) -> void:
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if dir.current_is_dir():
            if file_name != ".import" and file_name != ".godot":
                _scan_directory(dir, path + "/" + file_name)
        else:
            if _matches_filter(file_name):
                _add_file_to_list(path + "/" + file_name)
        file_name = dir.get_next()
    dir.list_dir_end()

func _matches_filter(file_name: String) -> bool:
    for filter in file_filter.split(","):
        if file_name.ends_with(filter.trim_prefix("*")):
            return true
    return false

func _add_file_to_list(path: String) -> void:
    var icon := get_editor_icon("ResourceFile")
    file_list.add_item(path.get_file(), icon)
    var idx := file_list.item_count - 1
    file_list.set_item_tooltip(idx, path)

func _on_search(text: String) -> void:
    for i in range(file_list.item_count):
        var item_text := file_list.get_item_text(i)
        file_list.set_item_disabled(i, not text.is_empty() and not item_text.contains(text))
```

---

## 3. 资源导入插件

### 3.1 完整导入闭环

一个自定义导入器要跑通，需要四个部分配合：

| 环节 | 位置 | 说明 |
|---|---|---|
| 源文件 | `res://xxx.mydata` | 你要解析的原始文件 |
| `.import` 文件 | `res://xxx.mydata.import` | 导入参数与产物路径的索引 |
| 导入产物 | `res://.godot/imported/xxx.mydata-<md5>.res` | 真正的资源 |
| 导入器 | `EditorImportPlugin` 子类 | 把源文件变成资源 |

`.import` 文件是**类 INI 格式**的文本，长这样：

```ini
[remap]

importer="my.mydata.importer"
type="Resource"
uid="uid://c8kx0y1ab2q3t"
path="res://.godot/imported/xxx.mydata-1a2b3c4d.res"
metadata={
"vram_texture": false
}

[deps]

source_file="res://xxx.mydata"
dest_files=["res://.godot/imported/xxx.mydata-1a2b3c4d.res"]

[params]

compress=0
scale=1.0
```

其中 `[remap]` 段由导入器写、`[params]` 段存用户可见的导入选项、
`[deps]` 段描述产物依赖。`[remap]` 段的 `path` 指向 `.godot/imported/` 下的
实际文件，`uid` 是资源的唯一 ID。

```gdscript
# 自定义资源导入插件（完整版）
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name CustomImportPlugin
extends EditorImportPlugin

# 唯一名：编辑器用它标识导入器，不能与其它导入器重名
func _get_importer_name() -> String:
    return "my.custom.importer"

# 在导入窗口里显示的名字（接在 "Import as " 后面）
func _get_visible_name() -> String:
    return "Custom Data"

# 本导入器认领的扩展名
func _get_recognized_extensions() -> PackedStringArray:
    return ["mydata"]

# 产物的保存扩展名（存到 .godot/imported/ 下）
func _get_save_extension() -> String:
    return "tres"

# 产物的资源类型
func _get_resource_type() -> String:
    return "Resource"

# 导入预设数量：必须 >= 1，否则编辑器不展示任何导入选项，
# _get_import_options() / _get_option_visibility() 全部变成死代码
func _get_preset_count() -> int:
    return 1

# 预设名：与 _get_preset_count() 一一对应（这里只有第 0 个）
func _get_preset_name(preset_index: int) -> String:
    return "Default"

# 导入选项：数组下标 0 对应上面第 0 个预设
func _get_import_options(path: String, preset_index: int) -> Array[Dictionary]:
    return [
        {"name": "compress", "default_value": false, "type": TYPE_BOOL},
        {"name": "scale", "default_value": 1.0, "type": TYPE_FLOAT,
         "hint": PROPERTY_HINT_RANGE, "hint_string": "0.1,4.0,0.1"},
    ]

# 某个选项是否可见：4.3 的签名是 3 参
# (path, option_name, options)，master 也是 3 参
func _get_option_visibility(path: String, option_name: StringName, options: Dictionary) -> bool:
    # 示例：只有勾选了 compress 才显示压缩质量
    if option_name == "lossy_quality" and options.has("compress"):
        return bool(options["compress"])
    return true

# 是否可以并行导入：导入器是线程安全的就返回 true
func _can_import_threaded() -> bool:
    return true

# 导入顺序：数字小的先导入。
# ResourceImporter.IMPORT_ORDER_DEFAULT = 0，IMPORT_ORDER_SCENE = 100。
# 自定义导入器通常应给一个比 100 小的值，避免场景先于它被导入
func _get_import_order() -> int:
    return 50

# 优先级：同一扩展名有多个导入器时，数字大的优先（默认 1.0）
func _get_priority() -> float:
    return 1.0

# 真正的导入工作
func _import(source_file: String, save_path: String, options: Dictionary,
        platform_variants: PackedStringArray, gen_files: PackedStringArray) -> Error:
    var file := FileAccess.open(source_file, FileAccess.READ)
    if file == null:
        return FAILED
    var content := file.get_as_text()
    file.close()

    var resource := Resource.new()
    resource.set_meta("source", source_file)
    resource.set_meta("content", content)

    # 如果导入过程还会产出别的资源文件（例如贴图），
    # 用 append_import_external_resource() 触发它们的导入；
    # 它只能在 _import() 回调内部调用。
    # var tex_path := source_file + ".png"
    # if FileAccess.file_exists(tex_path):
    #     append_import_external_resource(tex_path)

    # 产物必须存到 save_path + "." + _get_save_extension()
    var save_path_full := save_path + "." + _get_save_extension()
    return ResourceSaver.save(resource, save_path_full)
```

**注册导入器**：

```gdscript
# 注册导入器
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

var _importer: CustomImportPlugin

func _enter_tree() -> void:
    _importer = CustomImportPlugin.new()
    add_import_plugin(_importer)

func _exit_tree() -> void:
    if _importer:
        remove_import_plugin(_importer)
        _importer = null
```

> **机制说明**：
> - `EditorImportPlugin` **继承自 `ResourceImporter`**（不是 `RefCounted`）。
>   `ResourceImporter` 提供 `ImportOrder` 枚举：`IMPORT_ORDER_DEFAULT = 0`、
>   `IMPORT_ORDER_SCENE = 100`。
> - `append_import_external_resource(path, custom_options, custom_importer, generator_parameters)`
>   **只能在 `_import()` 内部调用**。它做两件事：触发外部资源的导入；
>   把 `generator_parameters` 写进该资源的 `.import` 文件 `[remap]` 段的
>   `generator_parameters` 键（例如存源数据的 md5）。
> - `_get_option_visibility()` 在 **4.3 与 master 上都是 3 个参数**
>   `(path, option_name, options)`；写 2 参会在 4.3 上签名不匹配。

### 3.2 批量导入工具

```gdscript
# 批量导入工具
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name BatchImportTool
extends EditorPlugin

func _enter_tree() -> void:
    add_tool_menu_item("批量导入资源", _batch_import)

func _exit_tree() -> void:
    remove_tool_menu_item("批量导入资源")

func _batch_import() -> void:
    var dir_dialog := EditorFileDialog.new()
    dir_dialog.file_mode = EditorFileDialog.FILE_MODE_OPEN_DIR
    dir_dialog.access = EditorFileDialog.ACCESS_RESOURCES
    dir_dialog.dir_selected.connect(_on_dir_selected)
    add_child(dir_dialog)
    dir_dialog.popup_centered_ratio(0.5)

func _on_dir_selected(path: String) -> void:
    var dir := DirAccess.open(path)
    if dir == null:
        return
    var count := 0

    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if file_name.ends_with(".mydata"):
            _import_file(path + "/" + file_name)
            count += 1
        file_name = dir.get_next()
    dir.list_dir_end()

    print("批量导入完成：%d 个文件" % count)

func _import_file(path: String) -> void:
    # Godot 4 的导入器是 EditorImportPlugin：由编辑器按扩展名自动匹配并调用 _import()，
    # 不存在 EditorResourceImporter.new() 再 import() 的用法。
    # 想让文件重新走导入流程，应通过 EditorFileSystem 触发：
    var fs := EditorInterface.get_resource_filesystem()
    if fs:
        fs.update_file(path)   # 标记该文件需要重新导入
        fs.scan()              # 重新扫描文件系统
```

---

## 4. EditorExportPlugin（导出扩展点）

`EditorExportPlugin` 在**导出发生时**介入：可以改导出选项、过滤要导出的文件、
往包里塞额外文件、定制资源与场景。

```gdscript
# 导出扩展点
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name CustomExportPlugin
extends EditorExportPlugin

# 唯一名：导出器按名字排序，必须实现
func _get_name() -> String:
    return "MyExportPlugin"

# 是否支持某个平台
func _supports_platform(platform: EditorExportPlatform) -> bool:
    return platform is EditorExportPlatformPC

# 给这个导出插件增加选项（出现在导出对话框的插件分区里）
func _get_export_options(platform: EditorExportPlatform) -> Array[Dictionary]:
    return [
        {
            "option": {
                "name": "my_plugin/include_debug_symbols",
                "type": TYPE_BOOL,
            },
            "default_value": false,
            "update_visibility": true,
        },
    ]

# 声明这个预设需要哪些特性标签
func _get_export_features(platform: EditorExportPlatform, debug: bool) -> PackedStringArray:
    return PackedStringArray(["my_plugin"])

# 导出开始
func _export_begin(features: PackedStringArray, is_debug: bool, path: String, flags: int) -> void:
    print("开始导出：", path, " 特性：", features)

# 逐个文件回调：可以 skip() 掉某个文件
func _export_file(path: String, type: String, features: PackedStringArray) -> void:
    if path.ends_with(".mydata"):
        # 不导出这类中间文件
        skip()
        return
    if path.ends_with("config.json"):
        # 把一个自定义文件塞进包里
        add_file("res://generated/config.json", PackedByteArray("{}".to_utf8_buffer()), false)

# 导出结束
func _export_end() -> void:
    print("导出结束")
```

```gdscript
# 注册导出插件
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

var _exporter: CustomExportPlugin

func _enter_tree() -> void:
    _exporter = CustomExportPlugin.new()
    add_export_plugin(_exporter)

func _exit_tree() -> void:
    if _exporter:
        remove_export_plugin(_exporter)
        _exporter = null
```

> **机制说明**：`EditorExportPlugin` 继承自 `RefCounted`（不是 Node），
> 关键钩子共五个：`_get_name()`（必须实现）、`_supports_platform()`、
> `_get_export_options()`、`_get_export_features()`、
> `_export_begin()` / `_export_file()` / `_export_end()`。
> 在 `_export_file()` 里调 `skip()` 可以把当前文件排除出导出包；
> `add_file(path, bytes, remap)` 可以往包里追加自定义文件。
> `EditorExportPlatform` 是**抽象基类**，不能实例化；4.7.2 起它有了**实例方法** `export_project(preset, debug, path, flags, notify)`（要传 `EditorExportPreset`），但那是给导出插件与编辑器内部用的——脚本侧完全自动化的导出仍应走命令行（见第 65 篇 CI 一节）。

---

## 5. EditorPlugin 的其余官方扩展点

### 5.1 主屏幕扩展

```gdscript
# 主屏幕扩展：在工作区选择器里加一个自己的标签页
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

var _panel: Control

func _enter_tree() -> void:
    _panel = preload("res://addons/my_plugin/my_panel.tscn").instantiate()
    # get_editor_main_screen() 返回的是 VBoxContainer，不是 Viewport；
    # 子控件要占满空间必须设 size_flags_vertical = SIZE_EXPAND_FILL
    _panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
    EditorInterface.get_editor_main_screen().add_child(_panel)
    _panel.hide()

func _has_main_screen() -> bool:
    # 返回 true 才会占用工作区选择器的一个位置
    return true

func _make_visible(visible: bool) -> void:
    # 主屏幕插件必须自己管理可见性
    if _panel:
        _panel.visible = visible

func _get_plugin_name() -> String:
    return "My Plugin"

func _get_plugin_icon() -> Texture2D:
    # 用编辑器主题里的内建图标（推荐 16×16 白色透明底）
    return EditorInterface.get_editor_theme().get_icon("Node", "EditorIcons")
```

### 5.2 视口输入转发

```gdscript
# 视口输入转发
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

func _handles(object: Object) -> bool:
    # 只有 _handles() 返回 true 时，下面的输入转发才会被调用
    return object is Node2D

func _forward_canvas_gui_input(event: InputEvent) -> bool:
    # 2D 视口：返回 true 表示吃掉这个事件，不再传给其它编辑器类
    if event is InputEventMouseMotion:
        return false
    return false

func _forward_3d_gui_input(camera: Camera3D, event: InputEvent) -> int:
    # 3D 视口：返回 EditorPlugin.AFTER_GUI_INPUT_STOP / PASS / CUSTOM
    if event is InputEventMouseButton:
        return EditorPlugin.AFTER_GUI_INPUT_STOP
    return EditorPlugin.AFTER_GUI_INPUT_PASS
```

### 5.3 底部面板与工具栏

```gdscript
# 底部面板 / 工具栏 / 菜单
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

var _bottom_button: Button
var _toolbar_button: Button

func _enter_tree() -> void:
    # 底部面板：返回新增的按钮引用，自己负责显示/隐藏
    _bottom_button = add_control_to_bottom_panel(_make_bottom_panel(), "我的面板")

    # 工具栏：CONTAINER_TOOLBAR 是 CustomControlContainer 枚举值
    _toolbar_button = Button.new()
    _toolbar_button.text = "我的工具"
    _toolbar_button.pressed.connect(_on_toolbar_pressed)
    add_control_to_container(EditorPlugin.CONTAINER_TOOLBAR, _toolbar_button)

    # 「项目 → 工具」菜单项
    add_tool_menu_item("我的插件/执行", _on_tool_menu)

func _exit_tree() -> void:
    if _bottom_button:
        # 官方文档明确要求：先 remove，再自己 free
        remove_control_from_bottom_panel(_bottom_button)
        _bottom_button.queue_free()
        _bottom_button = null

    if _toolbar_button:
        # remove_control_from_container() 是 2 参：
        # (CustomControlContainer 枚举, 控件)
        remove_control_from_container(EditorPlugin.CONTAINER_TOOLBAR, _toolbar_button)
        _toolbar_button.queue_free()
        _toolbar_button = null

    remove_tool_menu_item("我的插件/执行")

func _make_bottom_panel() -> Control:
    var panel := VBoxContainer.new()
    var label := Label.new()
    label.text = "底部面板内容"
    panel.add_child(label)
    return panel

func _on_toolbar_pressed() -> void:
    if _bottom_button:
        _bottom_button.button_pressed = not _bottom_button.button_pressed

func _on_tool_menu() -> void:
    pass
```

### 5.4 其它注册入口一览

```gdscript
# 其它注册入口
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

func _enter_tree() -> void:
    # 3D 操纵器插件
    # add_node_3d_gizmo_plugin(gizmo_plugin)

    # 调试器插件
    # add_debugger_plugin(debugger_plugin)

    # 翻译解析插件
    # add_translation_parser_plugin(parser)

    # 资源转换插件
    # add_resource_conversion_plugin(converter)

    # 场景格式导入器（把自定义 3D 格式导成场景）
    # add_scene_format_importer_plugin(importer)

    # 场景后导入插件（给 3D 资产导入对话框加选项）
    # add_scene_post_import_plugin(plugin)

    # Autoload 单例：插件间通信的官方手段
    # add_autoload_singleton("MyPluginHub", "res://addons/my_plugin/hub.gd")

    # 自定义节点类型（创建对话框里多一项）
    # add_custom_type("MyNode", "Node2D", preload("res://addons/my_plugin/my_node.gd"), icon)

func _exit_tree() -> void:
    # 上面对应的 remove_* 都要调用；Autoload 用 remove_autoload_singleton()
    pass
```

### 5.5 编辑器图标与主题

```gdscript
# 编辑器图标与主题
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

func _get_plugin_icon() -> Texture2D:
    # 正规取用方式：编辑器主题的 "EditorIcons" 类型图
    var theme := EditorInterface.get_editor_theme()
    return theme.get_icon("Node", "EditorIcons")

func _get_plugin_color() -> Color:
    # 也可以从主题取色
    return EditorInterface.get_editor_theme().get_color("accent_color", "Editor")

func get_dock_icon() -> Texture2D:
    # EditorPlugin 不是 Control，没有 get_theme_icon()（那是 Control 的方法）。
    # 这里同样从编辑器主题里取：
    return EditorInterface.get_editor_theme().get_icon("Node", "EditorIcons")
```

> **机制说明**：
> - `EditorInterface.get_editor_theme()` 返回编辑器的 `Theme`；
>   编辑器内置图标在 `"EditorIcons"` 类型下，颜色在 `"Editor"` 类型下。
> - 控件上取图标应该用 `Control.get_theme_icon(name, type)`——
>   它会沿控件树向上找到正确的 Theme。
> - **编辑器主题预设**由编辑器设置 `interface/theme/preset` 控制。
>   4.3 源码（`editor/themes/editor_theme_manager.cpp`）里识别这些取值：
>   `Default`（深色默认）、`Breeze Dark`、`Godot 2`、`Gray`、`Light`、
>   `Solarized (Dark)`、`Solarized (Light)`、`Black (OLED)`、
>   `Custom`（用户自定义过 accent/base color 时自动落到这一档）。
>   **注意没有 `"Dark"` 这个取值**——想用深色默认主题请写 `"Default"`。
>   相关的还有 `interface/theme/contrast`（默认 0.3）、
>   `interface/theme/spacing_preset`（`Default` / `Compact` / `Spacious`）、
>   `interface/theme/custom_theme`。
> - 4.6 起的编辑器主题体系与「可移动 / 浮动停靠面板」有较大变化，
>   **本文基线是 4.3**；4.6 分支的设置键名以编辑器实际显示为准
>   （本机 `4.3` 与 `master` 上无法核对 4.6 的键名，故此处不给结论）。

---

## 6. 插件发布

插件的打包、发布到 AssetLib 的硬性规则（zip 根目录必须直接含
`addons/<插件名>/plugin.cfg`、图标与截图规格、版本号必须与 `plugin.cfg` 一致、
审核要点）见**第 58 篇 §4.4**。

`plugin.cfg` 的规范也在第 58 篇：它是 INI 格式，元数据全部写在 `[plugin]` 段
（`name` / `description` / `author` / `version` / `script`），
**4.3 不支持 `[dependencies]` 段**——依赖要在自己的 `_enter_tree()` 里用
`EditorInterface.is_plugin_enabled()` 自行检测。

---

## 📝 本章总结

### 核心要点

1. **Inspector 插件**靠 `add_inspector_plugin()` 注册，六个回调按
   `_can_handle` → `_parse_begin` → `_parse_property` → `_parse_end` 顺序触发
2. **自定义属性**靠 `_get_property_list()` / `_get()` / `_set()` /
   `_property_can_revert()` / `_property_get_revert()`，且脚本必须是 `@tool`
3. **Dock 挂载**要用 `EditorPlugin` 的 `add_control_to_dock()`，
   控件本身不能调用它；底部面板走 `add_control_to_bottom_panel()`
4. **资源导入**是四段式闭环：源文件 → `.import` 文件 → `.godot/imported/` 产物 →
   导入器；`_get_preset_count()` 必须 ≥ 1
5. **导出扩展**用 `EditorExportPlugin` 的五个钩子，`skip()` 可排除文件
6. **编辑器图标**从 `EditorInterface.get_editor_theme()` 取，
   主题预设置键是 `interface/theme/preset`（没有 `"Dark"` 这个值）

### 关键 API 速查

| API | 所属类 | 用途 |
|---|---|---|
| `add_inspector_plugin()` | EditorPlugin | 注册检查器插件 |
| `add_control_to_dock()` | EditorPlugin | 挂载到 Dock 槽位（8 个） |
| `add_control_to_bottom_panel()` | EditorPlugin | 挂载到底部面板 |
| `add_control_to_container()` | EditorPlugin | 挂载到工具栏等容器 |
| `remove_control_from_container()` | EditorPlugin | 从容器移除（2 参） |
| `add_import_plugin()` | EditorPlugin | 注册导入器 |
| `add_export_plugin()` | EditorPlugin | 注册导出器 |
| `add_tool_menu_item()` | EditorPlugin | 「项目 → 工具」菜单项 |
| `add_autoload_singleton()` | EditorPlugin | 注册 Autoload 单例 |
| `get_undo_redo()` | EditorPlugin | 取编辑器撤销/重做管理器（见第 67 篇） |
| `get_editor_theme()` | EditorInterface | 取编辑器 Theme |
| `get_resource_filesystem()` | EditorInterface | 取 EditorFileSystem 单例 |
| `append_import_external_resource()` | EditorImportPlugin | 在 `_import()` 内触发外部资源导入 |

---

## 🔗 延伸阅读

- **官方文档 · 检查器插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/inspector_plugins.html>
- **官方文档 · 导入插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/import_plugins.html>
- **官方文档 · 导出插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/export_plugins.html>
- **官方文档 · 自定义节点类型**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/custom_nodes.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorplugin.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorinterface.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_object.html>（自定义属性）
- **源码位置**: `editor/plugins/editor_plugin.cpp`, `editor/import/editor_import_plugin.cpp`

---

## 📋 下一章预告

**第 63 篇：编辑器高级功能**

- 编辑器脚本（EditorScript）的正确用法
- 编辑器内调试控制台
- 编辑器扩展点总览：哪些地方能挂钩子

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 58 篇：插件开发](/articles/58-plugin-development.md)
**下一篇**: [第 63 篇：编辑器高级功能](/articles/63-editor-advanced-features.md)

---

*写作时间：2026-03-21*  
*字数：约 1,700 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
