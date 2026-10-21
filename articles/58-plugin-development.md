# 第 58 篇：插件开发

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 无（建议先读第一卷引擎基础）  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

Godot 的插件系统是扩展编辑器功能的核心机制。通过插件，开发者可以创建自定义工具、扩展编辑器功能、创建新的工作流。本章将深入探讨插件架构、插件开发流程、插件通信以及最佳实践。

---

## 🎯 学习目标

- 理解插件架构和组件
- 掌握插件开发流程
- 学会插件通信机制
- 熟悉插件分发和安装
- 掌握插件最佳实践

---

## 1. 插件架构

### 1.1 插件类型

```
插件类型:
┌─────────────────────────────────────────────────────────────┐
│                      插件类型                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EditorPlugin：编辑器插件（扩展编辑器功能）             │
│  2. EditorInspectorPlugin：检查器插件（自定义属性显示）    │
│  3. EditorImportPlugin：导入插件（支持新文件格式）         │
│  4. EditorExportPlugin：导出插件（自定义导出流程）         │
│  5. EditorTranslationParserPlugin：翻译解析插件            │
│  6. EditorDebuggerPlugin：调试器插件（自定义调试面板）     │
│  7. EditorNode3DGizmoPlugin：3D 操纵器插件                │
│  8. EditorResourceConversionPlugin：资源转换插件           │
│  9. EditorSceneFormatImporter：场景格式导入插件           │
│  10. EditorScenePostImportPlugin：场景后导入插件           │
│                                                             │
│  ⚠️ 不存在 EditorSettingsPlugin / EditorFileSystemPlugin / │
│  EditorResourcePreviewPlugin 这三个类（4.x 已移除或从未有） │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

> **机制说明**：4.x 里所有「插件基类」都继承自 `RefCounted`（`EditorImportPlugin`
> 继承 `ResourceImporter`，`EditorPlugin` 继承 `Node`），由 `EditorPlugin` 通过
> `add_inspector_plugin()` / `add_import_plugin()` / `add_export_plugin()` 等方法
> 注册。**设置项**不需要专用基类：用 `EditorInterface.get_editor_settings().set_setting()`
> 写入即可；**资源缩略图预览**用 `EditorInterface.get_resource_previewer()` 返回的
> `EditorResourcePreview` 单例，没有「预览插件基类」这种东西。

### 1.2 插件生命周期

```gdscript
# 插件生命周期：EditorPlugin 的两个关键回调
# ⚠️ 面向编辑器的脚本必须加 @tool，否则不会在编辑器进程内实例化
@tool
extends EditorPlugin

func _enter_tree():
    # 插件启用时调用
    print("Plugin enabled")
    _initialize()

func _exit_tree():
    # 插件禁用时调用
    print("Plugin disabled")
    _cleanup()

func _initialize():
    # 初始化插件
    _setup_ui()
    _register_handlers()

func _cleanup():
    # 清理资源
    _remove_ui()
    _unregister_handlers()

func _setup_ui():
    # 设置 UI 控件
    pass

func _remove_ui():
    # 移除 UI 控件
    pass

func _register_handlers():
    # 注册事件处理
    pass

func _unregister_handlers():
    # 注销事件处理
    pass
```

> **机制说明**：`EditorPlugin` 继承自 `Node`，所以 `_enter_tree()` / `_exit_tree()`
> 是它进入/离开编辑器场景树时由引擎自动触发的，**不需要也无法手工调用**。
> 插件脚本必须带 `@tool` 注解，否则在编辑器里不会被执行。

### 1.3 插件依赖

```gdscript
# 插件依赖管理
# ⚠️ EditorInterface 只在编辑器进程内存在，面向编辑器的脚本必须加 @tool
@tool
extends RefCounted

# 依赖的插件「目录名」（res://addons/<目录名>/），不是 plugin.cfg 的路径
var dependencies: Dictionary = {}

func check_dependencies() -> bool:
    # 检查依赖：EditorInterface.is_plugin_enabled() 接受插件目录名
    for dep in dependencies:
        if not is_plugin_available(dep):
            return false
    return true

func is_plugin_available(plugin_dir_name: String) -> bool:
    # 官方 API：判断指定插件是否已启用，参数是插件目录名
    return EditorInterface.is_plugin_enabled(plugin_dir_name)

# 启用插件的正规做法：EditorInterface.set_plugin_enabled()
# ⚠️ 参数同样是插件「目录名」，不是 res://addons/x/plugin.cfg 路径
func enable_plugin(plugin_dir_name: String) -> void:
    if EditorInterface.is_plugin_enabled(plugin_dir_name):
        return
    EditorInterface.set_plugin_enabled(plugin_dir_name, true)

