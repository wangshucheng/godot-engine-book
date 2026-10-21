# 第 46 篇：音频播放器

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 45 章 音频系统  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

音频播放器是游戏音频系统的核心组件，负责播放各种音频资源。从简单的音效播放到复杂的音频混合，音频播放器能够为游戏提供丰富的听觉体验。

Godot 提供了多种音频播放器，包括 2D 音频播放器、3D 音频播放器、音频流播放器等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解音频播放器的基本概念
- 掌握 2D 音频播放器
- 学会 3D 音频播放器
- 熟悉音频流播放器
- 掌握音频播放器优化

---

## 1. 音频播放器基础

### 1.1 音频播放器类型

```
音频播放器类型:
┌─────────────────────────────────────────────────────────────┐
│                      音频播放器类型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioStreamPlayer：非定位音频播放器（UI / BGM）         │
│  2. AudioStreamPlayer2D：2D 定位音频播放器                  │
│  3. AudioStreamPlayer3D：3D 定位音频播放器                  │
│  4. AudioStreamMicrophone：麦克风输入（AudioStream 资源）   │
│  5. AudioStreamRandomizer：随机挑选子流的包装器             │
│  6. AudioStreamPolyphonic：多声道音频流                     │
│  7. AudioStreamGenerator：程序化生成音频的流                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 音频播放器组件

```
音频播放器组件:
┌─────────────────────────────────────────────────────────────┐
│                      音频播放器组件                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioStreamPlayer：非定位音频播放器节点                 │
│  2. AudioStreamPlayer2D / 3D：定位音频播放器节点            │
│  3. AudioStream：音频流资源基类                             │
│  4. AudioStreamOggVorbis：OGG Vorbis 音频流                 │
│  5. AudioStreamWAV：WAV 音频流                              │
│  6. AudioStreamMP3：MP3 音频流                              │
│  7. AudioStreamGenerator：程序化音频流                      │
│  8. AudioStreamPlayback：音频播放接口                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 音频播放器流程

```
音频播放器处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      音频播放器处理流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 音频播放器接收音频资源                                  │
│  2. 音频播放器解码音频数据                                  │
│  3. 音频播放器应用音量和音调                                │
│  4. 音频播放器处理 3D 空间定位                              │
│  5. 音频播放器输出到音频总线                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 非定位音频播放器（AudioStreamPlayer）

### 2.1 基础 AudioStreamPlayer

```gdscript
# 非定位音频播放器基础
#
# 官方定义："plays an audio stream non-positionally"——它不定位，
# 适合 UI、菜单、背景音乐；要做空间定位请用 AudioStreamPlayer2D / 3D。
class_name BasicAudioStreamPlayer

extends AudioStreamPlayer

# ⚠️ volume_db / pitch_scale / autoplay 都是 AudioStreamPlayer 的原生成员，
# 在子类里重复 @export 会让 GDScript 4 在**解析期**就报：
#   Member "volume_db" redefined (original in native class 'AudioStreamPlayer')
# 这里只声明引擎没有的字段。
@export var stream_path: String = ""
@export var loop_enabled: bool = false

func _ready():
    # 加载音频流
    if stream_path != "":
        var loaded := load(stream_path)
        if loaded is AudioStream:
            stream = loaded

    # 演示如何修改引擎原生属性
    volume_db = 0.0
    pitch_scale = 1.0

    # ⚠️ 循环不在播放器上设置：
    #   AudioStreamPlayer 没有 loop / loop_mode 属性，也没有 LOOP_FORWARD 常量
    #   （LOOP_FORWARD 属于 AudioStreamWAV.LoopMode 枚举）。
    #   循环要设在"流"上：
    #     AudioStreamOggVorbis / AudioStreamMP3 → loop(bool) + loop_offset(float)
    #     AudioStreamWAV                      → loop_mode + loop_begin + loop_end
    #   注意：改的是共享资源，会影响所有使用同一份流的播放器。
    if loop_enabled:
        set_loop(true)

    # 自动播放（autoplay 是引擎属性，节点入树时会自动 play）
    if autoplay:
        play()

func play_audio():
    # 播放音频
    play()

func stop_audio():
    # 停止音频
    stop()

func pause_audio():
    # 暂停音频：AudioStreamPlayer 没有 pause() 方法，
    # 只有 stream_paused 属性（也没有 set_stream_paused() 脚本方法）。
    stream_paused = true

func resume_audio():
    # 恢复音频：把 stream_paused 置回 false，才会从暂停处继续。
    # 注意 play() 是"从头重播"，不能用来"恢复暂停"。
    stream_paused = false

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_loop(enabled: bool):
    # 设置循环（设在流上，不在播放器上）
    if stream is AudioStreamOggVorbis:
        (stream as AudioStreamOggVorbis).loop = enabled
    elif stream is AudioStreamMP3:
        (stream as AudioStreamMP3).loop = enabled
    elif stream is AudioStreamWAV:
        # WAV 的循环区间 loop_begin / loop_end（单位：采样数）
        # 会在导入 WAV 时自动带过来；只切模式的话要确认区间已就位。
        (stream as AudioStreamWAV).loop_mode = (
            AudioStreamWAV.LOOP_FORWARD if enabled else AudioStreamWAV.LOOP_DISABLED
        )

