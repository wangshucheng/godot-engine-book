# 第 37 篇：动画系统基础

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 无（建议先读第一卷引擎基础）  
> **难度等级**: ⭐⭐ 中级

---

## 📖 本章导读

动画系统是游戏开发中实现角色和物体动态效果的关键组件。从简单的角色动画到复杂的机械动画，动画系统能够为游戏带来生动的视觉效果和交互体验。

Godot 提供了多种动画系统，包括动画播放器、动画混合器、动画控制器等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解动画系统的基本概念
- 掌握动画播放器使用
- 学会动画混合器应用
- 熟悉动画控制器
- 掌握骨骼动画系统

---

## 1. 动画系统基础

### 1.1 动画类型

```
动画类型分类:
┌─────────────────────────────────────────────────────────────┐
│                      动画类型                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 关键帧动画：通过关键帧定义动画（最常用）                │
│  2. 过渡动画：基于状态机自动切换动画                       │
│  3. 程序化动画：通过脚本生成动画                           │
│  4. 骨骼动画：基于骨骼系统的动画                          │
│  5. 视频动画：使用视频文件作为动画                          │
│  6. 2D 动画：2D 物体的动画                                 │
│  7. 3D 动画：3D 物体的动画                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 动画组件

```
动画系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      动画组件                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AnimationPlayer：动画播放器                               │
│  2. AnimationNodeStateMachine：动画状态机                    │
│  3. AnimationNodeBlendTree：动画混合树                        │
│  4. AnimationNodeBlendSpace1D / 2D：1D / 2D 混合空间          │
│  5. AnimationNodeAnimation：引用单个动画片段                  │
│  6. AnimationNodeBlend2 / Blend3：按权重混合多路输入          │
│  7. AnimationNodeTransition：多输入之间的条件切换             │
│  8. AnimationNodeTimeScale / TimeSeek：时间缩放与跳转         │
│  9. AnimationNodeStateMachinePlayback：状态机运行时控制器     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 动画流程

```
动画处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      动画处理流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 动画播放器接收时间更新信号                               │
│  2. 动画播放器调用动画节点处理动画                           │
│  3. 动画节点根据时间更新动画曲线                             │
│  4. 动画节点更新节点属性（位置、旋转、缩放）                 │
│  5. 节点应用变换到场景物体                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 动画时间

```gdscript
# 动画时间管理
class_name AnimationTimeManager

@export var playback_speed: float = 1.0
@export var time_scale: float = 1.0

var current_time: float = 0.0

func _process(delta):
    current_time += delta * playback_speed * time_scale

func get_time():
    return current_time

func reset_time():
    current_time = 0.0

func set_time(time: float):
    current_time = time
```

---

## 2. 动画播放器

### 2.1 基础动画播放器

```gdscript
# 基础动画播放器
class_name BasicAnimationPlayer

extends AnimationPlayer

@export var animation_name: String = "walk"
@export var loop: bool = true

func _ready():
    # 设置播放器
    if not animation_name.empty():
        play(animation_name)
    
    # 启用循环
    if loop:
        set_loop_mode(LoopMode.LOOP)

func _process(delta):
    # 检查动画是否播放完成
    if is_playing() and not loop:
        stop()

func play_animation(anim_name: String):
    if has_animation(anim_name):
        play(anim_name)
    else:
        print("Animation not found: ", anim_name)

func stop_animation():
    stop()
```

### 2.2 动画播放控制

```gdscript
# 动画播放控制
class_name AnimationController

@export var animation_player: AnimationPlayer
@export var animation_name: String

func _ready():
    if animation_player and not animation_name.empty():
        animation_player.play(animation_name)

func play():
    if animation_player and not animation_name.empty():
        animation_player.play(animation_name)

func stop():
    if animation_player:
        animation_player.stop()

func set_speed(speed: float):
    if animation_player:
        animation_player.set_speed_scale(speed)

func set_loop(loop: bool):
    if animation_player:
        animation_player.set_loop_mode(loop ? LoopMode.LOOP : LoopMode.ONCE)

func set_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)
```

### 2.3 动画事件

```gdscript
# 动画事件处理
class_name AnimationEventProcessor

extends Node3D

@export var animation_player: AnimationPlayer
@export var event_name: String

func _ready():
    if animation_player and not event_name.empty():
        animation_player.animation_finished.connect(_on_animation_finished)
        animation_player.animation_started.connect(_on_animation_started)

func _on_animation_started(anim_name: String):
    print("Animation started: ", anim_name)