func disable_plugin(plugin_dir_name: String) -> void:
    EditorInterface.set_plugin_enabled(plugin_dir_name, false)

func add_dependency(plugin_name: String, version: String) -> void:
    # 添加依赖
    dependencies[plugin_name] = version

func remove_dependency(plugin_name: String) -> void:
    # 移除依赖
    dependencies.erase(plugin_name)

func get_dependencies_list() -> Array:
    # 获取依赖列表
    return dependencies.keys()
```

> **机制说明**：`editor_plugins/enabled` 这个项目设置键名没有错，但 4.2 以后官方
> 推荐用 `EditorInterface.set_plugin_enabled()` / `is_plugin_enabled()`，两者参数
> 都是**插件目录名**。直接改写 `editor_plugins/enabled` 仍然可行（元素是
> `res://addons/<目录名>/plugin.cfg` 形式的路径），但跳过了编辑器的启用/禁用流程，
> 不推荐。

---

## 2. 插件开发

### 2.1 创建插件

```gdscript
# 创建插件：4.x 真实存在的插件基类
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends RefCounted

func create_editor_plugin() -> EditorPlugin:
    # 编辑器插件：继承 Node，由编辑器在 _enter_tree() 里接管
    return EditorPlugin.new()

func create_inspector_plugin() -> EditorInspectorPlugin:
    # 检查器插件：继承 RefCounted，用 add_inspector_plugin() 注册
    return EditorInspectorPlugin.new()

func create_import_plugin() -> EditorImportPlugin:
    # 导入插件：继承 ResourceImporter，用 add_import_plugin() 注册
    return EditorImportPlugin.new()

func create_export_plugin() -> EditorExportPlugin:
    # 导出插件：继承 RefCounted，用 add_export_plugin() 注册
    return EditorExportPlugin.new()

func create_translation_parser_plugin() -> EditorTranslationParserPlugin:
    # 翻译解析插件：用 add_translation_parser_plugin() 注册
    return EditorTranslationParserPlugin.new()

func create_debugger_plugin() -> EditorDebuggerPlugin:
    # 调试器插件：用 add_debugger_plugin() 注册
    return EditorDebuggerPlugin.new()

func create_node_3d_gizmo_plugin() -> EditorNode3DGizmoPlugin:
    # 3D 操纵器插件：用 add_node_3d_gizmo_plugin() 注册
    return EditorNode3DGizmoPlugin.new()

func create_resource_conversion_plugin() -> EditorResourceConversionPlugin:
    # 资源转换插件：用 add_resource_conversion_plugin() 注册
    return EditorResourceConversionPlugin.new()

# ⚠️ 不存在 EditorSettingsPlugin / EditorFileSystemPlugin / EditorResourcePreviewPlugin
# 设置项用 EditorInterface.get_editor_settings()，资源预览用 EditorResourcePreview 单例：
func write_plugin_setting(key: String, value: Variant) -> void:
    var settings := EditorInterface.get_editor_settings()
    settings.set_setting("plugins/my_plugin/%s" % key, value)

func request_resource_preview(path: String) -> void:
    var previewer := EditorInterface.get_resource_previewer()
    if previewer:
        previewer.queue_resource_preview(path)
```

> **机制说明**：`EditorPlugin.add_inspector_plugin()` / `add_import_plugin()` /
> `add_export_plugin()` 等方法要求传入**已实例化**的插件对象，并在 `_exit_tree()`
> 里用对应的 `remove_*()` 注销——这才是 4.x 的「注册」语义，编辑器里并不存在
> `_get_plugins()` 之类的回调。

### 2.2 插件注册

```gdscript
# 插件注册
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginRegistration

extends EditorPlugin

var _dock: Control

func _enter_tree() -> void:
    # 插件被启用时编辑器会自动调用 _enter_tree()，无需也无法手动注册
    _initialize_plugin()

func _exit_tree() -> void:
    # 插件被禁用或编辑器退出时自动调用，在这里做对称清理
    _cleanup_plugin()

func _initialize_plugin() -> void:
    # 例：注册一个右侧 Dock（这两个方法都属于 EditorPlugin）
    _dock = VBoxContainer.new()
    add_control_to_dock(EditorPlugin.DOCK_SLOT_RIGHT_UL, _dock)

func _cleanup_plugin() -> void:
    if _dock:
        # 先从 Dock 摘掉，再释放；不要用 free() 立即释放仍在场景树中的节点
        remove_control_from_docks(_dock)
        _dock.queue_free()
        _dock = null

func _handles(object: Object) -> bool:
    # 检查是否处理对象
    return true

func _edit(object: Object):
    # 编辑对象
    pass

func _make_visible(visible: bool):
    # 设置可见性
    pass
```

