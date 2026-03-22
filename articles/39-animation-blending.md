# 第 25 篇：动画混合

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 第 34 章 动画控制器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

动画混合是游戏开发中实现流畅动画过渡和复杂动画效果的关键技术。通过动画混合，开发者可以将多个动画无缝地结合在一起，创造出更加自然和生动的角色动作。

Godot 提供了多种动画混合技术，包括 AnimationNodeBlend2、AnimationNodeAdd2、AnimationNodeBlend3 等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解动画混合的基本概念
- 掌握 AnimationNodeBlend2 使用
- 学会 AnimationNodeAdd2 应用
- 熟悉 AnimationNodeBlend3
- 掌握高级动画混合技术

---

## 1. 动画混合基础

### 1.1 动画混合类型

```
动画混合类型:
┌─────────────────────────────────────────────────────────────┐
│                      动画混合类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 线性混合：两个动画按权重线性插值                        │
│  2. 加法混合：两个动画相加                                  │
│  3. 乘法混合：两个动画相乘                                  │
│  4. 最大值混合：取两个动画的最大值                          │
│  5. 最小值混合：取两个动画的最小值                          │
│  6. 自定义混合：自定义混合函数                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画混合流程

```
动画混合处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画混合处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 动画混合器接收两个或多个动画输入                        │
│  2. 动画混合器根据权重计算混合比例                          │
│  3. 动画混合器对每个动画属性进行混合                        │
│  4. 动画混合器输出最终混合后的动画数据                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画混合参数

```gdscript
# 动画混合参数
class_name AnimationBlendParameters

@export var blend_weight: float = 0.5
@export var blend_mode: int = 0  # 0: linear, 1: add, 2: multiply
@export var blend_duration: float = 0.5

func _ready():
    # 初始化参数
    blend_weight = 0.5
    blend_mode = 0
    blend_duration = 0.5

func update_parameters():
    # 更新参数
    blend_weight = $CharacterBody2D.velocity.length() / 5.0
    blend_mode = Input.get_action_strength("blend_mode")
    blend_duration = Input.get_action_strength("blend_duration")
```

---

## 2. AnimationNodeBlend2

### 2.1 基础 AnimationNodeBlend2

```gdscript
# 基础 AnimationNodeBlend2
class_name BasicAnimationNodeBlend2

extends AnimationNodeBlend2

@export var input_a: AnimationNode
@export var input_b: AnimationNode
@export var blend_amount: float = 0.5

func _ready():
    # 设置输入
    if input_a:
        set_input(0, input_a)
    if input_b:
        set_input(1, input_b)
    
    # 设置混合量
    set_blend_amount(blend_amount)

func _process(delta):
    # 处理混合
    process(delta)

func set_blend_amount(amount: float):
    blend_amount = clamp(amount, 0.0, 1.0)
    set_parameter("blend_amount", blend_amount)

func get_blend_amount() -> float:
    return blend_amount
```

### 2.2 AnimationNodeBlend2 参数

```gdscript
# AnimationNodeBlend2 参数
class_name AnimationNodeBlend2Parameters

extends Node

@export var blend_node: AnimationNodeBlend2
@export var parameter_name: String = "blend_amount"

func _ready():
    if blend_node and not parameter_name.empty():
        blend_node.set_parameter(parameter_name, 0.5)

func set_parameter(value: float):
    if blend_node and not parameter_name.empty():
        blend_node.set_parameter(parameter_name, value)

func get_parameter() -> float:
    if blend_node and not parameter_name.empty():
        return blend_node.get_parameter(parameter_name)
    return 0.5

func update_parameter():
    if blend_node and not parameter_name.empty():
        var value = $CharacterBody2D.velocity.length() / 5.0
        blend_node.set_parameter(parameter_name, value)
```

### 2.3 AnimationNodeBlend2 轨道

```gdscript
# AnimationNodeBlend2 轨道
class_name AnimationNodeBlend2Track

extends AnimationNodeBlend2Track

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationNodeBlend2State.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeBlend2State:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 3. AnimationNodeAdd2

### 3.1 基础 AnimationNodeAdd2

```gdscript
# 基础 AnimationNodeAdd2
class_name BasicAnimationNodeAdd2

