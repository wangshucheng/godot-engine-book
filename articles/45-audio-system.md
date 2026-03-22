# 第 35 篇：音频系统

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 44 章 动画混合器  
> **难度等级**: ⭐⭐⭐ 中级

---

## 📖 本章导读

音频系统是游戏开发中不可或缺的重要组成部分，从背景音乐到音效，从语音对话到环境音，音频系统能够极大地增强游戏的沉浸感和用户体验。

Godot 提供了完整的音频系统，包括音频播放器、音频混合器、音频效果器等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解音频系统的基本概念
- 掌握音频播放器使用
- 学会音频混合器应用
- 熟悉音频效果器
- 掌握音频系统优化

---

## 1. 音频系统基础

### 1.1 音频系统类型

```
音频系统类型:
┌─────────────────────────────────────────────────────────────┐
│                      音频系统类型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 2D 音频：适用于 2D 游戏和界面音频                    │
│  2. 3D 音频：适用于 3D 游戏的空间音频                    │
│  3. 背景音乐：循环播放的背景音乐                         │
│  4. 音效：短促的游戏音效                                 │
│  5. 语音：对话和旁白                                     │
│  6. 环境音：环境和氛围音                                 │
│  7. UI 音频：界面交互音效                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 音频系统组件

```
音频系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      音频系统组件                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioServer：音频服务器                               │
│  2. AudioStream：音频流资源                               │
│  3. AudioStreamPlayer：2D 音频播放器                      │
│  4. AudioStreamPlayer3D：3D 音频播放器                    │
│  5. AudioBus：音频总线                                    │
│  6. AudioEffect：音频效果器                               │
│  7. AudioListener：音频监听器                             │
│  8. AudioStreamOGGVorbis：OGG 音频流                      │
│  9. AudioStreamWAV：WAV 音频流                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 音频系统流程

```
音频系统处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      音频系统处理流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 音频系统接收音频资源                                  │
│  2. 音频播放器解码音频数据                                │
│  3. 音频效果器处理音频效果                                │
│  4. 音频总线混合多个音频                                  │
│  5. 音频监听器接收音频输出                                │
│  6. 音频输出到扬声器                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 音频播放器

### 2.1 2D 音频播放器

```gdscript
# 2D 音频播放器
class_name AudioStreamPlayer2D

extends AudioStreamPlayer

@export var stream_path: String
@export var volume_db: float = 0.0
@export var pitch_scale: float = 1.0
@export var autoplay: bool = false

func _ready():
    # 加载音频流
    if stream_path != "":
        var stream = load(stream_path)
        if stream:
            stream = stream
    
    # 设置音量
    volume_db = volume_db
    
    # 设置音调
    pitch_scale = pitch_scale
    
    # 自动播放
    if autoplay:
        play()

func play_audio():
    # 播放音频
    play()

func stop_audio():
    # 停止音频
    stop()

func pause_audio():
    # 暂停音频
    pause()

func resume_audio():
    # 恢复音频
    if paused:
        play()

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func is_playing() -> bool:
    # 检查是否正在播放
    return playing

func get_playback_position() -> float:
    # 获取播放位置
    return get_playback_position()

func set_playback_position(position: float):
    # 设置播放位置
    seek(position)
```

### 2.2 3D 音频播放器

```gdscript
# 3D 音频播放器
class_name AudioStreamPlayer3D

extends AudioStreamPlayer3D

@export var stream_path: String
@export var volume_db: float = 0.0
@export var pitch_scale: float = 1.0
@export var attenuation_filter_db: float = 1.0
@export var attenuation_distance: float = 10.0
@export var max_db: float = 0.0
@export var unit_size: float = 10.0

func _ready():
    # 加载音频流
    if stream_path != "":
        var stream = load(stream_path)
        if stream:
            stream = stream
    
    # 设置音量
    volume_db = volume_db
    
    # 设置音调
    pitch_scale = pitch_scale
    
    # 设置衰减
    attenuation_filter_db = attenuation_filter_db
    attenuation_distance = attenuation_distance
    max_db = max_db
    unit_size = unit_size

func play_audio():
    # 播放音频
    play()

