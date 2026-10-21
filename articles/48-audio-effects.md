# 第 48 篇：音频效果器

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 47 章 音频混合器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

音频效果器是游戏音频系统中用于处理和增强音频信号的重要工具。通过音频效果器，开发者可以为音频添加混响、均衡、压缩、延迟等各种效果，极大地提升游戏的音频质量和沉浸感。

Godot 提供了丰富的音频效果器，包括 EQ、Reverb、Compressor、Delay、Distortion、Filter 等。本章将深入探讨这些效果器的实现和优化。

---

## 🎯 学习目标

- 理解音频效果器的基本概念
- 掌握均衡器效果器
- 学会混响效果器应用
- 熟悉压缩器效果器
- 掌握其他常用效果器
- 掌握音频效果器优化

---

## 1. 音频效果器基础

### 1.1 音频效果器类型

```
音频效果器类型:
┌─────────────────────────────────────────────────────────────┐
│                      音频效果器类型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioEffectEQ / EQ6 / EQ10 / EQ21：均衡器效果器         │
│  2. AudioEffectReverb：混响效果器                           │
│  3. AudioEffectCompressor：压缩器效果器                     │
│  4. AudioEffectLimiter / HardLimiter：限幅器                │
│  5. AudioEffectDelay：延迟效果器（双 tap + feedback）       │
│  6. AudioEffectDistortion：失真效果器                       │
│  7. AudioEffectFilter 及其子类：滤波器效果器                │
│  8. AudioEffectChorus / Phaser / PitchShift：调制类效果器   │
│  9. AudioEffectAmplify / Panner / StereoEnhance：增益与声像 │
│ 10. AudioEffectCapture / Record / Spectrum：采集与分析      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 音频效果器组件

```
音频效果器组件:
┌─────────────────────────────────────────────────────────────┐
│                      音频效果器组件                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioEffect：效果器基类                                 │
│  2. AudioEffectInstance：效果器实例                         │
│  3. AudioEffectEQ21：21 段均衡器                            │
│  4. AudioEffectEQ10：10 段均衡器                            │
│  5. AudioEffectEQ6：6 段均衡器                              │
│  6. AudioEffectReverb：混响效果器                          │
│  7. AudioEffectCompressor：压缩器效果器                    │
│  8. AudioEffectDelay：延迟效果器                           │
│  9. AudioEffectDistortion：失真效果器                      │
│  10. AudioEffectFilter：滤波器效果器                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 音频效果器流程

```
音频效果器处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      音频效果器处理流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 音频信号输入到效果器                                   │
│  2. 效果器处理音频信号（滤波、延迟、混响等）               │
│  3. 效果器输出处理后的音频信号                             │
│  4. 多个效果器串联处理                                     │
│  5. 最终输出到音频总线                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 均衡器效果器

### 2.1 AudioEffectEQ21

```gdscript
# 21 段均衡器
class_name AudioEffectEQ21Controller

extends Node

# ⚠️ AudioEffectEQ 没有 band_count 属性，也没有 set_band_gain() / get_band_gain()：
#    真实方法只有 get_band_count() / set_band_gain_db(int, float) / get_band_gain_db(int)。
#    另外每个频点还以动态属性 "band_db/<频率>_hz" 暴露（如 band_db/50_hz）。

func create_eq21() -> AudioEffectEQ21:
    # 创建 21 段均衡器
    var eq = AudioEffectEQ21.new()
    
    # 初始化所有频段增益为 0 dB
    for i in range(eq.get_band_count()):
        eq.set_band_gain_db(i, 0.0)
    
    return eq

func apply_band_gain(eq: AudioEffectEQ, band_idx: int, gain_db: float) -> void:
    # 设置频段增益（引擎方法名是 set_band_gain_db，单位 dB）
    if band_idx >= 0 and band_idx < eq.get_band_count():
        eq.set_band_gain_db(band_idx, gain_db)

func read_band_gain(eq: AudioEffectEQ, band_idx: int) -> float:
    # 读取频段增益（引擎方法名是 get_band_gain_db）
    if band_idx >= 0 and band_idx < eq.get_band_count():
        return eq.get_band_gain_db(band_idx)
    return 0.0

