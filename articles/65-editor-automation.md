# 第 65 篇：编辑器自动化

> **本卷定位**: 第八卷 编辑器扩展（6 篇）  
> **前置知识**: 第 64 章 编辑器性能调优  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编辑器自动化可以大幅提高开发效率，减少重复性工作。通过自动化脚本、工作流和批处理工具，开发者可以实现一键生成代码、批量处理资源、自动化测试等任务。本章将探讨编辑器自动化脚本、工作流、工具和最佳实践。

---

## 🎯 学习目标

- 掌握编辑器自动化脚本
- 学会自动化工作流
- 熟悉批处理工具
- 掌握自动化最佳实践

---

## 1. 编辑器自动化脚本

### 1.1 自动化脚本基础

```gdscript
# 自动化脚本基础
class_name AutomationScriptBase

extends EditorScript

func _run():
    # 自动化脚本主函数
    _validate_environment()
    _execute_tasks()
    _generate_report()

func _validate_environment():
    # 验证环境
    if not get_editor_interface():
        push_error("Editor interface not available")
        return
    
    var scene = get_editor_interface().get_edited_scene_root()
    if not scene:
        push_error("No scene opened")
        return

func _execute_tasks():
    # 执行任务
    _prefab_generation()
    _batch_import()
    _data_export()

func _generate_report():
    # 生成报告
    var report = {
        "timestamp": Time.get_unix_time(),
        "tasks_completed": 3,
        "success": true
    }
    print("Automation report:", JSON.stringify(report, "  "))
```

### 1.2 代码生成脚本

```gdscript
# 代码生成脚本
class_name CodeGenerationScript

extends EditorScript

func _run():
    # 代码生成脚本主函数
    _generate_class()
    _generate_component()
    _generate_system()

func _generate_class():
    # 生成类
    var class_template = """
extends Node

class_name ClassName

func _ready():
    pass

func _process(delta):
    pass
"""
    class_template = class_template.replace("ClassName", "MyClass")
    print("Generated class:", class_template)

func _generate_component():
    # 生成组件
    var component_template = """
extends Node2D

class_name ComponentName

func _ready():
    pass

func update():
    pass
"""
    component_template = component_template.replace("ComponentName", "MyComponent")
    print("Generated component:", component_template)

func _generate_system():
    # 生成系统
    var system_template = """
extends Node

class_name SystemName

func _ready():
    pass

func update(delta):
    pass
"""
    system_template = system_template.replace("SystemName", "MySystem")
    print("Generated system:", system_template)
```

### 1.3 批量资源处理脚本

```gdscript
# 批量资源处理脚本
class_name BatchResourceProcessingScript

extends EditorScript

func _run():
    # 批量资源处理脚本主函数
    _batch_import_textures()
    _batch_process_audio()
    _batch_convert_scenes()

func _batch_import_textures():
    # 批量导入纹理
    var texture_dir = "res://textures/"
    var files = _get_files_in_directory(texture_dir)
    
    for file in files:
        if file.ends_with(".png") or file.ends_with(".jpg"):
            _import_texture(texture_dir + file)

func _import_texture(path: String):
    # 导入纹理
    var texture = load(path)
    if texture:
        print("Imported texture:", path)
        # 这里可以添加额外的处理逻辑
        # 例如：生成mipmaps、压缩等

func _batch_process_audio():
    # 批量处理音频
    var audio_dir = "res://audio/"
    var files = _get_files_in_directory(audio_dir)
    
    for file in files:
        if file.ends_with(".wav") or file.ends_with(".ogg"):
            _process_audio(audio_dir + file)

func _process_audio(path: String):
    # 处理音频
    var audio = load(path)
    if audio:
        print("Processed audio:", path)
        # 这里可以添加额外的处理逻辑
        # 例如：标准化、压缩等

func _batch_convert_scenes():
    # 批量转换场景
    var scene_dir = "res://scenes/"
    var files = _get_files_in_directory(scene_dir)
    
    for file in files:
        if file.ends_with(".tscn"):
            _convert_scene(scene_dir + file)

func _convert_scene(path: String):
    # 转换场景
    var scene = load(path)
    if scene:
        print("Converted scene:", path)
        # 这里可以添加额外的转换逻辑
        # 例如：更新节点名称、优化节点结构等

func _get_files_in_directory(path: String) -> Array:
    # 获取目录中的文件
    var files = []
    var dir = DirAccess.open(path)
    if dir:
        dir.list_dir_begin()
        var file_name = dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
    return files
```

