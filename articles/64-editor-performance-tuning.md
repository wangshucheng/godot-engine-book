# 第 64 篇：编辑器性能调优

> **本卷定位**: 第八卷 编辑器扩展（8 篇）  
> **前置知识**: 第 63 章 编辑器高级功能  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编辑器性能直接影响开发效率和体验。本章是**第八卷的性能专篇**：讲清楚
「用哪些指标衡量编辑器」「热点在哪」「怎么优化」「怎么持续监控」。

> **卷内边界**：本章只讲性能。扩展点 API 在第 61 篇；
> 「编辑器里有什么能改的」在第 63 篇；批量干活与 CI 在第 65 篇；
> 写法规范在第 67 篇。
>
> ⚠️ **本篇所有阈值数字**（1000 个节点 / 1000 次 draw call / 16 ms 帧时间等）
> 均为 **⚠️ 示意数据（未附测试环境）**，仅用于说明判断逻辑，
> 真实阈值必须以你自己项目的实测基线为准。

---

## 🎯 学习目标

- 掌握编辑器进程的性能指标读取方式
- 会用脚本定位场景树、资源与渲染热点
- 掌握场景树与资源加载的优化手段
- 建立可持续运行的性能监控与报告

---

## 1. 编辑器性能分析

### 1.1 性能分析工具

```gdscript
# 编辑器性能采样
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name EditorPerformanceAnalyzer
extends Node

func get_performance_metrics() -> Dictionary:
    # 获取性能指标
    return {
        "frame_time": Performance.get_monitor(Performance.TIME_PROCESS),
        "memory_usage": OS.get_static_memory_usage(),
        "fps": Engine.get_frames_per_second(),
        # ⚠️ Time.get_ticks_msec() 返回的是「引擎启动以来的毫秒总数」，
        #    不是帧时间。帧时间要用 1000.0 / FPS，或直接读 Performance 监视器。
        "frame_time": 1000.0 / max(Engine.get_frames_per_second(), 1),
        "process_time": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
        "scene_tree_size": _get_scene_tree_size(),
        "resource_cache_size": _get_resource_cache_size(),
        "editor_plugin_count": _get_editor_plugin_count(),
    }

func _get_scene_tree_size() -> int:
    # 获取场景树大小
    var scene := EditorInterface.get_edited_scene_root()
    if scene:
        return _count_nodes(scene)
    return 0

func _count_nodes(node: Node) -> int:
    # 计算节点数量
    var count := 1
    for child in node.get_children():
        count += _count_nodes(child)
    return count

func _get_resource_cache_size() -> int:
    # 没有可查询的"资源缓存"对象；用对象监视器里的资源计数代替
    return int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT))

func _get_editor_plugin_count() -> int:
    # 编辑器没有列出插件实例的 API；启用数从项目设置读取
    var enabled_plugins: PackedStringArray = ProjectSettings.get_setting(
        "editor_plugins/enabled", PackedStringArray())
    return enabled_plugins.size()
```

> **机制说明**：
> - 引擎**没有** `PerformanceProfiler` 这个类（全书检索 `class_name PerformanceProfiler`
>   命中 0）。要采样只能自己组合 `Performance.get_monitor()`、
>   `Performance.get_monitor(Performance.TIME_PROCESS)`、`Engine.get_frames_per_second()`。
> - `Performance.TIME_PROCESS` 返回的是**秒**（float），乘 1000 才是毫秒。
> - 引擎**没有** CPU 占用率 API：`OS.get_process_cpu_usage()` 在 4.3 不存在。
>   能拿到的是单帧处理耗时 `Performance.get_monitor(Performance.TIME_PROCESS)`（单位：秒）。
> - 引擎**没有** `OS.get_total_memory()`。系统物理内存总量在
>   `OS.get_memory_info()` 返回的字典里（`physical` 键，单位：字节）；
>   引擎自身占用看 `OS.get_static_memory_usage()` 或
>   `Performance.get_monitor(Performance.MEMORY_STATIC)`。

### 1.2 性能热点识别

