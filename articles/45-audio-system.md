# 第 45 篇：音频系统

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 无  
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
│  3. AudioStreamPlayer：非定位音频播放器（UI / BGM）         │
│  4. AudioStreamPlayer2D / 3D：定位音频播放器                │
│  5. AudioBus：音频总线                                      │
│  6. AudioEffect：音频效果器                                 │
│  7. AudioListener2D / 3D：音频听者                          │
│  8. AudioStreamOggVorbis：OGG 音频流                        │
│  9. AudioStreamWAV：WAV 音频流                              │
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
# 2D 定位音频播放器
#
# 注意类名：引擎内置的类叫 AudioStreamPlayer2D（基类是 Node2D），
# 自定义类不要用同名 class_name，否则会遮蔽内置类。
class_name My2DAudioPlayer

extends AudioStreamPlayer2D

# 只声明引擎没有的字段。volume_db / pitch_scale / autoplay / bus /
# stream_paused 都是 AudioStreamPlayer2D 的原生成员，
# 在子类里重复 @export 会让 GDScript 4 在**解析期**就报：
#   Member "volume_db" redefined (original in native class 'AudioStreamPlayer2D')
@export var stream_path: String = ""

func _ready():
    # 加载音频流（stream 是引擎属性，直接赋值）
    if stream_path != "":
        var loaded := load(stream_path)
        if loaded is AudioStream:
            stream = loaded

    # 演示如何修改引擎原生属性
    volume_db = 0.0
    pitch_scale = 1.0

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
    # 暂停音频：AudioStreamPlayer2D 没有 pause() 方法，
    # 正确做法是设置 stream_paused 属性（没有 set_stream_paused() 方法）。
    stream_paused = true

func resume_audio():
    # 恢复音频：把 stream_paused 置回 false，会从原位置继续播
    stream_paused = false

func set_volume(volume: float):
    # 设置音量（线性 → dB）
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    # 设置音调
    pitch_scale = pitch

func set_playback_position(position: float):
    # 设置播放位置（seek 是引擎原生方法）
    seek(position)

# 播放状态与播放位置直接用引擎原生成员/方法，不要再包一层同名函数：
#   player.playing                  → 是否正在播放
#   player.get_playback_position()  → 当前播放位置（秒）
# 包一层同名函数既会遮蔽原生方法（GDScript 还会警告"引擎不会调用它"），
# 写成 `func get_playback_position(): return get_playback_position()`
# 更是无限自递归，调用即栈溢出。
```

### 2.2 3D 音频播放器

```gdscript
# 3D 定位音频播放器
#
# 类名不要叫 AudioStreamPlayer3D（会遮蔽引擎内置类）。
class_name My3DAudioPlayer

extends AudioStreamPlayer3D

# volume_db / pitch_scale / autoplay / unit_size / max_distance /
# attenuation_model / attenuation_filter_db 等全是原生成员，
# 在子类里重复 @export 会在解析期报 "Member ... redefined"。
@export var stream_path: String = ""

func _ready():
    if stream_path != "":
        var loaded := load(stream_path)
        if loaded is AudioStream:
            stream = loaded

    # Godot 4 的距离衰减完全由引擎算，参数就这三项：
    #   unit_size         —— 衰减因子，越大听得越远
    #   max_distance      —— 超过这个距离完全听不见（>0 才生效）
    #   attenuation_model —— 衰减曲线类型（见 §5.2）
    unit_size = 10.0
    max_distance = 50.0
    attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE

    # 远处声音会被低通滤波；把 cutoff 提到 20500（人耳上限）即可关闭
    attenuation_filter_db = -24.0
    attenuation_filter_cutoff_hz = 5000.0

    # 多普勒：选择在哪一步计算多普勒频移
    doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_PHYSICS_STEP

    # 发声角度：只在正前方锥形内不衰减
    emission_angle_enabled = false
    emission_angle_degrees = 45.0

    # 区域混响：哪些 Area3D 层会影响这个播放器
    area_mask = 1

    # 立体声扩展强度
    panning_strength = 1.0

