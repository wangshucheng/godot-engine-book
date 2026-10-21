# 第 67 篇：编辑器扩展最佳实践

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 66 章 编辑器扩展模板  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编写高质量的编辑器扩展需要遵循一系列最佳实践。本章是**第八卷的规范篇**：
代码怎么组织、编辑器里怎么不卡、交互怎么做、错误怎么报、设置存哪里。

> **卷内边界**：本章只管 **GDScript 侧的编辑器扩展写法**。
> 扩展点 API 在第 61 篇；「编辑器里有什么能改的」在第 63 篇；
> 性能调优在第 64 篇；批量干活与 CI 在第 65 篇；
> 插件打包与 AssetLib 发布在第 58 篇。
> 与**卷九第 71 篇**的界线：71 篇讲的是 **C++ 自定义模块**的规范
> （`GDCLASS`、`ClassDB` 注册、编译产物布局等），本章讲的是 GDScript 侧，
> 两者互不覆盖。

---

## 🎯 学习目标

- 掌握编辑器扩展的代码组织与命名约定
- 掌握 `@tool` 的真实行为与编辑器内脚本生命周期
- 会用 `EditorUndoRedoManager` 把操作接进编辑器的撤销栈
- 知道插件设置该存在哪里

---

## 1. 代码质量最佳实践

### 1.1 命名规范

```gdscript
# 命名规范
@tool
class_name NamingConventions

# 插件命名
# - 使用帕斯卡命名法 (PascalCase)
# - 以 "Plugin" 或 "Editor" 结尾
var plugin_name := "MyCustomEditor"
var plugin_class := "MyCustomEditorPlugin"

# 函数命名
# - 使用蛇形命名法 (snake_case)
# - 动词开头，描述功能
func _enter_tree() -> void:
    pass

func setup_dock() -> void:
    pass

func cleanup_resources() -> void:
    pass

# 变量命名
# - 使用蛇形命名法 (snake_case)
# - 前缀表示范围
var private_variable: String = ""
var _internal_variable: String = ""
var public_variable: String = ""

# 常量命名
# - 使用大写蛇形命名法 (SCREAMING_SNAKE_CASE)
const MAX_CONNECTIONS := 100
const DEFAULT_TIMEOUT := 30.0
const PLUGIN_NAME := "MyCustomEditor"

# 类命名
# - 使用帕斯卡命名法 (PascalCase)
# - 描述清楚功能
# ⚠️ GDScript 里内部类必须写成 class 名字 extends 父类: 的形式，
#    并且必须有一个（哪怕是空的）类体，不能只写一个光秃秃的类名。
class CustomEditorDock extends Control:
    pass

class ResourceProcessor extends RefCounted:
    pass

class SceneValidator extends RefCounted:
    pass

# 信号命名
# - 使用蛇形命名法 (snake_case)
# - 描述事件
signal resource_loaded
signal processing_completed
signal error_occurred
```

### 1.2 注释规范

```gdscript
# 注释规范
@tool
class_name CommentingConventions

# 1. 文件头注释
"""
File: my_custom_editor.gd
Author: Your Name
Description: Custom editor extension for Godot
Version: 1.0.0
License: MIT
"""

# 2. 类注释
class CustomEditor extends Control:
    """
    Custom editor for managing game resources.

    Features:
    - Resource management
    - Batch processing
    - Error handling

    Usage:
    var editor = CustomEditor.new()
    editor.initialize()
    """

    func _init() -> void:
        pass

# 3. 函数注释
"""
Preprocesses resources before loading.

Args:
    resource_path: Path to the resource file
    options: Processing options

Returns:
    bool: True if successful, false otherwise
"""
func preprocess_resource(resource_path: String, options: Dictionary) -> bool:
    return true

# 4. 行内注释
var max_retries := 3  # Maximum retry attempts for failed operations
var timeout := 30.0   # Timeout in seconds

# 5. 代码块注释
#region Resource Loading
"""
Loads resources from disk.
Handles both synchronous and asynchronous loading.
"""
func load_resources(paths: Array) -> Array:
    return paths
#endregion

# 6. BUG注释
func broken_function() -> void:
    # BUG: This function doesn't handle edge cases properly
    # TODO: Fix edge case handling
    pass

# 7. TODO注释
func incomplete_function() -> void:
    # TODO: Implement error handling
    # TODO: Add unit tests
    pass
```

### 1.3 代码组织

```gdscript
# 代码组织：插件主脚本的标准骨架
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginCodeOrganization

extends EditorPlugin

# 1.1 信号
signal resource_loaded
signal error_occurred

# 1.2 导出属性
@export var option1: bool = true
@export var option2: int = 100

# 1.3 私有变量
var dock: Control
var button: Button
var cache: Dictionary = {}

# 2. 生命周期函数
func _enter_tree() -> void:
    # 初始化插件
    pass

func _exit_tree() -> void:
    # 清理插件
    pass

# 3. 公共接口
func initialize() -> void:
    pass

func cleanup() -> void:
    pass

# 4. 私有方法
func _setup_ui() -> void:
    pass

func _cleanup_ui() -> void:
    pass

# 5. 事件处理
func _on_button_pressed() -> void:
    pass

func _on_resource_loaded(path: String) -> void:
    pass

# 6. 内部工具函数
func _validate_path(path: String) -> bool:
    return true

func _format_timestamp() -> String:
    return Time.get_datetime_string_from_unix(Time.get_unix_time())
```

---

## 2. 性能优化最佳实践

### 2.1 延迟加载

