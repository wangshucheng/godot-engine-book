# 第 66 篇：编辑器扩展模板

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 65 章 编辑器自动化  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编辑器扩展模板为开发者提供了快速创建插件和扩展的基础结构。通过模板，开发者可以快速启动项目，避免重复创建基础文件。本章讲**插件脚手架与工程化模板**：目录怎么组织、文件怎么生成、模板本身怎么版本化与测试。

> ⚠️ **本文的「模板」≠ Godot 的 ScriptTemplate / ProjectTemplate**
>
> Godot 引擎本身有两套官方的「模板」机制：
> - **ScriptTemplate**：新建脚本时在「创建脚本」对话框里出现的代码片段模板，
>   存在编辑器的 `script_templates.cfg` 里；
> - **ProjectTemplate**：项目管理器里「从模板创建项目」用的项目骨架，
>   由 `ProjectManager` 从 `res://.godot/exported/...` 之外的模板目录读取。
>
> 它们都是**引擎功能**，不是插件体系的一部分。
> **本文讲的是自建的插件脚手架**：一组用脚本生成的目录与文件，
> 用来快速产出一个符合规范的 Godot 插件。两者名字相近但没有继承关系，
> 不要混淆。

---

## 🎯 学习目标

- 理解插件脚手架的分层结构
- 掌握用脚本生成插件目录与 `plugin.cfg`
- 掌握模板的版本管理与自检
- 清楚模板与 AssetLib 发布流程的分工

---

## 1. 编辑器扩展模板架构

### 1.1 模板结构

```
编辑器扩展模板结构:
┌─────────────────────────────────────────────────────────────┐
│                      编辑器扩展模板结构                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 核心模板（Core Template）：基本插件结构                 │
│  2. 工具模板（Tool Template）：工具类插件结构               │
│  3. 资源模板（Resource Template）：资源管理插件结构         │
│  4. 工作流模板（Workflow Template）：工作流插件结构         │
│  5. UI模板（UI Template）：UI扩展插件结构                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 模板组件

```gdscript
# 模板组件
@tool
class_name TemplateComponents

var core_template := {
    "name": "Core Template",
    "description": "Basic plugin structure",
    "files": [
        "plugin.gd",
        "plugin.cfg",
        "icon.svg",
        "README.md",
    ],
    "features": [
        "plugin initialization",
        "dock setup",
        "menu item",
        "settings",
    ],
}

var tool_template := {
    "name": "Tool Template",
    "description": "Tool plugin structure",
    "files": [
        "tool.gd",
        "plugin.cfg",
        "icon.svg",
        "README.md",
        "editor_script.gd",
    ],
    "features": [
        "editor script",
        "custom dock",
        "toolbar button",
        "hotkey",
    ],
}

var resource_template := {
    "name": "Resource Template",
    "description": "Resource management plugin structure",
    "files": [
        "resource_plugin.gd",
        "plugin.cfg",
        "icon.svg",
        "README.md",
        "editor_inspector_plugin.gd",
    ],
    "features": [
        "inspector plugin",
        "resource tools",
        "batch operations",
    ],
}

var workflow_template := {
    "name": "Workflow Template",
    "description": "Workflow plugin structure",
    "files": [
        "workflow_plugin.gd",
        "plugin.cfg",
        "icon.svg",
        "README.md",
        "workflow.gd",
    ],
    "features": [
        "workflow state machine",
        "task scheduler",
        "progress tracking",
    ],
}

var ui_template := {
    "name": "UI Template",
    "description": "UI extension plugin structure",
    "files": [
        "ui_plugin.gd",
        "plugin.cfg",
        "icon.svg",
        "README.md",
        "custom_control.gd",
    ],
    "features": [
        "custom control",
        "theme support",
        "input handling",
    ],
}

func get_template(template_name: String) -> Dictionary:
    return {
        "core": core_template,
        "tool": tool_template,
        "resource": resource_template,
        "workflow": workflow_template,
        "ui": ui_template,
    }.get(template_name, {})
```

### 1.3 模板接口

```gdscript
# 模板接口
@tool
class_name TemplateInterface

