# 第 37 篇：动画系统基础

> **本卷定位**: 第四卷 动画系统（8 篇）  
> **前置知识**: 无（建议先读第一卷引擎基础）  
> **难度等级**: ⭐⭐ 中级

---

## 📖 本章导读

动画系统是游戏开发中实现角色和物体动态效果的关键组件。从简单的角色动画到复杂的机械动画，动画系统能够为游戏带来生动的视觉效果和交互体验。

本章是第四卷的**入门篇**，只讲三件事：动画系统的基本概念、`AnimationPlayer` 的正确用法、以及 `Skeleton3D` 姿势 API 的入门。

> **本卷分工**：状态机（`AnimationNodeStateMachine`）见第 43 篇，混合（`AnimationNodeBlendTree` / BlendSpace）见第 39 篇，"从脚本驱动一棵已配置好的动画树"见第 38 篇，骨骼与蒙皮的完整讲解见第 44 篇。**本章不重复这三块内容。**

---

## 🎯 学习目标

- 理解动画系统的基本概念与组件分工
- 掌握 `AnimationPlayer` 的播放、循环与事件用法
- 理解 `AnimationMixer` 抽象层与 Godot 3.x → 4.x 的属性迁移
- 熟悉 `Animation` 资源（轨道 / 关键帧 / 事件轨道）
- 掌握 `Skeleton3D` 姿势 API 的入门读写
- 了解动画压缩、LOD 与缓存的常见做法

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
│  1. AnimationMixer：动画播放器与动画树的共同基类            │
│  2. AnimationPlayer：单动画播放器（继承 AnimationMixer）    │
│  3. AnimationTree：动画树（继承 AnimationMixer）            │
│  4. AnimationLibrary / Animation：动画资源与资源库          │
│  5. AnimationNodeStateMachine：动画状态机                  │
│  6. AnimationNodeBlendTree：动画混合树                      │
│  7. AnimationNodeBlendSpace1D / 2D：1D / 2D 混合空间        │
│  8. AnimationNodeAnimation：引用单个动画片段                │
│  9. AnimationNodeBlend2 / Add2 / Blend3：按权重混合多路输入 │
│ 10. AnimationNodeTransition / OneShot：条件切换与一次性播放 │
│ 11. AnimationNodeTimeScale / TimeSeek：时间缩放与跳转       │
│ 12. AnimationNodeStateMachinePlayback：状态机运行时控制器   │
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
│  1. AnimationMixer 在 process 阶段推进时间                  │
│  2. AnimationTree 求值节点图，得到混合后的属性值            │
│  3. AnimationPlayer 播放单个 Animation 资源                 │
│  4. 曲线求值由引擎完成，脚本只负责读状态 / 写参数          │
│  5. 结果写入 Skeleton3D 姿势或普通节点属性                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

> **关键点**：Godot 4.x 里 `AnimationPlayer` 与 `AnimationTree` 都继承自 `AnimationMixer`，
> 播放与混合的底层实现都在 `AnimationMixer` 里，脚本侧的可见 API 主要是 `AnimationMixer` 的成员。
> 详见第 3 节。

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
    # 注意：循环模式是 Animation 资源上的属性，不是 AnimationPlayer 的方法。
    # Godot 3.x 的 set_loop_mode(LoopMode.LOOP) 在 4.x 中已不存在。
    if loop:
        var anim := get_animation(animation_name)
        if anim:
            anim.loop_mode = Animation.LOOP_LINEAR

func _process(delta):
    # 检查动画是否播放完成
    if is_playing() and not loop:
        stop()

func play_animation(anim_name: String):
    # has_animation() 定义在 AnimationMixer 上，AnimationPlayer 继承了它
    if has_animation(anim_name):
        play(anim_name)
    else:
        print("Animation not found: ", anim_name)

func stop_animation():
    stop()
```

**循环模式对照（4.x）**

| Godot 3.x（已废弃） | Godot 4.x |
|---|---|
| `player.set_loop_mode(LoopMode.LOOP)` | `anim.loop_mode = Animation.LOOP_LINEAR` |
| `player.set_loop_mode(LoopMode.ONCE)` | `anim.loop_mode = Animation.LOOP_NONE` |
| `LoopMode.PINGPONG` | `Animation.LOOP_PINGPONG` |

`AnimationPlayer` 在 4.x 里 **没有** `set_loop_mode()` / `get_loop_mode()`，也没有 `LoopMode` 枚举；
循环属于"被播放的那条 `Animation` 资源"的属性。`Animation` 资源上可写的循环常量有
`Animation.LOOP_NONE`（0）、`Animation.LOOP_LINEAR`（1）、`Animation.LOOP_PINGPONG`（2）。

### 2.2 动画播放控制

```gdscript
# 动画播放控制
class_name AnimationPlaybackHelper

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
        animation_player.speed_scale = speed

