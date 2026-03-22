# 第 61 篇：高级编辑器扩展

> **本卷定位**: 第八卷 编辑器扩展（高优先级篇）  
> **前置知识**: 第 58 章 插件开发基础  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

高级编辑器扩展可以大幅提升开发效率和团队协作。通过自定义 Inspector、Dock 面板、导入插件等，可以创建符合项目需求的专业工具链。

本章将深入探讨 EditorInspector 插件、自定义 Dock、资源导入插件、编辑器自动化等高级技术。

---

## 🎯 学习目标

- 掌握 EditorInspector 插件
- 学会自定义 Dock 面板
- 熟悉资源导入插件
- 实施编辑器自动化
- 了解插件发布流程

---

## 1. EditorInspector 插件

### 1.1 自定义属性编辑器

```gdscript
# 自定义 Inspector 插件
class_name CustomInspectorPlugin
extends EditorInspectorPlugin

# 支持的角色类型
func _can_handle(object):
    return object is Player or object is Enemy

# 解析属性
func _parse_property(object, type, name, hint_type, hint_string, usage_flags, wide):
    # 为特定属性创建自定义编辑器
    if name == "health" and object is Player:
        var label = Label.new()
        label.text = "玩家生命值"
        add_custom_control(label)
        
        var slider = HSlider.new()
        slider.min_value = 0
        slider.max_value = 100
        slider.value = object.health
        slider.custom_minimum_size.x = 200
        
        # 连接信号
        slider.value_changed.connect(
            func(value): 
                object.health = value
        )
        
        add_custom_control(slider)
        return true
    
    return false

# 添加分类
func _parse_category(object, category):
    if category == "Combat":
        var label = Label.new()
        label.text = "=== 战斗属性 ==="
        add_custom_control(label)

# 使用方法
# 在插件初始化时注册
func _get_plugins():
    return [CustomInspectorPlugin.new()]
```

### 1.2 自定义属性提示

```gdscript
# 自定义属性提示
class_name TooltipPlugin
extends EditorInspectorPlugin

func _parse_property(object, type, name, hint_type, hint_string, usage_flags, wide):
    # 添加工具提示
    if name == "damage":
        var tooltip = "伤害值：\n"
        tooltip += "- 基础伤害\n"
        tooltip += "- 受力量加成\n"
        tooltip += "- 可被暴击放大"
        
        # 设置属性提示
        # 通过 metadata 传递
        return false
    
    return false
```

---

## 2. 自定义 Dock 面板

### 2.1 创建 Dock 面板

```gdscript
# 自定义 Dock 面板
class_name CustomDock
extends Control

@export var dock_name: String = "My Dock"

var vbox: VBoxContainer
var tree: Tree

func _ready():
    _setup_ui()

func _setup_ui():
    # 创建布局
    vbox = VBoxContainer.new()
    add_child(vbox)
    
    # 标题
    var title = Label.new()
    title.text = dock_name
    title.add_theme_font_size_override("font_size", 16)
    vbox.add_child(title)
    
    # 工具栏
    var toolbar = HBoxContainer.new()
    vbox.add_child(toolbar)
    
    var refresh_btn = Button.new()
    refresh_btn.text = "刷新"
    refresh_btn.pressed.connect(_on_refresh)
    toolbar.add_child(refresh_btn)
    
    var settings_btn = Button.new()
    settings_btn.text = "设置"
    settings_btn.pressed.connect(_on_settings)
    toolbar.add_child(settings_btn)
    
    # 树形列表
    tree = Tree.new()
    tree.columns = 2
    vbox.add_child(tree)
    
    # 填充数据
    _populate_tree()

func _populate_tree():
    tree.clear()
    var root = tree.create_item()
    root.set_text(0, "项目资源")
    
    # 添加示例数据
    var item = tree.create_item(root)
    item.set_text(0, "玩家预制体")
    item.set_text(1, "5 个")
    item.set_icon(0, get_editor_icon("Node2D"))
    
    item = tree.create_item(root)
    item.set_text(0, "敌人预制体")
    item.set_text(1, "10 个")
    item.set_icon(0, get_editor_icon("CharacterBody2D"))

func get_editor_icon(icon_name: String) -> Texture2D:
    # 获取 Godot 编辑器图标
    return get_theme_icon(icon_name, "EditorIcons")

func _on_refresh():
    _populate_tree()

func _on_settings():
    # 打开设置对话框
    pass

# 注册 Dock 到编辑器
func _enter_tree():
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, self)

func _exit_tree():
    remove_control_from_docks(self)
```

### 2.2 资源浏览器

