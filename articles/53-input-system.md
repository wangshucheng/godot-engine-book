# 第 43 篇：输入系统

> **本卷定位**: 第七卷 脚本系统（8 篇）  
> **前置知识**: 第 52 章 网络优化  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

输入系统是游戏与玩家交互的桥梁，负责处理键盘、鼠标、手柄、触摸等各种输入设备。一个优秀的输入系统能够提供流畅、响应迅速的操作体验，并支持多种输入设备和自定义映射。

Godot 提供了完整的输入系统，包括 InputMap、InputEvent、输入动作等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解输入系统的基本概念
- 掌握 InputMap 配置
- 学会 InputEvent 处理
- 熟悉输入动作系统
- 掌握输入系统优化

---

## 1. 输入系统基础

### 1.1 输入系统类型

```
输入系统类型:
┌─────────────────────────────────────────────────────────────┐
│                      输入系统类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 键盘输入：按键、组合键                                 │
│  2. 鼠标输入：移动、点击、滚轮                             │
│  3. 手柄输入：按钮、摇杆、扳机                             │
│  4. 触摸输入：点击、滑动、多点触控                         │
│  5. 手势输入：滑动手势、复杂手势                           │
│  6. 语音输入：语音命令                                     │
│  7. 体感输入：动作捕捉、姿态识别                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 输入系统组件

```
输入系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      输入系统组件                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Input：输入单例                                        │
│  2. InputMap：输入映射资源                                 │
│  3. InputEvent：输入事件基类                               │
│  4. InputEventKey：键盘事件                                │
│  5. InputEventMouseButton：鼠标按钮事件                    │
│  6. InputEventMouseMotion：鼠标移动事件                    │
│  7. InputEventJoypadButton：手柄按钮事件                   │
│  8. InputEventJoypadMotion：手柄移动事件                   │
│  9. InputEventScreenTouch：触摸事件                        │
│  10. InputEventAction：动作事件                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 输入系统流程

```
输入系统处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      输入系统处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 硬件检测输入（按键、移动等）                           │
│  2. 系统生成 InputEvent                                    │
│  3. InputMap 映射到动作                                    │
│  4. 游戏代码查询输入状态                                   │
│  5. 执行对应游戏逻辑                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. InputMap 配置

### 2.1 基础 InputMap

```gdscript
# InputMap 基础配置
class_name InputMapConfig

extends Node

func _ready():
    # 创建输入动作
    _setup_movement_actions()
    _setup_combat_actions()
    _setup_ui_actions()

func _setup_movement_actions():
    # 设置移动动作
    if not InputMap.has_action("move_forward"):
        InputMap.add_action("move_forward")
        InputMap.action_add_event("move_forward", InputEventKey.new())
        InputMap.action_add_event("move_forward", _create_key_event(KEY_W))
        InputMap.action_add_event("move_forward", _create_key_event(KEY_UP))
    
    if not InputMap.has_action("move_backward"):
        InputMap.add_action("move_backward")
        InputMap.action_add_event("move_backward", _create_key_event(KEY_S))
        InputMap.action_add_event("move_backward", _create_key_event(KEY_DOWN))
    
    if not InputMap.has_action("move_left"):
        InputMap.add_action("move_left")
        InputMap.action_add_event("move_left", _create_key_event(KEY_A))
        InputMap.action_add_event("move_left", _create_key_event(KEY_LEFT))
    
    if not InputMap.has_action("move_right"):
        InputMap.add_action("move_right")
        InputMap.action_add_event("move_right", _create_key_event(KEY_D))
        InputMap.action_add_event("move_right", _create_key_event(KEY_RIGHT))
    
    if not InputMap.has_action("jump"):
        InputMap.add_action("jump")
        InputMap.action_add_event("jump", _create_key_event(KEY_SPACE))