### 2.3 插件配置

```gdscript
# 插件配置
class_name PluginConfiguration

var config: ConfigFile = ConfigFile.new()

func load_config(path: String):
    # 加载配置文件
    var err = config.load(path)
    if err != OK:
        print("Failed to load config: ", err)
        return false
    
    return true

func save_config(path: String):
    # 保存配置文件
    var err = config.save(path)
    if err != OK:
        print("Failed to save config: ", err)
        return false
    
    return true

func get_setting(name: String, default: Variant = null):
    # 获取设置值
    if config.has_section_key("settings", name):
        return config.get_value("settings", name)
    return default

func set_setting(name: String, value: Variant):
    # 设置设置值
    config.set_value("settings", name, value)

func get_section_values(section: String) -> Dictionary:
    # 获取部分值
    var values = {}
    for key in config.get_section_keys(section):
        values[key] = config.get_value(section, key)
    return values

func get_all_sections() -> Array:
    # 获取所有部分
    return config.get_sections()
```

---

## 3. 插件通信

### 3.1 插件间通信

```gdscript
# 插件间通信：官方手段是 Autoload 单例 + EditorSettings.settings_changed
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

# 单例名：其它插件/脚本通过 Engine.get_singleton("PluginHub") 或直接
# 把该脚本设为 Autoload 后按名字访问
const HUB_SCRIPT := preload("res://addons/plugin_hub/plugin_hub.gd")

var _hub: Node

func _enter_tree() -> void:
    # 方式一：add_autoload_singleton() 把脚本注册为 Autoload 单例
    # （等价于在「项目设置 → 自动加载」里添加一行）
    add_autoload_singleton("PluginHub", HUB_SCRIPT)
    _hub = get_node_or_null("/root/PluginHub")

    # 方式二：监听编辑器设置的任意变化信号
    var settings := EditorInterface.get_editor_settings()
    settings.settings_changed.connect(_on_editor_settings_changed)

func _exit_tree() -> void:
    var settings := EditorInterface.get_editor_settings()
    if settings.settings_changed.is_connected(_on_editor_settings_changed):
        settings.settings_changed.disconnect(_on_editor_settings_changed)

    # 移除 Autoload 单例
    remove_autoload_singleton("PluginHub")
    _hub = null

func _on_editor_settings_changed() -> void:
    # 任一编辑器设置变化都会触发（4.3 EditorSettings 只有一个 settings_changed 信号，
    # 没有按前缀区分的信号；需要按组判断时用 get_changed_settings()）
    var changed := EditorInterface.get_editor_settings().get_changed_settings()
    for key in changed:
        if key.begins_with("plugins/my_plugin/"):
            print("本插件的设置变化了：", key)

# 方式三：自定义信号做点对点广播（插件内部自用）
signal plugin_message(message: String, data: Variant)

func send_message(message: String, data: Variant = null) -> void:
    plugin_message.emit(message, data)

func receive_message(message: String, data: Variant) -> void:
    match message:
        "refresh":
            _refresh()
        "update":
            _update(data)

func _refresh() -> void:
    pass

func _update(data: Variant) -> void:
    pass
```

> **机制说明**：编辑器**没有**「按名字查找插件实例」的 API
> （`EditorInterface` 全表里没有 `get_plugins()` / `register_plugin()`）。
> 跨插件协作的正规做法是把一个脚本注册成 **Autoload 单例**
> （`EditorPlugin.add_autoload_singleton()`），双方共同持有同一个节点引用；
> 需要感知「用户改了某个设置」时监听 `EditorSettings.settings_changed`，
> 再用 `get_changed_settings()` 过滤出关心的键。

### 3.2 事件系统

```gdscript
# 事件系统
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginEvents

signal plugin_event(event_type: String, data: Variant)

func emit_event(event_type: String, data: Variant):
    # 发出事件
    plugin_event.emit(event_type, data)

func listen_for_event(event_type: String, callback: Callable):
    # 监听事件：4.x 的 Object.connect() 第二个参数是 Callable
    connect("plugin_event", callback)

func remove_event_listener(callback: Callable):
    # 移除事件监听器
    if is_connected("plugin_event", callback):
        disconnect("plugin_event", callback)

# 事件处理器
@tool
class_name PluginEventProcessor

func process_event(event_type: String, data: Variant):
    # 处理事件
    if event_type == "plugin_action":
        _handle_plugin_action(data)
    elif event_type == "resource_changed":
        _handle_resource_change(data)
    elif event_type == "settings_changed":
        _handle_settings_change(data)

func _handle_plugin_action(data: Variant):
    # 处理插件动作
    pass

func _handle_resource_change(data: Variant):
    # 处理资源变化
    pass

func _handle_settings_change(data: Variant):
    # 处理设置变化
    pass
```