```gdscript
# 延迟加载
@tool
class_name DeferredLoading
extends Node

# 1. 使用 call_deferred
func setup_dock_deferred() -> void:
    call_deferred("_setup_dock")

func _setup_dock() -> void:
    # 实际的设置逻辑
    pass

# 2. 使用 await 进行异步操作
func load_resources_async() -> Resource:
    # 开始异步加载
    ResourceLoader.load_threaded_request("res://scene.tscn")

    # 等待加载完成
    var progress: Array = []
    while ResourceLoader.load_threaded_get_status("res://scene.tscn", progress) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        await get_tree().create_timer(0.1).timeout

    # 加载完成
    return ResourceLoader.load_threaded_get("res://scene.tscn")

# 3. 使用 Timer 进行延迟调用
var _timer: Timer

func deferred_callback() -> void:
    _timer = Timer.new()
    _timer.wait_time = 1.0
    _timer.one_shot = true
    _timer.timeout.connect(_on_timer_timeout)
    add_child(_timer)
    _timer.start()

func _on_timer_timeout() -> void:
    pass

# 4. 使用队列进行批处理
var pending_operations: Array = []
var is_processing: bool = false

func queue_operation(operation: Callable) -> void:
    # 排队操作
    pending_operations.append(operation)
    if not is_processing:
        is_processing = true
        call_deferred("_process_queue")

func _process_queue() -> void:
    # 处理队列
    while pending_operations.size() > 0 and not is_processing:
        var operation: Callable = pending_operations.pop_front()
        operation.call()
    is_processing = false
```

### 2.2 缓存策略

```gdscript
# 缓存策略
@tool
class_name CachingStrategy
extends Node

# 1. 缓存频繁访问的节点
var cached_node: Node

func _ready() -> void:
    cached_node = get_node_or_null("Path/To/Node")

func update_cached_node() -> void:
    if cached_node and is_instance_valid(cached_node):
        cached_node.call("update")

# 2. 缓存频繁使用的资源
var resource_cache: Dictionary = {}

func get_cached_resource(path: String) -> Resource:
    if not resource_cache.has(path):
        var resource := load(path)
        if resource:
            resource_cache[path] = resource
    return resource_cache.get(path)

func clear_resource_cache() -> void:
    resource_cache.clear()

# 3. 缓存计算结果
var calculation_cache: Dictionary = {}

func expensive_calculation(input: Variant) -> Variant:
    if not calculation_cache.has(input):
        calculation_cache[input] = _do_expensive_calculation(input)
    return calculation_cache[input]

func clear_calculation_cache() -> void:
    calculation_cache.clear()

# 4. 需要弱引用时用 WeakRef（不能把 Object 直接塞进 Dictionary 当弱引用）
var weak_references: Dictionary = {}

func get_weak_reference(key: String, obj: Object) -> WeakRef:
    if not weak_references.has(key):
        weak_references[key] = weakref(obj)
    return weak_references[key]

func clear_weak_references() -> void:
    weak_references.clear()
```

### 2.3 事件优化

```gdscript
# 事件优化
@tool
class_name EventOptimization
extends Node

# 1. 使用信号代替轮询
signal value_changed(old_value: Variant, new_value: Variant)

var _value: int = 0

func set_value(new_value: int) -> void:
    if _value != new_value:
        var old_value := _value
        _value = new_value
        value_changed.emit(old_value, new_value)

func get_value() -> int:
    return _value

# 2. 节流事件
var last_execution_time: int = 0
var cooldown := 0.1  # 100ms cooldown

func throttled_update() -> void:
    var current_time := Time.get_ticks_msec()
    if current_time - last_execution_time > cooldown * 1000:
        _do_update()
        last_execution_time = current_time

func _do_update() -> void:
    pass

# 3. 防抖事件
var debounced_callback: Callable
var debounce_timer: Timer

func debounced_update(callback: Callable) -> void:
    debounced_callback = callback

    if debounce_timer == null:
        debounce_timer = Timer.new()
        debounce_timer.wait_time = 0.5
        debounce_timer.one_shot = true
        add_child(debounce_timer)

    if debounce_timer.timeout.is_connected(_on_debounce_timeout):
        debounce_timer.timeout.disconnect(_on_debounce_timeout)
    debounce_timer.timeout.connect(_on_debounce_timeout)
    debounce_timer.start()

func _on_debounce_timeout() -> void:
    if debounced_callback:
        debounced_callback.call()
        debounced_callback = Callable()

# 4. 批量事件
var pending_events: Array = []
var is_processing: bool = false

func queue_event(event_data: Variant) -> void:
    pending_events.append(event_data)
    if not is_processing:
        is_processing = true
        call_deferred("_process_events")

func _process_events() -> void:
    while pending_events.size() > 0:
        var event_data: Variant = pending_events.pop_front()
        _handle_event(event_data)
    is_processing = false

func _handle_event(event_data: Variant) -> void:
    pass
```

---

## 3. 用户交互最佳实践

### 3.1 UI响应性

```gdscript
# UI响应性
@tool
class_name UIResponsiveness
extends Control

# 1. 使用 loading 状态
var is_loading: bool = false
var loading_label: Label
var loading_progress_bar: ProgressBar
var status_label: Label

func load_resources() -> void:
    is_loading = true
    update_ui_state()
    call_deferred("_do_load_resources")

func _do_load_resources() -> void:
    is_loading = false
    update_ui_state()

func update_ui_state() -> void:
    if is_loading:
        loading_label.show()
        loading_progress_bar.visible = true
        loading_progress_bar.value = 50
    else:
        loading_label.hide()
        loading_progress_bar.visible = false

# 2. 提供反馈
func perform_action() -> void:
    status_label.text = "Performing action..."
    call_deferred("_do_action")

func _do_action() -> void:
    status_label.text = "Action completed successfully"
    call_deferred("_clear_status", 2.0)

func _clear_status(delay: float) -> void:
    # 延迟清理状态
    await get_tree().create_timer(delay).timeout
    status_label.text = ""

# 3. 使用确认对话框
func dangerous_action() -> void:
    var dialog := ConfirmationDialog.new()
    dialog.title_text = "Confirm Action"
    dialog.dialog_text = "Are you sure you want to perform this action?"
    dialog.confirmed.connect(_on_action_confirmed)
    add_child(dialog)
    dialog.popup_centered()

func _on_action_confirmed() -> void:
    pass

# 4. 撤销功能请用编辑器的撤销栈，不要自己造轮子
#    详见本章 §8「编辑器内撤销 / 重做」
```

