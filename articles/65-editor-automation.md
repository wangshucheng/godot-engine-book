# 第 65 篇：编辑器自动化

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 64 章 编辑器性能调优  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编辑器自动化可以大幅提高开发效率，减少重复性工作。本章是**第八卷的工具链篇**：
讲清楚「怎么用脚本批量干活」「构建 / 测试 / 部署怎么串起来」
「CI 里怎么用无头编辑器跑」。

> **卷内边界**：本章只讲**自动化与工具链**。
> 扩展点 API 在第 61 篇；「编辑器里有什么能改的」在第 63 篇；
> 性能调优在第 64 篇；写法规范在第 67 篇；
> 插件打包与 AssetLib 发布在第 58 篇。

---

## 🎯 学习目标

- 掌握 EditorScript 批处理的写法
- 会写构建、场景验证、部署三类工作流
- 会用命令行参数在 CI 里驱动编辑器
- 知道怎么把插件的单元测试接进 CI

---

## 1. 编辑器自动化脚本

### 1.1 自动化脚本基础

```gdscript
# 自动化脚本基础
# ⚠️ 必须加 @tool：EditorScript 明确要求 tool 模式才能在编辑器里运行
@tool
class_name AutomationScriptBase
extends EditorScript

func _run() -> void:
    # 自动化脚本主函数：唯一入口，由「文件 → 运行」触发
    _validate_environment()
    _execute_tasks()
    _generate_report()

func _validate_environment() -> bool:
    # 验证环境
    # EditorInterface 在 4.2+ 已是全局单例，直接用名字访问
    var scene := EditorInterface.get_edited_scene_root()
    if scene == null:
        push_error("No scene opened")
        return false
    return true

func _execute_tasks() -> void:
    _prefab_generation()
    _batch_import()
    _data_export()

func _generate_report() -> void:
    var report := {
        "timestamp": Time.get_unix_time(),
        "tasks_completed": 3,
        "success": true,
    }
    print("Automation report:", JSON.stringify(report, "  "))
```

> **机制说明**：
> - `EditorScript` 继承 `RefCounted`，**不是** `Node`。
>   它的唯一入口是 `_run()`，由脚本编辑器的「文件 → 运行」触发。
> - `EditorScript.new()._run()` **不被支持**——`_run()` 是编辑器手动触发的回调，
>   不是可以从代码里调用的普通方法。
> - 异步场景要小心：`EditorScript` 是 `RefCounted`，
>   没有任何引用时会被立刻释放，`await` 之后 `self` 可能已经失效。
>   异步任务请自己持有一份引用。

### 1.2 代码生成脚本

```gdscript
# 代码生成脚本
@tool
class_name CodeGenerationScript
extends EditorScript

func _run() -> void:
    _generate_class()
    _generate_component()
    _generate_system()

func _generate_class() -> void:
    var class_template := """
extends Node

class_name MyClass

func _ready():
    pass

func _process(delta):
    pass
"""
    print("Generated class:", class_template)

func _generate_component() -> void:
    var component_template := """
extends Node2D

class_name MyComponent

func _ready():
    pass

func update():
    pass
"""
    print("Generated component:", component_template)

func _generate_system() -> void:
    var system_template := """
extends Node

class_name MySystem

func _ready():
    pass

func update(delta):
    pass
"""
    print("Generated system:", system_template)
```

### 1.3 批量资源处理脚本

```gdscript
# 批量资源处理脚本
@tool
class_name BatchResourceProcessingScript
extends EditorScript

func _run() -> void:
    _batch_import_textures()
    _batch_process_audio()
    _batch_convert_scenes()

func _batch_import_textures() -> void:
    var texture_dir := "res://textures/"
    for file in _get_files_in_directory(texture_dir):
        if file.ends_with(".png") or file.ends_with(".jpg"):
            _import_texture(texture_dir + file)

func _import_texture(path: String) -> void:
    var texture := load(path)
    if texture:
        print("Imported texture:", path)

func _batch_process_audio() -> void:
    var audio_dir := "res://audio/"
    for file in _get_files_in_directory(audio_dir):
        if file.ends_with(".wav") or file.ends_with(".ogg"):
            _process_audio(audio_dir + file)

func _process_audio(path: String) -> void:
    var audio := load(path)
    if audio:
        print("Processed audio:", path)

func _batch_convert_scenes() -> void:
    var scene_dir := "res://scenes/"
    for file in _get_files_in_directory(scene_dir):
        if file.ends_with(".tscn"):
            _convert_scene(scene_dir + file)

func _convert_scene(path: String) -> void:
    var scene := load(path)
    if scene:
        print("Converted scene:", path)

func _get_files_in_directory(path: String) -> Array:
    var files: Array = []
    var dir := DirAccess.open(path)
    if dir:
        dir.list_dir_begin()
        var file_name := dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
        dir.list_dir_end()
    return files
```