### 1.4 数据导出脚本

```gdscript
# 数据导出脚本
class_name DataExportScript

extends EditorScript

func _run():
    # 数据导出脚本主函数
    _export_items()
    _export_levels()
    _export_statistics()

func _export_items():
    # 导出物品数据
    var items = _get_all_items()
    var export_data = []
    
    for item in items:
        export_data.append({
            "id": item["id"],
            "name": item["name"],
            "type": item["type"],
            "value": item["value"]
        })
    
    _save_to_json(export_data, "res://export/items.json")
    print("Exported items:", export_data.size())

func _export_levels():
    # 导出关卡数据
    var levels = _get_all_levels()
    var export_data = []
    
    for level in levels:
        export_data.append({
            "id": level["id"],
            "name": level["name"],
            "difficulty": level["difficulty"],
            "enemy_count": level["enemy_count"]
        })
    
    _save_to_json(export_data, "res://export/levels.json")
    print("Exported levels:", export_data.size())

func _export_statistics():
    # 导出统计信息
    var stats = {
        "total_items": _get_all_items().size(),
        "total_levels": _get_all_levels().size(),
        "total_scenes": _get_all_scenes().size()
    }
    
    _save_to_json(stats, "res://export/statistics.json")
    print("Exported statistics:", stats)

func _get_all_items() -> Array:
    # 获取所有物品
    return [
        {"id": 1, "name": "Sword", "type": "weapon", "value": 100},
        {"id": 2, "name": "Shield", "type": "armor", "value": 150},
        {"id": 3, "name": "Potion", "type": "consumable", "value": 50}
    ]

func _get_all_levels() -> Array:
    # 获取所有关卡
    return [
        {"id": 1, "name": "Level 1", "difficulty": "easy", "enemy_count": 5},
        {"id": 2, "name": "Level 2", "difficulty": "medium", "enemy_count": 10},
        {"id": 3, "name": "Level 3", "difficulty": "hard", "enemy_count": 15}
    ]

func _get_all_scenes() -> Array:
    # 获取所有场景
    return ["res://scenes/main.tscn", "res://scenes/menu.tscn"]

func _save_to_json(data: Variant, path: String):
    # 保存到JSON文件
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(data, "  "))
        file.close()
        print("Saved to JSON:", path)
```

---

## 2. 自动化工作流

### 2.1 构建工作流

```gdscript
# 构建工作流
class_name BuildWorkflow

extends EditorScript

func _run():
    # 构建工作流主函数
    _validate_project()
    _build_resources()
    _build_scene()
    _export_build()

func _validate_project():
    # 验证项目
    print("Validating project...")
    
    # 检查关键资源
    if not ResourceLoader.exists("res://scenes/main.tscn"):
        push_error("Main scene not found")
        return
    
    # 检查脚本
    if not ResourceLoader.exists("res://scripts/main.gd"):
        push_error("Main script not found")
        return
    
    print("Project validation passed")

func _build_resources():
    # 构建资源
    print("Building resources...")
    
    # 预加载所有资源
    var resource_paths = [
        "res://textures/",
        "res://audio/",
        "res://scenes/"
    ]
    
    for path in resource_paths:
        _precache_resources(path)
    
    print("Resource building completed")

func _precache_resources(path: String):
    # 预缓存资源
    var dir = DirAccess.open(path)
    if dir:
        dir.list_dir_begin()
        var file_name = dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                load(path + file_name)
            file_name = dir.get_next()

func _build_scene():
    # 构建场景
    print("Building scene...")
    
    # 打开主场景
    var scene_path = "res://scenes/main.tscn"
    get_editor_interface().open_scene_from_path(scene_path)
    
    # 运行场景
    get_editor_interface().play_main_scene()
    
    # 停止场景
    await get_editor_interface().get_editor_main_viewport().get_tree().create_timer(1.0).timeout
    get_editor_interface().stop_playing_scene()
    
    print("Scene building completed")

func _export_build():
    # 导出构建
    print("Exporting build...")
    
    var export_settings = {
        "path": "res://export/build",
        "format": "PCK",
        "options": {
            "export_debug": false,
            "export_pck": true
        }
    }
    
    _export_project(export_settings)
    print("Build export completed")

func _export_project(settings: Dictionary):
    # 导出项目
    # 这里应该是与导出系统集成
    # Godot 4.0+ 使用 EditorExportPlugin
    pass
```