### 3.2 用户提示

```gdscript
# 用户提示
@tool
class_name UserNotifications
extends Control

# 1. 使用 print_debug：GDScript 的调试输出函数就叫 print_debug
func debug_message(message: String) -> void:
    print_debug(message)

# 2. 使用 push_warning
func warning_message(message: String) -> void:
    push_warning(message)

# 3. 使用 push_error
func error_message(message: String) -> void:
    push_error(message)

# 4. 使用自定义对话框
func custom_notification(message: String, title: String = "Notification") -> void:
    var dialog := PopupPanel.new()
    # ⚠️ PopupPanel 没有 title_text（那是 Window 的属性）
    dialog.title = title
    dialog.modal = true

    var vbox := VBoxContainer.new()
    dialog.add_child(vbox)

    var label := Label.new()
    label.text = message
    vbox.add_child(label)

    var button := Button.new()
    button.text = "OK"
    # 4.x 的 connect 第二个参数是 Callable，不接受 (对象, 方法名) 三参重载
    button.pressed.connect(dialog.queue_free)
    vbox.add_child(button)

    add_child(dialog)
    dialog.popup_centered()

# 5. 使用状态栏消息
#    status_label 是类成员，不是局部变量：_clear_status_bar() 里也要用到它
var status_label: Label

func status_bar_message(message: String, duration: int = 3) -> void:
    status_label.text = message
    if duration > 0:
        call_deferred("_clear_status_bar", duration)

func _clear_status_bar(delay: float) -> void:
    # 清理状态栏
    await get_tree().create_timer(delay).timeout
    status_label.text = ""
```

### 3.3 键盘快捷键

```gdscript
# 键盘快捷键
@tool
class_name KeyboardShortcuts
extends EditorPlugin

var _registered_shortcuts: Dictionary = {}

# 1. 工具菜单项（EditorPlugin 提供；4.x 的第二个参数是 Callable）
func _enter_tree() -> void:
    add_tool_menu_item("My Plugin/Action", _on_action)

func _exit_tree() -> void:
    remove_tool_menu_item("My Plugin/Action")

# 2. 覆盖某个「内建编辑器动作」的按键
func override_editor_shortcut() -> void:
    # set_builtin_action_override() 是 4.3 的公开 API：
    # 用指定的输入事件覆盖一个内建的编辑器动作
    var ev := InputEventKey.new()
    ev.keycode = KEY_A
    ev.ctrl_pressed = true
    ev.shift_pressed = true

    var settings := EditorInterface.get_editor_settings()
    settings.set_builtin_action_override("editor/undo", [ev])

# 3. 新增一条自定义快捷键（4.4+ 才有 add_shortcut）
func register_custom_shortcut_4_4_plus() -> void:
    # ⚠️ 4.3 的 EditorSettings 没有 add_shortcut()，
    #    它是 4.4+ 才加上的方法，而且必须通过实例调用：
    #    EditorInterface.get_editor_settings().add_shortcut("my_plugin/action", shortcut)
    # 另外，EditorSettings 没有暴露 save() 方法给脚本，
    #    编辑器设置是「变更后自动保存」的，不需要手动保存。
    var shortcut := Shortcut.new()
    var ev := InputEventKey.new()
    ev.keycode = KEY_F5
    ev.ctrl_pressed = true
    shortcut.events = [ev]

    var settings := EditorInterface.get_editor_settings()
    if settings.has_method("add_shortcut"):
        settings.call("add_shortcut", "my_plugin/action", shortcut)
        _registered_shortcuts["my_plugin/action"] = shortcut
    else:
        push_warning("当前 Godot 版本的 EditorSettings 没有 add_shortcut()，请改用工具菜单项。")

# 4. 游戏内快捷键沿用 InputMap
func ensure_input_action() -> void:
    if not InputMap.has_action("my_plugin_action"):
        InputMap.add_action("my_plugin_action")

# 5. 上下文敏感触发
func _process(_delta: float) -> void:
    if Input.is_action_just_pressed("my_plugin_action") and _is_action_enabled():
        _on_action()

func _is_action_enabled() -> bool:
    # EditorInterface 在 4.2+ 是全局单例
    return EditorInterface.get_edited_scene_root() != null

# 6. 快捷键冲突：编辑器不提供 get_editor_plugins()/has_shortcut() 这类查询接口，
#    需要自己维护已注册列表做比对，最终冲突由编辑器的快捷键面板统一裁决
func check_shortcut_conflict(shortcut_path: String) -> bool:
    return _registered_shortcuts.has(shortcut_path)
```

---

## 4. 错误处理最佳实践

### 4.1 错误处理

```gdscript
# GDScript 没有 try-catch，失败必须靠错误码、null 检查或布尔返回值传递
@tool
class_name ErrorHandling
extends RefCounted

# 1. 用错误码 + push_error 报告失败
func safe_operation() -> Error:
    var error := _dangerous_operation()
    if error != OK:
        push_error("Operation failed: %s" % error_string(error))
    return error

# 2. 使用错误返回
func potentially_failing_operation() -> Variant:
    var result = _do_operation()
    if result == null:
        return {"success": false, "error": "Operation failed"}
    return {"success": true, "data": result}

# 3. 使用 assert
func validate_input(value: int) -> void:
    assert(value >= 0, "Value must be non-negative")
    assert(value <= 100, "Value must be <= 100")

# 4. 使用自定义错误类型
#    ⚠️ 内部类的 extends 必须写在同一行
class CustomError extends RefCounted:

    var message: String
    var code: int

    func _init(msg: String, err_code: int) -> void:
        message = msg
        code = err_code

# 5. 错误日志
func log_error(error: Variant, context: String = "") -> void:
    var error_log := {
        "timestamp": Time.get_datetime_string_from_unix(Time.get_unix_time()),
        "error": error,
        "context": context,
        "stack_trace": get_stack(),
    }
    _save_error_log(error_log)

func _save_error_log(error_log: Dictionary) -> void:
    var file := FileAccess.open("user://logs/error.log", FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(error_log, "  "))
        file.close()
```

