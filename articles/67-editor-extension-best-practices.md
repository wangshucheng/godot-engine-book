# 第 57 篇：编辑器扩展最佳实践

> **本卷定位**: 第八卷 编辑器扩展（6 篇）  
> **前置知识**: 第 66 章 编辑器扩展模板  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编写高质量的编辑器扩展需要遵循一系列最佳实践。通过遵循这些实践，可以确保扩展的可维护性、性能、安全性和用户体验。本章将探讨代码质量、性能优化、用户交互、错误处理和安全等方面的最佳实践。

---

## 🎯 学习目标

- 掌握代码质量最佳实践
- 学会性能优化技巧
- 理解用户交互最佳实践
- 熟悉错误处理策略
- 掌握安全最佳实践

---

## 1. 代码质量最佳实践

### 1.1 命名规范

```gdscript
# 命名规范
class_name NamingConventions

# 插件命名
# - 使用帕斯卡命名法 (PascalCase)
# - 以 "Plugin" 或 "Editor" 结尾
var plugin_name = "MyCustomEditor"
var plugin_class = "MyCustomEditorPlugin"

# 函数命名
# - 使用蛇形命名法 (snake_case)
# - 动词开头，描述功能
func _enter_tree():
    pass

func setup_dock():
    pass

func cleanup_resources():
    pass

# 变量命名
# - 使用蛇形命名法 (snake_case)
# - 前缀表示范围
var private_variable: String = ""
var _internal_variable: String = ""
var public_variable: String = ""

# 常量命名
# - 使用大写蛇形命名法 (SCREAMING_SNAKE_CASE)
const MAX_CONNECTIONS = 100
const DEFAULT_TIMEOUT = 30.0
const PLUGIN_NAME = "MyCustomEditor"

# 类命名
# - 使用帕斯卡命名法 (PascalCase)
# - 描述清楚功能
class CustomEditorDock
class ResourceProcessor
class SceneValidator

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
class CustomEditor:
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
    
    func _init():
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
    pass

# 4. 行内注释
var max_retries = 3  # Maximum retry attempts for failed operations
var timeout = 30.0   # Timeout in seconds

# 5. 代码块注释
#region Resource Loading
"""
Loads resources from disk.
Handles both synchronous and asynchronous loading.
"""
func load_resources(paths: Array) -> Array:
    pass
#endregion

# 6. BUG注释
func broken_function():
    # BUG: This function doesn't handle edge cases properly
    # TODO: Fix edge case handling
    pass

# 7. TODO注释
func incomplete_function():
    # TODO: Implement error handling
    # TODO: Add unit tests
    pass
```

### 1.3 代码组织

```gdscript
# 代码组织
class_code_organization

# 1. 统一的代码结构
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
var cache: Dictionary

# 1.4 已加载的节点
@onready var label = $Label

# 2. 生命周期函数
func _enter_tree():
    # 初始化插件
    pass

func _exit_tree():
    # 清理插件
    pass

# 3. 公共接口
func initialize():
    # 初始化
    pass

func cleanup():
    # 清理
    pass

# 4. 私有方法
func _setup_ui():
    # 设置UI
    pass

func _cleanup_ui():
    # 清理UI
    pass

# 5. 事件处理
func _on_button_pressed():
    # 按钮按下
    pass

func _on_resource_loaded(path: String):
    # 资源加载完成
    pass

# 6. 内部工具函数
func _validate_path(path: String) -> bool:
    # 验证路径
    return true

func _format_timestamp() -> String:
    # 格式化时间戳
    return Time.get_datetime_string_from_unix(Time.get_unix_time())
```

---

## 2. 性能优化最佳实践

### 2.1 延迟加载