func play_audio():
    play()

func stop_audio():
    stop()

func pause_audio():
    # 没有 pause() 方法，用 stream_paused 属性
    stream_paused = true

func resume_audio():
    stream_paused = false

func set_volume(volume: float):
    volume_db = linear_to_db(volume)

func set_pitch(pitch: float):
    pitch_scale = pitch

func set_attenuation_model(model: int):
    # 衰减模型是枚举，见 §5.2
    attenuation_model = model

func set_max_distance(distance: float):
    max_distance = distance
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
    # Godot 4 的信号连接用 Callable：
    # Object.connect(signal, callable) 已移除 3.x 的 connect(signal, target, method) 三参重载
    if audio_player:
        audio_player.finished.connect(_on_audio_finished)
    
    if audio_player_3d:
        audio_player_3d.finished.connect(_on_audio_3d_finished)

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
    
    # ⚠️ 不要用 `audio_server.bus_count = 8` 来"规划"总线。
    # bus_count 的 setter（set_bus_count）会**重建总线列表**：
    #   - 数量变小时，超出部分的总线被直接销毁（连同名称与效果器）；
    #   - 数量变大时，新建的总线用的是占位名 "New Bus" / "New Bus 2"。
    # 正规做法是在编辑器的「Audio 总线」面板里配好，存成
    # res://default_bus_layout.tres；运行时只做增量调整。
    
    # add_bus() 不带参数 = 追加到末尾；add_bus(pos) 会在 pos 处插入
    var bus_names = ["Music", "SFX", "Voice", "Ambient", "UI", "Reverb", "Effects"]
    for bus_name in bus_names:
        if audio_server.get_bus_index(bus_name) == -1:
            audio_server.add_bus()
            var idx := audio_server.bus_count - 1
            audio_server.set_bus_name(idx, bus_name)

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
    
    # ⚠️ bus_count 的 setter 会重建总线列表并清掉已有总线的名称与效果器，
    # 这里改用 add_bus() 增量创建（详见 47 篇「总线与支路」）。
    
    # 创建总线（索引 0 默认就是 Master）
    var idx = 0
    for bus_name in bus_settings:
        if idx == 0:
            audio_server.set_bus_name(idx, bus_name)
        else:
            audio_server.add_bus()
            idx = audio_server.bus_count - 1
            audio_server.set_bus_name(idx, bus_name)
        
        # 设置初始音量
        var volume = bus_settings[bus_name]["volume"]
        audio_server.set_bus_volume_db(idx, linear_to_db(volume))
        
        # 设置初始静音
        var mute = bus_settings[bus_name]["mute"]
        audio_server.set_bus_mute(idx, mute)
        
        idx += 1

func update_bus_settings():
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
        reverb.room_size = 0.8          # 0~1，模拟房间尺寸
        reverb.damping = 0.5            # 0~1，墙壁反射率（引擎属性是 damping，没有 dampening）
        reverb.wet = 0.2                # 0~1，湿信号占比
        reverb.dry = 0.8                # 0~1，干信号占比
        reverb.predelay_msec = 20.0     # 预延迟，单位毫秒（引擎属性是 predelay_msec）
        audio_server.add_bus_effect(master_bus_idx, reverb)
    
    # 为音乐总线添加均衡器
    var music_bus_idx = audio_server.get_bus_index("Music")
    if music_bus_idx != -1:
        # 4.x 只有 AudioEffectEQ（基类）/ EQ6 / EQ10 / EQ21，没有 AudioEffectEQ2
        var eq = AudioEffectEQ10.new()
        # 频点数量用 get_band_count() 拿，增益用 set_band_gain_db()（单位 dB）
        for i in range(eq.get_band_count()):
            eq.set_band_gain_db(i, 0.0)
        eq.set_band_gain_db(0, 6.0)   # 低频提升
        eq.set_band_gain_db(4, 3.0)   # 中频提升
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
        reverb.damping = 0.5
        reverb.wet = 0.2
        reverb.dry = 0.8
        reverb.predelay_msec = 20.0
        audio_server.add_bus_effect(bus_idx, reverb)