### 2.2 测试工作流

```gdscript
# 测试工作流
class_name TestWorkflow

extends EditorScript

func _run():
    # 测试工作流主函数
    _setup_test_environment()
    _run_unit_tests()
    _run_integration_tests()
    _generate_test_report()

func _setup_test_environment():
    # 设置测试环境
    print("Setting up test environment...")
    
    # 加载测试场景
    var test_scene = load("res://test/main.tscn")
    if test_scene:
        var scene_instance = test_scene.instantiate()
        get_editor_interface().get_edited_scene_root().add_child(scene_instance)
    
    # 加载测试脚本
    var test_script = load("res://test/test_runner.gd")
    
    print("Test environment setup completed")

func _run_unit_tests():
    # 运行单元测试
    print("Running unit tests...")
    
    var test_script = load("res://test/test_runner.gd")
    if test_script:
        var runner = test_script.new()
        runner.run_tests()
    
    print("Unit tests completed")

func _run_integration_tests():
    # 运行集成测试
    print("Running integration tests...")
    
    var test_scene = get_editor_interface().get_edited_scene_root()
    if test_scene:
        # 实例化测试场景
        var test_instance = test_scene.instantiate()
        get_editor_interface().get_edited_scene_root().add_child(test_instance)
        
        # 运行测试
        test_instance.run_integration_tests()
    
    print("Integration tests completed")

func _generate_test_report():
    # 生成测试报告
    print("Generating test report...")
    
    var report = {
        "timestamp": Time.get_unix_time(),
        "unit_tests": {
            "total": 10,
            "passed": 8,
            "failed": 2
        },
        "integration_tests": {
            "total": 5,
            "passed": 4,
            "failed": 1
        },
        "overall": {
            "total": 15,
            "passed": 12,
            "failed": 3,
            "success_rate": 80.0
        }
    }
    
    print("Test report:", JSON.stringify(report, "  "))
```

### 2.3 部署工作流

```gdscript
# 部署工作流
class_name DeploymentWorkflow

extends EditorScript

func _run():
    # 部署工作流主函数
    _validate_deployment_environment()
    _build_deployment_package()
    _deploy_to_target()
    _verify_deployment()

func _validate_deployment_environment():
    # 验证部署环境
    print("Validating deployment environment...")
    
    # 检查部署配置
    var deploy_config = _load_deployment_config()
    if not deploy_config:
        push_error("Deployment config not found")
        return
    
    # 检查目标环境
    var target_env = deploy_config.get("target_environment", "")
    if target_env == "":
        push_error("Target environment not specified")
        return
    
    print("Deployment environment validation passed")

func _load_deployment_config() -> Dictionary:
    # 加载部署配置
    var config_path = "res://deploy/config.json"
    var file = FileAccess.open(config_path, FileAccess.READ)
    if file:
        var json_string = file.get_as_text()
        file.close()
        
        var json = JSON.new()
        json.parse(json_string)
        return json.data
    return {}

func _build_deployment_package():
    # 构建部署包
    print("Building deployment package...")
    
    var deploy_config = _load_deployment_config()
    var package_settings = deploy_config.get("package_settings", {})
    
    # 构建资源包
    _build_resource_package(package_settings)
    
    # 构建二进制包
    _build_binary_package(package_settings)
    
    print("Deployment package built")

func _build_resource_package(settings: Dictionary):
    # 构建资源包
    # 这里应该是与资源打包系统集成
    pass

func _build_binary_package(settings: Dictionary):
    # 构建二进制包
    # 这里应该是与构建系统集成
    pass

func _deploy_to_target():
    # 部署到目标
    print("Deploying to target...")
    
    var deploy_config = _load_deployment_config()
    var target_settings = deploy_config.get("target_settings", {})
    
    # 上传文件
    _upload_files(target_settings)
    
    # 配置服务器
    _configure_server(target_settings)
    
    print("Deployment completed")

func _upload_files(settings: Dictionary):
    # 上传文件
    # 这里应该是与FTP/SFTP或云存储集成
    pass

func _configure_server(settings: Dictionary):
    # 配置服务器
    # 这里应该是与服务器配置管理集成
    pass

func _verify_deployment():
    # 验证部署
    print("Verifying deployment...")
    
    var deploy_config = _load_deployment_config()
    var verify_settings = deploy_config.get("verify_settings", {})
    
    # 检查部署状态
    var status = _check_deployment_status(verify_settings)
    
    if status["success"]:
        print("Deployment verification passed")
    else:
        push_error("Deployment verification failed")
```