func stop_audio():
    # 停止音频
    stop()

func pause_audio():
    # 暂停音频
    pause()

func resume_audio():
    # 恢复音频
    if paused:
        play()

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func is_playing() -> bool:
    # 检查是否正在播放
    return playing

func get_playback_position() -> float:
    # 获取播放位置
    return get_playback_position()

func set_playback_position(position: float):
    # 设置播放位置
    seek(position)

func set_attenuation(distance: float):
    # 设置衰减
    attenuation_distance = distance
```

### 2.3 音频播放控制器

```gdscript
# 音频播放控制器
class_name AudioPlayerController

extends Node

@export var audio_player: AudioStreamPlayer
@export var audio_player_3d: AudioStreamPlayer3D

func _ready():
    # 设置音频播放器
    if audio_player:
        audio_player.connect("finished", self, "_on_audio_finished")
    
    if audio_player_3d:
        audio_player_3d.connect("finished", self, "_on_audio_3d_finished")

func _on_audio_finished():
    # 音频播放完成
    print("Audio finished")

func _on_audio_3d_finished():
    # 3D 音频播放完成
    print("3D Audio finished")

func play_audio(audio_name: String):
    # 播放音频
    if audio_player and audio_player.has_method("play"):
        audio_player.play()

func play_audio_3d(audio_name: String):
    # 播放 3D 音频
    if audio_player_3d and audio_player_3d.has_method("play"):
        audio_player_3d.play()

func stop_audio():
    # 停止音频
    if audio_player:
        audio_player.stop()
    
    if audio_player_3d:
        audio_player_3d.stop()

func set_volume(volume: float):
    # 设置音量
    if audio_player:
        audio_player.volume_db = linear_to_db(volume)
    
    if audio_player_3d:
        audio_player_3d.volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    if audio_player:
        audio_player.pitch_scale = pitch
    
    if audio_player_3d:
        audio_player_3d.pitch_scale = pitch

func fade_out(duration: float):
    # 淡出
    var tween = create_tween()
    tween.tween_method(set_volume, get_volume(), 0.0, duration)

func fade_in(duration: float):
    # 淡入
    var tween = create_tween()
    tween.tween_method(set_volume, 0.0, get_volume(), duration)

func get_volume() -> float:
    # 获取音量
    if audio_player:
        return db_to_linear(audio_player.volume_db)
    return 1.0
```

---

## 3. 音频总线

### 3.1 音频总线基础

```gdscript
# 音频总线基础
class_name AudioBusController

extends Node

func _ready():
    # 初始化音频总线
    initialize_audio_buses()

func initialize_audio_buses():
    # 获取音频服务器
    var audio_server = AudioServer
    
    # 设置总线数量
    audio_server.bus_count = 8
    
    # 设置主总线名称
    audio_server.set_bus_name(0, "Master")
    
    # 创建其他总线
    audio_server.add_bus(1)
    audio_server.set_bus_name(1, "Music")
    
    audio_server.add_bus(2)
    audio_server.set_bus_name(2, "SFX")
    
    audio_server.add_bus(3)
    audio_server.set_bus_name(3, "Voice")
    
    audio_server.add_bus(4)
    audio_server.set_bus_name(4, "Ambient")
    
    audio_server.add_bus(5)
    audio_server.set_bus_name(5, "UI")
    
    audio_server.add_bus(6)
    audio_server.set_bus_name(6, "Reverb")
    
    audio_server.add_bus(7)
    audio_server.set_bus_name(7, "Effects")

func set_bus_volume(bus_name: String, volume: float):
    # 设置总线音量
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.set_bus_volume_db(bus_idx, linear_to_db(volume))

func set_bus_mute(bus_name: String, mute: bool):
    # 设置总线静音
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.set_bus_mute(bus_idx, mute)

func set_bus_solo(bus_name: String, solo: bool):
    # 设置总线独奏
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.set_bus_solo(bus_idx, solo)

func add_audio_effect(bus_name: String, effect: AudioEffect):
    # 添加音频效果
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.add_bus_effect(bus_idx, effect)
```

### 3.2 音频总线管理器

```gdscript
# 音频总线管理器
class_name AudioBusManager

