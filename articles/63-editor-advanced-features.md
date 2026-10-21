# 第 63 篇：编辑器高级功能

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 61 章 高级编辑器扩展  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

本章讲**广度**：Godot 编辑器里有哪些地方是可以挂钩子的、可以用脚本驱动的。

> **卷内边界**：本章只讲「编辑器里有什么能改的」。
> 扩展点的**官方 API 签名**在第 61 篇；「编辑器怎么快」在第 64 篇；
> 「怎么批量干活、CI 怎么跑」在第 65 篇；「怎么写才不出错」在第 67 篇；
> 「插件怎么打包发布」在第 58 篇。

---

## 🎯 学习目标

- 搞清 EditorScript 到底是什么、什么时候用
- 能在编辑器内跑一个可交互的调试控制台
- 列出编辑器里所有可挂钩的事件源
- 知道哪些「看起来像扩展点」其实不是

---

## 1. 编辑器脚本

### 1.1 EditorScript 的定位

```gdscript
# 编辑器脚本
# ⚠️ 必须加 @tool：4.3 的 EditorScript.xml 明确写着
#    "Extending scripts need to have tool mode enabled."
@tool
class_name EditorScriptAdvanced
extends EditorScript

func _run() -> void:
    # 唯一入口：由脚本编辑器的「文件 → 运行」触发（Ctrl+Shift+X）
    # EditorScript 不是 Node，没有 _ready()/_process() 回调，
    # 也就没有「进入场景树」这回事。
    var scene := EditorInterface.get_edited_scene_root()
    if scene == null:
        push_warning("当前没有正在编辑的场景")
        return

    var selection := EditorInterface.get_selection().get_selected_nodes()
    _process_selection(selection)

func _process_selection(selection: Array) -> void:
    for node in selection:
        if node is MeshInstance3D:
            _process_mesh(node)

func _process_mesh(mesh_instance: MeshInstance3D) -> void:
    var mesh := mesh_instance.mesh
    if mesh:
        _optimize_mesh(mesh)

func _optimize_mesh(mesh: Mesh) -> void:
    # 这里可以添加具体的优化代码
    pass
```

> **机制说明**：
> - 官方定义是 `<class name="EditorScript" inherits="RefCounted">`——
>   它**直接继承 `RefCounted`**，与 `Script` / `Resource` 没有继承关系，
>   也不是 `Node`。
> - 因为不是 `Node`，所以**没有** `_ready()` / `_process()` / `_enter_tree()`。
>   把它们写在 `EditorScript` 里是死代码，永远不会被调用。
> - `EditorScript` 是 `RefCounted`：没有任何引用时它会被立刻释放，
>   这会让异步操作（`await`）在执行到一半时失去 `self`。
>   异步任务里请自己持有一份引用。
> - 唯一入口是 `_run()`。`EditorScript.new()._run()` **不被支持**：
>   `_run()` 是由编辑器在脚本编辑器里手动触发的。
> - `EditorScript` 自带 `get_scene()`（等价于
>   `EditorInterface.get_edited_scene_root()`）与 `add_root_node(node)`
>   （把节点加到当前场景根上，效果等价于编辑器操作，可被撤销）。

```gdscript
# 用 add_root_node() 往当前场景里加节点
@tool
extends EditorScript

func _run() -> void:
    var root := get_scene()
    if root == null:
        push_warning("当前没有正在编辑的场景")
        return

    var node := Node3D.new()
    node.name = "SpawnedByEditorScript"
    add_root_node(node)     # 与编辑器操作等效，可被撤销
    print("已添加到场景：", root.name)

func report_selection() -> void:
    # 读取编辑器状态
    var selected := EditorInterface.get_selection().get_selected_nodes()
    print("当前选中 %d 个节点" % selected.size())
```

### 1.2 什么时候用 EditorScript，什么时候用 EditorPlugin

| 场景 | 选谁 |
|------|------|
| 「运行一次」的批处理动作（改一批资源、生成代码、验证场景） | **EditorScript** |
| 需要常驻、要有 UI 面板、要响应编辑器事件 | **EditorPlugin** |
| 需要在导出时介入 | **EditorPlugin** + `EditorExportPlugin` |
| 需要在导入时介入 | **EditorPlugin** + `EditorImportPlugin` |

> **机制说明**：两者都跑在**编辑器进程**里，都必须加 `@tool`。
> EditorScript 是一次性的（跑完就结束），EditorPlugin 是常驻的
> （`_enter_tree()` / `_exit_tree()` 之间的整个生命周期）。

