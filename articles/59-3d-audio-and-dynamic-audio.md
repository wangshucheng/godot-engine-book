# 第 59 篇：3D 音频和动态音频系统

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 48 章 音频效果器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

3D 音频和动态音频系统是现代游戏提升沉浸感的关键技术。通过空间音频定位、动态混音、自适应音乐等技术，可以为玩家带来身临其境的听觉体验。

本章将深入探讨 3D 音频空间化、动态混音、自适应音乐等核心技术。

先说清楚一件很容易被误解的事：**Godot 4.x 没有实现 HRTF（双耳渲染）**。
本章会明确划出这条边界，然后讲引擎真正提供的 3D 音频能力。

---

## 🎯 学习目标

- 理解 Godot 4 的 3D 音频能力边界（**含"引擎没有 HRTF"这件事**）
- 掌握 `AudioListener3D` 监听者模型与 `attenuation_model` 四种衰减模型
- 学会动态混音与侧链 ducking
- 熟悉自适应音乐（`AudioStreamPlaylist` / `AudioStreamInteractive`）
- 实施音频性能优化

---

## 1. 3D 音频空间化

### 1.1 空间音频原理

```
3D 音频定位线索:
┌─────────────────────────────────────────────────────────────┐
│ 线索类型          │ 描述                  │ 频率范围        │
├─────────────────────────────────────────────────────────────┤
│ ITD（时间差）     │ 双耳时间差异          │ <1500 Hz       │
│ IID（强度差）     │ 双耳强度差异          │ >1500 Hz       │
│ HRTF（头相关）    │ 耳廓滤波效应          │ 全频段         │
│ 混响              │ 房间反射              │ 全频段         │
│ 多普勒效应        │ 运动频率变化          │ 运动物体       │
└─────────────────────────────────────────────────────────────┘
```

> 这张表是**双耳渲染（binaural rendering）**的理论背景。
> Godot 4 只实现了其中的"幅度声像 + 距离衰减 + 低通衰减滤波 + 多普勒 + 混响"，
> **没有** ITD / ILD / HRTF 这三项双耳线索（详见 §1.2）。

### 1.2 Godot 4.x 的 3D 音频到底做了什么（以及没做什么）

> ⚠️ **重要边界**：Godot 4.x **没有实现**双耳渲染（HRTF，Head-Related Transfer Function）。
> 具体核验依据（4.7.2 官方源码）：
> - `doc/classes/AudioServer.xml` 的方法表里没有任何 `hrtf` 相关项；
> - `servers/audio/effects/` 目录下没有 HRTF 效果器；
> - `ProjectSettings` 的 `audio/*` 完整清单里没有 HRTF 设置项。
>
> 因此**不存在** `AudioServer.set_hrtf_enabled()` / `set_hrtf_interpolation_enabled()` 这类 API，
> 也**不存在**"项目设置 → Audio → Driver → HRTF Mode"这样的选项。
> 网上流传的 Godot 4 HRTF 教程几乎都是基于 Godot 3.x 的 `AudioListener` 时代写的。

Godot 4 的 3D 音频是**幅度声像 + 距离衰减 + 低通衰减滤波 + 多普勒 + 发声角度 + 区域混响**，
属于"单声道源 + 立体声扩展（amplitude panning）"的经典方案，
而不是基于 HRTF 的双耳卷积。