var templates: Dictionary = {}

func initialize() -> void:
    _load_templates()

func _load_templates() -> void:
    var components := TemplateComponents.new()
    templates = {
        "core": components.core_template,
        "tool": components.tool_template,
        "resource": components.resource_template,
        "workflow": components.workflow_template,
        "ui": components.ui_template,
    }

func get_template(template_name: String) -> Dictionary:
    return templates.get(template_name, {})

func get_all_templates() -> Dictionary:
    return templates

func get_template_names() -> Array:
    return templates.keys()

func get_template_features(template_name: String) -> Array:
    return get_template(template_name).get("features", [])

func get_template_files(template_name: String) -> Array:
    return get_template(template_name).get("files", [])
```

---

## 2. 模板创建

### 2.1 核心模板创建

```gdscript
# 核心模板创建
@tool
class_name CoreTemplateCreator

func create_core_template(template_path: String) -> bool:
    # 创建核心模板
    if not _create_directory(template_path):
        return false
    _create_plugin_file(template_path)
    _create_plugin_cfg_file(template_path)
    _create_readme_file(template_path)
    return true

func _create_directory(path: String) -> bool:
    # 创建目录（4.x 用 DirAccess 的静态方法，路径必须是绝对路径）
    var err := DirAccess.make_dir_recursive_absolute(path)
    if err != OK:
        push_error("无法创建目录 %s（错误码 %d）" % [path, err])
        return false
    return true

func _create_plugin_file(path: String) -> void:
    # 创建插件文件
    # ⚠️ 生成的插件脚本必须以 @tool 开头，否则在编辑器里不会被实例化
    var plugin_code := """
@tool
extends EditorPlugin

func _enter_tree():
    # 初始化插件
    pass

func _exit_tree():
    # 清理插件
    pass

func _handles(object):
    # 检查对象
    return false

func _edit(object):
    # 编辑对象
    pass

func _make_visible(visible):
    # 设置可见性
    pass
"""
    _write_text(path + "/plugin.gd", plugin_code)

func _create_plugin_cfg_file(path: String) -> void:
    # Godot 识别插件的唯一依据是 plugin.cfg（INI 格式）；
    # metadata.json 不是 Godot 的约定，编辑器不会读取它。
    # 缺少 plugin.cfg 时，「项目设置 → 插件」列表里根本不会出现该插件。
    # ⚠️ 4.3 只解析 [plugin] 段的 script/version/name/description/author，
    #    没有 [dependencies] 分支——不要写 [dependencies]，它不会有任何效果。
    var cfg := """[plugin]

name="MyPlugin"
description="A Godot plugin"
author="Your Name"
version="1.0.0"
script="plugin.gd"
"""
    _write_text(path + "/plugin.cfg", cfg)

func _create_readme_file(path: String) -> void:
    var readme := """
# MyPlugin

A Godot plugin.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

1. Copy the plugin folder to your Godot project's `res://addons/my_plugin/` directory
2. Enable the plugin in Project > Project Settings > Plugins

## Usage

1. Open the plugin dock
2. Use the plugin features

## License

MIT License
"""
    _write_text(path + "/README.md", readme)

func _write_text(path: String, content: String) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        push_error("无法写入：" + path)
        return
    file.store_string(content)
    file.close()
```

### 2.2 工具模板创建

```gdscript
# 工具模板创建
@tool
class_name ToolTemplateCreator

func create_tool_template(template_path: String) -> bool:
    _create_directory(template_path)
    _create_tool_file(template_path)
    _create_plugin_cfg_file(template_path)
    _create_readme_file(template_path)
    _create_editor_script_file(template_path)
    return true

