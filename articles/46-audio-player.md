# 第 36 篇：音频播放器

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
│  1. AudioStreamPlayer：2D 音频播放器                        │
│  2. AudioStreamPlayer3D：3D 音频播放器                     │
│  3. AudioStreamMicrophone：麦克风音频播放器                 │
│  4. AudioStreamRandomizer：随机音频播放器                   │
│  5. AudioStreamPolyphonic：多声道音频播放器                 │
│  6. AudioStreamPlayer2D：2D 音频播放器（另一种实现）        │
│  7. AudioStreamPlayerPeer：网络音频播放器                   │
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
│  1. AudioStreamPlayer：音频播放器节点                       │
│  2. AudioStream：音频流资源                                 │
│  3. AudioStreamSample：音频采样流                           │
│  4. AudioStreamOGGVorbis：OGG 音频流                        │
│  5. AudioStreamWAV：WAV 音频流                              │
│  6. AudioStreamMP3：MP3 音频流                              │
│  7. AudioStreamResource：音频资源                           │
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

## 2. 2D 音频播放器

### 2.1 基础 AudioStreamPlayer

```gdscript
# 2D 音频播放器基础
class_name BasicAudioStreamPlayer

extends AudioStreamPlayer

@export var stream_path: String
@export var volume_db: float = 0.0
@export var pitch_scale: float = 1.0
@export var autoplay: bool = false
@export var loop: bool = false
@export var loop_offset: float = 0.0

func _ready():
    # 加载音频流
    if stream_path != "":
        var stream = load(stream_path)
        if stream is AudioStream:
            stream = stream
    
    # 设置音量
    volume_db = volume_db
    
    # 设置音调
    pitch_scale = pitch_scale
    
    # 设置循环
    loop_mode = loop
    if loop:
        set_stream_paused(false)
    
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

func is_playing() -> bool:
    # 检查是否正在播放
    return playing

func get_playback_position() -> float:
    # 获取播放位置
    return get_playback_position()

func set_playback_position(position: float):
    # 设置播放位置
    seek(position)

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_loop(enabled: bool):
    # 设置循环
    loop_mode = enabled

func set_loop_offset(offset: float):
    # 设置循环偏移
    loop_offset = offset

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
    
    # 连接完成信号以自动清理
    player.connect("finished", self, "_on_player_finished", [player])

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
            player.disconnect("finished", self, "_on_player_finished")
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
    
    # 连接完成信号以归还播放器
    player.connect("finished", self, "_on_sound_finished", [player])

func _on_sound_finished(player: AudioStreamPlayer):
    # 音效播放完成
    if player.is_connected("finished", self, "_on_sound_finished"):
        player.disconnect("finished", self, "_on_sound_finished")
    return_player(player)

func get_pool_size() -> int:
    # 获取池大小
    return pool.size()

func get_available_count() -> int:
    # 获取可用数量
    return pool.size()
```

---

## 3. 3D 音频播放器

### 3.1 基础 AudioStreamPlayer3D