### 3.3 信号系统

```gdscript
# 信号系统
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginSignals

signal button_pressed
signal menu_item_selected
signal property_changed

func connect_button_pressed(callback: Callable):
    # 4.x 推荐用 Signal.connect()（button_pressed.connect(callback)），
    # Object.connect(signal_name, callable) 依然可用
    connect("button_pressed", callback)

func connect_menu_item_selected(callback: Callable):
    connect("menu_item_selected", callback)

func connect_property_changed(callback: Callable):
    connect("property_changed", callback)

func emit_button_pressed():
    button_pressed.emit()

func emit_menu_item_selected(item: String):
    menu_item_selected.emit(item)

func emit_property_changed(property: String, value: Variant):
    property_changed.emit(property, value)

# 信号处理器
@tool
class_name PluginSignalProcessor

func handle_button_press():
    # 处理按钮按下
    emit_button_pressed()

func handle_menu_selection(item: String):
    # 处理菜单选择
    emit_menu_item_selected(item)

func handle_property_change(property: String, value: Variant):
    # 处理属性变化
    emit_property_changed(property, value)
```

---

## 4. 插件分发

### 4.1 插件打包（读取 plugin.cfg 元数据）

```gdscript
# 插件打包：元数据一律从 plugin.cfg 的 [plugin] 段读取
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends RefCounted

const PLUGIN_CFG := "res://addons/my_plugin/plugin.cfg"

func package_plugin() -> Dictionary:
    # 打包插件
    var package := {
        "name": "",
        "version": "",
        "description": "",
        "author": "",
        "files": _get_files("res://addons/my_plugin"),
    }
    package.merge(read_plugin_metadata(PLUGIN_CFG))
    return package

func read_plugin_metadata(plugin_cfg_path: String) -> Dictionary:
    # ⚠️ EditorPlugin 上没有 get_version()/get_dependencies()/get_files()/
    #    get_description()/get_author()/get_license()/get_homepage() 这些 getter。
    #    插件的权威元数据在 plugin.cfg 里，用 ConfigFile 读。
    var cfg := ConfigFile.new()
    var err := cfg.load(plugin_cfg_path)
    if err != OK:
        push_error("无法读取插件配置：%s（错误码 %d）" % [plugin_cfg_path, err])
        return {}
    return {
        "name": cfg.get_value("plugin", "name", ""),
        "version": cfg.get_value("plugin", "version", ""),
        "description": cfg.get_value("plugin", "description", ""),
        "author": cfg.get_value("plugin", "author", ""),
    }

func _get_files(root: String) -> Array:
    var files: Array = []
    var dir := DirAccess.open(root)
    if dir == null:
        return files
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir():
            files.append(root + "/" + file_name)
        file_name = dir.get_next()
    dir.list_dir_end()
    return files

func create_package(output_path: String) -> bool:
    # 创建包
    var package_data := package_plugin()
    var file := FileAccess.open(output_path, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(package_data, "  "))
        file.close()
        return true
    return false
```

> **机制说明**：`EditorPlugin` 的元数据只有 `get_plugin_version()`（读 `plugin.cfg`
> 的 `version` 字段）和 `get_plugin_name()`（读 `plugin.cfg` 的 `name` 字段）；
> 描述、作者等字段**只存在于 `plugin.cfg` 文件里**，必须用 `ConfigFile` 读。
> `plugin.cfg` 是 INI 格式，用 `JSON.parse()` 读它一定失败。

### 4.2 插件安装

```gdscript
# 插件安装
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends RefCounted

func install_plugin(plugin_data: Dictionary, plugin_path: String) -> bool:
    # 安装插件
    # 插件的启用状态记录在项目设置中，编辑器扫描 addons/ 后自行实例化 EditorPlugin，
    # 不存在"new 一个 EditorPlugin 再注册"的流程
    var success := _install_files(plugin_data["files"], plugin_path)
    if success:
        # 编辑器没有 register_plugin()；把插件加入启用列表
        _enable_plugin(plugin_path)
        return true
    return false

func _install_files(files: Array, plugin_path: String) -> bool:
    # 安装文件
    # ⚠️ 原来的写法把 return 写在 for 循环体内，无论 files 有几个都只会安装第 0 个。
    # 正确做法：用标志位累加，循环结束后再 return。
    var all_ok := true
    for file in files:
        var file_path := plugin_path + "/" + file["path"]
        var file_content: String = file["content"]

        # 目标目录可能还不存在
        var dir_path := file_path.get_base_dir()
        if not DirAccess.dir_exists_absolute(dir_path):
            DirAccess.make_dir_recursive_absolute(dir_path)

        var f := FileAccess.open(file_path, FileAccess.WRITE)
        if f == null:
            push_error("无法写入文件：%s" % file_path)
            all_ok = false
            continue
        f.store_string(file_content)
        f.close()
    return all_ok

func _enable_plugin(plugin_path: String) -> void:
    # 启用插件：4.2+ 官方推荐 EditorInterface.set_plugin_enabled()
    # 参数是插件的「目录名」（addons/ 下的那一层），不是 plugin.cfg 的完整路径
    var dir_name := plugin_path.get_file()
    EditorInterface.set_plugin_enabled(dir_name, true)
```

