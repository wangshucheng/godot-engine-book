# 第 46 篇：资源系统

> **本卷定位**: 第八卷 编辑器扩展（6 篇）  
> **前置知识**: 第 55 章 GDScript 进阶  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

资源系统是 Godot 引擎的核心架构之一，所有游戏内容（场景、脚本、纹理、音频等）都以资源的形式存在。理解资源系统的工作原理对于高效开发 Godot 游戏至关重要。

本章将深入探讨资源系统的基础知识、资源管理、加载优化以及自定义资源创建。

---

## 🎯 学习目标

- 理解资源系统的基本概念
- 掌握资源加载和卸载
- 学会资源缓存管理
- 熟悉自定义资源创建
- 掌握资源系统优化

---

## 1. 资源系统基础

### 1.1 资源系统类型

```
资源系统类型:
┌─────────────────────────────────────────────────────────────┐
│                      资源系统类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 内置资源：引擎内置的资源类型                           │
│  2. 外部资源：文件系统中的资源文件                         │
│  3. 子资源：嵌入在其他资源中的资源                         │
│  4. 动态资源：运行时创建的资源                             │
│  5. 自定义资源：用户定义的资源类型                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 常见资源类型

```
常见资源类型:
┌─────────────────────────────────────────────────────────────┐
│                      常见资源类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PackedScene：场景资源                                  │
│  2. Script：脚本资源                                       │
│  3. Texture2D/Texture3D：纹理资源                          │
│  4. AudioStream：音频资源                                  │
│  5. Font：字体资源                                         │
│  6. Material：材质资源                                     │
│  7. Animation：动画资源                                    │
│  8. TileSet：瓦片集资源                                    │
│  9. StyleBox：样式框资源                                   │
│  10. Custom Resource：自定义资源                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 资源系统流程

```
资源系统处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      资源系统处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 资源导入（编辑器导入外部文件）                         │
│  2. 资源加载（运行时加载资源）                             │
│  3. 资源缓存（缓存已加载资源）                             │
│  4. 资源实例化（创建资源实例）                             │
│  5. 资源使用（在游戏 中使用资源）                          │
│  6. 资源卸载（释放不再使用的资源）                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 资源加载

### 2.1 基础资源加载

```gdscript
# 基础资源加载
class_name ResourceLoading

extends Node

# 同步加载
func load_resource_sync(path: String):
    var resource = load(path)
    return resource

# 异步加载
func load_resource_async(path: String, callback: Callable):
    var loader = ResourceLoader.load_threaded_request(path)
    await check_load_progress(loader)
    callback.call(loader)

func check_load_progress(loader: ResourceLoader) -> float:
    var progress = []
    var status = ResourceLoader.load_threaded_get_status(path, progress)
    
    match status:
        ResourceLoader.THREAD_LOAD_IN_PROGRESS:
            await get_tree().create_timer(0.1).timeout
            return check_load_progress(loader)
        ResourceLoader.THREAD_LOAD_LOADED:
            return 1.0
        _:
            return 0.0

# 批量加载
func load_resources_batch(paths: Array) -> Array:
    var resources = []
    for path in paths:
        var resource = load(path)
        resources.append(resource)
    return resources

# 后台加载
func load_resources_background(paths: Array):
    for path in paths:
        ResourceLoader.load_threaded_request(path)

# 检查加载状态
func check_load_status(path: String) -> int:
    var progress = []
    return ResourceLoader.load_threaded_get_status(path, progress)

# 获取加载结果
func get_loaded_resource(path: String):
    var progress = []
    var status = ResourceLoader.load_threaded_get_status(path, progress)
    if status == ResourceLoader.THREAD_LOAD_LOADED:
        return ResourceLoader.load_threaded_get(path)
    return null
```

### 2.2 资源缓存

```gdscript
# 资源缓存管理
class_name ResourceCache

extends Node

var cache: Dictionary = {}
var max_cache_size: int = 100

func load_and_cache(path: String):
    # 加载并缓存资源
    if cache.has(path):
        return cache[path]
    
    var resource = load(path)
    if resource:
        cache[path] = resource
        
        # 检查缓存大小
        if cache.size() > max_cache_size:
            _evict_oldest()
    
    return resource

func get_cached(path: String):
    # 获取缓存资源
    return cache.get(path, null)

func remove_from_cache(path: String):
    # 从缓存移除
    cache.erase(path)

func clear_cache():
    # 清空缓存
    cache.clear()

func _evict_oldest():
    # 移除最旧的缓存项
    if cache.size() > 0:
        var oldest_key = cache.keys()[0]
        cache.erase(oldest_key)

func get_cache_stats() -> Dictionary:
    # 获取缓存统计
    return {
        "size": cache.size(),
        "max_size": max_cache_size,
        "memory_usage": _calculate_memory_usage()
    }