### 4.2 输入验证

```gdscript
# 输入验证
@tool
class_name InputValidation
extends RefCounted

# 1. 验证输入类型
func validate_input_type(value: Variant, expected_type: Variant.Type) -> bool:
    if typeof(value) != expected_type:
        push_error("Invalid input type. Expected: " + var_to_str(expected_type))
        return false
    return true

# 2. 验证输入范围
func validate_input_range(value: int, min_value: int, max_value: int) -> bool:
    if value < min_value or value > max_value:
        push_error("Value out of range: %d (expected %d-%d)" % [value, min_value, max_value])
        return false
    return true

# 3. 验证输入非空
func validate_not_empty(value: String) -> bool:
    if value.strip_edges().length() == 0:
        push_error("Input cannot be empty")
        return false
    return true

# 4. 验证文件路径
func validate_file_path(path: String) -> bool:
    if not ResourceLoader.exists(path):
        push_error("File not found: " + path)
        return false
    return true

# 5. 验证 URL
func validate_url(url: String) -> bool:
    # ⚠️ HTTPClient 没有 connect(url) 方法（那是 3.x 的旧 API）。
    #    4.x 要先 connect_to_host(host, port)，url 只写主机之后的部分。
    var parsed := url.split("/")
    if parsed.size() < 3:
        push_error("Invalid URL: " + url)
        return false

    var host := parsed[2]
    var port := 443 if parsed[1] == "https" else 80
    var http := HTTPClient.new()
    var error := http.connect_to_host(host, port)
    if error != OK:
        push_error("Invalid URL: " + url)
        return false
    http.close()
    return true
```

### 4.3 错误恢复

```gdscript
# 错误恢复
@tool
class_name ErrorRecovery
extends Node

# 1. 自动重试（GDScript 无异常，用返回值判断成败）
func operation_with_retry(max_retries: int = 3) -> bool:
    var retries := 0
    while retries < max_retries:
        if risky_operation():
            return true
        retries += 1
        if retries >= max_retries:
            push_error("Operation failed after %d retries" % max_retries)
            return false
        await get_tree().create_timer(1.0 * retries).timeout  # 退避等待
    return false

func risky_operation() -> bool:
    return true

# 2. 优雅降级
func operation_with_fallback() -> Dictionary:
    var result := _try_primary_method()
    if not result["success"]:
        result = _try_fallback_method()
    return result

func _try_primary_method() -> Dictionary:
    return {"success": false, "error": "Primary method failed"}

func _try_fallback_method() -> Dictionary:
    return {"success": true, "data": "Fallback result"}

# 3. 事务处理
var transaction_active: bool = false
var saved_state: Variant

func start_transaction() -> void:
    saved_state = _save_state()
    transaction_active = true

func commit_transaction() -> void:
    transaction_active = false
    saved_state = null

func rollback_transaction() -> void:
    _restore_state(saved_state)
    transaction_active = false

func _save_state() -> Variant:
    return null

func _restore_state(state: Variant) -> void:
    pass

# 4. 错误报告
func report_error(error: Variant, recoverable: bool = true) -> void:
    var error_report := {
        "error": error,
        "timestamp": Time.get_unix_time(),
        "recoverable": recoverable,
        "user_action": "Please try again or contact support",
    }
    show_error_dialog(error_report)

func show_error_dialog(report: Dictionary) -> void:
    push_error(str(report))

# 5. 自动恢复
func auto_recover(error_type: String) -> bool:
    match error_type:
        "network_error":
            return _recover_network_error()
        "file_error":
            return _recover_file_error()
        "resource_error":
            return _recover_resource_error()
        _:
            return false

func _recover_network_error() -> bool:
    return true

func _recover_file_error() -> bool:
    return true

func _recover_resource_error() -> bool:
    return true
```

---

## 5. 安全最佳实践

### 5.1 权限检查

```gdscript
# 权限检查
@tool
class_name PermissionChecks
extends EditorPlugin

# 1. 检查插件是否启用
func check_plugin_enabled(plugin_dir_name: String) -> bool:
    # EditorInterface 在 4.2+ 是全局单例
    return EditorInterface.is_plugin_enabled(plugin_dir_name)

# 2. 检查文件系统权限
func check_file_permission(path: String, mode: int) -> bool:
    if mode == FileAccess.READ and not FileAccess.file_exists(path):
        return false
    if mode == FileAccess.WRITE:
        var dir := DirAccess.open(path.get_base_dir())
        return dir != null
    return true

# 3. 检查资源权限
func check_resource_permission(path: String) -> bool:
    return ResourceLoader.exists(path)

# 4. 检查用户角色
#    编辑器没有「用户角色」的概念，这属于应用层的权限模型，
#    插件里通常自己实现（例如读项目设置里的白名单）
func check_user_role(required_role: String) -> bool:
    var allowed: Array = ProjectSettings.get_setting("my_plugin/allowed_roles", [])
    return allowed.has(required_role)

# 5. 检查项目状态
func check_project_state() -> bool:
    return EditorInterface.get_edited_scene_root() != null
```

### 5.2 数据验证