```gdscript
# 性能热点识别
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PerformanceHotspotIdentifier
extends Node

# severity 用数值，便于排序；阈值均为 ⚠️ 示意数据（未附测试环境）
const SEVERITY_HIGH := 3
const SEVERITY_MEDIUM := 2

func identify_hotspots() -> Array:
    # 识别性能热点
    var hotspots: Array = []

    hotspots += _identify_scene_tree_hotspots()
    hotspots += _identify_resource_hotspots()
    hotspots += _identify_rendering_hotspots()
    hotspots += _identify_ui_hotspots()

    # 按严重程度排序（数值比较，不是字符串比较）
    hotspots.sort_custom(func(a, b): return a["severity"] > b["severity"])
    return hotspots

func _identify_scene_tree_hotspots() -> Array:
    var hotspots: Array = []

    var scene := EditorInterface.get_edited_scene_root()
    if scene:
        var node_count := _count_nodes(scene)
        if node_count > 1000:   # ⚠️ 示意数据（未附测试环境）
            hotspots.append({
                "type": "scene_tree",
                "name": "Large scene tree",
                "severity": SEVERITY_HIGH,
                "description": "场景节点数超过 1000",
                "recommendation": "考虑用实例化场景（InstancedScene）拆分",
            })

        var process_count := _count_process_nodes(scene)
        if process_count > 100:  # ⚠️ 示意数据（未附测试环境）
            hotspots.append({
                "type": "scene_tree",
                "name": "Process nodes",
                "severity": SEVERITY_MEDIUM,
                "description": "启用 _process 的节点超过 100",
                "recommendation": "改用信号驱动或降低处理频率",
            })

    return hotspots

func _count_process_nodes(node: Node) -> int:
    var count := 0
    if node.get_process_mode() != Node.PROCESS_MODE_DISABLED:
        count += 1
    for child in node.get_children():
        count += _count_process_nodes(child)
    return count

func _identify_resource_hotspots() -> Array:
    var hotspots: Array = []

    var resource_count := _get_resource_cache_size()
    if resource_count > 10000:  # ⚠️ 示意数据（未附测试环境）
        hotspots.append({
            "type": "resource_loading",
            "name": "Large resource cache",
            "severity": SEVERITY_MEDIUM,
            "description": "驻留资源数超过 10000",
            "recommendation": "检查是否有资源被无谓地常驻引用",
        })

    return hotspots

func _identify_rendering_hotspots() -> Array:
    var hotspots: Array = []

    var visible_objects := RenderingServer.get_rendering_info(
        RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)
    if visible_objects > 1000:  # ⚠️ 示意数据（未附测试环境）
        hotspots.append({
            "type": "rendering",
            "name": "High visible nodes",
            "severity": SEVERITY_HIGH,
            "description": "单帧可见对象超过 1000",
            "recommendation": "考虑剔除、LOD 与实例化",
        })

    if RenderingServer.get_rendering_info(
            RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME) > 1000:  # ⚠️ 示意数据（未附测试环境）
        hotspots.append({
            "type": "rendering",
            "name": "High draw calls",
            "severity": SEVERITY_HIGH,
            "description": "单帧 draw call 超过 1000",
            "recommendation": "合并材质与网格，或使用 MultiMesh",
        })

    return hotspots

func _identify_ui_hotspots() -> Array:
    # 编辑器设置里没有 editor_metrics；
    # 编辑器进程的帧耗时直接读 Performance 监视器（在编辑器中同样有效）
    var hotspots: Array = []

    var frame_ms := Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
    if frame_ms > 16.0:  # ⚠️ 示意数据（未附测试环境）
        hotspots.append({
            "type": "ui",
            "name": "High UI frame time",
            "severity": SEVERITY_MEDIUM,
            "description": "编辑器帧耗时超过 16 ms",
            "recommendation": "检查是不是有插件在每帧做重活",
        })

    return hotspots
```

### 1.3 性能基准测试