extends AnimationNodeAdd2

@export var input_a: AnimationNode
@export var input_b: AnimationNode
@export var add_amount: float = 1.0

func _ready():
    # 设置输入
    if input_a:
        set_input(0, input_a)
    if input_b:
        set_input(1, input_b)
    
    # 设置添加量
    set_add_amount(add_amount)

func _process(delta):
    # 处理添加
    process(delta)

func set_add_amount(amount: float):
    add_amount = amount
    set_parameter("add_amount", add_amount)

func get_add_amount() -> float:
    return add_amount
```

### 3.2 AnimationNodeAdd2 参数

```gdscript
# AnimationNodeAdd2 参数
class_name AnimationNodeAdd2Parameters

extends Node

@export var add_node: AnimationNodeAdd2
@export var parameter_name: String = "add_amount"

func _ready():
    if add_node and not parameter_name.empty():
        add_node.set_parameter(parameter_name, 1.0)

func set_parameter(value: float):
    if add_node and not parameter_name.empty():
        add_node.set_parameter(parameter_name, value)

func get_parameter() -> float:
    if add_node and not parameter_name.empty():
        return add_node.get_parameter(parameter_name)
    return 1.0

func update_parameter():
    if add_node and not parameter_name.empty():
        var value = $CharacterBody2D.velocity.length() / 5.0
        add_node.set_parameter(parameter_name, value)
```

### 3.3 AnimationNodeAdd2 轨道

```gdscript
# AnimationNodeAdd2 轨道
class_name AnimationNodeAdd2Track

extends AnimationNodeAdd2Track

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationNodeAdd2State.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeAdd2State:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 4. AnimationNodeBlend3

### 4.1 基础 AnimationNodeBlend3

```gdscript
# 基础 AnimationNodeBlend3
class_name BasicAnimationNodeBlend3

extends AnimationNodeBlend3

@export var input_a: AnimationNode
@export var input_b: AnimationNode
@export var input_c: AnimationNode
@export var blend_amount_x: float = 0.5
@export var blend_amount_y: float = 0.5

func _ready():
    # 设置输入
    if input_a:
        set_input(0, input_a)
    if input_b:
        set_input(1, input_b)
    if input_c:
        set_input(2, input_c)
    
    # 设置混合量
    set_blend_amount_x(blend_amount_x)
    set_blend_amount_y(blend_amount_y)

func _process(delta):
    # 处理混合
    process(delta)

func set_blend_amount_x(amount: float):
    blend_amount_x = clamp(amount, 0.0, 1.0)
    set_parameter("blend_amount_x", blend_amount_x)

func get_blend_amount_x() -> float:
    return blend_amount_x

func set_blend_amount_y(amount: float):
    blend_amount_y = clamp(amount, 0.0, 1.0)
    set_parameter("blend_amount_y", blend_amount_y)

func get_blend_amount_y() -> float:
    return blend_amount_y
```

### 4.2 AnimationNodeBlend3 参数

```gdscript
# AnimationNodeBlend3 参数
class_name AnimationNodeBlend3Parameters

extends Node

@export var blend_node: AnimationNodeBlend3
@export var parameter_x: String = "blend_amount_x"
@export var parameter_y: String = "blend_amount_y"

func _ready():
    if blend_node and not parameter_x.empty():
        blend_node.set_parameter(parameter_x, 0.5)
    if blend_node and not parameter_y.empty():
        blend_node.set_parameter(parameter_y, 0.5)

func set_parameter_x(value: float):
    if blend_node and not parameter_x.empty():
        blend_node.set_parameter(parameter_x, value)

func get_parameter_x() -> float:
    if blend_node and not parameter_x.empty():
        return blend_node.get_parameter(parameter_x)
    return 0.5

func set_parameter_y(value: float):
    if blend_node and not parameter_y.empty():
        blend_node.set_parameter(parameter_y, value)

func get_parameter_y() -> float:
    if blend_node and not parameter_y.empty():
        return blend_node.get_parameter(parameter_y)
    return 0.5

func update_parameters():
    if blend_node and not parameter_x.empty():
        var value_x = $CharacterBody2D.velocity.x / 5.0
        blend_node.set_parameter(parameter_x, value_x)
    if blend_node and not parameter_y.empty():
        var value_y = $CharacterBody2D.velocity.y / 5.0
        blend_node.set_parameter(parameter_y, value_y)
```