func _setup_combat_actions():
    # 设置战斗动作
    if not InputMap.has_action("attack"):
        InputMap.add_action("attack")
        InputMap.action_add_event("attack", _create_key_event(KEY_K))
        InputMap.action_add_event("attack", _create_mouse_button_event(BUTTON_LEFT))
    
    if not InputMap.has_action("skill"):
        InputMap.add_action("skill")
        InputMap.action_add_event("skill", _create_key_event(KEY_J))
        InputMap.action_add_event("skill", _create_mouse_button_event(BUTTON_RIGHT))
    
    if not InputMap.has_action("block"):
        InputMap.add_action("block")
        InputMap.action_add_event("block", _create_key_event(KEY_L))

func _setup_ui_actions():
    # 设置 UI 动作
    if not InputMap.has_action("ui_accept"):
        InputMap.add_action("ui_accept")
        InputMap.action_add_event("ui_accept", _create_key_event(KEY_ENTER))
    
    if not InputMap.has_action("ui_cancel"):
        InputMap.add_action("ui_cancel")
        InputMap.action_add_event("ui_cancel", _create_key_event(KEY_ESCAPE))
    
    if not InputMap.has_action("ui_pause"):
        InputMap.add_action("ui_pause")
        InputMap.action_add_event("ui_pause", _create_key_event(KEY_P))

func _create_key_event(keycode: int) -> InputEventKey:
    # 创建键盘事件
    var event = InputEventKey.new()
    event.keycode = keycode
    return event

func _create_mouse_button_event(button: int) -> InputEventMouseButton:
    # 创建鼠标按钮事件
    var event = InputEventMouseButton.new()
    event.button_index = button
    return event

func remove_action(action_name: String):
    # 移除动作
    if InputMap.has_action(action_name):
        InputMap.erase_action(action_name)

func get_action_events(action_name: String) -> Array:
    # 获取动作的所有事件
    if InputMap.has_action(action_name):
        return InputMap.get_action_list(action_name)
    return []
```

### 2.2 自定义 InputMap

```gdscript
# 自定义 InputMap
class_name CustomInputMap

extends Node

var custom_actions: Dictionary = {}

func _ready():
    load_custom_input_map()

func load_custom_input_map():
    # 加载自定义输入映射
    var config = ConfigFile.new()
    var err = config.load("user://input_config.ini")
    
    if err == OK:
        for action in config.get_sections():
            custom_actions[action] = {}
            for key in config.get_section_keys(action):
                custom_actions[action][key] = config.get_value(action, key)

func save_custom_input_map():
    # 保存自定义输入映射
    var config = ConfigFile.new()
    
    for action in custom_actions:
        config.set_value(action, "events", var_to_bytes(custom_actions[action]))
    
    config.save("user://input_config.ini")

func add_custom_action(action_name: String, events: Array):
    # 添加自定义动作
    custom_actions[action_name] = events
    
    if not InputMap.has_action(action_name):
        InputMap.add_action(action_name)
    
    for event in events:
        InputMap.action_add_event(action_name, event)

func remove_custom_action(action_name: String):
    # 移除自定义动作
    custom_actions.erase(action_name)
    if InputMap.has_action(action_name):
        InputMap.erase_action(action_name)

func rebind_action(action_name: String, new_events: Array):
    # 重新绑定动作
    remove_custom_action(action_name)
    add_custom_action(action_name, new_events)

func get_custom_binding(action_name: String) -> Array:
    # 获取自定义绑定
    return custom_actions.get(action_name, [])

func reset_to_default():
    # 重置为默认
    custom_actions.clear()
    var config = ConfigFile.new()
    config.load("user://input_config.ini")
    for section in config.get_sections():
        config.erase_section(section)
    config.save("user://input_config.ini")
```

### 2.3 输入配置文件

```gdscript
# 输入配置文件
class_name InputConfigFile

extends Node

const CONFIG_PATH = "user://input_settings.json"

func save_input_settings(settings: Dictionary):
    # 保存输入设置
    var file = FileAccess.open(CONFIG_PATH, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(settings, "  "))
        file.close()