```gdscript
# 延迟加载
class_name DeferredLoading

# 1. 使用call_deferred
func setup_dock_deferred():
    call_deferred("_setup_dock")

func _setup_dock():
    # 实际的设置逻辑
    pass

# 2. 使用await进行异步操作
func load_resources_async():
    # 开始异步加载
    var loader = ResourceLoader.load_threaded_request("res://scene.tscn")
    
    # 等待加载完成
    var progress = []
    while ResourceLoader.load_threaded_get_status("res://scene.tscn", progress) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        await get_tree().create_timer(0.1).timeout
    
    # 加载完成
    var resource = ResourceLoader.load_threaded_get("res://scene.tscn")
    return resource

# 3. 使用Timer进行延迟调用
func deferred_callback():
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.one_shot = true
    timer.connect("timeout", self, "_on_timer_timeout")
    add_child(timer)
    timer.start()

func _on_timer_timeout():
    # 计时器超时
    pass

# 4. 使用队列进行批处理
var pending_operations: Array = []
var is_processing: bool = false

func queue_operation(operation):
    # 排队操作
    pending_operations.append(operation)
    if not is_processing:
        is_processing = true
        call_deferred("_process_queue")

func _process_queue():
    # 处理队列
    while pending_operations.size() > 0 and not is_processing:
        var operation = pending_operations.pop_front()
        operation.call()
    
    is_processing = false
```

### 2.2 缓存策略

```gdscript
# 缓存策略
class_name CachingStrategy

# 1. 缓存频繁访问的节点
var cached_node: Node

func _ready():
    cached_node = get_node("Path/To/Node")

func update_cached_node():
    # 使用缓存的节点
    cached_node.update()

# 2. 缓存 frequently used resources
var resource_cache: Dictionary = {}

func get_cached_resource(path: String):
    if not resource_cache.has(path):
        var resource = load(path)
        if resource:
            resource_cache[path] = resource
    return resource_cache.get(path)

func clear_resource_cache():
    # 清空资源缓存
    resource_cache.clear()

# 3. 缓存计算结果
var calculation_cache: Dictionary = {}

func expensive_calculation(input: Variant) -> Variant:
    if not calculation_cache.has(input):
        calculation_cache[input] = _do_expensive_calculation(input)
    return calculation_cache[input]

func clear_calculation_cache():
    # 清空计算缓存
    calculation_cache.clear()

# 4. 使用WeakReference
var weak_references: Dictionary = {}

func get_weak_reference(key: String, obj: Object):
    # 获取弱引用
    if not weak_references.has(key):
        weak_references[key] = obj
    return weak_references[key]

func clear_weak_references():
    # 清空弱引用
    weak_references.clear()
```

### 2.3 事件优化

```gdscript
# 事件优化
class_name EventOptimization

# 1. 使用信号代替轮询
extends Node

signal value_changed(old_value: Variant, new_value: Variant)

var _value: int = 0

func set_value(new_value: int):
    if _value != new_value:
        var old_value = _value
        _value = new_value
        value_changed.emit(old_value, new_value)

func get_value() -> int:
    return _value

# 2. 节流事件
var last_execution_time: int = 0
var cooldown = 0.1  # 100ms cooldown

func throttled_update():
    var current_time = Time.get_ticks_msec()
    if current_time - last_execution_time > cooldown * 1000:
        _do_update()
        last_execution_time = current_time

func _do_update():
    # 实际的更新逻辑
    pass

# 3. 防抖事件
var debounced_callback: Callable
var debounce_timer: Timer

func debounced_update(callback: Callable):
    # 防抖更新
    debounced_callback = callback
    
    if not debounce_timer:
        debounce_timer = Timer.new()
        debounce_timer.wait_time = 0.5
        debounce_timer.one_shot = true
        add_child(debounce_timer)
    
    debounce_timer.timeout.disconnect(_on_debounce_timeout)
    debounce_timer.timeout.connect(_on_debounce_timeout)
    debounce_timer.start()

func _on_debounce_timeout():
    # 防抖超时
    if debounced_callback:
        debounced_callback.call()
        debounced_callback = null

# 4. 批量事件
var pending_events: Array = []
var is_processing: bool = false

func queue_event(event_data):
    # 排队事件
    pending_events.append(event_data)
    if not is_processing:
        is_processing = true
        call_deferred("_process_events")

func _process_events():
    # 处理事件
    while pending_events.size() > 0:
        var event_data = pending_events.pop_front()
        _handle_event(event_data)
    
    is_processing = false

func _handle_event(event_data):
    # 处理事件
    pass
```

