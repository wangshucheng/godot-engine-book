# 第 42 篇：粒子系统

> **本卷定位**: 第四卷 动画系统（扩展篇）  
> **前置知识**: 第 42 章 骨骼动画  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

动画性能优化是游戏开发中确保流畅体验的关键环节。复杂的角色动画系统可能占用大量 CPU 和 GPU 资源，尤其是在多角色场景中。通过合理的优化策略，可以在保持动画质量的同时，显著提升性能表现。

本章将深入探讨动画压缩、GPU 加速、动画 LOD、批量更新等核心技术。

---

## 🎯 学习目标

- 理解动画性能瓶颈
- 掌握动画压缩技术
- 学会 GPU 加速动画
- 熟悉动画 LOD 系统
- 掌握批量动画更新
- 实施最佳实践

---

## 1. 动画性能瓶颈分析

### 1.1 性能指标

```
动画性能关键指标:
┌─────────────────────────────────────────────────────────────┐
│ 指标              │ 描述                  │ 优化目标        │
├─────────────────────────────────────────────────────────────┤
│ CPU 时间/角色      │ 每角色动画更新耗时    │ <0.5ms         │
│ 骨骼数量          │ 每角色骨骼数          │ <70 骨          │
│ 混合节点数        │ 动画树节点数量        │ <20 个          │
│ IK 链数量         │ 同时运行的 IK 链       │ <4 条           │
│ 蒙皮顶点数        │ 受骨骼影响的顶点数    │ <5000          │
│ 内存占用          │ 动画资源内存          │ <10MB/角色     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 性能分析工具

```gdscript
# 动画性能分析器
class_name AnimationProfiler

extends Node

var profile_data: Dictionary = {}
var frame_count: int = 0

func _ready():
    set_process(true)

func _process(delta):
    frame_count += 1
    
    if frame_count >= 60:
        _print_statistics()
        frame_count = 0
        profile_data.clear()

func start_profile(category: String):
    profile_data[category] = {
        "start": Time.get_ticks_usec(),
        "count": 0
    }

func end_profile(category: String):
    if profile_data.has(category):
        var elapsed = Time.get_ticks_usec() - profile_data[category]["start"]
        profile_data[category]["elapsed"] = elapsed
        profile_data[category]["count"] += 1

func _print_statistics():
    print("\n=== Animation Performance ===")
    for category in profile_data:
        var data = profile_data[category]
        var avg = data.get("elapsed", 0) / max(1, data["count"])
        print("%s: %.2f μs (calls: %d)" % [category, avg, data["count"]])
    
    # 计算 FPS 影响
    var total_time = 0.0
    for category in profile_data:
        total_time += profile_data[category].get("elapsed", 0)
    
    var fps_impact = (total_time / 16666.0) * 100
    print("Total FPS Impact: %.2f%%" % fps_impact)

# 使用示例
func update_animation():
    $AnimationProfiler.start_profile("skeleton_update")
    _update_skeletons()
    $AnimationProfiler.end_profile("skeleton_update")
    
    $AnimationProfiler.start_profile("blend_tree")
    _update_blend_trees()
    $AnimationProfiler.end_profile("blend_tree")
```

---

## 2. 动画压缩技术

### 2.1 关键帧压缩

```
压缩方法对比:
┌─────────────────────────────────────────────────────────────┐
│ 方法              │ 压缩率  │ 质量损失 │ 适用场景          │
├─────────────────────────────────────────────────────────────┤
│ 关键帧移除        │ 30-50%  │ 低       │ 通用              │
│ 曲线简化          │ 40-60%  │ 中       │ 平滑动画          │
│ 量化压缩          │ 50-70%  │ 中       │ 网络传输          │
│ 预测编码          │ 60-80%  │ 低       │ 序列动画          │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 关键帧压缩器
class_name AnimationKeyframeCompressor

# 压缩动画资源
static func compress_animation(anim: Animation, threshold: float = 0.001) -> Animation:
    var compressed = anim.duplicate()
    
    for track_idx in range(anim.get_track_count()):
        var track = anim.get_track(track_idx)
        
        if track.type == Animation.TYPE_VALUE:
            _compress_value_track(compressed, track_idx, threshold)
        elif track.type == Animation.TYPE_ROTATION:
            _compress_rotation_track(compressed, track_idx, threshold)
    
    return compressed