func load_input_settings() -> Dictionary:
    # 加载输入设置
    if not FileAccess.file_exists(CONFIG_PATH):
        return {}
    
    var file = FileAccess.open(CONFIG_PATH, FileAccess.READ)
    if file:
        var text = file.get_as_text()
        file.close()
        
        var json = JSON.new()
        var error = json.parse(text)
        if error == OK:
            return json.data
    
    return {}

func apply_input_settings(settings: Dictionary):
    # 应用输入设置
    for action_name in settings:
        var events_data = settings[action_name]
        
        if InputMap.has_action(action_name):
            InputMap.erase_action(action_name)
        
        InputMap.add_action(action_name)
        
        for event_data in events_data:
            var event = _deserialize_event(event_data)
            if event:
                InputMap.action_add_event(action_name, event)

func _deserialize_event(data: Dictionary) -> InputEvent:
    # 反序列化事件
    var event_type = data.get("type", "")
    
    match event_type:
        "InputEventKey":
            var event = InputEventKey.new()
            event.keycode = data.get("keycode", 0)
            return event
        "InputEventMouseButton":
            var event = InputEventMouseButton.new()
            event.button_index = data.get("button_index", 0)
            return event
        "InputEventJoypadButton":
            var event = InputEventJoypadButton.new()
            event.button_index = data.get("button_index", 0)
            return event
    
    return null

func _serialize_event(event: InputEvent) -> Dictionary:
    # 序列化事件
    var data = {"type": event.get_class()}
    
    if event is InputEventKey:
        data["keycode"] = event.keycode
    elif event is InputEventMouseButton:
        data["button_index"] = event.button_index
    elif event is InputEventJoypadButton:
        data["button_index"] = event.button_index
    
    return data
```

---

## 3. InputEvent 处理

### 3.1 键盘事件

```gdscript
# 键盘事件处理
class_name KeyboardEventHandler

extends Node

signal key_pressed(keycode: int)
signal key_released(keycode: int)
signal key_combo_pressed(combo: Array)

var pressed_keys: Array = []
var combo_buffer: Array = []
var combo_timer: float = 0.0
const COMBO_TIMEOUT = 0.5

func _input(event):
    if event is InputEventKey:
        _handle_key_event(event)

func _handle_key_event(event: InputEventKey):
    var keycode = event.keycode
    
    if event.pressed:
        if keycode not in pressed_keys:
            pressed_keys.append(keycode)
        key_pressed.emit(keycode)
        
        # 处理组合键
        _add_to_combo_buffer(keycode)
        _check_combo()
    else:
        pressed_keys.erase(keycode)
        key_released.emit(keycode)

func _add_to_combo_buffer(keycode: int):
    # 添加到组合键缓冲
    combo_buffer.append(keycode)
    combo_timer = COMBO_TIMEOUT
    
    # 限制缓冲大小
    if combo_buffer.size() > 5:
        combo_buffer.pop_front()

func _check_combo():
    # 检查组合键
    # 可以检测特定组合，如 Ctrl+C, Alt+F4 等
    if combo_buffer.size() >= 2:
        if combo_buffer[-1] == KEY_C and combo_buffer[-2] == KEY_CTRL:
            key_combo_pressed.emit([KEY_CTRL, KEY_C])
        elif combo_buffer[-1] == KEY_V and combo_buffer[-2] == KEY_CTRL:
            key_combo_pressed.emit([KEY_CTRL, KEY_V])

func _process(delta):
    # 更新组合键计时器
    if combo_timer > 0:
        combo_timer -= delta
        if combo_timer <= 0:
            combo_buffer.clear()

func is_key_pressed(keycode: int) -> bool:
    return keycode in pressed_keys

func get_pressed_keys() -> Array:
    return pressed_keys.duplicate()
```

### 3.2 鼠标事件

```gdscript
# 鼠标事件处理
class_name MouseEventHandler

extends Node