---

## 2. 编辑器内调试控制台

### 2.1 控制台控件

```gdscript
# 编辑器内调试控制台
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name DebugConsole
extends PanelContainer

var history: Array = []
var history_index: int = 0

var _output: TextEdit
var _input: LineEdit

func _ready() -> void:
    _setup_ui()

func _setup_ui() -> void:
    var vbox := VBoxContainer.new()
    add_child(vbox)

    # 标题：TextEdit 没有 set_title()，用 Label 顶替
    var title := Label.new()
    title.text = "Debug Console"
    vbox.add_child(title)

    _output = TextEdit.new()
    _output.editable = false
    _output.size_flags_vertical = Control.SIZE_EXPAND_FILL
    vbox.add_child(_output)

    _input = LineEdit.new()
    _input.placeholder_text = "输入 help / clear / inspect"
    _input.text_submitted.connect(_on_input_submitted)
    vbox.add_child(_input)

    _print_line("调试控制台已就绪。输入 help 查看命令。")

func _on_input_submitted(text: String) -> void:
    _input.clear()
    var command := text.strip_edges()
    if command.is_empty():
        return
    history.append(command)
    history_index = history.size()
    _print_line("> " + command)
    _run_command(command)

func _print_line(text: String) -> void:
    # TextEdit 没有 append_text()（那是 RichTextLabel 的方法）；
    # 往只读终端里追加一行，直接累加 text 属性即可。
    _output.text += text + "\n"
```

### 2.2 命令分发与接入插件

```gdscript
# 命令分发 + 接入插件
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name DebugConsolePlugin
extends EditorPlugin

var _dock: DebugConsole

func _enter_tree() -> void:
    _setup_dock()

func _exit_tree() -> void:
    _cleanup_dock()

func _setup_dock() -> void:
    _dock = DebugConsole.new()
    _dock.name = "AdvancedDebugDock"
    # 底部面板不是 Dock 槽位：4.3 的 DockSlot 枚举只有 8 个槽位 + DOCK_SLOT_MAX，
    # 没有 DOCK_SLOT_BOTTOM_DRAG 这种值。
    # 底部面板要用 add_control_to_bottom_panel(控件, "标题")，
    # 它返回新增的 Button 引用，由插件自己负责显示/隐藏。
    add_control_to_bottom_panel(_dock, "调试控制台")

func _cleanup_dock() -> void:
    if _dock:
        # 先从底部面板摘掉，再释放；对已在场景树中的节点用 queue_free()
        remove_control_from_bottom_panel(_dock)
        _dock.queue_free()
        _dock = null

func _run_command(command: String) -> void:
    match command:
        "help":
            _dock._print_line("可用命令：help / clear / inspect")
        "clear":
            _dock._output.clear()
        "inspect":
            _inspect_selection()
        _:
            _dock._print_line("未知命令：" + command)

func _inspect_selection() -> void:
    var selection := EditorInterface.get_selection().get_selected_nodes()
    for node in selection:
        _dock._print_line("Inspecting: " + str(node.name))
```

> **机制说明**：`EditorPlugin.DockSlot` 枚举在 4.3 里只有
> `DOCK_SLOT_LEFT_UL` / `LEFT_BL` / `LEFT_UR` / `LEFT_BR` /
> `RIGHT_UL` / `RIGHT_BL` / `RIGHT_UR` / `RIGHT_BR` 八个槽位
> （外加一个表示枚举大小的 `DOCK_SLOT_MAX`）。
> 底部面板属于另一套机制：`add_control_to_bottom_panel(control, title, shortcut = null)`
> 返回一个 `Button`（就是你切换面板用的那个按钮），
> 对应清理函数是 `remove_control_from_bottom_panel(control)`。

---

## 3. 编辑器扩展点总览

### 3.1 可挂钩的事件源

编辑器**没有**统一的「扩展点注册表」。所谓扩展点，其实是下面这些具体的
信号、虚函数与单例方法的组合：