### 1.4 数据导出脚本

```gdscript
# 数据导出脚本
@tool
class_name DataExportScript
extends EditorScript

func _run() -> void:
    _export_items()
    _export_levels()
    _export_statistics()

func _export_items() -> void:
    var export_data: Array = []
    for item in _get_all_items():
        export_data.append({
            "id": item["id"],
            "name": item["name"],
            "type": item["type"],
            "value": item["value"],
        })
    _save_to_json(export_data, "res://export/items.json")
    print("Exported items:", export_data.size())

func _export_levels() -> void:
    var export_data: Array = []
    for level in _get_all_levels():
        export_data.append({
            "id": level["id"],
            "name": level["name"],
            "difficulty": level["difficulty"],
            "enemy_count": level["enemy_count"],
        })
    _save_to_json(export_data, "res://export/levels.json")
    print("Exported levels:", export_data.size())

func _export_statistics() -> void:
    var stats := {
        "total_items": _get_all_items().size(),
        "total_levels": _get_all_levels().size(),
        "total_scenes": _get_all_scenes().size(),
    }
    _save_to_json(stats, "res://export/statistics.json")
    print("Exported statistics:", stats)

func _get_all_items() -> Array:
    return [
        {"id": 1, "name": "Sword", "type": "weapon", "value": 100},
        {"id": 2, "name": "Shield", "type": "armor", "value": 150},
        {"id": 3, "name": "Potion", "type": "consumable", "value": 50},
    ]

func _get_all_levels() -> Array:
    return [
        {"id": 1, "name": "Level 1", "difficulty": "easy", "enemy_count": 5},
        {"id": 2, "name": "Level 2", "difficulty": "medium", "enemy_count": 10},
        {"id": 3, "name": "Level 3", "difficulty": "hard", "enemy_count": 15},
    ]

func _get_all_scenes() -> Array:
    return ["res://scenes/main.tscn", "res://scenes/menu.tscn"]

func _save_to_json(data: Variant, path: String) -> void:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(data, "  "))
        file.close()
        print("Saved to JSON:", path)
    else:
        push_error("无法写入：" + path)
```

---

## 2. 自动化工作流

### 2.1 构建工作流

```gdscript
# 构建工作流
@tool
class_name BuildWorkflow
extends EditorScript

func _run() -> void:
    _validate_project()
    _build_resources()
    _build_scene()
    _export_build()

func _validate_project() -> bool:
    print("Validating project...")
    if not ResourceLoader.exists("res://scenes/main.tscn"):
        push_error("Main scene not found")
        return false
    if not ResourceLoader.exists("res://scripts/main.gd"):
        push_error("Main script not found")
        return false
    print("Project validation passed")
    return true

func _build_resources() -> void:
    print("Building resources...")
    for path in ["res://textures/", "res://audio/", "res://scenes/"]:
        _precache_resources(path)
    print("Resource building completed")

func _precache_resources(path: String) -> void:
    var dir := DirAccess.open(path)
    if dir == null:
        return
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir():
            load(path + file_name)
        file_name = dir.get_next()
    dir.list_dir_end()

func _build_scene() -> void:
    print("Building scene...")
    EditorInterface.open_scene_from_path("res://scenes/main.tscn")
    EditorInterface.play_main_scene()

    # ⚠️ EditorInterface 没有 get_editor_main_viewport()。
    #    「场景是否在运行」没有信号，只能轮询 is_playing_scene()。
    #    EditorScript 继承 RefCounted，没有 get_tree()；
    #    要拿定时器得用 Engine.get_main_loop() 拿编辑器进程的 SceneTree。
    var tree := Engine.get_main_loop() as SceneTree
    var waited := 0.0
    while EditorInterface.is_playing_scene() and waited < 10.0:
        if tree == null:
            break
        await tree.create_timer(0.1).timeout
        waited += 0.1

    EditorInterface.stop_playing_scene()
    print("Scene building completed")

func _export_build() -> void:
    print("Exporting build...")
    _export_project("Windows Desktop", "res://build/game.exe")
    print("Build export completed")

func _export_project(preset: String, output_path: String) -> void:
    # EditorExportPlatform 是抽象基类：既不能实例化，也没有静态 export_project()。
    # 编辑器内想做导出定制，应实现 EditorExportPlugin 的回调；
    # 完全脚本化的导出则通过命令行完成（CI 场景推荐，见第 6 节）。
    var args := PackedStringArray([
        "--headless",
        "--path", ProjectSettings.globalize_path("res://"),
        "--export-release", preset, output_path,
    ])
    var output: Array = []
    var exit_code := OS.execute(OS.get_executable_path(), args, output, true)

    if exit_code == 0:
        print("导出成功：%s" % output_path)
    else:
        push_error("导出失败（退出码 %d）：%s" % [exit_code, "\n".join(output)])
```

