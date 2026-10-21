# 第 47 篇：音频混合器

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
│  3. AudioEffect：音频效果器（效果混合器）                   │
│  4. AudioBusLayout：音频总线布局（配置混合器）              │
│  5. AudioStreamPlayback：音频播放混合器                     │
│  6. AudioDriver：音频驱动（底层混合器）                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 音频混合器组件

```
音频混合器组件:
┌─────────────────────────────────────────────────────────────┐
│                      音频混合器组件                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AudioServer：音频服务器                                 │
│  2. AudioBus：音频总线                                      │
│  3. AudioEffect：音频效果器（完整清单见 §4.1）              │
│  4. AudioEffectInstance：效果器运行时实例                   │
│  5. AudioBusLayout：总线布局资源                            │
│  6. AudioEffectSpectrumAnalyzer：频谱分析效果器             │
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
    
    # 获取混音率：⚠️ mix_rate 不是属性，方法是 get_mix_rate()，返回 float
    print("Mix rate: ", audio_server.get_mix_rate())
    
    # 获取输出延迟：⚠️ 引擎没有 input_latency（那是 3.x 的属性），
    # 只有 get_output_latency()
    print("Output latency: ", audio_server.get_output_latency())

func get_bus_count() -> int:
    return AudioServer.bus_count

func get_mix_rate() -> float:
    # ⚠️ 返回值是 float（Hz），不是 int
    return AudioServer.get_mix_rate()

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
    # add_bus() 不带参数 = 追加到末尾；add_bus(pos) 会在 pos 处插入
    audio_server.add_bus()
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

func set_bus_send(bus_name: String, send_bus_name: String) -> bool:
    # 设置总线发送（支路）
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    # ⚠️ 官方签名是 set_bus_send(int bus_idx, StringName send)：
    #    第二参数是**目标总线名**，不是索引。
    #    官方描述："Connects the output of the bus at bus_idx to the bus named send."
    if bus_idx != -1 and audio_server.get_bus_index(send_bus_name) != -1:
        audio_server.set_bus_send(bus_idx, send_bus_name)
        return true
    return false

func get_bus_send(bus_name: String) -> String:
    # 获取总线发送
    var audio_server = AudioServer
    var bus_idx = audio_server.get_bus_index(bus_name)
    if bus_idx != -1:
        # ⚠️ get_bus_send() 返回的是**目标总线名**（StringName），不是索引
        var send_bus_name := audio_server.get_bus_send(bus_idx)
        if send_bus_name != &"":
            return String(send_bus_name)
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
# AudioServer 混音时序监控
class_name AudioServerPerformanceMonitor

extends Node

# 采样"距上次混音的相对时间"（秒）
var mix_interval_history = []
var max_history_size = 60

func _ready():
    # 开始监控
    start_monitoring()

func start_monitoring():
    # 连接定时器
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.timeout.connect(_update_stats)
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计
    var audio_server = AudioServer
    # ⚠️ get_time_since_last_mix() 的官方描述是"距上次混音的相对时间"（秒），
    #    **不是 CPU 使用率**。Godot 4 也没有暴露混音线程的 CPU 占用百分比
    #    （AudioServer 没有 performance_get()，Performance 里没有 time_usage/*）。
    #    所以这里把它当作"混音节奏"来观察：间隔异常变大往往意味着卡顿。
    var interval := audio_server.get_time_since_last_mix()
    
    mix_interval_history.append(interval)
    if mix_interval_history.size() > max_history_size:
        mix_interval_history.remove_at(0)

func get_average_mix_interval() -> float:
    # 平均混音间隔（秒）
    if mix_interval_history.is_empty():
        return 0.0
    
    var total = 0.0
    for interval in mix_interval_history:
        total += interval
    
    return total / mix_interval_history.size()

func get_peak_mix_interval() -> float:
    # 最大混音间隔（秒）
    var peak = 0.0
    for interval in mix_interval_history:
        if interval > peak:
            peak = interval
    
    return peak

func get_current_mix_interval() -> float:
    # 当前混音间隔（秒）
    if mix_interval_history.is_empty():
        return 0.0
    
    return mix_interval_history[-1]

func print_stats():
    # 打印统计信息
    print("Audio Server Stats:")
    print("- Current Mix Interval: ", get_current_mix_interval())
    print("- Average Mix Interval: ", get_average_mix_interval())
    print("- Peak Mix Interval: ", get_peak_mix_interval())
```