signal mouse_clicked(button: int, position: Vector2)
signal mouse_double_clicked(button: int, position: Vector2)
signal mouse_dragged(button: int, from: Vector2, to: Vector2)
signal mouse_scrolled(delta: Vector2)

var mouse_position: Vector2 = Vector2.ZERO
var drag_start: Vector2 = Vector2.ZERO
var is_dragging: bool = false
var drag_button: int = -1
var last_click_time: float = 0.0
var last_click_button: int = -1
var last_click_position: Vector2 = Vector2.ZERO
const DOUBLE_CLICK_INTERVAL = 0.3

func _input(event):
    if event is InputEventMouseButton:
        _handle_mouse_button(event)
    elif event is InputEventMouseMotion:
        _handle_mouse_motion(event)

func _handle_mouse_button(event: InputEventMouseButton):
    var button = event.button_index
    var position = event.position
    
    if event.pressed:
        # 检查双击
        var current_time = Time.get_ticks_msec() / 1000.0
        if button == last_click_button and \
           current_time - last_click_time < DOUBLE_CLICK_INTERVAL and \
           position.distance_to(last_click_position) < 10:
            mouse_double_clicked.emit(button, position)
        else:
            mouse_clicked.emit(button, position)
        
        # 开始拖拽
        is_dragging = true
        drag_start = position
        drag_button = button
        
        last_click_time = current_time
        last_click_button = button
        last_click_position = position
    else:
        # 结束拖拽
        if is_dragging and drag_button == button:
            var drag_end = position
            if drag_start.distance_to(drag_end) > 5:
                mouse_dragged.emit(button, drag_start, drag_end)
            is_dragging = false
            drag_button = -1

func _handle_mouse_motion(event: InputEventMouseMotion):
    mouse_position = event.position
    
    if event.relative.length() > 0:
        # 处理鼠标移动
        pass

func get_mouse_position() -> Vector2:
    return mouse_position

func is_mouse_dragging() -> bool:
    return is_dragging

func get_drag_start() -> Vector2:
    return drag_start
```

### 3.3 手柄事件

```gdscript
# 手柄事件处理
class_name GamepadEventHandler

extends Node

signal gamepad_connected(device: int)
signal gamepad_disconnected(device: int)
signal gamepad_button_pressed(device: int, button: int)
signal gamepad_button_released(device: int, button: int)
signal gamepad_axis_moved(device: int, axis: int, value: float)

var connected_devices: Array = []
var axis_deadzone: float = 0.1
var trigger_threshold: float = 0.5

func _ready():
    # 检测已连接的手柄
    for device in range(8):
        if Input.is_joy_known(device):
            _on_gamepad_connected(device)

func _input(event):
    if event is InputEventJoypadButton:
        _handle_gamepad_button(event)
    elif event is InputEventJoypadMotion:
        _handle_gamepad_motion(event)
    elif event is InputEventJoypadConnection:
        _handle_gamepad_connection(event)

func _handle_gamepad_button(event: InputEventJoypadButton):
    var device = event.device
    var button = event.button_index
    
    if event.pressed:
        gamepad_button_pressed.emit(device, button)
    else:
        gamepad_button_released.emit(device, button)

func _handle_gamepad_motion(event: InputEventJoypadMotion):
    var device = event.device
    var axis = event.axis
    var value = event.axis_value
    
    # 应用死区
    if abs(value) < axis_deadzone:
        value = 0.0
    
    gamepad_axis_moved.emit(device, axis, value)

func _handle_gamepad_connection(event: InputEventJoypadConnection):
    var device = event.device
    
    if event.connected:
        _on_gamepad_connected(device)
    else:
        _on_gamepad_disconnected(device)

func _on_gamepad_connected(device: int):
    if device not in connected_devices:
        connected_devices.append(device)
        gamepad_connected.emit(device)

func _on_gamepad_disconnected(device: int):
    connected_devices.erase(device)
    gamepad_disconnected.emit(device)

func get_connected_gamepads() -> Array:
    return connected_devices.duplicate()

