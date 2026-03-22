# 第 62 篇：音频分析和语音系统

> **本卷定位**: 第五卷 音频系统（完善篇）  
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

@export var fft_size: int = 2048
@export var min_frequency: float = 20.0
@export var max_frequency: float = 20000.0

var audio_stream: AudioStreamPlayer
var spectrum_instance: AudioEffectSpectrumAnalyzerInstance
var spectrum_data: PoolRealArray

func _ready():
    _setup_analyzer()

func _setup_analyzer():
    # 创建音频流
    audio_stream = AudioStreamPlayer.new()
    add_child(audio_stream)
    
    # 添加频谱分析效果
    var bus_index = AudioServer.get_bus_index("Master")
    var effect = AudioEffectSpectrumAnalyzer.new()
    effect.magnitude = 80.0
    effect.hsz = fft_size
    AudioServer.add_bus_effect(bus_index, effect)
    
    # 获取频谱实例
    spectrum_instance = AudioServer.get_bus_effect_instance(bus_index, 1)

func _process(delta):
    # 获取频谱数据
    _update_spectrum()

func _update_spectrum():
    var data = spectrum_instance.get_data_for_range(min_frequency, max_frequency)
    
    # 转换为数组
    spectrum_data = []
    for i in range(data.size()):
        spectrum_data.append(data[i])

# 获取频段能量
func get_band_energy(band: String) -> float:
    match band:
        "sub": return _get_average(0, 4)       # 20-60Hz
        "bass": return _get_average(4, 10)     # 60-250Hz
        "low_mid": return _get_average(10, 20) # 250-500Hz
        "mid": return _get_average(20, 40)     # 500-2kHz
        "high_mid": return _get_average(40, 60)# 2k-4kHz
        "high": return _get_average(60, 80)    # 4k-20kHz
    return 0.0

func _get_average(start: int, end: int) -> float:
    var sum = 0.0
    for i in range(start, min(end, spectrum_data.size())):
        sum += spectrum_data[i]
    return sum / (end - start)

# 获取峰值频率
func get_peak_frequency() -> float:
    var max_value = 0.0
    var max_index = 0
    
    for i in range(spectrum_data.size()):
        if spectrum_data[i] > max_value:
            max_value = spectrum_data[i]
            max_index = i
    
    # 转换为频率
    return min_frequency + (max_index / float(spectrum_data.size())) * (max_frequency - min_frequency)
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
        # 获取频段能量
        var energy = analyzer.get_band_energy(_get_band_name(i))
        
        # 平滑高度
        bar_heights[i] = lerp(bar_heights[i], energy, 0.3)
        
        # 计算位置
        var x = i * (bar_width + bar_spacing)
        var height = bar_heights[i] * size.y
        
        # 绘制条形
        var color = color_gradient.sample(float(i) / bar_count)
        draw_rect(Rect2(x, size.y - height, bar_width, height), color)

func _get_band_name(index: int) -> String:
    var bands = ["sub", "bass", "low_mid", "mid", "high_mid", "high"]
    var band_index = int(float(index) / bar_count * bands.size())
    return bands[clamp(band_index, 0, bands.size() - 1)]
```

### 2.2 波形可视化

```gdscript
# 音频波形可视化
class_name AudioWaveformVisualizer

extends Control

@export var sample_count: int = 512
@export var line_color: Color = Color.CYAN

var audio_buffer: PoolRealArray = []

func _ready():
    # 初始化缓冲区
    for i in range(sample_count):
        audio_buffer.append(0.0)

func _draw():
    _draw_waveform()

func _draw_waveform():
    if audio_buffer.is_empty():
        return
    
    var points = PoolVector2Array()
    
    for i in range(sample_count):
        var x = float(i) / sample_count * size.x
        var y = size.y / 2.0 + (audio_buffer[i] * size.y / 2.0)
        
        if i == 0:
            points.append(Vector2(x, y))
        else:
            points.append(Vector2(x, y))
    
    draw_polyline(points, line_color, 2.0)