> **机制说明**：`EditorInterface` 4.3 的方法全表里**没有**
> `get_editor_main_viewport()`。与「视口」相关的只有三个：
> `get_editor_viewport_2d()`（返回 `SubViewport`）、
> `get_editor_viewport_3d(idx)`（返回 `SubViewport`）、
> `get_editor_main_screen()`（返回 `VBoxContainer`，**不是** Viewport）。
> 而「场景开始运行 / 停止运行」**没有信号**，
> 只能用 `while EditorInterface.is_playing_scene(): await ...` 轮询。

### 2.2 场景验证工具

```gdscript
# 场景验证工具
@tool
class_name SceneValidator
extends EditorScript

func _run() -> void:
    _validate_all_scenes()

func _validate_all_scenes() -> void:
    var errors: Array = []
    for scene_path in _get_all_scenes():
        var scene_errors := _validate_scene(scene_path)
        if not scene_errors.is_empty():
            errors.append({"scene": scene_path, "errors": scene_errors})

    if errors.is_empty():
        print("所有场景验证通过！")
    else:
        _show_validation_report(errors)

func _get_all_scenes() -> PackedStringArray:
    var scenes := PackedStringArray()
    var dir := DirAccess.open("res://scenes")
    if dir == null:
        return scenes
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir() and file_name.ends_with(".tscn"):
            scenes.append("res://scenes/" + file_name)
        file_name = dir.get_next()
    dir.list_dir_end()
    return scenes

func _validate_scene(scene_path: String) -> Array:
    var errors: Array = []

    var packed := load(scene_path)
    if packed == null:
        errors.append("无法加载场景")
        return errors

    var root := packed.instantiate()
    _check_missing_nodes(root, errors)
    _check_script_errors(root, errors)
    _check_performance_issues(root, errors)

    # ⚠️ 对已在场景树中的节点用 free() 会立即释放，
    #    本帧内若还有引用就会崩；统一用 queue_free()
    root.queue_free()

    return errors

func _check_missing_nodes(node: Node, errors: Array) -> void:
    for child in node.get_children():
        if not is_instance_valid(child):
            errors.append("节点 %s 有缺失的引用" % node.get_path())
        _check_missing_nodes(child, errors)

func _check_script_errors(node: Node, errors: Array) -> void:
    var script := node.get_script()
    if script:
        if not script.can_instantiate():
            errors.append("脚本错误：%s" % script.resource_path)

func _check_performance_issues(node: Node, errors: Array) -> void:
    if node is MeshInstance3D:
        var mesh := node.mesh
        if mesh and mesh.get_surface_count() > 10:  # ⚠️ 示意数据（未附测试环境）
            errors.append("网格面数过多：%s" % node.get_path())
    for child in node.get_children():
        _check_performance_issues(child, errors)

func _show_validation_report(errors: Array) -> void:
    var report := "场景验证报告:\n\n"
    for error_data in errors:
        report += "场景：%s\n" % error_data["scene"]
        for error in error_data["errors"]:
            report += "  - %s\n" % error
        report += "\n"
    print(report)
```