---

## 3. AudioBus

### 3.1 AudioBus 基础

```gdscript
# AudioBus 基础
class_name AudioBusMixController

extends Node

func _ready():
    # 初始化音频总线
    initialize_audio_buses()

func initialize_audio_buses():
    var audio_server = AudioServer
    
    # ⚠️ 不要用 `audio_server.bus_count = 3`。
    # bus_count 的 setter（set_bus_count）会**重建总线列表**：
    #   - 数量变小时，超出部分的总线被直接销毁（连同名称与效果器）；
    #   - 数量变大时，新建总线的名字是占位名 "New Bus" / "New Bus 2"。
    # 总线布局的正确做法见 §5.4（编辑器 → Audio 面板 → default_bus_layout.tres）。
    
    # 运行时只做增量调整：add_bus() 追加，add_bus(pos) 在 pos 处插入
    for bus_name in ["Music", "SFX"]:
        if audio_server.get_bus_index(bus_name) == -1:
            audio_server.add_bus()
            var idx := audio_server.bus_count - 1
            audio_server.set_bus_name(idx, bus_name)
    
    # 设置初始音量
    audio_server.set_bus_volume_db(audio_server.get_bus_index("Master"), 0.0)
    audio_server.set_bus_volume_db(audio_server.get_bus_index("Music"), -5.0)
    audio_server.set_bus_volume_db(audio_server.get_bus_index("SFX"), -3.0)

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

func add_effect_to_bus(bus_name: String, effect: AudioEffect, at_position: int = -1) -> int:
    # 把效果器挂到总线上。
    # at_position 指定插入位置（-1 = 追加到末尾）——**顺序就是执行顺序**。
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return -1
    AudioServer.add_bus_effect(bus_idx, effect, at_position)
    return AudioServer.get_bus_effect_count(bus_idx) - 1

func remove_effect_from_bus(bus_name: String, effect_idx: int):
    # 从总线移除效果器
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.remove_bus_effect(bus_idx, effect_idx)
        print("Removed effect from bus: ", bus_name)

func swap_effects(bus_name: String, effect_idx: int, by_effect_idx: int) -> bool:
    # 换位：把第 effect_idx 个效果器和第 by_effect_idx 个对调
    # ⚠️ 引擎只有 swap_bus_effects()（换位），**没有 move_bus_effect()**
    #    （后者在 4.x 已不存在，且只能换位、不能任意插入）。
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return false
    var count := AudioServer.get_bus_effect_count(bus_idx)
    if effect_idx < 0 or by_effect_idx < 0 or effect_idx >= count or by_effect_idx >= count:
        return false
    AudioServer.swap_bus_effects(bus_idx, effect_idx, by_effect_idx)
    return true

func move_effect(bus_name: String, effect_idx: int, to_position: int) -> bool:
    # 真正的"移动"要自己实现：取出 → remove → add_bus_effect(bus, eff, at_position)
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return false
    var count := AudioServer.get_bus_effect_count(bus_idx)
    if effect_idx < 0 or effect_idx >= count:
        return false
    var effect := AudioServer.get_bus_effect(bus_idx, effect_idx)
    AudioServer.remove_bus_effect(bus_idx, effect_idx)
    var target := clampi(to_position, 0, AudioServer.get_bus_effect_count(bus_idx))
    AudioServer.add_bus_effect(bus_idx, effect, target)
    return true

func get_bus_effect_count(bus_name: String) -> int:
    # 获取总线效果器数量
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        return AudioServer.get_bus_effect_count(bus_idx)
    return 0

func get_bus_effect(bus_name: String, effect_idx: int) -> AudioEffect:
    # 获取总线效果器
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        return AudioServer.get_bus_effect(bus_idx, effect_idx)
    return null

func clear_bus_effects(bus_name: String):
    # 清除总线所有效果器
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        var count = AudioServer.get_bus_effect_count(bus_idx)
        for i in range(count - 1, -1, -1):
            AudioServer.remove_bus_effect(bus_idx, i)
        print("Cleared effects from bus: ", bus_name)
```