```gdscript
# 性能基准测试
# ⚠️ 面向编辑器的脚本必须加 @tool
# 基准测试需要 await，所以必须继承 Node（RefCounted 没有 get_tree()）
@tool
class_name PerformanceBenchmark
extends Node

var benchmarks := {
    "scene_tree_creation": {
        "name": "Scene Tree Creation",
        "description": "Create and destroy a scene tree",
        "test_function": "test_scene_tree_creation",
    },
    "resource_loading": {
        "name": "Resource Loading",
        "description": "Load resources from disk",
        "test_function": "test_resource_loading",
    },
    "rendering_performance": {
        "name": "Rendering Performance",
        "description": "Test rendering performance",
        "test_function": "test_rendering_performance",
    },
}

func run_benchmark(benchmark_name: String) -> Dictionary:
    var benchmark: Dictionary = benchmarks.get(benchmark_name, {})
    if benchmark.is_empty():
        return {}
    return await _run_test_function(benchmark["test_function"])

func _run_test_function(function_name: String) -> Dictionary:
    match function_name:
        "test_scene_tree_creation":
            return _test_scene_tree_creation()
        "test_resource_loading":
            return _test_resource_loading()
        "test_rendering_performance":
            return _test_rendering_performance()
    return {}

func _test_scene_tree_creation() -> Dictionary:
    # Time.get_ticks_msec() 用作「区间计时」是正确的：取前后两次的差值
    var start_time := Time.get_ticks_msec()

    var scene := SceneTree.new()
    var root := Node.new()
    root.name = "Root"
    scene.add_child(root)

    for i in range(1000):
        var node := Node.new()
        node.name = "Node" + str(i)
        root.add_child(node)

    scene.queue_free()

    var end_time := Time.get_ticks_msec()

    return {
        "name": "Scene Tree Creation",
        "time_ms": end_time - start_time,
        "nodes_created": 1000,
    }

func _test_resource_loading() -> Dictionary:
    var start_time := Time.get_ticks_msec()

    for i in range(100):
        var resource := load("res://icon.png")
        if resource == null:
            push_warning("资源加载失败：res://icon.png")

    var end_time := Time.get_ticks_msec()

    return {
        "name": "Resource Loading",
        "time_ms": end_time - start_time,
        "resources_loaded": 100,
    }

func _test_rendering_performance() -> Dictionary:
    # 等待 1000 帧完成，读取真实帧时间而非调用不存在的绘制接口
    var start_time := Time.get_ticks_msec()
    var start_frames := Engine.get_frames_drawn()
    while Engine.get_frames_drawn() - start_frames < 1000:
        await get_tree().process_frame
    var end_time := Time.get_ticks_msec()

    return {
        "name": "Rendering Performance",
        "time_ms": end_time - start_time,
        "frames_rendered": 1000,
    }
```

> **机制说明**：**插件无法被脚本「注册」进编辑器**。
> 4.3 的 `EditorInterface` 方法全表里没有 `register_plugin()` /
> `unregister_plugin()` / `get_plugins()`——插件实例由编辑器扫描 `addons/`
> 之后自行创建，脚本唯一能做的是用 `EditorInterface.set_plugin_enabled()` /
> `is_plugin_enabled()` 切换启用状态（参数是插件**目录名**）。
> 想测「插件开销」只能测自己插件里真实存在的开销。

---

## 2. 编辑器优化技巧

### 2.1 场景树优化

```gdscript
# 场景树优化
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name SceneTreeOptimization
extends Node

func optimize_scene_tree(scene: Node) -> void:
    # 优化场景树
    _cleanup_unused_nodes(scene)
    _merge_similar_nodes(scene)
    _optimize_process_nodes(scene)

func _cleanup_unused_nodes(scene: Node) -> void:
    # 清理未使用的节点
    for child in scene.get_children():
        if child.is_queued_for_deletion():
            scene.remove_child(child)
            # ⚠️ 对已在场景树中的节点用 free() 会立即释放，
            #    本帧内若还有引用就会崩；统一用 queue_free()
            child.queue_free()

func _merge_similar_nodes(scene: Node) -> void:
    # 合并相似节点
    var node_groups := {}
    for child in scene.get_children():
        var key := child.get_class()
        if node_groups.has(key):
            node_groups[key].append(child)
        else:
            node_groups[key] = [child]

    for key in node_groups:
        if node_groups[key].size() > 100:  # ⚠️ 示意数据（未附测试环境）
            _merge_nodes(node_groups[key])

func _merge_nodes(nodes: Array) -> void:
    # 合并节点
    pass

func _optimize_process_nodes(scene: Node) -> void:
    # 优化 process 节点
    for child in scene.get_children():
        if child.get_process_mode() != Node.PROCESS_MODE_DISABLED:
            child.set_process_mode(Node.PROCESS_MODE_IDLE)
```