### 4.3 AnimationNodeBlend3 轨道

```gdscript
# AnimationNodeBlend3 轨道
class_name AnimationNodeBlend3Track

extends AnimationNodeBlend3Track

func _ready():
    # 添加状态
    add_state("Idle", 0.0, 1.0)
    add_state("Walk", 1.0, 2.0)
    add_state("Run", 2.0, 3.0)
    
    # 设置初始状态
    set_state("Idle")

func _process(delta):
    # 更新当前状态
    var state = get_state()
    if state:
        state.process(delta)

func add_state(state_name: String, start_time: float, end_time: float):
    add_key(AnimationNodeBlend3State.new(), start_time, end_time, state_name)

func set_state(state_name: String):
    if has_state(state_name):
        set_current_key(state_name)

func get_state() -> AnimationNodeBlend3State:
    if has_state(get_current_key()):
        return get_state_key(get_current_key())
    return null
```

---

## 5. 高级动画混合技术

### 5.1 分层动画混合

```gdscript
# 分层动画混合
class_name LayeredAnimationBlending

extends Node

@export var upper_body_blend: AnimationNodeBlend2
@export var lower_body_blend: AnimationNodeBlend2
@export var facial_blend: AnimationNodeBlend2

func _ready():
    # 设置上半身混合
    if upper_body_blend:
        upper_body_blend.set_input(0, $IdleUpper)
        upper_body_blend.set_input(1, $AttackUpper)
        upper_body_blend.set_blend_amount(0.0)
    
    # 设置下半身混合
    if lower_body_blend:
        lower_body_blend.set_input(0, $IdleLower)
        lower_body_blend.set_input(1, $WalkLower)
        lower_body_blend.set_blend_amount(0.0)
    
    # 设置面部混合
    if facial_blend:
        facial_blend.set_input(0, $NeutralFace)
        facial_blend.set_input(1, $HappyFace)
        facial_blend.set_blend_amount(0.0)

func update_blending():
    # 更新上半身混合
    if upper_body_blend:
        var upper_blend = Input.get_action_strength("attack")
        upper_body_blend.set_blend_amount(upper_blend)
    
    # 更新下半身混合
    if lower_body_blend:
        var lower_blend = $CharacterBody2D.velocity.length() / 5.0
        lower_body_blend.set_blend_amount(lower_blend)
    
    # 更新面部混合
    if facial_blend:
        var facial_blend = Input.get_action_strength("happy")
        facial_blend.set_blend_amount(facial_blend)
```

### 5.2 时间同步混合

```gdscript
# 时间同步混合
class_name TimeSyncedBlending

extends Node

@export var primary_animation: AnimationPlayer
@export var secondary_animation: AnimationPlayer
@export var sync_offset: float = 0.0

func _ready():
    # 连接信号
    primary_animation.connect("animation_started", self, "_on_primary_started")
    primary_animation.connect("animation_finished", self, "_on_primary_finished")

func _on_primary_started(anim_name: String):
    # 同步开始次要动画
    if secondary_animation and secondary_animation.has_animation(anim_name):
        secondary_animation.play(anim_name)
        secondary_animation.seek(primary_animation.get_current_animation_position() + sync_offset)

func _on_primary_finished(anim_name: String):
    # 同步结束次要动画
    if secondary_animation:
        secondary_animation.stop()

func update_sync():
    # 更新同步偏移
    if primary_animation.is_playing() and secondary_animation.is_playing():
        var primary_pos = primary_animation.get_current_animation_position()
        var secondary_pos = secondary_animation.get_current_animation_position()
        sync_offset = primary_pos - secondary_pos
```

### 5.3 权重动画混合