extends Node

var bus_settings = {
    "Master": {"volume": 1.0, "mute": false},
    "Music": {"volume": 0.8, "mute": false},
    "SFX": {"volume": 0.7, "mute": false},
    "Voice": {"volume": 1.0, "mute": false},
    "Ambient": {"volume": 0.5, "mute": false},
    "UI": {"volume": 0.6, "mute": false},
    "Reverb": {"volume": 0.3, "mute": false},
    "Effects": {"volume": 0.4, "mute": false}
}

func _ready():
    # 初始化音频总线
    initialize_audio_buses()

func initialize_audio_buses():
    # 获取音频服务器
    var audio_server = AudioServer
    
    # 设置总线数量
    audio_server.bus_count = bus_settings.size()
    
    # 创建总线
    var idx = 0
    for bus_name in bus_settings:
        if idx == 0:
            audio_server.set_bus_name(idx, bus_name)
        else:
            audio_server.add_bus(idx)
            audio_server.set_bus_name(idx, bus_name)
        
        # 设置初始音量
        var volume = bus_settings[bus_name]["volume"]
        audio_server.set_bus_volume_db(idx, linear_to_db(volume))
        
        # 设置初始静音
        var mute = bus_settings[bus_name]["mute"]
        audio_server.set_bus_mute(idx, mute)
        
        idx += 1

func update_bus_settings():
    # 更新总线设置
    var audio_server = AudioServer
    var idx = 0
    for bus_name in bus_settings:
        var bus_idx = audio_server.get_bus_index(bus_name)
        if bus_idx != -1:
            # 更新音量
            var volume = bus_settings[bus_name]["volume"]
            audio_server.set_bus_volume_db(bus_idx, linear_to_db(volume))
            
            # 更新静音
            var mute = bus_settings[bus_name]["mute"]
            audio_server.set_bus_mute(bus_idx, mute)
        
        idx += 1

func set_master_volume(volume: float):
    # 设置主音量
    bus_settings["Master"]["volume"] = volume
    set_bus_volume("Master", volume)

func set_music_volume(volume: float):
    # 设置音乐音量
    bus_settings["Music"]["volume"] = volume
    set_bus_volume("Music", volume)

func set_sfx_volume(volume: float):
    # 设置音效音量
    bus_settings["SFX"]["volume"] = volume
    set_bus_volume("SFX", volume)

func set_voice_volume(volume: float):
    # 设置语音音量
    bus_settings["Voice"]["volume"] = volume
    set_bus_volume("Voice", volume)

func set_ambient_volume(volume: float):
    # 设置环境音音量
    bus_settings["Ambient"]["volume"] = volume
    set_bus_volume("Ambient", volume)

func set_ui_volume(volume: float):
    # 设置界面音量
    bus_settings["UI"]["volume"] = volume
    set_bus_volume("UI", volume)

func mute_all():
    # 静音所有
    for bus_name in bus_settings:
        bus_settings[bus_name]["mute"] = true
        set_bus_mute(bus_name, true)

func unmute_all():
    # 取消静音所有
    for bus_name in bus_settings:
        bus_settings[bus_name]["mute"] = false
        set_bus_mute(bus_name, false)
```

### 3.3 音频总线效果器

```gdscript
# 音频总线效果器
class_name AudioBusEffects

extends Node

func _ready():
    # 初始化音频效果
    initialize_audio_effects()

func initialize_audio_effects():
    var audio_server = AudioServer
    
    # 为主总线添加混响效果
    var master_bus_idx = audio_server.get_bus_index("Master")
    if master_bus_idx != -1:
        var reverb = AudioEffectReverb.new()
        reverb.room_size = 0.8
        reverb.dampening = 0.5
        reverb.wet = 0.2
        reverb.dry = 0.8
        audio_server.add_bus_effect(master_bus_idx, reverb)
    
    # 为音乐总线添加均衡器
    var music_bus_idx = audio_server.get_bus_index("Music")
    if music_bus_idx != -1:
        var eq = AudioEffectEQ2.new()
        eq bands[0].gain = 2.0  # 低音增强
        eq bands[6].gain = 1.5  # 高音增强
        audio_server.add_bus_effect(music_bus_idx, eq)
    
    # 为音效总线添加压缩器
    var sfx_bus_idx = audio_server.get_bus_index("SFX")
    if sfx_bus_idx != -1:
        var compressor = AudioEffectCompressor.new()
        compressor.ratio = 4.0
        compressor.threshold = -6.0
        compressor.attack_us = 100.0
        compressor.release_ms = 200.0
        audio_server.add_bus_effect(sfx_bus_idx, compressor)

