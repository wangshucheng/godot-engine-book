# 第 38 篇：音频效果器

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
│  1. AudioEffectEQ：均衡器效果器                            │
│  2. AudioEffectReverb：混响效果器                          │
│  3. AudioEffectCompressor：压缩器效果器                    │
│  4. AudioEffectDelay：延迟效果器                           │
│  5. AudioEffectDistortion：失真效果器                      │
│  6. AudioEffectFilter：滤波器效果器                        │
│  7. AudioEffectChorus：合唱效果器                          │
│  8. AudioEffectFlanger：镶边效果器                         │
│  9. AudioEffectPhaser：移相效果器                          │
│  10. AudioEffectPitchShift：音调变换效果器                 │
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

func create_eq21() -> AudioEffectEQ21:
    # 创建 21 段均衡器
    var eq = AudioEffectEQ21.new()
    
    # 初始化所有频段增益为 0
    for i in range(eq.band_count):
        eq.set_band_gain(i, 0.0)
    
    return eq

func set_band_gain(eq: AudioEffectEQ21, band_idx: int, gain_db: float):
    # 设置频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        eq.set_band_gain(band_idx, gain_db)

func get_band_gain(eq: AudioEffectEQ21, band_idx: int) -> float:
    # 获取频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        return eq.get_band_gain(band_idx)
    return 0.0

func set_eq21_preset(eq: AudioEffectEQ21, preset: String):
    # 设置 EQ21 预设
    match preset:
        "flat":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
        
        "bass_boost":
            for i in range(5):
                set_band_gain(eq, i, 6.0 - i * 1.0)
            for i in range(5, eq.band_count):
                set_band_gain(eq, i, 0.0)
        
        "treble_boost":
            for i in range(eq.band_count - 5):
                set_band_gain(eq, i, 0.0)
            for i in range(eq.band_count - 5, eq.band_count):
                set_band_gain(eq, i, (i - (eq.band_count - 5)) * 1.5)
        
        "vocal":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
            set_band_gain(eq, 8, -2.0)
            set_band_gain(eq, 9, 2.0)
            set_band_gain(eq, 10, 4.0)
            set_band_gain(eq, 11, 4.0)
            set_band_gain(eq, 12, 2.0)
            set_band_gain(eq, 13, -2.0)
        
        "rock":
            set_band_gain(eq, 0, 5.0)
            set_band_gain(eq, 1, 4.0)
            set_band_gain(eq, 2, 3.0)
            set_band_gain(eq, 3, 1.0)
            set_band_gain(eq, 4, -1.0)
            set_band_gain(eq, 5, -2.0)
            set_band_gain(eq, 6, -1.0)
            set_band_gain(eq, 7, 1.0)
            set_band_gain(eq, 8, 3.0)
            set_band_gain(eq, 9, 4.0)
            set_band_gain(eq, 10, 5.0)
        
        "pop":
            set_band_gain(eq, 0, 3.0)
            set_band_gain(eq, 1, 4.0)
            set_band_gain(eq, 2, 5.0)
            set_band_gain(eq, 3, 4.0)
            set_band_gain(eq, 4, 2.0)
            set_band_gain(eq, 5, 0.0)
            set_band_gain(eq, 6, 0.0)
            set_band_gain(eq, 7, 2.0)
            set_band_gain(eq, 8, 4.0)
            set_band_gain(eq, 9, 5.0)
            set_band_gain(eq, 10, 4.0)
        
        "jazz":
            set_band_gain(eq, 0, 4.0)
            set_band_gain(eq, 1, 3.0)
            set_band_gain(eq, 2, 2.0)
            set_band_gain(eq, 3, 1.0)
            set_band_gain(eq, 4, 0.0)
            set_band_gain(eq, 5, 0.0)
            set_band_gain(eq, 6, 1.0)
            set_band_gain(eq, 7, 2.0)
            set_band_gain(eq, 8, 3.0)
            set_band_gain(eq, 9, 4.0)
            set_band_gain(eq, 10, 5.0)
        
        "classical":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
            set_band_gain(eq, 0, 2.0)
            set_band_gain(eq, 1, 2.0)
            set_band_gain(eq, 9, 2.0)
            set_band_gain(eq, 10, 3.0)
        
        "dance":
            set_band_gain(eq, 0, 6.0)
            set_band_gain(eq, 1, 5.0)
            set_band_gain(eq, 2, 4.0)
            set_band_gain(eq, 3, 2.0)
            set_band_gain(eq, 4, 0.0)
            set_band_gain(eq, 5, -2.0)
            set_band_gain(eq, 6, -2.0)
            set_band_gain(eq, 7, 0.0)
            set_band_gain(eq, 8, 2.0)
            set_band_gain(eq, 9, 4.0)
            set_band_gain(eq, 10, 5.0)