```gdscript
# 3D 音频空间化：Godot 4 的真实能力
class_name SpatialAudio3D

extends AudioStreamPlayer3D

# ⚠️ 引擎原生成员，不要重复 @export（会在解析期报 "Member ... redefined"）：
#   volume_db / pitch_scale / autoplay / unit_size / max_distance /
#   attenuation_model / attenuation_filter_db / attenuation_filter_cutoff_hz /
#   max_db / emission_angle_* / area_mask / panning_strength /
#   doppler_tracking / bus / stream / stream_paused
@export var listener_path: NodePath

func _ready():
    # ① 听者：Godot 4 用 AudioListener3D 决定"声音从哪里被听到"。
    #    默认从摄像机位置听到；加入 AudioListener3D 并 make_current() 后改由它决定。
    var listener := get_node_or_null(listener_path) as AudioListener3D
    if listener and not listener.is_current():
        listener.make_current()

    # ② 距离衰减：引擎按 attenuation_model 计算
    unit_size = 10.0            # 衰减因子，越大听得越远
    max_distance = 50.0         # 超过这个距离完全听不见
    attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE

    # ③ 远处的低通滤波：让远处的声音"闷"下来
    #    把 cutoff 提到 20500（人耳上限）即可关闭该滤波
    attenuation_filter_cutoff_hz = 5000.0
    attenuation_filter_db = -24.0

    # ④ 立体声扩展（amplitude panning）：左右声道的幅度差，不是双耳卷积
    panning_strength = 1.0

    # ⑤ 多普勒：用枚举选择计算步进，不是 doppler_scale 浮点数
    doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_PHYSICS_STEP

    # ⑥ 发声角度：只在这个锥形范围内不衰减
    emission_angle_enabled = true
    emission_angle_degrees = 45.0
    emission_angle_filter_attenuation_db = -12.0

    # ⑦ 区域混响：哪些 Area3D 层会影响这个播放器
    area_mask = 1

func set_attenuation_model(model: int) -> void:
    # 四种衰减模型（枚举 AudioStreamPlayer3D.AttenuationModel）：
    #   ATTENUATION_INVERSE_DISTANCE        线性反比
    #   ATTENUATION_INVERSE_SQUARE_DISTANCE  平方反比（最接近物理直觉）
    #   ATTENUATION_LOGARITHMIC              对数
    #   ATTENUATION_DISABLED                 不随距离衰减（仍保留声像）
    attenuation_model = model

func set_doppler_tracking(mode: int) -> void:
    # 多普勒的计算步进（枚举 AudioStreamPlayer3D.DopplerTracking）：
    #   DOPPLER_TRACKING_DISABLED      关闭
    #   DOPPLER_TRACKING_IDLE_STEP     每个处理帧（_process）计算
    #   DOPPLER_TRACKING_PHYSICS_STEP  每个物理帧计算（移动物体更平滑）
    doppler_tracking = mode
```

#### 想要真正的 HRTF 怎么办

| 路线 | 做法 | 代价 |
|---|---|---|
| GDExtension 插件 | 自己写一个双耳卷积节点（加载 SOFA / HRIR 数据，对左右耳脉冲响应做卷积） | 需要 C++ 与音频线程经验；卷积开销不小 |
| 第三方插件 | AssetLib 上的社区双耳渲染插件 | 维护状态与引擎版本兼容性要自己评估 |
| 退回立体声扩展 | 直接用引擎原生的幅度声像 + 距离衰减 | 前后定位不如 HRTF，但零成本、跨平台一致 |

> 在引擎里手工算 ITD / ILD 再乘到音量上**是行不通的**：
> ITD（双耳时间差）和 ILD（双耳强度差）需要的是**波形级**的双耳卷积，
> 靠"改一下左右声道增益"只能近似 ILD 覆盖的低频部分，
> 高频的耳廓滤波与相位差完全丢失——所以引擎里也就没有读这些值的接口。

---

## 2. 动态混音系统

### 2.1 动态混音原理

```
动态混音层次:
┌─────────────────────────────────────────────────────────────┐
│ 混音层级                                                    │
├─────────────────────────────────────────────────────────────┤
│ Master Bus（主总线）                                        │
│   ↓                                                         │
│ Music Bus（音乐）────→ 动态音量调整                         │
│   ↓                                                         │
│ SFX Bus（音效）────→ 优先级管理                            │
│   ↓                                                         │
│ Dialogue Bus（对话）─→ 强制 ducking                        │
│   ↓                                                         │
│ Ambience Bus（环境）─→ 淡入淡出                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 动态混音实现

```gdscript
# 动态混音管理器
class_name DynamicMixer

extends Node

# 音频总线索引
var music_bus: int = 0
var sfx_bus: int = 1
var dialogue_bus: int = 2
var ambience_bus: int = 3

# 混音状态
var current_state: String = "normal"
var state_volumes: Dictionary = {}

func _ready():
    _setup_audio_buses()
    _initialize_states()

func _setup_audio_buses():
    music_bus = AudioServer.get_bus_index("Music")
    sfx_bus = AudioServer.get_bus_index("SFX")
    dialogue_bus = AudioServer.get_bus_index("Dialogue")
    ambience_bus = AudioServer.get_bus_index("Ambience")