> **机制说明**：`EditorInterface.set_plugin_enabled(plugin, enabled)` 的 `plugin`
> 参数文档写得很明确：「The plugin name is the same as its directory name.」
> 传 `res://addons/my_plugin/plugin.cfg` 这样的路径是无效的。

### 4.3 插件在线检查更新（正确的 HTTP 写法）

```gdscript
# 插件在线检查更新
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
extends EditorPlugin

# HTTPRequest 必须挂在场景树上才能发起请求
var _http: HTTPRequest
# 下载目标路径存为成员变量：回调里拿不到形参
var _save_path: String = ""

func _enter_tree() -> void:
    _http = HTTPRequest.new()
    add_child(_http)
    _http.request_completed.connect(_on_request_completed)

func _exit_tree() -> void:
    if _http:
        _http.request_completed.disconnect(_on_request_completed)
        _http.queue_free()
        _http = null

func check_for_updates(plugin_name: String, version: String) -> void:
    # 检查更新
    _save_path = "user://plugins/%s.zip" % plugin_name
    var headers := PackedStringArray(["Content-Type: application/json"])
    var body := JSON.stringify({
        "plugin": plugin_name,
        "version": version,
    })
    var err := _http.request("https://api.example.org/plugins/" + plugin_name, headers, HTTPClient.METHOD_POST, body)
    if err != OK:
        push_error("发起更新检查失败，错误码 %d" % err)

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    if result != HTTPRequest.RESULT_SUCCESS:
        push_error("更新检查失败，传输结果 %d" % result)
        return
    if response_code != 200:
        push_error("更新检查失败，HTTP 状态码 %d" % response_code)
        return
    var parsed = JSON.parse_string(body.get_string_from_utf8())
    if typeof(parsed) != TYPE_DICTIONARY:
        return
    if parsed.get("available", false):
        download_update(parsed.get("url", ""))

func download_update(url: String) -> void:
    # 下载更新包：save_path 是成员变量，回调里直接用
    _save_path = "user://plugins/update.zip"
    var err := _http.request(url)
    if err != OK:
        push_error("下载失败，错误码 %d" % err)

func _on_download_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
        push_error("下载失败")
        return
    var file := FileAccess.open(_save_path, FileAccess.WRITE)
    if file == null:
        push_error("无法写入：%s" % _save_path)
        return
    file.store_buffer(body)
    file.close()
```

> **机制说明**：`HTTPClient.request()` 的签名是
> `request(method: int enum HTTPClient.Method, url: String, headers: PackedStringArray, body: String = "")`
> ——**第 1 个参数是枚举而不是字符串**（要写 `HTTPClient.METHOD_POST`），
> **第 4 个参数是请求体字符串而不是 bool**。
> 4.3 版还没有 `client_cert` / `client_key` 这两个参数（4.4+ 才加入），
> 但无论如何，低层 `HTTPClient` **必须先 `connect_to_host(host, port)`**，
> 否则请求根本发不出去；`url` 只写主机之后的部分。
> 更省事、也更不容易写错的做法是直接用 `HTTPRequest` 节点（本文示例即如此）：
> 它自己处理连接、TLS、线程与下载落盘，并给出 `request_completed` 信号。
> 另有两点要注意：
> - `HTTPRequest` **必须已经加进场景树**（`add_child()`）才会发请求，
>   否则 `request()` 直接返回 `ERR_UNCONFIGURED`；
> - 如果只是下载文件到磁盘，用它的 `download_file` 属性指定落盘路径即可，
>   连 `request_completed` 都不用接，收到数据会自动写进那个文件。

### 4.4 发布到 AssetLib（可操作细节）

