# 第 62 篇：音频分析和语音系统

> **本卷定位**: 第五卷 音频系统（6 篇）  
> **前置知识**: 第 59 章 3D 音频和动态音频  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

音频分析和语音系统为游戏带来更高级的音频交互能力。通过 FFT 频谱分析、节拍检测、语音聊天等技术，可以实现音乐游戏、语音通信等丰富功能。

本章将深入探讨音频分析、FFT 频谱、节拍检测、语音聊天集成等技术。

---

## 🎯 学习目标

- 理解 FFT 频谱分析原理
- 掌握音频可视化技术
- 学会节拍检测方法
- 熟悉语音聊天集成
- 实施音频识别基础

---

## 1. FFT 频谱分析

### 1.1 FFT 原理

```
FFT（快速傅里叶变换）:
┌─────────────────────────────────────────────────────────────┐
│ 时域信号 → FFT → 频域信号                                   │
│                                                             │
│ 应用:                                                       │
│ - 音频可视化（频谱仪）                                      │
│ - 节拍检测                                                  │
│ - 音效识别                                                  │
│ - 均衡器                                                    │
└─────────────────────────────────────────────────────────────┘

关键参数:
- 采样率：44100 Hz（CD 质量）
- FFT 大小：1024/2048/4096 点
- 频段数：FFT 大小/2
```

### 1.2 Godot 音频分析实现

```gdscript
# 音频分析器
class_name AudioAnalyzer

extends Node

@export var min_frequency: float = 20.0
@export var max_frequency: float = 20000.0

var audio_stream: AudioStreamPlayer
var spectrum_instance: AudioEffectSpectrumAnalyzerInstance
# 每个频段的能量（左声道 + 右声道之和）
var band_data: PackedFloat32Array = PackedFloat32Array()

# 各频段的频率范围（Hz）
const BAND_RANGES := [
    [20.0, 60.0],       # sub
    [60.0, 250.0],      # bass
    [250.0, 500.0],     # low_mid
    [500.0, 2000.0],    # mid
    [2000.0, 4000.0],   # high_mid
    [4000.0, 20000.0],  # high
]
const BAND_NAMES := ["sub", "bass", "low_mid", "mid", "high_mid", "high"]

func _ready():
    _setup_analyzer()

func _setup_analyzer():
    # 创建音频流
    audio_stream = AudioStreamPlayer.new()
    add_child(audio_stream)
    
    # 添加频谱分析效果
    var bus_index = AudioServer.get_bus_index("Master")
    var effect = AudioEffectSpectrumAnalyzer.new()
    # ⚠️ 真实成员是 buffer_length / fft_size / tap_back_pos：
    #    没有 magnitude，也没有 hsz。
    #    频点数量由 fft_size 决定（FFT_SIZE_2048 → 1024 个频点），
    #    不要硬编码成 80 段。
    effect.fft_size = AudioEffectSpectrumAnalyzer.FFT_SIZE_2048
    effect.buffer_length = 0.2
    AudioServer.add_bus_effect(bus_index, effect)
    
    # 获取频谱实例
    # ⚠️ 刚添加的效果器索引是最后一个（不是硬编码的 1）；
    #    而且 get_bus_effect_instance() 返回的是 AudioEffectInstance，
    #    要显式转成 AudioEffectSpectrumAnalyzerInstance 才能调它自己的方法。
    var effect_index = AudioServer.get_bus_effect_count(bus_index) - 1
    spectrum_instance = AudioServer.get_bus_effect_instance(bus_index, effect_index) as AudioEffectSpectrumAnalyzerInstance

func _process(_delta: float) -> void:
    # 获取频谱数据
    _update_spectrum()

func _update_spectrum() -> void:
    # ⚠️ 没有 get_data_for_range()。
    #    真实方法：get_magnitude_for_frequency_range(from_hz, to_hz, mode) -> Vector2
    #    返回的 Vector2.x 是左声道、.y 是右声道；
    #    mode 取 MAGNITUDE_AVERAGE(0) 或 MAGNITUDE_MAX(1)。
    band_data = PackedFloat32Array()
    for band_range in BAND_RANGES:
        var magnitude := spectrum_instance.get_magnitude_for_frequency_range(
            band_range[0], band_range[1], AudioEffectSpectrumAnalyzerInstance.MAGNITUDE_AVERAGE
        )
        band_data.append(magnitude.x + magnitude.y)

# 获取某个预定义频段的能量
func get_band_energy(band: String) -> float:
    var index := BAND_NAMES.find(band)
    if index < 0 or index >= band_data.size():
        return 0.0
    return band_data[index]

# 获取任意频率区间的平均能量（线性）
func get_energy_in_range(from_hz: float, to_hz: float) -> float:
    var magnitude := spectrum_instance.get_magnitude_for_frequency_range(
        from_hz, to_hz, AudioEffectSpectrumAnalyzerInstance.MAGNITUDE_AVERAGE
    )
    return magnitude.x + magnitude.y

# 获取能量最高的频段中心频率
func get_peak_frequency() -> float:
    var peak_value := 0.0
    var peak_index := 0
    
    for i in range(band_data.size()):
        if band_data[i] > peak_value:
            peak_value = band_data[i]
            peak_index = i
    
    if peak_index >= BAND_RANGES.size():
        return 0.0
    var band_range: Array = BAND_RANGES[peak_index]
    return (band_range[0] + band_range[1]) * 0.5
```