func _initialize_states():
    # 定义不同状态的混音配置
    state_volumes = {
        "normal": {
            "music": -10.0,
            "sfx": -5.0,
            "dialogue": -3.0,
            "ambience": -15.0
        },
        "combat": {
            "music": -5.0,      # 音乐提升
            "sfx": -3.0,        # 音效提升
            "dialogue": -3.0,
            "ambience": -20.0   # 环境音降低
        },
        "stealth": {
            "music": -15.0,     # 音乐降低
            "sfx": -8.0,        # 音效降低
            "dialogue": -3.0,
            "ambience": -10.0   # 环境音提升
        },
        "cutscene": {
            "music": -20.0,     # 音乐大幅降低
            "sfx": -15.0,       # 音效降低
            "dialogue": -3.0,   # 对话保持
            "ambience": -25.0   # 环境音大幅降低
        }
    }

# 切换混音状态
func set_mix_state(state: String, transition_time: float = 1.0):
    if not state_volumes.has(state):
        return
    
    current_state = state
    var target_volumes = state_volumes[state]
    
    # 平滑过渡
    _tween_bus_volume(music_bus, target_volumes["music"], transition_time)
    _tween_bus_volume(sfx_bus, target_volumes["sfx"], transition_time)
    _tween_bus_volume(dialogue_bus, target_volumes["dialogue"], transition_time)
    _tween_bus_volume(ambience_bus, target_volumes["ambience"], transition_time)

func _tween_bus_volume(bus_index: int, target_db: float, duration: float):
    var tween = create_tween()
    tween.tween_method(
        func(value): AudioServer.set_bus_volume_db(bus_index, value),
        AudioServer.get_bus_volume_db(bus_index),
        target_db,
        duration
    )

# 侧链压缩（Ducking）——用总线音量做 duck
func duck_audio(duck_bus: int, target_db: float, duration: float, attack: float = 0.1):
    # duration 是"恢复时长"；压低用 attack（默认 0.1 秒）
    var original_db = AudioServer.get_bus_volume_db(duck_bus)
    
    # 降低音量
    var tween = create_tween()
    tween.tween_method(
        func(value): AudioServer.set_bus_volume_db(duck_bus, value),
        original_db,
        target_db,
        attack
    )
    
    # 恢复音量
    tween.tween_method(
        func(value): AudioServer.set_bus_volume_db(duck_bus, value),
        target_db,
        original_db,
        duration
    )

# 更"专业"的 ducking：给总线挂压缩器，用另一条总线做侧链检测
func setup_sidechain_ducking(music_bus_name: String, trigger_bus_name: String):
    # AudioEffectCompressor.sidechain 的官方说明：
    # "Reduce the sound level using another audio bus for threshold detection."
    # 也就是：触发总线一出声，本总线就被压下去——比手动改音量更平滑。
    var bus_idx := AudioServer.get_bus_index(music_bus_name)
    if bus_idx == -1:
        return
    var compressor := AudioEffectCompressor.new()
    compressor.sidechain = trigger_bus_name
    compressor.threshold = -20.0
    compressor.ratio = 8.0
    compressor.attack_us = 50.0
    compressor.release_ms = 300.0
    AudioServer.add_bus_effect(bus_idx, compressor)

# 对话播放时自动降低其他音轨
func play_dialogue(dialogue_audio: AudioStream):
    # 降低音乐和环境音
    duck_audio(music_bus, -20.0, 2.0)
    duck_audio(ambience_bus, -25.0, 2.0)
    
    # 播放对话
    var player = AudioStreamPlayer.new()
    player.stream = dialogue_audio
    player.bus = "Dialogue"
    add_child(player)
    player.play()
    
    # 播放完成后恢复
    player.finished.connect(func():
        set_mix_state(current_state, 1.0)
        player.queue_free()
    )
```

---

## 3. 自适应音乐系统

### 3.1 自适应音乐原理

```
自适应音乐层次:
┌─────────────────────────────────────────────────────────────┐
│ 音乐层              │ 触发条件              │ 过渡方式      │
├─────────────────────────────────────────────────────────────┤
│ 探索层（平静）      │ 无战斗                │ 淡入淡出      │
│ 紧张层（悬疑）      │ 发现敌人              │ 交叉淡出      │
│ 战斗层（激烈）      │ 进入战斗              │ 小节对齐*     │
│ 胜利层（高潮）      │ 战斗胜利              │ 立即切换      │
│ 失败层（低沉）      │ 战斗失败              │ 淡入          │
└─────────────────────────────────────────────────────────────┘
```

> \* "小节对齐"不是靠手写计时器做到的：引擎真正提供的是
> `AudioStreamInteractive` 的过渡时机（`TRANSITION_FROM_TIME_NEXT_BEAT` /
> `TRANSITION_FROM_TIME_NEXT_BAR`），它依赖 `AudioStream._get_bpm()` 报告的节拍信息。
> 见 §3.2。

### 3.2 自适应音乐实现

```gdscript
# 自适应音乐：引擎原生方案（AudioStreamInteractive）
#
# ⚠️ AudioStreamInteractive / AudioStreamPlaylist 来自 modules/interactive_music，
#    官方发行版默认启用；如果你用的是关掉了该模块的自定义构建，这两个类就不存在。
#    运行期可以自检：ClassDB.class_exists("AudioStreamInteractive")
class_name AdaptiveMusicInteractive