```

### 2.2 AudioEffectEQ10

```gdscript
# 10 段均衡器
class_name AudioEffectEQ10Controller

extends Node

func create_eq10() -> AudioEffectEQ10:
    # 创建 10 段均衡器
    var eq = AudioEffectEQ10.new()
    
    # 初始化所有频段增益为 0
    for i in range(eq.band_count):
        eq.set_band_gain(i, 0.0)
    
    return eq

func set_band_gain(eq: AudioEffectEQ10, band_idx: int, gain_db: float):
    # 设置频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        eq.set_band_gain(band_idx, gain_db)

func get_band_gain(eq: AudioEffectEQ10, band_idx: int) -> float:
    # 获取频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        return eq.get_band_gain(band_idx)
    return 0.0

func set_eq10_preset(eq: AudioEffectEQ10, preset: String):
    # 设置 EQ10 预设
    match preset:
        "flat":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
        
        "bass_boost":
            for i in range(3):
                set_band_gain(eq, i, 6.0 - i * 1.5)
            for i in range(3, eq.band_count):
                set_band_gain(eq, i, 0.0)
        
        "treble_boost":
            for i in range(eq.band_count - 3):
                set_band_gain(eq, i, 0.0)
            for i in range(eq.band_count - 3, eq.band_count):
                set_band_gain(eq, i, (i - (eq.band_count - 3)) * 2.0)
        
        "vocal":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
            set_band_gain(eq, 3, -2.0)
            set_band_gain(eq, 4, 3.0)
            set_band_gain(eq, 5, 4.0)
            set_band_gain(eq, 6, 2.0)
        
        "rock":
            set_band_gain(eq, 0, 5.0)
            set_band_gain(eq, 1, 3.0)
            set_band_gain(eq, 2, 0.0)
            set_band_gain(eq, 3, -2.0)
            set_band_gain(eq, 4, -2.0)
            set_band_gain(eq, 5, 0.0)
            set_band_gain(eq, 6, 2.0)
            set_band_gain(eq, 7, 4.0)
            set_band_gain(eq, 8, 5.0)
        
        "pop":
            set_band_gain(eq, 0, 3.0)
            set_band_gain(eq, 1, 4.0)
            set_band_gain(eq, 2, 5.0)
            set_band_gain(eq, 3, 3.0)
            set_band_gain(eq, 4, 0.0)
            set_band_gain(eq, 5, 0.0)
            set_band_gain(eq, 6, 2.0)
            set_band_gain(eq, 7, 4.0)
            set_band_gain(eq, 8, 5.0)
```

### 2.3 AudioEffectEQ6

```gdscript
# 6 段均衡器
class_name AudioEffectEQ6Controller

extends Node

func create_eq6() -> AudioEffectEQ6:
    # 创建 6 段均衡器
    var eq = AudioEffectEQ6.new()
    
    # 初始化所有频段增益为 0
    for i in range(eq.band_count):
        eq.set_band_gain(i, 0.0)
    
    return eq

func set_band_gain(eq: AudioEffectEQ6, band_idx: int, gain_db: float):
    # 设置频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        eq.set_band_gain(band_idx, gain_db)

func get_band_gain(eq: AudioEffectEQ6, band_idx: int) -> float:
    # 获取频段增益
    if band_idx >= 0 and band_idx < eq.band_count:
        return eq.get_band_gain(band_idx)
    return 0.0

func set_eq6_preset(eq: AudioEffectEQ6, preset: String):
    # 设置 EQ6 预设
    match preset:
        "flat":
            for i in range(eq.band_count):
                set_band_gain(eq, i, 0.0)
        
        "bass_boost":
            set_band_gain(eq, 0, 6.0)
            set_band_gain(eq, 1, 4.0)
            set_band_gain(eq, 2, 2.0)
            set_band_gain(eq, 3, 0.0)
            set_band_gain(eq, 4, 0.0)
            set_band_gain(eq, 5, 0.0)
        
        "treble_boost":
            set_band_gain(eq, 0, 0.0)
            set_band_gain(eq, 1, 0.0)
            set_band_gain(eq, 2, 0.0)
            set_band_gain(eq, 3, 2.0)
            set_band_gain(eq, 4, 4.0)
            set_band_gain(eq, 5, 6.0)
        
        "vocal":
            set_band_gain(eq, 0, 0.0)
            set_band_gain(eq, 1, -2.0)
            set_band_gain(eq, 2, 3.0)
            set_band_gain(eq, 3, 4.0)
            set_band_gain(eq, 4, 2.0)
            set_band_gain(eq, 5, 0.0)
        
        "rock":
            set_band_gain(eq, 0, 5.0)
            set_band_gain(eq, 1, 2.0)
            set_band_gain(eq, 2, -2.0)
            set_band_gain(eq, 3, 0.0)
            set_band_gain(eq, 4, 3.0)
            set_band_gain(eq, 5, 5.0)