### 3.3 AudioBus 支路（send）模型

```gdscript
# AudioBus 支路（send）模型
class_name AudioBusRouting

extends Node

# set_bus_send(int bus_idx, StringName send) 的官方描述是：
#   "Connects the output of the bus at bus_idx to the bus named send."
# 即：本总线的输出会**汇入**另一条总线（不是"改道"，也不是"复制一份"）。
# 一条总线只有一个 send 目标，总线的拓扑完全由各总线的 send 字段决定。
#
#   ┌──────────┐ send=Reverb ┌──────────┐ send=Master ┌────────┐
#   │  Music   │─────────────▶│  Reverb  │────────────▶│ Master │
#   └──────────┘              └──────────┘             └────────┘
#
# ⚠️ 两条硬约束（来自引擎源码 AudioServer::_mix_step）：
#   1. send 目标的索引必须**小于**本总线，否则引擎会回退到 Master
#      （源码注释："invalid, send to master"）。所以上例中 Reverb 必须排在
#      Music **前面**（索引更小），否则 send 会被忽略。
#   2. 因此"Music 同时进 Master 和 Reverb"在 4.x 里做不到：
#      一条总线只有一个去向。想要湿声混响，要么把 AudioEffectReverb 直接挂在
#      Music 总线上，要么把 Music 整条改道到 Reverb 总线。

func set_bus_send(bus_name: String, send_bus_name: String) -> bool:
    # 把本总线的输出汇入另一条总线
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return false
    if AudioServer.get_bus_index(send_bus_name) == -1:
        return false
    # ⚠️ 第二参数是 StringName（总线名），传索引是错的
    AudioServer.set_bus_send(bus_idx, send_bus_name)
    return true

func get_bus_send(bus_name: String) -> String:
    # 获取本总线汇入的目标总线名
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return ""
    # ⚠️ get_bus_send() 返回的是**目标总线名**（StringName），不是索引
    var send_bus_name := AudioServer.get_bus_send(bus_idx)
    return String(send_bus_name) if send_bus_name != &"" else ""

func clear_bus_send(bus_name: String) -> void:
    # 断开支路：传空名即可
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx != -1:
        AudioServer.set_bus_send(bus_idx, &"")

func create_bus_chain(bus_names: Array) -> void:
    # 创建总线链：A → B → C（每个 send 指向下一个）
    for i in range(bus_names.size() - 1):
        set_bus_send(bus_names[i], bus_names[i + 1])

func create_reverb_send(source_bus: String, reverb_bus: String) -> bool:
    # 典型用法：把一条总线整条改道到混响总线
    # ⚠️ reverb_bus 的索引必须小于 source_bus 的索引，否则会被引擎忽略
    return set_bus_send(source_bus, reverb_bus)
```

---

## 4. 音频效果器与效果器链

### 4.1 Godot 4.3 内置效果器清单

Godot 4.3 的 `servers/audio/effects/` 目录里一共 17 组效果器：