---

## 3. 用户交互最佳实践

### 3.1 UI响应性

```gdscript
# UI响应性
class_name UIResponsiveness

# 1. 使用loading状态
var is_loading: bool = false

func load_resources():
    is_loading = true
    update_ui_state()
    
    # 模拟异步加载
    call_deferred("_do_load_resources")

func _do_load_resources():
    # 实际的加载逻辑
    # ...
    
    is_loading = false
    update_ui_state()

func update_ui_state():
    # 更新UI状态
    if is_loading:
        loading_label.show()
        loading_progress_bar.visible = true
        loading_progress_bar.value = 50
    else:
        loading_label.hide()
        loading_progress_bar.visible = false

# 2. 提供反馈
func perform_action():
    # 显示进度反馈
    status_label.text = "Performing action..."
    
    # 执行操作
    call_deferred("_do_action")

func _do_action():
    # 实际的操作
    # ...
    
    # 显示完成反馈
    status_label.text = "Action completed successfully"
    call_deferred("_clear_status", 2.0)

func _clear_status(delay: float):
    # 延迟清理状态
    await get_tree().create_timer(delay).timeout
    status_label.text = ""

# 3. 使用确认对话框
func dangerous_action():
    var dialog = ConfirmationDialog.new()
    dialog.title_text = "Confirm Action"
    dialog.dialog_text = "Are you sure you want to perform this action?"
    
    dialog.connect("confirmed", self, "_on_action_confirmed")
    dialog.popup_centered()

func _on_action_confirmed():
    # 确认后执行操作
    pass

# 4. 提供撤销功能
var action_history: Array = []
var current_action_index: int = -1

func perform_action_with_undo(action_data):
    # 执行带有撤销功能的操作
    # ...
    
    # 添加到历史记录
    action_history.append(action_data)
    current_action_index += 1
    
    # 移除后续的历史记录
    while current_action_index < action_history.size() - 1:
        action_history.pop_back()

func undo_last_action():
    # 撤销最后一个操作
    if current_action_index >= 0:
        var action = action_history[current_action_index]
        _undo_action(action)
        current_action_index -= 1

func redo_last_action():
    # 恢复最后一个操作
    if current_action_index < action_history.size() - 1:
        current_action_index += 1
        var action = action_history[current_action_index]
        _redo_action(action)
```

### 3.2 用户提示

```gdscript
# 用户提示
class_name UserNotifications

# 1. 使用push_debug_messages
func debug_message(message: String):
    push_debug_message(message)

# 2. 使用push_warning
func warning_message(message: String):
    push_warning(message)

# 3. 使用push_error
func error_message(message: String):
    push_error(message)

# 4. 使用自定义对话框
func custom_notification(message: String, title: String = "Notification"):
    var dialog = PopupPanel.new()
    dialog.title_text = title
    dialog.modal = true
    
    var vbox = VBoxContainer.new()
    dialog.add_child(vbox)
    
    var label = Label.new()
    label.text = message
    vbox.add_child(label)
    
    var button = Button.new()
    button.text = "OK"
    button.connect("pressed", dialog, "queue_free")
    vbox.add_child(button)
    
    dialog.popup_centered()

# 5. 使用状态栏消息
func status_bar_message(message: String, duration: int = 3):
    # 假设有状态栏
    var status_label = get_node("StatusBar/Label")
    status_label.text = message
    
    if duration > 0:
        call_deferred("_clear_status_bar", duration)

func _clear_status_bar(delay: float):
    # 清理状态栏
    await get_tree().create_timer(delay).timeout
    status_label.text = ""
```

### 3.3 键盘快捷键