```gdscript
# 编辑器扩展点一览
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name EditorExtensions
extends EditorPlugin

func get_extension_points() -> Dictionary:
    # 编辑器真实可用的事件源（没有统一的 "extension point" 机制）
    return {
        "scene_changed": "编辑的场景切换（EditorPlugin 信号）",
        "scene_closed": "场景被关闭（EditorPlugin 信号）",
        "scene_saved": "场景已保存（EditorPlugin 信号）",
        "resource_saved": "资源保存后（EditorPlugin 信号）",
        "main_screen_changed": "主屏幕切换（EditorPlugin 信号）",
        "selection_changed": "编辑器选中项变化（EditorSelection 信号）",
        "node_added": "节点加入场景树（SceneTree 信号）",
        "node_removed": "节点离开场景树（SceneTree 信号）",
        "_export_begin/_export_end": "导出前后（EditorExportPlugin 虚函数，不是信号）",
    }

func connect_extension_point(extension_point: String, callback: Callable) -> void:
    match extension_point:
        "scene_changed":
            scene_changed.connect(callback)
        "scene_saved":
            scene_saved.connect(callback)
        "resource_saved":
            resource_saved.connect(callback)
        "main_screen_changed":
            main_screen_changed.connect(callback)
        "selection_changed":
            # EditorInterface.get_selection() 返回 EditorSelection，
            # 它有且只有一个信号：selection_changed
            EditorInterface.get_selection().selection_changed.connect(callback)
        "node_added":
            get_tree().node_added.connect(callback)
        "node_removed":
            get_tree().node_removed.connect(callback)
        _:
            # 「场景开始运行 / 停止运行」没有对应信号
            push_warning("该事件请轮询 EditorInterface.is_playing_scene()")
            push_warning("导出阶段请在 EditorExportPlugin 中实现 _export_begin()/_export_end()")

func disconnect_extension_point(extension_point: String, callback: Callable) -> void:
    match extension_point:
        "scene_changed":
            scene_changed.disconnect(callback)
        "scene_saved":
            scene_saved.disconnect(callback)
        "resource_saved":
            resource_saved.disconnect(callback)
        "main_screen_changed":
            main_screen_changed.disconnect(callback)
        "selection_changed":
            EditorInterface.get_selection().selection_changed.disconnect(callback)
        "node_added":
            get_tree().node_added.disconnect(callback)
        "node_removed":
            get_tree().node_removed.disconnect(callback)
        _:
            pass
```

> **机制说明**：
> - `EditorInterface` 在 4.3 与 master 上都**没有**
>   `get_edited_scene_root_changed()` 这个方法，`EditorInterface` 也没有任何
>   `<signals>` 段。「当前编辑的场景变了」用
>   `EditorPlugin` 的 **`scene_changed` 信号**；
>   「用户换了个选中项」用
>   `EditorInterface.get_selection().selection_changed`。
> - 「场景开始运行 / 停止运行」**没有信号**，只能轮询
>   `EditorInterface.is_playing_scene()`。
> - 4.2 起 `EditorInterface` 已经是**全局单例**，
>   直接写 `EditorInterface.get_edited_scene_root()` 即可，
>   不需要（也不应该在非 EditorPlugin 类里调用）`get_editor_interface()`——
>   那个方法只存在于 `EditorPlugin` 与 `EditorScript` 上，且已标记为 deprecated。

### 3.2 扩展的启用与管理

```gdscript
# 扩展的启用与管理
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name ExtensionManagement
extends EditorPlugin

func _enter_tree() -> void:
    # 插件的启用状态记录在项目设置的 editor_plugins/enabled 中，
    # 由编辑器扫描 addons/ 后自行实例化；脚本不能手工「注册插件实例」。
    print("当前已启用扩展：", get_all_extensions())

func get_all_extensions() -> PackedStringArray:
    # 已启用的扩展列表本身就是一串 plugin.cfg 路径
    return ProjectSettings.get_setting("editor_plugins/enabled", PackedStringArray())

func is_extension_enabled(plugin_dir_name: String) -> bool:
    # 官方 API：参数是插件目录名
    return EditorInterface.is_plugin_enabled(plugin_dir_name)

func set_extension_enabled(plugin_dir_name: String, enabled: bool) -> void:
    # 官方 API：4.2+ 推荐用它而不是直接改 editor_plugins/enabled
    EditorInterface.set_plugin_enabled(plugin_dir_name, enabled)

func get_plugin_version(plugin_dir_name: String) -> String:
    # 版本号从 plugin.cfg 读（EditorPlugin 上只有 get_plugin_version()，
    # 它读的也是 plugin.cfg 的 version 字段）
    var cfg := ConfigFile.new()
    if cfg.load("res://addons/%s/plugin.cfg" % plugin_dir_name) != OK:
        return "0.0.0"
    return cfg.get_value("plugin", "version", "0.0.0")
```