func set_eq21_preset(eq: AudioEffectEQ21, preset: String):
    # 设置 EQ21 预设
    match preset:
        "flat":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
        
        "bass_boost":
            for i in range(5):
                apply_band_gain(eq, i, 6.0 - i * 1.0)
            for i in range(5, eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
        
        "treble_boost":
            for i in range(eq.get_band_count() - 5):
                apply_band_gain(eq, i, 0.0)
            for i in range(eq.get_band_count() - 5, eq.get_band_count()):
                apply_band_gain(eq, i, (i - (eq.get_band_count() - 5)) * 1.5)
        
        "vocal":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
            apply_band_gain(eq, 8, -2.0)
            apply_band_gain(eq, 9, 2.0)
            apply_band_gain(eq, 10, 4.0)
            apply_band_gain(eq, 11, 4.0)
            apply_band_gain(eq, 12, 2.0)
            apply_band_gain(eq, 13, -2.0)
        
        "rock":
            apply_band_gain(eq, 0, 5.0)
            apply_band_gain(eq, 1, 4.0)
            apply_band_gain(eq, 2, 3.0)
            apply_band_gain(eq, 3, 1.0)
            apply_band_gain(eq, 4, -1.0)
            apply_band_gain(eq, 5, -2.0)
            apply_band_gain(eq, 6, -1.0)
            apply_band_gain(eq, 7, 1.0)
            apply_band_gain(eq, 8, 3.0)
            apply_band_gain(eq, 9, 4.0)
            apply_band_gain(eq, 10, 5.0)
        
        "pop":
            apply_band_gain(eq, 0, 3.0)
            apply_band_gain(eq, 1, 4.0)
            apply_band_gain(eq, 2, 5.0)
            apply_band_gain(eq, 3, 4.0)
            apply_band_gain(eq, 4, 2.0)
            apply_band_gain(eq, 5, 0.0)
            apply_band_gain(eq, 6, 0.0)
            apply_band_gain(eq, 7, 2.0)
            apply_band_gain(eq, 8, 4.0)
            apply_band_gain(eq, 9, 5.0)
            apply_band_gain(eq, 10, 4.0)
        
        "jazz":
            apply_band_gain(eq, 0, 4.0)
            apply_band_gain(eq, 1, 3.0)
            apply_band_gain(eq, 2, 2.0)
            apply_band_gain(eq, 3, 1.0)
            apply_band_gain(eq, 4, 0.0)
            apply_band_gain(eq, 5, 0.0)
            apply_band_gain(eq, 6, 1.0)
            apply_band_gain(eq, 7, 2.0)
            apply_band_gain(eq, 8, 3.0)
            apply_band_gain(eq, 9, 4.0)
            apply_band_gain(eq, 10, 5.0)
        
        "classical":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
            apply_band_gain(eq, 0, 2.0)
            apply_band_gain(eq, 1, 2.0)
            apply_band_gain(eq, 9, 2.0)
            apply_band_gain(eq, 10, 3.0)
        
        "dance":
            apply_band_gain(eq, 0, 6.0)
            apply_band_gain(eq, 1, 5.0)
            apply_band_gain(eq, 2, 4.0)
            apply_band_gain(eq, 3, 2.0)
            apply_band_gain(eq, 4, 0.0)
            apply_band_gain(eq, 5, -2.0)
            apply_band_gain(eq, 6, -2.0)
            apply_band_gain(eq, 7, 0.0)
            apply_band_gain(eq, 8, 2.0)
            apply_band_gain(eq, 9, 4.0)
            apply_band_gain(eq, 10, 5.0)
```

### 2.2 AudioEffectEQ10

```gdscript
# 10 段均衡器
class_name AudioEffectEQ10Controller

extends Node

func create_eq10() -> AudioEffectEQ10:
    # 创建 10 段均衡器
    var eq = AudioEffectEQ10.new()
    
    # 初始化所有频段增益为 0 dB
    for i in range(eq.get_band_count()):
        eq.set_band_gain_db(i, 0.0)
    
    return eq

func apply_band_gain(eq: AudioEffectEQ, band_idx: int, gain_db: float) -> void:
    # 设置频段增益
    if band_idx >= 0 and band_idx < eq.get_band_count():
        eq.set_band_gain_db(band_idx, gain_db)

func read_band_gain(eq: AudioEffectEQ, band_idx: int) -> float:
    # 读取频段增益
    if band_idx >= 0 and band_idx < eq.get_band_count():
        return eq.get_band_gain_db(band_idx)
    return 0.0

func set_eq10_preset(eq: AudioEffectEQ10, preset: String):
    # 设置 EQ10 预设
    match preset:
        "flat":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
        
        "bass_boost":
            for i in range(3):
                apply_band_gain(eq, i, 6.0 - i * 1.5)
            for i in range(3, eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
        
        "treble_boost":
            for i in range(eq.get_band_count() - 3):
                apply_band_gain(eq, i, 0.0)
            for i in range(eq.get_band_count() - 3, eq.get_band_count()):
                apply_band_gain(eq, i, (i - (eq.get_band_count() - 3)) * 2.0)
        
        "vocal":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
            apply_band_gain(eq, 3, -2.0)
            apply_band_gain(eq, 4, 3.0)
            apply_band_gain(eq, 5, 4.0)
            apply_band_gain(eq, 6, 2.0)
        
        "rock":
            apply_band_gain(eq, 0, 5.0)
            apply_band_gain(eq, 1, 3.0)
            apply_band_gain(eq, 2, 0.0)
            apply_band_gain(eq, 3, -2.0)
            apply_band_gain(eq, 4, -2.0)
            apply_band_gain(eq, 5, 0.0)
            apply_band_gain(eq, 6, 2.0)
            apply_band_gain(eq, 7, 4.0)
            apply_band_gain(eq, 8, 5.0)
        
        "pop":
            apply_band_gain(eq, 0, 3.0)
            apply_band_gain(eq, 1, 4.0)
            apply_band_gain(eq, 2, 5.0)
            apply_band_gain(eq, 3, 3.0)
            apply_band_gain(eq, 4, 0.0)
            apply_band_gain(eq, 5, 0.0)
            apply_band_gain(eq, 6, 2.0)
            apply_band_gain(eq, 7, 4.0)
            apply_band_gain(eq, 8, 5.0)
```

### 2.3 AudioEffectEQ6

```gdscript
# 6 段均衡器
class_name AudioEffectEQ6Controller

extends Node

func create_eq6() -> AudioEffectEQ6:
    # 创建 6 段均衡器
    var eq = AudioEffectEQ6.new()
    
    # 初始化所有频段增益为 0 dB
    for i in range(eq.get_band_count()):
        eq.set_band_gain_db(i, 0.0)
    
    return eq

func apply_band_gain(eq: AudioEffectEQ, band_idx: int, gain_db: float) -> void:
    # 设置频段增益
    if band_idx >= 0 and band_idx < eq.get_band_count():
        eq.set_band_gain_db(band_idx, gain_db)

func read_band_gain(eq: AudioEffectEQ, band_idx: int) -> float:
    # 读取频段增益
    if band_idx >= 0 and band_idx < eq.get_band_count():
        return eq.get_band_gain_db(band_idx)
    return 0.0

func set_eq6_preset(eq: AudioEffectEQ6, preset: String):
    # 设置 EQ6 预设
    match preset:
        "flat":
            for i in range(eq.get_band_count()):
                apply_band_gain(eq, i, 0.0)
        
        "bass_boost":
            apply_band_gain(eq, 0, 6.0)
            apply_band_gain(eq, 1, 4.0)
            apply_band_gain(eq, 2, 2.0)
            apply_band_gain(eq, 3, 0.0)
            apply_band_gain(eq, 4, 0.0)
            apply_band_gain(eq, 5, 0.0)
        
        "treble_boost":
            apply_band_gain(eq, 0, 0.0)
            apply_band_gain(eq, 1, 0.0)
            apply_band_gain(eq, 2, 0.0)
            apply_band_gain(eq, 3, 2.0)
            apply_band_gain(eq, 4, 4.0)
            apply_band_gain(eq, 5, 6.0)
        
        "vocal":
            apply_band_gain(eq, 0, 0.0)
            apply_band_gain(eq, 1, -2.0)
            apply_band_gain(eq, 2, 3.0)
            apply_band_gain(eq, 3, 4.0)
            apply_band_gain(eq, 4, 2.0)
            apply_band_gain(eq, 5, 0.0)
        
        "rock":
            apply_band_gain(eq, 0, 5.0)
            apply_band_gain(eq, 1, 2.0)
            apply_band_gain(eq, 2, -2.0)
            apply_band_gain(eq, 3, 0.0)
            apply_band_gain(eq, 4, 3.0)
            apply_band_gain(eq, 5, 5.0)
```

---

## 3. 混响效果器

### 3.1 AudioEffectReverb

```gdscript
# 混响效果器
class_name ReverbEffectController

extends Node

# ⚠️ 参数名以 AudioEffectReverb 的官方成员为准：
#    room_size（0~1） / damping（0~1） / wet（0~1） / dry（0~1）
#    predelay_msec（毫秒） / spread（0~1） / hipass（0~1） / predelay_feedback（0~1）
#    没有 dampening，也没有 pre_delay。

func create_reverb() -> AudioEffectReverb:
    # 创建混响效果器
    var reverb = AudioEffectReverb.new()
    
    # 设置默认参数
    reverb.room_size = 0.8
    reverb.damping = 0.5
    reverb.wet = 0.2
    reverb.dry = 0.8
    reverb.predelay_msec = 20.0
    reverb.spread = 1.0
    reverb.hipass = 0.0
    reverb.predelay_feedback = 0.4
    
    return reverb

func set_room_size(reverb: AudioEffectReverb, size: float) -> void:
    # 设置房间大小（0~1）
    reverb.room_size = clamp(size, 0.0, 1.0)

func set_damping(reverb: AudioEffectReverb, damping: float) -> void:
    # 设置阻尼（0~1）—— 引擎属性名是 damping
    reverb.damping = clamp(damping, 0.0, 1.0)

func set_wet(reverb: AudioEffectReverb, wet: float) -> void:
    # 设置湿信号（0~1）
    reverb.wet = clamp(wet, 0.0, 1.0)

func set_dry(reverb: AudioEffectReverb, dry: float) -> void:
    # 设置干信号（0~1）
    reverb.dry = clamp(dry, 0.0, 1.0)

func set_predelay(reverb: AudioEffectReverb, msec: float) -> void:
    # 设置预延迟（毫秒）—— 引擎属性名是 predelay_msec，单位是毫秒不是比例
    reverb.predelay_msec = clamp(msec, 0.0, 500.0)

func set_reverb_preset(reverb: AudioEffectReverb, preset: String) -> void:
    # 设置混响预设
    match preset:
        "small_room":
            reverb.room_size = 0.3
            reverb.damping = 0.5
            reverb.wet = 0.15
            reverb.dry = 0.85
            reverb.predelay_msec = 10.0
        
        "medium_room":
            reverb.room_size = 0.5
            reverb.damping = 0.5
            reverb.wet = 0.2
            reverb.dry = 0.8
            reverb.predelay_msec = 20.0
        
        "large_room":
            reverb.room_size = 0.7
            reverb.damping = 0.4
            reverb.wet = 0.25
            reverb.dry = 0.75
            reverb.predelay_msec = 30.0
        
        "hall":
            reverb.room_size = 0.9
            reverb.damping = 0.3
            reverb.wet = 0.35
            reverb.dry = 0.65
            reverb.predelay_msec = 50.0
        
        "cathedral":
            reverb.room_size = 1.0
            reverb.damping = 0.2
            reverb.wet = 0.45
            reverb.dry = 0.55
            reverb.predelay_msec = 80.0
        
        "plate":
            reverb.room_size = 0.6
            reverb.damping = 0.6
            reverb.wet = 0.3
            reverb.dry = 0.7
            reverb.predelay_msec = 0.0
        
        "spring":
            reverb.room_size = 0.4
            reverb.damping = 0.7
            reverb.wet = 0.25
            reverb.dry = 0.75
            reverb.predelay_msec = 10.0
        
        "arena":
            reverb.room_size = 0.85
            reverb.damping = 0.35
            reverb.wet = 0.4
            reverb.dry = 0.6
            reverb.predelay_msec = 60.0
        
        "auditorium":
            reverb.room_size = 0.75
            reverb.damping = 0.45
            reverb.wet = 0.3
            reverb.dry = 0.7
            reverb.predelay_msec = 40.0
        
        "cave":
            reverb.room_size = 0.95
            reverb.damping = 0.15
            reverb.wet = 0.5
            reverb.dry = 0.5
            reverb.predelay_msec = 100.0
```

### 3.2 混响效果器应用

```gdscript
# 混响效果器应用
class_name ReverbApplication

extends Node

func apply_reverb_to_bus(bus_name: String, preset: String = "medium_room"):
    # 应用混响到总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var reverb = create_reverb_with_preset(preset)
    AudioServer.add_bus_effect(bus_idx, reverb)

func create_reverb_with_preset(preset: String) -> AudioEffectReverb:
    # 创建带预设的混响
    var reverb = create_reverb()
    set_reverb_preset(reverb, preset)
    return reverb

func remove_reverb_from_bus(bus_name: String):
    # 从总线移除混响
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count - 1, -1, -1):
        var effect = AudioServer.get_bus_effect(bus_idx, i)
        if effect is AudioEffectReverb:
            AudioServer.remove_bus_effect(bus_idx, i)

func adjust_reverb_wet(bus_name: String, wet_amount: float):
    # 调整混响湿信号
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count):
        var effect = AudioServer.get_bus_effect(bus_idx, i)
        if effect is AudioEffectReverb:
            effect.wet = clamp(wet_amount, 0.0, 1.0)