### 2.2 资源加载优化

```gdscript
# 资源加载优化
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name ResourceLoadingOptimization
extends Node

var lazy_paths: Array[String] = []

func optimize_resource_loading() -> void:
    # 没有开关式的"缓存加载"或"异步加载"编辑器设置：
    # 资源缓存是 ResourceLoader 的内建行为，后台加载用线程化 API
    _use_threaded_loading()
    _implement_lazy_loading()

func _use_threaded_loading() -> void:
    # 后台线程加载大资源，避免卡顿（4.x 取代 3.x 的 load_interactive）
    ResourceLoader.load_threaded_request("res://large_level.scn")
    var progress: Array = []
    if ResourceLoader.load_threaded_get_status("res://large_level.scn", progress) \
            == ResourceLoader.THREAD_LOAD_LOADED:
        var resource := ResourceLoader.load_threaded_get("res://large_level.scn")
        if resource:
            print("加载完成：", resource)

func _implement_lazy_loading() -> void:
    # 懒加载：只保存路径，真正需要时再 load
    # 典型场景：编辑器面板不在 _init() 里扫描全部资源
    lazy_paths = ["res://textures/a.png", "res://textures/b.png"]

func get_lazy(index: int) -> Resource:
    return load(lazy_paths[index]) if index < lazy_paths.size() else null

func _preload_critical_resources() -> void:
    # 关键资源用 preload 在编译期加载，最稳
    var icon := preload("res://icon.png")

func _unload_unused_resources(resource: Resource) -> void:
    # ⚠️ 不存在 ResourceCache.get_cached()/remove()：
    # 资源由引用计数管理，释放只需去掉所有引用
    resource = null
```

### 2.3 渲染优化

```gdscript
# 渲染优化：这些能力属于游戏项目本身，不存在 editor settings 开关
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name RenderingOptimization
extends Node3D

func optimize_rendering() -> void:
    _implement_culling()
    _use_lod()

# 遮挡剔除：在场景里放 OccluderInstance3D 并由编辑器烘焙遮挡网格
func _implement_culling() -> void:
    var occluder := OccluderInstance3D.new()
    occluder.bake_mask = 4294967295   # 默认烘焙所有视觉层
    add_child(occluder)

# LOD：用节点的 visibility_range_* 按距离控制显示
func _use_lod() -> void:
    var mesh_instance := $MeshInstance3D as MeshInstance3D
    if mesh_instance:
        mesh_instance.visibility_range_begin = 0.0
        mesh_instance.visibility_range_end = 50.0

# 减少绘制调用：合并网格或使用 MultiMesh 实例化
func _reduce_draw_calls(source: Mesh, count: int) -> void:
    var multi_mesh := MultiMesh.new()
    multi_mesh.transform_format = MultiMesh.TRANSFORM_3D
    multi_mesh.mesh = source
    multi_mesh.instance_count = count
```

---

## 3. 最佳实践

### 3.1 开发最佳实践

```gdscript
# 开发最佳实践
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name DevelopmentBestPractices
extends Node

func follow_development_best_practices() -> void:
    _use_deferred_calls()
    _implement_background_loading()
    _use_object_pools()

func _use_deferred_calls() -> void:
    # 使用 deferred 调用，不要阻塞主线程
    call_deferred("update_ui")
    call_deferred("process_data")

func _implement_background_loading() -> void:
    # 实现后台加载：使用多线程加载大资源
    pass

func _use_object_pools() -> void:
    # 使用对象池：复用对象而不是创建和销毁
    pass

func _optimize_draw_calls() -> void:
    # 优化 draw 调用：批处理相似的 draw 调用
    pass

func _reduce_memory_usage() -> void:
    # 减少内存使用：及时释放未使用的资源
    pass
```

### 3.2 性能监控最佳实践

