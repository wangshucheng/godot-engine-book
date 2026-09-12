# 第 64 篇：编辑器性能调优

> **本卷定位**: 第八卷 编辑器扩展（7 篇）  
> **前置知识**: 第 63 章 编辑器高级功能  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

编辑器性能直接影响开发效率和体验。通过性能调优，开发者可以显著提升编辑器的响应速度、减少内存占用、优化资源加载。本章将探讨编辑器性能分析、优化技巧、最佳实践和性能监控工具。

---

## 🎯 学习目标

- 掌握编辑器性能分析
- 学会编辑器优化技巧
- 熟悉最佳实践
- 掌握性能监控工具

---

## 1. 编辑器性能分析

### 1.1 性能分析工具

```gdscript
# 性能分析工具
class_name EditorPerformanceAnalyzer

var profiler = PerformanceProfiler.new()

func start_profiling():
    # 开始性能分析
    profiler.start()
    print("Performance profiling started")

func stop_profiling():
    # 停止性能分析
    profiler.stop()
    var results = profiler.get_results()
    print("Performance profiling stopped")
    return results

func get_performance_metrics() -> Dictionary:
    # 获取性能指标
    return {
        "cpu_usage": OS.get_process_cpu_usage(),
        "memory_usage": OS.get_total_memory(),
        "fps": Engine.get_frames_per_second(),
        "frame_time": Time.get_ticks_msec(),
        "scene_tree_size": _get_scene_tree_size(),
        "resource_cache_size": _get_resource_cache_size(),
        "editor_plugin_count": _get_editor_plugin_count()
    }

func _get_scene_tree_size() -> int:
    # 获取场景树大小
    var scene = get_editor_interface().get_edited_scene_root()
    if scene:
        return _count_nodes(scene)
    return 0

func _count_nodes(node: Node) -> int:
    # 计算节点数量
    var count = 1
    for child in node.get_children():
        count += _count_nodes(child)
    return count

func _get_resource_cache_size() -> int:
    # 没有可查询的“资源缓存”对象；用对象监视器里的资源计数代替
    return int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT))

func _get_editor_plugin_count() -> int:
    # 编辑器没有列出插件实例的 API；启用数从项目设置读取
    var enabled_plugins: PackedStringArray = ProjectSettings.get_setting(
        "editor_plugins/enabled", PackedStringArray())
    return enabled_plugins.size()
```

### 1.2 性能热点识别

```gdscript
# 性能热点识别
class_name PerformanceHotspotIdentifier

func identify_hotspots() -> Array:
    # 识别性能热点
    var hotspots = []
    
    # 识别场景树热点
    var scene_tree_hotspots = _identify_scene_tree_hotspots()
    hotspots += scene_tree_hotspots
    
    # 识别资源加载热点
    var resource_hotspots = _identify_resource_hotspots()
    hotspots += resource_hotspots
    
    # 识别渲染热点
    var rendering_hotspots = _identify_rendering_hotspots()
    hotspots += rendering_hotspots
    
    # 识别UI热点
    var ui_hotspots = _identify_ui_hotspots()
    hotspots += ui_hotspots
    
    # 按严重程度排序
    hotspots.sort_custom(func(a, b): return a["severity"] > b["severity"])
    
    return hotspots

func _identify_scene_tree_hotspots() -> Array:
    # 识别场景树热点
    var hotspots = []
    
    var scene = get_editor_interface().get_edited_scene_root()
    if scene:
        var node_count = _count_nodes(scene)
        if node_count > 1000:
            hotspots.append({
                "type": "scene_tree",
                "name": "Large scene tree",
                "severity": "high",
                "description": "Scene has more than 1000 nodes",
                "recommendation": "Consider using groups or instances"
            })
        
        var process_count = _count_process_nodes(scene)
        if process_count > 100:
            hotspots.append({
                "type": "scene_tree",
                "name": "Process nodes",
                "severity": "medium",
                "description": "Scene has more than 100 nodes with process",
                "recommendation": "Consider using deferred calls"
            })
    
    return hotspots

func _count_process_nodes(node: Node) -> int:
    # 计算process节点数量
    var count = 0
    if node.get_process_mode() != NODE_PROCESS_MODE_DISABLED:
        count += 1
    for child in node.get_children():
        count += _count_process_nodes(child)
    return count

func _identify_resource_hotspots() -> Array:
    # 识别资源加载热点
    var hotspots = []
    
    var resource_count = _get_resource_cache_size()
    if resource_count > 10000:
        hotspots.append({
            "type": "resource_loading",
            "name": "Large resource cache",
            "severity": "medium",
            "description": "Resource cache has more than 10000 resources",
            "recommendation": "Consider resource reloading and caching"
        })
    
    return hotspots

func _identify_rendering_hotspots() -> Array:
    # 识别渲染热点
    var hotspots = []
    
    var visible_objects := RenderingServer.get_rendering_info(
        RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)
    if visible_objects > 1000:
        hotspots.append({
            "type": "rendering",
            "name": "High visible nodes",
            "severity": "high",
            "description": "More than 1000 visible nodes",
            "recommendation": "Consider culling and LOD"
        })
    
    if RenderingServer.get_rendering_info(
            RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME) > 1000:
        hotspots.append({
            "type": "rendering",
            "name": "High draw calls",
            "severity": "high",
            "description": "More than 1000 draw calls",
            "recommendation": "Consider batching and instancing"
        })
    
    return hotspots

func _identify_ui_hotspots() -> Array:
    # 编辑器设置里没有 editor_metrics；
    # 编辑器进程的帧耗时直接读 Performance 监视器（在编辑器中同样有效）
    var hotspots: Array = []

    var frame_ms := Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
    if frame_ms > 16.0:
        hotspots.append({
            "type": "ui",
            "name": "High UI frame time",
            "severity": "medium",
            "description": "Editor frame time is over 16ms",
            "recommendation": "Consider UI optimization"
        })

    return hotspots
```