func _create_tool_file(path: String) -> void:
    var tool_code := """
@tool
extends EditorPlugin

var dock: Control
var button: Button

func _enter_tree():
    _setup_dock()
    _setup_button()

func _exit_tree():
    _cleanup_dock()
    _cleanup_button()

func _setup_dock():
    dock = Control.new()
    dock.name = "MyToolDock"
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock():
    if dock:
        # 先从 Dock 摘掉，再释放；对已在场景树中的节点用 queue_free()
        remove_control_from_docks(dock)
        dock.queue_free()
        dock = null

func _setup_button():
    button = Button.new()
    button.text = "My Tool"
    button.pressed.connect(_on_button_pressed)
    add_control_to_container(CONTAINER_TOOLBAR, button)

func _cleanup_button():
    if button:
        # ⚠️ 没有 remove_control_from_containers()；
        #    正确 API 是 2 参的 remove_control_from_container(容器枚举, 控件)
        remove_control_from_container(CONTAINER_TOOLBAR, button)
        button.queue_free()
        button = null

func _on_button_pressed():
    pass

func _handles(object):
    return false

func _edit(object):
    pass

func _make_visible(visible):
    if dock:
        dock.visible = visible
"""
    _write_text(path + "/tool.gd", tool_code)

func _create_editor_script_file(path: String) -> void:
    # 编辑器脚本同样必须加 @tool
    var editor_script_code := """
@tool
extends EditorScript

func _run():
    # 编辑器脚本
    print("Running editor script")
"""
    _write_text(path + "/editor_script.gd", editor_script_code)
```

### 2.3 资源模板创建

```gdscript
# 资源模板创建
@tool
class_name ResourceTemplateCreator

func create_resource_template(template_path: String) -> bool:
    _create_directory(template_path)
    _create_resource_plugin_file(template_path)
    _create_plugin_cfg_file(template_path)
    _create_readme_file(template_path)
    _create_inspector_plugin_file(template_path)
    return true

func _create_resource_plugin_file(path: String) -> void:
    var resource_plugin_code := """
@tool
extends EditorPlugin

var dock: Control
var inspector_plugin: EditorInspectorPlugin

func _enter_tree():
    _setup_dock()
    _setup_inspector_plugin()

func _exit_tree():
    _cleanup_dock()
    _cleanup_inspector_plugin()

func _setup_dock():
    dock = Control.new()
    dock.name = "ResourceToolDock"
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock():
    if dock:
        remove_control_from_docks(dock)
        dock.queue_free()
        dock = null

func _setup_inspector_plugin():
    inspector_plugin = EditorInspectorPlugin.new()
    add_inspector_plugin(inspector_plugin)

func _cleanup_inspector_plugin():
    if inspector_plugin:
        remove_inspector_plugin(inspector_plugin)
        # EditorInspectorPlugin 继承 RefCounted，不需要 queue_free()，
        # 去掉引用后由引用计数自动回收
        inspector_plugin = null
"""
    _write_text(path + "/resource_plugin.gd", resource_plugin_code)

func _create_inspector_plugin_file(path: String) -> void:
    var inspector_plugin_code := """
@tool
extends EditorInspectorPlugin

func _can_handle(object):
    # 检查对象：这里换成你自己的资源类
    return object is Resource and object.get_class() == "MyResource"

func _parse_begin(object):
    # 开始解析
    var label = Label.new()
    label.text = "My Resource Inspector"
    add_custom_control(label)

func _parse_end(object):
    # 结束解析
    pass

func _parse_category(object, category):
    # 解析类别
    pass

func _parse_property(object, type, name, hint_type, hint_string, usage_flags, wide):
    # 解析属性
    return false
"""
    _write_text(path + "/editor_inspector_plugin.gd", inspector_plugin_code)
```

### 2.4 工作流模板创建

```gdscript
# 工作流模板创建
@tool
class_name WorkflowTemplateCreator

func create_workflow_template(template_path: String) -> bool:
    _create_directory(template_path)
    _create_workflow_plugin_file(template_path)
    _create_plugin_cfg_file(template_path)
    _create_readme_file(template_path)
    _create_workflow_file(template_path)
    return true