```

---

## 4. 压缩器效果器

### 4.1 AudioEffectCompressor

```gdscript
# 压缩器效果器
class_name CompressorEffectController

extends Node

# ⚠️ AudioEffectCompressor 的成员是：
#    threshold（不是 threshold_db） / gain（不是 makeup_db）
#    ratio / attack_us / release_ms / mix / sidechain
#    取值范围：threshold -60~0 dB，ratio 1~48，
#    attack_us 20~2000 μs，release_ms 20~2000 ms。

func create_compressor() -> AudioEffectCompressor:
    # 创建压缩器效果器
    var compressor = AudioEffectCompressor.new()
    
    # 设置默认参数
    compressor.ratio = 4.0
    compressor.threshold = -6.0
    compressor.attack_us = 100.0
    compressor.release_ms = 200.0
    compressor.gain = 0.0
    compressor.mix = 1.0
    compressor.sidechain = ""
    
    return compressor

func set_ratio(compressor: AudioEffectCompressor, ratio: float) -> void:
    # 设置压缩比（1~48）
    compressor.ratio = clamp(ratio, 1.0, 48.0)

func set_threshold(compressor: AudioEffectCompressor, threshold_db: float) -> void:
    # 设置阈值（-60~0 dB）—— 引擎属性名是 threshold
    compressor.threshold = clamp(threshold_db, -60.0, 0.0)

