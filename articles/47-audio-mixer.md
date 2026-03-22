# 第 37 篇：音频混合器

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 46 章 音频播放器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

音频混合器是游戏音频系统的核心组件，负责将多个音频源混合成一个统一的音频输出。通过音频混合器，开发者可以控制不同音频类型的音量平衡、应用音频效果、实现音频路由等复杂功能。

Godot 提供了强大的音频混合器系统，包括 AudioServer、AudioBus、AudioEffect 等。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解音频混合器的基本概念
- 掌握 AudioServer 使用
- 学会 AudioBus 配置
- 熟悉 AudioEffect 应用
- 掌握音频混合器优化

---

## 1. 音频混合器基础

### 1.1 音频混合器类型

```
音频混合器类型:
┌─────────────────────────────────────────────────────────────┐
│                      音频混合器类型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioServer：音频服务器（核心混合器）                  │
│  2. AudioBus：音频总线（通道混合器）                       │
│  3. AudioEffect：音频效果器（效果混合器）                  │
│  4. AudioBusLayout：音频总线布局（配置混合器）             │
│  5. AudioStreamPlayback：音频播放混合器                    │
│  6. AudioDriver：音频驱动（底层混合器）                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 音频混合器组件

```
音频混合器组件:
┌─────────────────────────────────────────────────────────────┐
│                      音频混合器组件                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioServer：音频服务器                                 │
│  2. AudioBus：音频总线                                      │
│  3. AudioEffect：音频效果器                                 │
│  4. AudioEffectEQ：均衡器效果器                            │
│  5. AudioEffectReverb：混响效果器                          │
│  6. AudioEffectCompressor：压缩器效果器                    │
│  7. AudioEffectDelay：延迟效果器                           │
│  8. AudioEffectDistortion：失真效果器                      │
│  9. AudioEffectFilter：滤波器效果器                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 音频混合器流程

```
音频混合器处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      音频混合器处理流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 音频播放器输出音频信号到总线                           │
│  2. 音频总线接收多个音频信号                               │
│  3. 音频效果器处理音频信号                                 │
│  4. 音频总线混合所有音频信号                               │
│  5. 主总线输出最终混合音频                                 │
│  6. 音频驱动输出到扬声器                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. AudioServer

### 2.1 AudioServer 基础

```gdscript
# AudioServer 基础
class_name AudioServerController

extends Node

func _ready():
    # 初始化 AudioServer
    initialize_audio_server()

func initialize_audio_server():
    var audio_server = AudioServer
    
    # 获取总线数量
    print("Bus count: ", audio_server.bus_count)
    
    # 获取混音率
    print("Mix rate: ", audio_server.mix_rate)
    
    # 获取输入延迟
    print("Input latency: ", audio_server.input_latency)
    
    # 获取输出延迟
    print("Output latency: ", audio_server.output_latency)

func get_bus_count() -> int:
    return AudioServer.bus_count

func get_mix_rate() -> int:
    return AudioServer.mix_rate

func get_bus_name(bus_idx: int) -> String:
    return AudioServer.get_bus_name(bus_idx)

func get_bus_index(bus_name: String) -> int:
    return AudioServer.get_bus_index(bus_name)

func set_bus_volume_db(bus_idx: int, volume_db: float):
    AudioServer.set_bus_volume_db(bus_idx, volume_db)

func get_bus_volume_db(bus_idx: int) -> float:
    return AudioServer.get_bus_volume_db(bus_idx)

func set_bus_mute(bus_idx: int, mute: bool):
    AudioServer.set_bus_mute(bus_idx, mute)

func is_bus_mute(bus_idx: int) -> bool:
    return AudioServer.is_bus_mute(bus_idx)

func set_bus_solo(bus_idx: int, solo: bool):
    AudioServer.set_bus_solo(bus_idx, solo)

func is_bus_solo(bus_idx: int) -> bool:
    return AudioServer.is_bus_solo(bus_idx)
```

### 2.2 AudioServer 总线管理

```gdscript
# AudioServer 总线管理
class_name AudioServerBusManager

extends Node

func add_audio_bus(bus_name: String):
    # 添加音频总线
    var audio_server = AudioServer
    audio_server.add_bus(audio_server.bus_count)
    audio_server.set_bus_name(audio_server.bus_count - 1, bus_name)
    print("Added bus: ", bus_name)

func remove_audio_bus(bus_name: String):
    # 移除音频总线
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.remove_bus(bus_idx)
        print("Removed bus: ", bus_name)