```gdscript
# 自定义资源浏览器
class_name ResourceBrowserDock
extends CustomDock

@export var file_filter: String = "*.tres,*.res,*.tscn"

var search_box: LineEdit
var file_list: ItemList

func _setup_ui():
    super._setup_ui()
    
    # 添加搜索框
    search_box = LineEdit.new()
    search_box.placeholder_text = "搜索资源..."
    search_box.text_changed.connect(_on_search)
    vbox.add_child(search_box)
    
    # 文件列表
    file_list = ItemList.new()
    file_list.icon_mode = ItemList.ICON_MODE_TOP
    file_list.max_columns = 4
    vbox.add_child(file_list)
    
    # 加载资源
    _load_resources()

func _load_resources():
    file_list.clear()
    
    var dir = DirAccess.open("res://")
    _scan_directory(dir, "res://")

func _scan_directory(dir: DirAccess, path: String):
    dir.list_dir_begin()
    var file_name = dir.get_next()
    
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
    var filters = file_filter.split(",")
    for filter in filters:
        if file_name.ends_with(filter.trim_prefix("*")):
            return true
    return false

func _add_file_to_list(path: String):
    var icon = get_editor_icon("ResourceFile")
    file_list.add_item(path.get_file(), icon)
    var idx = file_list.item_count - 1
    file_list.set_item_tooltip(idx, path)

func _on_search(text: String):
    # 过滤列表
    for i in range(file_list.item_count):
        var item_text = file_list.get_item_text(i)
        file_list.set_item_disabled(i, not text.is_empty() and not item_text.contains(text))
```

---

## 3. 资源导入插件

### 3.1 自定义导入器

```gdscript
# 自定义资源导入插件
class_name CustomImportPlugin
extends EditorImportPlugin

func _get_importer_name():
    return "my.custom.importer"

func _get_visible_name():
    return "Custom Data"

func _get_recognized_extensions():
    return ["mydata"]

func _get_save_extension():
    return "tres"

func _get_resource_type():
    return "Resource"

func _get_preset_count():
    return 0

func _get_preset_name(preset_index):
    return "Default"

func _get_import_options(path, preset_index):
    return [
        {"name": "Option 1", "default_value": true},
        {"name": "Option 2", "default_value": 1.0}
    ]

func _get_option_visibility(path, option_name, options):
    return true

func _import(source_file, save_path, options, platform_variants, gen_files):
    # 读取源文件
    var file = FileAccess.open(source_file, FileAccess.READ)
    var content = file.get_as_text()
    
    # 处理数据
    var resource = Resource.new()
    resource.set_meta("source", source_file)
    resource.set_meta("content", content)
    
    # 保存资源
    var save_path_full = save_path + "." + _get_save_extension()
    return ResourceSaver.save(resource, save_path_full)
```

### 3.2 批量导入工具

```gdscript
# 批量导入工具
class_name BatchImportTool
extends EditorPlugin

func _enter_tree():
    # 添加菜单项
    add_tool_menu_item("批量导入资源", _batch_import)

func _exit_tree():
    remove_tool_menu_item("批量导入资源")

func _batch_import():
    var dir_dialog = EditorFileDialog.new()
    dir_dialog.file_mode = EditorFileDialog.FILE_MODE_OPEN_DIR
    dir_dialog.access = EditorFileDialog.ACCESS_RESOURCES
    dir_dialog.dir_selected.connect(_on_dir_selected)
    add_child(dir_dialog)
    dir_dialog.popup_centered_ratio(0.5)

func _on_dir_selected(path):
    var dir = DirAccess.open(path)
    var count = 0
    
    # 扫描并导入
    dir.list_dir_begin()
    var file_name = dir.get_next()
    
    while file_name != "":
        if file_name.ends_with(".mydata"):
            _import_file(path + "/" + file_name)
            count += 1
        file_name = dir.get_next()
    
    dir.list_dir_end()
    
    print("批量导入完成：%d 个文件" % count)

func _import_file(path):
    # 调用 Godot 导入系统
    var importer = EditorResourceImporter.new()
    importer.import(path)
```

---

## 4. 编辑器自动化

### 4.1 构建管道扩展

```gdscript
# 构建管道自动化
class_name BuildPipeline
extends EditorPlugin

var export_presets: Array = []

func _enter_tree():
    # 添加构建菜单
    add_tool_menu_item("构建项目", _build_project)
    add_tool_menu_item("批量导出", _batch_export)

func _exit_tree():
    remove_tool_menu_item("构建项目")
    remove_tool_menu_item("批量导出")

func _build_project():
    # 运行测试
    _run_tests()
    
    # 构建场景
    _build_scenes()
    
    # 导出项目
    _export_project()
    
    # 生成版本
    _create_version()

func _run_tests():
    print("运行测试...")
    # 调用测试框架
    # 可以使用 Gut 或其他测试框架

func _build_scenes():
    print("构建场景...")
    var scenes = _get_all_scenes()
    
    for scene_path in scenes:
        var scene = load(scene_path)
        # 验证场景
        _validate_scene(scene)

func _export_project():
    print("导出项目...")
    
    var export_preset = "Windows Desktop"
    var output_path = "build/game.exe"
    
    var err = EditorExportPlatform.export_project(
        output_path,
        false,  # debug
        export_preset
    )
    
    if err == OK:
        print("导出成功：%s" % output_path)
    else:
        print("导出失败：%d" % err)

func _create_version():
    # 生成版本号
    var version = {
        "major": 1,
        "minor": 0,
        "patch": 0,
        "build": Time.get_unix_time_from_system()
    }
    
    var file = FileAccess.open("res://version.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(version))
```