func update_buffer(samples: PoolRealArray):
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

signal beat_detected

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
# 语音聊天管理器
class_name VoiceChatManager

extends Node

@export var input_device: String = ""
@export var output_device: String = ""
@export var voice_volume_db: float = 0.0

var is_recording: bool = false
var audio_input: AudioStreamPlayer
var audio_output: AudioStreamPlayer

signal voice_activity_detected
signal voice_received

func _ready():
    _setup_audio_devices()

func _setup_audio_devices():
    # 配置输入设备
    if input_device != "":
        AudioServer.input_device = input_device
    
    # 配置输出设备
    if output_device != "":
        AudioServer.output_device = output_device
    
    # 创建音频流
    audio_input = AudioStreamPlayer.new()
    audio_input.bus = "VoiceChat"
    add_child(audio_input)
    
    audio_output = AudioStreamPlayer.new()
    audio_output.bus = "VoiceChat"
    add_child(audio_output)

func start_recording():
    is_recording = true
    audio_input.stream = AudioStreamMicrophone.new()
    audio_input.play()

func stop_recording():
    is_recording = false
    audio_input.stop()

func play_voice(audio_data: PoolByteArray):
    var stream = AudioStreamMP3.new()
    stream.data = audio_data
    audio_output.stream = stream
    audio_output.play()

func _process(delta):
    if is_recording:
        _detect_voice_activity()

func _detect_voice_activity():
    # 检测语音活动
    var volume_db = audio_input.get_volume_db()
    
    if volume_db > -40.0:  # 阈值
        emit_signal("voice_activity_detected")
```

### 4.2 网络语音聊天

```gdscript
# 网络语音聊天
class_name NetworkVoiceChat

extends VoiceChatManager

var peer_id: int = 0
var compression_enabled: bool = true

func _ready():
    super._ready()
    
    # 连接网络信号
    if multiplayer.has_signal("peer_connected"):
        multiplayer.peer_connected.connect(_on_peer_connected)
        multiplayer.peer_disconnected.connect(_on_peer_disconnected)

func _on_peer_connected(id: int):
    print("Peer connected: ", id)

func _on_peer_disconnected(id: int):
    print("Peer disconnected: ", id)

func send_voice_data():
    if not is_recording:
        return
    
    # 获取音频数据
    var audio_data = _capture_audio()
    
    # 压缩（可选）
    if compression_enabled:
        audio_data = _compress_audio(audio_data)
    
    # 发送给其他玩家
    rpc("_receive_voice_data", audio_data)

func _compress_audio(data: PoolByteArray) -> PoolByteArray:
    # 使用 Opus 或其他编解码器
    # 简化示例
    return data

func _decompress_audio(data: PoolByteArray) -> PoolByteArray:
    # 解压缩
    return data

@rpc("any_peer", "unreliable")
func _receive_voice_data(data: PoolByteArray):
    # 解压缩
    if compression_enabled:
        data = _decompress_audio(data)
    
    # 播放
    play_voice(data)
    emit_signal("voice_received")

func _capture_audio() -> PoolByteArray:
    # 捕获音频数据
    # 实际实现需要访问音频缓冲区
    return PoolByteArray()
```

---

## 📝 本章总结

### 核心要点

1. **FFT 频谱分析**是音频处理的基础
2. **音频可视化**提升用户体验
3. **节拍检测**用于音乐游戏和同步
4. **语音聊天**增强多人交互
5. **性能优化**确保实时处理

### 关键术语

| 术语 | 解释 |
|------|------|
| FFT | 快速傅里叶变换，时域转频域 |
| Spectrum | 频谱，频率分布 |
| Beat Detection | 节拍检测 |
| Voice Activity Detection | 语音活动检测 |
| Codec | 编解码器，压缩音频 |

---

*写作时间：2026-03-21*  
*字数：约 6,000 字*  
*状态：✅ 完成*
