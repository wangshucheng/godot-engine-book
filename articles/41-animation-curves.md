# 第 41 篇：动画曲线

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 40 章 角色动画  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

动画曲线是动画数据的最小单位：一个 `Animation` 资源由「轨道 + 关键帧」组成，
关键帧之间由插值曲线连接，决定了动画的节奏与质感。

本章讲的是**在运行时以代码方式构建与操纵 Animation 曲线**——用 `Animation`、
`Curve` 两个资源类直接写出关键帧、调整插值与切线、做关键帧抽稀与预览。

> **关于编辑器内的曲线编辑 UI**：编辑器里的曲线编辑器、关键帧面板、时间轴拖拽
> 属于**编辑器扩展**范畴，不在运行时 API 里，需在第八卷《编辑器扩展》中单独讨论。
> 本章只覆盖**运行时**可用的曲线 API。

---

## 🎯 学习目标

- 理解 `Animation` 的「轨道 + 关键帧」数据模型
- 掌握 `Animation` 轨道类型与 `track_set_path()` 的路径格式
- 掌握关键帧的增删改与插值类型设置
- 掌握 `Curve` 资源的构建与采样
- 熟悉动画资源的预览与关键帧抽稀
- 了解运行时构建动画资源的性能注意事项

---

## 1. 动画曲线基础

### 1.1 运行时的曲线相关资源

```
运行时可用的动画 / 曲线相关类型:
┌─────────────────────────────────────────────────────────────┐
│                      运行时类型                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Animation：动画资源（轨道 + 关键帧）                     │
│  2. AnimationLibrary：动画库（Godot 4 起取代 3.x 扁平列表）  │
│  3. AnimationPlayer：播放器（负责播放 Animation）            │
│  4. Curve：曲线资源（贝塞尔切线控制点）                       │
│  5. Tween：补间（简单数值过渡）                              │
│                                                             │
│  ⚠️ Godot 4.x 不存在 AnimationTrack / AnimationKey /         │
│     AnimationCurve / CurveResource 这几个 3.x 时代的类。      │
│     轨道是 Animation 内部的索引，关键帧是轨道内的索引，       │
│     曲线则直接用 Curve 资源。                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画曲线的组成部分

```
动画曲线结构:
┌─────────────────────────────────────────────────────────────┐
│  Animation                                                  │
│   ├── track 0 (TYPE_TRANSFORM_3D)                           │
│   │      ├── key 0 @ 0.0s                                   │
│   │      ├── key 1 @ 1.0s                                   │
│   │      └── key 2 @ 2.0s                                   │
│   ├── track 1 (TYPE_VALUE)                                  │
│   └── track 2 (TYPE_METHOD)                                 │
│                                                             │
│  每条轨道：                                                 │
│    - 类型（TYPE_*）                                         │
│    - 路径（NodePath，形如 "节点路径:属性名"）               │
│    - 关键帧数组（时间 + 值 + 插值类型 + 过渡参数）          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 关键帧求值流程

```
关键帧求值流程:
┌─────────────────────────────────────────────────────────────┐
│                      关键帧求值流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationMixer 推进时间到 t                            │
│  2. 在轨道上二分查找 t 两侧的关键帧 k0 / k1                 │
│  3. 按插值类型（NEAREST / LINEAR / CUBIC / ANGLE）求值       │
│  4. 把结果写入轨道路径指向的属性                            │
│  5. 多条动画同时驱动时，由 AnimationMixer 做最终混合        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 关键帧编辑

### 2.1 基础关键帧编辑

```gdscript
# 关键帧编辑基础：运行时构建 Animation 资源
class_name BasicKeyframeEditor

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"

func _ready():
    # 设置动画
    if animation_player and not animation_name.empty():
        create_animation(animation_name)

