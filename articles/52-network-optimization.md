# 第 52 篇：网络优化

> **本卷定位**: 第六卷 网络系统（5 篇）  
> **前置知识**: 第 51 章 网络同步  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

网络优化是多人游戏性能的关键，直接影响玩家的游戏体验。通过网络性能分析、带宽优化、延迟优化和同步优化，可以显著提升游戏的网络性能和稳定性。

本章将深入探讨网络优化的各种技术和方法，以及如何在 Godot 中实现这些优化。

---

## 🎯 学习目标

- 理解网络性能分析方法
- 掌握带宽优化技术
- 学会延迟优化方法
- 熟悉同步优化策略
- 掌握网络优化实践

> ⚠️ **关于本章的数值**：本章出现的所有阈值与默认值（同步率 60/30/10 Hz、插值缓冲 50–200 ms、RTT 150 ms、Jitter 50 ms、单机带宽上限 50–100 kbps 等）都是**示意值 / 经验起点**，**未附测试环境**（没有给出 CPU、带宽、延迟、玩家数、包长等测量条件）。它们的作用是告诉你"该调哪几个旋钮"，**不是**可以直接抄进项目的推荐值。真实取值必须在**你自己的网络条件下**用第 1 节的监控器实测后确定。

---

## 1. 网络性能分析

### 1.1 性能指标

```
网络性能指标:
┌─────────────────────────────────────────────────────────────┐
│                      网络性能指标                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 延迟（Latency/RTT）：往返时间                          │
│  2. 带宽（Bandwidth）：数据传输速率                        │
│  3. 丢包率（Packet Loss）：丢失包的比例                    │
│  4. 抖动（Jitter）：延迟变化                               │
│  5. 吞吐量（Throughput）：有效数据传输速率                 │
│  6. 连接数（Connections）：活跃连接数量                    │
│  7. 包大小（Packet Size）：平均包大小                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 性能监控器

```gdscript
# 网络性能监控器
class_name NetworkBandwidthMonitor

extends Node

# 采样间隔（秒）。注意这是「间隔」而不是「频率」，
# 频率 = 1.0 / sample_interval。
@export var sample_interval: float = 1.0
@export var history_size: int = 60

var stats: Dictionary = {
    "rtt": [],
    "bandwidth_sent": [],
    "bandwidth_received": [],
    "packets_sent": [],
    "packets_received": [],
    "packet_loss": [],
    "jitter": []
}

# 本采样窗口内的累加量
var current_session: Dictionary = {
    "bytes_sent": 0,
    "bytes_received": 0,
    "packets_sent": 0,
    "packets_received": 0,
    "packets_lost": 0,
    "start_time": 0
}

# 应用层 ping/pong 得到的原始 RTT 样本（在两次采样之间累积）
var _rtt_samples: Array = []
# 应用层序号统计：用于算「序号缺口」
var _highest_seq_sent: int = -1
var _highest_seq_received: int = -1
var _last_sample_ms: int = 0

signal stats_updated(stats: Dictionary)

func _ready():
    current_session.start_time = Time.get_ticks_msec()
    _last_sample_ms = Time.get_ticks_msec()
    
    # 启动定时采样
    var timer = Timer.new()
    timer.wait_time = sample_interval
    timer.timeout.connect(_sample_stats)
    add_child(timer)
    timer.start()

func _sample_stats():
    # 采样统计
    _calculate_bandwidth()
    _calculate_rtt()
    _calculate_jitter()
    _calculate_packet_loss()
    
    # 存储样本
    _store_sample()
    
    # 清理历史
    _cleanup_history()
    
    _last_sample_ms = Time.get_ticks_msec()
    stats_updated.emit(get_current_stats())

func record_packet_sent(bytes: int, seq: int = -1):
    # 记录发送包
    current_session.bytes_sent += bytes
    current_session.packets_sent += 1
    if seq >= 0:
        _highest_seq_sent = maxi(_highest_seq_sent, seq)

func record_packet_received(bytes: int, seq: int = -1):
    # 记录接收包
    current_session.bytes_received += bytes
    current_session.packets_received += 1
    if seq >= 0:
        # 序号缺口 = 本次收到的序号 - 期望的下一个序号
        var expected := _highest_seq_received + 1
        if seq > expected:
            current_session.packets_lost += seq - expected
        _highest_seq_received = maxi(_highest_seq_received, seq)

func record_rtt(rtt_ms: float):
    # 记录 RTT 样本（由应用层 ping/pong 提供）
    _rtt_samples.append(rtt_ms)

func _calculate_bandwidth():
    # 计算带宽：用**真实经过的时间**做分母，不能拿配置值当实际耗时
    var now_ms := Time.get_ticks_msec()
    var elapsed_seconds := max(0.001, float(now_ms - _last_sample_ms) / 1000.0)
    var sent_bps = (current_session.bytes_sent * 8) / elapsed_seconds
    var received_bps = (current_session.bytes_received * 8) / elapsed_seconds
    
    stats.bandwidth_sent.append(sent_bps)
    stats.bandwidth_received.append(received_bps)
    
    # 重置计数
    current_session.bytes_sent = 0
    current_session.bytes_received = 0