func add_reverb_to_bus(bus_name: String):
    # 为总线添加混响
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        var reverb = AudioEffectReverb.new()
        reverb.room_size = 0.8
        reverb.dampening = 0.5
        reverb.wet = 0.2
        reverb.dry = 0.8
        audio_server.add_bus_effect(bus_idx, reverb)

func add_eq_to_bus(bus_name: String):
    # 为总线添加均衡器
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        var eq = AudioEffectEQ2.new()
        eq.bands[0].gain = 2.0  # 低音增强
        eq.bands[6].gain = 1.5  # 高音增强
        audio_server.add_bus_effect(bus_idx, eq)

func add_compressor_to_bus(bus_name: String):
    # 为总线添加压缩器
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        var compressor = AudioEffectCompressor.new()
        compressor.ratio = 4.0
        compressor.threshold = -6.0
        compressor.attack_us = 100.0
        compressor.release_ms = 200.0
        audio_server.add_bus_effect(bus_idx, compressor)
```

---

## 4. 音频效果器

### 4.1 混响效果器

```gdscript
# 混响效果器
class_name ReverbEffect

extends AudioEffectReverb

@export var room_size: float = 0.8
@export var dampening: float = 0.5
@export var wet: float = 0.2
@export var dry: float = 0.8

func _ready():
    # 设置混响参数
    room_size = room_size
    dampening = dampening
    wet = wet
    dry = dry

func update_parameters():
    # 更新参数
    room_size = room_size
    dampening = dampening
    wet = wet
    dry = dry

func set_room_size(size: float):
    # 设置房间大小
    room_size = size

func set_dampening(damp: float):
    # 设置阻尼
    dampening = damp

func set_wet_amount(amount: float):
    # 设置湿信号量
    wet = amount

func set_dry_amount(amount: float):
    # 设置干信号量
    dry = amount
```

### 4.2 均衡器效果器

```gdscript
# 均衡器效果器
class_name EQEffect

extends AudioEffectEQ2

@export var low_gain: float = 1.0
@export var mid_gain: float = 1.0
@export var high_gain: float = 1.0

func _ready():
    # 设置均衡器参数
    update_parameters()

func update_parameters():
    # 更新参数
    bands[0].gain = low_gain   # 低频
    bands[3].gain = mid_gain   # 中频
    bands[6].gain = high_gain  # 高频

func set_low_gain(gain: float):
    # 设置低频增益
    low_gain = gain
    bands[0].gain = low_gain

func set_mid_gain(gain: float):
    # 设置中频增益
    mid_gain = gain
    bands[3].gain = mid_gain

func set_high_gain(gain: float):
    # 设置高频增益
    high_gain = gain
    bands[6].gain = high_gain

func set_band_gain(band_idx: int, gain: float):
    # 设置指定频段增益
    if band_idx < bands.size():
        bands[band_idx].gain = gain
```

### 4.3 压缩器效果器

```gdscript
# 压缩器效果器
class_name CompressorEffect

extends AudioEffectCompressor

@export var ratio: float = 4.0
@export var threshold: float = -6.0
@export var attack_us: float = 100.0
@export var release_ms: float = 200.0

func _ready():
    # 设置压缩器参数
    update_parameters()

func update_parameters():
    # 更新参数
    ratio = ratio
    threshold = threshold
    attack_us = attack_us
    release_ms = release_ms

func set_ratio(ratio_val: float):
    # 设置压缩比
    ratio = ratio_val

func set_threshold(threshold_val: float):
    # 设置阈值
    threshold = threshold_val