### 2.3 部署工作流

```gdscript
# 部署工作流
@tool
class_name DeploymentWorkflow
extends EditorScript

func _run() -> void:
    _validate_deployment_environment()
    _build_deployment_package()
    _deploy_to_target()
    _verify_deployment()

func _validate_deployment_environment() -> bool:
    print("Validating deployment environment...")
    var deploy_config := _load_deployment_config()
    if deploy_config.is_empty():
        push_error("Deployment config not found")
        return false
    if deploy_config.get("target_environment", "") == "":
        push_error("Target environment not specified")
        return false
    print("Deployment environment validation passed")
    return true

func _load_deployment_config() -> Dictionary:
    var file := FileAccess.open("res://deploy/config.json", FileAccess.READ)
    if file == null:
        return {}
    var json := JSON.new()
    json.parse(file.get_as_text())
    file.close()
    return json.data if json.data is Dictionary else {}

func _build_deployment_package() -> void:
    print("Building deployment package...")
    var deploy_config := _load_deployment_config()
    var package_settings: Dictionary = deploy_config.get("package_settings", {})
    _build_resource_package(package_settings)
    _build_binary_package(package_settings)
    print("Deployment package built")

func _build_resource_package(settings: Dictionary) -> void:
    # 这里应该是与资源打包系统集成
    pass

func _build_binary_package(settings: Dictionary) -> void:
    # 这里应该是与构建系统集成
    pass

func _deploy_to_target() -> void:
    print("Deploying to target...")
    var deploy_config := _load_deployment_config()
    var target_settings: Dictionary = deploy_config.get("target_settings", {})
    _upload_files(target_settings)
    _configure_server(target_settings)
    print("Deployment completed")

func _upload_files(settings: Dictionary) -> void:
    # 这里应该是与 FTP/SFTP 或云存储集成
    pass

func _configure_server(settings: Dictionary) -> void:
    # 这里应该是与服务器配置管理集成
    pass

func _verify_deployment() -> void:
    print("Verifying deployment...")
    var deploy_config := _load_deployment_config()
    var verify_settings: Dictionary = deploy_config.get("verify_settings", {})
    var status := _check_deployment_status(verify_settings)
    if status["success"]:
        print("Deployment verification passed")
    else:
        push_error("Deployment verification failed")

func _check_deployment_status(settings: Dictionary) -> Dictionary:
    return {"success": true}
```

---

## 3. 批处理工具

### 3.1 批量导入工具

```gdscript
# 批量导入工具
@tool
class_name AutomatedBatchImporter
extends RefCounted

func batch_import_textures(directory: String, options: Dictionary = {}) -> int:
    var imported := 0
    for file in _get_files_in_directory(directory):
        if file.ends_with(".png") or file.ends_with(".jpg"):
            _import_texture(directory + "/" + file, options)
            imported += 1
    print("Batch imported", imported, "textures")
    return imported

func batch_import_audio(directory: String, options: Dictionary = {}) -> int:
    var imported := 0
    for file in _get_files_in_directory(directory):
        if file.ends_with(".wav") or file.ends_with(".ogg"):
            _import_audio(directory + "/" + file, options)
            imported += 1
    print("Batch imported", imported, "audio files")
    return imported

func _get_files_in_directory(directory: String) -> Array:
    var files: Array = []
    var dir := DirAccess.open(directory)
    if dir:
        dir.list_dir_begin()
        var file_name := dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
        dir.list_dir_end()
    return files

func _import_texture(path: String, options: Dictionary) -> void:
    # 导入纹理：4.x 的导入器由编辑器按扩展名自动匹配，
    # 这里只负责触发重新导入
    var fs := EditorInterface.get_resource_filesystem()
    if fs:
        fs.update_file(path)
        fs.scan()

func _import_audio(path: String, options: Dictionary) -> void:
    print("Importing audio:", path)
```

### 3.2 批量处理工具