func add_eq_to_bus(bus_name: String):
    # 为总线添加均衡器
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        var eq = AudioEffectEQ10.new()
        for i in range(eq.get_band_count()):
            eq.set_band_gain_db(i, 0.0)
        eq.set_band_gain_db(0, 6.0)  # 低频提升
        eq.set_band_gain_db(4, 3.0)  # 中频提升
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

# ⚠️ room_size / damping / wet / dry 都是 AudioEffectReverb 的原生成员，
# 在子类里用 @export 重新声明会让 GDScript 4 在解析期直接报错：
#   Member "room_size" redefined (original in native class 'AudioEffectReverb')
# 这里只写"书特有"的字段，参数一律用引擎属性。

@export var preset_name: String = "default"

func _ready():
    # 演示如何修改引擎原生属性
    room_size = 0.8
    damping = 0.5
    wet = 0.2
    dry = 0.8
    predelay_msec = 20.0

func update_parameters():
    # 更新参数（把引擎属性夹到合法区间）
    room_size = clamp(room_size, 0.0, 1.0)
    damping = clamp(damping, 0.0, 1.0)
    wet = clamp(wet, 0.0, 1.0)
    dry = clamp(dry, 0.0, 1.0)

func set_room_size(size: float):
    # 设置房间大小（0~1）
    room_size = clamp(size, 0.0, 1.0)

func set_damping(damp: float):
    # 设置阻尼（0~1）—— 引擎属性名是 damping，没有 dampening
    damping = clamp(damp, 0.0, 1.0)

func set_wet_amount(amount: float):
    # 设置湿信号量（0~1）
    wet = clamp(amount, 0.0, 1.0)

func set_dry_amount(amount: float):
    # 设置干信号量（0~1）
    dry = clamp(amount, 0.0, 1.0)

func set_predelay(msec: float):
    # 设置预延迟（毫秒）—— 引擎属性名是 predelay_msec
    predelay_msec = clamp(msec, 0.0, 500.0)
```

### 4.2 均衡器效果器

```gdscript
# 均衡器效果器
class_name EQEffect

# 4.x 只有 AudioEffectEQ（基类）/ EQ6 / EQ10 / EQ21，没有 AudioEffectEQ2
extends AudioEffectEQ10

# low_gain / mid_gain / high_gain 是"书特有"字段，不是引擎成员，可以 @export；
# 引擎的频点增益一律用 set_band_gain_db() 写（单位 dB）。
@export var low_gain: float = 1.0
@export var mid_gain: float = 1.0
@export var high_gain: float = 1.0

func _ready():
    # 设置均衡器参数
    update_parameters()

func update_parameters():
    # 更新参数：EQ10 的 10 个频点按对数分布，低/中/高各取一段
    var count := get_band_count()
    var low_band := int(count * 0.2)
    var mid_band := int(count * 0.5)
    for i in range(count):
        set_band_gain_db(i, 0.0)
    for i in range(0, low_band):
        set_band_gain_db(i, linear_to_db(low_gain))
    for i in range(mid_band, mid_band + 2):
        set_band_gain_db(i, linear_to_db(mid_gain))
    for i in range(count - 2, count):
        set_band_gain_db(i, linear_to_db(high_gain))

func set_low_gain(gain: float):
    # 设置低频增益（线性倍率）
    low_gain = gain
    var count := get_band_count()
    for i in range(int(count * 0.2)):
        set_band_gain_db(i, linear_to_db(low_gain))

func set_mid_gain(gain: float):
    # 设置中频增益
    mid_gain = gain
    var mid_band := int(get_band_count() * 0.5)
    for i in range(mid_band, mid_band + 2):
        set_band_gain_db(i, linear_to_db(mid_gain))