func _create_workflow_plugin_file(path: String) -> void:
    var workflow_plugin_code := """
@tool
extends EditorPlugin

var dock: Control
var workflow: Workflow

func _enter_tree():
    _setup_dock()
    _setup_workflow()

func _exit_tree():
    _cleanup_dock()
    _cleanup_workflow()

func _setup_dock():
    dock = Control.new()
    dock.name = "WorkflowDock"
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock():
    if dock:
        remove_control_from_docks(dock)
        dock.queue_free()
        dock = null

func _setup_workflow():
    workflow = Workflow.new()
    workflow.setup()

func _cleanup_workflow():
    if workflow:
        workflow.shutdown()
        # Workflow 继承 Node，释放要用 queue_free()
        workflow.queue_free()
        workflow = null
"""
    _write_text(path + "/workflow_plugin.gd", workflow_plugin_code)

func _create_workflow_file(path: String) -> void:
    var workflow_code := """
@tool
extends Node

var state_machine: StateMachine

func setup():
    state_machine = StateMachine.new()
    state_machine.setup()

func shutdown():
    if state_machine:
        state_machine.shutdown()

# ⚠️ GDScript 4.x 的内部类必须把 extends 写在 class 名的同一行：
#    class StateMachine extends RefCounted:
#    另起一行写 extends 是 3.x 的旧写法，4.x 解析不了。
class StateMachine extends RefCounted:

    var current_state: String = "idle"
    var states: Dictionary = {}

    func setup():
        pass

    func shutdown():
        pass

    func update():
        pass
"""
    _write_text(path + "/workflow.gd", workflow_code)
```

### 2.5 UI模板创建

```gdscript
# UI模板创建
@tool
class_name UITemplateCreator

func create_ui_template(template_path: String) -> bool:
    _create_directory(template_path)
    _create_ui_plugin_file(template_path)
    _create_plugin_cfg_file(template_path)
    _create_readme_file(template_path)
    _create_custom_control_file(template_path)
    return true

func _create_ui_plugin_file(path: String) -> void:
    var ui_plugin_code := """
@tool
extends EditorPlugin

var dock: Control
var custom_control: CustomControl

func _enter_tree():
    _setup_dock()
    _setup_custom_control()

func _exit_tree():
    _cleanup_dock()
    _cleanup_custom_control()

func _setup_dock():
    dock = Control.new()
    dock.name = "UICustomDock"
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _cleanup_dock():
    if dock:
        remove_control_from_docks(dock)
        dock.queue_free()
        dock = null

func _setup_custom_control():
    custom_control = CustomControl.new()
    dock.add_child(custom_control)

func _cleanup_custom_control():
    if custom_control:
        # 已在场景树中，用 queue_free()
        custom_control.queue_free()
        custom_control = null
"""
    _write_text(path + "/ui_plugin.gd", ui_plugin_code)

func _create_custom_control_file(path: String) -> void:
    var custom_control_code := """
@tool
extends Control

func _ready():
    _setup_ui()

func _setup_ui():
    var label = Label.new()
    label.text = "Custom Control"
    add_child(label)
"""
    _write_text(path + "/custom_control.gd", custom_control_code)
```

---

## 3. 模板分发

> **卷内边界**：插件**打包成 zip 并发布到 AssetLib** 的硬性规则
> （zip 根目录必须直接含 `addons/<插件名>/plugin.cfg`、图标与截图规格、
> 版本号必须与 `plugin.cfg` 一致、审核要点）属于**第 58 篇 §4.4**。
> 本节只讲「模板自身的分发」：把一份脚手架复制到另一个项目里。

### 3.1 模板打包

```gdscript
# 模板打包
@tool
class_name TemplatePackager

func package_template(template_path: String, output_path: String) -> bool:
    # 打包模板：导出成一个 JSON 清单 + 文件内容
    var template_archive := {
        "files": _get_template_files(template_path),
        "metadata": _get_template_metadata(template_path),
    }

    var file := FileAccess.open(output_path, FileAccess.WRITE)
    if file == null:
        push_error("无法写入：" + output_path)
        return false
    file.store_string(JSON.stringify(template_archive, "  "))
    file.close()
    return true

func _get_template_files(template_path: String) -> Array:
    var files: Array = []
    var dir := DirAccess.open(template_path)
    if dir == null:
        return files
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir():
            files.append(file_name)
        file_name = dir.get_next()
    dir.list_dir_end()
    return files