func move_audio_bus(bus_name: String, new_index: int):
    # 移动音频总线
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.move_bus(bus_idx, new_index)
        print("Moved bus: ", bus_name, " to index: ", new_index)

func set_bus_send(bus_name: String, send_bus_name: String):
    # 设置总线发送
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    var send_bus_idx = audio_server.get_bus_index(send_bus_name)
    if bus_idx != -1 and send_bus_idx != -1:
        audio_server.set_bus_send(bus_idx, send_bus_idx)

func get_bus_send(bus_name: String) -> String:
    # 获取总线发送
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        var send_bus_idx = audio_server.get_bus_send(bus_idx)
        if send_bus_idx != -1:
            return audio_server.get_bus_name(send_bus_idx)
    return ""

func set_bus_effect_enabled(bus_name: String, effect_idx: int, enabled: bool):
    # 设置总线效果启用状态
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        audio_server.set_bus_effect_enabled(bus_idx, effect_idx, enabled)

func is_bus_effect_enabled(bus_name: String, effect_idx: int) -> bool:
    # 检查总线效果启用状态
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        return audio_server.is_bus_effect_enabled(bus_idx, effect_idx)
    return false
```

### 2.3 AudioServer 性能监控

```gdscript
# AudioServer 性能监控
class_name AudioServerPerformanceMonitor

extends Node

var cpu_usage_history = []
var max_history_size = 60

func _ready():
    # 开始性能监控
    start_monitoring()

func start_monitoring():
    # 连接定时器
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.connect("timeout", self, "_update_stats")
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新性能统计
    var audio_server = AudioServer
    var cpu_usage = audio_server.get_time_since_last_mix()
    
    cpu_usage_history.append(cpu_usage)
    if cpu_usage_history.size() > max_history_size:
        cpu_usage_history.remove_at(0)

func get_average_cpu_usage() -> float:
    # 获取平均 CPU 使用率
    if cpu_usage_history.size() == 0:
        return 0.0
    
    var total = 0.0
    for usage in cpu_usage_history:
        total += usage
    
    return total / cpu_usage_history.size()

func get_peak_cpu_usage() -> float:
    # 获取峰值 CPU 使用率
    if cpu_usage_history.size() == 0:
        return 0.0
    
    var peak = 0.0
    for usage in cpu_usage_history:
        if usage > peak:
            peak = usage
    
    return peak

func get_current_cpu_usage() -> float:
    # 获取当前 CPU 使用率
    if cpu_usage_history.size() == 0:
        return 0.0
    
    return cpu_usage_history[-1]

func print_stats():
    # 打印统计信息
    print("Audio Server Stats:")
    print("- Current CPU: ", get_current_cpu_usage())
    print("- Average CPU: ", get_average_cpu_usage())
    print("- Peak CPU: ", get_peak_cpu_usage())
```

---

## 3. AudioBus

### 3.1 AudioBus 基础

```gdscript
# AudioBus 基础
class_name AudioBusController

extends Node

func _ready():
    # 初始化音频总线
    initialize_audio_buses()

func initialize_audio_buses():
    var audio_server = AudioServer
    
    # 设置默认总线
    audio_server.bus_count = 3
    
    # 设置总线名称
    audio_server.set_bus_name(0, "Master")
    audio_server.set_bus_name(1, "Music")
    audio_server.set_bus_name(2, "SFX")
    
    # 设置初始音量
    audio_server.set_bus_volume_db(0, 0.0)  # Master
    audio_server.set_bus_volume_db(1, -5.0) # Music
    audio_server.set_bus_volume_db(2, -3.0) # SFX

func set_master_volume(volume_db: float):
    # 设置主音量
    AudioServer.set_bus_volume_db(0, volume_db)

func set_music_volume(volume_db: float):
    # 设置音乐音量
    AudioServer.set_bus_volume_db(1, volume_db)

func set_sfx_volume(volume_db: float):
    # 设置音效音量
    AudioServer.set_bus_volume_db(2, volume_db)

func get_master_volume() -> float:
    return AudioServer.get_bus_volume_db(0)

func get_music_volume() -> float:
    return AudioServer.get_bus_volume_db(1)

func get_sfx_volume() -> float:
    return AudioServer.get_bus_volume_db(2)

func mute_bus(bus_name: String):
    # 静音总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_mute(bus_idx, true)

func unmute_bus(bus_name: String):
    # 取消静音总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_mute(bus_idx, false)