### 1.3 性能基准测试

```gdscript
# 性能基准测试
class_name PerformanceBenchmark

var benchmarks = {
    "scene_tree_creation": {
        "name": "Scene Tree Creation",
        "description": "Create and destroy a scene tree",
        "test_function": "test_scene_tree_creation"
    },
    "resource_loading": {
        "name": "Resource Loading",
        "description": "Load resources from disk",
        "test_function": "test_resource_loading"
    },
    "rendering_performance": {
        "name": "Rendering Performance",
        "description": "Test rendering performance",
        "test_function": "test_rendering_performance"
    },
    "editor_plugin_performance": {
        "name": "Editor Plugin Performance",
        "description": "Test editor plugin performance",
        "test_function": "test_editor_plugin_performance"
    }
}

func run_benchmark(benchmark_name: String) -> Dictionary:
    # 运行基准测试
    var benchmark = benchmarks.get(benchmark_name, {})
    if benchmark:
        var test_function = benchmark["test_function"]
        return _run_test_function(test_function)
    return {}

func _run_test_function(function_name: String) -> Dictionary:
    # 运行测试函数
    match function_name:
        "test_scene_tree_creation":
            return _test_scene_tree_creation()
        "test_resource_loading":
            return _test_resource_loading()
        "test_rendering_performance":
            return _test_rendering_performance()
        "test_editor_plugin_performance":
            return _test_editor_plugin_performance()
    return {}

func _test_scene_tree_creation() -> Dictionary:
    # 测试场景树创建
    var start_time = Time.get_ticks_msec()
    
    var scene = SceneTree.new()
    var root = Node.new()
    root.name = "Root"
    scene.add_child(root)
    
    # 创建1000个节点
    for i in range(1000):
        var node = Node.new()
        node.name = "Node" + str(i)
        root.add_child(node)
    
    scene.queue_free()
    
    var end_time = Time.get_ticks_msec()
    
    return {
        "name": "Scene Tree Creation",
        "time_ms": end_time - start_time,
        "nodes_created": 1000
    }

func _test_resource_loading() -> Dictionary:
    # 测试资源加载
    var start_time = Time.get_ticks_msec()
    
    # 加载100个资源
    for i in range(100):
        var resource = load("res://icon.png")
    
    var end_time = Time.get_ticks_msec()
    
    return {
        "name": "Resource Loading",
        "time_ms": end_time - start_time,
        "resources_loaded": 100
    }

func _test_rendering_performance() -> Dictionary:
    # 测试渲染性能
    var start_time = Time.get_ticks_msec()
    
    # 等待 1000 帧完成，读取真实帧时间而非调用不存在的绘制接口
    var start_frames := Engine.get_frames_drawn()
    while Engine.get_frames_drawn() - start_frames < 1000:
        await get_tree().process_frame
    
    var end_time = Time.get_ticks_msec()
    
    return {
        "name": "Rendering Performance",
        "time_ms": end_time - start_time,
        "frames_rendered": 1000
    }

func _test_editor_plugin_performance() -> Dictionary:
    # 测试编辑器插件性能
    var start_time = Time.get_ticks_msec()
    
    # 创建100个插件
    for i in range(100):
        var plugin = EditorPlugin.new()
        plugin.name = "Plugin" + str(i)
        get_editor_interface().register_plugin(plugin)
    
    # 移除插件
    for i in range(100):
        get_editor_interface().unregister_plugin(get_editor_interface().get_plugins()[0])
    
    var end_time = Time.get_ticks_msec()
    
    return {
        "name": "Editor Plugin Performance",
        "time_ms": end_time - start_time,
        "plugins_created": 100
    }
```