func set_loop_offset(offset: float):
    # 设置循环起点偏移（秒）
    if stream is AudioStreamOggVorbis:
        (stream as AudioStreamOggVorbis).loop_offset = offset
    elif stream is AudioStreamMP3:
        (stream as AudioStreamMP3).loop_offset = offset

func fade_in(duration: float):
    # 淡入
    var tween = create_tween()
    tween.tween_method(set_volume, 0.0, db_to_linear(volume_db), duration)

func fade_out(duration: float):
    # 淡出
    var tween = create_tween()
    tween.tween_method(set_volume, db_to_linear(volume_db), 0.0, duration)
    tween.tween_callback(stop_audio)

# 播放状态与播放位置直接用引擎原生成员/方法：
#   player.playing                 → 是否正在播放
#   player.get_playback_position() → 当前播放位置（秒）
# 不要包一层同名函数：既遮蔽原生方法，也会造成无限自递归。
```

### 2.2 音频播放器管理器

```gdscript
# 音频播放器管理器
class_name AudioStreamPlayerManager

extends Node

var players = []
var max_players: int = 10

func create_player(stream_path: String) -> AudioStreamPlayer:
    # 创建音频播放器
    if players.size() < max_players:
        var player = AudioStreamPlayer.new()
        player.stream = load(stream_path)
        add_child(player)
        players.append(player)
        return player
    else:
        # 如果达到最大播放器数量，复用最早的播放器
        var oldest_player = players[0]
        oldest_player.stream = load(stream_path)
        players.push_back(players.pop_front())  # 移动到末尾
        return oldest_player

func play_sound(stream_path: String, volume: float = 1.0, pitch: float = 1.0):
    # 播放音效
    var player = create_player(stream_path)
    player.volume_db = linear_to_db(volume)
    player.pitch_scale = pitch
    player.play()
    
    # 连接完成信号以自动清理。
    # ⚠️ create_player() 在池满时会**复用**同一个播放器，
    #    每次都 connect 会让同一个节点累积多条 finished 连接，
    #    所以先用同样的 Callable 形态判断是否已连接。
    var on_finished := _on_player_finished.bind(player)
    if not player.finished.is_connected(on_finished):
        player.finished.connect(on_finished)

func _on_player_finished(player: AudioStreamPlayer):
    # 播放完成后的处理
    if players.has(player):
        players.erase(player)
        player.queue_free()

func stop_all():
    # 停止所有播放器
    for player in players:
        if player and is_instance_valid(player):
            player.stop()
            # 断开时必须用与连接时**完全一致**的 Callable 形态
            # （这里连接的是 _on_player_finished.bind(player)）
            var on_finished := _on_player_finished.bind(player)
            if player.finished.is_connected(on_finished):
                player.finished.disconnect(on_finished)
            player.queue_free()
    players.clear()

func set_global_volume(volume: float):
    # 设置全局音量
    for player in players:
        if player and is_instance_valid(player):
            player.volume_db = linear_to_db(volume)

func set_global_pitch(pitch: float):
    # 设置全局音调
    for player in players:
        if player and is_instance_valid(player):
            player.pitch_scale = pitch
```

### 2.3 音频播放器池

```gdscript
# 音频播放器池
class_name AudioStreamPlayerPool

extends Node

var pool = []
var pool_size: int = 10

func _ready():
    # 初始化播放器池
    initialize_pool()

func initialize_pool():
    # 创建播放器池
    for i in range(pool_size):
        var player = AudioStreamPlayer.new()
        player.bus = "SFX"  # 设置音频总线
        player.autoplay = false
        add_child(player)
        pool.append(player)

func get_player() -> AudioStreamPlayer:
    # 获取可用播放器
    if pool.size() > 0:
        return pool.pop_back()
    else:
        # 如果池为空，创建新的播放器
        var player = AudioStreamPlayer.new()
        player.bus = "SFX"
        add_child(player)
        return player

func return_player(player: AudioStreamPlayer):
    # 归还播放器到池
    if pool.size() < pool_size:
        player.stop()
        player.seek(0)
        pool.append(player)
    else:
        # 池已满，销毁播放器
        player.queue_free()

func play_sound(stream_path: String, volume: float = 1.0):
    # 使用池播放音效
    var player = get_player()
    player.stream = load(stream_path)
    player.volume_db = linear_to_db(volume)
    player.play()
    
    # 连接完成信号以归还播放器。
    # ⚠️ 池里的播放器会被复用，每次都 connect 会累积多条 finished 连接。
    # 先用同样的 Callable 形态判断是否已连接。
    var on_finished := _on_sound_finished.bind(player)
    if not player.finished.is_connected(on_finished):
        player.finished.connect(on_finished)

func _on_sound_finished(player: AudioStreamPlayer):
    # 音效播放完成
    var on_finished := _on_sound_finished.bind(player)
    if player.finished.is_connected(on_finished):
        player.finished.disconnect(on_finished)
    return_player(player)

func get_pool_size() -> int:
    # 获取池大小
    return pool.size()

func get_available_count() -> int:
    # 获取可用数量
    return pool.size()
```

---

## 3. 3D 定位音频播放器

### 3.1 基础 AudioStreamPlayer3D

```gdscript
# 3D 定位音频播放器基础
class_name BasicAudioStreamPlayer3D

extends AudioStreamPlayer3D