```gdscript
# 数据验证
@tool
class_name DataValidation
extends RefCounted

# 1. 验证 JSON 数据
func validate_json_data(data: Variant, schema: Dictionary) -> bool:
    if not (data is Dictionary):
        return false
    for key in schema:
        if not data.has(key):
            push_error("Missing required field: " + key)
            return false
        var expected_type = schema[key]
        if typeof(data[key]) != expected_type:
            push_error("Invalid type for field: " + key + ". Expected: " + str(expected_type))
            return false
    return true

# 2. 验证数组
func validate_array(arr: Array, item_type: Variant.Type, min_size: int = 0, max_size: int = -1) -> bool:
    if arr.size() < min_size:
        push_error("Array too small. Minimum size: " + str(min_size))
        return false
    if max_size >= 0 and arr.size() > max_size:
        push_error("Array too large. Maximum size: " + str(max_size))
        return false
    for item in arr:
        if typeof(item) != item_type:
            push_error("Invalid item type in array")
            return false
    return true

# 3. 验证字典
func validate_dictionary(dict: Dictionary, keys: Dictionary) -> bool:
    for key in keys:
        if not dict.has(key):
            push_error("Missing required key: " + key)
            return false
        var validator: Callable = keys[key]
        if not validator.call(dict[key]):
            push_error("Invalid value for key: " + key)
            return false
    return true

# 4. 验证字符串
#    ⚠️ 不要把参数命名为 str：那是 GDScript 的全局函数名，会遮蔽它
func validate_string(value: String, min_length: int = 0, max_length: int = -1, regex: String = "") -> bool:
    if value.length() < min_length:
        push_error("String too short. Minimum length: " + str(min_length))
        return false
    if max_length >= 0 and value.length() > max_length:
        push_error("String too long. Maximum length: " + str(max_length))
        return false
    if regex != "":
        if not value.match(regex):
            push_error("String does not match pattern: " + regex)
            return false
    return true

# 5. 验证数值
func validate_number(value: Variant, min_value: float = -INF, max_value: float = INF, is_integer: bool = false) -> bool:
    if is_integer and not (value is int):
        push_error("Value must be an integer")
        return false
    if value < min_value:
        push_error("Value below minimum: " + str(min_value))
        return false
    if value > max_value:
        push_error("Value above maximum: " + str(max_value))
        return false
    return true
```

### 5.3 安全操作

```gdscript
# 安全操作
@tool
class_name SafeOperations
extends RefCounted

# 1. 安全文件操作
func safe_file_operation(operation: Callable, path: String) -> Variant:
    if not check_file_permission(path, FileAccess.WRITE):
        push_error("Permission denied for file: " + path)
        return null
    return operation.call(path)

func check_file_permission(path: String, mode: int) -> bool:
    if mode == FileAccess.WRITE:
        var dir := DirAccess.open(path.get_base_dir())
        return dir != null
    return FileAccess.file_exists(path)

# 2. 安全网络操作
func safe_network_operation(request: String, url: String) -> Variant:
    if not _is_url_safe(url):
        push_error("Unsafe URL: " + url)
        return null
    return _perform_network_request(request, url)

func _is_url_safe(url: String) -> bool:
    # 只允许 http / https
    return url.begins_with("http://") or url.begins_with("https://")

func _perform_network_request(request: String, url: String) -> Variant:
    return null

# 3. 安全资源加载
func safe_resource_load(path: String) -> Resource:
    if not ResourceLoader.exists(path):
        push_error("Permission denied for resource: " + path)
        return null
    var resource := load(path)
    if resource == null:
        push_error("Failed to load resource: " + path)
        return null
    return resource

# 4. 安全数据导出
func safe_data_export(data: Variant, path: String) -> bool:
    if not _is_valid_export_data(data):
        push_error("Invalid export data")
        return false
    if not check_file_permission(path, FileAccess.WRITE):
        push_error("Permission denied for export path: " + path)
        return false
    return _export_data(data, path)

func _is_valid_export_data(data: Variant) -> bool:
    return data != null

func _export_data(data: Variant, path: String) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(data, "  "))
    file.close()
    return true
```

---

## 6. 实践：完整插件