```

---

## 3. 混响效果器

### 3.1 AudioEffectReverb

```gdscript
# 混响效果器
class_name AudioEffectReverbController

extends Node

func create_reverb() -> AudioEffectReverb:
    # 创建混响效果器
    var reverb = AudioEffectReverb.new()
    
    # 设置默认参数
    reverb.room_size = 0.8
    reverb.dampening = 0.5
    reverb.wet = 0.2
    reverb.dry = 0.8
    reverb.pre_delay = 0.0
    
    return reverb

func set_room_size(reverb: AudioEffectReverb, size: float):
    # 设置房间大小
    reverb.room_size = clamp(size, 0.0, 1.0)

func set_dampening(reverb: AudioEffectReverb, damp: float):
    # 设置阻尼
    reverb.dampening = clamp(damp, 0.0, 1.0)

func set_wet(reverb: AudioEffectReverb, wet: float):
    # 设置湿信号
    reverb.wet = clamp(wet, 0.0, 1.0)

func set_dry(reverb: AudioEffectReverb, dry: float):
    # 设置干信号
    reverb.dry = clamp(dry, 0.0, 1.0)

func set_pre_delay(reverb: AudioEffectReverb, delay: float):
    # 设置预延迟
    reverb preg_delay = clamp(delay, 0.0, 1.0)

func set_reverb_preset(reverb: AudioEffectReverb, preset: String):
    # 设置混响预设
    match preset:
        "small_room":
            reverb.room_size = 0.3
            reverb.dampening = 0.5
            reverb.wet = 0.15
            reverb.dry = 0.85
            reverb.pre_delay = 0.01
        
        "medium_room":
            reverb.room_size = 0.5
            reverb.dampening = 0.5
            reverb.wet = 0.2
            reverb.dry = 0.8
            reverb.pre_delay = 0.02
        
        "large_room":
            reverb.room_size = 0.7
            reverb.dampening = 0.4
            reverb.wet = 0.25
            reverb.dry = 0.75
            reverb.pre_delay = 0.03
        
        "hall":
            reverb.room_size = 0.9
            reverb.dampening = 0.3
            reverb.wet = 0.35
            reverb.dry = 0.65
            reverb.pre_delay = 0.05
        
        "cathedral":
            reverb.room_size = 1.0
            reverb.dampening = 0.2
            reverb.wet = 0.45
            reverb.dry = 0.55
            reverb.pre_delay = 0.08
        
        "plate":
            reverb.room_size = 0.6
            reverb.dampening = 0.6
            reverb.wet = 0.3
            reverb.dry = 0.7
            reverb.pre_delay = 0.0
        
        "spring":
            reverb.room_size = 0.4
            reverb.dampening = 0.7
            reverb.wet = 0.25
            reverb.dry = 0.75
            reverb.pre_delay = 0.01
        
        "arena":
            reverb.room_size = 0.85
            reverb.dampening = 0.35
            reverb.wet = 0.4
            reverb.dry = 0.6
            reverb.pre_delay = 0.06
        
        "auditorium":
            reverb.room_size = 0.75
            reverb.dampening = 0.45
            reverb.wet = 0.3
            reverb.dry = 0.7
            reverb.pre_delay = 0.04
        
        "cave":
            reverb.room_size = 0.95
            reverb.dampening = 0.15
            reverb.wet = 0.5
            reverb.dry = 0.5
            reverb.pre_delay = 0.1
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
class_name AudioEffectCompressorController

extends Node

func create_compressor() -> AudioEffectCompressor:
    # 创建压缩器效果器
    var compressor = AudioEffectCompressor.new()
    
    # 设置默认参数
    compressor.ratio = 4.0
    compressor.threshold_db = -6.0
    compressor.attack_us = 100.0
    compressor.release_ms = 200.0
    compressor.makeup_db = 0.0
    compressor.sidechain = ""
    
    return compressor

func set_ratio(compressor: AudioEffectCompressor, ratio: float):
    # 设置压缩比
    compressor.ratio = clamp(ratio, 1.0, 20.0)

func set_threshold(compressor: AudioEffectCompressor, threshold_db: float):
    # 设置阈值
    compressor.threshold_db = clamp(threshold_db, -60.0, 0.0)