static func _compress_value_track(anim: Animation, track_idx: int, threshold: float):
    var key_count = anim.track_get_key_count(track_idx)
    
    if key_count < 3:
        return  # 关键帧太少，不压缩
    
    var keys_to_remove = []
    
    # 检测可移除的关键帧
    for i in range(1, key_count - 1):
        var prev_key = anim.track_get_key_value(track_idx, i - 1)
        var curr_key = anim.track_get_key_value(track_idx, i)
        var next_key = anim.track_get_key_key(track_idx, i + 1)
        
        # 线性插值误差检测
        var interpolated = prev_key.lerp(next_key, 0.5)
        var error = interpolated.distance_to(curr_key)
        
        if error < threshold:
            keys_to_remove.append(i)
    
    # 从后向前移除（避免索引问题）
    for i in range(keys_to_remove.size() - 1, -1, -1):
        anim.track_remove_key(track_idx, keys_to_remove[i])

# 使用示例
func load_and_compress_animation(path: String):
    var anim = load(path) as Animation
    var compressed = AnimationKeyframeCompressor.compress_animation(anim, 0.001)
    
    print("Original keys: ", anim.get_track_key_count(0))
    print("Compressed keys: ", compressed.get_track_key_count(0))
    print("Compression ratio: ", (1.0 - float(compressed.get_track_key_count(0)) / anim.get_track_key_count(0)) * 100, "%")
```

### 2.2 骨骼数据量化

```gdscript
# 骨骼变换量化
class_name BoneTransformQuantizer

@export var position_precision: int = 1000  # 位置精度
@export var rotation_precision: int = 1000  # 旋转精度
@export var scale_precision: int = 1000     # 缩放精度

# 量化变换
func quantize_transform(transform: Transform3D) -> PackedInt32Array:
    var quantized = PackedInt32Array()
    
    # 量化位置
    quantized.append(int(transform.origin.x * position_precision))
    quantized.append(int(transform.origin.y * position_precision))
    quantized.append(int(transform.origin.z * position_precision))
    
    # 量化旋转（四元数）
    var quat = transform.basis.get_rotation_quaternion()
    quantized.append(int(quat.x * rotation_precision))
    quantized.append(int(quat.y * rotation_precision))
    quantized.append(int(quat.z * rotation_precision))
    quantized.append(int(quat.w * rotation_precision))
    
    # 量化缩放
    quantized.append(int(transform.basis.get_scale().x * scale_precision))
    quantized.append(int(transform.basis.get_scale().y * scale_precision))
    quantized.append(int(transform.basis.get_scale().z * scale_precision))
    
    return quantized

# 反量化变换
func dequantize_transform(quantized: PackedInt32Array) -> Transform3D:
    var pos = Vector3(
        quantized[0] / float(position_precision),
        quantized[1] / float(position_precision),
        quantized[2] / float(position_precision)
    )
    
    var quat = Quaternion(
        quantized[3] / float(rotation_precision),
        quantized[4] / float(rotation_precision),
        quantized[5] / float(rotation_precision),
        quantized[6] / float(rotation_precision)
    )
    
    var scale = Vector3(
        quantized[7] / float(scale_precision),
        quantized[8] / float(scale_precision),
        quantized[9] / float(scale_precision)
    )
    
    return Transform3D(Basis(quat, scale), pos)

# 内存节省计算
func calculate_memory_savings(bone_count: int, animation_count: int) -> Dictionary:
    var original_size = bone_count * animation_count * 12 * 4  # 12 个 float，每个 4 字节
    var compressed_size = bone_count * animation_count * 10 * 4  # 10 个 int，每个 4 字节
    
    return {
        "original_mb": original_size / (1024.0 * 1024.0),
        "compressed_mb": compressed_size / (1024.0 * 1024.0),
        "savings_percent": (1.0 - compressed_size / float(original_size)) * 100
    }
```

---

## 3. GPU 加速动画

### 3.1 GPU 蒙皮

```
GPU 蒙皮优势:
┌─────────────────────────────────────────────────────────────┐
│ CPU 蒙皮 vs GPU 蒙皮                                         │
├─────────────────────────────────────────────────────────────┤
│ CPU 蒙皮:                                                   │
│ - 每帧计算顶点变换                                          │
│ - 占用 CPU 资源                                              │
│ - 适合少量角色                                              │
│                                                             │
│ GPU 蒙皮:                                                   │
│ - 顶点变换在 GPU 进行                                        │
│ - 释放 CPU 资源                                              │
│ - 适合大量角色（100+）                                      │
│ - 需要 Shader 支持                                           │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# GPU 蒙皮设置
func setup_gpu_skinning(mesh_instance: MeshInstance3D):
    # 启用 GPU 蒙皮
    mesh_instance.skinning = MeshInstance3D.SKINNING_GPU
    
    # 设置骨骼纹理
    var skeleton = mesh_instance.skeleton
    if skeleton:
        _update_bone_texture(skeleton)