func _get_template_metadata(template_path: String) -> Dictionary:
    # 获取模板元数据
    # ⚠️ plugin.cfg 是 INI 格式，用 JSON.parse() 读它一定失败，必须用 ConfigFile
    var cfg := ConfigFile.new()
    if cfg.load(template_path + "/plugin.cfg") != OK:
        return {}
    return {
        "name": cfg.get_value("plugin", "name", ""),
        "version": cfg.get_value("plugin", "version", "0.0.0"),
        "description": cfg.get_value("plugin", "description", ""),
        "author": cfg.get_value("plugin", "author", ""),
    }
```

### 3.2 模板安装

```gdscript
# 模板安装
@tool
class_name TemplateInstaller

func install_template(template_path: String, destination_path: String) -> bool:
    # 安装模板
    if not DirAccess.dir_exists_absolute(destination_path):
        DirAccess.make_dir_recursive_absolute(destination_path)

    var source_dir := DirAccess.open(template_path)
    if source_dir == null:
        push_error("无法读取模板目录：" + template_path)
        return false

    var ok := true
    source_dir.list_dir_begin()
    var file_name := source_dir.get_next()
    while file_name != "":
        if not source_dir.current_is_dir():
            if not _copy_file(template_path + "/" + file_name, destination_path + "/" + file_name):
                ok = false
        file_name = source_dir.get_next()
    source_dir.list_dir_end()
    return ok

func _copy_file(source_path: String, dest_path: String) -> bool:
    var source_file := FileAccess.open(source_path, FileAccess.READ)
    if source_file == null:
        return false
    var content := source_file.get_buffer(source_file.get_length())
    source_file.close()

    var dest_file := FileAccess.open(dest_path, FileAccess.WRITE)
    if dest_file == null:
        return false
    dest_file.store_buffer(content)
    dest_file.close()
    return true
```

### 3.3 模板版本检查

```gdscript
# 模板版本检查
@tool
class_name TemplateUpdater

func check_for_updates(template_name: String, remote_version: String) -> Dictionary:
    # 检查更新
    var installed_version := _get_installed_version(template_name)
    if _compare_versions(remote_version, installed_version) > 0:
        return {
            "available": true,
            "latest_version": remote_version,
            "installed_version": installed_version,
        }
    return {
        "available": false,
        "latest_version": remote_version,
        "installed_version": installed_version,
    }

func _get_installed_version(template_name: String) -> String:
    # 获取已安装版本：plugin.cfg 是 INI 格式，用 ConfigFile 读
    var cfg := ConfigFile.new()
    if cfg.load("res://addons/%s/plugin.cfg" % template_name) != OK:
        return "0.0.0"
    return cfg.get_value("plugin", "version", "0.0.0")

func _compare_versions(a: String, b: String) -> int:
    # ⚠️ 版本号不能直接用 > 比较（那是字符串比较，"10.0.0" < "9.0.0"）
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

---

## 4. 模板维护

### 4.1 版本管理

```gdscript
# 版本管理
@tool
class_name TemplateVersionManagement

func bump_version(current_version: String, type: String) -> String:
    var parts := current_version.split(".")
    if parts.size() < 3:
        return current_version
    var major := int(parts[0])
    var minor := int(parts[1])
    var patch := int(parts[2])

    match type:
        "major":
            major += 1
            minor = 0
            patch = 0
        "minor":
            minor += 1
            patch = 0
        "patch":
            patch += 1
        _:
            return current_version

    return "%d.%d.%d" % [major, minor, patch]

func validate_version(version: String) -> bool:
    var parts := version.split(".")
    if parts.size() != 3:
        return false
    for part in parts:
        if not part.is_valid_int():
            return false
    return true

func compare_versions(version1: String, version2: String) -> int:
    # 比较版本：返回 -1 / 0 / 1
    var parts1 := version1.split(".")
    var parts2 := version2.split(".")
    for i in range(min(parts1.size(), parts2.size())):
        var num1 := int(parts1[i])
        var num2 := int(parts2[i])
        if num1 < num2:
            return -1
        elif num1 > num2:
            return 1
    return 0
```

### 4.2 模板测试

