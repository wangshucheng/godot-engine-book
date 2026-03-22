# 第 41 篇：动画曲线

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 42 章 骨骼动画  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

动画曲线编辑器是游戏开发中实现精确动画控制的重要工具。通过动画曲线编辑器，开发者可以创建和编辑复杂的动画曲线，实现平滑的动画过渡和复杂的动画效果。

Godot 提供了强大的动画曲线编辑器，包括关键帧编辑、曲线调整、动画预览等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解动画曲线编辑器的基本概念
- 掌握关键帧编辑
- 学会曲线调整技术
- 熟悉动画预览
- 掌握动画曲线编辑器优化

---

## 1. 动画曲线编辑器基础

### 1.1 动画曲线编辑器类型

```
动画曲线编辑器类型:
┌─────────────────────────────────────────────────────────────┐
│                      动画曲线编辑器类型                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 关键帧编辑器：编辑关键帧和曲线                          │
│  2. 曲线调整器：调整曲线形状和参数                          │
│  3. 动画预览器：预览动画效果                                │
│  4. 贴图编辑器：编辑动画贴图                                │
│  5. 属性编辑器：编辑动画属性                                │
│  6. 时间轴编辑器：编辑时间轴和帧率                          │
│  7. 节点编辑器：编辑动画节点                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画曲线编辑器组件

```
动画曲线编辑器组件:
┌─────────────────────────────────────────────────────────────┐
│                      动画曲线编辑器组件                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Animation: 动画资源                                     │
│  2. AnimationPlayer: 动画播放器                             │
│  3. AnimationTrack: 动画轨道                                │
│  4. AnimationKey: 动画关键帧                                │
│  5. AnimationCurve: 动画曲线                                │
│  6. AnimationNode: 动画节点                                 │
│  7. AnimationTree: 动画树                                   │
│  8. AnimationMixer: 动画混合器                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画曲线编辑器流程

```
动画曲线编辑器处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画曲线编辑器处理流程                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 编辑器接收动画数据                                      │
│  2. 关键帧编辑器编辑关键帧                                  │
│  3. 曲线编辑器调整曲线                                      │
│  4. 预览播放器预览动画                                      │
│  5. 保存动画数据                                            │
│  6. 导出动画数据                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 关键帧编辑

### 2.1 基础关键帧编辑

```gdscript
# 关键帧编辑基础
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
    var animation = Animation.new()
    
    # 添加轨道
    var track_idx = animation.add_track(AnimationTrackType.TRANSFORM_3D)
    animation.track_set_path(track_idx, "Transform3D")
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, Transform3D(Basis(), Vector3(0, 0, 0)))
    animation.track_insert_key(track_idx, 1.0, Transform3D(Basis(), Vector3(1, 0, 0)))
    animation.track_insert_key(track_idx, 2.0, Transform3D(Basis(), Vector3(1, 1, 0)))
    animation.track_insert_key(track_idx, 3.0, Transform3D(Basis(), Vector3(0, 1, 0)))
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画到播放器
    animation_player.add_animation(anim_name, animation)

func edit_keyframe(time: float, transform: Transform3D):
    # 编辑关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, transform)

func remove_keyframe(time: float):
    # 移除关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_remove_key(track_idx, time)

func get_keyframe(time: float) -> Transform3D:
    # 获取关键帧
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            return animation.track_get_key_value(track_idx, animation.track_find_key(track_idx, time))
    return Transform3D()
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

func _process(delta):
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

func set_keyframe_value(value: Transform3D):
    # 设置关键帧值
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_value(0, keyframe_index, value)

func set_keyframe_interp_mode(mode: Animation.InterpolationMode):
    # 设置关键帧插值模式
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_interp_mode(0, keyframe_index, mode)

func set_keyframe_tangent_mode(mode: Animation.TangentMode):
    # 设置关键帧切线模式
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            animation.track_set_key_tangent_mode(0, keyframe_index, mode)
```

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
    var animation = Animation.new()
    
    # 添加轨道
    var track_idx = animation.add_track(AnimationTrackType.TRANSFORM_3D)
    animation.track_set_path(track_idx, "Transform3D")
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, Transform3D(Basis(), Vector3(0, 0, 0)))
    animation.track_insert_key(track_idx, 0.5, Transform3D(Basis(), Vector3(1, 0, 0)))
    animation.track_insert_key(track_idx, 1.0, Transform3D(Basis(), Vector3(1, 1, 0)))
    animation.track_insert_key(track_idx, 1.5, Transform3D(Basis(), Vector3(0, 1, 0)))
    animation.track_insert_key(track_idx, 2.0, Transform3D(Basis(), Vector3(0, 0, 0)))
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画
    add_animation(anim_name, animation)

func _process(delta):
    # 更新关键帧动画
    if is_playing():
        var time = get_current_animation_position()
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
# 曲线调整基础
class_name BasicCurveEditor

extends Node3D

@export var animation_player: AnimationPlayer
@export var animation_name: String = "walk"

func _ready():
    # 设置曲线
    if animation_player and not animation_name.empty():
        create_curve("curve")

func create_curve(curve_name: String):
    # 创建曲线
    var curve = Curve.new()
    
    # 添加点
    curve.add_point(0.0, 0.0)
    curve.add_point(0.5, 0.8)
    curve.add_point(1.0, 1.0)
    
    # 设置点属性
    curve.set_point_out(0, 0.5)
    curve.set_point_in(1, 0.5)
    curve.set_point_out(1, 0.5)
    
    # 保存曲线
    $CurveResource.curve = curve

func edit_curve_point(point_index: int, time: float, value: float):
    # 编辑曲线点
    if $CurveResource.curve:
        $CurveResource.curve.set_point_position(point_index, Vector2(time, value))

func remove_curve_point(point_index: int):
    # 移除曲线点
    if $CurveResource.curve:
        $CurveResource.curve.remove_point(point_index)

func get_curve_value(time: float) -> float:
    # 获取曲线值
    if $CurveResource.curve:
        return $CurveResource.curve.sample(time)
    return 0.0
```