func set_attack(compressor: AudioEffectCompressor, attack_us: float) -> void:
    # 设置攻击时间（20~2000 μs）
    compressor.attack_us = clamp(attack_us, 20.0, 2000.0)

func set_release(compressor: AudioEffectCompressor, release_ms: float) -> void:
    # 设置释放时间（20~2000 ms）
    compressor.release_ms = clamp(release_ms, 20.0, 2000.0)

func set_gain(compressor: AudioEffectCompressor, gain_db: float) -> void:
    # 设置补偿增益（dB）—— 引擎属性名是 gain，没有 makeup_db
    compressor.gain = clamp(gain_db, -24.0, 24.0)

func set_sidechain(compressor: AudioEffectCompressor, sidechain_bus: String) -> void:
    # 设置侧链：用另一条总线的信号做阈值检测（做 ducking）
    compressor.sidechain = sidechain_bus

func set_compressor_preset(compressor: AudioEffectCompressor, preset: String) -> void:
    # 设置压缩器预设
    match preset:
        "light":
            compressor.ratio = 2.0
            compressor.threshold = -12.0
            compressor.attack_us = 50.0
            compressor.release_ms = 100.0
            compressor.gain = 0.0
        
        "medium":
            compressor.ratio = 4.0
            compressor.threshold = -6.0
            compressor.attack_us = 100.0
            compressor.release_ms = 200.0
            compressor.gain = 2.0
        
        "heavy":
            compressor.ratio = 8.0
            compressor.threshold = -3.0
            compressor.attack_us = 20.0
            compressor.release_ms = 300.0
            compressor.gain = 4.0
        
        "vocal":
            compressor.ratio = 3.0
            compressor.threshold = -9.0
            compressor.attack_us = 30.0
            compressor.release_ms = 150.0
            compressor.gain = 3.0
        
        "bass":
            compressor.ratio = 5.0
            compressor.threshold = -5.0
            compressor.attack_us = 80.0
            compressor.release_ms = 250.0
            compressor.gain = 2.0
        
        "drums":
            compressor.ratio = 6.0
            compressor.threshold = -4.0
            compressor.attack_us = 10.0
            compressor.release_ms = 100.0
            compressor.gain = 3.0
        
        "mastering":
            compressor.ratio = 1.5
            compressor.threshold = -15.0
            compressor.attack_us = 100.0
            compressor.release_ms = 300.0
            compressor.gain = 1.0
```

### 4.2 压缩器效果器应用

```gdscript
# 压缩器效果器应用
class_name CompressorApplication

extends Node

func apply_compressor_to_bus(bus_name: String, preset: String = "medium"):
    # 应用压缩器到总线
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var compressor = create_compressor_with_preset(preset)
    AudioServer.add_bus_effect(bus_idx, compressor)

func create_compressor_with_preset(preset: String) -> AudioEffectCompressor:
    # 创建带预设的压缩器
    var compressor = create_compressor()
    set_compressor_preset(compressor, preset)
    return compressor

func remove_compressor_from_bus(bus_name: String):
    # 从总线移除压缩器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count - 1, -1, -1):
        var effect = AudioServer.get_bus_effect(bus_idx, i)
        if effect is AudioEffectCompressor:
            AudioServer.remove_bus_effect(bus_idx, i)

func adjust_compressor_threshold(bus_name: String, threshold_db: float):
    # 调整压缩器阈值
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count):
        var effect = AudioServer.get_bus_effect(bus_idx, i)
        if effect is AudioEffectCompressor:
            # 引擎属性名是 threshold，没有 threshold_db
            effect.threshold = clamp(threshold_db, -60.0, 0.0)
```

---

## 5. 其他效果器

### 5.1 AudioEffectDelay

```gdscript
# 延迟效果器
class_name AudioEffectDelayController

extends Node

# ⚠️ AudioEffectDelay 没有 delay_ms / feedback / wet 这三个属性。
#    4.x 的模型是「两个 tap + 一路 feedback」：
#      tap1_active / tap1_delay_ms / tap1_level_db / tap1_pan
#      tap2_active / tap2_delay_ms / tap2_level_db / tap2_pan
#      feedback_active / feedback_delay_ms / feedback_level_db / feedback_lowpass
#      dry（0~1）
#    想得到"反复回响"，必须把 feedback_active 设为 true，
#    否则只有固定时间的一次回声。

func create_delay() -> AudioEffectDelay:
    # 创建延迟效果器
    var delay = AudioEffectDelay.new()
    
    # 设置默认参数
    delay.tap1_active = true
    delay.tap1_delay_ms = 250.0
    delay.tap1_level_db = -6.0
    delay.tap1_pan = 0.2
    
    delay.tap2_active = false
    delay.tap2_delay_ms = 500.0
    delay.tap2_level_db = -12.0
    delay.tap2_pan = -0.4
    
    # 回授默认关闭
    delay.feedback_active = false
    delay.feedback_delay_ms = 340.0
    delay.feedback_level_db = -6.0
    delay.feedback_lowpass = 16000.0
    
    delay.dry = 1.0
    return delay

func set_tap1_delay(delay: AudioEffectDelay, ms: float) -> void:
    # 设置第一个 tap 的延迟时间（毫秒）
    delay.tap1_delay_ms = clamp(ms, 0.0, 5000.0)

func set_tap2_delay(delay: AudioEffectDelay, ms: float) -> void:
    # 设置第二个 tap 的延迟时间（毫秒）
    delay.tap2_delay_ms = clamp(ms, 0.0, 5000.0)

func set_feedback(delay: AudioEffectDelay, enabled: bool, level_db: float = -6.0) -> void:
    # 打开回授才会产生"反复回响"
    delay.feedback_active = enabled
    delay.feedback_level_db = clamp(level_db, -60.0, 0.0)

func set_dry(delay: AudioEffectDelay, dry: float) -> void:
    # 设置干信号（0~1）
    delay.dry = clamp(dry, 0.0, 1.0)