func _update_bone_texture(skeleton: Skeleton3D):
    var bone_count = skeleton.get_bone_count()
    
    # 创建骨骼数据纹理
    var bone_data = PackedFloat32Array()
    
    for i in range(bone_count):
        var pose = skeleton.get_bone_global_pose(i)
        
        # 添加变换矩阵（4x4）
        for j in range(4):
            for k in range(4):
                bone_data.append(pose[j][k])
    
    # 创建纹理
    var texture = ImageTexture.create_from_image(
        Image.create_from_data(
            4, bone_count, false, Image.FORMAT_RGBAF, bone_data
        )
    )
    
    # 应用到材质
    _apply_bone_texture_to_materials(texture)
```

### 3.2 计算着色器动画

```gdscript
# 使用计算着色器更新骨骼
class_name ComputeShaderAnimation

extends Node

@compute_shader("res://shaders/bone_update.cs")
var bone_update_shader: ComputeShader

@export var bone_buffer: RID
@export var thread_count: int = 64

func _ready():
    _setup_compute_pipeline()

func _setup_compute_pipeline():
    # 创建计算管线
    var pipeline = RenderingServer.compute_pipeline_create()
    RenderingServer.compute_pipeline_set_compute_shader(pipeline, bone_update_shader.get_rid())
    
    # 创建缓冲区
    bone_buffer = RenderingServer.storage_buffer_create(
        1024 * 64,  # 最大 64 个骨骼
        PackedByteArray()
    )

func update_bones(delta: float, bones: Array):
    # 更新骨骼数据到缓冲区
    _upload_bone_data(bones)
    
    # 分发计算任务
    var dispatch_count = (bones.size() + thread_count - 1) / thread_count
    RenderingServer.compute_dispatch(pipeline, dispatch_count, 1, 1)
    
    # 读取结果
    _download_bone_data()

func _upload_bone_data(bones: Array):
    var data = PackedByteArray()
    for bone in bones:
        # 序列化骨骼数据
        data.append_array(_serialize_bone(bone))
    
    RenderingServer.buffer_update(bone_buffer, 0, data.size(), data)
```

---

## 4. 动画 LOD 系统

### 4.1 LOD 层级设计

```
动画 LOD 层级:
┌─────────────────────────────────────────────────────────────┐
│ LOD 级别  │ 距离     │ 更新频率 │ 骨骼数 │ 混合复杂度 │
├─────────────────────────────────────────────────────────────┤
│ LOD 0    │ 0-20m    │ 每帧     │ 全部   │ 完整        │
│ LOD 1    │ 20-50m   │ 每 2 帧    │ 80%    │ 简化        │
│ LOD 2    │ 50-100m  │ 每 4 帧    │ 50%    │ 最小        │
│ LOD 3    │ 100m+    │ 暂停     │ 0%     │ 禁用        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 LOD 实现