func set_attack(attack_val: float):
    # 设置攻击时间
    attack_us = attack_val

func set_release(release_val: float):
    # 设置释放时间
    release_ms = release_val
```

---

## 5. 音频系统优化

### 5.1 音频资源管理

```gdscript
# 音频资源管理
class_name AudioManager

extends Node

var audio_cache = {}
var active_streams = []

func preload_audio(audio_path: String):
    # 预加载音频
    if not audio_cache.has(audio_path):
        var audio_stream = load(audio_path)
        audio_cache[audio_path] = audio_stream
        print("Preloaded audio: ", audio_path)

func get_audio_stream(audio_path: String) -> AudioStream:
    # 获取音频流
    if audio_cache.has(audio_path):
        return audio_cache[audio_path]
    
    # 如果未缓存，加载并缓存
    var audio_stream = load(audio_path)
    audio_cache[audio_path] = audio_stream
    return audio_stream

func play_audio_once(audio_path: String, volume: float = 1.0):
    # 播放一次性音频
    var stream = get_audio_stream(audio_path)
    
    # 创建临时播放器
    var player = AudioStreamPlayer.new()
    player.stream = stream
    player.volume_db = linear_to_db(volume)
    
    # 连接完成信号以清理资源
    player.connect("finished", player, "queue_free")
    
    # 添加到场景
    add_child(player)
    player.play()
    
    # 添加到活跃流列表
    active_streams.append(player)

func play_music(audio_path: String, volume: float = 0.8):
    # 播放音乐
    var stream = get_audio_stream(audio_path)
    
    # 创建音乐播放器
    var player = AudioStreamPlayer.new()
    player.stream = stream
    player.volume_db = linear_to_db(volume)
    player.autoplay = true
    player.loop = true
    
    # 添加到场景
    add_child(player)
    player.play()
    
    # 添加到活跃流列表
    active_streams.append(player)

func stop_all_audio():
    # 停止所有音频
    for player in active_streams:
        if player and is_instance_valid(player):
            player.stop()
            player.queue_free()
    
    active_streams.clear()

func unload_unused_audio():
    # 卸载未使用的音频
    var unused_paths = []
    for path in audio_cache:
        var is_used = false
        for player in active_streams:
            if player and is_instance_valid(player) and player.stream == audio_cache[path]:
                is_used = true
                break
        
        if not is_used:
            unused_paths.append(path)
    
    for path in unused_paths:
        audio_cache.erase(path)
        print("Unloaded unused audio: ", path)
```

### 5.2 音频距离衰减

```gdscript
# 音频距离衰减
class_name AudioDistanceAttenuation

extends Node3D

@export var max_distance: float = 30.0
@export var min_distance: float = 5.0
@export var attenuation_curve: Curve

func _process(delta):
    # 更新音频衰减
    update_attenuation()

func update_attenuation():
    # 计算到监听器的距离
    var listener_pos = get_viewport().get_camera_3d().global_transform.origin
    var distance = global_transform.origin.distance_to(listener_pos)
    
    # 计算衰减值
    var attenuation = calculate_attenuation(distance)
    
    # 应用到音频播放器
    if $AudioStreamPlayer3D:
        $AudioStreamPlayer3D.volume_db = linear_to_db(attenuation)

func calculate_attenuation(distance: float) -> float:
    # 计算衰减
    if distance <= min_distance:
        return 1.0
    elif distance >= max_distance:
        return 0.0
    else:
        var normalized_distance = (distance - min_distance) / (max_distance - min_distance)
        if attenuation_curve:
            return attenuation_curve.sample(1.0 - normalized_distance)
        else:
            # 线性衰减
            return 1.0 - normalized_distance

func set_max_distance(dist: float):
    max_distance = dist

func set_min_distance(dist: float):
    min_distance = dist

func set_attenuation_curve(curve: Curve):
    attenuation_curve = curve
```

### 5.3 音频性能监控

```gdscript
# 音频性能监控
class_name AudioPerformanceMonitor

extends Node

var active_players = 0
var total_samples = 0
var cpu_usage = 0.0

func _ready():
    # 开始监控
    start_monitoring()