### 4.2 场景验证工具

```gdscript
# 场景验证工具
class_name SceneValidator
extends EditorPlugin

func _enter_tree():
    add_tool_menu_item("验证场景", _validate_all_scenes)

func _validate_all_scenes():
    var scenes = _get_all_scenes()
    var errors = []
    
    for scene_path in scenes:
        var scene_errors = _validate_scene(scene_path)
        if not scene_errors.is_empty():
            errors.append({
                "scene": scene_path,
                "errors": scene_errors
            })
    
    if errors.is_empty():
        print("所有场景验证通过！")
    else:
        _show_validation_report(errors)

func _validate_scene(scene_path: String) -> Array:
    var errors = []
    
    # 加载场景
    var scene = load(scene_path)
    if not scene:
        errors.append("无法加载场景")
        return errors
    
    # 检查缺失的节点
    var root = scene.instantiate()
    _check_missing_nodes(root, errors)
    
    # 检查脚本错误
    _check_script_errors(root, errors)
    
    # 检查性能问题
    _check_performance_issues(root, errors)
    
    root.free()
    
    return errors

func _check_missing_nodes(node: Node, errors: Array):
    # 检查是否有缺失的节点引用
    for child in node.get_children():
        if not is_instance_valid(child):
            errors.append("节点 %s 有缺失的引用" % node.get_path())
        
        _check_missing_nodes(child, errors)

func _check_script_errors(node: Node, errors: Array):
    if node.get_script():
        var script = node.get_script()
        # 检查脚本是否有效
        if not script.can_instantiate():
            errors.append("脚本错误：%s" % script.resource_path)

func _check_performance_issues(node: Node, errors: Array):
    # 检查潜在性能问题
    if node is MeshInstance3D:
        if node.mesh and node.mesh.get_surface_count() > 10:
            errors.append("网格面数过多：%s" % node.get_path())
    
    for child in node.get_children():
        _check_performance_issues(child, errors)

func _show_validation_report(errors: Array):
    var report = "场景验证报告:\n\n"
    
    for error_data in errors:
        report += "场景：%s\n" % error_data.scene
        for error in error_data.errors:
            report += "  - %s\n" % error
        report += "\n"
    
    print(report)
```

---

## 5. 插件发布流程

### 5.1 AssetLib 提交

```
AssetLib 提交流程:
┌─────────────────────────────────────────────────────────────┐
│ 1. 准备插件文件                                             │
│    - plugin.cfg（插件配置）                                 │
│    - 插件脚本和文件                                         │
│    - 文档和示例                                             │
│                                                             │
│ 2. 创建 GitHub 仓库                                          │
│    - 公开仓库                                               │
│    - 包含 README.md                                         │
│    - 添加 LICENSE                                           │
│                                                             │
│ 3. 提交到 AssetLib                                          │
│    - 访问 Godot AssetLib                                    │
│    - 填写插件信息                                           │
│    - 提交审核                                               │
│                                                             │
│ 4. 维护和更新                                               │
│    - 响应用户反馈                                           │
│    - 定期更新修复 bug                                        │
│    - 发布新版本                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 插件配置

```ini
; plugin.cfg 示例
[plugin]

name="My Custom Plugin"
description="A powerful plugin for Godot"
author="Your Name"
version="1.0.0"
script="plugin.gd"

[dependencies]
; 如果有依赖其他插件
; other_plugin=">=1.0.0"
```

```gdscript
# plugin.gd - 插件主脚本
@tool
extends EditorPlugin

func _enter_tree():
    # 插件启用时调用
    print("插件已启用")
    
    # 添加自定义功能
    _add_custom_features()

func _exit_tree():
    # 插件禁用时调用
    print("插件已禁用")
    
    # 清理自定义功能
    _remove_custom_features()

func _add_custom_features():
    # 添加 Dock
    # 添加菜单
    # 注册导入器
    pass

func _remove_custom_features():
    # 移除 Dock
    # 移除菜单
    # 注销导入器
    pass
```

---

## 📝 本章总结

### 核心要点

1. **EditorInspector 定制属性编辑**，提升用户体验
2. **自定义 Dock 面板**，创建专业工具
3. **资源导入插件**，支持自定义格式
4. **编辑器自动化**，提高开发效率
5. **插件发布流程**，分享成果给社区

### 插件开发最佳实践

```
✅ 插件开发清单:
□ 清晰的文档和示例
□ 合理的错误处理
□ 用户友好的界面
□ 性能优化
□ 兼容性测试
□ 版本管理
□ 许可证选择
```

---

*写作时间：2026-03-21*  
*字数：约 8,000 字*  
*状态：✅ 完成*