| 效果器类 | 作用 | 关键成员 |
|----------|------|----------|
| `AudioEffectAmplify` | 整体增益 | `volume_db` |
| `AudioEffectEQ` / `AudioEffectEQ6` / `AudioEffectEQ10` / `AudioEffectEQ21` | 均衡 | `get_band_count()` / `set_band_gain_db()` / `get_band_gain_db()` |
| `AudioEffectReverb` | 混响 | `room_size` / `damping` / `wet` / `dry` / `predelay_msec` / `spread` / `hipass` / `predelay_feedback` |
| `AudioEffectCompressor` | 压缩 | `threshold` / `ratio` / `attack_us` / `release_ms` / `gain` / `mix` / `sidechain` |
| `AudioEffectLimiter` | 软限幅 | `ceiling_db` / `threshold_db` / `soft_clip_db` / `soft_clip_ratio` |
| `AudioEffectHardLimiter` | 硬限幅 | `ceiling_db` / `pre_gain_db` / `release` |
| `AudioEffectDelay` | 延迟 | `tap1_*` / `tap2_*` / `feedback_*` / `dry` |
| `AudioEffectDistortion` | 失真 | `mode` / `drive` / `pre_gain` / `post_gain` / `keep_hf_hz` |
| `AudioEffectFilter` | 滤波**基类** | `cutoff_hz` / `db` / `gain` / `resonance` |
| `AudioEffectLowPassFilter` / `AudioEffectHighPassFilter` / `AudioEffectBandPassFilter` / `AudioEffectNotchFilter` / `AudioEffectBandLimitFilter` / `AudioEffectLowShelfFilter` / `AudioEffectHighShelfFilter` | 各种滤波器（`AudioEffectFilter` 的子类） | 同基类 |
| `AudioEffectChorus` | 合唱 | `voice_count` / `voice/N/*` / `wet` / `dry` |
| `AudioEffectPhaser` | 移相 | `rate_hz` / `feedback` / `depth` / `range_min_hz` / `range_max_hz` |
| `AudioEffectPitchShift` | 变调 | `pitch_scale` / `fft_size` / `oversampling` |
| `AudioEffectPanner` | 声像 | `pan` |
| `AudioEffectStereoEnhance` | 立体声扩展 | `pan_pullout` / `time_pullout_ms` / `surround` |
| `AudioEffectCapture` | 采集原始 PCM | `buffer_length` / `get_buffer()` / `get_frames_available()` |
| `AudioEffectRecord` | 录制为 `AudioStreamWAV` | `format` / `set_recording_active()` / `get_recording()` |
| `AudioEffectSpectrumAnalyzer` | 频谱分析 | `fft_size` / `buffer_length` / `tap_back_pos` |

> **没有** `AudioEffectFlanger`（镶边）——4.x 的 `servers/audio/effects/` 里没有这个文件。
> 想要镶边只能用 `AudioEffectChorus` 近似，或者自己写 GDExtension。
>
> 每个效果器的**参数含义与预设**集中在第 48 篇《音频效果器》讲；本章只讲
> "效果器怎么挂到总线上、按什么顺序执行"。

### 4.2 效果器的执行顺序

一条总线上的效果器是**串行**执行的：总线先把这个总线上所有播放器的输出混在一起，
按 `add_bus_effect()` 的插入顺序依次跑完效果器链，然后把**结果**汇入它的 send 目标。
（引擎源码 `AudioServer::_mix_step()`：先跑 `bus->effects` 循环，再做 `//process send`。）

```
总线上的信号流向:

  播放器（Music / SFX / Voice ... 的输出）
        │
        ▼
  ┌────────────────────────────────┐
  │ 1. Filter（高通 / 低通）        │  ← 先切掉不该有的频段
  ├────────────────────────────────┤
  │ 2. EQ（均衡）                   │  ← 修正音色
  ├────────────────────────────────┤
  │ 3. Distortion（失真）           │  ← 制造谐波
  ├────────────────────────────────┤
  │ 4. Compressor（压缩）           │  ← 控制动态
  ├────────────────────────────────┤
  │ 5. Delay / Chorus / Phaser      │  ← 时间类效果
  ├────────────────────────────────┤
  │ 6. Reverb（混响）               │  ← 最后：要吃前面效果的输出
  └────────────────────────────────┘
        │
        ▼
  send 目标总线 → …… → Master → 声卡
```