func start_monitoring():
    # 连接定时器以定期更新
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.connect("timeout", self, "_update_stats")
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计信息
    var audio_server = AudioServer
    active_players = audio_server.bus_count
    total_samples = audio_server.mix_rate * audio_server.input_latency
    cpu_usage = audio_server.performance_get("time_usage/max")

func get_active_players() -> int:
    return active_players

func get_cpu_usage() -> float:
    return cpu_usage

func get_total_samples() -> int:
    return total_samples

func print_stats():
    print("Audio Stats:")
    print("- Active Players: ", get_active_players())
    print("- CPU Usage: ", get_cpu_usage())
    print("- Total Samples: ", get_total_samples())
```

---

## 6. 实践：完整音频系统

### 6.1 基础音频系统

```gdscript
# 基础音频系统
class_name BasicAudioSystem

extends Node

@export var master_volume: float = 1.0
@export var music_volume: float = 0.8
@export var sfx_volume: float = 0.7

var audio_manager: AudioManager
var bus_manager: AudioBusManager

func _ready():
    # 初始化音频系统
    initialize_audio_system()

func initialize_audio_system():
    # 创建音频管理器
    audio_manager = AudioManager.new()
    add_child(audio_manager)
    
    # 创建总线管理器
    bus_manager = AudioBusManager.new()
    add_child(bus_manager)
    
    # 设置初始音量
    bus_manager.set_master_volume(master_volume)
    bus_manager.set_music_volume(music_volume)
    bus_manager.set_sfx_volume(sfx_volume)

func play_sound(sound_path: String, volume: float = 1.0):
    # 播放音效
    audio_manager.play_audio_once(sound_path, volume)

func play_music(music_path: String):
    # 播放音乐
    audio_manager.play_music(music_path)

func set_master_volume(vol: float):
    # 设置主音量
    bus_manager.set_master_volume(vol)

func set_music_volume(vol: float):
    # 设置音乐音量
    bus_manager.set_music_volume(vol)

func set_sfx_volume(vol: float):
    # 设置音效音量
    bus_manager.set_sfx_volume(vol)

func mute_audio():
    # 静音
    bus_manager.mute_all()

func unmute_audio():
    # 取消静音
    bus_manager.unmute_all()
```

### 6.2 高级音频系统

```gdscript
# 高级音频系统
class_name AdvancedAudioSystem

extends Node

@export var master_volume: float = 1.0
@export var music_volume: float = 0.8
@export var sfx_volume: float = 0.7
@export var voice_volume: float = 1.0
@export var ambient_volume: float = 0.5

var audio_manager: AudioManager
var bus_manager: AudioBusManager
var effects_manager: AudioBusEffects
var performance_monitor: AudioPerformanceMonitor

func _ready():
    # 初始化高级音频系统
    initialize_advanced_audio_system()

func initialize_advanced_audio_system():
    # 创建音频管理器
    audio_manager = AudioManager.new()
    add_child(audio_manager)
    
    # 创建总线管理器
    bus_manager = AudioBusManager.new()
    add_child(bus_manager)
    
    # 创建效果管理器
    effects_manager = AudioBusEffects.new()
    add_child(effects_manager)
    
    # 创建性能监控器
    performance_monitor = AudioPerformanceMonitor.new()
    add_child(performance_monitor)
    
    # 设置初始音量
    bus_manager.set_master_volume(master_volume)
    bus_manager.set_music_volume(music_volume)
    bus_manager.set_sfx_volume(sfx_volume)
    bus_manager.set_voice_volume(voice_volume)
    bus_manager.set_ambient_volume(ambient_volume)

func play_3d_sound(sound_path: String, position: Vector3, volume: float = 1.0):
    # 播放 3D 音效
    var stream = audio_manager.get_audio_stream(sound_path)
    
    # 创建 3D 播放器
    var player_3d = AudioStreamPlayer3D.new()
    player_3d.stream = stream
    player_3d.global_transform.origin = position
    player_3d.volume_db = linear_to_db(volume)
    
    # 连接完成信号以清理资源
    player_3d.connect("finished", player_3d, "queue_free")
    
    # 添加到场景
    add_child(player_3d)
    player_3d.play()