func set_loop(loop: bool):
    # 循环模式写在 Animation 资源上
    if animation_player == null:
        return
    var anim := animation_player.get_animation(animation_name)
    if anim:
        anim.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE

func set_animation(anim_name: String):
    # has_animation() 在 AnimationPlayer（AnimationMixer）上，不在普通 Node 上
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)
```

> **命名提示**：本类名从 `AnimationController` 改为 `AnimationPlaybackHelper`。
> Godot 4.x **没有** `AnimationController` 这个内置类；若脚本用 `class_name AnimationController`
> 再在别处声明 `func f(c: AnimationController)`，会解析到自定义类而不是引擎类，容易与其它章节冲突。

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

# AnimationMixer 的 animation_started / animation_finished 参数类型是 StringName
func _on_animation_started(anim_name: StringName):
    print("Animation started: ", anim_name)

func _on_animation_finished(anim_name: StringName):
    print("Animation finished: ", anim_name)
    # 可以在这里添加动画结束后的逻辑

func trigger_event(event_name: String):
    if animation_player:
        animation_player.seek(animation_player.current_animation_length)
```

> `AnimationMixer.animation_started` / `animation_finished` 的形参类型在官方类参考中就是
> **StringName**（不是 String）。回调签名写成 `String` 也能连上，但拿到的值类型与引擎声明不一致，
> 建议统一按 `StringName` 写。

---

## 3. AnimationMixer 抽象层与 3.x → 4.x 迁移

Godot 4.x 把"播放器"和"动画树"的公共部分抽到了基类 **`AnimationMixer`**：

```
Node
 └── AnimationMixer          ← 动画列表管理 + 播放 + 混合 + root_node
      ├── AnimationPlayer    ← 单条 Animation 播放
      └── AnimationTree      ← 节点图求值 + 参数
```

`AnimationMixer` 提供的能力（4.3 官方类参考，非穷举）：

| 类别 | 成员 |
|---|---|
| 动画库 | `add_animation_library` / `get_animation_library` / `remove_animation_library` / `rename_animation_library` / `get_animation_library_list` / `has_animation_library` |
| 动画查询 | `get_animation` / `has_animation` / `get_animation_list` / `find_animation` / `find_animation_library` |
| 播放控制 | `advance(delta)` / `capture(...)` / `clear_caches()` |
| 属性 | `active` / `root_node` / `callback_mode_process` / `callback_mode_method` / `callback_mode_discrete` / `deterministic` / `root_motion_track` / `audio_max_polyphony` / `reset_on_save` |
| 信号 | `animation_started` / `animation_finished` / `animation_list_changed` / `animation_libraries_updated` / `mixer_updated` / `mixer_applied` / `caches_cleared` |
| Root Motion | `get_root_motion_position()` / `get_root_motion_rotation()` / `get_root_motion_scale()` 及 `*_accumulator()` 变体 |

### 3.1 3.x → 4.x 属性对照

Godot 3.x 中挂在 `AnimationPlayer` 上的若干属性，在 4.x 里被上移到 `AnimationMixer` 并改名：

| Godot 3.x | Godot 4.x（推荐写法） | 备注 |
|---|---|---|
| `AnimationPlayer.root` | `AnimationMixer.root_node` | 3.x 的 `set_root()` 仍保留，但已标记 deprecated |
| `AnimationPlayer.process_callback` | `AnimationMixer.callback_mode_process` | 3.x 的 `set_process_callback()` 已 deprecated |
| `AnimationPlayer.method_call_mode` | `AnimationMixer.callback_mode_method` | 3.x 的 `set_method_call_mode()` 已 deprecated |
| `AnimationPlayer.playback_default_blend_time` | 仍在 `AnimationPlayer` 上 | 未迁移 |
| `AnimationPlayer.assigned_animation` | 仍在 `AnimationPlayer` 上 | 未迁移 |

`AnimationTree` 也只剩两个 deprecated 方法：`get_process_callback()` / `set_process_callback()`，
它们只是 `AnimationMixer.callback_mode_process` 的旧名入口。

### 3.2 手动驱动（不使用引擎的 process 回调）

需要在固定时间步 / 回放 / 网络同步等场景手动推进动画时，用
`AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL` + `advance(delta)`：

```gdscript
# 手动驱动 AnimationMixer：引擎不再自动推进，由 advance() 显式步进
class_name ManualDriveMixer

extends Node

@export var mixer: AnimationMixer

func _ready() -> void:
    # 关闭引擎自动推进
    mixer.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL

func step(delta: float) -> void:
    # AnimationMixer 没有 process() 方法，手动推进用 advance()
    mixer.advance(delta)
```