### 3.3 看起来像扩展点、其实不是的东西

| 虚构 API | 实际情况 |
|---|---|
| `EditorInterface.get_edited_scene_root_changed()` | 不存在。用 `EditorPlugin.scene_changed` 信号 |
| `EditorInterface.register_plugin()` / `unregister_plugin()` / `get_plugins()` | 都不存在。插件由编辑器扫描 `addons/` 后自行实例化 |
| `EditorInterface.get_editor_main_viewport()` | 不存在。只有 `get_editor_viewport_2d()` / `get_editor_viewport_3d()` / `get_editor_main_screen()`（后者返回 `VBoxContainer`，**不是** Viewport） |
| `EditorExtension`（所谓「编辑器扩展基类」） | 虚构类，不存在 |
| `EditorResourceImporter.new()` | 不存在。导入器是 `EditorImportPlugin` |
| `EditorExportPlatform.export_project()` | 不存在。`EditorExportPlatform` 是抽象基类，不能实例化 |
| `EditorPlugin.remove_control_from_containers()` | 不存在。只有 2 参的 `remove_control_from_container(container, control)` |
| `PerformanceProfiler` | 不存在。引擎提供的是 `Performance.get_monitor()` 系列 |

---

## 4. 本篇的边界：原章节的去向

本篇聚焦「编辑器里有什么能改的」。原版中越界的章节已按卷内职责切分到别处：

| 原章节 | 归属 | 说明 |
|---|---|---|
| 1.3 自定义编辑器（Dock 挂载） | **第 61 篇 §2** | 扩展点 API 与官方签名在 61 篇 |
| 3.1 性能优化 / 3.2 响应优化 / 3.3 UI 优化 | **第 64 篇** | 整节与 64 篇同题，已交由 64 篇独占 |
| 4.1 代码规范 / 4.2 性能优化 / 4.3 安全最佳实践 | **第 67 篇** | 规范类内容统一以 67 篇为准 |
| 5. 实践：完整编辑器系统 | **第 64 / 67 篇** | 性能仪表板归 64 篇，规范清单归 67 篇 |

> 场景树的「清理未使用节点」这类具体做法，参见**第 64 篇 §2.1 场景树优化**；
> 本篇不重复。

---

## 📝 本章总结

### 核心要点

1. **EditorScript 直接继承 `RefCounted`**，唯一入口是 `_run()`，
   没有 `_ready()` / `_process()`，必须加 `@tool`
2. **调试控制台**用 `PanelContainer` + `TextEdit` + `LineEdit` 实现；
   底部面板要走 `add_control_to_bottom_panel()`，不是 Dock 槽位
3. **扩展点总览**：场景/资源/主屏幕变化是 `EditorPlugin` 的信号，
   选中变化是 `EditorSelection.selection_changed`，
   节点增删是 `SceneTree` 的信号
4. **`EditorInterface` 是全局单例**（4.2+），
   在非 EditorPlugin/EditorScript 的类里不要调用 `get_editor_interface()`
5. **场景运行/停止没有信号**，只能轮询 `EditorInterface.is_playing_scene()`

### 关键术语

| 术语 | 解释 |
|---|---|
| EditorScript | 编辑器脚本，继承 `RefCounted`，一次性执行 |
| EditorPlugin | 编辑器插件，继承 `Node`，常驻并响应编辑器事件 |
| EditorSelection | 编辑器选中项管理器，信号 `selection_changed` |
| EditorInterface | 编辑器界面单例，4.2+ 起为全局单例 |
| DebugConsole | 本篇的调试控制台控件 |

---

## 🔗 延伸阅读

- **官方文档 · EditorScript**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/scripting_the_editor.html>
- **官方文档 · 插件总览**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/index.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorscript.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorplugin.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorselection.html>
- **源码位置**: `editor/editor_script.cpp`, `editor/plugins/editor_plugin.cpp`

---

## 📋 下一章预告

**第 64 篇：编辑器性能调优**

- 编辑器性能指标怎么读
- 场景树与资源加载的热点定位
- 监控工具与报告生成

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 61 篇：高级编辑器扩展](/articles/61-advanced-editor-extensions.md)
**下一篇**: [第 64 篇：编辑器性能调优](/articles/64-editor-performance-tuning.md)

---

*写作时间：2026-03-20*  
*字数：约 1,300 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