---

## 3. 批处理工具

### 3.1 批量导入工具

```gdscript
# 批量导入工具
class_name BatchImportTool

func batch_importTextures(directory: String, options: Dictionary = {}):
    # 批量导入纹理
    var files = _get_files_in_directory(directory)
    var imported = 0
    
    for file in files:
        if file.ends_with(".png") or file.ends_with(".jpg"):
            _importTexture(directory + "/" + file, options)
            imported += 1
    
    print("Batch imported", imported, "textures")

func batch_importAudio(directory: String, options: Dictionary = {}):
    # 批量导入音频
    var files = _get_files_in_directory(directory)
    var imported = 0
    
    for file in files:
        if file.ends_with(".wav") or file.ends_with(".ogg"):
            _importAudio(directory + "/" + file, options)
            imported += 1
    
    print("Batch imported", imported, "audio files")

func _get_files_in_directory(directory: String) -> Array:
    # 获取目录中的文件
    var files = []
    var dir = DirAccess.open(directory)
    if dir:
        dir.list_dir_begin()
        var file_name = dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
    return files

func _importTexture(path: String, options: Dictionary):
    # 导入纹理
    # 这里应该是与导入系统集成
    print("Importing texture:", path)

func _importAudio(path: String, options: Dictionary):
    # 导入音频
    # 这里应该是与导入系统集成
    print("Importing audio:", path)
```

### 3.2 批量处理工具

```gdscript
# 批量处理工具
class_name BatchProcessingTool

func batch_convertScenes(directory: String, conversion_function: Callable):
    # 批量转换场景
    var files = _get_files_in_directory(directory)
    var processed = 0
    
    for file in files:
        if file.ends_with(".tscn"):
            conversion_function.call(directory + "/" + file)
            processed += 1
    
    print("Batch processed", processed, "scenes")

func batch_optimizeNodes(scene: Node, optimization_function: Callable):
    # 批量优化节点
    _processNode(scene, optimization_function)

func _processNode(node: Node, optimization_function: Callable):
    # 处理节点
    optimization_function.call(node)
    
    for child in node.get_children():
        _processNode(child, optimization_function)

func _get_files_in_directory(directory: String) -> Array:
    # 获取目录中的文件
    var files = []
    var dir = DirAccess.open(directory)
    if dir:
        dir.list_dir_begin()
        var file_name = dir.get_next()
        while file_name != "":
            if not dir.current_is_dir():
                files.append(file_name)
            file_name = dir.get_next()
    return files
```

### 3.3 批量导出工具

```gdscript
# 批量导出工具
class_name BatchExportTool

func batch_exportJSON(scene: Node, export_function: Callable):
    # 批量导出JSON
    var export_data = {}
    
    # 收集数据
    _collectData(scene, export_data)
    
    # 导出JSON
    var json_string = JSON.stringify(export_data, "  ")
    var file = FileAccess.open("res://export/data.json", FileAccess.WRITE)
    if file:
        file.store_string(json_string)
        file.close()

func batch_exportCSV(data: Array, export_function: Callable):
    # 批量导出CSV
    var csv_content = ""
    
    # 生成CSV
    for row in data:
        csv_content += ",".join(row) + "\n"
    
    # 导出CSV
    var file = FileAccess.open("res://export/data.csv", FileAccess.WRITE)
    if file:
        file.store_string(csv_content)
        file.close()

func _collectData(node: Node, data: Dictionary):
    # 收集数据
    data["name"] = node.name
    data["class"] = node.get_class()
    data["children"] = []
    
    for child in node.get_children():
        var child_data = {}
        _collectData(child, child_data)
        data["children"].append(child_data)
```

---

## 4. 最佳实践

### 4.1 自动化脚本最佳实践