> 顺序不是硬规则，但有三条通用原则：
> 1. **滤波放最前**——先把不该进入后续环节的频段去掉，后面每一级都在做无用功；
> 2. **压缩放在失真之后**——这样压缩器看到的是已经失真后的信号；
> 3. **混响放最后**——混响要听到前面所有效果的输出。
>
> 引擎不校验顺序，`add_bus_effect()` 的第三个参数 `at_position`
> 就是用来把效果器插到指定位置的；不传就追加到末尾。

---

## 5. 混音线程模型与平台差异

### 5.1 混音线程

Godot 4 的混音不在游戏主线程里做：音频驱动跑一条**独立混音线程**，
每轮回调 `AudioServer::_driver_process()`，里面按需调用 `_mix_step()` 完成一个混音块。
主线程只负责把播放器的样本写进各自的混音缓冲。

```
主线程                                 混音线程（音频驱动线程）
──────────────────────────            ────────────────────────────
AudioStreamPlayer 写入样本   ─────▶   _driver_process()
                                      └─ _mix_step()
                                           ├─ 收集各播放器的活跃样本
                                           ├─ 累加到各自总线的缓冲
                                           ├─ 跑该总线上的效果器链（串行）
                                           └─ 把结果汇入 send 目标总线
                                      └─ 输出到声卡
```

几个实践后果：

- **跨线程改总线 / 效果器要加锁**：`AudioServer.lock()` / `AudioServer.unlock()` 成对使用。
  锁住期间不要做耗时操作，否则会直接卡住混音线程、听不到声音。
- **`LOOKAHEAD_BUFFER_SIZE`（64 帧）** 是引擎在"当前混音块"和"下一块"之间保留的过渡缓冲，
  用来平滑淡入淡出与重采样。
- **Godot 4 没有暴露混音线程的 CPU 占用百分比**：`AudioServer` 没有 `performance_get()`，
  `Performance` 里也没有 `time_usage/*` 监视器（那是 Godot 3.x 的名字）。
  能拿到的只有 `AudioServer.get_time_since_last_mix()`（"距上次混音的相对时间"，单位秒）
  和 `Performance.get_monitor(Performance.AUDIO_OUTPUT_LATENCY)`（等价于 `get_output_latency()`）。
  要做真正的音频性能分析，得自己采样并结合引擎 Profiler。

### 5.2 相关项目设置

| 项目设置 | 默认值 | 说明 |
|----------|--------|------|
| `audio/driver/mix_rate` | 44100 | 混音采样率（Hz） |
| `audio/driver/output_latency` | 15 | 输出延迟（ms）；**Android 与 Windows 10 之前的 Windows 会忽略它**（官方文档原话）。实际值请用 `AudioServer.get_output_latency()` 查询 |
| `audio/driver/output_latency.web` | 50 | Web 平台的输出延迟（ms） |
| `audio/driver/mix_rate.web` | 0 | Web 平台的混音采样率；`0` 表示"让浏览器自己选"（某些浏览器不喜欢被强制指定采样率） |
| `audio/general/3d_panning_strength` | 0.5 | 3D 立体声扩展的全局强度；`AudioStreamPlayer3D.panning_strength` 在其基础上相乘。`0.0` = 完全关闭声像；`1.0` = 声源正对左/右时该声道被完全静音。默认 `0.5` 是按耳机调的，用音箱时往往要调小 |
| `audio/general/2d_panning_strength` | 0.5 | 2D 版本 |
| `audio/buses/channel_disable_threshold_db` | -60 | 低于该电平的总线通道会被暂时禁用（省 CPU：该总线上的效果器不再做任何处理） |
| `audio/buses/channel_disable_time` | 2.0 | 连续低于阈值多少秒后禁用（秒） |
| `audio/buses/default_bus_layout` | `res://default_bus_layout.tres` | 默认总线布局资源 |
| `audio/driver/enable_input` | false | 是否启用音频输入（麦克风）；**录音必须打开** |