```gdscript
# 权重动画混合
class_name WeightedAnimationBlending

extends Node

@export var animations: Array
@export var weights: Array

func _ready():
    # 初始化权重
    for i in range(animations.size()):
        weights.append(0.0)

func update_weights():
    # 更新权重
    var total_weight = 0.0
    for i in range(animations.size()):
        weights[i] = get_animation_weight(i)
        total_weight += weights[i]
    
    # 归一化权重
    if total_weight > 0.0:
        for i in range(weights.size()):
            weights[i] /= total_weight

func get_animation_weight(index: int) -> float:
    # 根据条件计算权重
    match index:
        0:  # Idle
            return max(0.0, 1.0 - $CharacterBody2D.velocity.length() / 5.0)
        1:  # Walk
            return clamp($CharacterBody2D.velocity.length() / 5.0, 0.0, 1.0)
        2:  # Run
            return clamp(($CharacterBody2D.velocity.length() - 3.0) / 2.0, 0.0, 1.0)
        _: 
            return 0.0

func blend_animations():
    # 混合动画
    update_weights()
    
    # 应用权重到动画播放器
    for i in range(animations.size()):
        if animations[i] is AnimationPlayer:
            animations[i].set_speed_scale(weights[i])
```

---

## 6. 动画混合优化

### 6.1 动画混合缓存

```gdscript
# 动画混合缓存
class_name AnimationBlendCache

var cache = {}

func get_blend(blend_name: String) -> AnimationBlend:
    if cache.has(blend_name):
        return cache[blend_name]
    
    var blend = AnimationBlend.new()
    cache[blend_name] = blend
    return blend

func clear_cache():
    cache.clear()
```

### 6.2 动画混合LOD

```gdscript
# 动画混合LOD
class_name AnimationBlendLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_blends: Array = ["simple", "medium", "complex"]

func update_lod(camera_position: Vector2, character: Node2D):
    var distance = camera_position.distance_to(character.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_blends.size() - 1)
    
    # 更新混合
    if lod_index < lod_blends.size():
        character.animation_blend.set_blend_type(lod_blends[lod_index])
```

### 6.3 动画混合压缩

```gdscript
# 动画混合压缩
class_name AnimationBlendCompressor

@export var max_inputs: int = 2

func compress_blend(blend: AnimationBlend):
    if blend.get_inputs().size() > max_inputs:
        # 优化输入
        var new_inputs = []
        
        # 保留关键输入
        for i in range(min(max_inputs, blend.get_inputs().size())):
            new_inputs.append(blend.get_inputs()[i])
        
        blend.set_inputs(new_inputs)
        print("Blend compressed from ", blend.get_inputs().size(), " to ", new_inputs.size())
    else:
        print("Blend already small enough")
```

---

## 7. 实践：角色动画混合

### 7.1 基础角色动画混合

```gdscript
# 基础角色动画混合
class_name CharacterAnimationBlending

extends Node2D

@export var idle_animation: AnimationPlayer
@export var walk_animation: AnimationPlayer
@export var run_animation: AnimationPlayer
@export var blend_node: AnimationNodeBlend2

func _ready():
    # 设置混合节点
    if blend_node:
        blend_node.set_input(0, idle_animation)
        blend_node.set_input(1, walk_animation)
        blend_node.set_blend_amount(0.0)

func _process(delta):
    # 更新混合
    update_blending()

func update_blending():
    if blend_node:
        var speed = $CharacterBody2D.velocity.length()
        var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
        blend_node.set_blend_amount(blend_amount)
        
        # 切换到跑步动画
        if speed > 3.0:
            blend_node.set_input(1, run_animation)
        else:
            blend_node.set_input(1, walk_animation)
```

### 7.2 骨骼动画混合

```gdscript
# 骨骼动画混合
class_name SkeletonAnimationBlending

extends Node3D

@export var skeleton: Skeleton3D
@export var idle_animation: AnimationPlayer
@export var walk_animation: AnimationPlayer
@export var blend_node: AnimationNodeBlend2

func _ready():
    if skeleton and idle_animation and walk_animation:
        idle_animation.skeleton = skeleton
        walk_animation.skeleton = skeleton
        
        if blend_node:
            blend_node.set_input(0, idle_animation)
            blend_node.set_input(1, walk_animation)
            blend_node.set_blend_amount(0.0)

func _process(delta):
    # 更新混合
    update_blending()

func update_blending():
    if blend_node:
        var speed = $CharacterBody3D.linear_velocity.length()
        var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
        blend_node.set_blend_amount(blend_amount)
```

### 7.3 2D 动画混合