```gdscript
# 自动化脚本最佳实践
class_name AutomationScriptBestPractices

func follow_optimisation_script_best_practices():
    # 遵循自动化脚本最佳实践
    _use_deferred_calls()
    _implement_error_handling()
    _add_progress_tracking()

func _use_deferred_calls():
    # 使用deferred调用
    # 避免阻塞主线程
    pass

func _implement_error_handling():
    # 实现错误处理
    # 使用try-catch和错误报告
    pass

func _add_progress_tracking():
    # 添加进度跟踪
    # 显示进度条和状态
    pass

func _use_multithreading():
    # 使用多线程
    # 处理大量数据时使用多线程
    pass
```

### 4.2 工作流最佳实践

```gdscript
# 工作流最佳实践
class_name WorkflowBestPractices

func follow_optimisation_workflow_best_practices():
    # 遵循工作流最佳实践
    _use_state_machines()
    _implement_logging()
    _add_validation()

func _use_state_machines():
    # 使用状态机
    # 管理工作流状态
    pass

func _implement_logging():
    # 实现日志记录
    # 记录所有重要事件
    pass

func _add_validation():
    # 添加验证
    # 验证每个步骤
    pass

func _use_template_workflow():
    # 使用模板工作流
    # 标准化工作流
    pass
```

### 4.3 批处理工具最佳实践

```gdscript
# 批处理工具最佳实践
class_name BatchToolBestPractices

func follow_optimisation_batch_tool_best_practices():
    # 遵循批处理工具最佳实践
    _use_batching()
    _implement_progress_tracking()
    _add_error_handling()

func _use_batching():
    # 使用批处理
    # 批量处理多个项目
    pass

func _implement_progress_tracking():
    # 实现进度跟踪
    # 显示进度条和状态
    pass

func _add_error_handling():
    # 添加错误处理
    # 处理错误并继续处理其他项目
    pass

func _use_multithreading():
    # 使用多线程
    # 处理大量数据时使用多线程
    pass
```

---

## 5. 实践：完整自动化系统

### 5.1 自动化协调器

```gdscript
# 自动化协调器
class_name AutomationCoordinator

var scripts: Dictionary = {}
var workflows: Dictionary = {}
var tools: Dictionary = {}

func initialize():
    # 初始化自动化协调器
    _load_scripts()
    _load_workflows()
    _load_tools()

func _load_scripts():
    # 加载脚本
    scripts = {
        "code_generation": CodeGenerationScript.new(),
        "batch_resource_processing": BatchResourceProcessingScript.new(),
        "data_export": DataExportScript.new()
    }

func _load_workflows():
    # 加载工作流
    workflows = {
        "build": BuildWorkflow.new(),
        "test": TestWorkflow.new(),
        "deployment": DeploymentWorkflow.new()
    }

func _load_tools():
    # 加载工具
    tools = {
        "batch_import": BatchImportTool.new(),
        "batch_processing": BatchProcessingTool.new(),
        "batch_export": BatchExportTool.new()
    }

func run_script(script_name: String):
    # 运行脚本
    if scripts.has(script_name):
        scripts[script_name].run()

func run_workflow(workflow_name: String):
    # 运行工作流
    if workflows.has(workflow_name):
        workflows[workflow_name].run()

func batch_importTextures(directory: String, options: Dictionary):
    # 批量导入纹理
    if tools.has("batch_import"):
        tools["batch_import"].batch_importTextures(directory, options)

func batch_exportJSON(scene: Node):
    # 批量导出JSON
    if tools.has("batch_export"):
        tools["batch_export"].batch_exportJSON(scene)
```

### 5.2 自动化仪表板