```gdscript
# 键盘快捷键
class_name KeyboardShortcuts

# 1. 注册快捷键
func _enter_tree():
    # 添加快捷键
    add_tool_menu_item("My Plugin/Action", self, "_on_action")

func _exit_tree():
    # 移除快捷键
    remove_tool_menu_items()

# 2. 使用快捷键助手
var shortcut_helper: ShortcutHelper

func _enter_tree():
    shortcut_helper = ShortcutHelper.new()
    shortcut_helper.add_shortcut("Ctrl+Shift+A", "My Plugin/Action", self, "_on_action")

# 3. 上下文敏感快捷键
func _process(delta):
    # 检查快捷键
    if Input.is_action_just_pressed("my_plugin_action"):
        if _is_action_enabled():
            _on_action()

func _is_action_enabled() -> bool:
    # 检查动作是否可用
    return get_editor_interface().get_edited_scene_root() != null

# 4. 快捷键自定义
@export var custom_shortcut: String = "Ctrl+Shift+A"

func _ready():
    # 设置自定义快捷键
    shortcut_helper.add_shortcut(custom_shortcut, "My Plugin/Action", self, "_on_action")

# 5. 快捷键冲突解决
func check_shortcut_conflict(shortcut: String) -> bool:
    # 检查快捷键冲突
    var editors = get_editor_interface().get_editor_plugins()
    for editor in editors:
        if editor.has_shortcut(shortcut):
            return true
    return false
```

---

## 4. 错误处理最佳实践

### 4.1 异常处理

```gdscript
# 异常处理
class_name ExceptionHandling

# 1. 使用try-catch
func safe_operation():
    try:
        # 可能出错的操作
        dangerous_operation()
    except:
        push_error("Operation failed: " + str(error_message))

# 2. 使用错误返回
func potentially_failing_operation() -> Variant:
    var result = _do_operation()
    if result == null:
        return {"success": false, "error": "Operation failed"}
    return {"success": true, "data": result}

# 3. 使用assert
func validate_input(value: int):
    assert(value >= 0, "Value must be non-negative")
    assert(value <= 100, "Value must be <= 100")

# 4. 使用自定义异常
class CustomError:
    extends RefCounted
    
    var message: String
    var code: int
    
    func _init(msg: String, err_code: int):
        message = msg
        code = err_code

# 5. 错误日志
func log_error(error: Variant, context: String = ""):
    var timestamp = Time.get_datetime_string_from_unix(Time.get_unix_time())
    var error_log = {
        "timestamp": timestamp,
        "error": error,
        "context": context,
        "stack_trace": get_stack()
    }
    
    # 保存到文件
    _save_error_log(error_log)
```

### 4.2 输入验证

```gdscript
# 输入验证
class_name InputValidation

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
    if value.trim_prefix(" ").trim_suffix(" ").length() == 0:
        push_error("Input cannot be empty")
        return false
    return true

# 4. 验证文件路径
func validate_file_path(path: String) -> bool:
    if not ResourceLoader.exists(path):
        push_error("File not found: " + path)
        return false
    return true

# 5. 验证URL
func validate_url(url: String) -> bool:
    var http = HTTPClient.new()
    var error = http.connect(url)
    
    if error != OK:
        push_error("Invalid URL: " + url)
        return false
    
    http.close()
    return true
```

### 4.3 错误恢复

```gdscript
# 错误恢复
class_name ErrorRecovery

# 1. 自动重试
func operation_with_retry(max_retries: int = 3):
    var retries = 0
    while retries < max_retries:
        try:
            # 执行操作
            risky_operation()
            return true  # 成功
        except:
            retries += 1
            if retries >= max_retries:
                push_error("Operation failed after %d retries" % max_retries)
                return false
            await get_tree().create_timer(1.0 * retries).timeout  # 指数backoff

# 2. 优雅降级
func operation_with_fallback():
    var result = _try_primary_method()
    if not result["success"]:
        result = _try_fallback_method()
    return result

func _try_primary_method() -> Dictionary:
    # 主要方法
    return {"success": false, "error": "Primary method failed"}

func _try_fallback_method() -> Dictionary:
    # 备用方法
    return {"success": true, "data": "Fallback result"}

# 3. 事务处理
var transaction_active: bool = false
var saved_state: Variant

func start_transaction():
    # 开始事务
    saved_state = _save_state()
    transaction_active = true

func commit_transaction():
    # 提交事务
    transaction_active = false
    saved_state = null

func rollback_transaction():
    # 回滚事务
    _restore_state(saved_state)
    transaction_active = false

# 4. 错误报告
func report_error(error: Variant, recoverable: bool = true):
    # 报告错误
    var error_report = {
        "error": error,
        "timestamp": Time.get_unix_time(),
        "recoverable": recoverable,
        "user_action": "Please try again or contact support"
    }
    
    # 显示给用户
    show_error_dialog(error_report)

# 5. 自动恢复
func auto_recover(error: Variant) -> bool:
    # 自动恢复
    match error.type:
        "network_error":
            return _recover_network_error()
        "file_error":
            return _recover_file_error()
        "resource_error":
            return _recover_resource_error()
        _:
            return false

func _recover_network_error() -> bool:
    # 恢复网络错误
    # 重连等
    return true

func _recover_file_error() -> bool:
    # 恢复文件错误
    # 使用默认文件等
    return true

func _recover_resource_error() -> bool:
    # 恢复资源错误
    # 重新加载等
    return true
```