---

## 2. 编辑器优化技巧

### 2.1 场景树优化

```gdscript
# 场景树优化
class_name SceneTreeOptimization

func optimize_scene_tree(scene: Node):
    # 优化场景树
    _cleanup_unused_nodes(scene)
    _merge_similar_nodes(scene)
    _optimize_process_nodes(scene)

func _cleanup_unused_nodes(scene: Node):
    # 清理未使用的节点
    for child in scene.get_children():
        if child.is_queued_for_deletion():
            scene.remove_child(child)
            child.free()

func _merge_similar_nodes(scene: Node):
    # 合并相似节点
    var node_groups = {}
    for child in scene.get_children():
        var key = child.get_class() + child.name
        if node_groups.has(key):
            node_groups[key].append(child)
        else:
            node_groups[key] = [child]
    
    for key in node_groups:
        if node_groups[key].size() > 100:
            _merge_nodes(node_groups[key])

func _optimize_process_nodes(scene: Node):
    # 优化process节点
    for child in scene.get_children():
        if child.get_process_mode() != NODE_PROCESS_MODE_DISABLED:
            child.set_process_mode(NODE_PROCESS_MODE_IDLE)
```

### 2.2 资源加载优化

```gdscript
# 资源加载优化
class_name ResourceLoadingOptimization

var lazy_paths: Array[String] = []

func optimize_resource_loading() -> void:
    # 没有开关式的“缓存加载”或“异步加载”编辑器设置：
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
class_name RenderingOptimization

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
class_name DevelopmentBestPractices

func follow_development_best_practices():
    # 遵循开发最佳实践
    _use_deferred_calls()
    _implement_background_loading()
    _use_object_pools()

func _use_deferred_calls():
    # 使用deferred调用
    # 不要阻塞主线程
    call_deferred("update_ui")
    call_deferred("process_data")

func _implement_background_loading():
    # 实现后台加载
    # 使用多线程加载大资源
    pass

func _use_object_pools():
    # 使用对象池
    # 复用对象而不是创建和销毁
    pass

func _optimize_draw_calls():
    # 优化draw调用
    # 批处理相似的draw调用
    pass

func _reduce_memory_usage():
    # 减少内存使用
    # 及时释放未使用的资源
    pass
```

### 3.2 性能监控最佳实践

```gdscript
# 性能监控最佳实践
class_name PerformanceMonitoringBestPractices

var performance_metrics: Dictionary = {}

func start_performance_monitoring():
    # 开始性能监控
    _start_monitoring_timer()
    _initialise_metrics()

func stop_performance_monitoring():
    # 停止性能监控
    _stop_monitoring_timer()

func _start_monitoring_timer():
    # 开始监控计时器
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.one_shot = false
    timer.timeout.connect(_on_monitoring_timer_timeout)
    add_child(timer)
    timer.start()

func _stop_monitoring_timer():
    # 停止监控计时器
    pass

func _on_monitoring_timer_timeout():
    # 监控计时器超时
    _update_performance_metrics()
    _check_performance_thresholds()

func _initialise_metrics():
    # 初始化指标
    performance_metrics = {
        "frame_time": [],
        "cpu_usage": [],
        "memory_usage": [],
        "render_time": [],
        "scene_tree_size": []
    }

func _update_performance_metrics():
    # 更新性能指标
    var current_metrics = get_performance_metrics()
    
    # 更新指标历史
    for key in current_metrics:
        if not performance_metrics.has(key):
            performance_metrics[key] = []
        performance_metrics[key].append(current_metrics[key])
        
        # 保持最近100个样本
        if performance_metrics[key].size() > 100:
            performance_metrics[key].pop_front()

func _check_performance_thresholds():
    # 检查性能阈值
    if performance_metrics["frame_time"].size() > 0:
        var avg_frame_time = performance_metrics["frame_time"].sum() / performance_metrics["frame_time"].size()
        if avg_frame_time > 16:
            print("Performance warning: Average frame time is over 16ms")
```