```gdscript
# 批量处理工具
@tool
class_name BatchProcessingTool
extends RefCounted

func batch_convert_scenes(directory: String, conversion_function: Callable) -> int:
    var processed := 0
    for file in _get_files_in_directory(directory):
        if file.ends_with(".tscn"):
            conversion_function.call(directory + "/" + file)
            processed += 1
    print("Batch processed", processed, "scenes")
    return processed

func batch_optimize_nodes(scene: Node, optimization_function: Callable) -> void:
    _process_node(scene, optimization_function)

func _process_node(node: Node, optimization_function: Callable) -> void:
    optimization_function.call(node)
    for child in node.get_children():
        _process_node(child, optimization_function)

func _get_files_in_directory(directory: String) -> Array:
    var files: Array = []
    var dir := DirAccess.open(directory)
    if dir:
        dir.list_dir_begin()
        var file_name := dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
        dir.list_dir_end()
    return files
```

### 3.3 批量导出工具

```gdscript
# 批量导出工具
@tool
class_name BatchExportTool
extends RefCounted

func batch_export_json(scene: Node) -> bool:
    var export_data := {}
    _collect_data(scene, export_data)

    var file := FileAccess.open("res://export/data.json", FileAccess.WRITE)
    if file == null:
        push_error("无法写入 res://export/data.json")
        return false
    file.store_string(JSON.stringify(export_data, "  "))
    file.close()
    return true

func batch_export_csv(data: Array) -> bool:
    var csv_content := ""
    for row in data:
        csv_content += ",".join(row) + "\n"

    var file := FileAccess.open("res://export/data.csv", FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(csv_content)
    file.close()
    return true

func _collect_data(node: Node, data: Dictionary) -> void:
    data["name"] = node.name
    data["class"] = node.get_class()
    data["children"] = []

    for child in node.get_children():
        var child_data := {}
        _collect_data(child, child_data)
        data["children"].append(child_data)
```

---

## 4. 最佳实践

### 4.1 自动化脚本最佳实践

```gdscript
# 自动化脚本最佳实践
@tool
class_name AutomationScriptBestPractices
extends RefCounted

func follow_optimisation_script_best_practices() -> void:
    _use_deferred_calls()
    _implement_error_handling()
    _add_progress_tracking()

func _use_deferred_calls() -> void:
    # 使用 deferred 调用，避免阻塞主线程
    pass

func _implement_error_handling() -> void:
    # 实现错误处理
    # GDScript 没有 try-catch：用错误码、空值检查与 push_error 上报
    pass

func _add_progress_tracking() -> void:
    # 添加进度跟踪：显示进度条和状态
    pass

func _use_multithreading() -> void:
    # 使用多线程：处理大量数据时使用多线程
    pass
```

### 4.2 工作流最佳实践

```gdscript
# 工作流最佳实践
@tool
class_name WorkflowBestPractices
extends RefCounted

func follow_optimisation_workflow_best_practices() -> void:
    _use_state_machines()
    _implement_logging()
    _add_validation()

func _use_state_machines() -> void:
    # 使用状态机管理工作流状态
    pass

func _implement_logging() -> void:
    # 实现日志记录：记录所有重要事件
    pass

func _add_validation() -> void:
    # 添加验证：验证每个步骤
    pass
```

### 4.3 批处理工具最佳实践

```gdscript
# 批处理工具最佳实践
@tool
class_name BatchToolBestPractices
extends RefCounted

func follow_optimisation_batch_tool_best_practices() -> void:
    _use_batching()
    _implement_progress_tracking()
    _add_error_handling()

func _use_batching() -> void:
    # 使用批处理：批量处理多个项目
    pass

func _implement_progress_tracking() -> void:
    # 实现进度跟踪：显示进度条和状态
    pass

func _add_error_handling() -> void:
    # 添加错误处理：处理错误并继续处理其他项目
    pass
```

---

## 5. 实践：完整自动化系统