func play_background_music(music_path: String):
    # 播放背景音乐
    audio_manager.play_music(music_path)

func play_voice_line(voice_path: String):
    # 播放语音
    audio_manager.play_audio_once(voice_path, voice_volume)

func play_ambient_sound(ambient_path: String):
    # 播放环境音
    audio_manager.play_audio_once(ambient_path, ambient_volume)

func set_master_volume(vol: float):
    bus_manager.set_master_volume(vol)

func set_music_volume(vol: float):
    bus_manager.set_music_volume(vol)

func set_sfx_volume(vol: float):
    bus_manager.set_sfx_volume(vol)

func set_voice_volume(vol: float):
    bus_manager.set_voice_volume(vol)

func set_ambient_volume(vol: float):
    bus_manager.set_ambient_volume(vol)

func toggle_mute():
    if bus_manager.bus_settings["Master"]["mute"]:
        bus_manager.unmute_all()
    else:
        bus_manager.mute_all()

func get_performance_stats():
    return performance_monitor.get_cpu_usage()
```

### 6.3 完整音频系统

```gdscript
# 完整音频系统
class_name FullAudioSystem

extends Node

var basic_system: BasicAudioSystem
var advanced_system: AdvancedAudioSystem

func _ready():
    # 初始化完整音频系统
    initialize_full_audio_system()

func initialize_full_audio_system():
    # 创建基础系统
    basic_system = BasicAudioSystem.new()
    add_child(basic_system)
    
    # 创建高级系统
    advanced_system = AdvancedAudioSystem.new()
    add_child(advanced_system)

func play_sound(sound_path: String, volume: float = 1.0):
    # 播放音效
    basic_system.play_sound(sound_path, volume)

func play_3d_sound(sound_path: String, position: Vector3, volume: float = 1.0):
    # 播放 3D 音效
    advanced_system.play_3d_sound(sound_path, position, volume)

func play_music(music_path: String):
    # 播放音乐
    basic_system.play_music(music_path)

func play_voice(voice_path: String):
    # 播放语音
    advanced_system.play_voice_line(voice_path)

func play_ambient(ambient_path: String):
    # 播放环境音
    advanced_system.play_ambient_sound(ambient_path)

func set_master_volume(vol: float):
    basic_system.set_master_volume(vol)

func set_music_volume(vol: float):
    basic_system.set_music_volume(vol)

func set_sfx_volume(vol: float):
    basic_system.set_sfx_volume(vol)

func set_voice_volume(vol: float):
    advanced_system.set_voice_volume(vol)

func set_ambient_volume(vol: float):
    advanced_system.set_ambient_volume(vol)

func mute_all():
    basic_system.mute_audio()

func unmute_all():
    basic_system.unmute_audio()

func get_performance_stats():
    return advanced_system.get_performance_stats()

func update(dt):
    # 更新音频系统
    pass
```

---

## 📝 本章总结

### 核心要点

1. **音频播放器是基础**，分为 2D 和 3D 播放器
2. **音频总线用于组织音频**，不同的音频类型使用不同的总线
3. **音频效果器增强音频质量**，包括混响、均衡、压缩等
4. **音频系统优化**，包括资源管理、距离衰减、性能监控
5. **完整音频系统**，整合所有音频功能

### 关键术语

| 术语 | 解释 |
|------|------|
| AudioStreamPlayer | 2D 音频播放器 |
| AudioStreamPlayer3D | 3D 音频播放器 |
| AudioBus | 音频总线 |
| AudioEffect | 音频效果器 |
| AudioServer | 音频服务器 |
| Attenuation | 距离衰减 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Audio](https://docs.godotengine.org/en/stable/tutorials/audio/index.html)
- **源码位置**: `servers/audio/`
- **技术博客**: [Godot Audio System](https://godotengine.org/article/audio-system/)

---

## 📋 下一章预告

**第 46 篇：音频播放器**

- 音频播放器基础
- 2D 音频播放器
- 3D 音频播放器
- 音频播放器优化

---

*写作时间：2026-03-20*  
*字数：约 11,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*