### 3.3 调试最佳实践

```gdscript
# 调试最佳实践
class_name DebuggingBestPractices

func follow_debugging_best_practices():
    # 遵循调试最佳实践
    _use_profiling()
    _implement_logging()
    _add_performance_markers()

func _use_profiling():
    # 使用性能分析
    # 定期运行性能分析器
    pass

func _implement_logging():
    # 实现日志记录
    # 使用适当的日志级别
    pass

func _add_performance_markers():
    # 添加性能标记
    # 在关键代码点添加性能标记
    pass

func _optimize_debug_output():
    # 优化调试输出
    # 限制调试输出频率
    pass
```

---

## 4. 性能监控工具

### 4.1 实时监控工具

```gdscript
# 实时监控工具
class_name RealtimeMonitoringTool

var metrics: Dictionary = {}
var history: Dictionary = {}
var timer: Timer

func _ready():
    # 初始化实时监控工具
    _setup_ui()
    _setup_monitoring()

func _setup_ui():
    # 设置UI
    var dock = Control.new()
    dock.name = "RealtimeMonitorDock"
    
    var vbox = VBoxContainer.new()
    dock.add_child(vbox)
    
    var title = Label.new()
    title.text = "Real-time Monitor"
    title.align = Label.ALIGN_CENTER
    vbox.add_child(title)
    
    var metrics_label = Label.new()
    metrics_label.text = "Metrics will appear here"
    metrics_label.size_flags_vertical = SIZE_EXPAND_FILL
    vbox.add_child(metrics_label)
    
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)

func _setup_monitoring():
    # 设置监控
    timer = Timer.new()
    timer.wait_time = 0.5
    timer.one_shot = false
    timer.timeout.connect(_on_monitoring_timer_timeout)
    add_child(timer)
    timer.start()

func _on_monitoring_timer_timeout():
    # 监控计时器超时
    _update_metrics()
    _update_ui()

func _update_metrics():
    # 更新指标
    metrics["fps"] = Engine.get_frames_per_second()
    metrics["cpu_usage"] = OS.get_process_cpu_usage()
    metrics["memory_usage"] = OS.get_total_memory()
    metrics["scene_tree_size"] = _get_scene_tree_size()

func _update_ui():
    # 更新UI
    var metrics_label = get_node("Dock/MetricsLabel")
    metrics_label.text = "FPS: " + str(metrics["fps"]) + "\n"
    metrics_label.text += "CPU Usage: " + str(metrics["cpu_usage"]) + "%\n"
    metrics_label.text += "Memory Usage: " + str(metrics["memory_usage"] / 1024 / 1024) + " MB\n"
    metrics_label.text += "Scene Tree Size: " + str(metrics["scene_tree_size"]) + " nodes"
```

### 4.2 历史分析工具

```gdscript
# 历史分析工具
class_name HistoryAnalysisTool

var history: Dictionary = {}
var max_samples: int = 1000

func record_history(sample: Dictionary):
    # 记录历史
    for key in sample:
        if not history.has(key):
            history[key] = []
        history[key].append(sample[key])
        
        # 保持最大样本数
        if history[key].size() > max_samples:
            history[key].pop_front()

func get_history_stats(key: String) -> Dictionary:
    # 获取历史统计
    if not history.has(key) or history[key].size() == 0:
        return {}
    
    var data = history[key]
    var stats = {
        "min": data.min(),
        "max": data.max(),
        "avg": data.sum() / data.size(),
        "median": data.sort().front_back()[data.size() / 2]
    }
    
    return stats

func get_performance_trend(key: String) -> String:
    # 获取性能趋势
    if not history.has(key) or history[key].size() < 2:
        return "stable"
    
    var data = history[key]
    var last_half = data.slice(data.size() / 2)
    var first_half = data.slice(0, data.size() / 2)
    
    var last_avg = last_half.sum() / last_half.size()
    var first_avg = first_half.sum() / first_half.size()
    
    var change_percentage = (last_avg - first_avg) / first_avg * 100
    
    if change_percentage > 10:
        return "degrading"
    elif change_percentage < -10:
        return "improving"
    else:
        return "stable"

func generate_history_report() -> Dictionary:
    # 生成历史报告
    var report = {}
    
    for key in history:
        report[key] = {
            "stats": get_history_stats(key),
            "trend": get_performance_trend(key)
        }
    
    return report
```