# ⚠️ volume_db / pitch_scale / autoplay / unit_size / max_distance /
#    max_db / attenuation_filter_db / area_mask / panning_strength
#    全是原生成员，重复 @export 会在解析期报 "Member ... redefined"。
@export var stream_path: String = ""

func _ready():
    # 加载音频流
    if stream_path != "":
        var loaded := load(stream_path)
        if loaded is AudioStream:
            stream = loaded

    # 演示如何修改引擎原生属性
    volume_db = 0.0
    pitch_scale = 1.0

    # Godot 4 的 3D 衰减参数：
    #   unit_size         —— 衰减因子
    #   max_distance      —— 完全听不见的距离（>0 才生效）
    #   attenuation_model —— 衰减曲线类型
    # ⚠️ 没有 attenuation_distance，也没有 min_distance
    unit_size = 10.0
    max_distance = 50.0
    attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
    attenuation_filter_db = -24.0
    max_db = 3.0
    area_mask = 1
    panning_strength = 1.0

func play_audio():
    # 播放音频
    play()

func stop_audio():
    # 停止音频
    stop()

func pause_audio():
    # 暂停音频：用 stream_paused 属性，没有 pause() 方法
    stream_paused = true

func resume_audio():
    # 恢复音频
    stream_paused = false

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_attenuation_model(model: int):
    # 设置衰减模型（枚举 AudioStreamPlayer3D.AttenuationModel）
    attenuation_model = model

func set_max_distance(distance: float):
    # 设置最大距离
    max_distance = distance

func set_attenuation_filter(filter_db: float):
    # 设置远处低通滤波的衰减量
    attenuation_filter_db = filter_db

func set_panning_strength(strength: float):
    # 设置立体声扩展强度
    panning_strength = strength

func fade_in(duration: float):
    # 淡入
    var tween = create_tween()
    tween.tween_method(set_volume, 0.0, db_to_linear(volume_db), duration)

func fade_out(duration: float):
    # 淡出
    var tween = create_tween()
    tween.tween_method(set_volume, db_to_linear(volume_db), 0.0, duration)
    tween.tween_callback(stop_audio)
```

### 3.2 3D 音频播放器控制器

```gdscript
# 3D 音频播放器控制器
class_name AudioStreamPlayer3DController

extends Node3D

@export var player_3d: AudioStreamPlayer3D
@export var stream_path: String = ""
@export var unit_size: float = 10.0
@export var max_distance: float = 50.0
@export var follow_target: NodePath
# 听者节点：Godot 4 的听者由 AudioListener3D 决定
# （默认从摄像机位置听到，加入 AudioListener3D 并 make_current() 后改由它决定）
@export var listener_path: NodePath

var target: Node3D

func _ready():
    # 初始化 3D 音频播放器
    if player_3d:
        if stream_path != "":
            player_3d.stream = load(stream_path)
        player_3d.unit_size = unit_size
        player_3d.max_distance = max_distance

    # 获取跟随目标
    if follow_target:
        target = get_node(follow_target) as Node3D

    # 把自己注册为当前听者
    var listener := _get_listener()
    if listener:
        listener.make_current()

func _process(_delta: float) -> void:
    # 更新 3D 音频播放器
    if target:
        # 跟随目标
        global_transform.origin = target.global_transform.origin

func _get_listener() -> AudioListener3D:
    if listener_path.is_empty():
        return null
    var node := get_node_or_null(listener_path) as AudioListener3D
    if node and not node.is_current():
        node.make_current()
    return node

func play_sound():
    # 播放音效
    if player_3d:
        player_3d.play()

func stop_sound():
    # 停止音效
    if player_3d:
        player_3d.stop()

func pause_sound():
    # 暂停音效：用 stream_paused 属性
    if player_3d:
        player_3d.stream_paused = true

func resume_sound():
    # 恢复音效
    if player_3d:
        player_3d.stream_paused = false

func set_volume(volume: float):
    # 设置音量
    if player_3d:
        player_3d.volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    if player_3d:
        player_3d.pitch_scale = pitch

func set_attenuation_params(new_unit_size: float, new_max_dist: float):
    # 设置衰减参数
    # ⚠️ AudioStreamPlayer3D 没有 min_distance：
    #   近距离由 unit_size 决定，远距离由 max_distance 截断。
    if player_3d:
        player_3d.unit_size = new_unit_size
        player_3d.max_distance = new_max_dist

func set_follow_target(new_target: Node3D):
    # 设置跟随目标
    target = new_target

func get_distance_to_listener() -> float:
    # 获取到监听者的距离
    # 用 AudioListener3D 的位置，而不是 get_viewport().get_camera_3d()：
    # 后者绕开了 Godot 4 的监听者模型。
    var listener := _get_listener()
    if listener == null:
        return 0.0
    return global_transform.origin.distance_to(listener.global_transform.origin)

func is_within_range() -> bool:
    # 检查是否在范围内
    var distance = get_distance_to_listener()
    return distance <= max_distance

func update_attenuation():
    # 衰减由引擎按 attenuation_model 计算，脚本不要再自己乘一遍音量
    # （那会和引擎的衰减叠乘，导致音量曲线失真）。
    if player_3d:
        player_3d.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE
```

### 3.3 3D 音频播放器池

```gdscript
# 3D 音频播放器池
class_name AudioStreamPlayer3DPool

extends Node

var pool = []
var pool_size: int = 10

func _ready():
    # 初始化 3D 播放器池
    initialize_pool()