---

## 2. 音频可视化

### 2.1 频谱可视化

```gdscript
# 音频频谱可视化
class_name AudioSpectrumVisualizer

extends Control

@export var bar_count: int = 64
@export var bar_width: float = 10.0
@export var bar_spacing: float = 2.0
@export var color_gradient: Gradient
@export var min_frequency: float = 20.0
@export var max_frequency: float = 20000.0

var analyzer: AudioAnalyzer
var bar_heights: Array = []

func _ready():
    analyzer = AudioAnalyzer.new()
    add_child(analyzer)
    
    # 初始化条形高度
    for i in range(bar_count):
        bar_heights.append(0.0)

func _draw():
    _draw_spectrum_bars()

func _draw_spectrum_bars():
    for i in range(bar_count):
        # 每根柱子对应一段频率，按对数分布（低频不会挤成一根）
        var from_hz := min_frequency * pow(max_frequency / min_frequency, float(i) / float(bar_count))
        var to_hz := min_frequency * pow(max_frequency / min_frequency, float(i + 1) / float(bar_count))
        var energy = analyzer.get_energy_in_range(from_hz, to_hz)
        
        # 平滑高度
        bar_heights[i] = lerp(bar_heights[i], energy, 0.3)
        
        # 计算位置
        var x = i * (bar_width + bar_spacing)
        var height = bar_heights[i] * size.y
        
        # 绘制条形
        var color = color_gradient.sample(float(i) / bar_count)
        draw_rect(Rect2(x, size.y - height, bar_width, height), color)
```

### 2.2 波形可视化

```gdscript
# 音频波形可视化
class_name AudioWaveformVisualizer

extends Control

@export var sample_count: int = 512
@export var line_color: Color = Color.CYAN

# ⚠️ PoolRealArray 是 Godot 3.x 的类型，4.x 已移除；
#    对应物是 PackedFloat32Array（注意要用 () 构造，不能写 = []）
var audio_buffer: PackedFloat32Array = PackedFloat32Array()

func _ready():
    # 初始化缓冲区
    for i in range(sample_count):
        audio_buffer.append(0.0)

func _draw():
    _draw_waveform()

func _draw_waveform():
    if audio_buffer.is_empty():
        return
    
    var points := PackedVector2Array()
    
    for i in range(sample_count):
        var x = float(i) / sample_count * size.x
        var y = size.y / 2.0 + (audio_buffer[i] * size.y / 2.0)
        
        if i == 0:
            points.append(Vector2(x, y))
        else:
            points.append(Vector2(x, y))
    
    draw_polyline(points, line_color, 2.0)

func update_buffer(samples: PackedFloat32Array) -> void:
    audio_buffer = samples
    update()
```