---

## 5. 安全最佳实践

### 5.1 权限检查

```gdscript
# 权限检查
class_name PermissionChecks

# 1. 检查编辑器权限
func check_editor_permission(permission: String) -> bool:
    var editor_interface = get_editor_interface()
    return editor_interface.has_permission(permission)

# 2. 检查文件系统权限
func check_file_permission(path: String, mode: int) -> bool:
    if mode == FileAccess.READ and not FileAccess.file_exists(path):
        return false
    if mode == FileAccess.WRITE:
        var dir = DirAccess.open(path.get_base_dir())
        return dir != null
    return true

# 3. 检查资源权限
func check_resource_permission(path: String) -> bool:
    if not ResourceLoader.exists(path):
        return false
    # 这里可以添加更复杂的权限检查
    return true

# 4. 检查用户角色
func check_user_role(required_role: String) -> bool:
    var user = _get_current_user()
    return user.has_role(required_role)

# 5. 检查项目状态
func check_project_state() -> bool:
    var editor_interface = get_editor_interface()
    return editor_interface.get_edited_scene_root() != null
```

### 5.2 数据验证

```gdscript
# 数据验证
class_name DataValidation

# 1. 验证JSON数据
func validate_json_data(data: Variant, schema: Dictionary) -> bool:
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
        
        var validator = keys[key]
        if not validator(dict[key]):
            push_error("Invalid value for key: " + key)
            return false
    
    return true

# 4. 验证字符串
func validate_string(str: String, min_length: int = 0, max_length: int = -1, regex: String = "") -> bool:
    if str.length() < min_length:
        push_error("String too short. Minimum length: " + str(min_length))
        return false
    
    if max_length >= 0 and str.length() > max_length:
        push_error("String too long. Maximum length: " + str(max_length))
        return false
    
    if regex != "":
        if not str.match(regex):
            push_error("String does not match pattern: " + regex)
            return false
    
    return true

# 5. 验证数值
func validate_number(value: Variant, min_value: float = -INF, max_value: float = INF, is_integer: bool = false) -> bool:
    if is_integer and not value is int:
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
class_name SafeOperations

# 1. 安全文件操作
func safe_file_operation(operation: Callable, path: String) -> Variant:
    if not check_file_permission(path, FileAccess.WRITE):
        push_error("Permission denied for file: " + path)
        return null
    
    return operation.call(path)

# 2. 安全网络操作
func safe_network_operation(request: String, url: String) -> Variant:
    if not _is_url_safe(url):
        push_error("Unsafe URL: " + url)
        return null
    
    # 执行网络请求
    return _perform_network_request(request, url)

# 3. 安全资源加载
func safe_resource_load(path: String) -> Resource:
    if not check_resource_permission(path):
        push_error("Permission denied for resource: " + path)
        return null
    
    var resource = load(path)
    if not resource:
        push_error("Failed to load resource: " + path)
        return null
    
    return resource

# 4. 安全数据导出
func safe_data_export(data: Variant, path: String) -> bool:
    # 验证数据
    if not _is_valid_export_data(data):
        push_error("Invalid export data")
        return false
    
    # 验证路径
    if not check_file_permission(path, FileAccess.WRITE):
        push_error("Permission denied for export path: " + path)
        return false
    
    # 导出数据
    return _export_data(data, path)

# 5. 安全宏执行
func safe_macro_execution(code: String, context: Dictionary) -> Variant:
    # 验证代码安全性
    if not _is_code_safe(code):
        push_error("Unsafe macro code detected")
        return null
    
    # 执行代码
    return _execute_macro(code, context)
```