func _on_animation_finished(anim_name: String):
    print("Animation finished: ", anim_name)
    # 可以在这里添加动画结束后的逻辑

func trigger_event(event_name: String):
    if animation_player:
        animation_player.seek(animation_player.length())
```

---

## 3. 动画状态机

### 3.1 状态机基础

```gdscript
# 用代码构建动画状态机（等价于在 AnimationTree 编辑器中连线）
class_name AnimationStateMachineBuilder

extends Node3D

@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback
var _current_state: StringName

func _ready() -> void:
    var state_machine := AnimationNodeStateMachine.new()

    # 1) add_node(name, node)：状态本身是任意 AnimationNode，
    #    播放单个动画片段时用 AnimationNodeAnimation
    for anim_name in ["Idle", "Walk", "Run"]:
        var anim := AnimationNodeAnimation.new()
        anim.animation = anim_name
        state_machine.add_node(anim_name, anim)

    # 2) add_transition(from, to, transition)：过渡规则由独立资源描述
    state_machine.add_transition("Idle", "Walk", _make_xfade(0.25))
    state_machine.add_transition("Walk", "Run", _make_xfade(0.20))
    state_machine.add_transition("Run", "Walk", _make_xfade(0.20))
    state_machine.add_transition("Walk", "Idle", _make_xfade(0.25))

    # 3) 挂到 AnimationTree 上，再取回运行时的 playback 对象
    tree.tree_root = state_machine
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    travel_to(&"Idle")

func _make_xfade(seconds: float) -> AnimationNodeStateMachineTransition:
    var t := AnimationNodeStateMachineTransition.new()
    t.xfade_time = seconds
    t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
    return t

func travel_to(state_name: StringName) -> void:
    playback.travel(state_name)

# 状态切换没有信号，需要轮询 get_current_node()
func _process(_delta: float) -> void:
    var current := playback.get_current_node()
    if current != _current_state:
        _current_state = current
        print("State changed to: ", current)
```

### 3.2 状态转换条件

```gdscript
# 转换条件由 AnimationNodeStateMachineTransition.advance_condition 描述，
# 条件值是挂在 AnimationTree 上的布尔开关，用 set_condition() 更新
class_name StateTransitionCondition

extends Node3D

@export var tree: AnimationTree
@export var transition_index: int = 0
@export var condition_name: StringName = &"can_walk"

@onready var _character: CharacterBody3D = $CharacterBody3D

func _ready() -> void:
    var state_machine := tree.tree_root as AnimationNodeStateMachine
    if state_machine == null:
        push_error("tree_root 不是 AnimationNodeStateMachine")
        return

    var transition := state_machine.get_transition(transition_index)
    transition.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED
    transition.advance_condition = condition_name

func _physics_process(_delta: float) -> void:
    # 每帧只更新条件开关，切换本身由状态机完成，无需手动调用切换
    tree.set_condition(condition_name, _character.velocity.length() > 0.5)
```

### 3.3 过渡推进模式

```gdscript
# AnimationNodeStateMachineTransition 提供三种推进方式，混用才能覆盖常见需求
class_name TransitionAdvanceModes

extends Node

func configure_transitions(state_machine: AnimationNodeStateMachine) -> void:
    # 1) AUTO：交叉淡入结束后自动切到目标状态
    var auto_t := state_machine.get_transition(0)
    auto_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
    auto_t.xfade_time = 0.2

    # 2) ENABLED：仅当条件为 true 时允许切换（配合 tree.set_condition）
    var cond_t := state_machine.get_transition(1)
    cond_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED
    cond_t.advance_condition = &"can_jump"

    # 3) DISABLED：暂时禁用该过渡，例如受击动画未播完前禁止移动
    var locked_t := state_machine.get_transition(2)
    locked_t.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_DISABLED

# 需要“硬切”时用 start()：跳过过渡，立即进入目标状态
func teleport_to(playback: AnimationNodeStateMachinePlayback, state_name: StringName) -> void:
    playback.start(state_name, true)
```

---

## 4. 动画混合树

### 4.1 混合树基础

```gdscript
# 用代码构建 1D 混合空间（速度驱动的 Idle → Walk → Run）
class_name BlendTreeBuilder

extends Node3D

@export var tree: AnimationTree