---

## 3. 节拍检测

### 3.1 节拍检测原理

```
节拍检测方法:
┌─────────────────────────────────────────────────────────────┐
│ 1. 能量检测法                                               │
│    - 检测低频能量峰值                                       │
│    - 简单快速                                               │
│                                                             │
│ 2. 频谱通量法                                               │
│    - 检测频谱变化                                           │
│    - 更准确                                                 │
│                                                             │
│ 3. 相位锁定法                                               │
│    - 追踪节拍相位                                           │
│    - 最准确但复杂                                           │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 节拍检测实现

```gdscript
# 节拍检测器
class_name BeatDetector

extends Node

@export var threshold: float = 0.8
@export var min_bpm: float = 60.0
@export var max_bpm: float = 180.0

var analyzer: AudioAnalyzer
var energy_history: Array = []
var beat_history: Array = []
var current_bpm: float = 0.0
var last_beat_time: float = 0.0

# ⚠️ 信号必须带参数：否则下面 emit_signal("beat_detected", bpm)
#    会抛 "expected 0 arguments, but called with 1"
signal beat_detected(bpm: float)

func _ready():
    analyzer = AudioAnalyzer.new()
    add_child(analyzer)

func _process(delta):
    _detect_beat()

func _detect_beat():
    # 获取低频能量
    var bass_energy = analyzer.get_band_energy("bass")
    energy_history.append(bass_energy)
    
    # 限制历史记录
    if energy_history.size() > 60:  # 1 秒
        energy_history.pop_front()
    
    # 检测峰值
    if _is_peak(bass_energy):
        var current_time = Time.get_ticks_msec() / 1000.0
        
        if last_beat_time > 0:
            var beat_interval = current_time - last_beat_time
            
            # 验证 BPM 范围
            var detected_bpm = 60.0 / beat_interval
            if detected_bpm >= min_bpm and detected_bpm <= max_bpm:
                _on_beat_detected(current_time, detected_bpm)
        
        last_beat_time = current_time

func _is_peak(energy: float) -> bool:
    if energy_history.size() < 10:
        return false
    
    # 计算平均能量
    var avg_energy = 0.0
    for i in range(energy_history.size() - 1):
        avg_energy += energy_history[i]
    avg_energy /= (energy_history.size() - 1)
    
    # 检测峰值
    return energy > (avg_energy * threshold)

func _on_beat_detected(time: float, bpm: float):
    current_bpm = bpm
    beat_history.append(time)
    
    # 限制历史记录
    if beat_history.size() > 10:
        beat_history.pop_front()
    
    emit_signal("beat_detected", bpm)
```

---

## 4. 语音聊天集成

### 4.1 语音聊天基础

```gdscript
# 麦克风采集与语音活动检测（VAD）
#
# ⚠️ 引擎**不提供**语音聊天能力：没有回声消除（AEC）、降噪（NS）、
#    自动增益控制（AGC）、抖动缓冲（jitter buffer），也没有内置 Opus 编解码。
#    4.x 与麦克风相关的原语只有：
#      AudioStreamMicrophone —— 把麦克风当成一个音频流来播
#      AudioEffectRecord     —— 把总线录成 AudioStreamWAV
#      AudioEffectCapture    —— 实时取出原始 PCM 帧
#    下面演示的是"用 AudioEffectCapture 做 VAD"，网络部分见 §4.2。
class_name VoiceActivityDetector

extends Node

@export var input_device: String = ""
@export var bus_name: String = "VoiceChat"
# VAD 阈值（dBFS）：要按实际麦克风与环境噪声标定，这里只是起点
@export var vad_threshold_db: float = -40.0