```gdscript
# 性能监控最佳实践
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name PerformanceMonitoringBestPractices
extends Node

var performance_metrics: Dictionary = {}
var _timer: Timer

func start_performance_monitoring() -> void:
    _start_monitoring_timer()
    _initialise_metrics()

func stop_performance_monitoring() -> void:
    _stop_monitoring_timer()

func _start_monitoring_timer() -> void:
    if _timer:
        return
    _timer = Timer.new()
    _timer.wait_time = 1.0
    _timer.one_shot = false
    _timer.timeout.connect(_on_monitoring_timer_timeout)
    add_child(_timer)
    _timer.start()

func _stop_monitoring_timer() -> void:
    if _timer:
        _timer.stop()
        _timer.queue_free()
        _timer = null

func _on_monitoring_timer_timeout() -> void:
    _update_performance_metrics()
    _check_performance_thresholds()

func _initialise_metrics() -> void:
    performance_metrics = {
        "frame_time": [],
        "cpu_usage": [],
        "memory_usage": [],
        "render_time": [],
        "scene_tree_size": [],
    }

func _update_performance_metrics() -> void:
    var current_metrics := get_performance_metrics()

    for key in current_metrics:
        if not performance_metrics.has(key):
            performance_metrics[key] = []
        performance_metrics[key].append(current_metrics[key])

        # 保持最近 100 个样本
        if performance_metrics[key].size() > 100:
            performance_metrics[key].pop_front()

func get_performance_metrics() -> Dictionary:
    return {
        "frame_time": 1000.0 / max(Engine.get_frames_per_second(), 1),
        "frame_time": Performance.get_monitor(Performance.TIME_PROCESS),
        "memory_usage": Performance.get_monitor(Performance.MEMORY_STATIC),
        "render_time": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
        "scene_tree_size": 0,
    }

func _check_performance_thresholds() -> void:
    var samples: Array = performance_metrics.get("frame_time", [])
    if samples.is_empty():
        return
    var avg_frame_time: float = samples.sum() / samples.size()
    if avg_frame_time > 16.0:  # ⚠️ 示意数据（未附测试环境）
        print("性能告警：平均帧耗时超过 16 ms（当前 %.2f ms）" % avg_frame_time)
```

### 3.3 调试最佳实践

```gdscript
# 调试最佳实践
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name DebuggingBestPractices
extends Node

func follow_debugging_best_practices() -> void:
    _use_profiling()
    _implement_logging()
    _add_performance_markers()

func _use_profiling() -> void:
    # 使用性能分析：定期采样 Performance 监视器
    pass

func _implement_logging() -> void:
    # 实现日志记录：使用适当的日志级别
    # print_debug() / push_warning() / push_error()
    pass

func _add_performance_markers() -> void:
    # 添加性能标记：在关键代码点采样
    pass

func _optimize_debug_output() -> void:
    # 优化调试输出：限制输出频率
    pass
```

---

## 4. 性能监控工具

### 4.1 实时监控工具