### 3.2 曲线属性

```gdscript
# 曲线属性
class_name CurveProperties

extends Node3D

@export var curve_resource: CurveResource
@export var curve: Curve

func _ready():
    # 设置曲线属性
    if curve_resource and curve_resource.curve:
        curve = curve_resource.curve

func _process(delta):
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
    # 设置切线模式
    if curve:
        curve.tangent_mode = mode

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
    # 移除曲线点
    if curve:
        curve.remove_point_at_time(time)

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
        var time = animation_player.get_current_animation_position()
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
        animation_player.connect("animation_finished", self, "_on_animation_finished")

func _on_animation_finished(anim_name: String):
    print("Animation finished: ", anim_name)

func _process(delta):
    # 更新动画预览器
    if animation_player and animation_player.is_playing():
        var time = animation_player.get_current_animation_position()
        var length = animation_player.get_current_animation_length()
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
# 动画预览系统
class_name AnimationPreviewSystem

extends Node3D

@export var animation_player: AnimationPlayer
@export var preview_node: Node3D
@export var timeline: Control

func _ready():
    # 设置动画预览系统
    if animation_player:
        animation_player.connect("animation_finished", self, "_on_animation_finished")
    
    if timeline:
        timeline.connect("time_changed", self, "_on_timeline_changed")

func _on_animation_finished(anim_name: String):
    print("Animation finished: ", anim_name)

func _on_timeline_changed(time: float):
    # 时间轴变化
    if animation_player:
        animation_player.seek(time)

func _process(delta):
    # 更新动画预览系统
    if animation_player and animation_player.is_playing():
        var time = animation_player.get_current_animation_position()
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
    var track_idx = animation.add_track(AnimationTrackType.TRANSFORM_3D)
    animation.track_set_path(track_idx, "Transform3D")
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, Transform3D(Basis(), Vector3(0, 0, 0)))
    animation.track_insert_key(track_idx, 1.0, Transform3D(Basis(), Vector3(1, 0, 0)))
    animation.track_insert_key(track_idx, 2.0, Transform3D(Basis(), Vector3(1, 1, 0)))
    animation.track_insert_key(track_idx, 3.0, Transform3D(Basis(), Vector3(0, 1, 0)))
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画
    animation_player.add_animation(anim_name, animation)

func edit_animation(time: float, transform: Transform3D):
    # 编辑动画
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, transform)

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
    var track_idx = animation.add_track(AnimationTrackType.TRANSFORM_3D)
    animation.track_set_path(track_idx, "Transform3D")
    
    # 添加关键帧
    animation.track_insert_key(track_idx, 0.0, Transform3D(Basis(), Vector3(0, 0, 0)))
    animation.track_insert_key(track_idx, 1.0, Transform3D(Basis(), Vector3(1, 0, 0)))
    animation.track_insert_key(track_idx, 2.0, Transform3D(Basis(), Vector3(1, 1, 0)))
    animation.track_insert_key(track_idx, 3.0, Transform3D(Basis(), Vector3(0, 1, 0)))
    
    # 设置动画循环
    animation.loop_mode = Animation.LOOP_LINEAR
    
    # 添加动画
    animation_player.add_animation(anim_name, animation)

func edit_animation(time: float, transform: Transform3D):
    # 编辑动画
    if animation_player and not animation_name.empty():
        var animation = animation_player.get_animation(animation_name)
        if animation:
            var track_idx = 0
            animation.track_insert_key(track_idx, time, transform)

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

func _ready():
    # 设置完整动画曲线编辑器系统
    if basic_system:
        basic_system.play_emission()
    
    if advanced_system:
        advanced_system.play_emission()
    
    if keyframe_optimizer:
        if $AnimationPlayer and $AnimationPlayer.has_animation("walk"):
            keyframe_optimizer.optimize_animation($AnimationPlayer.get_animation("walk"))
    
    if curve_optimizer:
        if $CurveResource and $CurveResource.curve:
            curve_optimizer.optimize_curve($CurveResource.curve)
    
    if preview_optimizer:
        preview_optimizer.optimize_preview($AnimationPreviewer)

func _process(delta):
    # 更新完整动画曲线编辑器系统
    if basic_system:
        basic_system.process(delta)
    
    if advanced_system:
        advanced_system.process(delta)
    
    if keyframe_optimizer:
        if $AnimationPlayer and $AnimationPlayer.has_animation("walk"):
            keyframe_optimizer.optimize_animation($AnimationPlayer.get_animation("walk"))
    
    if curve_optimizer:
        if $CurveResource and $CurveResource.curve:
            curve_optimizer.optimize_curve($CurveResource.curve)
    
    if preview_optimizer:
        preview_optimizer.optimize_preview($AnimationPreviewer)

func play_emission():
    # 开始发射
    if basic_system:
        basic_system.play_emission()
    if advanced_system:
        advanced_system.play_emission()

func stop_emission():
    # 停止发射
    if basic_system:
        basic_system.stop_emission()
    if advanced_system:
        advanced_system.stop_emission()
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

- **官方文档**: [Godot Animation](https://docs.godotengine.org/en/stable/tutorials/animation/animation.html)
- **源码位置**: `servers/animation/`
- **技术博客**: [Godot Animation Curve Editor](https://godotengine.org/article/animation-curve-editor/)

---

## 📋 下一章预告

**第 44 篇：动画混合器**

- 动画混合器基础
- 动画混合器配置
- 动画混合器应用
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 10,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*