```gdscript
# 模板测试
@tool
class_name TemplateTesting

func test_template(template_path: String) -> Dictionary:
    var test_results := {
        "name": "",
        "version": "",
        "files_exist": true,
        "files_valid": true,
        "metadata_valid": true,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "errors": [],
    }

    test_results["total_tests"] += 1
    if _check_files_exist(template_path):
        test_results["passed_tests"] += 1
    else:
        test_results["failed_tests"] += 1
        test_results["files_exist"] = false
        test_results["errors"].append("缺少必需文件")

    test_results["total_tests"] += 1
    if _check_files_valid(template_path):
        test_results["passed_tests"] += 1
    else:
        test_results["failed_tests"] += 1
        test_results["files_valid"] = false
        test_results["errors"].append("文件内容不合法")

    test_results["total_tests"] += 1
    if _check_metadata_valid(template_path):
        test_results["passed_tests"] += 1
    else:
        test_results["failed_tests"] += 1
        test_results["metadata_valid"] = false
        test_results["errors"].append("元数据不合法")

    var metadata := _get_metadata(template_path)
    test_results["name"] = metadata.get("name", "Unknown")
    test_results["version"] = metadata.get("version", "0.0.0")

    return test_results

func _check_files_exist(template_path: String) -> bool:
    var required_files := ["plugin.cfg", "plugin.gd", "README.md"]
    for file in required_files:
        if not FileAccess.file_exists(template_path + "/" + file):
            return false
    return true

func _check_files_valid(template_path: String) -> bool:
    # 检查文件有效性：面向编辑器的脚本必须以 @tool 开头
    var script_path := template_path + "/plugin.gd"
    if not FileAccess.file_exists(script_path):
        return false
    var file := FileAccess.open(script_path, FileAccess.READ)
    if file == null:
        return false
    var content := file.get_as_text()
    file.close()
    return content.strip_edges().begins_with("@tool")

func _check_metadata_valid(template_path: String) -> bool:
    var metadata := _get_metadata(template_path)
    return metadata.has("name") and metadata.has("version") and not metadata["version"].is_empty()

func _get_metadata(template_path: String) -> Dictionary:
    # 获取元数据：plugin.cfg 是 INI 格式，用 ConfigFile 读
    var cfg := ConfigFile.new()
    if cfg.load(template_path + "/plugin.cfg") != OK:
        return {}
    return {
        "name": cfg.get_value("plugin", "name", ""),
        "version": cfg.get_value("plugin", "version", "0.0.0"),
        "description": cfg.get_value("plugin", "description", ""),
        "author": cfg.get_value("plugin", "author", ""),
    }
```

### 4.3 模板文档

```gdscript
# 模板文档
@tool
class_name TemplateDocumentation

func generate_documentation(template_path: String) -> Dictionary:
    var documentation := {
        "name": "",
        "version": "",
        "description": "",
        "installation": "",
        "usage": "",
        "features": [],
        "changelog": "",
        "license": "",
    }

    var metadata := _get_metadata(template_path)
    documentation["name"] = metadata.get("name", "Unknown")
    documentation["version"] = metadata.get("version", "0.0.0")
    documentation["description"] = metadata.get("description", "")

    var readme := _get_readme(template_path)
    documentation["installation"] = _extract_section(readme, "Installation")
    documentation["usage"] = _extract_section(readme, "Usage")
    documentation["changelog"] = _extract_section(readme, "Changelog")

    documentation["features"] = _extract_features(template_path)
    return documentation

func _get_metadata(template_path: String) -> Dictionary:
    # 获取元数据：plugin.cfg 是 INI 格式，用 ConfigFile 读
    var cfg := ConfigFile.new()
    if cfg.load(template_path + "/plugin.cfg") != OK:
        return {}
    return {
        "name": cfg.get_value("plugin", "name", ""),
        "version": cfg.get_value("plugin", "version", "0.0.0"),
        "description": cfg.get_value("plugin", "description", ""),
        "author": cfg.get_value("plugin", "author", ""),
    }

func _get_readme(template_path: String) -> String:
    var file := FileAccess.open(template_path + "/README.md", FileAccess.READ)
    if file == null:
        return ""
    var content := file.get_as_text()
    file.close()
    return content

func _extract_section(text: String, section_name: String) -> String:
    var start_marker := "## " + section_name
    var start_pos := text.find(start_marker)
    if start_pos == -1:
        return ""
    var end_pos := text.find("\n## ", start_pos + 1)
    if end_pos == -1:
        end_pos = text.length()
    return text.substr(start_pos, end_pos - start_pos)

func _extract_features(template_path: String) -> Array:
    # 提取特性：读模板清单里的 features 列表
    var components := TemplateComponents.new()
    var features: Array = []
    for key in components.get_template("core").get("features", []):
        features.append(key)
    return features
```