func set_high_gain(gain: float):
    # 设置高频增益
    high_gain = gain
    var count := get_band_count()
    for i in range(count - 2, count):
        set_band_gain_db(i, linear_to_db(high_gain))

func set_band_gain(band_idx: int, gain_db: float):
    # 设置指定频段增益（引擎方法名是 set_band_gain_db，单位 dB）
    if band_idx >= 0 and band_idx < get_band_count():
        set_band_gain_db(band_idx, gain_db)
```

### 4.3 压缩器效果器

```gdscript
# 压缩器效果器
class_name CompressorEffect

extends AudioEffectCompressor

# ⚠️ ratio / threshold / attack_us / release_ms 全是原生成员，
# 重复 @export 会在解析期报 "Member ... redefined"。
# 这里只保留书特有字段，参数直接用引擎属性。

@export var preset_name: String = "default"

func _ready():
    # 设置压缩器参数
    update_parameters()

func update_parameters():
    # 更新参数（把引擎属性夹到合法区间）
    ratio = clamp(ratio, 1.0, 48.0)
    threshold = clamp(threshold, -60.0, 0.0)
    attack_us = clamp(attack_us, 20.0, 2000.0)
    release_ms = clamp(release_ms, 20.0, 2000.0)
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
    
    # 连接完成信号以清理资源（Godot 4 用 Callable 形式）
    player.finished.connect(player.queue_free)
    
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
    # ⚠️ AudioStreamPlayer 没有 loop 属性，循环要设在"流"上：
    #   AudioStreamOggVorbis / AudioStreamMP3 → loop(bool) + loop_offset(float)
    #   AudioStreamWAV                    → loop_mode + loop_begin + loop_end
    if stream is AudioStreamOggVorbis:
        var ogg := stream as AudioStreamOggVorbis
        ogg.loop = true
        ogg.loop_offset = 0.0
    elif stream is AudioStreamWAV:
        # WAV 的循环区间（单位：采样数）会在导入时自动带过来，这里只切模式
        var wav := stream as AudioStreamWAV
        wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
    
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

# ⚠️ AudioStreamPlayer3D **没有**可注入自定义衰减曲线的接口，
# 也没有 min_distance 属性。距离衰减完全由引擎按
# unit_size + max_distance + attenuation_model 计算，
# 所以这里演示的是"选模型"，不是"算曲线"。
@export var player_path: NodePath = ^"AudioStreamPlayer3D"

func _ready():
    var player := get_node(player_path) as AudioStreamPlayer3D
    if player == null:
        return

    # 1) 衰减因子：越大越"穿得远"
    player.unit_size = 10.0

    # 2) 最大距离：超过就完全听不见（>0 才生效，且始终是线性截断）
    player.max_distance = 40.0

    # 3) 衰减模型：引擎内置四种
    player.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE

    # 远处的低通滤波：截止频率 5000Hz，衰减 -24dB；
    # 把 cutoff 提到 20500（人耳上限）即可关闭该滤波。
    player.attenuation_filter_cutoff_hz = 5000.0
    player.attenuation_filter_db = -24.0

func set_attenuation_model(model: int):
    # 四种模型（枚举 AudioStreamPlayer3D.AttenuationModel）：
    #   ATTENUATION_INVERSE_DISTANCE        线性反比
    #   ATTENUATION_INVERSE_SQUARE_DISTANCE  平方反比（最接近物理直觉）
    #   ATTENUATION_LOGARITHMIC              对数
    #   ATTENUATION_DISABLED                 不随距离衰减（仍保留声像）
    var player := get_node(player_path) as AudioStreamPlayer3D
    if player:
        player.attenuation_model = model

func set_max_distance(dist: float):
    var player := get_node(player_path) as AudioStreamPlayer3D
    if player:
        player.max_distance = dist