```gdscript
# 动画 LOD 管理器
class_name AnimationLODManager

extends Node

@export var lod_distances: Array[float] = [20.0, 50.0, 100.0]
@export var player: Node3D

var animated_characters: Array = []

func _ready():
    set_process(true)

func register_character(character: Node3D):
    animated_characters.append({
        "node": character,
        "current_lod": 0,
        "update_counter": 0
    })

func _process(delta):
    for char_data in animated_characters:
        _update_character_lod(char_data, delta)

func _update_character_lod(char_data: Dictionary, delta):
    var character = char_data["node"]
    var distance = character.global_transform.origin.distance_to(player.global_transform.origin)
    
    var new_lod = _calculate_lod(distance)
    
    if new_lod != char_data["current_lod"]:
        _apply_lod(character, new_lod)
        char_data["current_lod"] = new_lod
    
    # 根据 LOD 决定是否更新
    if _should_update(char_data["current_lod"], char_data["update_counter"]):
        _update_animation(character, delta)
    
    char_data["update_counter"] += 1

func _calculate_lod(distance: float) -> int:
    if distance < lod_distances[0]:
        return 0
    elif distance < lod_distances[1]:
        return 1
    elif distance < lod_distances[2]:
        return 2
    else:
        return 3

func _should_update(lod: int, counter: int) -> bool:
    match lod:
        0: return true          # 每帧更新
        1: return counter % 2 == 0  # 每 2 帧
        2: return counter % 4 == 0  # 每 4 帧
        3: return false         # 暂停
    return true

func _apply_lod(character: Node3D, lod: int):
    var anim_tree = character.get_node_or_null("AnimationTree")
    if not anim_tree:
        return
    
    match lod:
        0:
            anim_tree.set_process(true)
            _enable_all_bones(character)
        1:
            _simplify_blend_tree(anim_tree)
        2:
            _disable_expressions(character)
        3:
            anim_tree.set_process(false)

func _enable_all_bones(character: Node3D):
    # 启用所有骨骼
    pass

func _simplify_blend_tree(anim_tree: AnimationTree):
    # 简化混合树
    pass

func _disable_expressions(character: Node3D):
    # 禁用表情动画
    pass
```

---

## 5. 批量动画更新

### 5.1 动画更新批处理

```gdscript
# 批量动画更新器
class_name BatchAnimationUpdater

extends Node

@export var batch_size: int = 10
@export var update_interval: float = 0.016  # 60 FPS

var character_queue: Array = []
var current_batch: int = 0

func _ready():
    set_process(true)

func add_character(character: Node3D):
    character_queue.append(character)

func remove_character(character: Node3D):
    character_queue.erase(character)

func _process(delta):
    var start_time = Time.get_ticks_usec()
    var processed = 0
    
    # 处理一批角色
    while processed < batch_size and current_batch < character_queue.size():
        var character = character_queue[current_batch]
        
        if is_instance_valid(character) and character.is_visible_in_tree():
            _update_animation(character, delta)
        
        processed += 1
        current_batch += 1
        
        if current_batch >= character_queue.size():
            current_batch = 0  # 循环
        
        # 检查时间预算
        if Time.get_ticks_usec() - start_time > update_interval * 1000000:
            break

func _update_animation(character: Node3D, delta):
    var anim_tree = character.get_node_or_null("AnimationTree")
    if anim_tree and anim_tree.active:
        # 手动触发动画更新
        anim_tree.advance(delta)
```

### 5.2 动画缓存

```gdscript
# 动画状态缓存
class_name AnimationStateCache

extends Node

var cache: Dictionary = {}
var max_cache_size: int = 100
var cache_ttl: float = 5.0  # 缓存生存时间（秒）

func cache_pose(character_id: String, pose: Dictionary):
    cache[character_id] = {
        "pose": pose,
        "timestamp": Time.get_ticks_msec(),
        "hits": 0
    }
    
    # 清理过期缓存
    _cleanup_cache()

func get_cached_pose(character_id: String) -> Dictionary:
    if cache.has(character_id):
        var entry = cache[character_id]
        
        # 检查是否过期
        var age = Time.get_ticks_msec() - entry["timestamp"]
        if age < cache_ttl * 1000:
            entry["hits"] += 1
            return entry["pose"]
        else:
            cache.erase(character_id)
    
    return {}

func _cleanup_cache():
    if cache.size() <= max_cache_size:
        return
    
    # 移除最少使用的缓存
    var sorted = cache.keys()
    sorted.sort_custom(func(a, b): return cache[a]["hits"] < cache[b]["hits"])
    
    while cache.size() > max_cache_size:
        cache.erase(sorted[0])
```

---

## 📝 本章总结

### 核心要点

1. **性能分析是优化的基础**，先测量再优化
2. **动画压缩减少内存占用**，关键帧移除最有效
3. **GPU 蒙皮释放 CPU 资源**，适合大量角色
4. **动画 LOD 根据距离优化**，显著降低负载
5. **批量更新平滑性能峰值**，避免卡顿

### 性能优化清单

```
✅ 动画优化清单:
□ 启用 GPU 蒙皮（100+ 角色）
□ 实施动画 LOD
□ 压缩动画关键帧
□ 批量更新动画
□ 缓存动画状态
□ 禁用不可见角色动画
□ 简化远处角色混合树
□ 限制 IK 链数量
```

---

*写作时间：2026-03-21*  
*字数：约 6,000 字*  
*状态：✅ 完成*