func _ready() -> void:
    # AnimationNodeBlendSpace1D 把一个标量参数映射为若干动画的权重
    var space := AnimationNodeBlendSpace1D.new()
    space.min_space = 0.0
    space.max_space = 5.0

    # add_blend_point(node, pos)：pos 是该动画在数轴上的位置
    space.add_blend_point(_anim_node(&"Idle"), 0.0)
    space.add_blend_point(_anim_node(&"Walk"), 1.5)
    space.add_blend_point(_anim_node(&"Run"), 4.0)

    tree.tree_root = space
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

# 混合位置通过 AnimationTree 的参数路径写入
func update_blend(speed: float) -> void:
    tree.set("parameters/blend_position", speed)
```

### 4.2 节点级混合

```gdscript
# 用 AnimationNodeBlendTree 把多个 AnimationNode 串起来
class_name ParameterBlend

extends Node3D

@export var tree: AnimationTree

func _ready() -> void:
    var blend_tree := AnimationNodeBlendTree.new()

    # walk 状态
    var walk := AnimationNodeAnimation.new()
    walk.animation = &"Walk"
    blend_tree.add_node("walk", walk)

    # 时间缩放节点：整体加减速，不影响混合权重
    var time_scale := AnimationNodeTimeScale.new()
    blend_tree.add_node("time_scale", time_scale)

    # connect_node(输入节点名, 输入端口索引, 输出节点名)
    # BlendTree 内置一个名为 "output" 的输出节点
    blend_tree.connect_node("walk", 0, "time_scale")
    blend_tree.connect_node("time_scale", 0, "output")

    tree.tree_root = blend_tree
    tree.active = true

# 参数路径格式：parameters/<节点名>/<参数名>
func update_parameter(speed: float) -> void:
    tree.set("parameters/time_scale/scale", clampf(speed, 0.2, 2.0))
```

### 4.3 2D 混合空间

```gdscript
# 2D 混合空间：适合用两个参数（如速度与朝向）驱动动画
class_name BlendSpace2DBuilder

extends Node

func build_2d_blend(tree: AnimationTree) -> void:
    var space := AnimationNodeBlendSpace2D.new()

    # 依次添加混合点，索引按添加顺序为 0、1、2、3
    space.add_blend_point(_anim_node(&"Idle"), Vector2(0, 0))         # 0
    space.add_blend_point(_anim_node(&"WalkForward"), Vector2(0, 1.5)) # 1
    space.add_blend_point(_anim_node(&"WalkLeft"), Vector2(-1.5, 0))   # 2
    space.add_blend_point(_anim_node(&"WalkRight"), Vector2(1.5, 0))   # 3

    # 必须显式声明三角剖分，否则两个轴之间的插值不生效
    space.add_triangle(0, 1, 2)
    space.add_triangle(0, 2, 3)

    tree.tree_root = space
    tree.active = true

func _anim_node(anim_name: StringName) -> AnimationNodeAnimation:
    var anim := AnimationNodeAnimation.new()
    anim.animation = anim_name
    return anim

# 2D 混合空间的参数是 Vector2
func update_blend(tree: AnimationTree, velocity: Vector2) -> void:
    tree.set("parameters/blend_position", velocity)
```

---

## 5. 骨骼动画系统

### 5.1 骨骼基础

```gdscript
# 骨骼系统基础：Skeleton3D 用「索引」访问骨骼，没有 bone 节点对象
class_name SkeletonSystem

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer

func _ready() -> void:
    if skeleton and animation_player:
        # AnimationPlayer 通过 NodePath 指明要驱动的骨架
        animation_player.root_node = animation_player.get_path_to(skeleton)

func play_animation(anim_name: StringName) -> void:
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)

# 骨骼姿势按 索引 + 姿势分量 读写
func set_bone_transform(bone_name: StringName, transform: Transform3D) -> void:
    var idx := skeleton.find_bone(bone_name)   # 找不到时返回 -1
    if idx == -1:
        return
    skeleton.set_bone_pose_position(idx, transform.origin)
    skeleton.set_bone_pose_rotation(idx, transform.basis.get_rotation_quaternion())
    skeleton.set_bone_pose_scale(idx, transform.basis.get_scale())