func initialize_pool():
    # 创建 3D 播放器池
    for i in range(pool_size):
        var player = AudioStreamPlayer3D.new()
        player.bus = "SFX"  # 设置音频总线
        player.autoplay = false
        player.attenuation_filter_db = -24.0
        # ⚠️ 没有 attenuation_distance：近距用 unit_size，远距用 max_distance
        player.unit_size = 10.0
        player.max_distance = 50.0
        add_child(player)
        pool.append(player)

func get_player() -> AudioStreamPlayer3D:
    # 获取可用 3D 播放器
    if pool.size() > 0:
        return pool.pop_back()
    else:
        # 如果池为空，创建新的 3D 播放器
        var player = AudioStreamPlayer3D.new()
        player.bus = "SFX"
        player.attenuation_filter_db = -24.0
        player.unit_size = 10.0
        player.max_distance = 50.0
        add_child(player)
        return player

func return_player(player: AudioStreamPlayer3D):
    # 归还 3D 播放器到池
    if pool.size() < pool_size:
        player.stop()
        player.seek(0)
        pool.append(player)
    else:
        # 池已满，销毁播放器
        player.queue_free()

func play_3d_sound(stream_path: String, position: Vector3, volume: float = 1.0):
    # 使用池播放 3D 音效
    var player = get_player()
    player.stream = load(stream_path)
    player.global_transform.origin = position
    player.volume_db = linear_to_db(volume)
    player.play()
    
    # 连接完成信号以归还播放器（池复用前先判断是否已连接）
    var on_finished := _on_3d_sound_finished.bind(player)
    if not player.finished.is_connected(on_finished):
        player.finished.connect(on_finished)

func _on_3d_sound_finished(player: AudioStreamPlayer3D):
    # 3D 音效播放完成
    var on_finished := _on_3d_sound_finished.bind(player)
    if player.finished.is_connected(on_finished):
        player.finished.disconnect(on_finished)
    return_player(player)

func get_pool_size() -> int:
    # 获取池大小
    return pool.size()

func get_available_count() -> int:
    # 获取可用数量
    return pool.size()

func play_3d_sound_with_params(stream_path: String, position: Vector3, 
                               volume: float = 1.0, pitch: float = 1.0, 
                               min_dist: float = 1.0, max_dist: float = 10.0):
    # 使用参数播放 3D 音效
    var player = get_player()
    player.stream = load(stream_path)
    player.global_transform.origin = position
    player.volume_db = linear_to_db(volume)
    player.pitch_scale = pitch
    # ⚠️ 没有 min_distance，用 unit_size 表达"近处多响"的尺度
    player.unit_size = min_dist
    player.max_distance = max_dist
    player.play()
    
    # 连接完成信号以归还播放器
    player.finished.connect(_on_3d_sound_finished.bind(player))
```

---

## 4. 音频流播放器

### 4.1 音频流类型

```gdscript
# 音频流类型
class_name AudioStreamTypes

extends Node

func create_ogg_stream(path: String) -> AudioStreamOggVorbis:
    # 创建 OGG 音频流（类名是 AudioStreamOggVorbis，不是 AudioStreamOGGVorbis）
    return load(path) as AudioStreamOggVorbis

func create_wav_stream(path: String) -> AudioStreamWAV:
    # 创建 WAV 音频流
    return load(path) as AudioStreamWAV

func create_mp3_stream(path: String) -> AudioStreamMP3:
    # 创建 MP3 音频流
    return load(path) as AudioStreamMP3

func create_generator_stream(mix_rate: float = 22050.0) -> AudioStreamGenerator:
    # 创建程序化音频流
    var gen := AudioStreamGenerator.new()
    gen.mix_rate = mix_rate
    gen.buffer_length = 0.5
    return gen

func get_audio_format(path: String) -> String:
    # 获取音频格式
    # ⚠️ 4.x 没有 AudioStreamSample（那是 3.x 的类型，doc/classes 里已删除）
    if path.ends_with(".ogg"):
        return "OGG"
    elif path.ends_with(".wav"):
        return "WAV"
    elif path.ends_with(".mp3"):
        return "MP3"
    else:
        # 4.x 不支持 FLAC / Opus / MIDI，内置模块只有 vorbis / ogg / minimp3
        return "UNSUPPORTED"
```

### 4.2 引擎真正支持的音频格式

| 格式 | 4.x 是否内置 | 资源类 | 关键属性 |
|------|--------------|--------|----------|
| WAV | ✅ | `AudioStreamWAV` | `format`：`FORMAT_8_BITS` / `FORMAT_16_BITS` / `FORMAT_IMA_ADPCM` / `FORMAT_QOA`；循环用 `loop_mode` + `loop_begin` + `loop_end` |
| Ogg Vorbis | ✅ | `AudioStreamOggVorbis` | 循环用 `loop` + `loop_offset`；还带 `bpm` / `beat_count` / `bar_beats` |
| MP3 | ✅ | `AudioStreamMP3` | 循环用 `loop` + `loop_offset` |
| FLAC | ❌ | — | 4.x 没有内置解码器（`doc/classes/AudioStreamFLAC.xml` 不存在），需先转成 Ogg/WAV，或自行写 GDExtension |
| Opus | ❌ | — | 4.x 没有内置解码器（`AudioStreamOpus.xml` 不存在）；低延迟语音要走 WebRTC 或第三方库 |
| MIDI | ❌ | — | 4.x 没有内置 MIDI 合成器 |

> 引擎的音频模块只有三个：`modules/vorbis`（Vorbis 解码）、`modules/ogg`（Ogg 容器）、`modules/minimp3`（MP3 解码）。
> `AudioStreamSample`（3.x）与 `AudioStreamResource` 在 4.x 中均已不存在；
> 运行时生成/改写 PCM 用 `AudioStreamWAV.data`，程序化生成用 `AudioStreamGenerator`（见 §4.5）。

### 4.3 音频流播放器

```gdscript
# 音频流播放器
class_name AudioStreamPlayerAdvanced