func _calculate_rtt():
    # 计算 RTT：引擎没有提供 RTT 接口，必须由应用层 ping/pong 喂进来。
    # 每次采样取本窗口内 RTT 样本的平均值。
    if _rtt_samples.is_empty():
        return
    var total := 0.0
    for rtt in _rtt_samples:
        total += rtt
    stats.rtt.append(total / _rtt_samples.size())
    _rtt_samples.clear()

func _calculate_jitter():
    # 计算抖动：相邻两次采样的 RTT 均值之差的绝对值平均
    if stats.rtt.size() >= 2:
        var jitter = 0.0
        for i in range(1, stats.rtt.size()):
            jitter += abs(stats.rtt[i] - stats.rtt[i - 1])
        stats.jitter.append(jitter / (stats.rtt.size() - 1))

func _calculate_packet_loss():
    # 计算丢包率：用**应用层序号缺口**统计
    # 在可靠通道上，ENet 会重传，网络丢包表现为延迟而不是缺口；
    # 此时缺口统计到的是「应用层实际没交付到的消息数」。
    # 在非可靠通道上，同一套统计直接反映网络丢包率。
    var total_sent := int(current_session.packets_sent)
    if total_sent <= 0:
        return
    var lost := int(current_session.packets_lost)
    stats.packet_loss.append(float(lost) / float(total_sent))

func _store_sample():
    # 存储样本
    stats.packets_sent.append(current_session.packets_sent)
    stats.packets_received.append(current_session.packets_received)
    
    current_session.packets_sent = 0
    current_session.packets_received = 0
    current_session.packets_lost = 0

func _cleanup_history():
    # 清理历史
    for key in stats:
        while stats[key].size() > history_size:
            stats[key].pop_front()

func get_current_stats() -> Dictionary:
    # 获取当前统计
    return {
        "average_rtt": _get_average(stats.rtt),
        "average_bandwidth_sent": _get_average(stats.bandwidth_sent),
        "average_bandwidth_received": _get_average(stats.bandwidth_received),
        "average_jitter": _get_average(stats.jitter),
        "average_packet_loss": _get_average(stats.packet_loss),
        "total_bytes_sent": _sum(stats.bandwidth_sent) / 8.0,
        "total_bytes_received": _sum(stats.bandwidth_received) / 8.0,
        "session_duration": (Time.get_ticks_msec() - current_session.start_time) / 1000.0
    }

func _get_average(array: Array) -> float:
    if array.size() == 0:
        return 0.0
    var total = 0.0
    for val in array:
        total += val
    return total / array.size()

func _sum(array: Array) -> float:
    var total = 0.0
    for val in array:
        total += val
    return total

func print_stats():
    # 打印统计
    var current = get_current_stats()
    print("Network Performance Stats:")
    print("- Average RTT: ", current.average_rtt, " ms")
    print("- Avg Bandwidth Sent: ", current.average_bandwidth_sent / 1000, " kbps")
    print("- Avg Bandwidth Received: ", current.average_bandwidth_received / 1000, " kbps")
    print("- Average Jitter: ", current.average_jitter, " ms")
    print("- Average Packet Loss: ", current.average_packet_loss * 100.0, " %")
    print("- Session Duration: ", current.session_duration, " s")
```

> ⚠️ **指标来源说明（不是所有指标都能"自动拿到"）**
>
> | 指标 | 来源 | 能否由引擎直接提供 |
> |------|------|------------------|
> | 带宽（收 / 发） | 应用层在每次 `put_packet()` 前记字节数 | 否，需自己埋点 |
> | RTT | 应用层 ping/pong 的时间戳差 | 否，需自己埋点 |
> | 抖动 | 由 RTT 序列派生 | 否，依赖 RTT |
> | 丢包率 | 应用层序号缺口 | 否，需自己埋点 |
>
> Godot 的 `MultiplayerPeer` **没有**暴露 RTT、丢包率或带宽统计接口；ENet 内部有 `HOST_TOTAL_SENT_DATA` 等统计，但 `ENetMultiplayerPeer` 没有把它们暴露到脚本层。因此上表中的埋点是必需的，不是可选的。RTT 的 ping/pong 实现见第 51 篇 §4.1。

### 1.3 性能分析工具

```gdscript
# 网络性能分析工具
class_name NetworkProfiler

extends Node

var profile_data: Dictionary = {}

func start_profile(profile_name: String):
    # 开始分析
    profile_data[profile_name] = {
        "start_time": Time.get_ticks_usec(),
        "packets_sent": 0,
        "bytes_sent": 0,
        "packets_received": 0,
        "bytes_received": 0
    }