func _calculate_memory_usage() -> int:
    # 计算内存使用（估算）
    var total = 0
    for path in cache:
        # 简单估算，实际应该更复杂
        total += 1024 * 1024  # 假设每个资源 1MB
    return total
```

### 2.3 资源预加载

```gdscript
# 资源预加载
class_name ResourcePreloader

extends Node

@export var preload_paths: Array[String] = []
var preloaded_resources: Dictionary = {}

func _ready():
    preload_all()

func preload_all():
    # 预加载所有资源
    for path in preload_paths:
        preload_resource(path)

func preload_resource(path: String):
    # 预加载单个资源
    if not preloaded_resources.has(path):
        var resource = load(path)
        if resource:
            preloaded_resources[path] = resource

func get_preloaded(path: String):
    # 获取预加载资源
    return preloaded_resources.get(path, null)

func is_preloaded(path: String) -> bool:
    # 检查是否已预加载
    return preloaded_resources.has(path)

func preload_scene(scene_path: String) -> PackedScene:
    # 预加载场景
    var scene = load(scene_path)
    if scene is PackedScene:
        preloaded_resources[scene_path] = scene
    return scene

func instantiate_preloaded_scene(scene_path: String) -> Node:
    # 实例化预加载场景
    var scene = get_preloaded(scene_path)
    if scene:
        return scene.instantiate()
    return null
```

---

## 3. 资源管理

### 3.1 资源管理器

```gdscript
# 资源管理器
class_name ResourceManager

extends Node

var loaded_resources: Dictionary = {}
var resource_usage: Dictionary = {}

func load_resource(path: String, use_cache: bool = true):
    # 加载资源
    if use_cache and loaded_resources.has(path):
        resource_usage[path] = resource_usage.get(path, 0) + 1
        return loaded_resources[path]
    
    var resource = load(path)
    if resource:
        loaded_resources[path] = resource
        resource_usage[path] = 1
    
    return resource

func unload_resource(path: String, force: bool = false):
    # 卸载资源
    if not loaded_resources.has(path):
        return
    
    resource_usage[path] = resource_usage.get(path, 1) - 1
    
    if force or resource_usage[path] <= 0:
        loaded_resources.erase(path)
        resource_usage.erase(path)

func unload_unused_resources():
    # 卸载未使用的资源
    var to_remove = []
    for path in resource_usage:
        if resource_usage[path] <= 0:
            to_remove.append(path)
    
    for path in to_remove:
        unload_resource(path, true)

func get_loaded_count() -> int:
    # 获取已加载数量
    return loaded_resources.size()

func get_total_usage() -> int:
    # 获取总使用次数
    var total = 0
    for count in resource_usage.values():
        total += count
    return total

func print_stats():
    # 打印统计
    print("Loaded resources: ", get_loaded_count())
    print("Total usage count: ", get_total_usage())
```

### 3.2 资源引用计数

```gdscript
# 资源引用计数
class_name ResourceRefCount

extends RefCounted

var resource_path: String
var reference_count: int = 0

func _init(path: String):
    resource_path = path

func add_ref():
    reference_count += 1

func remove_ref():
    reference_count -= 1

func get_ref_count() -> int:
    return reference_count

func can_unload() -> bool:
    return reference_count <= 0

# 资源引用管理器
class_name ResourceReferenceManager

extends Node

var references: Dictionary = {}

func acquire(path: String):
    # 获取资源引用
    if not references.has(path):
        var ref = ResourceRefCount.new(path)
        ref.add_ref()
        references[path] = ref
        load(path)
    else:
        references[path].add_ref()

func release(path: String):
    # 释放资源引用
    if references.has(path):
        var ref = references[path]
        ref.remove_ref()
        
        if ref.can_unload():
            references.erase(path)
            # 卸载资源
            # ResourceLoader._free(path)

func get_ref_count(path: String) -> int:
    if references.has(path):
        return references[path].get_ref_count()
    return 0
```

### 3.3 资源依赖管理

```gdscript
# 资源依赖管理
class_name ResourceDependencyManager

extends Node

var dependencies: Dictionary = {}  # resource -> [dependencies]
var dependents: Dictionary = {}  # resource -> [dependents]

func register_dependency(resource_path: String, depends_on: Array):
    # 注册依赖
    dependencies[resource_path] = depends_on
    
    for dep in depends_on:
        if not dependents.has(dep):
            dependents[dep] = []
        dependents[dep].append(resource_path)

func get_dependencies(resource_path: String) -> Array:
    # 获取依赖
    return dependencies.get(resource_path, [])