```gdscript
# 高质量插件示例
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name HighQualityPlugin
extends EditorPlugin

# 信号
signal plugin_initialized
signal error_occurred

# 导出属性
@export var debug_mode: bool = false
@export var max_cache_size: int = 100

# 私有变量
var dock: Control
var button: Button
var cache: Dictionary = {}
var settings: EditorSettings
var status_label: Label

func _enter_tree() -> void:
    _validate_environment()
    _setup_dock()
    _setup_button()
    _load_settings()
    plugin_initialized.emit()

func _exit_tree() -> void:
    _cleanup_dock()
    _cleanup_button()
    _save_settings()

func _validate_environment() -> void:
    # 验证环境
    cache.clear()

func _setup_dock() -> void:
    # 设置停靠面板
    dock = Control.new()
    dock.name = "HighQualityPluginDock"

    var vbox := VBoxContainer.new()
    dock.add_child(vbox)

    # 状态标签
    status_label = Label.new()
    status_label.text = "Ready"
    vbox.add_child(status_label)

    # 进度条
    var progress_bar := ProgressBar.new()
    progress_bar.visible = false
    vbox.add_child(progress_bar)

    # 控件容器
    var controls := HBoxContainer.new()
    vbox.add_child(controls)

    var btn1 := Button.new()
    btn1.text = "Action 1"
    btn1.pressed.connect(_on_action_1_pressed)
    controls.add_child(btn1)

    var btn2 := Button.new()
    btn2.text = "Action 2"
    btn2.pressed.connect(_on_action_2_pressed)
    controls.add_child(btn2)

    add_control_to_dock(EditorPlugin.DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock() -> void:
    if dock:
        # 先从 Dock 摘掉再释放；对已在场景树中的节点用 queue_free()
        remove_control_from_docks(dock)
        dock.queue_free()
        dock = null

func _setup_button() -> void:
    # 设置工具栏按钮
    button = Button.new()
    button.text = "High Quality Plugin"
    button.pressed.connect(_on_toolbar_button_pressed)
    add_control_to_container(EditorPlugin.CONTAINER_TOOLBAR, button)

func _cleanup_button() -> void:
    if button:
        # ⚠️ 没有 remove_control_from_containers()；
        #    正确 API 是 2 参的 remove_control_from_container(容器枚举, 控件)
        remove_control_from_container(EditorPlugin.CONTAINER_TOOLBAR, button)
        button.queue_free()
        button = null

func _load_settings() -> void:
    # 加载设置
    # ⚠️ 不要用 EditorSettings.new()：编辑器用的是单例，
    #    new() 出来的实例与编辑器无关，写进去也不会落盘。
    settings = EditorInterface.get_editor_settings()

func _save_settings() -> void:
    # 保存设置：编辑器设置在变更后会自动保存
    if settings:
        settings.set_setting("plugins/high_quality_plugin/cache_size", cache.size())
        settings.set_setting("plugins/high_quality_plugin/debug_mode", debug_mode)

func _on_toolbar_button_pressed() -> void:
    if dock:
        dock.visible = not dock.visible

func _on_action_1_pressed() -> void:
    status_label.text = "Processing Action 1..."
    call_deferred("_do_action_1")

func _on_action_2_pressed() -> void:
    status_label.text = "Processing Action 2..."
    call_deferred("_do_action_2")

func _do_action_1() -> void:
    # GDScript 没有异常，用返回值判断执行结果
    var success := await _run_action(1)
    if not success:
        status_label.text = "Action 1 failed"
        error_occurred.emit("Action 1 failed")

func _do_action_2() -> void:
    var success := await _run_action(2)
    if not success:
        status_label.text = "Action 2 failed"
        error_occurred.emit("Action 2 failed")

func _run_action(index: int) -> bool:
    for i in range(10):
        status_label.text = "Processing Action %d... %d%%" % [index, (i + 1) * 10]
        await get_tree().create_timer(0.1).timeout
    status_label.text = "Action %d completed" % index
    return true

func _is_action_enabled(_action: String) -> bool:
    if debug_mode:
        return true
    return EditorInterface.get_edited_scene_root() != null

func _show_error(message: String) -> void:
    status_label.text = "Error: " + message
    push_error("High Quality Plugin: " + message)

func _show_success(message: String) -> void:
    status_label.text = "Success: " + message
    print_debug("High Quality Plugin: " + message)

func _show_warning(message: String) -> void:
    status_label.text = "Warning: " + message
    push_warning("High Quality Plugin: " + message)
```

### 6.1 插件系统的组装

```gdscript
# 插件系统的组装
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name FullPluginSystem
extends EditorPlugin

var _hub: Node

func _enter_tree() -> void:
    # 编辑器没有 register_plugin() / unregister_plugin() / get_plugins()：
    # 插件实例由编辑器扫描 addons/ 之后自行创建。
    # 插件之间要共享实例，唯一正规做法是注册成 Autoload 单例。
    _hub = get_node_or_null("/root/PluginHub")
    if _hub == null:
        add_autoload_singleton("PluginHub", "res://addons/my_plugin/plugin_hub.gd")
        _hub = get_node_or_null("/root/PluginHub")

func _exit_tree() -> void:
    if _hub:
        remove_autoload_singleton("PluginHub")
        _hub = null

func get_hub() -> Node:
    return _hub

func get_status() -> Dictionary:
    return {
        "hub": _hub != null,
        "undo_redo": get_undo_redo() != null,
    }
```

---

## 7. `@tool` 的真实行为与编辑器内脚本生命周期

这是编辑器扩展的第一课，也是最容易被忽略的一课。

### 7.1 `@tool` 到底做了什么

```gdscript
# @tool 脚本
@tool
extends Node

func _ready() -> void:
    # 有 @tool：这段代码在「编辑器进程」里也会跑
    print("在编辑器里也会执行")
```

> **机制说明**：
> - 4.3 的 `EditorScript.xml` 写得非常明确：
>   「Extending scripts need to have **tool mode** enabled.」
>   `Object.xml` 也写着：「If the object's script is not `@tool`,
>   this method will not be called in the editor.」（指 `_get_property_list()`）。
> - **不加 `@tool`，脚本在编辑器进程里根本不会被实例化**。
>   插件会表现为「启用了但什么也没发生」，而且**不会有任何报错**——
>   这是编辑器扩展最常见的「静默失败」。
> - 4.3 的 `gdscript_basics.rst` 明确：`@tool` 注解
>   「must be placed at the top of the file」。
> - 加了 `@tool` 之后，脚本的代码会在**编辑器进程**内执行，
>   也就是和游戏运行时**不同的进程**。所以：
>   - `Engine.is_editor_hint()` 返回 `true`；
>   - 访问 `EditorInterface` 是安全的；
>   - 但**不要**在 `@tool` 代码里做会污染项目的事（写文件、删资源、改场景）。

### 7.2 编辑器内脚本的生命周期

| 时机 | 发生了什么 |
|---|---|
| 插件启用 | 编辑器实例化 `EditorPlugin`，调用 `_enter_tree()` |
| 节点进入场景树 | 节点上的 `@tool` 脚本被实例化，触发 `_ready()` |
| 节点离开场景树 | 触发 `_exit_tree()` / `_notification(NOTIFICATION_PREDELETE)` |
| **修改并保存脚本** | 脚本被热重载：旧实例被销毁，**新实例被重建**，`_ready()` 再次触发 |
| 插件禁用 | 调用 `_exit_tree()`，插件实例被销毁 |
| 导出游戏 | `@tool` 代码**不进入运行包**；导出的运行包里是同一份脚本，但没有工具模式 |