func end_profile(profile_name: String) -> Dictionary:
    # 结束分析
    if profile_data.has(profile_name):
        var data = profile_data[profile_name]
        var duration_us = Time.get_ticks_usec() - data.start_time
        
        var result = {
            "duration_ms": duration_us / 1000.0,
            "packets_sent": data.packets_sent,
            "bytes_sent": data.bytes_sent,
            "packets_received": data.packets_received,
            "bytes_received": data.bytes_received,
            "throughput_kbps": (data.bytes_sent * 8) / duration_us if duration_us > 0 else 0
        }
        
        profile_data.erase(profile_name)
        return result
    
    return {}

func record_packet_sent(profile_name: String, bytes: int):
    if profile_data.has(profile_name):
        profile_data[profile_name].packets_sent += 1
        profile_data[profile_name].bytes_sent += bytes

func record_packet_received(profile_name: String, bytes: int):
    if profile_data.has(profile_name):
        profile_data[profile_name].packets_received += 1
        profile_data[profile_name].bytes_received += bytes

func compare_profiles(profile1: Dictionary, profile2: Dictionary) -> Dictionary:
    # 比较两个分析结果
    return {
        "duration_diff": profile1.duration_ms - profile2.duration_ms,
        "throughput_diff": profile1.throughput_kbps - profile2.throughput_kbps,
        "packets_diff": profile1.packets_sent - profile2.packets_sent
    }
```

---

## 2. 带宽优化

### 2.1 数据压缩

> 压缩标记字节的**线格式约定**（flag 取值、两端必须一致的三条规则）见第 50 篇《网络通信协议》§5.1；本节只讲运行时的压缩策略（阈值、回退、收益核算）。

```gdscript
# 数据压缩优化
class_name BandwidthCompression

static func compress_data(data: PackedByteArray, threshold: int = 100) -> PackedByteArray:
    # 压缩数据（仅当数据大于阈值）
    if data.size() < threshold:
        return data
    
    var compressed = data.compress(FileAccess.COMPRESSION_DEFLATE)
    
    # 如果压缩后更大，返回原数据
    if compressed.size() >= data.size():
        return data
    
    # 添加压缩标记
    var result = PackedByteArray()
    result.append(0x01)  # 压缩标记
    result.append_array(compressed)
    return result

static func decompress_data(data: PackedByteArray) -> PackedByteArray:
    # 解压数据
    if data.size() == 0:
        return data
    
    if data[0] == 0x01:
        return data.slice(1).decompress_dynamic(-1, FileAccess.COMPRESSION_DEFLATE)
    
    return data

static func get_compression_ratio(original: PackedByteArray, compressed: PackedByteArray) -> float:
    # 获取压缩率
    if original.size() == 0:
        return 0.0
    return 1.0 - (float(compressed.size()) / float(original.size()))

static func compress_variant(data: Variant, threshold: int = 100) -> PackedByteArray:
    # 压缩变体数据
    var raw = var_to_bytes(data)
    return compress_data(raw, threshold)

static func decompress_variant(data: PackedByteArray) -> Variant:
    # 解压变体数据
    var raw = decompress_data(data)
    return bytes_to_var(raw)
```

### 2.2 数据序列化优化

> 底层的定长编码工具类是第 50 篇《网络通信协议》§5.2 的 **`ProtocolSerialization`**（全卷公共工具类，固定字节序与字段顺序）。本节的 `SerializationOptimizer` 是它的**可调精度变体**：按精度档位选择 1 / 2 / 4 字节每分量，两者共享同一套字段顺序约定，可以互相替换。

```gdscript
# 数据序列化优化
class_name SerializationOptimizer

static func pack_vector3(v: Vector3, precision: int = 2) -> PackedByteArray:
    # 打包 Vector3（可调整精度）
    var data = PackedByteArray()
    
    match precision:
        0:  # 低精度（1 字节每分量）
            data.append(clamp(int(v.x * 127), -128, 127) + 128)
            data.append(clamp(int(v.y * 127), -128, 127) + 128)
            data.append(clamp(int(v.z * 127), -128, 127) + 128)
        1:  # 中精度（2 字节每分量）
            data.append_array(_encode_float16(v.x))
            data.append_array(_encode_float16(v.y))
            data.append_array(_encode_float16(v.z))
        2:  # 高精度（4 字节每分量）
            data.append_array(_encode_float(v.x))
            data.append_array(_encode_float(v.y))
            data.append_array(_encode_float(v.z))
    
    return data

static func unpack_vector3(data: PackedByteArray, precision: int = 2) -> Vector3:
    # 解包 Vector3
    match precision:
        0:
            if data.size() < 3:
                return Vector3.ZERO
            var x = (data[0] - 128) / 127.0
            var y = (data[1] - 128) / 127.0
            var z = (data[2] - 128) / 127.0
            return Vector3(x, y, z)
        1:
            if data.size() < 6:
                return Vector3.ZERO
            var x = _decode_float16(data.slice(0, 2))
            var y = _decode_float16(data.slice(2, 4))
            var z = _decode_float16(data.slice(4, 6))
            return Vector3(x, y, z)
        2:
            if data.size() < 12:
                return Vector3.ZERO
            var x = _decode_float(data.slice(0, 4))
            var y = _decode_float(data.slice(4, 8))
            var z = _decode_float(data.slice(8, 12))
            return Vector3(x, y, z)
    
    return Vector3.ZERO