func get_dependents(resource_path: String) -> Array:
    # 获取依赖此资源的资源
    return dependents.get(resource_path, [])

func can_unload(resource_path: String) -> bool:
    # 检查是否可以卸载
    var deps = get_dependents(resource_path)
    for dep in deps:
        if is_loaded(dep):
            return false
    return true

func is_loaded(resource_path: String) -> bool:
    # 检查是否已加载
    return ResourceLoader.exists(resource_path)

func unload_with_dependencies(resource_path: String):
    # 卸载资源及其依赖
    var deps = get_dependencies(resource_path)
    for dep in deps:
        if can_unload(dep):
            unload_resource(dep)
    
    unload_resource(resource_path)

func unload_resource(path: String):
    # 卸载资源
    pass
```

---

## 4. 自定义资源

### 4.1 创建自定义资源

```gdscript
# 自定义资源
class_name CustomResource

extends Resource

class_name ItemData

@export var item_name: String
@export var item_id: int
@export var item_type: String
@export var stack_size: int = 1
@export var icon: Texture2D
@export var description: String

func _init(name: String = "", id: int = 0, type: String = ""):
    item_name = name
    item_id = id
    item_type = type

func get_display_name() -> String:
    return item_name

func get_icon() -> Texture2D:
    return icon

func is_stackable() -> bool:
    return stack_size > 1

func get_max_stack() -> int:
    return stack_size
```

### 4.2 资源数组

```gdscript
# 资源数组
class_name ResourceArray

extends Resource

class_name ItemDatabase

@export var items: Array[ItemData] = []

func get_item_by_id(id: int) -> ItemData:
    for item in items:
        if item.item_id == id:
            return item
    return null

func get_item_by_name(name: String) -> ItemData:
    for item in items:
        if item.item_name == name:
            return item
    return null

func add_item(item: ItemData):
    items.append(item)

func remove_item(item: ItemData):
    items.erase(item)

func get_item_count() -> int:
    return items.size()

func get_all_items() -> Array:
    return items
```

### 4.3 资源导出导入

```gdscript
# 资源导出导入
class_name ResourceIO

extends Node

func export_resource(resource: Resource, path: String) -> bool:
    # 导出资源到文件
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file:
        var data = var_to_bytes(resource)
        file.store_buffer(data)
        file.close()
        return true
    return false

func import_resource(path: String) -> Resource:
    # 从文件导入资源
    var file = FileAccess.open(path, FileAccess.READ)
    if file:
        var data = file.get_buffer(file.get_length())
        var resource = bytes_to_var(data)
        file.close()
        return resource
    return null

func export_to_json(resource: Resource, path: String) -> bool:
    # 导出为 JSON
    var data = _resource_to_dict(resource)
    var json_string = JSON.stringify(data, "  ")
    
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file:
        file.store_string(json_string)
        file.close()
        return true
    return false

func import_from_json(path: String) -> Dictionary:
    # 从 JSON 导入
    var file = FileAccess.open(path, FileAccess.READ)
    if file:
        var text = file.get_as_text()
        file.close()
        
        var json = JSON.new()
        var error = json.parse(text)
        if error == OK:
            return json.data
    
    return {}

func _resource_to_dict(resource: Resource) -> Dictionary:
    # 资源转字典
    var data = {}
    for property in resource.get_property_list():
        var name = property.name
        if not name.begins_with("_"):
            data[name] = resource.get(name)
    return data
```

---

## 5. 资源系统优化

### 5.1 加载优化

```gdscript
# 加载优化
class_name ResourceLoadOptimization

extends Node

# 分帧加载
func load_resources_frame_by_frame(paths: Array, callback: Callable):
    var index = 0
    
    func load_next():
        if index < paths.size():
            load(paths[index])
            index += 1
            await get_tree().process_frame
            load_next.call_deferred()
        else:
            callback.call()
    
    load_next.call_deferred()

# 优先级加载
func load_by_priority(priority_queue: Array):
    # priority_queue: [{path: String, priority: int}]
    priority_queue.sort_custom(func(a, b): return a.priority > b.priority)
    
    for item in priority_queue:
        load(item.path)

# 按需加载
func load_on_demand(path: String):
    if not ResourceLoader.has_cached(path):
        load(path)

# 预加载关键资源
func preload_critical_resources(paths: Array):
    for path in paths:
        load(path)
```

### 5.2 内存优化

```gdscript
# 内存优化
class_name ResourceMemoryOptimization

extends Node

func unload_unused_textures():
    # 卸载未使用的纹理
    pass

func compress_resources():
    # 压缩资源
    pass

func use_resource_sharing():
    # 使用资源共享
    pass

func limit_cache_size(max_size_mb: int):
    # 限制缓存大小
    pass