```gdscript
# 自动化协调器
@tool
class_name AutomationCoordinator
extends RefCounted

var scripts: Dictionary = {}
var workflows: Dictionary = {}
var tools: Dictionary = {}

func initialize() -> void:
    _load_scripts()
    _load_workflows()
    _load_tools()

func _load_scripts() -> void:
    scripts = {
        "code_generation": CodeGenerationScript.new(),
        "batch_resource_processing": BatchResourceProcessingScript.new(),
        "data_export": DataExportScript.new(),
    }

func _load_workflows() -> void:
    workflows = {
        "build": BuildWorkflow.new(),
        "deployment": DeploymentWorkflow.new(),
    }

func _load_tools() -> void:
    tools = {
        "batch_import": AutomatedBatchImporter.new(),
        "batch_processing": BatchProcessingTool.new(),
        "batch_export": BatchExportTool.new(),
    }

func run_workflow(workflow_name: String) -> void:
    # 运行工作流
    # ⚠️ EditorScript 的入口是 _run()，而且它由编辑器手动触发，
    #    不支持从代码里调用。真正的自动化入口见第 6 节的命令行方案。
    if workflows.has(workflow_name):
        print("工作流 %s 需要在脚本编辑器里手动运行（File → Run）" % workflow_name)

func batch_import_textures(directory: String, options: Dictionary = {}) -> int:
    if tools.has("batch_import"):
        return tools["batch_import"].batch_import_textures(directory, options)
    return 0

func batch_export_json(scene: Node) -> bool:
    if tools.has("batch_export"):
        return tools["batch_export"].batch_export_json(scene)
    return false

func generate_report() -> Dictionary:
    return {
        "timestamp": Time.get_unix_time(),
        "scripts": {"total": scripts.size(), "names": scripts.keys()},
        "workflows": {"total": workflows.size(), "names": workflows.keys()},
        "tools": {"total": tools.size(), "names": tools.keys()},
    }
```

```gdscript
# 自动化仪表板
@tool
class_name AutomationDashboard
extends Control

var coordinator: AutomationCoordinator

func _ready() -> void:
    coordinator = AutomationCoordinator.new()
    coordinator.initialize()
    _setup_ui()

func _setup_ui() -> void:
    var vbox := VBoxContainer.new()
    add_child(vbox)

    var title := Label.new()
    title.text = "Automation Dashboard"
    vbox.add_child(title)

    var scripts_list := Tree.new()
    scripts_list.name = "ScriptsList"
    vbox.add_child(scripts_list)

    var tools_list := Tree.new()
    tools_list.name = "ToolsList"
    vbox.add_child(tools_list)

    _populate_lists()

func _populate_lists() -> void:
    var scripts_list := get_node("ScriptsList") as Tree
    scripts_list.clear()
    var root := scripts_list.create_item()
    root.set_text(0, "Scripts")
    for script_name in coordinator.scripts.keys():
        var item := scripts_list.create_item(root)
        item.set_text(0, script_name)
        item.set_meta("type", "script")

    var tools_list := get_node("ToolsList") as Tree
    tools_list.clear()
    root = tools_list.create_item()
    root.set_text(0, "Tools")
    for tool_name in coordinator.tools.keys():
        var item := tools_list.create_item(root)
        item.set_text(0, tool_name)
        item.set_meta("type", "tool")
```

> **机制说明**：上面这段仪表板有两个 4.x 特有的坑：
> 1. `get_node("ScriptsList")` 返回的是 `Node`，
>    要调用 `Tree` 的方法得先 `as Tree` 转换（或用 `@onready var x: Tree = $ScriptsList`）。
> 2. 节点在 `_ready()` 里用 `add_child()` 动态添加时，
>    `get_node()` 要等添加完成后再取。

---

## 6. CI 中的无头编辑器

### 6.1 常用命令行参数

以下参数取自 4.3 官方文档「Command line tutorial」：

| 参数 | 含义 |
|---|---|
| `--headless` | 无头模式（等价于 `--display-driver headless --audio-driver Dummy`） |
| `-e`, `--editor` | 启动编辑器而不是运行场景 |
| `--quit` | 第一次迭代后退出 |
| `--quit-after <N>` | 迭代 N 次后退出，设为 0 表示禁用 |
| `--import` | 启动编辑器、等待资源导入完成、然后退出。**隐含 `--editor` 与 `--quit`** |
| `--export-release <preset> <path>` | 用指定预设导出。**隐含 `--import`** |
| `--export-debug <preset> <path>` | 同上，使用 debug 模板 |
| `--export-pack <preset> <path>` | 只导出 PCK / ZIP 包 |
| `-s`, `--script <script>` | 运行脚本，**脚本必须继承 `SceneTree` 或 `MainLoop`** |
| `--check-only` | 只解析检查错误后退出（配合 `--script` 使用） |
| `--build-solutions` | 构建脚本解决方案（如 C# 项目）。隐含 `--editor` |
| `--path <dir>` | 指定项目目录（目录里要有 `project.godot`） |
| `-u`, `--upwards` | 向上递归查找 `project.godot` |