```gdscript
# 实时监控工具
# ⚠️ 面向编辑器的脚本必须加 @tool
# add_control_to_dock() 是 EditorPlugin 的成员函数，所以这里要继承 EditorPlugin
@tool
class_name RealtimeMonitoringTool
extends EditorPlugin

var metrics: Dictionary = {}
var _dock: Control
var _metrics_label: Label
var _timer: Timer

func _enter_tree() -> void:
    _setup_ui()
    _setup_monitoring()

func _exit_tree() -> void:
    if _timer:
        _timer.stop()
        _timer.queue_free()
        _timer = null
    if _dock:
        remove_control_from_docks(_dock)
        _dock.queue_free()
        _dock = null

func _setup_ui() -> void:
    _dock = Control.new()
    _dock.name = "RealtimeMonitorDock"

    var vbox := VBoxContainer.new()
    _dock.add_child(vbox)

    var title := Label.new()
    title.text = "Real-time Monitor"
    # Label 的属性名是 horizontal_alignment，不是 align
    title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    vbox.add_child(title)

    _metrics_label = Label.new()
    _metrics_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
    vbox.add_child(_metrics_label)

    add_control_to_dock(EditorPlugin.DOCK_SLOT_RIGHT_UL, _dock)

func _setup_monitoring() -> void:
    _timer = Timer.new()
    _timer.wait_time = 0.5
    _timer.one_shot = false
    _timer.timeout.connect(_on_monitoring_timer_timeout)
    add_child(_timer)
    _timer.start()

func _on_monitoring_timer_timeout() -> void:
    _update_metrics()
    _update_ui()

func _update_metrics() -> void:
    metrics["fps"] = Engine.get_frames_per_second()
    metrics["frame_time"] = 1000.0 / max(Engine.get_frames_per_second(), 1)
    metrics["frame_time"] = Performance.get_monitor(Performance.TIME_PROCESS)
    metrics["memory_usage"] = Performance.get_monitor(Performance.MEMORY_STATIC)
    metrics["scene_tree_size"] = _get_scene_tree_size()

func _get_scene_tree_size() -> int:
    var scene := EditorInterface.get_edited_scene_root()
    return _count_nodes(scene) if scene else 0

func _count_nodes(node: Node) -> int:
    var count := 1
    for child in node.get_children():
        count += _count_nodes(child)
    return count

func _update_ui() -> void:
    if _metrics_label == null:
        return
    _metrics_label.text = "FPS: %d\n" % metrics["fps"]
    _metrics_label.text += "帧耗时: %.2f ms\n" % metrics["frame_time"]
    _metrics_label.text += "CPU 占用: %.1f%%\n" % metrics["cpu_usage"]
    _metrics_label.text += "静态内存: %.2f MB\n" % (metrics["memory_usage"] / 1048576.0)
    _metrics_label.text += "场景树节点数: %d" % metrics["scene_tree_size"]
```

### 4.2 历史分析工具

```gdscript
# 历史分析工具
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name HistoryAnalysisTool
extends Node

var history: Dictionary = {}
var max_samples: int = 1000

func record_history(sample: Dictionary) -> void:
    for key in sample:
        if not history.has(key):
            history[key] = []
        history[key].append(sample[key])

        if history[key].size() > max_samples:
            history[key].pop_front()

func get_history_stats(key: String) -> Dictionary:
    if not history.has(key) or history[key].is_empty():
        return {}

    var data: Array = history[key]
    # ⚠️ Array 没有 front_back()（那是 Dictionary 的方法）；
    #    中位数要自己排序后取下标
    var sorted := data.duplicate()
    sorted.sort()
    var mid := sorted.size() / 2
    var median: float = sorted[mid]
    if sorted.size() % 2 == 0:
        median = (float(sorted[mid - 1]) + float(sorted[mid])) / 2.0

    return {
        "min": data.min(),
        "max": data.max(),
        "avg": data.sum() / data.size(),
        "median": median,
    }

func get_performance_trend(key: String) -> String:
    if not history.has(key) or history[key].size() < 2:
        return "stable"

    var data: Array = history[key]
    var first_half: Array = data.slice(0, data.size() / 2)
    var last_half: Array = data.slice(data.size() / 2)

    var first_avg: float = first_half.sum() / first_half.size()
    var last_avg: float = last_half.sum() / last_half.size()
    if first_avg == 0.0:
        return "stable"

    var change_percentage := (last_avg - first_avg) / first_avg * 100.0

    if change_percentage > 10.0:
        return "degrading"
    elif change_percentage < -10.0:
        return "improving"
    return "stable"

func generate_history_report() -> Dictionary:
    var report := {}
    for key in history:
        report[key] = {
            "stats": get_history_stats(key),
            "trend": get_performance_trend(key),
        }
    return report
```

### 4.3 报告生成工具