`callback_mode_process` 的三个取值：

| 常量 | 含义 |
|---|---|
| `ANIMATION_CALLBACK_MODE_PROCESS_IDLE` | 在 idle（process）帧推进，默认值 |
| `ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS` | 在物理帧推进，适合驱动物理体 |
| `ANIMATION_CALLBACK_MODE_PROCESS_MANUAL` | 不自动推进，需自行调用 `advance(delta)` |

> **常见错误**：`AnimationTree` 上没有 `process(delta)` 方法。4.3 的 `AnimationMixer` 方法表是
> `add_animation_library` / `advance` / `capture` / `clear_caches` / `find_animation` / `get_animation` /
> `has_animation` / …，**不含 `process()`**。在 `extends AnimationTree` 的脚本里写
> `func _process(delta): process(delta)` 会在运行时报
> `Invalid call. Nonexistent function 'process' in base 'AnimationTree'`。

---

## 4. 动画事件轨道与播放编排

`Animation` 资源由"轨道 + 关键帧"组成。除属性轨道外，Godot 提供两类**事件轨道**：

| 轨道类型常量 | 作用 | 关键帧值 |
|---|---|---|
| `Animation.TYPE_METHOD` | 调用目标对象上的方法 | `[对象: Object, 方法名: String, 参数: Array]` |
| `Animation.TYPE_AUDIO` | 播放一段音频 | `[流: AudioStream, 起始偏移: float]` |

```gdscript
# 用 TYPE_METHOD 轨道在动画特定时刻触发回调
class_name MethodTrackBuilder

extends Node

@export var animation_player: AnimationPlayer

func build_footstep_animation() -> void:
    var anim := Animation.new()
    anim.length = 1.0

    # 方法轨道：路径是「节点路径:方法名」
    var track := anim.add_track(Animation.TYPE_METHOD)
    anim.track_set_path(track, NodePath(".:_on_footstep"))
    anim.track_insert_key(track, 0.25, [get_parent(), "_on_footstep", []])

    # 音频轨道
    var audio_track := anim.add_track(Animation.TYPE_AUDIO)
    anim.track_set_path(audio_track, NodePath("."))
    anim.track_insert_key(audio_track, 0.25, [preload("res://footstep.ogg"), 0.0])

    # 写回 AnimationLibrary（Godot 4 起动画按库组织）
    var lib := animation_player.get_animation_library("")
    if lib:
        lib.add_animation(&"walk", anim)

func _on_footstep() -> void:
    print("footstep")
```

### 4.1 `animation_finished` 与 `queue()` 的配合

`AnimationPlayer.queue(name)` 可以把动画排队，等当前动画播完再播下一条；
`animation_finished` 信号在动画播完时触发（**循环动画不会触发该信号**）：

```gdscript
# 用队列串接动画，并在结束时回调
class_name AnimationSequencer

extends Node

@export var player: AnimationPlayer

func _ready() -> void:
    player.animation_finished.connect(_on_animation_finished)

func play_sequence() -> void:
    player.play(&"walk")
    player.queue(&"idle")

func _on_animation_finished(anim_name: StringName) -> void:
    print("finished: ", anim_name)
    if anim_name == &"idle":
        player.queue(&"walk")
```

> `queue()` 的官方说明：若当前播放的是**循环动画**，排队动画永远不会播放，
> 除非循环动画被某种方式停止。排队的键名同样遵守 `"库名/动画名"` 规则（默认库省略库名）。

---

## 5. 骨骼动画系统（入门）

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

    var time := current_animation_position
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

> 更完整的骨骼 / 蒙皮 / IK 讲解见第 44 篇《骨骼动画》。

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

> ⚠️ 示意数据（未附测试环境）：`lod_distances = [10, 30, 50]` 是常见的取值示例，
> 具体距离需要按角色大小、镜头 FOV 与目标机型自行实测。

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
@export var blend_tree: AnimationNodeBlendTree

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
    # tree.anim_player 是 NodePath（指向 AnimationPlayer 的路径），
    # 不是节点本身，必须 get_node() 之后才能调用方法。
    var player := get_node(tree.anim_player) as AnimationPlayer
    if player:
        tree.active = false          # 暂停树驱动，交还控制权
        player.play(anim_name)

# 混合量同样只能走参数路径：parameters/<节点名>/<参数名>
func set_blend_parameter(name: StringName, value: float) -> void:
    if blend_tree == null:
        return
    tree.set("parameters/%s/blend_position" % name, value)
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
    # has_animation() 在 AnimationPlayer（AnimationMixer）上，不在普通 Node 上
    if animation_player and animation_player.has_animation(anim_name):
        animation_player.play(anim_name)