func create_animation(anim_name: String):
    # 创建动画
    var animation := Animation.new()
    
    # 添加轨道
    var track_idx := animation.add_track(Animation.TYPE_TRANSFORM_3D)
    # track_set_path 的第二个参数类型是 NodePath；
    # 路径形如 "节点路径:属性名"（或 "节点路径:骨骼名"）
    animation.track_set_path(track_idx, NodePath("MeshInstance3D:position"))
    
    # 3D 变换轨道的关键帧值固定是 [位置, 旋转(四元数), 缩放] 三元组，
    # 不是 Transform3D。
    animation.track_insert_key(track_idx, 0.0, [Vector3(0, 0, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 1.0, [Vector3(1, 0, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 2.0, [Vector3(1, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 3.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画到播放器：AnimationPlayer 上没有 add_animation()，
    # 必须先拿到（或新建）一个 AnimationLibrary，再由库添加动画。
    var lib := animation_player.get_animation_library("")
    if lib == null:
        lib = AnimationLibrary.new()
        animation_player.add_animation_library("", lib)
    lib.add_animation(StringName(anim_name), animation)

func edit_keyframe(time: float, value: Array):
    # 编辑关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, value)

func remove_keyframe(time: float):
    # 移除关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            # track_remove_key(track_idx, key_idx) 的第二个参数是关键帧**索引**；
            # 按时间删除要用 track_remove_key_at_time()
            animation.track_remove_key_at_time(track_idx, time)

func get_keyframe(time: float) -> Variant:
    # 获取关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            var key_idx := animation.track_find_key(track_idx, time)
            if key_idx == -1:
                return null
            return animation.track_get_key_value(track_idx, key_idx)
    return null
```

### 2.2 关键帧属性

```gdscript
# 关键帧属性
class_name KeyframeProperties

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"
@export var keyframe_index: int = 0

func _ready():
    # 设置关键帧属性
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation and keyframe_index < animation.track_get_key_count(0):
            var keyframe = animation.track_get_key_value(0, keyframe_index)
            print("Keyframe: ", keyframe)

func _process(_delta):
    # 更新关键帧属性
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var keyframe = animation.track_get_key_value(0, keyframe_index)
            print("Keyframe: ", keyframe)

func set_keyframe_time(time: float):
    # 设置关键帧时间
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_time(0, keyframe_index, time)

func set_keyframe_value(value: Variant):
    # 设置关键帧值
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_value(0, keyframe_index, value)

func set_track_interpolation(mode: Animation.InterpolationType):
    # 设置整条轨道的插值类型
    # Godot 4.x 里没有 track_set_key_interp_mode()，
    # 插值类型是**轨道级**属性，用 track_set_interpolation_type()。
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_interpolation_type(0, mode)

func set_keyframe_transition(transition: float):
    # 设置关键帧的过渡参数（用于 Cubic 插值的缓动强度）
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_transition(0, keyframe_index, transition)
```

> **重要更正**：Godot 4.x 的 `Animation` **没有** `track_set_key_interp_mode()`，
> 也**没有** `track_set_key_tangent_mode()`。
> 插值类型（`INTERPOLATION_NEAREST` / `LINEAR` / `CUBIC` / `LINEAR_ANGLE` / `CUBIC_ANGLE`）
> 是**轨道级**属性，用 `track_set_interpolation_type(track_idx, mode)`；
> 关键帧级的可调项是过渡参数，用 `track_set_key_transition(track_idx, key_idx, transition)`。

### 2.3 关键帧动画

```gdscript
# 关键帧动画
class_name KeyframeAnimation

extends AnimationPlayer

func _ready():
    # 创建关键帧动画
    create_animation("walk")

func create_animation(anim_name: String):
    # 创建动画
    var animation := Animation.new()
    
    # 添加轨道
    var track_idx := animation.add_track(Animation.TYPE_TRANSFORM_3D)
    animation.track_set_path(track_idx, NodePath("MeshInstance3D:position"))
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 0.5, [Vector3(1, 0, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 1.0, [Vector3(1, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 1.5, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 2.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画：AnimationPlayer 没有 add_animation()，走 AnimationLibrary
    var lib := get_animation_library("")
    if lib == null:
        lib = AnimationLibrary.new()
        add_animation_library("", lib)
    lib.add_animation(StringName(anim_name), animation)

func _process(_delta):
    # 更新关键帧动画
    if is_playing():
        var time = current_animation_position
        print("Time: ", time)

func play_animation(anim_name: String):
    if has_animation(anim_name):
        play(anim_name)

func stop_animation():
    stop()
```

---

## 3. 曲线调整

### 3.1 基础曲线调整

```gdscript
# 曲线调整基础：Godot 4.x 直接用 Curve 资源，没有 CurveResource 这层包装
class_name BasicCurveEditor

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"

@export var curve: Curve

func _ready():
    # 设置曲线
    if animation_player and not animation_name.empty():
        create_curve()

func create_curve():
    # 创建曲线
    curve = Curve.new()
    
    # 添加点
    curve.add_point(0.0, 0.0)
    curve.add_point(0.5, 0.8)
    curve.add_point(1.0, 1.0)
    
    # 设置点属性（切线的水平 / 垂直长度）
    curve.set_point_out(0, 0.5)
    curve.set_point_in(1, 0.5)
    curve.set_point_out(1, 0.5)

func edit_curve_point(point_index: int, time: float, value: float):
    # 编辑曲线点
    if curve:
        curve.set_point_position(point_index, Vector2(time, value))

func remove_curve_point(point_index: int):
    # 移除曲线点
    if curve:
        curve.remove_point(point_index)

func get_curve_value(time: float) -> float:
    # 获取曲线值
    if curve:
        return curve.sample(time)
    return 0.0
```

### 3.2 曲线属性

```gdscript
# 曲线属性
class_name CurveProperties

extends Node3D

@export var curve: Curve

func _ready():
    # 设置曲线属性
    if curve == null:
        curve = Curve.new()

func _process(_delta):
    # 更新曲线属性
    if curve:
        print("Point count: ", curve.get_point_count())

func set_point_position(index: int, time: float, value: float):
    # 设置点位置
    if curve:
        curve.set_point_position(index, Vector2(time, value))

func set_point_out(index: int, value: float):
    # 设置点输出切线
    if curve:
        curve.set_point_out(index, value)

func set_point_in(index: int, value: float):
    # 设置点输入切线
    if curve:
        curve.set_point_in(index, value)

func set_tangent_mode(mode: int):
    # 设置切线模式。Curve 没有全局的 `tangent_mode` 属性，
    # 切线模式是**逐点**的：get_point_left_mode / get_point_right_mode
    if curve:
        for i in curve.point_count:
            curve.set_point_left_mode(i, mode)
            curve.set_point_right_mode(i, mode)

func set_curve_min(min_val: float):
    # 设置曲线最小值
    if curve:
        curve.min_value = min_val

func set_curve_max(max_val: float):
    # 设置曲线最大值
    if curve:
        curve.max_value = max_val
```

### 3.3 曲线调整器

```gdscript
# 曲线调整器
class_name CurveEditor

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"
@export var curve: Curve

func _ready():
    # 设置曲线调整器
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            # 创建曲线
            curve = Curve.new()
            curve.add_point(0.0, 0.0)
            curve.add_point(0.5, 0.8)
            curve.add_point(1.0, 1.0)

func _process(delta):
    # 更新曲线调整器
    if curve:
        print("Point count: ", curve.get_point_count())

func edit_curve(time: float, value: float):
    # 编辑曲线
    if curve:
        curve.add_point(time, value)

func remove_curve(time: float):
    # 移除曲线点。Curve 没有 `remove_point_at_time()`，
    # 要按时间删除得先找到最接近的点的索引，再按索引删。
    if curve and curve.point_count > 0:
        # 4.3 的 Curve 没有 get_closest_offset()/get_point_count()，
        # 只能自己按 get_point_position(i) 找最接近 time 的那个点
        var best := 0
        var best_delta := INF
        for i in curve.point_count:
            var delta: float = absf(curve.get_point_position(i).x - time)
            if delta < best_delta:
                best_delta = delta
                best = i
        curve.remove_point(best)

func get_curve_value(time: float) -> float:
    # 获取曲线值
    if curve:
        return curve.sample(time)
    return 0.0
```

---

## 4. 动画预览

### 4.1 基础动画预览

```gdscript
# 基础动画预览
class_name BasicAnimationPreview

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"

func _ready():
    # 设置动画预览
    if animation_player and not animation_name.empty():
        animation_player.play(animation_name)

func _process(delta):
    # 更新动画预览
    if animation_player:
        var time = animation_player.current_animation_position
        var length = animation_player.get_animation(animation_name).length
        print("Time: ", time, " / ", length)

func play_animation(anim_name: String):
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)

func stop_animation():
    if animation_player:
        animation_player.stop()

func pause_animation():
    if animation_player:
        animation_player.pause()

func resume_animation():
    if animation_player:
        animation_player.play()

func set_speed(speed: float):
    if animation_player:
        animation_player.speed_scale = speed
```

### 4.2 动画预览器

```gdscript
# 动画预览器
class_name AnimationPreviewer

extends Node3D

@export var animation_player: AnimationPlayer
@export var preview_node: Node3D

func _ready():
    # 设置动画预览器
    if animation_player:
        animation_player.animation_finished.connect(_on_animation_finished)

func _on_animation_finished(anim_name: StringName):
    print("Animation finished: ", anim_name)

func _process(_delta):
    # 更新动画预览器
    if animation_player and animation_player.is_playing():
        var time = animation_player.current_animation_position
        var length = animation_player.current_animation_length
        print("Time: ", time, " / ", length)

func play_preview():
    # 播放预览
    if animation_player:
        animation_player.play()

func stop_preview():
    # 停止预览
    if animation_player:
        animation_player.stop()

func set_preview_speed(speed: float):
    if animation_player:
        animation_player.speed_scale = speed

func set_preview_time(time: float):
    if animation_player:
        animation_player.seek(time)
```

### 4.3 动画预览系统

```gdscript
# 运行时的时间轴游标：Control 上没有 time_changed 信号，
# 需要自己定义一个带信号的节点（编辑器里的时间轴控件属于编辑器扩展范畴）。
class_name RuntimeTimelineCursor

extends Node

signal time_changed(time: float)

var current_time: float = 0.0

func set_current_time(time: float) -> void:
    current_time = time
    time_changed.emit(time)
```

### 4.3 动画预览系统

```gdscript
# 动画预览系统
class_name AnimationPreviewSystem

extends Node3D

@export var animation_player: AnimationPlayer
@export var preview_node: Node3D
@export var timeline: RuntimeTimelineCursor

func _ready():
    # 设置动画预览系统
    if animation_player:
        animation_player.animation_finished.connect(_on_animation_finished)
    
    if timeline:
        timeline.time_changed.connect(_on_timeline_changed)

func _on_animation_finished(anim_name: StringName):
    print("Animation finished: ", anim_name)

func _on_timeline_changed(time: float):
    # 时间轴变化
    if animation_player:
        animation_player.seek(time)

func _process(delta):
    # 更新动画预览系统
    if animation_player and animation_player.is_playing():
        var time = animation_player.current_animation_position
        if timeline:
            timeline.set_current_time(time)

func play_preview():
    # 播放预览
    if animation_player:
        animation_player.play()

func stop_preview():
    # 停止预览
    if animation_player:
        animation_player.stop()

func pause_preview():
    # 暂停预览
    if animation_player:
        animation_player.pause()

func resume_preview():
    # 恢复预览
    if animation_player:
        animation_player.play()

func set_preview_speed(speed: float):
    if animation_player:
        animation_player.speed_scale = speed

func set_preview_time(time: float):
    if animation_player:
        animation_player.seek(time)
```

---

## 5. 动画曲线编辑器优化

### 5.1 关键帧优化

```gdscript
# 关键帧优化
class_name KeyframeOptimizer

@export var max_keyframes: int = 100

func optimize_animation(animation: Animation):
    # 优化关键帧数量
    for track_idx in range(animation.get_track_count()):
        if animation.track_get_key_count(track_idx) > max_keyframes:
            # 移除不必要的关键帧
            var step = int(animation.track_get_key_count(track_idx) / max_keyframes) + 1
            for i in range(animation.track_get_key_count(track_idx) - 1, -1, -step):
                if i > 0:
                    animation.track_remove_key(track_idx, i)
            
            print("Animation optimized: track ", track_idx, " from ", 
                  animation.track_get_key_count(track_idx), " to ", 
                  animation.track_get_key_count(track_idx))
```

### 5.2 曲线优化

```gdscript
# 曲线优化
class_name CurveOptimizer

@export var max_points: int = 50

func optimize_curve(curve: Curve):
    # 优化曲线点数量
    if curve.get_point_count() > max_points:
        # 移除不必要的点
        var step = int(curve.get_point_count() / max_points) + 1
        for i in range(curve.get_point_count() - 1, -1, -step):
            if i > 0:
                curve.remove_point(i)
        
        print("Curve optimized: from ", curve.get_point_count(), " to ", 
              curve.get_point_count())
```

### 5.3 动画预览优化

```gdscript
# 动画预览优化
class_name AnimationPreviewOptimizer

@export var preview_quality: int = 1  # 1=低质量, 2=中等质量, 3=高质量

func optimize_preview(previewer: AnimationPreviewer):
    # 优化预览质量
    if previewer:
        match preview_quality:
            1:  # 低质量
                previewer.set_preview_speed(1.0)
                previewer.set_preview_time(0.0)
            2:  # 中等质量
                previewer.set_preview_speed(1.0)
                previewer.set_preview_time(0.0)
            3:  # 高质量
                previewer.set_preview_speed(1.0)
                previewer.set_preview_time(0.0)
```

---

## 6. 实践：完整动画曲线编辑器系统

### 6.1 基础动画曲线编辑器系统

```gdscript
# 基础动画曲线编辑器系统
class_name BasicAnimationCurveEditorSystem

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"
@export var curve: Curve

func _ready():
    # 设置基础动画曲线编辑器系统
    if animation_player and not animation_name.empty():
        create_animation(animation_name)
    
    if curve:
        curve.add_point(0.0, 0.0)
        curve.add_point(0.5, 0.8)
        curve.add_point(1.0, 1.0)

func create_animation(anim_name: String):
    # 创建动画
    var animation = Animation.new()
    
    # 添加轨道
    var track_idx = animation.add_track(Animation.TYPE_TRANSFORM_3D)
    animation.track_set_path(track_idx, NodePath("MeshInstance3D:position"))
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 1.0, [Vector3(1, 0, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 2.0, [Vector3(1, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 3.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画：AnimationPlayer 没有 add_animation()，走 AnimationLibrary
    var lib := animation_player.get_animation_library("")
    if lib == null:
        lib = AnimationLibrary.new()
        animation_player.add_animation_library("", lib)
    lib.add_animation(StringName(anim_name), animation)

func edit_animation(time: float, value: Array):
    # 编辑动画
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, value)

func edit_curve(time: float, value: float):
    # 编辑曲线
    if curve:
        curve.add_point(time, value)
```

### 6.2 高级动画曲线编辑器系统

```gdscript
# 高级动画曲线编辑器系统
class_name AdvancedAnimationCurveEditorSystem

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"
@export var curve: Curve
@export var keyframe_editor: BasicKeyframeEditor
@export var curve_editor: BasicCurveEditor
@export var animation_previewer: AnimationPreviewer

func _ready():
    # 设置高级动画曲线编辑器系统
    if animation_player and not animation_name.empty():
        create_animation(animation_name)
    
    if curve:
        curve.add_point(0.0, 0.0)
        curve.add_point(0.5, 0.8)
        curve.add_point(1.0, 1.0)
    
    if keyframe_editor:
        keyframe_editor.animation_player = animation_player
        keyframe_editor.animation_name = animation_name
    
    if curve_editor:
        curve_editor.animation_player = animation_player
        curve_editor.animation_name = animation_name
    
    if animation_previewer:
        animation_previewer.animation_player = animation_player

func create_animation(anim_name: String):
    # 创建动画
    var animation = Animation.new()
    
    # 添加轨道
    var track_idx = animation.add_track(Animation.TYPE_TRANSFORM_3D)
    animation.track_set_path(track_idx, NodePath("MeshInstance3D:position"))
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 1.0, [Vector3(1, 0, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 2.0, [Vector3(1, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    animation.track_insert_key(track_idx, 3.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画：AnimationPlayer 没有 add_animation()，走 AnimationLibrary
    var lib := animation_player.get_animation_library("")
    if lib == null:
        lib = AnimationLibrary.new()
        animation_player.add_animation_library("", lib)
    lib.add_animation(StringName(anim_name), animation)

func edit_animation(time: float, value: Array):
    # 编辑动画
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, value)

func edit_curve(time: float, value: float):
    # 编辑曲线
    if curve:
        curve.add_point(time, value)

func play_preview():
    # 播放预览
    if animation_previewer:
        animation_previewer.play_preview()

func stop_preview():
    # 停止预览
    if animation_previewer:
        animation_previewer.stop_preview()
```

### 6.3 完整动画曲线编辑器系统

```gdscript
# 完整动画曲线编辑器系统
class_name FullAnimationCurveEditorSystem

extends Node3D

@export var basic_system: BasicAnimationCurveEditorSystem
@export var advanced_system: AdvancedAnimationCurveEditorSystem
@export var keyframe_optimizer: KeyframeOptimizer
@export var curve_optimizer: CurveOptimizer
@export var preview_optimizer: AnimationPreviewOptimizer

@export var animation_player: AnimationPlayer
@export var curve: Curve

func _ready():
    # 设置完整动画曲线编辑器系统
    if basic_system:
        basic_system.edit_animation(0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    
    if advanced_system:
        advanced_system.edit_animation(0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    
    if keyframe_optimizer and animation_player:
        if animation_player.has_animation("walk"):
            keyframe_optimizer.optimize_animation(animation_player.get_animation("walk"))
    
    if curve_optimizer and curve:
        curve_optimizer.optimize_curve(curve)
    
    if preview_optimizer:
        preview_optimizer.optimize_preview($AnimationPreviewer)

func _process(_delta):
    # 更新完整动画曲线编辑器系统
    if keyframe_optimizer and animation_player:
        if animation_player.has_animation("walk"):
            keyframe_optimizer.optimize_animation(animation_player.get_animation("walk"))
    
    if curve_optimizer and curve:
        curve_optimizer.optimize_curve(curve)
    
    if preview_optimizer:
        preview_optimizer.optimize_preview($AnimationPreviewer)

func play_preview():
    # 开始预览
    if advanced_system:
        advanced_system.play_preview()

func stop_preview():
    # 停止预览
    if advanced_system:
        advanced_system.stop_preview()
```

---

## 📝 本章总结

### 核心要点

1. **关键帧编辑是基础**，通过关键帧定义动画
2. **曲线调整用于平滑动画**，通过曲线插值
3. **动画预览用于实时查看**，快速迭代动画
4. **动画曲线编辑器优化**，包括关键帧、曲线、预览优化
5. **完整动画曲线编辑器系统**，整合所有编辑器功能

### 关键术语

| 术语 | 解释 |
|------|------|
| Keyframe | 关键帧，定义动画的关键时间点 |
| Curve | 曲线，插值动画值 |
| Animation Preview | 动画预览，实时查看动画效果 |
| Animation Editor | 动画编辑器，编辑动画数据 |
| LOD | 细节层次，根据距离调整编辑器 |

---

## 🔗 延伸阅读

- **官方文档 · 动画教程索引**: <https://docs.godotengine.org/en/stable/tutorials/animation/index.html>
- **官方文档 · Animation（资源）**: <https://docs.godotengine.org/en/stable/classes/class_animation.html>
- **官方文档 · Curve**: <https://docs.godotengine.org/en/stable/classes/class_curve.html>
- **官方文档 · AnimationPlayer**: <https://docs.godotengine.org/en/stable/classes/class_animationplayer.html>
- **源码位置**: `scene/resources/animation.cpp`、`scene/resources/animation_library.cpp`、
  `scene/animation/animation_player.cpp`、`scene/animation/animation_mixer.cpp`

> **注意**：Godot 4.3 的 `servers/` 目录下**没有** `animation/` 子目录；
> 动画资源与实现分别位于 `scene/resources/` 与 `scene/animation/`。

---

## 📋 上下篇导航

**上一篇**: [第 40 篇：角色动画](/articles/40-character-animation.md)
**下一篇**: [第 43 篇：动画状态机](/articles/43-animation-state-machine.md)

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

*写作时间：2026-03-20*  
*字数：约 800 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