extends AudioStreamPlayer

# ⚠️ volume_db / pitch_scale / autoplay 都是原生成员，重复 @export 会解析报错
@export var stream_path: String = ""
@export var stream_type: String = "AUTO"  # AUTO, OGG, WAV, MP3
@export var loop_enabled: bool = false

var current_stream: AudioStream

func _ready():
    # 加载音频流
    current_stream = load_stream(stream_path)
    if current_stream:
        stream = current_stream

    # 演示如何修改引擎原生属性
    volume_db = 0.0
    pitch_scale = 1.0

    # 循环设在流上（见 §2.1）
    if loop_enabled:
        set_loop(true)

    # 自动播放
    if autoplay:
        play()

func load_stream(path: String) -> AudioStream:
    # 加载音频流
    var resource = load(path)
    if resource is AudioStream:
        return resource
    return null

func play_stream(new_stream_path: String):
    # 播放指定音频流
    var new_stream = load_stream(new_stream_path)
    if new_stream:
        stream = new_stream
        play()

func play_audio():
    # 播放音频
    if stream:
        play()

func stop_audio():
    # 停止音频
    stop()

func pause_audio():
    # 暂停音频：用 stream_paused 属性
    stream_paused = true

func resume_audio():
    # 恢复音频
    stream_paused = false

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_loop(enabled: bool):
    # 设置循环（设在流上）
    if stream is AudioStreamOggVorbis:
        (stream as AudioStreamOggVorbis).loop = enabled
    elif stream is AudioStreamMP3:
        (stream as AudioStreamMP3).loop = enabled
    elif stream is AudioStreamWAV:
        (stream as AudioStreamWAV).loop_mode = (
            AudioStreamWAV.LOOP_FORWARD if enabled else AudioStreamWAV.LOOP_DISABLED
        )

func get_stream_info() -> Dictionary:
    # 获取音频流信息
    var info = {}
    if stream:
        info["name"] = stream.resource_path
        info["length"] = stream.get_length() if stream.has_method("get_length") else 0
        # 循环状态来自"流"，播放器本身没有 loop 属性
        var looping := false
        if stream is AudioStreamOggVorbis:
            looping = (stream as AudioStreamOggVorbis).loop
        elif stream is AudioStreamMP3:
            looping = (stream as AudioStreamMP3).loop
        elif stream is AudioStreamWAV:
            looping = (stream as AudioStreamWAV).loop_mode != AudioStreamWAV.LOOP_DISABLED
        info["loop"] = looping
    return info

func fade_in(duration: float):
    # 淡入
    var tween = create_tween()
    tween.tween_method(set_volume, 0.0, db_to_linear(volume_db), duration)

func fade_out(duration: float):
    # 淡出
    var tween = create_tween()
    tween.tween_method(set_volume, db_to_linear(volume_db), 0.0, duration)
    tween.tween_callback(stop_audio)
```

### 4.4 音频流管理器

```gdscript
# 音频流管理器
class_name AudioStreamManager

extends Node

var stream_cache = {}
var active_players = []

func preload_stream(stream_path: String):
    # 预加载音频流
    if not stream_cache.has(stream_path):
        var stream = load(stream_path)
        if stream is AudioStream:
            stream_cache[stream_path] = stream
            print("Preloaded stream: ", stream_path)

func get_stream(stream_path: String) -> AudioStream:
    # 获取音频流
    if stream_cache.has(stream_path):
        return stream_cache[stream_path]
    
    # 如果未缓存，加载并缓存
    var stream = load(stream_path)
    if stream is AudioStream:
        stream_cache[stream_path] = stream
        return stream
    return null

func play_stream_once(stream_path: String, volume: float = 1.0):
    # 播放一次性音频流
    var stream = get_stream(stream_path)
    
    # 创建临时播放器
    var player = AudioStreamPlayer.new()
    player.stream = stream
    player.volume_db = linear_to_db(volume)
    
    # 连接完成信号以清理资源（Godot 4 用 Callable 形式）
    player.finished.connect(player.queue_free)
    
    # 添加到场景
    add_child(player)
    player.play()
    
    # 添加到活跃播放器列表
    active_players.append(player)

func play_3d_stream_once(stream_path: String, position: Vector3, volume: float = 1.0):
    # 播放一次性 3D 音频流
    var stream = get_stream(stream_path)
    
    # 创建临时 3D 播放器
    var player = AudioStreamPlayer3D.new()
    player.stream = stream
    player.global_transform.origin = position
    player.volume_db = linear_to_db(volume)
    
    # 连接完成信号以清理资源（Godot 4 用 Callable 形式）
    player.finished.connect(player.queue_free)
    
    # 添加到场景
    add_child(player)
    player.play()
    
    # 添加到活跃播放器列表
    active_players.append(player)