func set_delay_preset(delay: AudioEffectDelay, preset: String) -> void:
    # 设置延迟预设
    match preset:
        "slap":
            delay.tap1_active = true
            delay.tap1_delay_ms = 100.0
            delay.tap1_level_db = -6.0
            delay.tap2_active = false
            delay.feedback_active = false
        "echo":
            delay.tap1_active = true
            delay.tap1_delay_ms = 400.0
            delay.tap1_level_db = -6.0
            delay.tap2_active = false
            delay.feedback_active = true
            delay.feedback_delay_ms = 400.0
            delay.feedback_level_db = -12.0
        "repeat":
            delay.tap1_active = true
            delay.tap1_delay_ms = 600.0
            delay.tap1_level_db = -6.0
            delay.tap2_active = false
            delay.feedback_active = true
            delay.feedback_delay_ms = 600.0
            delay.feedback_level_db = -9.0
        "ambient":
            delay.tap1_active = true
            delay.tap1_delay_ms = 800.0
            delay.tap1_level_db = -9.0
            delay.tap2_active = true
            delay.tap2_delay_ms = 1200.0
            delay.tap2_level_db = -12.0
            delay.feedback_active = true
            delay.feedback_delay_ms = 800.0
            delay.feedback_level_db = -18.0
```

### 5.2 AudioEffectDistortion

```gdscript
# 失真效果器
class_name AudioEffectDistortionController

extends Node

# ⚠️ AudioEffectDistortion 没有 mix / level 属性。
#    真实成员是：mode（枚举）/ drive（0~1）/ pre_gain（dB）/ post_gain（dB）
#                / keep_hf_hz（高通截止频率，Hz）
#    模式：MODE_CLIP / MODE_ATAN / MODE_LOFI / MODE_OVERDRIVE / MODE_WAVESHAPE
#    注意：MODE_OVERDRIVE 下 drive 不起作用（官方文档明确说明）。

func create_distortion() -> AudioEffectDistortion:
    # 创建失真效果器
    var distortion = AudioEffectDistortion.new()
    
    # 设置默认参数
    distortion.mode = AudioEffectDistortion.MODE_OVERDRIVE
    distortion.drive = 0.5
    distortion.pre_gain = 0.0    # 效果前增益（dB，-60~60）
    distortion.post_gain = 0.0   # 效果后增益（dB，-80~24）
    distortion.keep_hf_hz = 16000.0
    
    return distortion

func set_mode(distortion: AudioEffectDistortion, mode: int) -> void:
    # 切换失真模式
    distortion.mode = mode

func set_drive(distortion: AudioEffectDistortion, drive: float) -> void:
    # 设置驱动量（0~1）
    distortion.drive = clamp(drive, 0.0, 1.0)

func set_post_gain(distortion: AudioEffectDistortion, gain_db: float) -> void:
    # 设置效果后增益（dB）—— 没有 mix / level，用 pre_gain / post_gain 控制
    distortion.post_gain = clamp(gain_db, -80.0, 24.0)

func set_distortion_preset(distortion: AudioEffectDistortion, preset: String) -> void:
    # 设置失真预设
    match preset:
        "overdrive":
            distortion.mode = AudioEffectDistortion.MODE_OVERDRIVE
            distortion.pre_gain = 0.0
            distortion.post_gain = 2.0
        "clip":
            distortion.mode = AudioEffectDistortion.MODE_CLIP
            distortion.drive = 0.7
            distortion.pre_gain = 0.0
            distortion.post_gain = 0.0
        "lofi":
            distortion.mode = AudioEffectDistortion.MODE_LOFI
            distortion.drive = 0.5
            distortion.post_gain = 0.0
        "fuzz":
            distortion.mode = AudioEffectDistortion.MODE_ATAN
            distortion.drive = 0.9
            distortion.post_gain = -2.0
        "waveshape":
            distortion.mode = AudioEffectDistortion.MODE_WAVESHAPE
            distortion.drive = 0.7
            distortion.post_gain = 0.0
```

### 5.3 AudioEffectFilter

```gdscript
# 滤波器效果器
class_name AudioEffectFilterController

extends Node

# ⚠️ AudioEffectFilter 是**基类**：
#    没有 filter_type 属性，也没有 FILTER_LOW_PASS / FILTER_HIGH_PASS 这类常量，
#    更没有 resonance_db（真实成员是 resonance，0~1）。
#    4.x 用一组子类表达滤波器类型：
#      AudioEffectLowPassFilter / HighPassFilter / BandPassFilter
#      AudioEffectNotchFilter / BandLimitFilter
#      AudioEffectLowShelfFilter / HighShelfFilter
#    （shelf 滤波器是有的，就是上面这两个子类。）
#    共同成员：cutoff_hz（Hz）/ db（斜率）/ gain / resonance

func create_low_pass() -> AudioEffectLowPassFilter:
    # 低通：切掉高频
    var filter := AudioEffectLowPassFilter.new()
    filter.cutoff_hz = 1000.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.resonance = 0.5
    return filter

func create_high_pass() -> AudioEffectHighPassFilter:
    # 高通：切掉低频
    var filter := AudioEffectHighPassFilter.new()
    filter.cutoff_hz = 500.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.resonance = 0.5
    return filter

func create_band_pass() -> AudioEffectBandPassFilter:
    # 带通：只保留一小段
    var filter := AudioEffectBandPassFilter.new()
    filter.cutoff_hz = 1000.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.resonance = 0.9
    return filter

func create_notch() -> AudioEffectNotchFilter:
    # 陷波：挖掉一小段
    var filter := AudioEffectNotchFilter.new()
    filter.cutoff_hz = 1000.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.resonance = 1.0
    return filter

func create_band_limit() -> AudioEffectBandLimitFilter:
    # 带限：只保留一段，其余全切掉
    var filter := AudioEffectBandLimitFilter.new()
    filter.cutoff_hz = 1000.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.resonance = 0.5
    return filter

func create_low_shelf() -> AudioEffectLowShelfFilter:
    # 低架：提升/衰减低频（4.x 有 shelf 滤波）
    var filter := AudioEffectLowShelfFilter.new()
    filter.cutoff_hz = 200.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.gain = 1.5
    return filter

func create_high_shelf() -> AudioEffectHighShelfFilter:
    # 高架：提升/衰减高频
    var filter := AudioEffectHighShelfFilter.new()
    filter.cutoff_hz = 5000.0
    filter.db = AudioEffectFilter.FILTER_12DB
    filter.gain = 1.5
    return filter