extends Node

@export var exploration_music: AudioStream
@export var tension_music: AudioStream
@export var combat_music: AudioStream

const CLIP_EXPLORATION := 0
const CLIP_TENSION := 1
const CLIP_COMBAT := 2

var stream_interactive: AudioStreamInteractive
var player: AudioStreamPlayer

func _ready():
    _build_stream()
    _build_player()

func _build_stream():
    stream_interactive = AudioStreamInteractive.new()
    stream_interactive.clip_count = 3
    stream_interactive.initial_clip = CLIP_EXPLORATION

    stream_interactive.set_clip_name(CLIP_EXPLORATION, &"exploration")
    stream_interactive.set_clip_stream(CLIP_EXPLORATION, exploration_music)
    stream_interactive.set_clip_name(CLIP_TENSION, &"tension")
    stream_interactive.set_clip_stream(CLIP_TENSION, tension_music)
    stream_interactive.set_clip_name(CLIP_COMBAT, &"combat")
    stream_interactive.set_clip_stream(CLIP_COMBAT, combat_music)

    # 过渡参数：
    #   from_time —— 什么时候切（IMMEDIATE / NEXT_BEAT / NEXT_BAR / END）
    #   to_time   —— 目标 clip 从哪里开始（SAME_POSITION / START）
    #   fade_mode —— 怎么切（DISABLED / IN / OUT / CROSS / AUTOMATIC）
    #   fade_beats—— 淡出长度（以拍计）
    # 这就是"小节对齐"的真正实现：引擎按 AudioStream._get_bpm() 找到下一小节的时机。
    stream_interactive.add_transition(
        CLIP_EXPLORATION, CLIP_TENSION,
        AudioStreamInteractive.TRANSITION_FROM_TIME_NEXT_BAR,
        AudioStreamInteractive.TRANSITION_TO_TIME_SAME_POSITION,
        AudioStreamInteractive.FADE_CROSS,
        4.0, false, -1, false
    )
    stream_interactive.add_transition(
        CLIP_TENSION, CLIP_COMBAT,
        AudioStreamInteractive.TRANSITION_FROM_TIME_NEXT_BAR,
        AudioStreamInteractive.TRANSITION_TO_TIME_SAME_POSITION,
        AudioStreamInteractive.FADE_CROSS,
        4.0, false, -1, false
    )
    # 战斗结束 → 探索：立刻切换 + 淡入
    stream_interactive.add_transition(
        CLIP_COMBAT, CLIP_EXPLORATION,
        AudioStreamInteractive.TRANSITION_FROM_TIME_IMMEDIATE,
        AudioStreamInteractive.TRANSITION_TO_TIME_START,
        AudioStreamInteractive.FADE_IN,
        2.0, false, -1, false
    )

func _build_player():
    player = AudioStreamPlayer.new()
    player.bus = "Music"
    add_child(player)
    player.stream = stream_interactive
    player.play()
```

```gdscript
# 自适应音乐：纯手工对照方案（多播放器交叉淡出）
#
# 这是"没有引擎支持时自己造"的写法：结构简单，但**做不到小节对齐**——
# AudioStreamPlayer 不知道 BPM，只能按墙钟时间做等长交叉淡出。
# 要小节对齐请用上面的 AudioStreamInteractive。
class_name AdaptiveMusicManual

extends Node

@export var exploration_music: AudioStream
@export var tension_music: AudioStream
@export var combat_music: AudioStream
@export var victory_music: AudioStream
@export var defeat_music: AudioStream

# 过渡配置
@export var crossfade_time: float = 2.0