### 5.3 Web / 移动端差异

- **`AudioServer.PLAYBACK_TYPE_SAMPLE`**：强制把播放当成"采样播放"。
  官方注释写得很清楚——**只在 Web 平台支持**，而且"sample 播放**不支持** AudioEffect"。
  也就是说，Web 上用 sample 播放模式时，整条总线效果器链会被绕过。
- **Web 有独立的设置项**：`audio/driver/mix_rate.web` 与 `audio/driver/output_latency.web`
  覆盖 `audio/driver/mix_rate` / `audio/driver/output_latency`。
- **Android 忽略 `audio/driver/output_latency`**：Android 由系统的 `AudioTrack` 管理缓冲，
  引擎不再自己加延迟。

### 5.4 总线布局：编辑器优先的工作流

```
推荐工作流（编辑器优先）:

  1. 编辑器 → 底部「Audio」面板 → 总线标签页
        ├─ 新建总线（Music / SFX / Voice / UI ...）
        ├─ 给每条总线挂效果器、设音量
        └─ 设置每条总线的 send（汇入目标）
                │
                ▼
  2. 布局保存为 res://default_bus_layout.tres
        （项目设置 audio/buses/default_bus_layout 指向它）
                │
                ▼
  3. 运行时只读地调整：音量 / 静音 / 独奏 / 效果器启停
     确实需要动态加总线时，用 AudioServer.add_bus() / remove_bus()
```

> 运行时用 `AudioServer.bus_count = N` 改总线数量是**危险**的：
> `set_bus_count()` 会重建总线列表——缩小时直接销毁超出数量的总线（连同名称与效果器），
> 放大时新建总线的名字是占位名 `New Bus` / `New Bus 2`。
> 增量操作用 `add_bus()`（追加）/ `add_bus(pos)`（在 pos 处插入）/
> `remove_bus(idx)` / `move_bus(from, to)` / `set_bus_name(idx, name)`。

---

## 6. 音频混合器优化

### 6.1 音频混合器缓存

```gdscript
# 音频混合器缓存
class_name AudioMixerCache

extends Node

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

### 6.2 音频混合器LOD

```gdscript
# 音频混合器LOD
class_name AudioMixerLOD

@export var lod_distances: Array = [10, 30, 50]
@export var lod_effects: Array = ["simple", "medium", "complex"]

func update_lod(camera_position: Vector3, bus_name: String):
    var bus_idx = AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    
    # ⚠️ current_scene 的类型是 Node，不保证有 global_transform
    #    （当前场景不是 Node3D 时会直接报错）
    var origin := Vector3.ZERO
    var scene := get_tree().current_scene as Node3D
    if scene:
        origin = scene.global_transform.origin
    var distance = camera_position.distance_to(origin)
    
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
            # ⚠️ count / 2 是整除：count == 1 时阈值是 0，等于把效果器全禁用了
            var half := int(ceil(count / 2.0))
            for i in range(count):
                AudioServer.set_bus_effect_enabled(bus_idx, i, i < half)
        "complex":
            # 复杂模式：启用所有效果
            var count = AudioServer.get_bus_effect_count(bus_idx)
            for i in range(count):
                AudioServer.set_bus_effect_enabled(bus_idx, i, true)
```

### 6.3 音频混合器性能监控

```gdscript
# 音频混合器性能监控
class_name AudioMixerPerformanceMonitor

extends Node

var effect_count = 0
var bus_count = 0
var mix_interval = 0.0  # 距上次混音的相对时间（秒），不是 CPU 使用率

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
    bus_count = AudioServer.bus_count
    effect_count = 0
    
    for i in range(bus_count):
        effect_count += AudioServer.get_bus_effect_count(i)
    
    mix_interval = AudioServer.get_time_since_last_mix()