var capture_effect: AudioEffectCapture
var is_recording: bool = false
var voice_level_db: float = -80.0

signal voice_activity_detected
signal voice_received

func _ready():
    _setup_audio_devices()

func _setup_audio_devices():
    # 配置输入设备
    # ⚠️ 必须先在项目设置里打开 audio/driver/enable_input（默认 false），
    #    否则 AudioStreamMicrophone 采不到任何数据。
    if input_device != "":
        AudioServer.input_device = input_device
    
    # 在目标总线上挂 AudioEffectCapture，用来取原始 PCM
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        AudioServer.add_bus()
        bus_idx = AudioServer.bus_count - 1
        AudioServer.set_bus_name(bus_idx, bus_name)
    
    capture_effect = AudioEffectCapture.new()
    capture_effect.buffer_length = 0.2
    AudioServer.add_bus_effect(bus_idx, capture_effect)
    
    # 把麦克风接到这条总线上
    var mic := AudioStreamPlayer.new()
    mic.stream = AudioStreamMicrophone.new()
    mic.bus = bus_name
    add_child(mic)
    mic.play()

func start_recording() -> void:
    is_recording = true

func stop_recording() -> void:
    is_recording = false

func _process(_delta: float) -> void:
    if is_recording:
        _detect_voice_activity()

func _detect_voice_activity() -> void:
    # ⚠️ 不能用播放器的 volume_db 做 VAD：
    #    volume_db 是"你设置的音量"，不是"麦克风采到的电平"。
    #    要拿真实电平，必须读原始 PCM 帧。
    var frames := capture_effect.get_frames_available()
    if frames <= 0:
        return
    
    var buffer := capture_effect.get_buffer(frames)
    if buffer.is_empty():
        return
    
    # 算 RMS（能量）→ dB
    var sum := 0.0
    for frame in buffer:
        sum += frame.x * frame.x
    var rms := sqrt(sum / float(buffer.size()))
    voice_level_db = linear_to_db(maxf(rms, 0.000001))
    
    if voice_level_db > vad_threshold_db:
        emit_signal("voice_activity_detected")
```

### 4.2 网络语音聊天：引擎不提供，需要自建

**Godot 4 没有语音聊天功能。** 引擎不提供回声消除（AEC）、降噪（NS）、
自动增益控制（AGC）、抖动缓冲（jitter buffer）、内置 Opus 编解码，
也没有"麦克风 → 编码 → 发给远端 → 解码 → 播放"的现成管线。
把任意字节塞进 `AudioStreamMP3.data` 是**不能**解码播放的——
`AudioStreamMP3.data` 必须是一段合法的 MP3 码流。

可行的三条路线：

| 路线 | 做法 | 适用场景 | 代价 |
|---|---|---|---|
| (a) 自建 PCM / Opus over UDP | 自己采 PCM，自己实现（或引入）Opus 编码，自己做 jitter buffer 与丢包隐藏，再用 `AudioStreamGenerator` 播放 | 愿意自己实现音频传输栈 | 工作量大；对延迟与丢包处理要求高 |
| (b) 可选编译的 WebRTC 模块 | `modules/webrtc` 提供 `WebRTCPeerConnection` / `WebRTCDataChannel`，用数据通道传音频包 | 需要点对点 / 中继的实时通话 | 该模块**默认不编译**进官方发行版，需要自己编译引擎 |
| (c) 第三方方案 | 例如 GodotSteam（Steam Networking）提供的语音服务 | 已有 Steam 生态 | 绑定平台 |

> ⚠️ 下列延迟预算为示意数据（未附测试环境），实际值取决于设备与网络。

> 移动端注意事项：
> - Android 需要 `RECORD_AUDIO` 权限；
> - iOS 需要在 `Info.plist` 里写 `NSMicrophoneUsageDescription`，否则系统直接拒绝；
> - 两者都需要 `ProjectSettings.audio/driver/enable_input = true`（默认 false），
>   否则 `AudioStreamMicrophone` 根本拿不到数据；
> - 延迟预算：采集 10~20 ms、编解码 10~20 ms、网络抖动缓冲 20~60 ms、
>   播放缓冲 20~40 ms，端到端通常在 100 ms 量级。

```gdscript
# 路线 (a)：自建音频传输的骨架
#
# ⚠️ 引擎**不提供**：回声消除、降噪、自动增益、抖动缓冲、Opus 编解码。
#    下面只演示"管线形状"，每个 TODO 都是引擎不替你做的事。
class_name NetworkVoiceChatSkeleton