func play_looped_stream(stream_path: String, volume: float = 0.8):
    # 播放循环音频流
    var stream = get_stream(stream_path)
    
    # 创建循环播放器
    var player = AudioStreamPlayer.new()
    player.stream = stream
    player.volume_db = linear_to_db(volume)
    # ⚠️ AudioStreamPlayer 没有 loop_mode，也没有 AudioStreamPlayer.LOOP_FORWARD：
    #   LOOP_FORWARD 属于 AudioStreamWAV.LoopMode。循环要设在"流"上。
    if stream is AudioStreamOggVorbis:
        (stream as AudioStreamOggVorbis).loop = true
    elif stream is AudioStreamMP3:
        (stream as AudioStreamMP3).loop = true
    elif stream is AudioStreamWAV:
        (stream as AudioStreamWAV).loop_mode = AudioStreamWAV.LOOP_FORWARD
    
    # 添加到场景
    add_child(player)
    player.play()
    
    # 添加到活跃播放器列表
    active_players.append(player)

func stop_all_streams():
    # 停止所有音频流
    for player in active_players:
        if player and is_instance_valid(player):
            player.stop()
            player.queue_free()
    
    active_players.clear()

func unload_unused_streams():
    # 卸载未使用的音频流
    var unused_paths = []
    for path in stream_cache:
        var is_used = false
        for player in active_players:
            if player and is_instance_valid(player) and player.stream == stream_cache[path]:
                is_used = true
                break
        
        if not is_used:
            unused_paths.append(path)
    
    for path in unused_paths:
        stream_cache.erase(path)
        print("Unloaded unused stream: ", path)

func get_active_stream_count() -> int:
    # 获取活跃音频流数量
    return active_players.size()

func get_cached_stream_count() -> int:
    # 获取缓存音频流数量
    return stream_cache.size()
```

---

### 4.5 程序化音频：AudioStreamGenerator

`AudioStreamGenerator` 是一个"由脚本往里灌数据"的音频流：播放器自己不会发声，
需要拿到 `AudioStreamGeneratorPlayback` 并不断 `push_frame()` / `push_buffer()`。

```gdscript
# 程序化音频：AudioStreamGenerator
class_name ProceduralAudio

extends Node

var playback: AudioStreamGeneratorPlayback
var sample_hz: float = 22050.0
var phase: float = 0.0
var freq_hz: float = 440.0

func _ready():
    var generator := AudioStreamGenerator.new()
    generator.mix_rate = sample_hz
    generator.buffer_length = 0.5

    var player := AudioStreamPlayer.new()
    player.stream = generator
    add_child(player)
    player.play()

    # 只有拿到 playback 对象才能往里推数据
    playback = player.get_stream_playback() as AudioStreamGeneratorPlayback

func _process(_delta: float) -> void:
    _fill_buffer()

func _fill_buffer() -> void:
    # get_frames_available() 返回还能塞多少帧；
    # 不及时填满就会 underrun（爆音）。
    var frames := playback.get_frames_available()
    var increment := freq_hz / sample_hz
    for i in range(frames):
        playback.push_frame(Vector2.ONE * sin(phase * TAU))
        phase = fmod(phase + increment, 1.0)

func push_samples(samples: PackedVector2Array) -> void:
    # 批量推送：先问 can_push_buffer()，能一次性塞进去就 push_buffer()
    if playback.can_push_buffer(samples.size()):
        playback.push_buffer(samples)
    else:
        # 塞不下就退化成逐帧
        for s in samples:
            if not playback.can_push_buffer(1):
                break
            playback.push_frame(s)
```

> `AudioStreamGenerator` 在 GDScript 里逐帧推的开销不小，官方文档建议优先用 C# 或
> GDExtension 实现；坚持用 GDScript 时把 `mix_rate` 降到 11025 / 22050 Hz 会好很多。

---

## 5. 音频播放器优化

### 5.1 音频播放器缓存

```gdscript
# 音频播放器缓存
class_name AudioPlayerCache

# ⚠️ 必须 extends Node：脚本要挂在节点上才能 add_child；
#    而且 AudioStreamPlayer 不在场景树里就不会发声。
extends Node

var cache = {}

func get_player(player_name: String) -> AudioStreamPlayer:
    if cache.has(player_name):
        return cache[player_name]
    
    var player = AudioStreamPlayer.new()
    # ⚠️ 必须 add_child 到场景树：
    #   1) 不入树 → 不会播放；
    #   2) queue_free() 对未入树的节点不生效，缓存清理不掉。
    add_child(player)
    cache[player_name] = player
    return player

func get_3d_player(player_name: String) -> AudioStreamPlayer3D:
    if cache.has(player_name + "_3d"):
        return cache[player_name + "_3d"]
    
    var player = AudioStreamPlayer3D.new()
    add_child(player)
    cache[player_name + "_3d"] = player
    return player

func clear_cache():
    for key in cache:
        if cache[key] and is_instance_valid(cache[key]):
            cache[key].queue_free()
    cache.clear()
```

### 5.2 音频播放器LOD

```gdscript
# 音频播放器 LOD
class_name AudioPlayerLOD

extends Node

@export var lod_distances: Array = [10, 30, 50]
@export var lod_players: Array = ["simple", "medium", "complex"]