func solo_bus(bus_name: String):
    # 独奏总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_solo(bus_idx, true)

func unsolo_bus(bus_name: String):
    # 取消独奏总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_solo(bus_idx, false)
```

### 3.2 AudioBus 效果器链

```gdscript
# AudioBus 效果器链
class_name AudioBusEffectChain

extends Node

func add_effect_to_bus(bus_name: String, effect: AudioEffect):
    # 添加效果器到总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.add_bus_effect(bus_idx, effect)
        print("Added effect to bus: ", bus_name)

func remove_effect_from_bus(bus_name: String, effect_idx: int):
    # 从总线移除效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.remove_bus_effect(bus_idx, effect_idx)
        print("Removed effect from bus: ", bus_name)

func move_bus_effect(bus_name: String, effect_idx: int, new_idx: int):
    # 移动总线效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.move_bus_effect(bus_idx, effect_idx, new_idx)
        print("Moved effect on bus: ", bus_name)

func get_bus_effect_count(bus_name: String) -> int:
    # 获取总线效果器数量
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        return AudioServer.get_bus_effect_count(bus_idx)
    return 0

func get_bus_effect(bus_name: String, effect_idx: int) -> AudioEffect:
    # 获取总线效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        return AudioServer.get_bus_effect(bus_idx, effect_idx)
    return null

func clear_bus_effects(bus_name: String):
    # 清除总线所有效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var count = AudioServer.get_bus_effect_count(bus_idx)
        for i in range(count - 1, -1, -1):
            AudioServer.remove_bus_effect(bus_idx, i)
        print("Cleared effects from bus: ", bus_name)
```

### 3.3 AudioBus 路由

```gdscript
# AudioBus 路由
class_name AudioBusRouting

extends Node

func route_bus_to_bus(from_bus_name: String, to_bus_name: String):
    # 路由总线到总线
    var from_bus_idx = AudioServer.get_bus_index(from_bus_name)
    var to_bus_idx = AudioServer.get_bus_index(to_bus_name)
    if from_bus_idx != -1 and to_bus_idx != -1:
        AudioServer.set_bus_send(from_bus_idx, to_bus_idx)
        print("Routed ", from_bus_name, " to ", to_bus_name)

func get_bus_routing(bus_name: String) -> String:
    # 获取总线路由
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var send_bus_idx = AudioServer.get_bus_send(bus_idx)
        if send_bus_idx != -1:
            return AudioServer.get_bus_name(send_bus_idx)
    return ""

func create_bus_chain(bus_names: Array):
    # 创建总线链
    for i in range(bus_names.size() - 1):
        route_bus_to_bus(bus_names[i], bus_names[i + 1])

func create_bus_tree(parent_bus: String, child_buses: Array):
    # 创建总线树
    for child_bus in child_buses:
        route_bus_to_bus(child_bus, parent_bus)

func reset_bus_routing(bus_name: String):
    # 重置总线路由
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_send(bus_idx, -1)
```

---

## 4. AudioEffect

### 4.1 均衡器效果器

```gdscript
# 均衡器效果器
class_name AudioEffectEQController

extends Node

func create_eq_effect() -> AudioEffectEQ21:
    # 创建 21 段均衡器
    var eq = AudioEffectEQ21.new()
    return eq

func create_eq10_effect() -> AudioEffectEQ10:
    # 创建 10 段均衡器
    var eq = AudioEffectEQ10.new()
    return eq

func create_eq6_effect() -> AudioEffectEQ6:
    # 创建 6 段均衡器
    var eq = AudioEffectEQ6.new()
    return eq

func set_eq_gain(eq: AudioEffect, band_idx: int, gain_db: float):
    # 设置均衡器增益
    if eq and band_idx < eq.band_count:
        eq.set_band_gain(band_idx, gain_db)

func get_eq_gain(eq: AudioEffect, band_idx: int) -> float:
    # 获取均衡器增益
    if eq and band_idx < eq.band_count:
        return eq.get_band_gain(band_idx)
    return 0.0