func update_animation() -> void:
    if animation_player == null or not animation_player.is_playing():
        return

    # 曲线求值由引擎完成，脚本只需查询进度
    var time := animation_player.current_animation_position
    var anim := animation_player.get_animation(&"walk")
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
    # is_playing() 是 AnimationPlayer 的方法，Node2D 本身没有
    if animation_player and animation_player.is_playing():
        update_sprite()

func update_sprite():
    # AnimationPlayer 没有 get_frame()，也不存在"帧对象"这种能读出
    # texture/position/rotation/scale 的东西。
    # 4.x 驱动 AnimatedSprite2D 的标准做法是在动画里给 animated_sprite.frame
    # 打属性轨道；这里演示的是纯代码推进帧号的写法。

    # 更新精灵
    if not animated_sprite:
        return
    var anim := get_animation(&"walk")
    if anim == null:
        return
    # 按播放进度换算成帧号。
    # 注意：AnimatedSprite2D 没有 hframes/vframes，切图信息在 SpriteFrames 上，
    # 用 sprite_frames.get_frame_count() 取总帧数。
    var frames := animated_sprite.sprite_frames
    if frames == null:
        return
    var total_frames := frames.get_frame_count()
    if total_frames <= 0:
        return
    var idx := int(current_animation_position * total_frames) % total_frames
    animated_sprite.frame = idx
```

---

## 📝 本章总结

### 核心要点

1. **动画播放器是基础**，负责播放动画；循环模式写在 `Animation` 资源上，不是播放器方法
2. **`AnimationMixer` 是 4.x 的抽象基类**，`AnimationPlayer` 与 `AnimationTree` 都继承自它
3. **3.x → 4.x 的属性迁移**：`root` → `root_node`、`process_callback` → `callback_mode_process`、
   `method_call_mode` → `callback_mode_method`
4. **状态机**见第 43 篇，**混合树与混合空间**见第 39 篇，**驱动层**见第 38 篇
5. **骨骼动画**基于 `Skeleton3D` 的索引式姿势 API，完整讲解见第 44 篇
6. **动画优化**包括压缩、LOD、缓存等

### 关键术语

| 术语 | 解释 |
|------|------|
| AnimationPlayer | 动画播放器，控制动画播放 |
| AnimationMixer | 4.x 中 AnimationPlayer 与 AnimationTree 的共同基类 |
| AnimationLibrary | 4.x 的动画容器，动画键名为 `"库名/动画名"` |
| StateMachine | 状态机，基于状态切换动画（第 43 篇） |
| BlendTree | 混合树，参数化动画混合（第 39 篇） |
| Skeleton | 骨骼，动画系统的核心 |
| LOD | 细节层次，根据距离调整动画 |

---

## 🔗 延伸阅读

- **官方文档 · 动画教程索引**: <https://docs.godotengine.org/en/stable/tutorials/animation/index.html>
- **官方文档 · AnimationPlayer**: <https://docs.godotengine.org/en/stable/classes/class_animationplayer.html>
- **官方文档 · AnimationMixer**: <https://docs.godotengine.org/en/stable/classes/class_animationmixer.html>
- **官方文档 · Animation（资源）**: <https://docs.godotengine.org/en/stable/classes/class_animation.html>
- **官方文档 · AnimationLibrary**: <https://docs.godotengine.org/en/stable/classes/class_animationlibrary.html>
- **官方文档 · Skeleton3D**: <https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html>
- **源码位置**: `scene/animation/`（`animation_mixer.cpp`、`animation_player.cpp`、`animation_tree.cpp`、
  `animation_node_state_machine.cpp`、`animation_blend_space_1d.cpp`、`animation_blend_space_2d.cpp`、
  `tween.cpp`）、`scene/resources/animation.cpp`、`scene/resources/animation_library.cpp`

> **注意**：Godot 4.3 的 `servers/` 目录下**没有** `animation/` 子目录。
> `servers/` 只包含 audio / camera / debugger / display / extensions / movie_writer /
> navigation / physics_2d / physics_3d / rendering / text / xr 等服务端模块，
> 动画系统完全在 `scene/animation/` 与 `scene/resources/` 中实现。

---

## 📋 上下篇导航

**上一篇**: [第 36 篇：物理调试与问题排查](/articles/36-physics-debugging.md)
**下一篇**: [第 38 篇：动画控制器](/articles/38-animation-controller.md)

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

*写作时间：2026-03-20*  
*字数：约 1,400 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