```
AssetLib 提交流程:
┌─────────────────────────────────────────────────────────────┐
│ 1. 准备插件目录                                            │
│    res://addons/<插件名>/plugin.cfg   ← 必须在这一层         │
│    res://addons/<插件名>/*.gd                                    │
│    res://addons/<插件名>/icon.svg （或 icon.png）              │
│    res://addons/<插件名>/screenshot.png                         │
│                                                             │
│ 2. 打包成 zip                                                │
│    ⚠️ 硬性规则：zip 的根目录必须直接包含 addons/<插件名>/      │
│       plugin.cfg 这一层目录，不能多套一层文件夹，              │
│       也不能把 plugin.cfg 放在 zip 根目录                     │
│                                                             │
│ 3. 创建 GitHub 仓库（公开）                                  │
│    - README.md（必填）                                       │
│    - LICENSE（必填，AssetLib 会展示许可证）                  │
│    - CHANGELOG.md（强烈建议）                                │
│                                                             │
│ 4. 提交到 AssetLib                                          │
│    - 访问 https://godotengine.org/asset-library/asset        │
│    - 上传 zip，填写名称/描述/版本号/截图/图标                 │
│    - 提交审核（通常几个工作日内）                             │
│                                                             │
│ 5. 维护和更新                                               │
│    - 版本号必须与 plugin.cfg 的 version 字段完全一致          │
│    - 每次发新版重新上传新 zip，并递增版本号                   │
└─────────────────────────────────────────────────────────────┘
```

**发布时的硬性规则与审核要点**

| 项目 | 规则 |
|------|------|
| zip 目录结构 | 根目录下必须有 `addons/<插件名>/plugin.cfg` |
| 插件名 | 必须与 `plugin.cfg` 里 `name` 字段一致 |
| 版本号 | AssetLib 上填的版本号必须与 `plugin.cfg` 的 `version` 一致 |
| 标识符 | `plugin.cfg` 的 `name` 应以英文单词开头，描述清晰 |
| 图标 | 建议 128×128 PNG 或 SVG；主屏幕插件的图标建议 16×16 白色透明底 |
| 截图 | 至少一张能体现插件实际用途的截图 |
| 许可证 | 必须附带开源许可证（MIT / Apache-2.0 / GPL 等） |
| 依赖 | AssetLib **不支持**在 `plugin.cfg` 里声明依赖（见下方说明） |

> **机制说明**：Godot 的插件系统**没有内建的依赖声明机制**。
> 4.3 的 `editor/editor_node.cpp` 解析 `plugin.cfg` 时只取 `[plugin]` 段的
> `script` / `version` / `name` / `description` / `author` 五个键，
> **写 `[dependencies]` 段不会有任何效果**（也不会报错）。需要依赖时，
> 请在自己的插件 `_enter_tree()` 里用
> `EditorInterface.is_plugin_enabled("<依赖插件目录名>")` 自行检测，
> 未启用就提示用户。

```gdscript
# 在自己的插件里检测依赖（4.3 没有 [dependencies] 段的替代品）
@tool
extends EditorPlugin

const REQUIRED_PLUGINS := ["my_dependency"]

func _enter_tree() -> void:
    for dep in REQUIRED_PLUGINS:
        if not EditorInterface.is_plugin_enabled(dep):
            push_warning("插件 %s 需要先启用依赖插件：%s" % [get_plugin_name(), dep])
```

---

## 5. 插件最佳实践

> 本节原来的「代码规范 / 性能优化 / 安全最佳实践」三小节只有空函数体，
> 与第 67 篇（编辑器扩展最佳实践）完全重复。**规范类内容统一以第 67 篇为准**：
> 代码组织与命名见 67 §1，编辑器内性能见 67 §2，交互与快捷键见 67 §3，
> 错误处理见 67 §4，安全与设置存储见 67 §5。
>
> 这里只保留三条与「插件发布」直接相关的硬规则：

1. **启用/禁用必须对称**：`_enter_tree()` 里加了什么，`_exit_tree()` 里就要
   移除什么（`remove_control_from_docks()` / `remove_inspector_plugin()` /
   `remove_tool_menu_item()` / `remove_autoload_singleton()` …），
   并对节点用 `queue_free()` 而不是 `free()`。
2. **元数据只在 `plugin.cfg` 里**：不要把描述、作者、版本号散落在别处，
   也不要指望 `EditorPlugin` 上有 `get_version()` 之类的 getter。
3. **面向编辑器的脚本必须加 `@tool`**：否则它在编辑器进程里根本不会被实例化，
   插件会表现为「启用了但什么也没发生」。

---

## 6. 实践：完整插件系统

### 6.1 插件管理器