```gdscript
# 3D 音频播放器基础
class_name BasicAudioStreamPlayer3D

extends AudioStreamPlayer3D

@export var stream_path: String
@export var volume_db: float = 0.0
@export var pitch_scale: float = 1.0
@export var attenuation_filter_db: float = 1.0
@export var attenuation_distance: float = 10.0
@export var max_db: float = 0.0
@export var unit_size: float = 10.0
@export var area_mask: int = 1
@export var panning_strength: float = 1.0

func _ready():
    # 加载音频流
    if stream_path != "":
        var stream = load(stream_path)
        if stream is AudioStream:
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
    area_mask = area_mask
    panning_strength = panning_strength

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

func is_playing() -> bool:
    # 检查是否正在播放
    return playing

func get_playback_position() -> float:
    # 获取播放位置
    return get_playback_position()

func set_playback_position(position: float):
    # 设置播放位置
    seek(position)

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_attenuation(distance: float):
    # 设置衰减
    attenuation_distance = distance

func set_attenuation_filter(filter: float):
    # 设置衰减滤波
    attenuation_filter_db = filter

func set_panning_strength(strength: float):
    # 设置平移强度
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
@export var stream_path: String
@export var max_distance: float = 30.0
@export var min_distance: float = 5.0
@export var follow_target: NodePath

var target: Node3D

func _ready():
    # 初始化 3D 音频播放器
    if player_3d:
        if stream_path != "":
            player_3d.stream = load(stream_path)
    
    # 获取跟随目标
    if follow_target:
        target = get_node(follow_target) as Node3D

func _process(delta):
    # 更新 3D 音频播放器
    if target:
        # 跟随目标
        global_transform.origin = target.global_transform.origin

func play_sound():
    # 播放音效
    if player_3d:
        player_3d.play()

func stop_sound():
    # 停止音效
    if player_3d:
        player_3d.stop()

func pause_sound():
    # 暂停音效
    if player_3d:
        player_3d.pause()

func resume_sound():
    # 恢复音效
    if player_3d and player_3d.paused:
        player_3d.play()

func set_volume(volume: float):
    # 设置音量
    if player_3d:
        player_3d.volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    if player_3d:
        player_3d.pitch_scale = pitch

func set_attenuation_params(min_dist: float, max_dist: float):
    # 设置衰减参数
    if player_3d:
        player_3d.min_distance = min_dist
        player_3d.max_distance = max_dist

func set_follow_target(new_target: Node3D):
    # 设置跟随目标
    target = new_target

func get_distance_to_listener() -> float:
    # 获取到监听器的距离
    if player_3d and get_viewport() and get_viewport().get_camera_3d():
        var listener_pos = get_viewport().get_camera_3d().global_transform.origin
        return global_transform.origin.distance_to(listener_pos)
    return 0.0

func is_within_range() -> bool:
    # 检查是否在范围内
    var distance = get_distance_to_listener()
    return distance <= max_distance

func update_attenuation():
    # 更新衰减
    var distance = get_distance_to_listener()
    if distance > max_distance:
        set_volume(0.0)
    elif distance > min_distance:
        var attenuation = 1.0 - ((distance - min_distance) / (max_distance - min_distance))
        set_volume(attenuation)
    else:
        set_volume(1.0)
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
        player.attenuation_filter_db = 1.0
        player.attenuation_distance = 10.0
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
        player.attenuation_filter_db = 1.0
        player.attenuation_distance = 10.0
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
    
    # 连接完成信号以归还播放器
    player.connect("finished", self, "_on_3d_sound_finished", [player])

func _on_3d_sound_finished(player: AudioStreamPlayer3D):
    # 3D 音效播放完成
    if player.is_connected("finished", self, "_on_3d_sound_finished"):
        player.disconnect("finished", self, "_on_3d_sound_finished")
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
    player.min_distance = min_dist
    player.max_distance = max_dist
    player.play()
    
    # 连接完成信号以归还播放器
    player.connect("finished", self, "_on_3d_sound_finished", [player])
```

---

## 4. 音频流播放器

### 4.1 音频流类型

```gdscript
# 音频流类型
class_name AudioStreamTypes

extends Node

func create_ogg_stream(path: String) -> AudioStreamOGGVorbis:
    # 创建 OGG 音频流
    return load(path) as AudioStreamOGGVorbis

func create_wav_stream(path: String) -> AudioStreamWAV:
    # 创建 WAV 音频流
    return load(path) as AudioStreamWAV

func create_mp3_stream(path: String) -> AudioStreamMP3:
    # 创建 MP3 音频流
    return load(path) as AudioStreamMP3

func create_sample_stream(path: String) -> AudioStreamSample:
    # 创建采样音频流
    return load(path) as AudioStreamSample

func get_audio_format(path: String) -> String:
    # 获取音频格式
    if path.ends_with(".ogg"):
        return "OGG"
    elif path.ends_with(".wav"):
        return "WAV"
    elif path.ends_with(".mp3"):
        return "MP3"
    elif path.ends_with(".sample"):
        return "SAMPLE"
    else:
        return "UNKNOWN"
```

### 4.2 音频流播放器