static func pack_rotation(rot: Quaternion) -> PackedByteArray:
    # 打包旋转（使用最小表示）
    # 四元数可以用 3 个 float 表示（第 4 个可以计算出来）
    var data = PackedByteArray()
    
    # 确保 w 为正（最小表示）
    if rot.w < 0:
        rot = Quaternion(-rot.x, -rot.y, -rot.z, -rot.w)
    
    # 只存储 x, y, z（w 可以计算）
    data.append_array(_encode_float(rot.x))
    data.append_array(_encode_float(rot.y))
    data.append_array(_encode_float(rot.z))
    
    return data

static func unpack_rotation(data: PackedByteArray) -> Quaternion:
    # 解包旋转
    if data.size() < 12:
        return Quaternion.IDENTITY
    
    var x = _decode_float(data.slice(0, 4))
    var y = _decode_float(data.slice(4, 8))
    var z = _decode_float(data.slice(8, 12))
    
    # 计算 w
    var w = sqrt(max(0.0, 1.0 - x * x - y * y - z * z))
    
    return Quaternion(x, y, z, w)

static func _encode_float(value: float) -> PackedByteArray:
    var data = PackedByteArray()
    data.resize(4)
    data.encode_float(0, value)
    return data

static func _decode_float(data: PackedByteArray) -> float:
    return data.decode_float(0)

static func _encode_float16(value: float) -> PackedByteArray:
    # 编码半精度 float（简化版）
    var data = PackedByteArray()
    data.resize(2)
    
    # 简化：只存储 16 位整数表示
    var int_val = clamp(int(value * 1000), -32768, 32767)
    data[0] = int_val & 0xFF
    data[1] = (int_val >> 8) & 0xFF
    
    return data

static func _decode_float16(data: PackedByteArray) -> float:
    # 解码半精度 float
    if data.size() < 2:
        return 0.0
    
    var int_val = data[0] | (data[1] << 8)
    if int_val > 32767:
        int_val -= 65536
    
    return float(int_val) / 1000.0
```

### 2.3 增量更新

```gdscript
# 增量更新
class_name DeltaUpdate

static func calculate_delta(old_state: Dictionary, new_state: Dictionary) -> Dictionary:
    # 计算增量
    var delta = {}
    
    for key in new_state:
        if not old_state.has(key):
            delta[key] = {"op": "add", "v": new_state[key]}
        elif old_state[key] != new_state[key]:
            delta[key] = {"op": "update", "v": new_state[key]}
    
    for key in old_state:
        if not new_state.has(key):
            delta[key] = {"op": "remove"}
    
    return delta

static func apply_delta(state: Dictionary, delta: Dictionary) -> Dictionary:
    # 应用增量
    var result = state.duplicate(true)
    
    for key in delta:
        match delta[key].op:
            "add":
                result[key] = delta[key].v
            "update":
                result[key] = delta[key].v
            "remove":
                result.erase(key)
    
    return result

static func calculate_position_delta(old_pos: Vector3, new_pos: Vector3, threshold: float = 0.01) -> Dictionary:
    # 计算位置增量（带阈值）
    var diff = new_pos - old_pos
    
    if diff.length() < threshold:
        return {}  # 变化太小，不发送
    
    return {"dx": diff.x, "dy": diff.y, "dz": diff.z}

static func apply_position_delta(pos: Vector3, delta: Dictionary) -> Vector3:
    # 应用位置增量
    if delta.is_empty():
        return pos
    
    return Vector3(
        pos.x + delta.get("dx", 0),
        pos.y + delta.get("dy", 0),
        pos.z + delta.get("dz", 0)
    )
```

---

## 3. 延迟优化

### 3.1 连接优化

```gdscript
# 连接优化
class_name ConnectionOptimizer

static func optimize_tcp_connection(tcp: StreamPeerTCP):
    # 优化 TCP 连接
    tcp.set_no_delay(true)  # 禁用 Nagle 算法

static func get_best_server(servers: Array) -> Dictionary:
    # 选择最佳服务器（基于 Ping）
    var best_server = null
    var best_rtt = INF
    
    for server in servers:
        var rtt = _measure_ping(server.ip, server.port)
        if rtt < best_rtt:
            best_rtt = rtt
            best_server = server
    
    return best_server if best_server else {}