```gdscript
# 2D 动画混合
class_name SpriteAnimationBlending

extends Node2D

@export var sprite_frames: SpriteFrames
@export var idle_animation: AnimationPlayer
@export var walk_animation: AnimationPlayer
@export var blend_node: AnimationNodeBlend2

func _ready():
    if sprite_frames and idle_animation and walk_animation:
        idle_animation.sprite_frames = sprite_frames
        walk_animation.sprite_frames = sprite_frames
        
        if blend_node:
            blend_node.set_input(0, idle_animation)
            blend_node.set_input(1, walk_animation)
            blend_node.set_blend_amount(0.0)

func _process(delta):
    # 更新混合
    update_blending()

func update_blending():
    if blend_node:
        var speed = $CharacterBody2D.velocity.length()
        var blend_amount = clamp(speed / 5.0, 0.0, 1.0)
        blend_node.set_blend_amount(blend_amount)
```

---

## 📝 本章总结

### 核心要点

1. **AnimationNodeBlend2 是基础**，用于两个动画的线性混合
2. **AnimationNodeAdd2 用于加法混合**，适合叠加效果
3. **AnimationNodeBlend3 用于三个动画的混合**，适合复杂场景
4. **分层动画混合**，可以分别控制不同身体部位
5. **动画混合优化**，包括缓存、LOD、压缩等

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationNodeBlend2 | 两个动画的线性混合 |
| AnimationNodeAdd2 | 两个动画的加法混合 |
| AnimationNodeBlend3 | 三个动画的混合 |
| Layered Blending | 分层动画混合 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Animation](https://docs.godotengine.org/en/stable/tutorials/animation/animation.html)
- **源码位置**: `servers/animation/`
- **技术博客**: [Godot Animation Blending](https://godotengine.org/article/animation-blending/)

---

## 📋 下一章预告

**第 36 篇：角色动画**

- 角色动画基础
- 角色动画控制器
- 角色动画混合
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 9,500 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*

---

## 8. 动画混合树详解（新增）

### 8.1 1D 混合树（1D Blend Tree）

1D 混合树用于在多个动画之间根据单个参数（如速度）进行平滑过渡。

```
1D 混合树示例（移动速度）:
┌─────────────────────────────────────────────────────────────┐
│ 速度参数：0.0 → 1.0 → 2.0 → 3.0                            │
│         ↓     ↓     ↓     ↓                                 │
│ 动画：  静止  走路  跑步  冲刺                               │
│                                                             │
│ 混合点:                                                     │
│ 0.0-1.0: 静止 ↔ 走路                                        │
│ 1.0-2.0: 走路 ↔ 跑步                                        │
│ 2.0-3.0: 跑步 ↔ 冲刺                                        │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 1D 混合树实现
class_name AnimationBlendTree1D

extends AnimationNodeBlendTree

@export var speed_parameter: String = "speed"
@export var animations: Array[String] = ["idle", "walk", "run", "sprint"]
@export var blend_points: Array[float] = [0.0, 1.0, 2.0, 3.0]

var tree: AnimationNodeBlendTree

func _init():
    _setup_blend_tree()

func _setup_blend_tree():
    tree = AnimationNodeBlendTree.new()
    
    # 创建混合节点
    for i in range(animations.size()):
        var anim_node = AnimationNodeAnimation.new()
        anim_node.animation = animations[i]
        tree.add_node(animations[i], anim_node)
    
    # 创建 1D 混合节点
    var blend1d = AnimationNodeBlend2.new()
    blend1d.set_blend_parameter(speed_parameter)
    tree.add_node("blend1d", blend1d
    
    # 连接节点
    tree.connect_node(animations[0], "", "blend1d", "in1")
    tree.connect_node(animations[1], "", "blend1d", "in2")
    
    # 设置输出
    tree.set_node_output("blend1d", true)

func set_speed(value: float):
    # 更新混合参数
    tree.set_parameter(speed_parameter, value)

# 高级：动态混合点
class_name DynamicBlendTree1D

extends AnimationBlendTree1D

@export var auto_calculate_points: bool = true

func _ready():
    if auto_calculate_points:
        _calculate_blend_points_from_animations()

func _calculate_blend_points_from_animations():
    # 根据动画长度自动计算混合点
    var total_length = 0.0
    for anim_name in animations:
        var anim_length = _get_animation_length(anim_name)
        total_length += anim_length
    
    # 均匀分布混合点
    var step = total_length / (animations.size() - 1)
    blend_points.clear()
    
    for i in range(animations.size()):
        blend_points.append(i * step)

func _get_animation_length(anim_name: String) -> float:
    # 获取动画长度（从 AnimationPlayer）
    return 1.0  # 简化
```

### 8.2 2D 混合树（2D Blend Tree）

2D 混合树使用两个参数（如 X/Y 方向）在动画空间中混合，常用于全方位移动。

```
2D 混合空间示例（移动方向）:
┌─────────────────────────────────────────────────────────────┐
│                      Y (向前/向后)                           │
│                      ↑                                      │
│                      │                                      │
│         左后 ●       │       ● 右后                         │
│                      │                                      │
│                      │                                      │
│  左 ●───────●───────●───────● 右   → X (向左/向右)          │
│       左前   │  前   │  右前                                 │
│                      │                                      │
│                      │                                      │
│         ● 左后       │       ● 右前                         │
│                      │                                      │
│                      │                                      │
└─────────────────────────────────────────────────────────────┘

混合权重计算:
- 根据输入 (X, Y) 找到周围的 4 个动画点
- 使用双线性插值计算权重
- 混合 4 个动画
```

```gdscript
# 2D 混合树实现
class_name AnimationBlendTree2D

extends AnimationNodeBlendTree

@export var x_parameter: String = "move_x"
@export var y_parameter: String = "move_y"

# 2D 网格中的动画（3x3 示例）
var animations_grid = {
    Vector2(-1, -1): "back_left",
    Vector2(0, -1): "back",
    Vector2(1, -1): "back_right",
    Vector2(-1, 0): "left",
    Vector2(0, 0): "idle",
    Vector2(1, 0): "right",
    Vector2(-1, 1): "front_left",
    Vector2(0, 1): "front",
    Vector2(1, 1): "front_right"
}

var tree: AnimationNodeBlendTree

func _init():
    _setup_2d_blend_tree()

func _setup_2d_blend_tree():
    tree = AnimationNodeBlendTree.new()
    
    # 创建动画节点
    for pos in animations_grid:
        var anim_name = animations_grid[pos]
        var anim_node = AnimationNodeAnimation.new()
        anim_node.animation = anim_name
        tree.add_node(anim_name, anim_node)
    
    # 创建 2D 混合节点
    var blend2d = AnimationNodeBlend2.new()
    tree.add_node("blend2d", blend2d)
    
    # 连接节点（简化示例，实际需要多层混合）
    # 实际实现使用 AnimationNodeBlendSpace2D
    
    tree.set_node_output("blend2d", true)

func set_direction(x: float, y: float):
    # 设置混合参数
    tree.set_parameter(x_parameter, x)
    tree.set_parameter(y_parameter, y)

# 使用 Godot 内置的 BlendSpace2D
func setup_blend_space_2d():
    var blend_space = AnimationNodeBlendSpace2D.new()
    
    # 添加混合点
    blend_space.add_blend_point(AnimationNodeAnimation.new(), Vector2(0, 0))  #  idle
    blend_space.add_blend_point(AnimationNodeAnimation.new(), Vector2(1, 0))  # 右
    blend_space.add_blend_point(AnimationNodeAnimation.new(), Vector2(0, 1))  # 前
    blend_space.add_blend_point(AnimationNodeAnimation.new(), Vector2(-1, 0)) # 左
    blend_space.add_blend_point(AnimationNodeAnimation.new(), Vector2(0, -1)) # 后
    
    # 设置混合模式
    blend_space.set_blend_mode(AnimationNodeBlendSpace2D.BLEND_MODE_INTERPOLATED)
    
    # 设置参数
    blend_space.set_parameter_x("move_x")
    blend_space.set_parameter_y("move_y")
    
    return blend_space
```

### 8.3 混合树性能优化

```
混合树性能考量:
┌─────────────────────────────────────────────────────────────┐
│ 因素              │ 影响            │ 优化建议              │
├─────────────────────────────────────────────────────────────┤
│ 混合节点数量      │ CPU 负载 +2-5%/个  │ 限制层级深度        │
│ 混合参数更新频率  │ 每帧计算        │ 按需更新              │
│ 动画轨道数量      │ 内存 + 计算      │ 禁用未使用轨道        │
│ 混合权重计算      │ 浮点运算        │ 缓存结果              │
└─────────────────────────────────────────────────────────────┘

最佳实践:
✅ 使用 1D/2D 混合树代替多层 Blend2
✅ 缓存混合权重计算结果
✅ 禁用远处角色的动画混合
✅ 简化混合树结构
❌ 过深的混合树嵌套
❌ 每帧重新创建混合节点
❌ 不必要的混合参数更新
```

---

## 9. 动画遮罩和分层（新增）

### 9.1 动画遮罩（Animation Mask）

动画遮罩允许只混合特定身体部位的动画，实现上半身/下半身独立动画。

```
动画遮罩示例:
┌─────────────────────────────────────────────────────────────┐
│ 身体部位遮罩:                                               │
│                                                             │
│ 上半身遮罩：[头，躯干，左臂，右臂]                          │
│ 下半身遮罩：[躯干，左腿，右腿，骨盆]                        │
│                                                             │
│ 应用:                                                       │
│ - 上半身：射击动画                                          │
│ - 下半身：跑步动画                                          │
│ - 混合：边跑边射击                                          │
└─────────────────────────────────────────────────────────────┘
```

```gdscript
# 动画遮罩系统
class_name AnimationMaskSystem

extends Node

# 身体部位定义
var body_parts = {
    "head": [],
    "spine": [],
    "left_arm": [],
    "right_arm": [],
    "pelvis": [],
    "left_leg": [],
    "right_leg": []
}

# 遮罩定义
var masks = {
    "upper_body": ["head", "spine", "left_arm", "right_arm"],
    "lower_body": ["pelvis", "left_leg", "right_leg"],
    "full_body": ["head", "spine", "left_arm", "right_arm", "pelvis", "left_leg", "right_leg"],
    "arms_only": ["left_arm", "right_arm"]
}

var animation_player: AnimationPlayer

func _ready():
    animation_player = $AnimationPlayer

# 应用遮罩混合
func play_with_mask(anim_name: String, mask_name: String, blend_time: float = 0.2):
    var mask = masks.get(mask_name, [])
    
    if mask.is_empty():
        # 无遮罩，正常播放
        animation_player.play(anim_name, blend_time)
    else:
        # 使用遮罩播放
        _play_layered_animation(anim_name, mask, blend_time)

func _play_layered_animation(anim_name: String, mask: Array, blend_time: float):
    # 方法 1：使用 AnimationTree 的 Layer 节点
    var tree: AnimationTree = animation_player.get_tree()
    if tree:
        # 设置遮罩
        tree.set("parameters/" + mask_name + "/mask", mask)
        
        # 播放动画
        tree.set("parameters/" + mask_name + "/request", anim_name)
    
    # 方法 2：手动混合（简化）
    for track_index in range(animation_player.get_animation(anim_name).get_track_count()):
        var track_name = animation_player.get_animation(anim_name).track_get_name(track_index)
        
        # 检查轨道是否在遮罩内
        if _track_in_mask(track_name, mask):
            # 启用轨道
            animation_player.set_track_enabled(track_index, true)
        else:
            # 禁用轨道
            animation_player.set_track_enabled(track_index, false)

func _track_in_mask(track_name: String, mask: Array) -> bool:
    # 检查轨道是否属于遮罩中的身体部位
    for part in mask:
        if track_name.begins_with(part):
            return true
    return false

# 示例：上半身射击，下半身跑步
func combat_movement():
    # 下半身：跑步
    play_with_mask("run", "lower_body", 0.2)
    
    # 上半身：射击
    play_with_mask("shoot", "upper_body", 0.1)
```

### 9.2 加法动画混合（Additive Blending）

加法混合将一个动画叠加到另一个动画上，常用于面部表情、手势等。

```gdscript
# 加法动画混合
class_name AdditiveAnimationMixer

extends Node

@export var base_animation: String = "idle"
@export var additive_animations: Array[String] = ["wave", "nod", "look_around"]

var animation_player: AnimationPlayer
var animation_tree: AnimationTree

func _ready():
    animation_player = $AnimationPlayer
    animation_tree = $AnimationTree
    
    _setup_additive_blend_tree()

func _setup_additive_blend_tree():
    var tree = animation_tree
    
    # 创建基础动画节点
    var base_node = AnimationNodeAnimation.new()
    base_node.animation = base_animation
    tree.add_node("base", base_node)
    
    # 创建加法混合节点
    for i in range(additive_animations.size()):
        var anim_name = additive_animations[i]
        
        var add_node = AnimationNodeAdd2.new()
        tree.add_node("add_" + str(i), add_node)
        
        var anim_node = AnimationNodeAnimation.new()
        anim_node.animation = anim_name
        tree.add_node(anim_name, anim_node)
    
    # 连接节点（链式加法）
    # base → add_0 → add_1 → add_2 → output

# 设置加法动画权重
func set_additive_weight(anim_name: String, weight: float):
    var param_name = "parameters/add_" + anim_name + "/blend_amount"
    animation_tree.set(param_name, weight)

# 示例：混合多个表情
func play_expressions():
    # 基础： idle
    animation_tree.set("parameters/base/request", "idle")
    
    # 加法 1: 微笑（权重 0.5）
    set_additive_weight("smile", 0.5)
    
    # 加法 2: 眨眼（权重 1.0）
    set_additive_weight("blink", 1.0)
    
    # 加法 3: 点头（权重 0.3）
    set_additive_weight("nod", 0.3)
```

### 9.3 实时混合权重调整

```gdscript
# 动态混合权重控制器
class_name DynamicBlendWeightController

extends Node

@export var weight_parameter: String = "blend_weight"
@export var smoothing: float = 0.2

var target_weight: float = 0.0
var current_weight: float = 0.0
var animation_tree: AnimationTree

func _ready():
    animation_tree = $AnimationTree

func _process(delta):
    # 平滑过渡权重
    current_weight = lerp(current_weight, target_weight, smoothing * delta * 60.0)
    
    # 更新参数
    animation_tree.set("parameters/" + weight_parameter, current_weight)

# 示例：根据速度动态混合走路/跑步
func update_movement_blend(speed: float):
    var walk_speed = 2.0
    var run_speed = 6.0
    
    if speed < walk_speed:
        target_weight = 0.0  # 完全走路
    elif speed > run_speed:
        target_weight = 1.0  # 完全跑步
    else:
        # 线性插值
        target_weight = (speed - walk_speed) / (run_speed - walk_speed)

# 示例：根据距离动态混合瞄准
func update_aim_blend(target_distance: float):
    var close_range = 5.0
    var far_range = 20.0
    
    if target_distance < close_range:
        target_weight = 1.0  # 完全瞄准
    elif target_distance > far_range:
        target_weight = 0.0  # 不瞄准
    else:
        target_weight = 1.0 - (target_distance - close_range) / (far_range - close_range)
```

---

## 📝 本章总结（更新）

### 核心要点（更新）

1. **AnimationNodeBlend2 是基础**，用于两个动画的线性混合
2. **AnimationNodeAdd2 用于加法混合**，适合叠加效果
3. **AnimationNodeBlend3 用于三个动画的混合**，适合复杂场景
4. **分层动画混合**，可以分别控制不同身体部位
5. **动画混合优化**，包括缓存、LOD、压缩等
6. **1D/2D 混合树简化复杂混合**（新增）
7. **动画遮罩实现身体部位独立控制**（新增）
8. **加法混合用于表情和手势叠加**（新增）

### 关键术语（更新）

| 术语 | 解释 |
|------|------|
| AnimationNodeBlend2 | 两个动画的线性混合 |
| AnimationNodeAdd2 | 两个动画的加法混合 |
| AnimationNodeBlend3 | 三个动画的混合 |
| Layered Blending | 分层动画混合 |
| LOD | 细节层次，根据距离调整动画 |
| Blend Tree 1D | 一维混合树，单参数混合（新增） |
| Blend Tree 2D | 二维混合树，双参数混合（新增） |
| Animation Mask | 动画遮罩，控制混合部位（新增） |
| Additive Blending | 加法混合，叠加动画效果（新增） |