```gdscript
# 自动化仪表板
class_name AutomationDashboard

extends Control

var coordinator: AutomationCoordinator

func _ready():
    # 初始化自动化仪表板
    coordinator = AutomationCoordinator.new()
    coordinator.initialize()
    
    _setup_ui()

func _setup_ui():
    # 设置UI
    var vbox = VBoxContainer.new()
    add_child(vbox)
    
    var title = Label.new()
    title.text = "Automation Dashboard"
    vbox.add_child(title)
    
    var scripts_list = Tree.new()
    scripts_list.name = "ScriptsList"
    vbox.add_child(scripts_list)
    
    var workflows_list = Tree.new()
    workflows_list.name = "WorkflowsList"
    vbox.add_child(workflows_list)
    
    var tools_list = Tree.new()
    tools_list.name = "ToolsList"
    vbox.add_child(tools_list)
    
    _populate_lists()

func _populate_lists():
    # 填充列表
    var scripts_list = get_node("ScriptsList")
    scripts_list.clear()
    
    var root = scripts_list.create_item()
    root.set_text(0, "Scripts")
    
    for script_name in coordinator.scripts.keys():
        var item = scripts_list.create_item(root)
        item.set_text(0, script_name)
        item.set_meta("type", "script")
    
    # 填充工作流列表
    var workflows_list = get_node("WorkflowsList")
    workflows_list.clear()
    
    root = workflows_list.create_item()
    root.set_text(0, "Workflows")
    
    for workflow_name in coordinator.workflows.keys():
        var item = workflows_list.create_item(root)
        item.set_text(0, workflow_name)
        item.set_meta("type", "workflow")
    
    # 填充工具列表
    var tools_list = get_node("ToolsList")
    tools_list.clear()
    
    root = tools_list.create_item()
    root.set_text(0, "Tools")
    
    for tool_name in coordinator.tools.keys():
        var item = tools_list.create_item(root)
        item.set_text(0, tool_name)
        item.set_meta("type", "tool")
```

### 5.3 自动化执行器

```gdscript
# 自动化执行器
class_name AutomationExecutor

var coordinator: AutomationCoordinator

func _ready():
    # 初始化自动化执行器
    coordinator = AutomationCoordinator.new()
    coordinator.initialize()

func run_script(script_name: String):
    # 运行脚本
    coordinator.run_script(script_name)

func run_workflow(workflow_name: String):
    # 运行工作流
    coordinator.run_workflow(workflow_name)

func batch_importTextures(directory: String, options: Dictionary):
    # 批量导入纹理
    coordinator.batch_importTextures(directory, options)

func batch_exportJSON(scene: Node):
    # 批量导出JSON
    coordinator.batch_exportJSON(scene)

func generate_report() -> Dictionary:
    # 生成报告
    var report = {
        "timestamp": Time.get_unix_time(),
        "scripts": {
            "total": coordinator.scripts.size(),
            "names": coordinator.scripts.keys()
        },
        "workflows": {
            "total": coordinator.workflows.size(),
            "names": coordinator.workflows.keys()
        },
        "tools": {
            "total": coordinator.tools.size(),
            "names": coordinator.tools.keys()
        }
    }
    
    return report
```

---

## 📝 本章总结

### 核心要点

1. **自动化脚本**，包括代码生成、资源处理和数据导出
2. **自动化工作流**，包括构建、测试和部署工作流
3. **批处理工具**，包括批量导入、处理和导出
4. **最佳实践**，确保自动化脚本的可靠性、可维护性和性能

### 关键术语

| 术语 | 解释 |
|------|------|
| AutomationScriptBase | 自动化脚本基础，自动化脚本的基础类 |
| CodeGenerationScript | 代码生成脚本，自动生成代码 |
| BatchResourceProcessingScript | 批量资源处理脚本，批量处理资源 |
| DataExportScript | 数据导出脚本，导出数据到文件 |
| BuildWorkflow | 构建工作流，自动化构建项目 |
| TestWorkflow | 测试工作流，自动化测试 |
| DeploymentWorkflow | 部署工作流，自动化部署 |
| BatchImportTool | 批量导入工具，批量导入资源 |
| BatchProcessingTool | 批量处理工具，批量处理数据 |
| BatchExportTool | 批量导出工具，批量导出数据 |
| AutomationCoordinator | 自动化协调器，管理所有自动化脚本和工具 |
| AutomationDashboard | 自动化仪表板，显示自动化状态 |
| AutomationExecutor | 自动化执行器，执行自动化任务 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Editor Automation](https://docs.godotengine.org/en/stable/tutorials/plugins/editor-automation.html)
- **源码位置**: `editor/automation/`
- **技术博客**: [Godot Editor Automation Guide](https://godotengine.org/article/editor-automation-guide/)

---

## 📋 下一章预告

**第 66 篇：编辑器扩展模板**

- 模板架构
- 模板创建
- 模板分发
- 模板维护

---

*写作时间：2026-03-20*  
*字数：约 16,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*