static func _measure_ping(ip: String, port: int) -> float:
    # 测量 Ping（简化版）
    var start_time = Time.get_ticks_msec()
    
    var tcp = StreamPeerTCP.new()
    tcp.connect_to_host(ip, port)
    
    var timeout = 5000  # 5 秒超时
    while tcp.get_status() == StreamPeerTCP.STATUS_CONNECTING:
        tcp.poll()
        if Time.get_ticks_msec() - start_time > timeout:
            return INF
    
    if tcp.get_status() == StreamPeerTCP.STATUS_CONNECTED:
        var rtt = Time.get_ticks_msec() - start_time
        tcp.disconnect_from_host()
        return rtt
    
    return INF
```

### 3.2 预测优化

```gdscript
# 预测优化
class_name PredictionOptimizer

var prediction_history: Array = []
var max_history: int = 20

func record_prediction(predicted: Vector3, actual: Vector3):
    # 记录预测误差
    var error = predicted.distance_to(actual)
    prediction_history.append(error)
    
    if prediction_history.size() > max_history:
        prediction_history.pop_front()

func get_average_prediction_error() -> float:
    # 获取平均预测误差
    if prediction_history.size() == 0:
        return 0.0
    
    var total = 0.0
    for error in prediction_history:
        total += error
    
    return total / prediction_history.size()

func should_increase_prediction_smoothness() -> bool:
    # 是否应该增加预测平滑度
    return get_average_prediction_error() > 1.0

func should_decrease_prediction_smoothness() -> bool:
    # 是否应该减少预测平滑度
    return get_average_prediction_error() < 0.1

func get_optimal_prediction_factor() -> float:
    # 获取最佳预测因子
    var avg_error = get_average_prediction_error()
    
    if avg_error > 1.0:
        return 0.5  # 减少预测
    elif avg_error < 0.1:
        return 1.5  # 增加预测
    else:
        return 1.0
```

### 3.3 插值优化

```gdscript
# 插值优化
class_name InterpolationOptimizer

@export var default_buffer_time_ms: int = 100
@export var min_buffer_time_ms: int = 50
@export var max_buffer_time_ms: int = 200

var current_buffer_time: int = default_buffer_time_ms
var rtt_history: Array = []

func update_rtt(rtt_ms: float):
    # 更新 RTT
    rtt_history.append(rtt_ms)
    if rtt_history.size() > 60:
        rtt_history.pop_front()
    
    # 调整缓冲时间
    _adjust_buffer_time()

func _adjust_buffer_time():
    # 调整缓冲时间
    var avg_rtt = _get_average_rtt()
    var jitter = _get_jitter()
    
    # 缓冲时间 = 平均 RTT/2 + 抖动
    var target_buffer = int(avg_rtt / 2 + jitter * 2)
    target_buffer = clamp(target_buffer, min_buffer_time_ms, max_buffer_time_ms)
    
    # 平滑调整
    current_buffer_time = lerp(current_buffer_time, target_buffer, 0.1)

func _get_average_rtt() -> float:
    if rtt_history.size() == 0:
        return 0.0
    
    var total = 0.0
    for rtt in rtt_history:
        total += rtt
    
    return total / rtt_history.size()

func _get_jitter() -> float:
    if rtt_history.size() < 2:
        return 0.0
    
    var avg = _get_average_rtt()
    var sum_diff = 0.0
    for rtt in rtt_history:
        sum_diff += abs(rtt - avg)
    
    return sum_diff / rtt_history.size()

func get_buffer_time() -> int:
    return current_buffer_time

func get_interpolation_t(snapshot1_time: int, snapshot2_time: int, current_time: int) -> float:
    # 获取插值 t 值
    var target_time = current_time - current_buffer_time
    
    if snapshot2_time == snapshot1_time:
        return 0.0
    
    return float(target_time - snapshot1_time) / float(snapshot2_time - snapshot1_time)
```

---

## 4. 同步优化

### 4.1 优先级同步

```gdscript
# 优先级同步
class_name PrioritySyncOptimizer

extends Node

@export var priority_levels: int = 3
@export var sync_rates: Array = [60.0, 30.0, 10.0]  # 高、中、低

var priority_queues: Array = []
var sync_timers: Array = []

func _ready():
    # 初始化优先级队列
    for i in range(priority_levels):
        priority_queues.append([])
        sync_timers.append(0.0)

func _process(delta):
    # 处理每个优先级
    for i in range(priority_levels):
        sync_timers[i] += delta
        
        var sync_interval = 1.0 / sync_rates[i]
        if sync_timers[i] >= sync_interval:
            sync_timers[i] = 0.0
            _sync_priority(i)

func add_to_sync(object: Node, priority: int):
    # 添加到同步队列
    priority = clamp(priority, 0, priority_levels - 1)
    
    # 从所有队列移除
    _remove_from_all_queues(object)
    
    # 添加到指定优先级队列
    priority_queues[priority].append(object)

func _remove_from_all_queues(object: Node):
    # 从所有队列移除
    for queue in priority_queues:
        queue.erase(object)

func _sync_priority(priority: int):
    # 同步指定优先级
    for object in priority_queues[priority]:
        if is_instance_valid(object):
            _sync_object(object, priority)