func set_cutoff(filter: AudioEffectFilter, hz: float) -> void:
    # 设置截止频率
    filter.cutoff_hz = clamp(hz, 1.0, 21000.0)

func set_resonance(filter: AudioEffectFilter, amount: float) -> void:
    # 设置共振（0~1）—— 属性名是 resonance，没有 resonance_db
    filter.resonance = clamp(amount, 0.0, 1.0)

func set_filter_db(filter: AudioEffectFilter, db_mode: int) -> void:
    # 设置滤波斜率：FILTER_6DB / FILTER_12DB / FILTER_18DB / FILTER_24DB
    filter.db = db_mode

func set_filter_preset(filter: AudioEffectFilter, preset: String) -> void:
    # 设置滤波器预设
    # ⚠️ 滤波器的"类型"在创建时由子类定死了，这里只能调参数、不能换类型
    match preset:
        "low_pass":
            filter.cutoff_hz = 1000.0
            filter.resonance = 0.5
        "high_pass":
            filter.cutoff_hz = 500.0
            filter.resonance = 0.5
        "band_pass":
            filter.cutoff_hz = 1000.0
            filter.resonance = 0.9
        "notch":
            filter.cutoff_hz = 1000.0
            filter.resonance = 1.0
        "band_limit":
            filter.cutoff_hz = 1000.0
            filter.resonance = 0.5
        "low_shelf":
            filter.cutoff_hz = 200.0
            filter.gain = 1.5
        "high_shelf":
            filter.cutoff_hz = 5000.0
            filter.gain = 1.5
```

### 5.4 增益、限幅与声像类效果器

```gdscript
# 增益 / 限幅 / 声像 / 立体声扩展
class_name AudioEffectUtilityController

extends Node

func create_amplify(db: float = 3.0) -> AudioEffectAmplify:
    # 整体增益：只有一个 volume_db
    var effect := AudioEffectAmplify.new()
    effect.volume_db = db
    return effect

func create_limiter(ceiling_db: float = -0.1) -> AudioEffectLimiter:
    # 软限幅：比 HardLimiter 柔和，带软削波
    var effect := AudioEffectLimiter.new()
    effect.ceiling_db = ceiling_db
    effect.threshold_db = 0.0
    effect.soft_clip_db = 2.0
    effect.soft_clip_ratio = 10.0
    return effect

func create_hard_limiter(ceiling_db: float = -0.3) -> AudioEffectHardLimiter:
    # 硬限幅：Master 总线上做最终保护时常用
    var effect := AudioEffectHardLimiter.new()
    effect.ceiling_db = ceiling_db
    effect.pre_gain_db = 0.0
    effect.release = 0.1
    return effect

func create_panner(pan: float = 0.0) -> AudioEffectPanner:
    # 声像：-1 全左，1 全右
    var effect := AudioEffectPanner.new()
    effect.pan = clamp(pan, -1.0, 1.0)
    return effect

func create_stereo_enhance() -> AudioEffectStereoEnhance:
    # 立体声扩展：把单声道撑开
    var effect := AudioEffectStereoEnhance.new()
    effect.pan_pullout = 1.0
    effect.time_pullout_ms = 0.0
    effect.surround = 0.0
    return effect
```

### 5.5 调制类效果器（Chorus / Phaser / PitchShift）

```gdscript
# 调制类效果器
class_name AudioEffectModulationController

extends Node

func create_chorus() -> AudioEffectChorus:
    # 合唱：voice_count 个声部，每个声部有独立的延迟 / 深度 / 声像
    var effect := AudioEffectChorus.new()
    effect.voice_count = 2
    effect.wet = 0.5
    effect.dry = 1.0
    # 声部 1 / 2 的参数也能用动态属性读写：
    #   voice/1/delay_ms、voice/1/depth_ms、voice/1/cutoff_hz、
    #   voice/1/level_db、voice/1/pan、voice/1/rate_hz
    effect.set_voice_delay_ms(0, 15.0)
    effect.set_voice_depth_ms(0, 2.0)
    effect.set_voice_pan(0, -0.5)
    effect.set_voice_rate_hz(0, 0.8)
    effect.set_voice_delay_ms(1, 20.0)
    effect.set_voice_depth_ms(1, 3.0)
    effect.set_voice_pan(1, 0.5)
    effect.set_voice_rate_hz(1, 1.2)
    return effect

func create_phaser() -> AudioEffectPhaser:
    # 移相
    var effect := AudioEffectPhaser.new()
    effect.rate_hz = 0.5
    effect.feedback = 0.7
    effect.depth = 1.0
    effect.range_min_hz = 440.0
    effect.range_max_hz = 1600.0
    return effect

func create_pitch_shift(scale: float = 1.0) -> AudioEffectPitchShift:
    # 变调（保持时长）
    var effect := AudioEffectPitchShift.new()
    effect.pitch_scale = scale
    effect.fft_size = AudioEffectPitchShift.FFT_SIZE_2048
    effect.oversampling = 4
    return effect
```

---

## 6. 音频效果器优化

### 6.1 效果器链优化

```gdscript
# 效果器链优化
class_name EffectChainOptimizer

extends Node

func optimize_effect_chain(bus_name: String):
    # 优化效果器链
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    
    # 移除禁用的效果器
    for i in range(count - 1, -1, -1):
        if not AudioServer.is_bus_effect_enabled(bus_idx, i):
            AudioServer.remove_bus_effect(bus_idx, i)
            print("Removed disabled effect from: ", bus_name)

func reorder_effects(bus_name: String, new_order: Array):
    # 重新排序效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    # 保存效果器
    var effects = []
    for i in range(AudioServer.get_bus_effect_count(bus_idx)):
        effects.append(AudioServer.get_bus_effect(bus_idx, i))
    
    # 清除所有效果器
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count - 1, -1, -1):
        AudioServer.remove_bus_effect(bus_idx, i)
    
    # 按新顺序添加效果器
    for idx in new_order:
        if idx >= 0 and idx < effects.size():
            AudioServer.add_bus_effect(bus_idx, effects[idx])
    # ⚠️ 引擎不会给"最佳顺序"，这里也删掉了原来那个返回 [0,1,2,3,4,5] 的
    #    占位函数——它对任何总线都是同一个常量，没有意义。
    #    通用顺序建议见 47 篇 §4.3。
```

### 6.2 效果器性能监控

```gdscript
# 效果器性能监控
class_name EffectPerformanceMonitor

extends Node

var effect_count = 0
var enabled_effect_count = 0