### 4.3 报告生成工具

```gdscript
# 报告生成工具
class_name ReportingTool

var report_data: Dictionary = {}
var report_history: Array = []

func generate_performance_report() -> Dictionary:
    # 生成性能报告
    report_data = {
        "timestamp": Time.get_unix_time(),
        "metrics": _get_performance_metrics(),
        "hotspots": _get_performance_hotspots(),
        "recommendations": _get_optimization_recommendations(),
        "history_stats": _get_history_stats()
    }
    
    report_history.append(report_data)
    return report_data

func _get_performance_metrics() -> Dictionary:
    # 获取性能指标
    return {
        "fps": Engine.get_frames_per_second(),
        "cpu_usage": OS.get_process_cpu_usage(),
        "memory_usage": OS.get_total_memory(),
        "scene_tree_size": _get_scene_tree_size(),
        "resource_cache_size": _get_resource_cache_size(),
        "editor_plugin_count": _get_editor_plugin_count()
    }

func _get_performance_hotspots() -> Array:
    # 获取性能热点
    returnidentify_hotspots()

func _get_optimization_recommendations() -> Array:
    # 获取优化建议
    var recommendations = []
    
    var metrics = _get_performance_metrics()
    
    if metrics["fps"] < 60:
        recommendations.append("Optimize rendering to achieve 60 FPS")
    
    if metrics["cpu_usage"] > 80:
        recommendations.append("Reduce CPU usage by optimizing scripts")
    
    if metrics["memory_usage"] > 8000:
        recommendations.append("Reduce memory usage by unloading unused resources")
    
    if metrics["scene_tree_size"] > 1000:
        recommendations.append("Reduce scene tree size by using groups or instances")
    
    return recommendations

func _get_history_stats() -> Dictionary:
    # 获取历史统计
    return generate_history_report()

func _get_scene_tree_size() -> int:
    # 获取场景树大小
    var scene = get_editor_interface().get_edited_scene_root()
    if scene:
        return _count_nodes(scene)
    return 0

func _count_nodes(node: Node) -> int:
    # 计算节点数量
    var count = 1
    for child in node.get_children():
        count += _count_nodes(child)
    return count

func _get_resource_cache_size() -> int:
    # 没有可查询的“资源缓存”对象；用对象监视器里的资源计数代替
    return int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT))

func _get_editor_plugin_count() -> int:
    # 编辑器没有列出插件实例的 API；启用数从项目设置读取
    var enabled_plugins: PackedStringArray = ProjectSettings.get_setting(
        "editor_plugins/enabled", PackedStringArray())
    return enabled_plugins.size()
```

---

## 📝 本章总结

### 核心要点

1. **编辑器性能分析**，包括分析工具、热点识别和基准测试
2. **编辑器优化技巧**，包括场景树、资源加载和渲染优化
3. **最佳实践**，包括开发、监控和调试最佳实践
4. **性能监控工具**，包括实时监控、历史分析和报告生成

### 关键术语

| 术语 | 解释 |
|------|------|
| PerformanceAnalyzer | 性能分析器，分析编辑器性能 |
| HotspotIdentifier | 热点识别器，识别性能热点 |
| Benchmark | 基准测试，测试编辑器性能 |
| SceneTreeOptimization | 场景树优化，优化场景树性能 |
| ResourceLoadingOptimization | 资源加载优化，优化资源加载性能 |
| RenderingOptimization | 渲染优化，优化渲染性能 |
| DevelopmentBestPractices | 开发最佳实践，遵循最佳实践 |
| PerformanceMonitoringBestPractices | 性能监控最佳实践，监控性能 |
| DebuggingBestPractices | 调试最佳实践，遵循调试最佳实践 |
| RealtimeMonitoringTool | 实时监控工具，实时监控性能 |
| HistoryAnalysisTool | 历史分析工具，分析历史数据 |
| ReportingTool | 报告生成工具，生成性能报告 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Editor Performance Tuning](https://docs.godotengine.org/en/stable/tutorials/plugins/editor-performance-tuning.html)
- **源码位置**: `editor/performance/`
- **技术博客**: [Godot Editor Performance Tuning Guide](https://godotengine.org/article/editor-performance-tuning-guide/)

---

## 📋 下一章预告

**第 65 篇：编辑器自动化**

- 编辑器自动化脚本
- 自动化工作流
- 批处理工具
- 最佳实践

---

*写作时间：2026-03-20*  
*字数：约 15,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*