func _sync_object(object: Node, priority: int):
    # 同步对象
    pass

func set_sync_rate(priority: int, rate: float):
    # 设置同步率
    if priority >= 0 and priority < priority_levels:
        sync_rates[priority] = rate
```

### 4.2 区域同步

```gdscript
# 区域同步
class_name ZoneSyncOptimizer

extends Node

@export var view_distance: float = 100.0
@export var sync_rate_near: float = 60.0
@export var sync_rate_far: float = 10.0
@export var near_distance: float = 30.0

var camera: Camera3D
var synced_objects: Dictionary = {}  # object -> last_sync_time

func _ready():
    camera = get_viewport().get_camera_3d()

func _process(delta):
    if not camera:
        return
    
    var camera_pos = camera.global_transform.origin
    var current_time = Time.get_ticks_msec()
    
    # 更新所有对象的同步
    for object in synced_objects:
        if is_instance_valid(object):
            var distance = object.global_transform.origin.distance_to(camera_pos)
            var last_sync = synced_objects[object]
            
            # 根据距离决定同步率
            var should_sync = false
            if distance < near_distance:
                if current_time - last_sync >= 1000.0 / sync_rate_near:
                    should_sync = true
            elif distance < view_distance:
                if current_time - last_sync >= 1000.0 / sync_rate_far:
                    should_sync = true
            
            if should_sync:
                _sync_object(object)
                synced_objects[object] = current_time

func add_object(object: Node):
    # 添加对象到同步
    synced_objects[object] = 0

func remove_object(object: Node):
    # 移除对象
    synced_objects.erase(object)

func _sync_object(object: Node):
    # 同步对象
    pass
```

### 4.3 兴趣管理

```gdscript
# 兴趣管理
class_name InterestManager

extends Node

var interested_objects: Dictionary = {}  # object -> interest_level
var camera: Camera3D

func _ready():
    camera = get_viewport().get_camera_3d()

func _process(delta):
    _update_interest_levels()

func _update_interest_levels():
    # 更新兴趣等级
    if not camera:
        return
    
    var camera_pos = camera.global_transform.origin
    var camera_dir = -camera.global_transform.basis.z
    
    for object in interested_objects:
        if is_instance_valid(object):
            var interest = _calculate_interest(object, camera_pos, camera_dir)
            interested_objects[object] = interest

func _calculate_interest(object: Node, camera_pos: Vector3, camera_dir: Vector3) -> float:
    # 计算兴趣等级（0-1）
    var object_pos = object.global_transform.origin
    var to_object = object_pos - camera_pos
    var distance = to_object.length()
    
    # 距离因子（越近兴趣越高）
    var distance_factor = 1.0 - clamp(distance / 100.0, 0.0, 1.0)
    
    # 方向因子（在视野内兴趣高）
    var direction_factor = 0.5
    if distance > 0:
        var angle = camera_dir.dot(to_object.normalized())
        direction_factor = clamp(angle + 0.5, 0.0, 1.0)
    
    # 综合兴趣
    return distance_factor * 0.7 + direction_factor * 0.3

func get_sync_rate(object: Node) -> float:
    # 根据兴趣获取同步率
    var interest = interested_objects.get(object, 0.5)
    
    # 兴趣越高，同步率越高
    return lerp(10.0, 60.0, interest)

func add_object(object: Node):
    interested_objects[object] = 0.5

func remove_object(object: Node):
    interested_objects.erase(object)
```

---

## 5. 实践：完整网络优化系统

### 5.1 优化管理器

```gdscript
# 优化管理器
class_name NetworkOptimizationManager

extends Node

var performance_monitor: NetworkBandwidthMonitor
var compression: BandwidthCompression
var connection_optimizer: ConnectionOptimizer
var prediction_optimizer: PredictionOptimizer
var interpolation_optimizer: InterpolationOptimizer
var priority_sync: PrioritySyncOptimizer
var zone_sync: ZoneSyncOptimizer
var interest_manager: InterestManager

func _ready():
    performance_monitor = NetworkBandwidthMonitor.new()
    add_child(performance_monitor)
    
    compression = BandwidthCompression.new()
    
    connection_optimizer = ConnectionOptimizer.new()
    
    prediction_optimizer = PredictionOptimizer.new()
    add_child(prediction_optimizer)
    
    interpolation_optimizer = InterpolationOptimizer.new()
    add_child(interpolation_optimizer)
    
    priority_sync = PrioritySyncOptimizer.new()
    add_child(priority_sync)
    
    zone_sync = ZoneSyncOptimizer.new()
    add_child(zone_sync)
    
    interest_manager = InterestManager.new()
    add_child(interest_manager)
    
    # 连接信号
    performance_monitor.stats_updated.connect(_on_stats_updated)

func _on_stats_updated(stats: Dictionary):
    # 根据统计调整优化
    _adjust_optimizations(stats)