func set_axis_deadzone(zone: float):
    axis_deadzone = zone

func get_axis_value(device: int, axis: int) -> float:
    var value = Input.get_joy_axis(device, axis)
    if abs(value) < axis_deadzone:
        return 0.0
    return value

func is_button_pressed(device: int, button: int) -> bool:
    return Input.is_joy_button_pressed(device, button)
```

---

## 4. 输入动作系统

### 4.1 基础输入动作

```gdscript
# 基础输入动作
class_name BasicInputActions

extends Node

signal action_pressed(action: String)
signal action_released(action: String)

var active_actions: Array = []

func _input(event):
    if event is InputEventAction:
        _handle_action_event(event)

func _handle_action_event(event: InputEventAction):
    var action = event.action
    
    if event.pressed:
        if action not in active_actions:
            active_actions.append(action)
        action_pressed.emit(action)
    else:
        active_actions.erase(action)
        action_released.emit(action)

func is_action_pressed(action: String) -> bool:
    return Input.is_action_pressed(action)

func is_action_just_pressed(action: String) -> bool:
    return Input.is_action_just_pressed(action)

func is_action_just_released(action: String) -> bool:
    return Input.is_action_just_released(action)

func get_action_strength(action: String) -> float:
    return Input.get_action_strength(action)

func get_active_actions() -> Array:
    return active_actions.duplicate()
```

### 4.2 输入动作管理器

```gdscript
# 输入动作管理器
class_name InputActionManager

extends Node

var action_bindings: Dictionary = {}
var action_callbacks: Dictionary = {}

func _ready():
    _setup_default_bindings()

func _setup_default_bindings():
    # 设置默认绑定
    action_bindings["move"] = ["move_forward", "move_backward", "move_left", "move_right"]
    action_bindings["combat"] = ["attack", "skill", "block"]
    action_bindings["ui"] = ["ui_accept", "ui_cancel", "ui_pause"]

func register_action(action_name: String, callback: Callable):
    # 注册动作回调
    if not action_callbacks.has(action_name):
        action_callbacks[action_name] = []
    action_callbacks[action_name].append(callback)

func unregister_action(action_name: String, callback: Callable):
    # 注销动作回调
    if action_callbacks.has(action_name):
        action_callbacks[action_name].erase(callback)

func _input(event):
    if event is InputEventAction:
        _trigger_action_callbacks(event.action, event.pressed)

func _trigger_action_callbacks(action: String, pressed: bool):
    if action_callbacks.has(action):
        for callback in action_callbacks[action]:
            if pressed:
                callback.call()

func get_action_group(group_name: String) -> Array:
    # 获取动作组
    return action_bindings.get(group_name, [])

func add_action_to_group(action: String, group: String):
    # 添加动作到组
    if not action_bindings.has(group):
        action_bindings[group] = []
    action_bindings[group].append(action)

func remove_action_from_group(action: String, group: String):
    # 从组移除动作
    if action_bindings.has(group):
        action_bindings[group].erase(action)
```

### 4.3 输入动作上下文

```gdscript
# 输入动作上下文
class_name InputActionContext

extends Node

var current_context: String = "default"
var context_stack: Array = []
var context_actions: Dictionary = {}

func _ready():
    # 设置默认上下文
    context_actions["default"] = ["move", "jump", "attack"]
    context_actions["ui"] = ["ui_accept", "ui_cancel", "ui_pause"]
    context_actions["dialog"] = ["ui_accept", "ui_cancel"]
    context_actions["menu"] = ["ui_accept", "ui_cancel", "ui_up", "ui_down"]

func set_context(context: String):
    # 设置上下文
    context_stack.append(current_context)
    current_context = context

func pop_context():
    # 弹出上下文
    if context_stack.size() > 0:
        current_context = context_stack.pop_back()

func get_current_context() -> String:
    return current_context

func is_action_available(action: String) -> bool:
    # 检查动作是否可用
    var actions = context_actions.get(current_context, [])
    return action in actions