func force_gc():
    # 强制垃圾回收
    for i in range(3):
        await get_tree().process_frame
```

### 5.3 性能监控

```gdscript
# 性能监控
class_name ResourcePerformanceMonitor

extends Node

var load_times: Dictionary = {}

func start_load_timer(path: String):
    load_times[path] = Time.get_ticks_msec()

func end_load_timer(path: String) -> float:
    if load_times.has(path):
        var elapsed = Time.get_ticks_msec() - load_times[path]
        load_times.erase(path)
        return elapsed
    return 0.0

func log_load_time(path: String, time_ms: float):
    print("Loaded ", path, " in ", time_ms, " ms")

func get_average_load_time() -> float:
    # 获取平均加载时间
    pass
```

---

## 6. 实践：完整资源系统

### 6.1 游戏资源管理器

```gdscript
# 游戏资源管理器
class_name GameResourceManager

extends Node

var resource_manager: ResourceManager
var preloader: ResourcePreloader
var cache: ResourceCache

func _ready():
    resource_manager = ResourceManager.new()
    add_child(resource_manager)
    
    preloader = ResourcePreloader.new()
    add_child(preloader)
    
    cache = ResourceCache.new()
    add_child(cache)

func load_game_resource(path: String):
    return resource_manager.load_resource(path)

func preload_game_resources(paths: Array):
    preloader.preload_paths = paths
    preloader.preload_all()

func get_cached_resource(path: String):
    return cache.get_cached(path)

func unload_game_resource(path: String):
    resource_manager.unload_resource(path)

func cleanup():
    resource_manager.unload_unused_resources()
    cache.clear_cache()
```

### 6.2 场景资源管理

```gdscript
# 场景资源管理
class_name SceneResourceManager

extends Node

var scene_cache: Dictionary = {}

func preload_scene(path: String):
    if not scene_cache.has(path):
        var scene = load(path)
        if scene is PackedScene:
            scene_cache[path] = scene

func instantiate_scene(path: String, parent: Node = null) -> Node:
    var scene = scene_cache.get(path)
    if not scene:
        scene = load(path)
        scene_cache[path] = scene
    
    if scene:
        var instance = scene.instantiate()
        if parent:
            parent.add_child(instance)
        return instance
    return null

func unload_scene(path: String):
    scene_cache.erase(path)

func get_loaded_scenes() -> Array:
    return scene_cache.keys()
```

### 6.3 完整资源系统

```gdscript
# 完整资源系统
class_name FullResourceSystem

extends Node

var game_resources: GameResourceManager
var scene_resources: SceneResourceManager

func _ready():
    game_resources = GameResourceManager.new()
    add_child(game_resources)
    
    scene_resources = SceneResourceManager.new()
    add_child(scene_resources)

func initialize():
    # 初始化资源系统
    preload_critical_resources()

func preload_critical_resources():
    # 预加载关键资源
    var critical_paths = [
        "res://scenes/main_menu.tscn",
        "res://scenes/game.tscn",
        "res://resources/player_data.tres"
    ]
    game_resources.preload_game_resources(critical_paths)

func load_scene(path: String, parent: Node = null) -> Node:
    return scene_resources.instantiate_scene(path, parent)

func load_resource(path: String):
    return game_resources.load_game_resource(path)

func cleanup():
    game_resources.cleanup()
    scene_resources.scene_cache.clear()

func get_stats() -> Dictionary:
    return {
        "cached_resources": game_resources.cache.cache.size(),
        "loaded_scenes": scene_resources.get_loaded_scenes().size()
    }
```

---

## 📝 本章总结

### 核心要点

1. **资源加载有同步和异步**，异步避免卡顿
2. **资源缓存提升性能**，但要注意内存
3. **引用计数管理生命周期**，避免内存泄漏
4. **自定义资源扩展功能**，创建游戏特定资源
5. **资源优化确保流畅**，加载、内存、性能优化

### 关键术语

| 术语 | 解释 |
|------|------|
| Resource | 资源，Godot 内容的基本单位 |
| Cache | 缓存，存储已加载资源 |
| Preload | 预加载，提前加载资源 |
| Reference Count | 引用计数，跟踪资源使用 |
| Dependency | 依赖，资源间的依赖关系 |
| Serialization | 序列化，资源存储和加载 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Resources](https://docs.godotengine.org/en/stable/tutorials/scripting/resources.html)
- **源码位置**: `core/io/`
- **技术博客**: [Godot Resource System Guide](https://godotengine.org/article/resource-system-guide/)

---

## 📋 下一章预告

**第 57 篇：编辑器基础**

- 编辑器架构
- 编辑器插件
- 自定义检查器
- 编辑器优化

---

*写作时间：2026-03-20*  
*字数：约 12,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 22:00*