func _adjust_optimizations(stats: Dictionary):
    # 根据统计调整优化
    var avg_rtt = stats.average_rtt
    var avg_jitter = stats.average_jitter
    
    # 高延迟时增加缓冲
    if avg_rtt > 150:
        interpolation_optimizer.current_buffer_time = 150
    elif avg_rtt < 50:
        interpolation_optimizer.current_buffer_time = 50
    
    # 高抖动时降低同步率
    if avg_jitter > 50:
        priority_sync.sync_rates = [30.0, 15.0, 5.0]
    elif avg_jitter < 10:
        priority_sync.sync_rates = [60.0, 30.0, 10.0]

func get_optimization_stats() -> Dictionary:
    # 获取优化统计
    return {
        "performance": performance_monitor.get_current_stats(),
        "prediction_error": prediction_optimizer.get_average_prediction_error(),
        "buffer_time": interpolation_optimizer.get_buffer_time(),
        "sync_rates": priority_sync.sync_rates
    }

func print_optimization_report():
    # 打印优化报告
    var stats = get_optimization_stats()
    print("Network Optimization Report:")
    print("- Average RTT: ", stats.performance.average_rtt, " ms")
    print("- Average Jitter: ", stats.performance.average_jitter, " ms")
    print("- Prediction Error: ", stats.prediction_error)
    print("- Buffer Time: ", stats.buffer_time, " ms")
    print("- Sync Rates: ", stats.sync_rates)
```

### 5.2 多人游戏优化

```gdscript
# 多人游戏优化
class_name MultiplayerOptimization

extends NetworkOptimizationManager

@export var max_players: int = 32
@export var player_priority: int = 0  # 最高优先级
@export var prop_priority: int = 1    # 中优先级
@export var environment_priority: int = 2  # 低优先级

func _ready():
    super._ready()

func register_player(player: Node):
    # 注册玩家（高优先级）
    priority_sync.add_to_sync(player, player_priority)
    interest_manager.add_object(player)

func register_prop(prop: Node):
    # 注册道具（中优先级）
    priority_sync.add_to_sync(prop, prop_priority)
    interest_manager.add_object(prop)

func register_environment(env: Node):
    # 注册环境（低优先级）
    priority_sync.add_to_sync(env, environment_priority)

func unregister_object(object: Node):
    # 注销对象
    priority_sync._remove_from_all_queues(object)
    interest_manager.remove_object(object)

func optimize_for_player_count(player_count: int):
    # 根据玩家数量优化
    if player_count > 20:
        # 多玩家时降低同步率
        priority_sync.sync_rates = [30.0, 15.0, 5.0]
    elif player_count > 10:
        priority_sync.sync_rates = [45.0, 20.0, 8.0]
    else:
        priority_sync.sync_rates = [60.0, 30.0, 10.0]
```

### 5.3 FPS 游戏优化

```gdscript
# FPS 游戏优化
class_name FPSOptimization

extends MultiplayerOptimization

@export var hitbox_sync_rate: float = 60.0
@export var player_model_sync_rate: float = 30.0
@export var projectile_sync_rate: float = 60.0

func _ready():
    super._ready()

func register_player_with_hitbox(player: Node, hitbox: Node):
    # 注册玩家和命中框
    register_player(player)
    
    # 命中框使用最高同步率
    priority_sync.add_to_sync(hitbox, player_priority)

func register_projectile(projectile: Node):
    # 注册抛射物
    priority_sync.add_to_sync(projectile, player_priority)

func optimize_for_latency(latency_ms: float):
    # 根据延迟优化
    if latency_ms > 100:
        # 高延迟：启用延迟补偿
        hitbox_sync_rate = 60.0  # 保持命中框高同步率
        player_model_sync_rate = 20.0  # 降低模型同步率
    else:
        hitbox_sync_rate = 60.0
        player_model_sync_rate = 30.0
    
    priority_sync.sync_rates = [hitbox_sync_rate, player_model_sync_rate, projectile_sync_rate]
```

### 5.4 传输层加密与安全边界

这一节回答一个常被忽略的问题：**你的游戏数据在网络上长什么样**。

#### 5.4.1 各传输层默认是否加密

| 传输层 | 载荷是否加密 | 说明 |
|--------|--------------|------|
| `ENetMultiplayerPeer` | **默认否** | ENet 的 UDP 载荷是明文；RPC 的序列化结果也是明文 |
| `WebSocketMultiplayerPeer`（`ws://`） | **否** | 明文 WebSocket |
| `WebSocketMultiplayerPeer`（`wss://`） | **是** | 由 TLS 提供，证书校验走 `TLSOptions` |
| `WebRTCMultiplayerPeer` | **是** | WebRTC DataChannel 使用 DTLS-SRTP，强制加密 |
| Godot 4 的高层多人 API（`MultiplayerAPI` / `SceneMultiplayer`） | **不提供应用层加密** | RPC 载荷按 `var_to_bytes` 等方式序列化后直接发出 |