func set_unit_size(size: float):
    var player := get_node(player_path) as AudioStreamPlayer3D
    if player:
        player.unit_size = size

func make_listener_current(listener: AudioListener3D):
    # Godot 4 的听者由 AudioListener3D 决定：
    # 默认从摄像机位置听到，加入 AudioListener3D 并 make_current() 后改由它决定。
    # 不要再用 get_viewport().get_camera_3d() 去"猜"听者位置。
    listener.make_current()
```

### 5.3 音频性能监控

```gdscript
# 音频性能监控
class_name AudioPerformanceMonitor

extends Node

var active_players = 0         # 实际含义是"总线数量"，引擎没有活跃播放器计数
var mix_rate = 0.0              # AudioServer.get_mix_rate()
var output_latency = 0.0       # AudioServer.get_output_latency()，单位秒
var time_since_last_mix = 0.0  # 距上次混音的相对时间，单位秒

func _ready():
    # 开始监控
    start_monitoring()

func start_monitoring():
    # 连接定时器以定期更新
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.timeout.connect(_update_stats)
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计信息
    var audio_server = AudioServer
    active_players = audio_server.bus_count
    # 采样率是方法 get_mix_rate()（返回 float）；引擎没有 input_latency，
    # 只有 get_output_latency()
    mix_rate = audio_server.get_mix_rate()
    output_latency = audio_server.get_output_latency()
    # ⚠️ Godot 4 **没有**暴露混音线程的 CPU 占用百分比：
    # AudioServer 没有 performance_get()，Performance 里也没有 time_usage/* 监视器
    #（那是 Godot 3.x 的名字）。只能自己采样 get_time_since_last_mix()
    #（官方描述："距上次混音的相对时间"，单位秒）做趋势观察。
    time_since_last_mix = audio_server.get_time_since_last_mix()

func get_bus_count() -> int:
    return active_players

func get_mix_rate() -> float:
    return mix_rate

func get_output_latency() -> float:
    return output_latency

func get_time_since_last_mix() -> float:
    return time_since_last_mix

func print_stats():
    print("Audio Stats:")
    print("- Bus Count: ", get_bus_count())
    print("- Mix Rate: ", get_mix_rate())
    print("- Output Latency: ", get_output_latency())
    print("- Time Since Last Mix: ", get_time_since_last_mix())
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
    
    # 连接完成信号以清理资源（Godot 4 用 Callable 形式）
    player_3d.finished.connect(player_3d.queue_free)
    
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
    # Godot 4 没有暴露混音线程的 CPU 占用，只能返回混音时序指标
    return performance_monitor.get_time_since_last_mix()
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
| AudioStreamPlayer | 非定位音频播放器（UI / 背景音乐） |
| AudioStreamPlayer2D | 2D 定位音频播放器 |
| AudioStreamPlayer3D | 3D 定位音频播放器 |
| AudioListener3D | 3D 音频听者，make_current() 后生效 |
| AudioBus | 音频总线 |
| AudioEffect | 音频效果器 |
| AudioServer | 音频服务器（总线与效果器的管理者） |
| attenuation_model | 3D 距离衰减模型（4 种枚举） |

---

## 🔗 延伸阅读

- **官方文档**: [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **官方文档**: [Audio streams](https://docs.godotengine.org/en/stable/tutorials/audio/audio_streams.html)
- **类参考**: [AudioServer](https://docs.godotengine.org/en/stable/classes/class_audioserver.html)
- **源码位置**: `servers/audio/`、`servers/audio/effects/`

---

## 📋 下一章预告

**第 46 篇：音频播放器**

- 音频播放器基础
- 2D / 3D 定位音频播放器
- 音频流类型与程序化音频
- 音频播放器优化

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 42 篇：动画性能优化](/articles/42-particle-system.md)
**下一篇**: [第 46 篇：音频播放器](/articles/46-audio-player.md)

---

*写作时间：2026-03-20*  
*字数：约 600 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 14:00*