---

## 6. 实践：完整插件

### 6.1 高质量插件示例

```gdscript
# 高质量插件示例
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
var cache: Dictionary
var settings: EditorSettings

# 已加载的节点
@onready var status_label = %StatusLabel

func _enter_tree():
    _validate_environment()
    _setup_dock()
    _setup_button()
    _load_settings()
    plugin_initialized.emit()

func _exit_tree():
    _cleanup_dock()
    _cleanup_button()
    _save_settings()

func _validate_environment():
    # 验证环境
    if not get_editor_interface():
        push_error("Editor interface not available")
        return
    
    # 初始化缓存
    cache.clear()

func _setup_dock():
    # 设置停靠面板
    dock = Control.new()
    dock.name = "HighQualityPluginDock"
    
    var vbox = VBoxContainer.new()
    dock.add_child(vbox)
    
    # 状态标签
    status_label = Label.new()
    status_label.text = "Ready"
    vbox.add_child(status_label)
    
    # 进度条
    var progress_bar = ProgressBar.new()
    progress_bar.visible = false
    vbox.add_child(progress_bar)
    
    # 控件容器
    var controls = HBoxContainer.new()
    vbox.add_child(controls)
    
    # 按钮1
    var btn1 = Button.new()
    btn1.text = "Action 1"
    btn1.connect("pressed", self, "_on_action_1_pressed")
    controls.add_child(btn1)
    
    # 按钮2
    var btn2 = Button.new()
    btn2.text = "Action 2"
    btn2.connect("pressed", self, "_on_action_2_pressed")
    controls.add_child(btn2)
    
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock():
    # 清理停靠面板
    if dock:
        remove_control_from_docks(dock)
        dock.free()

func _setup_button():
    # 设置工具栏按钮
    button = Button.new()
    button.text = "High Quality Plugin"
    button.connect("pressed", self, "_on_toolbar_button_pressed")
    add_control_to_container(CONTAINER_TOOLBAR, button)

func _cleanup_button():
    # 清理按钮
    if button:
        remove_control_from_containers(button)
        button.free()

func _load_settings():
    # 加载设置
    settings = get_editor_interface().get_editor_settings()
    if not settings:
        settings = EditorSettings.new()

func _save_settings():
    # 保存设置
    if settings:
        settings.set_setting("plugins/high_quality_plugin/cache_size", cache.size())
        settings.set_setting("plugins/high_quality_plugin/debug_mode", debug_mode)

func _on_toolbar_button_pressed():
    # 工具栏按钮按下
    if dock:
        dock.visible = not dock.visible

func _on_action_1_pressed():
    # 动作1按钮按下
    status_label.text = "Processing Action 1..."
    
    call_deferred("_do_action_1")

func _on_action_2_pressed():
    # 动作2按钮按下
    status_label.text = "Processing Action 2..."
    
    call_deferred("_do_action_2")

func _do_action_1():
    # 执行动作1
    try:
        # 模拟处理
        for i in range(10):
            # 更新状态
            status_label.text = "Processing Action 1... %d%%" % ((i + 1) * 10)
            
            # 短暂延迟
            await get_tree().create_timer(0.1).timeout
        
        status_label.text = "Action 1 completed"
    except:
        status_label.text = "Action 1 failed"
        error_occurred.emit("Action 1 failed")

func _do_action_2():
    # 执行动作2
    try:
        # 模拟处理
        for i in range(10):
            # 更新状态
            status_label.text = "Processing Action 2... %d%%" % ((i + 1) * 10)
            
            # 短暂延迟
            await get_tree().create_timer(0.1).timeout
        
        status_label.text = "Action 2 completed"
    except:
        status_label.text = "Action 2 failed"
        error_occurred.emit("Action 2 failed")

func _is_action_enabled(action: String) -> bool:
    # 检查动作是否可用
    if debug_mode:
        return true
    
    # 这里可以添加更复杂的检查逻辑
    return get_editor_interface().get_edited_scene_root() != null

func _show_error(message: String):
    # 显示错误
    status_label.text = "Error: " + message
    push_error("High Quality Plugin: " + message)

func _show_success(message: String):
    # 显示成功
    status_label.text = "Success: " + message
    push_debug_message("High Quality Plugin: " + message)

func _show_warning(message: String):
    # 显示警告
    status_label.text = "Warning: " + message
    push_warning("High Quality Plugin: " + message)
```