func update_lod(camera_position: Vector3, player: AudioStreamPlayer3D):
    var distance = camera_position.distance_to(player.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_players.size() - 1)
    
    # 更新播放器
    if lod_index < lod_players.size():
        player.volume_db = get_volume_by_lod(lod_players[lod_index])
        # ⚠️ 没有 attenuation_distance，用 unit_size 调整可听范围
        player.unit_size = get_unit_size_by_lod(lod_players[lod_index])

func get_volume_by_lod(level: String) -> float:
    # 各级别的音量偏移（dB）
    match level:
        "simple": return -6.0
        "medium": return -3.0
        "complex": return 0.0
    return 0.0

func get_unit_size_by_lod(level: String) -> float:
    # 各级别的衰减尺度
    match level:
        "simple": return 5.0
        "medium": return 10.0
        "complex": return 20.0
    return 10.0
```

### 5.3 音频播放器压缩

```gdscript
# 音频播放器压缩
class_name AudioPlayerCompressor

extends Node

@export var max_players: int = 20

func compress_audio_players(players: Array):
    if players.size() > max_players:
        # 找到需要停止的播放器（最久的）
        var players_to_stop = []
        for i in range(players.size() - max_players):
            players_to_stop.append(players[i])
        
        # 停止播放器
        for player in players_to_stop:
            if player and is_instance_valid(player):
                player.stop()
                player.queue_free()
            # ⚠️ erase() 作用在**传入参数**上：删的是调用方传进来的数组，
            #    这里就地删除，调用方拿到的才是压缩后的数量
            players.erase(player)
        
        # 现在 players.size() 已经是压缩后的数量，
        # 于是 players.size() + players_to_stop.size() 正好是压缩前的数量
        print("Audio players compressed: from ", players.size() + players_to_stop.size(), " to ", players.size())
    else:
        print("Audio players already small enough")
```

---

## 6. 实践：完整音频播放器系统

### 6.1 基础音频播放器系统

```gdscript
# 基础音频播放器系统
class_name BasicAudioPlayerSystem

extends Node

@export var master_volume: float = 1.0
@export var sfx_volume: float = 0.8
@export var music_volume: float = 0.7

var stream_manager: AudioStreamManager
var player_manager: AudioStreamPlayerManager

func _ready():
    # 初始化基础音频播放器系统
    initialize_basic_system()

func initialize_basic_system():
    # 创建流管理器
    stream_manager = AudioStreamManager.new()
    add_child(stream_manager)
    
    # 创建播放器管理器
    player_manager = AudioStreamPlayerManager.new()
    add_child(player_manager)
    
    # 预加载常用音频
    preload_common_audio()

func preload_common_audio():
    # 预加载常用音频
    stream_manager.preload_stream("res://audio/sfx/button_click.ogg")
    stream_manager.preload_stream("res://audio/sfx/player_jump.ogg")
    stream_manager.preload_stream("res://audio/music/main_theme.ogg")

func play_sfx(sfx_path: String, volume: float = 1.0):
    # 播放音效
    stream_manager.play_stream_once(sfx_path, volume * sfx_volume)

func play_music(music_path: String):
    # 播放音乐
    stream_manager.play_looped_stream(music_path, music_volume)

func play_3d_sfx(sfx_path: String, position: Vector3, volume: float = 1.0):
    # 播放 3D 音效
    stream_manager.play_3d_stream_once(sfx_path, position, volume * sfx_volume)

func stop_all_audio():
    # 停止所有音频
    stream_manager.stop_all_streams()

func set_master_volume(vol: float):
    # 设置主音量
    master_volume = vol
    # ⚠️ active_players 是 Array，没有 set_volume 方法，要遍历
    for player in stream_manager.active_players:
        if player and is_instance_valid(player):
            player.volume_db = linear_to_db(vol)

func set_sfx_volume(vol: float):
    # 设置音效音量
    sfx_volume = vol

func set_music_volume(vol: float):
    # 设置音乐音量
    music_volume = vol
```

### 6.2 高级音频播放器系统

```gdscript
# 高级音频播放器系统
class_name AdvancedAudioPlayerSystem

extends Node

@export var master_volume: float = 1.0
@export var sfx_volume: float = 0.8
@export var music_volume: float = 0.7
@export var voice_volume: float = 1.0
@export var ambient_volume: float = 0.5

var basic_system: BasicAudioPlayerSystem
var player_pool: AudioStreamPlayerPool
var player_3d_pool: AudioStreamPlayer3DPool

func _ready():
    # 初始化高级音频播放器系统
    initialize_advanced_system()

func initialize_advanced_system():
    # 创建基础系统
    basic_system = BasicAudioPlayerSystem.new()
    add_child(basic_system)
    
    # 创建播放器池
    player_pool = AudioStreamPlayerPool.new()
    add_child(player_pool)
    
    player_3d_pool = AudioStreamPlayer3DPool.new()
    add_child(player_3d_pool)

func play_sfx(sfx_path: String, volume: float = 1.0):
    # 播放音效
    player_pool.play_sound(sfx_path, volume * sfx_volume)

func play_3d_sfx(sfx_path: String, position: Vector3, volume: float = 1.0):
    # 播放 3D 音效
    player_3d_pool.play_3d_sound(sfx_path, position, volume * sfx_volume)