extends Node

@export var bus_name: String = "VoiceChat"

var capture_effect: AudioEffectCapture
var playback: AudioStreamGeneratorPlayback
# ⚠️ TODO：自己实现的 jitter buffer（收包按到达时间重排、
#    丢包时补静音或做丢包隐藏）。直接把网络包塞进播放缓冲
#    一定会出现明显的爆音与抖动。

func _ready():
    _setup_capture()
    _setup_playback()

func _setup_capture():
    # 采集：引擎只给你原始 PCM
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        AudioServer.add_bus()
        bus_idx = AudioServer.bus_count - 1
        AudioServer.set_bus_name(bus_idx, bus_name)
    capture_effect = AudioEffectCapture.new()
    capture_effect.buffer_length = 0.1
    AudioServer.add_bus_effect(bus_idx, capture_effect)

    var mic := AudioStreamPlayer.new()
    mic.stream = AudioStreamMicrophone.new()
    mic.bus = bus_name
    add_child(mic)
    mic.play()

func _setup_playback():
    # 播放：用 AudioStreamGenerator 把收到的 PCM 灌进去
    var generator := AudioStreamGenerator.new()
    generator.mix_rate = 48000.0
    generator.buffer_length = 0.1
    var player := AudioStreamPlayer.new()
    player.stream = generator
    player.bus = bus_name
    add_child(player)
    player.play()
    playback = player.get_stream_playback() as AudioStreamGeneratorPlayback

func _process(_delta: float) -> void:
    _capture_and_send()
    _drain_playback()

func _capture_and_send() -> void:
    var frames := capture_effect.get_frames_available()
    if frames <= 0:
        return
    var buffer := capture_effect.get_buffer(frames)
    if buffer.is_empty():
        return
    # ⚠️ TODO：把 PCM 编码成 Opus（或直接发 PCM）。
    #    引擎没有 Opus 编解码器：要么引入第三方 GDExtension，
    #    要么改走路线 (b) 的 WebRTC 数据通道 / 路线 (c)。
    # ⚠️ TODO：把编码后的包发出去（ENet / UDP / WebRTC DataChannel）。

func _drain_playback() -> void:
    # 把收到的帧推进播放缓冲
    while playback.get_frames_available() > 0:
        # ⚠️ TODO：从 jitter buffer 取一帧 PCM 填进来
        playback.push_frame(Vector2.ZERO)
```

### 4.3 录音与采集：正确链路

要录下"游戏里听到的声音"或"麦克风的声音"，4.x 有两条链路，别混用：

| 需求 | 用什么 | 关键 API |
|---|---|---|
| 录一段文件（WAV） | `AudioEffectRecord` | `format`（取 `AudioStreamWAV.Format`）/ `set_recording_active(true)` / `get_recording() -> AudioStreamWAV` |
| 实时拿原始 PCM（做 VAD、网络传输、自定义效果） | `AudioEffectCapture` | `buffer_length` / `get_frames_available()` / `get_buffer(frames) -> PackedVector2Array` / `can_get_buffer(frames)` / `get_discarded_frames()` |

两者都必须：

1. 挂在某条总线上（`AudioServer.add_bus_effect(bus_idx, effect)`）；
2. 打开 `ProjectSettings.audio/driver/enable_input`（**默认 false**），
   否则 `AudioStreamMicrophone` 采不到任何数据；
3. 移动端申请麦克风权限：Android `RECORD_AUDIO`、
   iOS `Info.plist` 里的 `NSMicrophoneUsageDescription`。

```gdscript
# 录音正确链路
class_name AudioRecorder