func _ready():
    # 开始性能监控
    start_monitoring()

func start_monitoring():
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.timeout.connect(_update_stats)
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计
    effect_count = 0
    enabled_effect_count = 0
    
    for i in range(AudioServer.bus_count):
        var count = AudioServer.get_bus_effect_count(i)
        effect_count += count
        
        for j in range(count):
            if AudioServer.is_bus_effect_enabled(i, j):
                enabled_effect_count += 1

func get_total_effect_count() -> int:
    return effect_count

func get_enabled_effect_count() -> int:
    return enabled_effect_count

func print_stats():
    print("Effect Stats:")
    print("- Total Effects: ", get_total_effect_count())
    print("- Enabled Effects: ", get_enabled_effect_count())
```

### 6.3 效果器预设管理

```gdscript
# 效果器预设管理
class_name EffectPresetManager

extends Node

var presets = {}

func _ready():
    # 加载预设
    load_presets()

func load_presets():
    # 加载预设库
    presets = {
        "eq_rock": {"type": "eq", "preset": "rock"},
        "eq_pop": {"type": "eq", "preset": "pop"},
        "eq_jazz": {"type": "eq", "preset": "jazz"},
        "eq_vocal": {"type": "eq", "preset": "vocal"},
        "reverb_small_room": {"type": "reverb", "preset": "small_room"},
        "reverb_hall": {"type": "reverb", "preset": "hall"},
        "compressor_vocal": {"type": "compressor", "preset": "vocal"},
        "compressor_bass": {"type": "compressor", "preset": "bass"},
        "compressor_drums": {"type": "compressor", "preset": "drums"},
        "compressor_mastering": {"type": "compressor", "preset": "mastering"},
        "delay_echo": {"type": "delay", "preset": "echo"},
        "distortion_overdrive": {"type": "distortion", "preset": "overdrive"},
        "filter_low_pass": {"type": "filter", "preset": "low_pass"}
    }

func apply_preset(bus_name: String, preset_name: String):
    # 应用预设到总线
    if not presets.has(preset_name):
        return
    
    var preset = presets[preset_name]
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var effect: AudioEffect
    match preset.type:
        "eq":
            effect = create_eq_with_preset(preset.preset)
        "reverb":
            effect = create_reverb_with_preset(preset.preset)
        "compressor":
            effect = create_compressor_with_preset(preset.preset)
        "delay":
            effect = create_delay_with_preset(preset.preset)
        "distortion":
            effect = create_distortion_with_preset(preset.preset)
        "filter":
            effect = create_filter_with_preset(preset.preset)
    
    if effect:
        AudioServer.add_bus_effect(bus_idx, effect)

func create_eq_with_preset(preset: String) -> AudioEffectEQ21:
    var eq = AudioEffectEQ21.new()
    var controller = AudioEffectEQ21Controller.new()
    controller.set_eq21_preset(eq, preset)
    return eq

func create_reverb_with_preset(preset: String) -> AudioEffectReverb:
    var reverb = AudioEffectReverb.new()
    var controller = ReverbEffectController.new()
    controller.set_reverb_preset(reverb, preset)
    return reverb

func create_compressor_with_preset(preset: String) -> AudioEffectCompressor:
    var compressor = AudioEffectCompressor.new()
    var controller = CompressorEffectController.new()
    controller.set_compressor_preset(compressor, preset)
    return compressor

func create_delay_with_preset(preset: String) -> AudioEffectDelay:
    var delay = AudioEffectDelay.new()
    var controller = AudioEffectDelayController.new()
    controller.set_delay_preset(delay, preset)
    return delay

func create_distortion_with_preset(preset: String) -> AudioEffectDistortion:
    var distortion = AudioEffectDistortion.new()
    var controller = AudioEffectDistortionController.new()
    controller.set_distortion_preset(distortion, preset)
    return distortion

func create_filter_with_preset(preset: String) -> AudioEffectFilter:
    # ⚠️ 滤波器的"类型"由子类决定，preset 名字决定用哪个子类；
    #    AudioEffectFilter 基类实例默认就是低通。
    var filter: AudioEffectFilter
    match preset:
        "high_pass":
            filter = AudioEffectHighPassFilter.new()
        "band_pass":
            filter = AudioEffectBandPassFilter.new()
        "notch":
            filter = AudioEffectNotchFilter.new()
        "band_limit":
            filter = AudioEffectBandLimitFilter.new()
        "low_shelf":
            filter = AudioEffectLowShelfFilter.new()
        "high_shelf":
            filter = AudioEffectHighShelfFilter.new()
        _:
            filter = AudioEffectFilter.new()
    var controller = AudioEffectFilterController.new()
    controller.set_filter_preset(filter, preset)
    return filter
```

---

## 7. 实践：完整音频效果器系统

### 7.1 基础音频效果器系统

```gdscript
# 基础音频效果器系统
class_name BasicAudioEffectSystem

extends Node

func _ready():
    # 初始化基础音频效果器系统
    initialize_basic_effects()

func initialize_basic_effects():
    # 为 Master 总线添加混响
    apply_reverb_to_bus("Master", "medium_room")
    
    # 为 Music 总线添加均衡器
    apply_eq_to_bus("Music", "flat")
    
    # 为 SFX 总线添加压缩器
    apply_compressor_to_bus("SFX", "medium")