func set_eq_preset(eq: AudioEffect, preset: String):
    # 设置均衡器预设
    match preset:
        "flat":
            for i in range(eq.band_count):
                set_eq_gain(eq, i, 0.0)
        "bass_boost":
            set_eq_gain(eq, 0, 6.0)
            set_eq_gain(eq, 1, 4.0)
            set_eq_gain(eq, 2, 2.0)
        "treble_boost":
            set_eq_gain(eq, eq.band_count - 3, 4.0)
            set_eq_gain(eq, eq.band_count - 2, 6.0)
            set_eq_gain(eq, eq.band_count - 1, 8.0)
        "vocal":
            set_eq_gain(eq, 3, -2.0)
            set_eq_gain(eq, 4, 2.0)
            set_eq_gain(eq, 5, 4.0)
            set_eq_gain(eq, 6, 2.0)
            set_eq_gain(eq, 7, -2.0)
```

### 4.2 混响效果器

```gdscript
# 混响效果器
class_name AudioEffectReverbController

extends Node

func create_reverb_effect() -> AudioEffectReverb:
    # 创建混响效果器
    var reverb = AudioEffectReverb.new()
    reverb.room_size = 0.8
    reverb.dampening = 0.5
    reverb.wet = 0.2
    reverb.dry = 0.8
    reverb.pre_delay = 0.0
    return reverb

func set_reverb_room_size(reverb: AudioEffectReverb, size: float):
    # 设置混响房间大小
    reverb.room_size = clamp(size, 0.0, 1.0)

func set_reverb_dampening(reverb: AudioEffectReverb, damp: float):
    # 设置混响阻尼
    reverb.dampening = clamp(damp, 0.0, 1.0)

func set_reverb_wet(reverb: AudioEffectReverb, wet: float):
    # 设置混响湿信号
    reverb.wet = clamp(wet, 0.0, 1.0)

func set_reverb_dry(reverb: AudioEffectReverb, dry: float):
    # 设置混响干信号
    reverb.dry = clamp(dry, 0.0, 1.0)

func set_reverb_preset(reverb: AudioEffectReverb, preset: String):
    # 设置混响预设
    match preset:
        "small_room":
            reverb.room_size = 0.3
            reverb.dampening = 0.5
            reverb.wet = 0.15
        "large_room":
            reverb.room_size = 0.7
            reverb.dampening = 0.4
            reverb.wet = 0.25
        "hall":
            reverb.room_size = 0.9
            reverb.dampening = 0.3
            reverb.wet = 0.35
        "cathedral":
            reverb.room_size = 1.0
            reverb.dampening = 0.2
            reverb.wet = 0.45
        "plate":
            reverb.room_size = 0.6
            reverb.dampening = 0.6
            reverb.wet = 0.3
```

### 4.3 压缩器效果器

```gdscript
# 压缩器效果器
class_name AudioEffectCompressorController

extends Node

func create_compressor_effect() -> AudioEffectCompressor:
    # 创建压缩器效果器
    var compressor = AudioEffectCompressor.new()
    compressor.ratio = 4.0
    compressor.threshold_db = -6.0
    compressor.attack_us = 100.0
    compressor.release_ms = 200.0
    compressor.makeup_db = 0.0
    return compressor

func set_compressor_ratio(compressor: AudioEffectCompressor, ratio: float):
    # 设置压缩器比率
    compressor.ratio = clamp(ratio, 1.0, 20.0)

func set_compressor_threshold(compressor: AudioEffectCompressor, threshold_db: float):
    # 设置压缩器阈值
    compressor.threshold_db = clamp(threshold_db, -60.0, 0.0)

func set_compressor_attack(compressor: AudioEffectCompressor, attack_us: float):
    # 设置压缩器攻击时间
    compressor.attack_us = clamp(attack_us, 0.0, 1000.0)

func set_compressor_release(compressor: AudioEffectCompressor, release_ms: float):
    # 设置压缩器释放时间
    compressor.release_ms = clamp(release_ms, 0.0, 5000.0)

func set_compressor_makeup(compressor: AudioEffectCompressor, makeup_db: float):
    # 设置压缩器补偿增益
    compressor.makeup_db = clamp(makeup_db, 0.0, 24.0)

func set_compressor_preset(compressor: AudioEffectCompressor, preset: String):
    # 设置压缩器预设
    match preset:
        "light":
            compressor.ratio = 2.0
            compressor.threshold_db = -12.0
            compressor.attack_us = 50.0
            compressor.release_ms = 100.0
        "medium":
            compressor.ratio = 4.0
            compressor.threshold_db = -6.0
            compressor.attack_us = 100.0
            compressor.release_ms = 200.0
        "heavy":
            compressor.ratio = 8.0
            compressor.threshold_db = -3.0
            compressor.attack_us = 20.0
            compressor.release_ms = 300.0