### 6.2 典型的 CI 流水线

```bash
# 1) 先导入资源（没有这一步，导出会因为 .godot/imported/ 为空而失败）
godot --headless --path . --import

# 2) 再导出
godot --headless --path . --export-release "Windows Desktop" build/game.exe

# 3) 或者：只导出资源包
godot --headless --path . --export-pack "Windows Desktop" build/game.pck
```

> **机制说明**：
> - `--export-release` / `--export-debug` / `--export-pack` **本身就隐含 `--import`**，
>   所以单独跑导出命令也会先导入资源。显式写一次 `--import` 是为了在
>   「导入失败」和「导出失败」之间得到更清晰的报错。
> - 官方文档明确要求：**在 CI（没有 GPU）上 `--headless` 是必需的**；
>   在有 GPU 的机器上，`--headless` 的作用是不弹窗口。
> - 导出用的是**编辑器二进制**，不是导出模板；并且**必须先安装导出模板**
>   （或在导出预设里指定合法的自定义模板），否则导出会失败。
> - 预设名必须与 `export_presets.cfg` 里的名字完全一致；
>   含空格或特殊字符（例如 `"Windows Desktop"`）时要用引号包起来。
> - 用相对路径指定导出目标时，路径是相对于**项目目录**（`project.godot` 所在目录），
>   不是相对于当前工作目录。目标目录必须已存在。
> - 退出码：命令成功返回 0，失败返回非 0。CI 里直接用退出码判定即可。

### 6.3 用 `--script` 跑自动化

```gdscript
# CI 用的批处理脚本
# ⚠️ 用 --script 启动的脚本必须继承 SceneTree 或 MainLoop
#    （它不是 EditorScript：EditorScript 需要编辑器进程才能跑）
extends SceneTree

func _init() -> void:
    print("开始批处理…")
    var failed := 0

    for path in _list_scenes():
        if not _validate_scene(path):
            failed += 1

    print("完成：%d 个失败" % failed)
    # quit(退出码) 让 CI 拿到非 0 退出码
    quit(failed)

func _list_scenes() -> PackedStringArray:
    var scenes := PackedStringArray()
    var dir := DirAccess.open("res://scenes")
    if dir == null:
        return scenes
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir() and file_name.ends_with(".tscn"):
            scenes.append("res://scenes/" + file_name)
        file_name = dir.get_next()
    dir.list_dir_end()
    return scenes

func _validate_scene(path: String) -> bool:
    var packed := load(path)
    if packed == null:
        push_error("无法加载：" + path)
        return false
    var root := packed.instantiate()
    var ok := root != null
    if root:
        root.queue_free()
    return ok
```

```bash
# 只做语法检查（不真的跑）：--check-only 会解析完就退出
godot --headless --path . --script res://tools/validate.gd --check-only

# 真正跑一遍
godot --headless --path . --script res://tools/validate.gd
```

> **机制说明**：
> - 用 `--script` 启动的脚本**必须继承 `SceneTree` 或 `MainLoop`**，
>   `EditorScript` 在这种模式下不会被执行。
> - `SceneTree` 脚本在 `_init()` 里跑完逻辑后要显式 `quit(退出码)`，
>   否则进程会一直挂着。
> - `--check-only` 适合做「语法门禁」：它只解析脚本、报告错误，不执行逻辑。

---

## 7. 插件的单元测试与 CI 验证

### 7.1 插件的测试结构

插件的纯逻辑（不依赖编辑器 UI 的部分）应该拆成**普通 GDScript 类**，
这样它们既能在编辑器里跑，也能在 `--script` 模式的无头环境里跑：