extends Node

@export var bus_name: String = "Master"

var record_effect: AudioEffectRecord

func _ready():
    var bus_idx := AudioServer.get_bus_index(bus_name)
    if bus_idx == -1:
        return
    record_effect = AudioEffectRecord.new()
    # 格式取 AudioStreamWAV.Format：
    #   FORMAT_8_BITS / FORMAT_16_BITS / FORMAT_IMA_ADPCM / FORMAT_QOA
    record_effect.format = AudioStreamWAV.FORMAT_16_BITS
    AudioServer.add_bus_effect(bus_idx, record_effect)

func start() -> void:
    # ⚠️ 重新开始录制会丢弃之前录到的内容
    record_effect.set_recording_active(true)

func stop_and_save(path: String = "user://recording.wav") -> String:
    record_effect.set_recording_active(false)
    var wav := record_effect.get_recording()
    if wav == null:
        return ""
    var err := wav.save_to_wav(path)
    return path if err == OK else ""
```

---

## 📝 本章总结

### 核心要点

1. **FFT 频谱分析**是音频处理的基础：`AudioEffectSpectrumAnalyzer` + `get_magnitude_for_frequency_range()`
2. **音频可视化**提升用户体验
3. **节拍检测**用于音乐游戏和同步
4. **引擎不提供语音聊天**：需自建 PCM/Opus over UDP、WebRTC 模块或第三方方案
5. **录音与采集**走 `AudioEffectRecord` / `AudioEffectCapture`，并打开 `audio/driver/enable_input`

### 关键术语

| 术语 | 解释 |
|------|------|
| FFT | 快速傅里叶变换，时域转频域 |
| Spectrum | 频谱，频率分布 |
| Beat Detection | 节拍检测 |
| Voice Activity Detection | 语音活动检测 |
| Codec | 编解码器，压缩音频 |
| `AudioEffectSpectrumAnalyzer` | 总线上的频谱分析效果器（不改变声音输出） |
| `AudioEffectCapture` | 实时取出总线上的原始 PCM |
| `AudioEffectRecord` | 把总线录成 `AudioStreamWAV` |
| Jitter Buffer | 抖动缓冲；网络音频必备，引擎不提供 |

---

## 🔗 延伸阅读

- **官方文档**: [Recording with microphone](https://docs.godotengine.org/en/stable/tutorials/audio/recording_with_microphone.html)
- **官方文档**: [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html)
- **类参考**: [AudioEffectSpectrumAnalyzer](https://docs.godotengine.org/en/stable/classes/class_audioeffectspectrumanalyzer.html)
- **类参考**: [AudioEffectSpectrumAnalyzerInstance](https://docs.godotengine.org/en/stable/classes/class_audioeffectspectrumanalyzerinstance.html)
- **类参考**: [AudioEffectCapture](https://docs.godotengine.org/en/stable/classes/class_audioeffectcapture.html)
- **类参考**: [AudioEffectRecord](https://docs.godotengine.org/en/stable/classes/class_audioeffectrecord.html)
- **源码位置**: `servers/audio/effects/audio_effect_spectrum_analyzer.cpp`、`servers/audio/effects/audio_effect_capture.cpp`

---

## 📋 下一章预告

**第 63 篇：编辑器高级功能**

- 编辑器插件与扩展点
- 自定义 Inspector 与节点
- 调试与自动化工具

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 59 篇：3D 音频和动态音频系统](/articles/59-3d-audio-and-dynamic-audio.md)
**下一篇**: [第 49 篇：网络系统](/articles/49-network-system.md)

---

*写作时间：2026-03-21*  
*字数：约 900 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*