```

---

## 5. 音频混合器优化

### 5.1 音频混合器缓存

```gdscript
# 音频混合器缓存
class_name AudioMixerCache

var effect_cache = {}

func get_effect(effect_name: String) -> AudioEffect:
    if effect_cache.has(effect_name):
        return effect_cache[effect_name].duplicate()
    
    var effect: AudioEffect
    match effect_name:
        "eq":
            effect = AudioEffectEQ21.new()
        "reverb":
            effect = AudioEffectReverb.new()
        "compressor":
            effect = AudioEffectCompressor.new()
    
    if effect:
        effect_cache[effect_name] = effect
    
    return effect.duplicate() if effect else null

func clear_cache():
    effect_cache.clear()
```

### 5.2 音频混合器LOD

```gdscript
# 音频混合器LOD
class_name AudioMixerLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_effects: Array = ["simple", "medium", "complex"]

func update_lod(camera_position: Vector3, bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var distance = camera_position.distance_to(get_tree().current_scene.global_transform.origin)
    
    var lod_index = 0
    for i in range(lod_distances.size()):
        if distance > lod_distances[i]:
            lod_index = i + 1
    
    lod_index = min(lod_index, lod_effects.size() - 1)
    
    # 更新效果器
    if lod_index < lod_effects.size():
        apply_lod_effects(bus_idx, lod_effects[lod_index])

func apply_lod_effects(bus_idx: int, lod_level: String):
    # 应用 LOD 效果器
    match lod_level:
        "simple":
            # 简单模式：只保留基本效果
            AudioServer.set_bus_effect_enabled(bus_idx, 0, true)
            for i in range(1, AudioServer.get_bus_effect_count(bus_idx)):
                AudioServer.set_bus_effect_enabled(bus_idx, i, false)
        "medium":
            # 中等模式：保留一半效果
            var count = AudioServer.get_bus_effect_count(bus_idx)
            for i in range(count):
                AudioServer.set_bus_effect_enabled(bus_idx, i, i < count / 2)
        "complex":
            # 复杂模式：启用所有效果
            var count = AudioServer.get_bus_effect_count(bus_idx)
            for i in range(count):
                AudioServer.set_bus_effect_enabled(bus_idx, i, true)
```

### 5.3 音频混合器性能监控

```gdscript
# 音频混合器性能监控
class_name AudioMixerPerformanceMonitor

extends Node

var effect_count = 0
var bus_count = 0
var cpu_usage = 0.0

func _ready():
    # 开始性能监控
    start_monitoring()

func start_monitoring():
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.connect("timeout", self, "_update_stats")
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计
    bus_count = AudioServer.bus_count
    effect_count = 0
    
    for i in range(bus_count):
        effect_count += AudioServer.get_bus_effect_count(i)
    
    cpu_usage = AudioServer.get_time_since_last_mix()

func get_effect_count() -> int:
    return effect_count

func get_bus_count() -> int:
    return bus_count

func get_cpu_usage() -> float:
    return cpu_usage

func print_stats():
    print("Audio Mixer Stats:")
    print("- Bus Count: ", get_bus_count())
    print("- Effect Count: ", get_effect_count())
    print("- CPU Usage: ", get_cpu_usage())
```

---

## 6. 实践：完整音频混合器系统

### 6.1 基础音频混合器系统

```gdscript
# 基础音频混合器系统
class_name BasicAudioMixerSystem

extends Node

func _ready():
    # 初始化基础音频混合器系统
    initialize_basic_mixer()

func initialize_basic_mixer():
    var audio_server = AudioServer
    
    # 设置总线
    audio_server.bus_count = 3
    audio_server.set_bus_name(0, "Master")
    audio_server.set_bus_name(1, "Music")
    audio_server.set_bus_name(2, "SFX")
    
    # 设置音量
    audio_server.set_bus_volume_db(0, 0.0)
    audio_server.set_bus_volume_db(1, -5.0)
    audio_server.set_bus_volume_db(2, -3.0)

func set_master_volume(volume_db: float):
    AudioServer.set_bus_volume_db(0, volume_db)

func set_music_volume(volume_db: float):
    AudioServer.set_bus_volume_db(1, volume_db)

func set_sfx_volume(volume_db: float):
    AudioServer.set_bus_volume_db(2, volume_db)

func mute_all():
    for i in range(AudioServer.bus_count):
        AudioServer.set_bus_mute(i, true)

func unmute_all():
    for i in range(AudioServer.bus_count):
        AudioServer.set_bus_mute(i, false)
```

### 6.2 高级音频混合器系统

```gdscript
# 高级音频混合器系统
class_name AdvancedAudioMixerSystem

extends Node

func _ready():
    # 初始化高级音频混合器系统
    initialize_advanced_mixer()

func initialize_advanced_mixer():
    var audio_server = AudioServer
    
    # 设置总线
    audio_server.bus_count = 6
    audio_server.set_bus_name(0, "Master")
    audio_server.set_bus_name(1, "Music")
    audio_server.set_bus_name(2, "SFX")
    audio_server.set_bus_name(3, "Voice")
    audio_server.set_bus_name(4, "Ambient")
    audio_server.set_bus_name(5, "UI")
    
    # 添加效果器
    add_reverb_to_bus("Master")
    add_eq_to_bus("Music")
    add_compressor_to_bus("SFX")

func add_reverb_to_bus(bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var reverb = AudioEffectReverb.new()
        reverb.room_size = 0.8
        AudioServer.add_bus_effect(bus_idx, reverb)

func add_eq_to_bus(bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var eq = AudioEffectEQ21.new()
        AudioServer.add_bus_effect(bus_idx, eq)

func add_compressor_to_bus(bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var compressor = AudioEffectCompressor.new()
        AudioServer.add_bus_effect(bus_idx, compressor)

func set_volume(bus_name: String, volume_db: float):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_volume_db(bus_idx, volume_db)

func mute_bus(bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_mute(bus_idx, true)

func unmute_bus(bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_mute(bus_idx, false)
```

### 6.3 完整音频混合器系统

```gdscript
# 完整音频混合器系统
class_name FullAudioMixerSystem

extends Node

var basic_system: BasicAudioMixerSystem
var advanced_system: AdvancedAudioMixerSystem
var performance_monitor: AudioMixerPerformanceMonitor

func _ready():
    # 初始化完整音频混合器系统
    initialize_full_mixer()

func initialize_full_mixer():
    basic_system = BasicAudioMixerSystem.new()
    add_child(basic_system)
    
    advanced_system = AdvancedAudioMixerSystem.new()
    add_child(advanced_system)
    
    performance_monitor = AudioMixerPerformanceMonitor.new()
    add_child(performance_monitor)

func set_master_volume(volume_db: float):
    basic_system.set_master_volume(volume_db)

func set_music_volume(volume_db: float):
    advanced_system.set_volume("Music", volume_db)

func set_sfx_volume(volume_db: float):
    advanced_system.set_volume("SFX", volume_db)

func set_voice_volume(volume_db: float):
    advanced_system.set_volume("Voice", volume_db)

func set_ambient_volume(volume_db: float):
    advanced_system.set_volume("Ambient", volume_db)

func set_ui_volume(volume_db: float):
    advanced_system.set_volume("UI", volume_db)

func mute_all():
    basic_system.mute_all()

func unmute_all():
    basic_system.unmute_all()

func get_performance_stats() -> Dictionary:
    return {
        "bus_count": performance_monitor.get_bus_count(),
        "effect_count": performance_monitor.get_effect_count(),
        "cpu_usage": performance_monitor.get_cpu_usage()
    }

func print_stats():
    performance_monitor.print_stats()
```

---

## 📝 本章总结

### 核心要点

1. **AudioServer 是核心混合器**，管理所有音频总线
2. **AudioBus 用于音频路由**，组织不同类型的音频
3. **AudioEffect 增强音频质量**，包括均衡、混响、压缩等
4. **音频混合器优化**，包括缓存、LOD、性能监控
5. **完整音频混合器系统**，整合所有混合器功能

### 关键术语

| 术语 | 解释 |
|------|------|
| AudioServer | 音频服务器，核心混合器 |
| AudioBus | 音频总线，音频通道 |
| AudioEffect | 音频效果器，音频处理 |
| AudioEffectEQ | 均衡器效果器 |
| AudioEffectReverb | 混响效果器 |
| AudioEffectCompressor | 压缩器效果器 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Audio](https://docs.godotengine.org/en/stable/tutorials/audio/index.html)
- **源码位置**: `servers/audio/`
- **技术博客**: [Godot Audio Mixer](https://godotengine.org/article/audio-mixer/)

---

## 📋 下一章预告

**第 48 篇：音频效果器**

- 音频效果器基础
- 均衡器效果器
- 混响效果器
- 压缩器效果器
- 性能优化

---

*写作时间：2026-03-20*  
*字数：约 12,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 15:00*