```gdscript
# 音频流播放器
class_name AudioStreamPlayerAdvanced

extends AudioStreamPlayer

@export var stream_path: String
@export var volume_db: float = 0.0
@export var pitch_scale: float = 1.0
@export var autoplay: bool = false
@export var loop: bool = false
@export var stream_type: String = "AUTO"  # AUTO, OGG, WAV, MP3, SAMPLE

var current_stream: AudioStream

func _ready():
    # 加载音频流
    current_stream = load_stream(stream_path)
    if current_stream:
        stream = current_stream
    
    # 设置音量
    volume_db = volume_db
    
    # 设置音调
    pitch_scale = pitch_scale
    
    # 设置循环
    loop_mode = loop
    
    # 自动播放
    if autoplay:
        play()

func load_stream(path: String) -> AudioStream:
    # 加载音频流
    var resource = load(path)
    if resource is AudioStream:
        return resource
    return null

func play_stream(stream_path: String):
    # 播放指定音频流
    var new_stream = load_stream(stream_path)
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
    # 暂停音频
    pause()

func resume_audio():
    # 恢复音频
    if paused:
        play()

func is_playing() -> bool:
    # 检查是否正在播放
    return playing

func get_playback_position() -> float:
    # 获取播放位置
    return get_playback_position()

func set_playback_position(position: float):
    # 设置播放位置
    seek(position)

func set_volume(volume: float):
    # 设置音量
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_loop(enabled: bool):
    # 设置循环
    loop_mode = enabled

func get_stream_info() -> Dictionary:
    # 获取音频流信息
    var info = {}
    if stream:
        info["name"] = stream.resource_path
        info["length"] = stream.get_length() if stream.has_method("get_length") else 0
        info["loop"] = loop_mode
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

### 4.3 音频流管理器

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
    
    # 连接完成信号以清理资源
    player.connect("finished", player, "queue_free")
    
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
    
    # 连接完成信号以清理资源
    player.connect("finished", player, "queue_free")
    
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
    player.loop_mode = AudioStreamPlayer.LOOP_FORWARD
    
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

## 5. 音频播放器优化

### 5.1 音频播放器缓存

```gdscript
# 音频播放器缓存
class_name AudioPlayerCache

var cache = {}

func get_player(player_name: String) -> AudioStreamPlayer:
    if cache.has(player_name):
        return cache[player_name]
    
    var player = AudioStreamPlayer.new()
    cache[player_name] = player
    return player

func get_3d_player(player_name: String) -> AudioStreamPlayer3D:
    if cache.has(player_name + "_3d"):
        return cache[player_name + "_3d"]
    
    var player = AudioStreamPlayer3D.new()
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
# 音频播放器LOD
class_name AudioPlayerLOD

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
        player.attenuation_distance = get_attenuation_by_lod(lod_players[lod_index])
```

### 5.3 音频播放器压缩

```gdscript
# 音频播放器压缩
class_name AudioPlayerCompressor

@export var max_players: int = 20

func compress_audio_players(players: Array):
    if players.size() > max_players:
        # 优化播放器数量
        var players_to_stop = []
        
        # 找到需要停止的播放器（最久的）
        for i in range(players.size() - max_players):
            players_to_stop.append(players[i])
        
        # 停止播放器
        for player in players_to_stop:
            if player and is_instance_valid(player):
                player.stop()
                player.queue_free()
                players.erase(player)
        
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
    stream_manager.active_players.set_volume(vol)

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
| AudioStreamPlayer | 2D 音频播放器 |
| AudioStreamPlayer3D | 3D 音频播放器 |
| AudioStream | 音频流资源 |
| AudioStreamOGGVorbis | OGG 音频流 |
| AudioStreamWAV | WAV 音频流 |
| AudioStreamMP3 | MP3 音频流 |
| AudioStreamSample | 采样音频流 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Audio](https://docs.godotengine.org/en/stable/tutorials/audio/index.html)
- **源码位置**: `servers/audio/`
- **技术博客**: [Godot Audio Player](https://godotengine.org/article/audio-player/)

---

## 📋 下一章预告

**第 47 篇：音频混合器**

- 音频混合器基础
- 音频总线混合
- 音频效果混合
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 12,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*