func get_effect_count() -> int:
    return effect_count

func get_bus_count() -> int:
    return bus_count

func get_mix_interval() -> float:
    # Godot 4 没有暴露混音线程的 CPU 占用，只能给出混音间隔
    return mix_interval

func print_stats():
    print("Audio Mixer Stats:")
    print("- Bus Count: ", get_bus_count())
    print("- Effect Count: ", get_effect_count())
    print("- Mix Interval: ", get_mix_interval())
```

---

## 7. 实践：完整音频混合器系统

### 7.1 基础音频混合器系统

```gdscript
# 基础音频混合器系统
class_name BasicAudioMixerSystem

extends Node

func _ready():
    # 初始化基础音频混合器系统
    initialize_basic_mixer()

func initialize_basic_mixer():
    var audio_server = AudioServer
    
    # ⚠️ 不要直接改 bus_count（会重建总线列表、清掉名称与效果器）
    # 增量创建总线
    for bus_name in ["Music", "SFX"]:
        if audio_server.get_bus_index(bus_name) == -1:
            audio_server.add_bus()
            var idx := audio_server.bus_count - 1
            audio_server.set_bus_name(idx, bus_name)
    
    # 设置音量
    audio_server.set_bus_volume_db(audio_server.get_bus_index("Master"), 0.0)
    audio_server.set_bus_volume_db(audio_server.get_bus_index("Music"), -5.0)
    audio_server.set_bus_volume_db(audio_server.get_bus_index("SFX"), -3.0)

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

### 7.2 高级音频混合器系统

```gdscript
# 高级音频混合器系统
class_name AdvancedAudioMixerSystem

extends Node

func _ready():
    # 初始化高级音频混合器系统
    initialize_advanced_mixer()

func initialize_advanced_mixer():
    var audio_server = AudioServer
    
    # ⚠️ 不要直接改 bus_count（会重建总线列表、清掉名称与效果器）
    # 增量创建总线
    for bus_name in ["Music", "SFX", "Voice", "Ambient", "UI"]:
        if audio_server.get_bus_index(bus_name) == -1:
            audio_server.add_bus()
            var idx := audio_server.bus_count - 1
            audio_server.set_bus_name(idx, bus_name)
    
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

### 7.3 完整音频混合器系统

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
        "mix_interval": performance_monitor.get_mix_interval()
    }

func print_stats():
    performance_monitor.print_stats()
```

---

## 📝 本章总结

### 核心要点

1. **AudioServer 是核心混合器**，管理所有音频总线
2. **AudioBus 的拓扑由 send 字段决定**，一条总线只汇入一个目标总线
3. **AudioEffect 增强音频质量**，包括均衡、混响、压缩等；顺序即执行顺序
4. **混音在独立线程上完成**，跨线程修改总线要用 `lock()` / `unlock()`
5. **音频混合器优化**，包括缓存、LOD、性能监控

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

- **官方文档**: [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **类参考**: [AudioServer](https://docs.godotengine.org/en/stable/classes/class_audioserver.html)
- **类参考**: [AudioBusLayout](https://docs.godotengine.org/en/stable/classes/class_audiobuslayout.html)
- **源码位置**: `servers/audio/audio_server.cpp`（`_mix_step()`）、`servers/audio/effects/`

---

## 📋 下一章预告

**第 48 篇：音频效果器**

- 音频效果器基础与 4.3 完整清单
- 均衡器 / 混响 / 压缩器 / 延迟 / 失真 / 滤波器
- 效果器预设与总线应用
- 效果器性能

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 46 篇：音频播放器](/articles/46-audio-player.md)
**下一篇**: [第 48 篇：音频效果器](/articles/48-audio-effects.md)

---

*写作时间：2026-03-20*  
*字数：约 1,600 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 15:00*