---

## 5. 实践：完整模板系统

### 5.1 模板协调器

```gdscript
# 模板协调器
@tool
class_name TemplateCoordinator

var creator: TemplateInterface
var packager: TemplatePackager
var installer: TemplateInstaller
var updater: TemplateUpdater
var tester: TemplateTesting
var documentation: TemplateDocumentation

func initialize() -> void:
    creator = TemplateInterface.new()
    creator.initialize()
    packager = TemplatePackager.new()
    installer = TemplateInstaller.new()
    updater = TemplateUpdater.new()
    tester = TemplateTesting.new()
    documentation = TemplateDocumentation.new()

func create_template(template_name: String, template_type: String) -> Dictionary:
    # 创建模板
    var template_path := "res://addons/%s" % template_name
    var ok := false

    match template_type:
        "core":
            ok = CoreTemplateCreator.new().create_core_template(template_path)
        "tool":
            ok = ToolTemplateCreator.new().create_tool_template(template_path)
        "resource":
            ok = ResourceTemplateCreator.new().create_resource_template(template_path)
        "workflow":
            ok = WorkflowTemplateCreator.new().create_workflow_template(template_path)
        "ui":
            ok = UITemplateCreator.new().create_ui_template(template_path)

    return {
        "status": "success" if ok else "failure",
        "path": template_path,
    }

func package_template(template_name: String) -> Dictionary:
    var template_path := "res://addons/%s" % template_name
    var output_path := "user://templates/%s.json" % template_name
    var success := packager.package_template(template_path, output_path)
    return {
        "status": "success" if success else "failure",
        "output_path": output_path,
    }

func install_template(template_name: String, destination_name: String) -> Dictionary:
    var template_path := "res://addons/%s" % template_name
    var destination_path := "res://addons/%s" % destination_name
    var success := installer.install_template(template_path, destination_path)
    return {
        "status": "success" if success else "failure",
        "destination_path": destination_path,
    }

func check_updates(template_name: String, remote_version: String) -> Dictionary:
    return updater.check_for_updates(template_name, remote_version)

func test_template(template_name: String) -> Dictionary:
    return tester.test_template("res://addons/%s" % template_name)

func generate_documentation(template_name: String) -> Dictionary:
    return documentation.generate_documentation("res://addons/%s" % template_name)
```

### 5.2 模板浏览器

```gdscript
# 模板浏览器
@tool
class_name TemplateBrowser
extends Control

var coordinator: TemplateCoordinator
var template_list: Tree

func _ready() -> void:
    coordinator = TemplateCoordinator.new()
    coordinator.initialize()
    _setup_ui()

func _setup_ui() -> void:
    var vbox := VBoxContainer.new()
    add_child(vbox)

    var title := Label.new()
    title.text = "Template Browser"
    vbox.add_child(title)

    template_list = Tree.new()
    template_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    vbox.add_child(template_list)

    var buttons_hbox := HBoxContainer.new()
    vbox.add_child(buttons_hbox)

    var create_btn := Button.new()
    create_btn.text = "Create"
    buttons_hbox.add_child(create_btn)

    var install_btn := Button.new()
    install_btn.text = "Install"
    buttons_hbox.add_child(install_btn)

    var test_btn := Button.new()
    test_btn.text = "Test"
    buttons_hbox.add_child(test_btn)

    _populate_template_list()

func _populate_template_list() -> void:
    template_list.clear()
    var root := template_list.create_item()
    root.set_text(0, "Templates")

    for template in coordinator.creator.get_template_names():
        var item := template_list.create_item(root)
        item.set_text(0, template)
        item.set_meta("type", "template")
```