func add_context_action(context: String, action: String):
    # 添加上下文动作
    if not context_actions.has(context):
        context_actions[context] = []
    context_actions[context].append(action)

func remove_context_action(context: String, action: String):
    # 移除上下文动作
    if context_actions.has(context):
        context_actions[context].erase(action)

func _input(event):
    if event is InputEventAction:
        if not is_action_available(event.action):
            # 阻止不可用的动作
            event.accepted = false
```

---

## 5. 输入系统优化

### 5.1 输入缓冲

```gdscript
# 输入缓冲
class_name InputBuffer

extends Node

@export var buffer_size: int = 10
@export var buffer_time_ms: int = 100

var input_buffer: Array = []

func _input(event):
    if event is InputEvent:
        _add_to_buffer(event)

func _add_to_buffer(event: InputEvent):
    var entry = {
        "event": event,
        "time": Time.get_ticks_msec(),
        "type": event.get_class()
    }
    
    input_buffer.append(entry)
    
    # 限制缓冲大小
    if input_buffer.size() > buffer_size:
        input_buffer.pop_front()
    
    # 清理过期输入
    _cleanup_buffer()

func _cleanup_buffer():
    var current_time = Time.get_ticks_msec()
    var cutoff = current_time - buffer_time_ms
    
    input_buffer = input_buffer.filter(func(entry): return entry.time > cutoff)

func get_recent_inputs(time_window_ms: int = 50) -> Array:
    # 获取最近的输入
    var current_time = Time.get_ticks_msec()
    var cutoff = current_time - time_window_ms
    
    return input_buffer.filter(func(entry): return entry.time > cutoff)

func get_last_input() -> Dictionary:
    # 获取最后输入
    if input_buffer.size() > 0:
        return input_buffer[-1]
    return {}

func clear_buffer():
    # 清空缓冲
    input_buffer.clear()
```

### 5.2 输入预测

```gdscript
# 输入预测
class_name InputPredictor

extends Node

var input_history: Array = []
var prediction_window_ms: int = 100

func _input(event):
    if event is InputEvent:
        _record_input(event)

func _record_input(event: InputEvent):
    input_history.append({
        "event": event,
        "time": Time.get_ticks_msec()
    })
    
    # 限制历史记录
    if input_history.size() > 60:
        input_history.pop_front()

func predict_next_input() -> Dictionary:
    # 预测下一个输入
    if input_history.size() < 2:
        return {}
    
    # 简单预测：基于最近的输入模式
    var recent = input_history.slice(-5)
    
    # 分析输入模式
    var pressed_actions = {}
    for entry in recent:
        if entry.event is InputEventAction and entry.event.pressed:
            var action = entry.event.action
            pressed_actions[action] = pressed_actions.get(action, 0) + 1
    
    # 返回最可能的动作
    var most_likely = ""
    var max_count = 0
    for action in pressed_actions:
        if pressed_actions[action] > max_count:
            max_count = pressed_actions[action]
            most_likely = action
    
    if most_likely != "":
        return {"action": most_likely, "confidence": float(max_count) / recent.size()}
    
    return {}

func get_input_pattern() -> Array:
    # 获取输入模式
    return input_history.duplicate()

func clear_history():
    input_history.clear()
```

### 5.3 输入灵敏度

```gdscript
# 输入灵敏度
class_name InputSensitivity

extends Node

@export var mouse_sensitivity: float = 1.0
@export var gamepad_sensitivity: float = 1.0
@export var axis_deadzone: float = 0.1

func _ready():
    load_sensitivity_settings()

func load_sensitivity_settings():
    # 加载灵敏度设置
    var config = ConfigFile.new()
    var err = config.load("user://input_sensitivity.ini")
    
    if err == OK:
        mouse_sensitivity = config.get_value("sensitivity", "mouse", 1.0)
        gamepad_sensitivity = config.get_value("sensitivity", "gamepad", 1.0)
        axis_deadzone = config.get_value("deadzone", "axis", 0.1)