func play_voice(voice_path: String, position: Vector3 = Vector3.ZERO):
    # 播放语音
    if position == Vector3.ZERO:
        # 2D 语音
        player_pool.play_sound(voice_path, voice_volume)
    else:
        # 3D 语音
        player_3d_pool.play_3d_sound(voice_path, position, voice_volume)

func play_ambient(ambient_path: String, position: Vector3):
    # 播放环境音
    player_3d_pool.play_3d_sound(ambient_path, position, ambient_volume)

func play_music(music_path: String):
    # 播放音乐
    basic_system.play_music(music_path)

func set_master_volume(vol: float):
    # 设置主音量
    master_volume = vol
    basic_system.set_master_volume(vol)

func set_sfx_volume(vol: float):
    # 设置音效音量
    sfx_volume = vol
    basic_system.set_sfx_volume(vol)

func set_music_volume(vol: float):
    # 设置音乐音量
    music_volume = vol
    basic_system.set_music_volume(vol)

func set_voice_volume(vol: float):
    # 设置语音音量
    voice_volume = vol

func set_ambient_volume(vol: float):
    # 设置环境音量
    ambient_volume = vol

func get_pool_stats() -> Dictionary:
    # 获取池统计
    return {
        "2d_pool_size": player_pool.get_pool_size(),
        "3d_pool_size": player_3d_pool.get_pool_size(),
        "2d_available": player_pool.get_available_count(),
        "3d_available": player_3d_pool.get_available_count()
    }
```

### 6.3 完整音频播放器系统

```gdscript
# 完整音频播放器系统
class_name FullAudioPlayerSystem

extends Node

var basic_system: BasicAudioPlayerSystem
var advanced_system: AdvancedAudioPlayerSystem

func _ready():
    # 初始化完整音频播放器系统
    initialize_full_system()

func initialize_full_system():
    # 创建基础系统
    basic_system = BasicAudioPlayerSystem.new()
    add_child(basic_system)
    
    # 创建高级系统
    advanced_system = AdvancedAudioPlayerSystem.new()
    add_child(advanced_system)

func play_sfx(sfx_path: String, volume: float = 1.0):
    # 播放音效
    advanced_system.play_sfx(sfx_path, volume)

func play_3d_sfx(sfx_path: String, position: Vector3, volume: float = 1.0):
    # 播放 3D 音效
    advanced_system.play_3d_sfx(sfx_path, position, volume)

func play_voice(voice_path: String, position: Vector3 = Vector3.ZERO):
    # 播放语音
    advanced_system.play_voice(voice_path, position)

func play_ambient(ambient_path: String, position: Vector3):
    # 播放环境音
    advanced_system.play_ambient(ambient_path, position)

func play_music(music_path: String):
    # 播放音乐
    advanced_system.play_music(music_path)

func set_master_volume(vol: float):
    # 设置主音量
    advanced_system.set_master_volume(vol)

func set_sfx_volume(vol: float):
    # 设置音效音量
    advanced_system.set_sfx_volume(vol)

func set_music_volume(vol: float):
    # 设置音乐音量
    advanced_system.set_music_volume(vol)

func set_voice_volume(vol: float):
    # 设置语音音量
    advanced_system.set_voice_volume(vol)

func set_ambient_volume(vol: float):
    # 设置环境音量
    advanced_system.set_ambient_volume(vol)

func get_performance_stats() -> Dictionary:
    # 获取性能统计
    return advanced_system.get_pool_stats()

func update(dt):
    # 更新音频播放器系统
    pass
```

---

## 📝 本章总结

### 核心要点

1. **2D 音频播放器用于界面和 2D 游戏**，简单的音频播放需求
2. **3D 音频播放器用于 3D 游戏**，提供空间音频体验
3. **音频流播放器处理不同格式**，OGG、WAV、MP3 等
4. **音频播放器池优化性能**，复用播放器减少创建开销
5. **音频播放器优化**，包括缓存、LOD、压缩等

### 关键术语

| 术语 | 解释 |
|------|------|
| AudioStreamPlayer | 非定位音频播放器（UI / 背景音乐） |
| AudioStreamPlayer2D | 2D 定位音频播放器 |
| AudioStreamPlayer3D | 3D 定位音频播放器 |
| AudioStream | 音频流资源基类 |
| AudioStreamOggVorbis | OGG Vorbis 音频流 |
| AudioStreamWAV | WAV 音频流（PCM8/16、IMA ADPCM、QOA） |
| AudioStreamMP3 | MP3 音频流 |
| AudioStreamGenerator | 程序化生成的音频流 |

---

## 🔗 延伸阅读

- **官方文档**: [Audio streams](https://docs.godotengine.org/en/stable/tutorials/audio/audio_streams.html)
- **官方文档**: [Using AudioServer](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **类参考**: [AudioStreamPlayer](https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer.html)
- **源码位置**: `scene/2d/audio_stream_player_2d.h`、`scene/3d/audio_stream_player_3d.h`、`servers/audio/effects/audio_stream_generator.cpp`

---

## 📋 下一章预告

**第 47 篇：音频混合器**

- 音频混合器基础
- 总线与支路（send）模型
- 效果器链与执行顺序
- 混音线程与性能优化

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 45 篇：音频系统](/articles/45-audio-system.md)
**下一篇**: [第 47 篇：音频混合器](/articles/47-audio-mixer.md)

---

*写作时间：2026-03-20*  
*字数：约 800 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