```gdscript
# 报告生成工具
# ⚠️ 面向编辑器的脚本必须加 @tool
@tool
class_name ReportingTool
extends Node

var report_data: Dictionary = {}
var report_history: Array = []
var _hotspot_identifier: PerformanceHotspotIdentifier

func _ready() -> void:
    _hotspot_identifier = PerformanceHotspotIdentifier.new()

func generate_performance_report() -> Dictionary:
    report_data = {
        "timestamp": Time.get_unix_time(),
        "metrics": _get_performance_metrics(),
        "hotspots": _get_performance_hotspots(),
        "recommendations": _get_optimization_recommendations(),
        "history_stats": _get_history_stats(),
    }
    report_history.append(report_data)
    return report_data

func _get_performance_metrics() -> Dictionary:
    return {
        "fps": Engine.get_frames_per_second(),
        "frame_time": 1000.0 / max(Engine.get_frames_per_second(), 1),
        "frame_time": Performance.get_monitor(Performance.TIME_PROCESS),
        "memory_usage": Performance.get_monitor(Performance.MEMORY_STATIC),
        "scene_tree_size": _get_scene_tree_size(),
        "resource_cache_size": int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT)),
    }

func _get_performance_hotspots() -> Array:
    if _hotspot_identifier == null:
        _hotspot_identifier = PerformanceHotspotIdentifier.new()
    return _hotspot_identifier.identify_hotspots()

func _get_optimization_recommendations() -> Array:
    var recommendations: Array = []
    var metrics := _get_performance_metrics()

    # 下列阈值均为 ⚠️ 示意数据（未附测试环境）
    if metrics["fps"] < 60:
        recommendations.append("渲染帧率未达 60 FPS")
    if metrics["cpu_usage"] > 80.0:
        recommendations.append("CPU 占用偏高，检查每帧热点")
    if metrics["memory_usage"] > 800000000:
        recommendations.append("静态内存占用偏高，检查常驻资源")
    if metrics["scene_tree_size"] > 1000:
        recommendations.append("场景树偏大，考虑实例化拆分")

    return recommendations

func _get_history_stats() -> Dictionary:
    return {}

func _get_scene_tree_size() -> int:
    var scene := EditorInterface.get_edited_scene_root()
    return _count_nodes(scene) if scene else 0

func _count_nodes(node: Node) -> int:
    var count := 1
    for child in node.get_children():
        count += _count_nodes(child)
    return count
```

---

## 📝 本章总结

### 核心要点

1. **没有 `PerformanceProfiler` 类**，采样要自己用 `Performance.get_monitor()` +
   `Engine.get_frames_per_second()`
2. **`Time.get_ticks_msec()` 是启动以来的毫秒总数**；帧时间用
   `1000.0 / FPS` 或 `Performance.TIME_PROCESS * 1000.0`
3. **插件不能被脚本注册**：`EditorInterface` 没有
   `register_plugin()` / `unregister_plugin()` / `get_plugins()`，
   只有 `set_plugin_enabled()` / `is_plugin_enabled()`
4. **`EditorInterface` 是全局单例**（4.2+），
   直接 `EditorInterface.get_edited_scene_root()`，
   不要在普通类里调 `get_editor_interface()`
5. **对已在场景树中的节点用 `queue_free()`**，不要用 `free()`
6. **所有阈值都是 ⚠️ 示意数据（未附测试环境）**，落地前请先测自己的基线

### 关键术语

| 术语 | 解释 |
|---|---|
| Performance | 引擎性能监视器（`get_monitor()`） |
| TIME_PROCESS | 单帧处理耗时监视器（单位：秒） |
| MEMORY_STATIC | 静态内存占用监视器（单位：字节） |
| OBJECT_RESOURCE_COUNT | 驻留资源数量监视器 |
| Performance.TIME_PROCESS | 单帧处理耗时（秒）；引擎没有 CPU 占用率 API |
| PerformanceHotspotIdentifier | 本篇的热点识别器 |
| RealtimeMonitoringTool | 本篇的实时监控 Dock |

---

## 🔗 延伸阅读

- **官方文档 · 性能监视器**: <https://docs.godotengine.org/en/stable/tutorials/performance/index.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_performance.html>
- **类参考**: <https://docs.godotengine.org/en/stable/classes/class_os.html>
- **源码位置**: `core/performance/performance.cpp`, `servers/rendering_server.cpp`

---

## 📋 下一章预告

**第 65 篇：编辑器自动化**

- EditorScript 批处理实战
- 构建 / 测试 / 部署工作流
- CI 里怎么用无头编辑器

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 63 篇：编辑器高级功能](/articles/63-editor-advanced-features.md)
**下一篇**: [第 65 篇：编辑器自动化](/articles/65-editor-automation.md)

---

*写作时间：2026-03-20*  
*字数：约 800 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