func save_sensitivity_settings():
    # 保存灵敏度设置
    var config = ConfigFile.new()
    config.set_value("sensitivity", "mouse", mouse_sensitivity)
    config.set_value("sensitivity", "gamepad", gamepad_sensitivity)
    config.set_value("deadzone", "axis", axis_deadzone)
    config.save("user://input_sensitivity.ini")

func set_mouse_sensitivity(sensitivity: float):
    mouse_sensitivity = clamp(sensitivity, 0.1, 5.0)

func set_gamepad_sensitivity(sensitivity: float):
    gamepad_sensitivity = clamp(sensitivity, 0.1, 5.0)

func set_axis_deadzone(zone: float):
    axis_deadzone = clamp(zone, 0.0, 0.5)

func get_mouse_sensitivity() -> float:
    return mouse_sensitivity

func get_gamepad_sensitivity() -> float:
    return gamepad_sensitivity

func get_axis_deadzone() -> float:
    return axis_deadzone

func apply_to_axis_value(value: float) -> float:
    # 应用灵敏度到轴值
    if abs(value) < axis_deadzone:
        return 0.0
    
    # 应用死区
    var adjusted = (abs(value) - axis_deadzone) / (1.0 - axis_deadzone)
    adjusted = clamp(adjusted, 0.0, 1.0)
    
    # 应用灵敏度
    return sign(value) * adjusted * gamepad_sensitivity
```

---

## 6. 实践：完整输入系统

### 6.1 基础输入管理器

```gdscript
# 基础输入管理器
class_name BasicInputManager

extends Node

var keyboard_handler: KeyboardEventHandler
var mouse_handler: MouseEventHandler
var gamepad_handler: GamepadEventHandler
var action_manager: InputActionManager

func _ready():
    keyboard_handler = KeyboardEventHandler.new()
    add_child(keyboard_handler)
    
    mouse_handler = MouseEventHandler.new()
    add_child(mouse_handler)
    
    gamepad_handler = GamepadEventHandler.new()
    add_child(gamepad_handler)
    
    action_manager = InputActionManager.new()
    add_child(action_manager)

func _input(event):
    # 事件会自动传递给子节点

func is_action_pressed(action: String) -> bool:
    return Input.is_action_pressed(action)

func is_action_just_pressed(action: String) -> bool:
    return Input.is_action_just_pressed(action)

func get_mouse_position() -> Vector2:
    return mouse_handler.get_mouse_position()

func get_connected_gamepads() -> Array:
    return gamepad_handler.get_connected_gamepads()

func register_action(action: String, callback: Callable):
    action_manager.register_action(action, callback)
```

### 6.2 高级输入管理器

```gdscript
# 高级输入管理器
class_name AdvancedInputManager

extends BasicInputManager

var input_buffer: InputBuffer
var input_predictor: InputPredictor
var sensitivity: InputSensitivity
var context: InputActionContext

func _ready():
    super._ready()
    
    input_buffer = InputBuffer.new()
    add_child(input_buffer)
    
    input_predictor = InputPredictor.new()
    add_child(input_predictor)
    
    sensitivity = InputSensitivity.new()
    add_child(sensitivity)
    
    context = InputActionContext.new()
    add_child(context)

func _input(event):
    super._input(event)
    
    # 检查上下文
    if event is InputEventAction:
        if not context.is_action_available(event.action):
            event.accepted = false

func set_input_context(ctx: String):
    context.set_context(ctx)

func pop_input_context():
    context.pop_context()

func get_current_context() -> String:
    return context.get_current_context()

func is_action_available(action: String) -> bool:
    return context.is_action_available(action)

func get_recent_inputs() -> Array:
    return input_buffer.get_recent_inputs()

func predict_input() -> Dictionary:
    return input_predictor.predict_next_input()

func set_mouse_sensitivity(sensitivity: float):
    self.sensitivity.set_mouse_sensitivity(sensitivity)