func set_attack(compressor: AudioEffectCompressor, attack_us: float):
    # 设置攻击时间
    compressor.attack_us = clamp(attack_us, 0.0, 1000.0)

func set_release(compressor: AudioEffectCompressor, release_ms: float):
    # 设置释放时间
    compressor.release_ms = clamp(release_ms, 0.0, 5000.0)

func set_makeup(compressor: AudioEffectCompressor, makeup_db: float):
    # 设置补偿增益
    compressor.makeup_db = clamp(makeup_db, 0.0, 24.0)

func set_sidechain(compressor: AudioEffectCompressor, sidechain_bus: String):
    # 设置侧链
    compressor.sidechain = sidechain_bus

func set_compressor_preset(compressor: AudioEffectCompressor, preset: String):
    # 设置压缩器预设
    match preset:
        "light":
            compressor.ratio = 2.0
            compressor.threshold_db = -12.0
            compressor.attack_us = 50.0
            compressor.release_ms = 100.0
            compressor.makeup_db = 0.0
        
        "medium":
            compressor.ratio = 4.0
            compressor.threshold_db = -6.0
            compressor.attack_us = 100.0
            compressor.release_ms = 200.0
            compressor.makeup_db = 2.0
        
        "heavy":
            compressor.ratio = 8.0
            compressor.threshold_db = -3.0
            compressor.attack_us = 20.0
            compressor.release_ms = 300.0
            compressor.makeup_db = 4.0
        
        "vocal":
            compressor.ratio = 3.0
            compressor.threshold_db = -9.0
            compressor.attack_us = 30.0
            compressor.release_ms = 150.0
            compressor.makeup_db = 3.0
        
        "bass":
            compressor.ratio = 5.0
            compressor.threshold_db = -5.0
            compressor.attack_us = 80.0
            compressor.release_ms = 250.0
            compressor.makeup_db = 2.0
        
        "drums":
            compressor.ratio = 6.0
            compressor.threshold_db = -4.0
            compressor.attack_us = 10.0
            compressor.release_ms = 100.0
            compressor.makeup_db = 3.0
        
        "mastering":
            compressor.ratio = 1.5
            compressor.threshold_db = -15.0
            compressor.attack_us = 100.0
            compressor.release_ms = 300.0
            compressor.makeup_db = 1.0
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
            effect.threshold_db = clamp(threshold_db, -60.0, 0.0)
```

---

## 5. 其他效果器

### 5.1 AudioEffectDelay

```gdscript
# 延迟效果器
class_name AudioEffectDelayController

extends Node

func create_delay() -> AudioEffectDelay:
    # 创建延迟效果器
    var delay = AudioEffectDelay.new()
    
    # 设置默认参数
    delay.delay_ms = 250.0
    delay.feedback = 0.3
    delay.wet = 0.3
    delay.dry = 0.7
    
    return delay

func set_delay_ms(delay: AudioEffectDelay, ms: float):
    # 设置延迟时间
    delay.delay_ms = clamp(ms, 0.0, 5000.0)

func set_feedback(delay: AudioEffectDelay, feedback: float):
    # 设置反馈
    delay.feedback = clamp(feedback, 0.0, 1.0)

func set_wet(delay: AudioEffectDelay, wet: float):
    # 设置湿信号
    delay.wet = clamp(wet, 0.0, 1.0)

func set_dry(delay: AudioEffectDelay, dry: float):
    # 设置干信号
    delay.dry = clamp(dry, 0.0, 1.0)

func set_delay_preset(delay: AudioEffectDelay, preset: String):
    # 设置延迟预设
    match preset:
        "slap":
            delay.delay_ms = 100.0
            delay.feedback = 0.1
            delay.wet = 0.2
        "echo":
            delay.delay_ms = 400.0
            delay.feedback = 0.4
            delay.wet = 0.3
        "repeat":
            delay.delay_ms = 600.0
            delay.feedback = 0.6
            delay.wet = 0.4
        "ambient":
            delay.delay_ms = 800.0
            delay.feedback = 0.8
            delay.wet = 0.5
```

### 5.2 AudioEffectDistortion

```gdscript
# 失真效果器
class_name AudioEffectDistortionController

extends Node

func create_distortion() -> AudioEffectDistortion:
    # 创建失真效果器
    var distortion = AudioEffectDistortion.new()
    
    # 设置默认参数
    distortion.drive = 0.5
    distortion.mix = 0.5
    distortion.level = 0.0
    
    return distortion

func set_drive(distortion: AudioEffectDistortion, drive: float):
    # 设置驱动
    distortion.drive = clamp(drive, 0.0, 1.0)