```gdscript
# 观察热重载
@tool
extends Node2D

func _ready() -> void:
    # ⚠️ 每次脚本热重载都会重新走到这里。
    #    所以 _ready() 里做初始化时，
    #    必须能安全地重复执行（幂等），或者用 _enter_tree() / _exit_tree() 配对。
    print("[%s] _ready()" % get_instance_id())

func _enter_tree() -> void:
    # 进入场景树时调用；和 _ready() 一样会被热重载触发
    print("[%s] _enter_tree()" % get_instance_id())

func _exit_tree() -> void:
    # 离开场景树时调用：热重载、关闭场景、删除节点都会走到这里
    print("[%s] _exit_tree()" % get_instance_id())
```

> **机制说明**：
> - `_ready()` 在节点**进入场景树**时触发（`Node._ready()` 的标准语义），
>   在编辑器里也一样——编辑器打开场景时就会实例化 `@tool` 节点并触发 `_ready()`。
> - **脚本热重载会重建节点**：编辑器重新加载脚本时，旧实例被销毁、
>   新实例被创建，`@tool` 脚本的状态（成员变量）**会丢失**。
>   因此需要跨重载保留的状态必须落在外部（文件、`EditorSettings`、
>   `ProjectSettings`、Autoload 单例）而不是节点成员里。
> - `@tool` 代码**不会被编译进导出的运行包**：工具模式是「编辑器行为」，
>   导出后的游戏里脚本照常运行，但不会执行工具分支
>   （`Engine.is_editor_hint()` 在运行包里恒为 `false`）。
> - 官方文档在工具模式一节有一条明确警告：
>   「Be cautious when freeing nodes with `queue_free()` or `free()`
>   in a tool script (especially the script's owner itself).」
>   ——在 `@tool` 脚本里释放节点要格外小心，尤其是脚本自己所在的节点。

### 7.3 什么时候必须加 `@tool`

| 场景 | 需要 `@tool`？ |
|---|---|
| `EditorPlugin` 主脚本 | **必须** |
| `EditorScript` | **必须** |
| `EditorInspectorPlugin` / `EditorImportPlugin` / `EditorExportPlugin` | **必须** |
| 挂在编辑器里、被 `@tool` 节点引用的辅助脚本 | **必须** |
| 纯逻辑工具类（被上面那些脚本调用） | 不必须，但加了也无妨 |
| 游戏运行时的普通脚本 | **不要**加 |

---

## 8. 编辑器内撤销 / 重做

编辑器里几乎所有操作都能撤销。插件做的修改**也应该**能撤销，
否则用户会看到一个「我的改动怎么回不去了」的编辑器。

```gdscript
# 编辑器内撤销 / 重做
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name UndoRedoExample
extends EditorPlugin

func _enter_tree() -> void:
    # EditorPlugin.get_undo_redo() 返回 EditorUndoRedoManager，
    # 它按「场景」自动把操作归到对应的撤销历史里。
    add_tool_menu_item("我的插件/批量改属性", _on_batch_set)

func _exit_tree() -> void:
    remove_tool_menu_item("我的插件/批量改属性")

func _on_batch_set() -> void:
    var root := EditorInterface.get_edited_scene_root()
    if root == null:
        return

    var undo_redo := get_undo_redo()
    # 一次操作 = 一个撤销步骤
    undo_redo.create_action("批量修改属性")
    for child in root.get_children():
        if child is Node2D:
            var node2d := child as Node2D
            # 记录「做」的操作：改之后的值
            undo_redo.add_do_property(node2d, "position", node2d.position + Vector2(10, 0))
            # 记录「撤」的操作：改之前的值
            undo_redo.add_undo_property(node2d, "position", node2d.position)
    # commit_action() 默认会立即执行 do 操作
    undo_redo.commit_action()
```

```gdscript
# 更复杂的操作：新增 / 删除节点
@tool
extends EditorPlugin

func add_node_with_undo(parent: Node, node: Node) -> void:
    var undo_redo := get_undo_redo()
    undo_redo.create_action("添加节点")
    # do：把节点加进来
    undo_redo.add_do_method(parent, "add_child", node)
    # undo：把它摘出去
    undo_redo.add_undo_method(parent, "remove_child", node)
    undo_redo.commit_action()
```

> **机制说明**：
> - `EditorPlugin.get_undo_redo()` 返回 `EditorUndoRedoManager`
>   （继承 `Object`），它是**编辑器插件专用的撤销管理器**，
>   会自动判断一次操作属于哪个场景的撤销历史：
>   - 操作对象是 `Node` → 归到当前编辑场景；
>   - 操作对象是内建资源 → 按资源路径归到对应场景；
>   - 其它（外部资源、项目设置等）→ 归到全局历史。
> - `EditorUndoRedoManager` 的 API 与 `UndoRedo` 基本一致，
>   差别是它用「对象 + 方法名」而不是 `Callable`：
>   `add_do_method(object, method, ...)` / `add_undo_method(object, method, ...)`。
> - 属性版本是 `add_do_property(object, property, value)` /
>   `add_undo_property(object, property, value)`。
> - 流程固定是：`create_action(name)` → 若干 `add_do_*` / `add_undo_*`
>   → `commit_action()`。
> - 想在用户改动 Inspector 里的某个属性时顺带做点事，
>   用 `EditorPlugin.add_undo_redo_inspector_hook_callback(callable)`，
>   回调签名是 `(undo_redo, modified_object, property, new_value)`。
> - 不需要接入编辑器历史时，直接用普通的 `UndoRedo` 类即可。

---

## 9. 插件设置的正规存储位

插件总要存点东西：用户改了开关、上次打开到哪个标签页、缓存的索引……
存哪里是有讲究的。

### 9.1 三种存储位的取舍

| 存储位 | 作用域 | 何时用 | API |
|---|---|---|---|
| **EditorSettings** | 跨项目的**编辑器全局**设置 | 用户个人偏好（主题、快捷键、面板布局） | `EditorInterface.get_editor_settings().set_setting("plugins/<name>/<key>", value)` |
| **ProjectSettings** | 项目内、**随项目提交**的设置 | 团队共享的项目配置 | `ProjectSettings.set_setting("my_plugin/<key>", value)` + `ProjectSettings.save()` |
| **ConfigFile @ `user://`** | 用户本地数据 | 缓存、索引、最近打开记录 | `ConfigFile` + `cfg.save("user://my_plugin.cfg")` |

```gdscript
# 插件设置的正规存储位
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PluginSettingsStore
extends EditorPlugin

const NS := "plugins/my_plugin/"

func _enter_tree() -> void:
    _load_editor_settings()
    _load_user_data()

func _load_editor_settings() -> void:
    # 编辑器全局设置：用 EditorInterface 拿**单例**
    # ⚠️ EditorSettings.new() 造出来的是与编辑器无关的普通实例，
    #    写进去不会落盘，编辑器也读不到。
    var settings := EditorInterface.get_editor_settings()
    var theme := settings.get_setting(NS + "theme", "Default")
    print("上次使用的面板主题：", theme)

func _save_editor_settings() -> void:
    # 编辑器设置是「变更后自动保存」的：
    # 4.3 的 EditorSettings **没有**暴露 save() 给脚本调用。
    var settings := EditorInterface.get_editor_settings()
    settings.set_setting(NS + "theme", "Default")

func _load_user_data() -> Dictionary:
    # 用户本地数据：ConfigFile 存到 user://
    var cfg := ConfigFile.new()
    if cfg.load("user://my_plugin.cfg") != OK:
        return {}
    return cfg.get_value("cache", "recent", {})

func _save_user_data(data: Dictionary) -> void:
    var cfg := ConfigFile.new()
    cfg.set_value("cache", "recent", data)
    var err := cfg.save("user://my_plugin.cfg")
    if err != OK:
        push_error("保存用户数据失败，错误码 %d" % err)
```

> **机制说明**：
> - **命名空间**：`EditorSettings` 的键名用斜杠分层，
>   官方建议用 `snake_case`。插件一律放在 `plugins/<插件名>/` 下面，
>   避免和引擎自己的键撞车。
> - **自动保存**：`EditorSettings` 的类文档写明
>   「Editor settings are saved automatically when changed.」，
>   所以 4.x **不需要**（也没有脚本可用的）手动 `save()`。
>   `EditorSettings.save()` 是引擎内部的 `static` C++ 方法，没有绑定给脚本。
> - **快捷键**：`EditorSettings.add_shortcut(path, shortcut)` 是 **4.4+** 才有的方法，
>   4.3 没有。4.3 的替代做法是
>   `set_builtin_action_override(name, events)` 覆盖一个**内建**编辑器动作的按键。
> - **项目设置**：写 `ProjectSettings` 要显式 `ProjectSettings.save()`
>   才会写进 `project.godot`；只调 `set_setting()` 不会落盘。
>   这和 `EditorSettings` 的行为不同，别搞混。

---

## 📝 本章总结

### 核心要点

1. **`@tool` 是编辑器扩展的地基**：不加它脚本在编辑器里不会被实例化，
   而且**不报错**；4.3 的 `EditorScript.xml` 明确要求 tool 模式
2. **`@tool` 脚本会被热重载重建**：`@ready` / `_ready()` 会再次触发，
   成员变量会丢失；跨重载的状态要存在外部
3. **`@tool` 代码不进入导出包**，运行包里 `Engine.is_editor_hint()` 恒为 `false`
4. **撤销要用 `EditorPlugin.get_undo_redo()`**（`EditorUndoRedoManager`）：
   `create_action()` → `add_do_*` / `add_undo_*` → `commit_action()`
5. **设置三选一**：`EditorSettings`（个人偏好，自动保存）、
   `ProjectSettings`（团队共享，要 `save()`）、`ConfigFile @ user://`（本地数据）
6. **`EditorSettings.new()` 是错的**，要用
   `EditorInterface.get_editor_settings()` 拿单例
7. **没有 `push_debug_message()`**：用 `print_debug()`

### 关键术语

| 术语 | 解释 |
|---|---|
| `@tool` | 工具模式注解，让脚本在编辑器进程内执行 |
| 热重载 | 修改保存脚本后，编辑器销毁旧实例并重建新实例 |
| EditorUndoRedoManager | 编辑器插件专用的撤销/重做管理器 |
| EditorSettings | 编辑器全局设置（单例，变更后自动保存） |
| ProjectSettings | 项目设置（需 `save()` 才落盘） |
| `user://` | 用户目录，插件本地数据的存放位置 |

---

## 🔗 延伸阅读

- **官方文档 · 工具模式**: <https://docs.godotengine.org/en/stable/tutorials/plugins/running_code_in_the_editor.html>
- **官方文档 · 编辑器脚本**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/scripting_the_editor.html>
- **官方文档 · 插件总览**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/index.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorplugin.html>（`get_undo_redo()`）
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorundoredomanager.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorsettings.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_undoredo.html>
- **源码位置**: `editor/plugins/editor_plugin.cpp`, `editor/editor_undo_redo_manager.cpp`

---

## 📋 下一章预告

**第 68 篇：项目总结**

- 全书分卷回顾
- 学习路径建议
- 常见问题速查

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 66 篇：编辑器扩展模板](/articles/66-editor-extension-templates.md)
**下一篇**: [第 68 篇：项目总结](/articles/68-project-summary.md)

---

*写作时间：2026-03-20*  
*字数：约 1,900 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