# 状态
var current_layer: String = "exploration"
var target_layer: String = "exploration"
var music_players: Dictionary = {}

func _ready():
    _setup_music_layers()

func _setup_music_layers():
    # 创建音乐播放器
    var layers = ["exploration", "tension", "combat", "victory", "defeat"]
    
    for layer in layers:
        var player = AudioStreamPlayer.new()
        player.bus = "Music"
        player.volume_db = -80.0  # 静音
        add_child(player)
        music_players[layer] = player
    
    # 播放初始层
    _play_layer("exploration")

func _process(_delta: float) -> void:
    # 检查状态变化
    _update_music_state()

func _update_music_state() -> void:
    var new_state = _determine_music_state()
    
    if new_state != target_layer:
        _transition_to_layer(new_state)

func _determine_music_state() -> String:
    # 根据游戏状态决定音乐层
    if is_in_combat():
        return "combat"
    elif is_enemy_nearby():
        return "tension"
    elif is_player_healthy():
        return "exploration"
    else:
        return "tension"

func _transition_to_layer(new_layer: String) -> void:
    target_layer = new_layer
    
    var current_player = music_players[current_layer]
    var target_player = music_players[target_layer]
    
    # 交叉淡出（等长，按墙钟时间）
    var tween = create_tween()
    
    # 淡出当前层
    tween.tween_property(current_player, "volume_db", -80.0, crossfade_time)
    
    # 淡入目标层
    target_player.volume_db = -80.0
    target_player.play()
    tween.parallel().tween_property(target_player, "volume_db", 0.0, crossfade_time)
    
    # 停止当前层
    tween.tween_callback(func(): current_player.stop())
    
    current_layer = target_layer

func _play_layer(layer: String) -> void:
    var player = music_players[layer]
    player.stream = _get_music_for_layer(layer)
    player.play()
    player.volume_db = 0.0

func _get_music_for_layer(layer: String) -> AudioStream:
    match layer:
        "exploration": return exploration_music
        "tension": return tension_music
        "combat": return combat_music
        "victory": return victory_music
        "defeat": return defeat_music
    return exploration_music

# 辅助函数
func is_in_combat() -> bool:
    # 检查是否在战斗中
    return false

func is_enemy_nearby() -> bool:
    # 检查是否有敌人在附近
    return false

func is_player_healthy() -> bool:
    # 检查玩家健康状态
    return true
```

---

## 4. 音频性能优化

### 4.1 音频池

```gdscript
# 音频播放器池
class_name AudioPool

extends Node

@export var pool_size: int = 20
@export var auto_expand: bool = true

var available_players: Array = []
var active_players: Array = []

func _ready():
    _initialize_pool()

func _initialize_pool():
    for i in range(pool_size):
        var player = AudioStreamPlayer3D.new()
        player.bus = "SFX"
        add_child(player)
        available_players.append(player)
        
        # 连接完成信号
        player.finished.connect(_on_player_finished.bind(player))

func play_sound(stream: AudioStream, position: Vector3, volume_db: float = 0.0) -> AudioStreamPlayer3D:
    var player = _get_available_player()
    
    if not player:
        if auto_expand:
            player = _create_new_player()
        else:
            push_warning("Audio pool exhausted!")
            return null
    
    player.stream = stream
    player.global_transform.origin = position
    player.volume_db = volume_db
    player.play()
    
    active_players.append(player)
    
    return player

func _get_available_player() -> AudioStreamPlayer3D:
    if available_players.size() > 0:
        return available_players.pop_front()
    return null

func _create_new_player() -> AudioStreamPlayer3D:
    var player = AudioStreamPlayer3D.new()
    player.bus = "SFX"
    add_child(player)
    player.finished.connect(_on_player_finished.bind(player))
    return player

func _on_player_finished(player: AudioStreamPlayer3D):
    active_players.erase(player)
    player.stream = null
    available_players.append(player)

# 预加载常用音效
func preload_sounds(sound_paths: Array):
    for path in sound_paths:
        var stream = load(path)
        # 缓存到内存
```

### 4.2 音频 LOD

```gdscript
# 音频 LOD 系统
class_name AudioLOD

extends Node

@export var lod_distances: Array[float] = [20.0, 50.0, 100.0]

enum LODLevel {
    FULL,      # 0-20m: 完整音质
    MEDIUM,    # 20-50m: 中等音质
    LOW,       # 50-100m: 低音质
    DISABLED   # 100m+: 静音
}