也就是说：**Godot 4 的高层多人 API 不提供任何应用层加密**。`SceneMultiplayer` 只负责路由与序列化，通道之上是否有 TLS，完全取决于你选的 `MultiplayerPeer` 与它连接的 URL 协议。

#### 5.4.2 ENet 的 DTLS（4.3 起可用，但有前提）

Godot 内置的 ENet（打了补丁的 `GODOT_ENET` 构建）带有 DTLS 支持，可以通过 `ENetConnection` 打开：

```gdscript
# ENet + DTLS（需要 Godot 内置的 ENet 构建）
var peer := ENetMultiplayerPeer.new()
peer.create_server(9999)
# create_server() 之后、连接建立之前，用 host 设置 DTLS。
# 注意：4.3 的 TLSOptions 只有 client() / client_unsafe() / server(key, certificate)，
# 没有 server_unsafe()——服务端必须提供自己的私钥与证书链。
var key := load("res://certs/server.key")          # CryptoKey
var cert := load("res://certs/server.crt")         # X509Certificate
var tls_options := TLSOptions.server(key, cert)
# ENetMultiplayerPeer 上取底层连接用 get_peer()（返回 ENetConnection），
# 没有 get_host() 方法。
var err := peer.get_peer().dtls_server_setup(tls_options)
if err != OK:
    push_error("DTLS 设置失败：%d" % err)
multiplayer.multiplayer_peer = peer
```

客户端侧对应 `peer.get_peer().dtls_client_setup(hostname, client_options)`。

**前提与限制**：

- 必须是 **Godot 自带的 ENet 构建**。用系统 vanilla ENet 编译的引擎上，这两个方法返回 `ERR_UNAVAILABLE`。
- `dtls_client_setup()` 需要**域名**（用于证书校验），不能直接用 IP。
- 必须在 `create_server()` / `create_client()` **之后**调用（此时 host 才存在），且要在连接真正建立**之前**完成。
- DTLS 会在握手阶段增加往返与握手字节，弱网环境下的连接建立时间会明显变长。

> 📌 选型建议：需要加密的**浏览器客户端**用 `wss://`（最省事，TLS 由浏览器与服务器处理）；需要加密的**原生客户端**可以用 ENet + DTLS；如果两端都由你控制，也可以自己在应用层做对称加密（把密文当作 `PackedByteArray` 传），但要自己处理密钥协商与重放保护。

#### 5.4.3 RPC 不是可信通道

这是本章最该记住的一条：**"消息是从服务器发来的"不等于"消息是真的"**。

- `@rpc("any_peer", ...)` 的接口，**任何**连上的客户端都能调用，参数随便填。服务器收到后如果直接采信，就等于把权限交出去了。
- `@rpc("authority", ...)` 只保证**调用者**是权威端，不保证**参数**没被改——权威端自己发出的数据被中间人篡改，同样是问题（这就是需要 TLS 的原因）。
- 客户端本地内存里的游戏状态、货币、伤害值，攻击者可以直接改内存绕过所有客户端逻辑。

**因此**：任何影响游戏结果的数据（位置、伤害、命中、掉落、货币）都必须**由服务器重算**，客户端上报的只能当作"请求"而不是"事实"。可伪造什么、必须重算什么，见第 57 篇《权威服务器架构》§5 的反作弊边界。

**加密解决的是"路上被偷看/被改写"，解决不了"对端自己就是攻击者"**。这两件事必须分开处理：前者用 TLS / DTLS，后者用服务器权威校验。

---

## 📝 本章总结

### 核心要点

1. **性能分析是优化的基础**，监控关键指标
2. **数据压缩减少带宽**，但增加 CPU 开销
3. **序列化优化减少包大小**，精度换带宽
4. **增量更新只发送变化**，大幅减少数据量
5. **延迟优化提升响应**，预测和插值是关键
6. **同步优化平衡性能和准确性**，优先级和区域同步

### 关键术语

| 术语 | 解释 |
|------|------|
| Bandwidth | 带宽，数据传输速率 |
| Latency | 延迟，数据传输时间 |
| Compression | 压缩，减少数据大小 |
| Delta Update | 增量更新，只发送变化 |
| Prediction | 预测，预判未来状态 |
| Interpolation | 插值，平滑状态过渡 |
| Priority Sync | 优先级同步，重要对象优先 |
| Interest Management | 兴趣管理，根据兴趣同步 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Network Optimization](https://docs.godotengine.org/en/stable/tutorials/networking/optimization.html)
- **Gaffer On Games**: 网络优化系列文章
- **Valve Source Networking**: Source 引擎优化实践

---

## 📋 下一章预告

**第 53 篇：输入系统**

- 输入系统基础
- 输入映射
- 输入处理
- 输入优化

---

*写作时间：2026-03-20*  
*字数：约 1,700 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*  

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）


**上一篇**: [第 51 篇：网络同步](/articles/51-network-synchronization.md)
**下一篇**: [第 54 篇：脚本系统](/articles/54-script-system.md)
---

*最后更新：2026-03-20 20:00*