func apply_reverb_to_bus(bus_name: String, preset: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var reverb = AudioEffectReverb.new()
    var controller = ReverbEffectController.new()
    controller.set_reverb_preset(reverb, preset)
    AudioServer.add_bus_effect(bus_idx, reverb)

func apply_eq_to_bus(bus_name: String, preset: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var eq = AudioEffectEQ21.new()
    var controller = AudioEffectEQ21Controller.new()
    controller.set_eq21_preset(eq, preset)
    AudioServer.add_bus_effect(bus_idx, eq)

func apply_compressor_to_bus(bus_name: String, preset: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var compressor = AudioEffectCompressor.new()
    var controller = CompressorEffectController.new()
    controller.set_compressor_preset(compressor, preset)
    AudioServer.add_bus_effect(bus_idx, compressor)
```

### 7.2 高级音频效果器系统

```gdscript
# 高级音频效果器系统
class_name AdvancedAudioEffectSystem

extends Node

var preset_manager: EffectPresetManager
var performance_monitor: EffectPerformanceMonitor

func _ready():
    # 初始化高级音频效果器系统
    initialize_advanced_effects()

func initialize_advanced_effects():
    preset_manager = EffectPresetManager.new()
    add_child(preset_manager)
    
    performance_monitor = EffectPerformanceMonitor.new()
    add_child(performance_monitor)
    
    # 为所有总线添加效果器
    setup_all_bus_effects()

func setup_all_bus_effects():
    # Master: 混响 + 压缩器
    preset_manager.apply_preset("Master", "reverb_hall")
    preset_manager.apply_preset("Master", "compressor_mastering")
    
    # Music: EQ + 压缩器
    preset_manager.apply_preset("Music", "eq_pop")
    preset_manager.apply_preset("Music", "compressor_vocal")
    
    # SFX: 压缩器
    preset_manager.apply_preset("SFX", "compressor_drums")
    
    # Voice: EQ + 压缩器
    preset_manager.apply_preset("Voice", "eq_vocal")
    preset_manager.apply_preset("Voice", "compressor_vocal")
    
    # Ambient: 混响
    preset_manager.apply_preset("Ambient", "reverb_small_room")

func apply_effect(bus_name: String, effect_type: String, preset: String):
    # 应用效果器
    preset_manager.apply_preset(bus_name, effect_type + "_" + preset)

func remove_effect(bus_name: String, effect_type: String):
    # 移除效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count - 1, -1, -1):
        var effect = AudioServer.get_bus_effect(bus_idx, i)
        if is_effect_type(effect, effect_type):
            AudioServer.remove_bus_effect(bus_idx, i)

func is_effect_type(effect: AudioEffect, effect_type: String) -> bool:
    # 检查效果器类型
    match effect_type:
        "eq":
            return effect is AudioEffectEQ
        "reverb":
            return effect is AudioEffectReverb
        "compressor":
            return effect is AudioEffectCompressor
        "delay":
            return effect is AudioEffectDelay
        "distortion":
            return effect is AudioEffectDistortion
        "filter":
            # AudioEffectFilter 是基类，is 会同时匹配所有滤波器子类
            return effect is AudioEffectFilter
        "amplify":
            return effect is AudioEffectAmplify
        "limiter":
            return effect is AudioEffectLimiter
        "hard_limiter":
            return effect is AudioEffectHardLimiter
        "chorus":
            return effect is AudioEffectChorus
        "phaser":
            return effect is AudioEffectPhaser
        "pitch_shift":
            return effect is AudioEffectPitchShift
        "panner":
            return effect is AudioEffectPanner
        "stereo_enhance":
            return effect is AudioEffectStereoEnhance
        "capture":
            return effect is AudioEffectCapture
        "record":
            return effect is AudioEffectRecord
        "spectrum_analyzer":
            return effect is AudioEffectSpectrumAnalyzer
    return false

func get_effect_stats() -> Dictionary:
    # 获取效果器统计
    return {
        "total_effects": performance_monitor.get_total_effect_count(),
        "enabled_effects": performance_monitor.get_enabled_effect_count()
    }
```

### 7.3 完整音频效果器系统

```gdscript
# 完整音频效果器系统
class_name FullAudioEffectSystem

extends Node

var basic_system: BasicAudioEffectSystem
var advanced_system: AdvancedAudioEffectSystem

func _ready():
    # 初始化完整音频效果器系统
    initialize_full_effect_system()

func initialize_full_effect_system():
    basic_system = BasicAudioEffectSystem.new()
    add_child(basic_system)
    
    advanced_system = AdvancedAudioEffectSystem.new()
    add_child(advanced_system)

func apply_reverb(bus_name: String, preset: String):
    # 应用混响
    advanced_system.apply_effect(bus_name, "reverb", preset)

func apply_eq(bus_name: String, preset: String):
    # 应用均衡器
    advanced_system.apply_effect(bus_name, "eq", preset)

func apply_compressor(bus_name: String, preset: String):
    # 应用压缩器
    advanced_system.apply_effect(bus_name, "compressor", preset)

func apply_delay(bus_name: String, preset: String):
    # 应用延迟
    advanced_system.apply_effect(bus_name, "delay", preset)

func apply_distortion(bus_name: String, preset: String):
    # 应用失真
    advanced_system.apply_effect(bus_name, "distortion", preset)

func apply_filter(bus_name: String, preset: String):
    # 应用滤波器
    advanced_system.apply_effect(bus_name, "filter", preset)

func remove_all_effects(bus_name: String):
    # 移除所有效果器
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    var count = AudioServer.get_bus_effect_count(bus_idx)
    for i in range(count - 1, -1, -1):
        AudioServer.remove_bus_effect(bus_idx, i)

func get_effect_stats() -> Dictionary:
    # 获取效果器统计
    return advanced_system.get_effect_stats()

func print_stats():
    # 打印统计
    advanced_system.performance_monitor.print_stats()
```

---

## 📝 本章总结

### 核心要点

1. **均衡器用于调整频率响应**，21 段、10 段、6 段可选
2. **混响用于模拟空间感**，多种预设可选
3. **压缩器用于控制动态范围**，保护听力并提升音质
4. **其他效果器**，包括延迟、失真、滤波器等
5. **效果器优化**，包括链优化、性能监控、预设管理

### 关键术语

| 术语 | 解释 |
|------|------|
| AudioEffectEQ | 均衡器效果器 |
| AudioEffectReverb | 混响效果器 |
| AudioEffectCompressor | 压缩器效果器 |
| AudioEffectDelay | 延迟效果器 |
| AudioEffectDistortion | 失真效果器 |
| AudioEffectFilter | 滤波器效果器 |

---

## 🔗 延伸阅读

- **官方文档**: [Audio buses（含效果器与总线用法）](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **类参考**: [AudioEffect](https://docs.godotengine.org/en/stable/classes/class_audioeffect.html)
- **类参考**: [AudioEffectReverb](https://docs.godotengine.org/en/stable/classes/class_audioeffectreverb.html)
- **源码位置**: `servers/audio/effects/`

---

## 📋 下一章预告

**第 49 篇：网络系统**

- 网络系统基础
- 网络通信协议
- 网络同步
- 网络优化

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 47 篇：音频混合器](/articles/47-audio-mixer.md)
**下一篇**: [第 59 篇：3D 音频和动态音频系统](/articles/59-3d-audio-and-dynamic-audio.md)

---

*写作时间：2026-03-20*  
*字数：约 600 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 16:00*