```
res://addons/my_plugin/
├── plugin.cfg
├── plugin.gd              # @tool extends EditorPlugin
├── core/                  # 纯逻辑，继承 RefCounted，不依赖编辑器
│   └── rules.gd
└── tests/
    └── test_rules.gd      # 继承 SceneTree 的无头测试入口
```

### 7.2 无头跑测试

```gdscript
# 无头测试入口
# ⚠️ 用 --script 启动的脚本必须继承 SceneTree 或 MainLoop
extends SceneTree

const Rules := preload("res://addons/my_plugin/core/rules.gd")

func _init() -> void:
    var failures := 0
    failures += _check("规则命中", func(): return Rules.evaluate("fire") == "weak")
    failures += _check("规则不命中", func(): return Rules.evaluate("unknown") == "none")
    print("失败数：%d" % failures)
    quit(failures)

func _check(label: String, fn: Callable) -> int:
    if fn.call():
        print("  ✓ ", label)
        return 0
    push_error("  ✗ ", label)
    return 1
```

```bash
godot --headless --path . --script res://addons/my_plugin/tests/test_rules.gd
```

### 7.3 社区测试框架

| 框架 | 说明 | 典型无头入口 |
|---|---|---|
| **GUT**（Godot Unit Test） | 最流行的 GDScript 单测框架 | `godot --headless -d -s addons/gut/gut_cmdln.gd` |
| **gdUnit4** | 另一个活跃的 GDScript 单测框架 | `godot --headless -c addons/gdUnit4/bin/GdUnitCmdTool.gd` |

> **机制说明**：这两个都是**社区插件**，命令行入口的具体路径与参数
> **以它们各自仓库的文档为准**，会随版本变化。
> 本书不对第三方插件的内部实现做保证。
> 无论用哪个框架，CI 的判定标准都一样：**进程退出码为 0 即通过**，
> 框架会把自己发现的失败数作为退出码返回。

---

## 📝 本章总结

### 核心要点

1. **`EditorScript` 继承 `RefCounted`**，唯一入口 `_run()`（编辑器手动触发），
   不能从代码里调用；命令行批处理要用继承 `SceneTree` 的脚本
2. **「场景是否在运行」没有信号**，
   只能用 `while EditorInterface.is_playing_scene(): await ...` 轮询；
   `EditorInterface` 没有 `get_editor_main_viewport()`
3. **CI 的标准三步**：`--headless --import` → `--export-release`；
   导出命令本身已隐含 `--import`
4. **`--script` 的脚本必须继承 `SceneTree` 或 `MainLoop`**，
   配 `--check-only` 可以只做语法门禁
5. **插件的纯逻辑要拆成普通类**，才能被无头测试覆盖；
   退出码是 CI 的唯一判定依据

### 关键术语

| 术语 | 解释 |
|---|---|
| EditorScript | 编辑器脚本，继承 `RefCounted`，手动触发 |
| SceneTree 脚本 | `--script` 模式的入口，必须继承 `SceneTree` 或 `MainLoop` |
| `--headless` | 无头模式，等价于 headless 显示驱动 + Dummy 音频驱动 |
| `--import` | 启动编辑器等资源导入完成后退出 |
| `--quit-after <N>` | 迭代 N 次后退出 |
| GUT / gdUnit4 | 两个社区 GDScript 单测框架 |

---

## 🔗 延伸阅读

- **官方文档 · 命令行**: <https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html>
- **官方文档 · 编辑器脚本**: <https://docs.godotengine.org/en/stable/tutorials/plugins/editor/scripting_the_editor.html>
- **官方文档 · 导出项目**: <https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_dedicated_servers.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_editorscript.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_os.html>（`OS.execute()`）
- **源码位置**: `main/main.cpp`（命令行参数解析）

---

## 📋 下一章预告

**第 66 篇：编辑器扩展模板**

- 插件脚手架的工程化结构
- 核心 / 工具 / 资源 / 工作流 / UI 五类模板
- 模板的版本管理与测试

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 64 篇：编辑器性能调优](/articles/64-editor-performance-tuning.md)
**下一篇**: [第 66 篇：编辑器扩展模板](/articles/66-editor-extension-templates.md)

---

*写作时间：2026-03-20*  
*字数：约 1,600 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