```gdscript
# 插件管理器
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginManager

extends EditorPlugin

# 目录名 -> plugin.cfg 的元数据字典
var installed_plugins: Dictionary = {}
var plugin_dependencies: Dictionary = {}

func _enter_tree():
    # 初始化插件管理器
    _load_installed_plugins()
    _check_dependencies()

func _exit_tree():
    # 清理插件管理器
    _cleanup()

func _load_installed_plugins():
    # 加载已安装插件
    for dir_name in _get_plugin_directories():
        var meta := _read_plugin_cfg(dir_name)
        if not meta.is_empty():
            installed_plugins[dir_name] = meta

func _get_plugin_directories() -> PackedStringArray:
    # 获取插件目录：res://addons/ 下的一级子目录
    var dirs := PackedStringArray()
    var base := DirAccess.open("res://addons")
    if base == null:
        return dirs
    base.list_dir_begin()
    var name := base.get_next()
    while name != "":
        if base.current_is_dir() and not name.begins_with("."):
            dirs.append(name)
        name = base.get_next()
    base.list_dir_end()
    return dirs

func _read_plugin_cfg(dir_name: String) -> Dictionary:
    # 用 ConfigFile 读 plugin.cfg 的 [plugin] 段
    var cfg := ConfigFile.new()
    var path := "res://addons/%s/plugin.cfg" % dir_name
    if cfg.load(path) != OK:
        return {}
    return {
        "name": cfg.get_value("plugin", "name", dir_name),
        "version": cfg.get_value("plugin", "version", "0.0.0"),
        "description": cfg.get_value("plugin", "description", ""),
        "author": cfg.get_value("plugin", "author", ""),
        "dir": dir_name,
    }

func _check_dependencies():
    # 检查依赖：4.3 的 plugin.cfg 没有 [dependencies] 段，
    # 依赖关系由插件自己在 _enter_tree() 里用 is_plugin_enabled() 检测
    for dir_name in installed_plugins:
        if not _is_plugin_enabled(dir_name):
            print("插件未启用：", dir_name)

func _is_plugin_enabled(dir_name: String) -> bool:
    return EditorInterface.is_plugin_enabled(dir_name)

func _cleanup():
    # 清理插件管理器
    installed_plugins.clear()
    plugin_dependencies.clear()

func get_plugin(dir_name: String) -> Dictionary:
    # 获取插件信息
    return installed_plugins.get(dir_name, {})

func get_all_plugins() -> Dictionary:
    # 获取所有插件信息
    return installed_plugins
```

### 6.2 插件版本管理

```gdscript
# 插件版本管理
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginUpdater

extends EditorPlugin

# 每天检查一次更新
var update_check_timer: Timer

func _ready():
    # 插件脚本继承 Node，_ready() 在进入场景树时触发
    update_check_timer = Timer.new()
    add_child(update_check_timer)
    update_check_timer.wait_time = 86400
    update_check_timer.one_shot = true
    update_check_timer.timeout.connect(_check_for_updates)

func _check_for_updates():
    # 检查更新：本地版本从 plugin.cfg 读，线上版本用 HTTPRequest 查
    var local_version := _get_installed_version(get_plugin_name())
    var remote_version := _get_remote_version(get_plugin_name())
    if remote_version.is_empty() or remote_version == local_version:
        return
    print("插件 %s 有新版本：%s → %s" % [get_plugin_name(), local_version, remote_version])

func _get_installed_version(dir_name: String) -> String:
    # ⚠️ plugin.cfg 是 INI 格式，用 JSON.parse() 读一定失败，必须用 ConfigFile
    var cfg := ConfigFile.new()
    if cfg.load("res://addons/%s/plugin.cfg" % dir_name) != OK:
        return "0.0.0"
    return cfg.get_value("plugin", "version", "0.0.0")

func _get_remote_version(dir_name: String) -> String:
    # 线上版本：HTTPRequest 节点自己处理连接与线程
    var http := HTTPRequest.new()
    add_child(http)
    var err := http.request("https://api.example.org/plugins/%s/latest" % dir_name)
    if err != OK:
        http.queue_free()
        return ""
    # 同步读取不可靠：真实实现应改用 request_completed 信号回调，
    # 这里为保持示例简洁直接返回空串，提示「尚未实现」
    http.queue_free()
    return ""

func _compare_versions(a: String, b: String) -> int:
    # 比较版本号：a > b 返回 1
    var pa := a.split(".")
    var pb := b.split(".")
    for i in range(min(pa.size(), pb.size())):
        var na := int(pa[i])
        var nb := int(pb[i])
        if na > nb:
            return 1
        elif na < nb:
            return -1
    return 0
```

> **机制说明**：`Engine.get_version_info()` 返回的是**字典**（含 `major` / `minor` /
> `patch` / `status` / `hash` 五个键），不是版本号字符串。
> 要拼版本号请写：
> `var v := Engine.get_version_info(); var ver := "%d.%d.%d" % [v.major, v.minor, v.patch]`。