func set_gamepad_sensitivity(sensitivity: float):
    self.sensitivity.set_gamepad_sensitivity(sensitivity)

func save_input_settings():
    sensitivity.save_sensitivity_settings()

func load_input_settings():
    sensitivity.load_sensitivity_settings()
```

### 6.3 完整输入系统

```gdscript
# 完整输入系统
class_name FullInputSystem

extends AdvancedInputManager

@export var enable_input_logging: bool = false
var input_log: Array = []

func _ready():
    super._ready()
    load_input_settings()

func _input(event):
    super._input(event)
    
    if enable_input_logging:
        _log_input(event)

func _log_input(event: InputEvent):
    input_log.append({
        "time": Time.get_ticks_msec(),
        "type": event.get_class(),
        "data": _serialize_event_data(event)
    })
    
    # 限制日志大小
    if input_log.size() > 1000:
        input_log.pop_front()

func _serialize_event_data(event: InputEvent) -> Dictionary:
    var data = {}
    
    if event is InputEventKey:
        data["keycode"] = event.keycode
        data["pressed"] = event.pressed
    elif event is InputEventMouseButton:
        data["button"] = event.button_index
        data["position"] = event.position
        data["pressed"] = event.pressed
    elif event is InputEventMouseMotion:
        data["position"] = event.position
        data["relative"] = event.relative
    elif event is InputEventAction:
        data["action"] = event.action
        data["pressed"] = event.pressed
    
    return data

func get_input_log() -> Array:
    return input_log.duplicate()

func clear_input_log():
    input_log.clear()

func export_input_log():
    # 导出输入日志
    var file = FileAccess.open("user://input_log.json", FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(input_log, "  "))
        file.close()

func get_input_stats() -> Dictionary:
    # 获取输入统计
    var stats = {
        "keyboard_events": 0,
        "mouse_events": 0,
        "gamepad_events": 0,
        "action_events": 0
    }
    
    for entry in input_log:
        match entry.type:
            "InputEventKey":
                stats.keyboard_events += 1
            "InputEventMouseButton", "InputEventMouseMotion":
                stats.mouse_events += 1
            "InputEventJoypadButton", "InputEventJoypadMotion":
                stats.gamepad_events += 1
            "InputEventAction":
                stats.action_events += 1
    
    return stats

func print_input_stats():
    var stats = get_input_stats()
    print("Input Statistics:")
    print("- Keyboard Events: ", stats.keyboard_events)
    print("- Mouse Events: ", stats.mouse_events)
    print("- Gamepad Events: ", stats.gamepad_events)
    print("- Action Events: ", stats.action_events)
```

---

## 📝 本章总结

### 核心要点

1. **InputMap 配置输入映射**，将硬件事件映射到动作
2. **InputEvent 处理各种输入**，键盘、鼠标、手柄、触摸
3. **输入动作系统抽象输入**，便于游戏逻辑处理
4. **输入上下文管理状态**，不同场景不同输入
5. **输入优化提升体验**，缓冲、预测、灵敏度调整

### 关键术语

| 术语 | 解释 |
|------|------|
| InputMap | 输入映射，硬件事件到动作的映射 |
| InputEvent | 输入事件，硬件事件的封装 |
| InputAction | 输入动作，抽象的输入命令 |
| Deadzone | 死区，忽略小幅度输入 |
| Sensitivity | 灵敏度，输入响应程度 |
| Context | 上下文，输入状态环境 |
| Buffer | 缓冲，存储历史输入 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Input](https://docs.godotengine.org/en/stable/tutorials/inputs/index.html)
- **源码位置**: `core/input/`
- **技术博客**: [Godot Input System Guide](https://godotengine.org/article/input-system-guide/)

---

## 📋 下一章预告

**第 54 篇：脚本系统**

- 脚本系统基础
- GDScript 语法
- 脚本生命周期
- 脚本优化

---

*写作时间：2026-03-20*  
*字数：约 13,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 21:00*