func get_bone_transform(bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    return skeleton.get_bone_pose(idx) if idx != -1 else Transform3D()

# 遍历骨架中的全部骨骼
func list_bones() -> Array[String]:
    var names: Array[String] = []
    for i in skeleton.get_bone_count():
        names.append(skeleton.get_bone_name(i))
    return names
```

### 5.2 骨骼动画播放器

```gdscript
# 骨骼动画播放器：曲线求值与骨骼驱动由引擎完成，脚本只做查询与二次修正
class_name SkeletonAnimationPlayer

extends AnimationPlayer

func _ready() -> void:
    if has_animation(&"walk"):
        play(&"walk")

func _process(_delta: float) -> void:
    if not is_playing():
        return

    var time := get_current_animation_position()
    var anim := get_animation(&"walk")
    if anim == null:
        return

    # Animation 由「轨道 + 关键帧」组成，并没有按骨骼组织的“帧对象”。
    # 需要精确控制时遍历轨道读取关键帧时间点即可。
    var total_tracks := anim.get_track_count()
    for track_idx in total_tracks:
        var key_count := anim.track_get_key_count(track_idx)
        if key_count > 0 and time > anim.track_get_key_time(track_idx, key_count - 1):
            _on_track_finished(track_idx)

func _on_track_finished(_track_idx: int) -> void:
    # 轨道播放结束的回调点，可按需叠加修正
    pass
```

### 5.3 骨骼绑定

```gdscript
# 骨骼绑定：MeshInstance3D 用 NodePath 指向 Skeleton3D
class_name SkeletonBinder

extends Node3D

@export var mesh: MeshInstance3D
@export var skeleton: Skeleton3D

func _ready() -> void:
    if mesh and skeleton:
        # 注意：骨骼层级来自导入的模型（glTF/FBX），不要在代码里手工拼骨骼
        mesh.skeleton = mesh.get_path_to(skeleton)

# 让任意节点跟随某根骨骼运动，用 BoneAttachment3D 而不是手算变换
func attach_to_bone(target: Node3D, bone_name: StringName) -> BoneAttachment3D:
    var attachment := BoneAttachment3D.new()
    attachment.bone_name = bone_name
    skeleton.add_child(attachment)
    target.reparent(attachment)
    return attachment
```

---

## 6. 动画优化

### 6.1 动画压缩

```gdscript
# 动画瘦身：Animation 没有“按骨骼取帧”的接口，只能按轨道操作
class_name AnimationCompressor

@export var max_keys_per_track: int = 100

func compress_animation(anim: Animation) -> void:
    # 提示：导入面板里的 Animation → Optimizer/Compression 通常比运行时删帧更有效，
    # 这里是运行时兜底方案。
    var removed := 0

    for track_idx in anim.get_track_count():
        var key_count := anim.track_get_key_count(track_idx)
        if key_count <= max_keys_per_track:
            continue

        # 等间隔抽样保留，从后往前删以避免索引前移
        var step := int(ceil(float(key_count) / max_keys_per_track))
        for i in range(key_count - 1, -1, -1):
            if i % step != 0:
                anim.track_remove_key(track_idx, i)
                removed += 1

    if removed > 0:
        print("已删除 %d 个关键帧" % removed)
    else:
        print("关键帧数量已在阈值内")
```

### 6.2 动画LOD

```gdscript
# 动画LOD
class_name AnimationLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_animations: Array = ["walk", "run", "idle"]

func update_lod(camera_position: Vector3, character: Node3D):
    var distance = camera_position.distance_to(character.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_animations.size() - 1)
    
    # 更新动画
    if lod_index < lod_animations.size():
        character.animation_player.play(lod_animations[lod_index])
```

### 6.3 动画缓存

```gdscript
# 动画缓存：运行时代码合成 Animation 资源
class_name AnimationCache

var cache: Dictionary = {}

func get_animation(anim_name: StringName) -> Animation:
    if cache.has(anim_name):
        return cache[anim_name]

    var anim := Animation.new()
    anim.length = 1.0

    # add_track() 只声明轨道类型；驱动哪个属性由 track_set_path() 决定
    var track_idx := anim.add_track(Animation.TYPE_TRANSFORM_3D)
    anim.track_set_path(track_idx, NodePath("Skeleton3D:Root"))

    # 3D 变换轨道的关键帧值固定为 [位置, 旋转(四元数), 缩放]
    anim.track_insert_key(track_idx, 0.0, [Vector3.ZERO, Quaternion.IDENTITY, Vector3.ONE])
    anim.track_insert_key(track_idx, 1.0, [Vector3(0, 1, 0), Quaternion.IDENTITY, Vector3.ONE])

    cache[anim_name] = anim
    return anim

func clear_cache() -> void:
    cache.clear()
```

---

## 7. 实践：角色动画

### 7.1 基础角色动画

```gdscript
# 基础角色动画系统：AnimationTree 负责播放，脚本只驱动参数并查询状态
class_name CharacterAnimationSystem

extends Node3D

@export var tree: AnimationTree

var playback: AnimationNodeStateMachinePlayback
var _current_state: StringName

func _ready() -> void:
    tree.active = true
    playback = tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
    travel_to(&"Idle")

func _process(_delta: float) -> void:
    # 状态切换没有信号，靠轮询当前节点
    var current := playback.get_current_node()
    if current != _current_state:
        _current_state = current
        print("State changed to: ", current)

func travel_to(state_name: StringName) -> void:
    playback.travel(state_name)

# 混合参数通过参数路径写入
func set_blend_position(value: float) -> void:
    tree.set("parameters/blend_position", value)

# 注意：AnimationTree 挂载后会接管同一个 AnimationPlayer，
# 不要再对该 AnimationPlayer 直接调用 play()，否则两套驱动会互相覆盖。
func play_animation(anim_name: StringName) -> void:
    var player := tree.anim_player
    if player:
        tree.active = false          # 暂停树驱动，交还控制权
        player.play(anim_name)

func set_blend_parameter(name: String, value: float):
    if blend_tree and has_parameter(name):
        blend_tree.set_parameter(name, value)
```

### 7.2 骨骼动画系统

```gdscript
# 骨骼动画系统
class_name SkeletonAnimationSystem

extends Node3D

@export var skeleton: Skeleton3D
@export var animation_player: AnimationPlayer

func _ready():
    if skeleton and animation_player:
        # AnimationPlayer 通过 NodePath 指向被驱动的骨架
        animation_player.root_node = animation_player.get_path_to(skeleton)

func play_animation(anim_name: String):
    if animation_player and has_animation(anim_name):
        animation_player.play(anim_name)

func update_animation() -> void:
    if not is_playing():
        return

    # 曲线求值由引擎完成，脚本只需查询进度或读取骨骼姿势
    var time := get_current_animation_position()
    var anim := get_animation(&"walk")
    if anim == null:
        return
    print("播放中：%.2fs / %d 条轨道" % [time, anim.get_track_count()])

# 需要读取某根骨骼的当前姿势时，交给 Skeleton3D 而不是自己算帧
func get_bone_pose(skeleton: Skeleton3D, bone_name: StringName) -> Transform3D:
    var idx := skeleton.find_bone(bone_name)
    return skeleton.get_bone_pose(idx) if idx != -1 else Transform3D()
```

### 7.3 2D 动画系统

```gdscript
# 2D 动画系统
class_name SpriteAnimationSystem

extends Node2D

@export var sprite_frames: SpriteFrames
@export var animated_sprite: AnimatedSprite2D

func _ready() -> void:
    # 帧序列动画属于 AnimatedSprite2D + SpriteFrames；
    # AnimationPlayer 没有 sprite_frames 属性，它驱动的是属性轨道。
    if sprite_frames and animated_sprite:
        animated_sprite.sprite_frames = sprite_frames

func play_animation(anim_name: StringName) -> void:
    if animated_sprite and animated_sprite.sprite_frames.has_animation(anim_name):
        animated_sprite.play(anim_name)

func update_animation():
    if is_playing():
        update_sprite()

func update_sprite():
    # 获取当前动画帧
    var frame = get_frame()
    
    # 更新精灵
    sprite.texture = frame.texture
    sprite.position = frame.position
    sprite.rotation = frame.rotation
    sprite.scale = frame.scale
```

---

## 📝 本章总结

### 核心要点

1. **动画播放器是基础**，负责播放动画
2. **状态机用于复杂动画控制**，基于条件切换动画
3. **混合树用于参数化动画**，根据参数混合状态
4. **骨骼动画系统**，基于骨骼系统的动画
5. **动画优化**，包括压缩、LOD、缓存等

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationPlayer | 动画播放器，控制动画播放 |
| StateMachine | 状态机，基于状态切换动画 |
| BlendTree | 混合树，参数化动画混合 |
| Skeleton | 骨骼，动画系统的核心 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Animation](https://docs.godotengine.org/en/stable/tutorials/animation/animation.html)
- **源码位置**: `servers/animation/`
- **技术博客**: [Godot Animation System](https://godotengine.org/article/animation-system/)

---

## 📋 下一章预告

**第 38 篇：动画控制器**

- 动画控制器基础
- AnimationTree 与 AnimationPlayer
- 状态机与混合树
- 动画控制器应用

---

*写作时间：2026-03-20*  
*字数：约 8,500 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