### 6.3 插件间通信与分发

```gdscript
# 插件间通信与分发
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginDistribution

extends EditorPlugin

const ASSET_LIB_URL := "https://godotengine.org/asset-library/asset"

func _enter_tree():
    # 初始化插件分发系统
    _setup_repository()

func _exit_tree():
    # 清理插件分发系统
    _cleanup_repository()

func _setup_repository():
    # 设置仓库：AssetLib 的检索与下载由编辑器内建的 AssetLib 标签页负责，
    # 插件不需要自己实现一套 HTTP 检索（见 4.3 节的正确 HTTP 写法）
    print("AssetLib 入口：", ASSET_LIB_URL)

func _cleanup_repository():
    # 清理仓库
    pass

func open_asset_lib() -> void:
    # 打开 AssetLib 主屏幕
    EditorInterface.set_main_screen_editor("AssetLib")

func _add_repository_to_manager(repo: Dictionary):
    # 跨插件协作：把管理插件注册成 autoload 单例，双方共同持有同一节点引用，
    # 而不是靠名字查找（编辑器没有「按名字获取插件实例」的 API）
    var manager: Node = get_node_or_null("/root/PluginManagerBridge")
    if manager and manager.has_method("add_repository"):
        manager.add_repository(repo)
```

> **机制说明**：AssetLib 的搜索/下载是**编辑器内建功能**
> （工作区顶部的 AssetLib 标签页），插件既不需要、也无法替换它。
> 插件要做的是把自己打包成符合 §4.4 规则的 zip，然后由用户提交到 AssetLib。

---

## 📝 本章总结

### 核心要点

1. **插件架构提供扩展能力**，4.x 的插件基类只有 EditorPlugin / EditorInspectorPlugin /
   EditorImportPlugin / EditorExportPlugin 等十种，**没有** `EditorSettingsPlugin` /
   `EditorFileSystemPlugin` / `EditorResourcePreviewPlugin`
2. **插件开发遵循生命周期**，`_enter_tree()` / `_exit_tree()` 由引擎自动触发，
   启用与清理必须对称
3. **插件通信用官方手段**：Autoload 单例 + `EditorSettings.settings_changed`，
   编辑器没有「按名字查插件实例」的 API
4. **插件元数据只在 `plugin.cfg` 里**，用 `ConfigFile` 读；`plugin.cfg` 不支持
   `[dependencies]` 段
5. **发布到 AssetLib**：zip 根目录必须直接含 `addons/<插件名>/plugin.cfg`，
   版本号必须与 `plugin.cfg` 一致

### 关键术语

| 术语 | 解释 |
|------|------|
| EditorPlugin | 编辑器插件，扩展编辑器功能（继承 Node） |
| EditorInspectorPlugin | 检查器插件，自定义属性显示（继承 RefCounted） |
| EditorImportPlugin | 导入插件，支持自定义文件格式（继承 ResourceImporter） |
| EditorExportPlugin | 导出插件，介入导出流程 |
| plugin.cfg | 插件的 INI 配置文件，`[plugin]` 段放元数据 |
| Autoload 单例 | 插件间通信的官方手段（`add_autoload_singleton()`） |
| PluginManager | 插件管理器，扫描 `addons/` 读取插件元数据 |
| PluginUpdater | 插件版本管理器，比对本地与线上版本号 |
| PluginDistribution | 插件分发器，对接 AssetLib 发布流程 |

---

## 🔗 延伸阅读

- **官方文档 · 创建与使用插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/index.html>
- **官方文档 · 检查器插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/inspector_plugins.html>
- **官方文档 · 导入插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/import_plugins.html>
- **官方文档 · 插件命令行**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/command_line_editor.html>
- **AssetLib**: <https://godotengine.org/asset-library>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorplugin.html>
- **源码位置**: `editor/plugins/editor_plugin.cpp`, `editor/editor_node.cpp`（解析 `plugin.cfg`）

---

## 📋 下一章预告

**第 61 篇：高级编辑器扩展**

- 四类扩展点：Inspector / Dock / 导入器 / 导出器
- `EditorPlugin` 其余官方扩展点（主屏幕、3D 控件、画布输入转发）
- 资源导入的完整闭环与 `EditorExportPlugin` 钩子

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 60 篇：C# 集成和脚本性能优化](/articles/60-csharp-and-script-optimization.md)
**下一篇**: [第 61 篇：高级编辑器扩展](/articles/61-advanced-editor-extensions.md)

---

*写作时间：2026-03-20*  
*字数：约 1,800 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