### 5.3 模板安装器插件

```gdscript
# 模板安装器插件
@tool
class_name TemplateInstallerPlugin
extends EditorPlugin

var coordinator: TemplateCoordinator
var browser: TemplateBrowser

func _enter_tree() -> void:
    coordinator = TemplateCoordinator.new()
    coordinator.initialize()

    browser = TemplateBrowser.new()
    add_control_to_dock(EditorPlugin.DOCK_SLOT_RIGHT_UL, browser)

func _exit_tree() -> void:
    if browser:
        # 先从 Dock 摘掉再释放
        remove_control_from_docks(browser)
        browser.queue_free()
        browser = null

func create_new_template(template_type: String) -> void:
    coordinator.create_template("My" + template_type.capitalize() + "Template", template_type)

func install_existing_template(template_name: String, destination_name: String) -> void:
    coordinator.install_template(template_name, destination_name)

func generate_template_report(template_name: String) -> Dictionary:
    var test_result := coordinator.test_template(template_name)
    var doc := coordinator.generate_documentation(template_name)
    return {
        "test_result": test_result,
        "documentation": doc,
        "generated_at": Time.get_unix_time(),
    }
```

---

## 📝 本章总结

### 核心要点

1. **本文的模板 ≠ 引擎的 ScriptTemplate / ProjectTemplate**，
   它是自建的插件脚手架目录结构
2. **生成的插件脚本一律以 `@tool` 开头**，否则在编辑器里不会被实例化
3. **`plugin.cfg` 是 INI 格式**，读它只能用 `ConfigFile`；
   4.3 只认 `[plugin]` 段，**没有 `[dependencies]` 分支**
4. **内部类的 `extends` 必须写在同一行**：`class StateMachine extends RefCounted:`
5. **对已在场景树中的节点用 `queue_free()`**；
   工具栏按钮的移除用 2 参的 `remove_control_from_container(容器, 控件)`
6. **版本号不能用字符串比较**，要用按段比较的数字比较

### 关键术语

| 术语 | 解释 |
|---|---|
| TemplateComponents | 模板组件，定义各模板的清单 |
| TemplateInterface | 模板接口，统一管理模板清单 |
| CoreTemplateCreator | 核心模板创建器 |
| ToolTemplateCreator | 工具模板创建器 |
| ResourceTemplateCreator | 资源模板创建器 |
| WorkflowTemplateCreator | 工作流模板创建器 |
| UITemplateCreator | UI 模板创建器 |
| TemplatePackager | 模板打包器，导出 JSON 清单 |
| TemplateInstaller | 模板安装器，复制到目标项目 |
| TemplateUpdater | 模板版本检查器 |
| TemplateVersionManagement | 模板版本号管理 |
| TemplateTesting | 模板自检 |
| TemplateDocumentation | 模板文档生成 |
| TemplateCoordinator | 模板协调器，串联上述组件 |
| TemplateBrowser | 模板浏览器面板 |
| TemplateInstallerPlugin | 把模板浏览器挂到 Dock 的插件 |

---

## 🔗 延伸阅读

- **官方文档 · 创建和使用插件**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/index.html>
- **官方文档 · 脚本模板**: <https://docs.godotengine.org/en/stable/tutorials/editor/script_templates.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_configfile.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_diraccess.html>
- **源码位置**: `editor/editor_node.cpp`（解析 `plugin.cfg`）

---

## 📋 下一章预告

**第 67 篇：编辑器扩展最佳实践**

- `@tool` 的真实行为与编辑器内脚本生命周期
- 编辑器内撤销 / 重做
- 插件设置的正规存储位

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 65 篇：编辑器自动化](/articles/65-editor-automation.md)
**下一篇**: [第 67 篇：编辑器扩展最佳实践](/articles/67-editor-extension-best-practices.md)

---

*写作时间：2026-03-20*  
*字数：约 900 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