func set_mix(distortion: AudioEffectDistortion, mix: float):
    # 设置混合
    distortion.mix = clamp(mix, 0.0, 1.0)

func set_level(distortion: AudioEffectDistortion, level: float):
    # 设置电平
    distortion.level = clamp(level, -24.0, 24.0)

func set_distortion_preset(distortion: AudioEffectDistortion, preset: String):
    # 设置失真预设
    match preset:
        "overdrive":
            distortion.drive = 0.4
            distortion.mix = 0.5
            distortion.level = 2.0
        "distortion":
            distortion.drive = 0.7
            distortion.mix = 0.7
            distortion.level = 0.0
        "fuzz":
            distortion.drive = 0.9
            distortion.mix = 0.9
            distortion.level = -2.0
        "bitcrush":
            distortion.drive = 0.5
            distortion.mix = 0.6
            distortion.level = 0.0
```

### 5.3 AudioEffectFilter

```gdscript
# 滤波器效果器
class_name AudioEffectFilterController

extends Node

func create_filter() -> AudioEffectFilter:
    # 创建滤波器效果器
    var filter = AudioEffectFilter.new()
    
    # 设置默认参数
    filter.cutoff_hz = 1000.0
    filter.resonance_db = 0.0
    filter.filter_type = AudioEffectFilter.FILTER_LOW_PASS
    
    return filter

func set_cutoff(filter: AudioEffectFilter, hz: float):
    # 设置截止频率
    filter.cutoff_hz = clamp(hz, 20.0, 20000.0)

func set_resonance(filter: AudioEffectFilter, db: float):
    # 设置共振
    filter.resonance_db = clamp(db, 0.0, 40.0)

func set_filter_type(filter: AudioEffectFilter, filter_type: int):
    # 设置滤波器类型
    filter.filter_type = filter_type

func set_filter_preset(filter: AudioEffectFilter, preset: String):
    # 设置滤波器预设
    match preset:
        "low_pass":
            filter.filter_type = AudioEffectFilter.FILTER_LOW_PASS
            filter.cutoff_hz = 1000.0
            filter.resonance_db = 0.0
        "high_pass":
            filter.filter_type = AudioEffectFilter.FILTER_HIGH_PASS
            filter.cutoff_hz = 500.0
            filter.resonance_db = 0.0
        "band_pass":
            filter.filter_type = AudioEffectFilter.FILTER_BAND_PASS
            filter.cutoff_hz = 1000.0
            filter.resonance_db = 5.0
        "notch":
            filter.filter_type = AudioEffectFilter.FILTER_NOTCH
            filter.cutoff_hz = 1000.0
            filter.resonance_db = 10.0
        "low_shelf":
            filter.filter_type = AudioEffectFilter.FILTER_LOWSHELF
            filter.cutoff_hz = 200.0
            filter.resonance_db = 0.0
        "high_shelf":
            filter.filter_type = AudioEffectFilter.FILTER_HIGHSHELF
            filter.cutoff_hz = 5000.0
            filter.resonance_db = 0.0
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

func get_optimal_effect_order() -> Array:
    # 获取最佳效果器顺序
    # 一般顺序：EQ -> Compressor -> Filter -> Distortion -> Delay -> Reverb
    return [0, 1, 2, 3, 4, 5]
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
    timer.connect("timeout", self, "_update_stats")
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
        "reverb_small_room": {"type": "reverb", "preset": "small_room"},
        "reverb_hall": {"type": "reverb", "preset": "hall"},
        "compressor_vocal": {"type": "compressor", "preset": "vocal"},
        "compressor_bass": {"type": "compressor", "preset": "bass"},
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
    var controller = AudioEffectReverbController.new()
    controller.set_reverb_preset(reverb, preset)
    return reverb

func create_compressor_with_preset(preset: String) -> AudioEffectCompressor:
    var compressor = AudioEffectCompressor.new()
    var controller = AudioEffectCompressorController.new()
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
    var filter = AudioEffectFilter.new()
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
    var controller = AudioEffectReverbController.new()
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
    var controller = AudioEffectCompressorController.new()
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
            return effect is AudioEffectFilter
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

- **官方文档**: [Godot Audio Effects](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **源码位置**: `servers/audio/effects/`
- **技术博客**: [Godot Audio Effects Guide](https://godotengine.org/article/audio-effects-guide/)

---

## 📋 下一章预告

**第 49 篇：网络系统**

- 网络系统基础
- 网络通信协议
- 网络同步
- 网络优化

---

*写作时间：2026-03-20*  
*字数：约 13,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 16:00*