func get_audio_lod(distance: float) -> LODLevel:
    if distance < lod_distances[0]:
        return LODLevel.FULL
    elif distance < lod_distances[1]:
        return LODLevel.MEDIUM
    elif distance < lod_distances[2]:
        return LODLevel.LOW
    else:
        return LODLevel.DISABLED

func apply_audio_lod(player: AudioStreamPlayer3D, lod: LODLevel):
    # ⚠️ AudioStreamPlayer3D 没有 attenuation 属性（那是 AudioStreamPlayer2D 的），
    #    也没有 attenuation_distance。3D 的衰减由
    #    unit_size + max_distance + attenuation_model 三者共同决定。
    match lod:
        LODLevel.FULL:
            player.volume_db = 0.0
            player.max_distance = 100.0
            player.unit_size = 20.0
            player.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE
        LODLevel.MEDIUM:
            player.volume_db = -5.0
            player.max_distance = 50.0
            player.unit_size = 10.0
            player.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE
        LODLevel.LOW:
            player.volume_db = -10.0
            player.max_distance = 20.0
            player.unit_size = 5.0
            player.attenuation_model = AudioStreamPlayer3D.ATTENUATION_LOGARITHMIC
        LODLevel.DISABLED:
            player.volume_db = -80.0
            player.stop()
```

---

## 📝 本章总结

### 核心要点

1. **Godot 4.x 没有 HRTF**：3D 音频 = 幅度声像 + 距离衰减 + 低通衰减滤波 + 多普勒 + 发声角度 + 区域混响
2. **听者由 `AudioListener3D` 决定**，默认是摄像机位置；`make_current()` 后改由它决定
3. **动态混音管理音频层次**，侧链 ducking 用 `AudioEffectCompressor.sidechain`
4. **自适应音乐**优先用 `AudioStreamPlaylist` / `AudioStreamInteractive`（能做小节对齐）
5. **音频池与 LOD 降低负载**，复用播放器、按距离简化

### 关键术语

| 术语 | 解释 |
|------|------|
| HRTF | 头部相关传输函数；Godot 4.x **未实现** |
| Amplitude Panning | 幅度声像；Godot 4 的 3D 定位手段 |
| `AudioListener3D` | 3D 听者节点，`make_current()` 后生效 |
| `attenuation_model` | 距离衰减模型，4 种枚举 |
| `emission_angle` | 发声角度；锥形外额外衰减 |
| `area_mask` | 影响该播放器的 `Area3D` 层（区域混响 / 总线重定向） |
| `doppler_tracking` | 多普勒的计算步进（处理帧 / 物理帧） |
| `AudioStreamPlaylist` | 顺序播放的音频流列表（`modules/interactive_music`） |
| `AudioStreamInteractive` | 带"clip + 过渡时机"的交互式音乐流（`modules/interactive_music`） |
| Sidechain | 侧链；用另一条总线做阈值检测 |

### 性能优化清单

> ⚠️ 示意数据（未附测试环境）：下面的数值是**经验建议区间**，不是实测基准。
> 实际并发上限取决于平台、混音线程预算、音频长度与效果器数量，
> 必须在目标设备上实测。

```
✅ 音频优化清单:
□ 使用音频池（20-50 个播放器）
□ 实施音频 LOD（按距离简化 attenuation_model 与 max_distance）
□ 限制并发音频源（<30）
□ 压缩音频文件（Vorbis）
□ 流式加载大文件
□ 禁用不可见音频源
□ 使用总线管理音量
```

---

## 🔗 延伸阅读

- **官方文档**: [3D audio](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **官方文档**: [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **类参考**: [AudioStreamPlayer3D](https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer3d.html)
- **类参考**: [AudioListener3D](https://docs.godotengine.org/en/stable/classes/class_audiolistener3d.html)
- **源码位置**: `scene/3d/audio_stream_player_3d.h`、`servers/audio/audio_server.cpp`、`modules/interactive_music/`

---

## 📋 下一章预告

**第 60 篇：C# 集成和脚本性能优化**

- C# 与 GDScript 的取舍
- 脚本层的性能剖析
- 跨语言调用的开销

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 48 篇：音频效果器](/articles/48-audio-effects.md)
**下一篇**: [第 62 篇：音频分析和语音系统](/articles/62-audio-analysis-and-voice.md)

---

*写作时间：2026-03-21*  
*字数：约 1,200 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