### 6.2 完整插件系统

```gdscript
# 完整插件系统
class_name FullPluginSystem

var plugin1: HighQualityPlugin
var plugin2: SecondPlugin
var plugin3: ThirdPlugin

func initialize():
    # 初始化完整插件系统
    plugin1 = HighQualityPlugin.new()
    plugin2 = SecondPlugin.new()
    plugin3 = ThirdPlugin.new()
    
    _register_plugins()

func _register_plugins():
    # 注册插件
    get_editor_interface().register_plugin(plugin1)
    get_editor_interface().register_plugin(plugin2)
    get_editor_interface().register_plugin(plugin3)

func cleanup():
    # 清理完整插件系统
    _unregister_plugins()
    plugin1.free()
    plugin2.free()
    plugin3.free()

func _unregister_plugins():
    # 注销插件
    get_editor_interface().unregister_plugin(plugin1)
    get_editor_interface().unregister_plugin(plugin2)
    get_editor_interface().unregister_plugin(plugin3)

func get_plugin_status() -> Dictionary:
    # 获取插件状态
    return {
        "plugin1": {
            "name": plugin1.name,
            "initialized": true,
            "status": plugin1.status_label.text
        },
        "plugin2": {
            "name": plugin2.name,
            "initialized": true,
            "status": plugin2.status_label.text
        },
        "plugin3": {
            "name": plugin3.name,
            "initialized": true,
            "status": plugin3.status_label.text
        }
    }
```

---

## 📝 本章总结

### 核心要点

1. **代码质量**，包括命名规范、注释和代码组织
2. **性能优化**，包括延迟加载、缓存和事件优化
3. **用户交互**，包括UI响应性、用户提示和键盘快捷键
4. **错误处理**，包括异常处理、输入验证和错误恢复
5. **安全最佳实践**，包括权限检查、数据验证和安全操作

### 关键术语

| 术语 | 解释 |
|------|------|
| NamingConventions | 命名规范，统一的命名规则 |
| CommentingConventions | 注释规范，代码注释的标准 |
| DeferredLoading | 延迟加载，避免阻塞主线程 |
| CachingStrategy | 缓存策略，存储频繁使用的数据 |
| EventOptimization | 事件优化，优化事件处理 |
| UIResponsiveness | UI响应性，保持界面响应 |
| UserNotifications | 用户提示，向用户反馈信息 |
| KeyboardShortcuts | 键盘快捷键，提供快捷操作 |
| ExceptionHandling | 异常处理，处理错误情况 |
| InputValidation | 输入验证，验证用户输入 |
| ErrorRecovery | 错误恢复，从错误中恢复 |
| PermissionChecks | 权限检查，验证操作权限 |
| DataValidation | 数据验证，验证数据有效性 |
| SafeOperations | 安全操作，确保操作安全 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Editor Extension Best Practices](https://docs.godotengine.org/en/stable/tutorials/plugins/editor-extension-best-practices.html)
- **源码位置**: `editor/best_practices/`
- **技术博客**: [Godot Editor Extension Best Practices Guide](https://godotengine.org/article/editor-extension-best-practices-guide/)

---

## 📋 下一章预告

**第 68 篇：项目总结**

- 总结归纳
- 最佳实践总结
- 学习路径
- 后续资源

---

*写作时间：2026-03-20*  
*字数：约 20,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*