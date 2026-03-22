# 第 41 篇：网络同步

> **本卷定位**: 第六卷 网络系统（8 篇）  
> **前置知识**: 第 50 章 网络通信协议  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

网络同步是多人游戏开发中最具挑战性的技术领域之一。如何在网络延迟、丢包、乱序等不利条件下，保持所有玩家看到的游戏状态一致，是网络同步的核心问题。

本章将深入探讨状态同步、输入同步、延迟补偿、预测和回滚等关键同步技术，以及如何在 Godot 中实现这些技术。

---

## 🎯 学习目标

- 理解网络同步的基本概念
- 掌握状态同步技术
- 学会输入同步方法
- 熟悉延迟补偿技术
- 掌握预测和回滚机制
- 掌握网络同步优化

---

## 1. 网络同步基础

### 1.1 同步类型

```
网络同步类型:
┌─────────────────────────────────────────────────────────────┐
│                      网络同步类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 状态同步：同步游戏状态                                 │
│  2. 输入同步：同步玩家输入                                 │
│  3. 帧同步：同步游戏帧                                     │
│  4. 快照同步：同步状态快照                                 │
│  5. 增量同步：同步状态变化                                 │
│  6. 预测同步：预测未来状态                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 同步架构

```
网络同步架构:
┌─────────────────────────────────────────────────────────────┐
│                      网络同步架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 客户端 - 服务器（C/S）：中心化架构                     │
│     - 权威服务器：服务器是权威状态                         │
│     - 监听客户端：客户端只是显示                           │
│                                                             │
│  2. 对等网络（P2P）：去中心化架构                          │
│     - 完全 P2P：所有节点平等                               │
│     - 主机 - 客户端：一个节点是主机                        │
│                                                             │
│  3. 混合架构：结合 C/S 和 P2P                              │
│     - 服务器权威 + 客户端预测                              │
│     - 服务器验证 + 客户端执行                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 同步问题

```
常见同步问题:
┌─────────────────────────────────────────────────────────────┐
│                      常见同步问题                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 延迟（Latency）：数据传输时间                          │
│  2. 抖动（Jitter）：延迟变化                               │
│  3. 丢包（Packet Loss）：数据丢失                          │
│  4. 乱序（Out of Order）：数据顺序错乱                     │
│  5. 不同步（Desync）：状态不一致                           │
│  6. 作弊（Cheating）：客户端篡改                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 状态同步

### 2.1 基础状态同步

```gdscript
# 基础状态同步
class_name BasicStateSynchronizer

extends Node

@export var sync_rate: float = 20.0  # 20Hz
var sync_timer: float = 0.0
var local_state: Dictionary = {}
var remote_state: Dictionary = {}

signal state_synced(state: Dictionary)

func _process(delta):
    if multiplayer.is_server():
        # 服务器：广播状态
        sync_timer += delta
        if sync_timer >= 1.0 / sync_rate:
            sync_timer = 0.0
            _broadcast_state()
    else:
        # 客户端：接收状态
        _interpolate_state(delta)

func _broadcast_state():
    # 广播状态
    local_state = _get_game_state()
    _sync_state.rpc(local_state)

@rpc("any_peer", "unreliable")
func _sync_state(state: Dictionary):
    # 同步状态
    remote_state = state
    state_synced.emit(state)

func _get_game_state() -> Dictionary:
    # 获取游戏状态
    return {
        "players": _get_player_states(),
        "timestamp": Time.get_ticks_msec()
    }

func _get_player_states() -> Array:
    # 获取玩家状态
    var states = []
    # 收集所有玩家状态
    return states

func _interpolate_state(delta):
    # 插值状态（平滑显示）
    pass
```

### 2.2 增量状态同步

```gdscript
# 增量状态同步
class_name DeltaStateSynchronizer

extends Node

@export var sync_rate: float = 30.0
var sync_timer: float = 0.0
var previous_state: Dictionary = {}
var current_state: Dictionary = {}

signal delta_synced(delta: Dictionary)

func _process(delta):
    if multiplayer.is_server():
        sync_timer += delta
        if sync_timer >= 1.0 / sync_rate:
            sync_timer = 0.0
            _broadcast_delta()

func _broadcast_delta():
    # 广播增量
    current_state = _get_game_state()
    var delta = _calculate_delta(previous_state, current_state)
    
    if delta.size() > 0:
        _sync_delta.rpc(delta)
        previous_state = current_state.duplicate(true)

@rpc("any_peer", "unreliable")
func _sync_delta(delta: Dictionary):
    # 同步增量
    current_state = _apply_delta(current_state, delta)
    delta_synced.emit(delta)

func _calculate_delta(old_state: Dictionary, new_state: Dictionary) -> Dictionary:
    # 计算增量
    var delta = {}
    
    for key in new_state:
        if not old_state.has(key):
            delta[key] = {"action": "add", "value": new_state[key]}
        elif old_state[key] != new_state[key]:
            delta[key] = {"action": "update", "value": new_state[key]}
    
    for key in old_state:
        if not new_state.has(key):
            delta[key] = {"action": "remove"}
    
    return delta

func _apply_delta(state: Dictionary, delta: Dictionary) -> Dictionary:
    # 应用增量
    var result = state.duplicate(true)
    
    for key in delta:
        match delta[key].action:
            "add":
                result[key] = delta[key].value
            "update":
                result[key] = delta[key].value
            "remove":
                result.erase(key)
    
    return result

func _get_game_state() -> Dictionary:
    return {
        "players": _get_player_states(),
        "timestamp": Time.get_ticks_msec()
    }

func _get_player_states() -> Array:
    return []
```

### 2.3 快照同步

```gdscript
# 快照同步
class_name SnapshotSynchronizer

extends Node

@export var snapshot_rate: float = 60.0
@export var max_snapshots: int = 60

var snapshots: Array = []  # 快照队列
var snapshot_timer: float = 0.0

signal snapshot_received(snapshot: Dictionary)

func _process(delta):
    if multiplayer.is_server():
        snapshot_timer += delta
        if snapshot_timer >= 1.0 / snapshot_rate:
            snapshot_timer = 0.0
            _create_snapshot()
    else:
        _process_snapshots(delta)

func _create_snapshot():
    # 创建快照
    var snapshot = {
        "sequence": snapshots.size(),
        "timestamp": Time.get_ticks_msec(),
        "state": _get_game_state()
    }
    
    snapshots.append(snapshot)
    
    # 限制快照数量
    if snapshots.size() > max_snapshots:
        snapshots.pop_front()
    
    # 发送快照
    _send_snapshot.rpc(snapshot)

@rpc("any_peer", "unreliable")
func _send_snapshot(snapshot: Dictionary):
    # 发送快照
    _store_snapshot(snapshot)

func _store_snapshot(snapshot: Dictionary):
    # 存储快照
    snapshots.append(snapshot)
    
    # 限制快照数量
    if snapshots.size() > max_snapshots:
        snapshots.pop_front()
    
    snapshot_received.emit(snapshot)

func _process_snapshots(delta):
    # 处理快照（插值/外推）
    if snapshots.size() >= 2:
        var current_time = Time.get_ticks_msec()
        var target_time = current_time - 100  # 100ms 延迟缓冲
        
        # 找到合适的快照
        var snapshot1 = snapshots[0]
        var snapshot2 = snapshots[1]
        
        for i in range(snapshots.size() - 1):
            if snapshots[i].timestamp <= target_time and snapshots[i + 1].timestamp >= target_time:
                snapshot1 = snapshots[i]
                snapshot2 = snapshots[i + 1]
                break
        
        # 插值
        var t = float(target_time - snapshot1.timestamp) / float(snapshot2.timestamp - snapshot1.timestamp)
        var interpolated_state = _interpolate_states(snapshot1.state, snapshot2.state, t)
        
        # 应用状态
        _apply_state(interpolated_state)

func _interpolate_states(state1: Dictionary, state2: Dictionary, t: float) -> Dictionary:
    # 插值状态
    var result = {}
    
    for key in state1:
        if state1[key] is Vector3 and state2.has(key):
            result[key] = state1[key].lerp(state2[key], t)
        elif state1[key] is float and state2.has(key):
            result[key] = lerp(state1[key], state2[key], t)
        elif state1[key] is Quaternion and state2.has(key):
            result[key] = state1[key].slerp(state2[key], t)
        else:
            result[key] = state1[key]
    
    return result

func _apply_state(state: Dictionary):
    # 应用状态
    pass

func _get_game_state() -> Dictionary:
    return {}
```

---

## 3. 输入同步

### 3.1 基础输入同步

```gdscript
# 基础输入同步
class_name BasicInputSynchronizer

extends Node

var local_inputs: Array = []
var remote_inputs: Array = []
var input_sequence: int = 0

signal input_received(input: Dictionary)

func _process(delta):
    # 收集本地输入
    _collect_local_input()
    
    # 发送输入
    if multiplayer.is_server():
        _broadcast_input()
    else:
        _send_input_to_server()
    
    # 处理远程输入
    _process_remote_inputs()

func _collect_local_input():
    # 收集本地输入
    var input = {
        "sequence": input_sequence,
        "timestamp": Time.get_ticks_msec(),
        "actions": _get_input_actions()
    }
    
    local_inputs.append(input)
    input_sequence += 1

func _get_input_actions() -> Dictionary:
    # 获取输入动作
    return {
        "move_forward": Input.is_action_pressed("move_forward"),
        "move_backward": Input.is_action_pressed("move_backward"),
        "move_left": Input.is_action_pressed("move_left"),
        "move_right": Input.is_action_pressed("move_right"),
        "jump": Input.is_action_just_pressed("jump"),
        "attack": Input.is_action_just_pressed("attack")
    }

func _broadcast_input():
    # 广播输入（服务器）
    if local_inputs.size() > 0:
        var input = local_inputs.pop_front()
        _sync_input.rpc(input)

func _send_input_to_server():
    # 发送输入到服务器（客户端）
    if local_inputs.size() > 0:
        var input = local_inputs.pop_front()
        _sync_input_to_server.rpc_id(1, input)

@rpc("any_peer", "reliable")
func _sync_input(input: Dictionary):
    # 同步输入
    remote_inputs.append(input)
    input_received.emit(input)

@rpc("server", "reliable")
func _sync_input_to_server(input: Dictionary):
    # 同步输入到服务器
    remote_inputs.append(input)
    input_received.emit(input)

func _process_remote_inputs():
    # 处理远程输入
    while remote_inputs.size() > 0:
        var input = remote_inputs.pop_front()
        _apply_input(input)

func _apply_input(input: Dictionary):
    # 应用输入
    pass
```

### 3.2 输入缓冲

```gdscript
# 输入缓冲
class_name InputBufferSynchronizer

extends Node

@export var buffer_size: int = 10
@export var buffer_time_ms: int = 100

var input_buffer: Array = []
var processed_sequence: int = -1

signal input_ready(input: Dictionary)

func _process(delta):
    # 收集输入
    var input = _collect_input()
    if input:
        input_buffer.append(input)
    
    # 处理缓冲
    _process_buffer()

func _collect_input() -> Dictionary:
    # 收集输入
    var current_time = Time.get_ticks_msec()
    
    return {
        "sequence": input_buffer.size(),
        "timestamp": current_time,
        "actions": _get_input_actions(),
        "target_time": current_time + buffer_time_ms
    }

func _process_buffer():
    # 处理缓冲
    var current_time = Time.get_ticks_msec()
    
    # 处理到期的输入
    while input_buffer.size() > 0:
        var input = input_buffer[0]
        
        if input.target_time <= current_time:
            input_buffer.pop_front()
            
            # 检查序列号
            if input.sequence > processed_sequence:
                processed_sequence = input.sequence
                input_ready.emit(input)
        else:
            break

func get_predicted_input() -> Dictionary:
    # 获取预测输入
    if input_buffer.size() > 0:
        return input_buffer[0]
    
    return {
        "sequence": -1,
        "actions": {},
        "timestamp": Time.get_ticks_msec()
    }

func _get_input_actions() -> Dictionary:
    return {
        "move_forward": Input.is_action_pressed("move_forward"),
        "move_backward": Input.is_action_pressed("move_backward"),
        "move_left": Input.is_action_pressed("move_left"),
        "move_right": Input.is_action_pressed("move_right"),
        "jump": Input.is_action_just_pressed("jump"),
        "attack": Input.is_action_just_pressed("attack")
    }
```

### 3.3 输入预测

```gdscript
# 输入预测
class_name InputPredictionSynchronizer

extends InputBufferSynchronizer

var predicted_state: Dictionary = {}
var confirmed_state: Dictionary = {}

func _process(delta):
    super._process(delta)
    
    # 预测状态
    _predict_state(delta)

func _predict_state(delta):
    # 预测状态
    var input = get_predicted_input()
    
    if input.sequence >= 0:
        # 根据输入预测状态
        predicted_state = _apply_input_to_state(predicted_state, input.actions, delta)

func _apply_input_to_state(state: Dictionary, actions: Dictionary, delta: float) -> Dictionary:
    # 应用输入到状态
    var result = state.duplicate()
    
    # 处理移动
    var move_direction = Vector3.ZERO
    if actions.get("move_forward", false):
        move_direction.z -= 1
    if actions.get("move_backward", false):
        move_direction.z += 1
    if actions.get("move_left", false):
        move_direction.x -= 1
    if actions.get("move_right", false):
        move_direction.x += 1
    
    if move_direction.length() > 0:
        move_direction = move_direction.normalized()
    
    # 更新位置
    if not result.has("position"):
        result["position"] = Vector3.ZERO
    if not result.has("velocity"):
        result["velocity"] = Vector3.ZERO
    
    var speed = 5.0
    result["velocity"] = move_direction * speed
    result["position"] = result["position"] + result["velocity"] * delta
    
    return result

func reconcile_state(server_state: Dictionary):
    # 调和状态（服务器纠正）
    confirmed_state = server_state
    
    # 如果预测状态与服务器状态不同，需要纠正
    if not _states_match(predicted_state, server_state):
        # 重新应用未确认的输入
        _reapply_unconfirmed_inputs(server_state)

func _states_match(state1: Dictionary, state2: Dictionary) -> bool:
    # 检查状态是否匹配
    if state1.has("position") and state2.has("position"):
        if state1["position"].distance_to(state2["position"]) > 0.1:
            return false
    
    return true

func _reapply_unconfirmed_inputs(state: Dictionary):
    # 重新应用未确认的输入
    var current_state = state.duplicate()
    
    for input in input_buffer:
        current_state = _apply_input_to_state(current_state, input.actions, 1.0 / 60.0)
    
    predicted_state = current_state
```

---

## 4. 延迟补偿

### 4.1 延迟测量

```gdscript
# 延迟测量
class_name LatencyMeasurer

extends Node

var ping_sequence: int = 0
var ping_times: Dictionary = {}  # sequence -> send_time
var rtt_history: Array = []
var current_rtt: float = 0.0

signal rtt_updated(rtt: float)

func _ready():
    # 定期发送 Ping
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.connect("timeout", self, "_send_ping")
    add_child(timer)
    timer.start()

func _process(delta):
    # 清理超时的 Ping
    _cleanup_old_pings()

func _send_ping():
    # 发送 Ping
    ping_sequence += 1
    ping_times[ping_sequence] = Time.get_ticks_msec()
    _send_ping.rpc()

@rpc("any_peer", "reliable")
func _send_ping():
    # 服务器收到 Ping，回复 Pong
    if multiplayer.is_server():
        _send_pong.rpc_id(multiplayer.get_remote_sender_id(), ping_sequence)
    else:
        # 客户端收到 Pong
        pass

@rpc("any_peer", "reliable")
func _send_pong(sequence: int):
    # 收到 Pong，计算 RTT
    if ping_times.has(sequence):
        var send_time = ping_times[sequence]
        ping_times.erase(sequence)
        
        var rtt = Time.get_ticks_msec() - send_time
        current_rtt = rtt
        rtt_history.append(rtt)
        
        # 限制历史记录
        if rtt_history.size() > 60:
            rtt_history.pop_front()
        
        rtt_updated.emit(rtt)

func _cleanup_old_pings():
    # 清理超时的 Ping
    var current_time = Time.get_ticks_msec()
    var to_remove = []
    
    for sequence in ping_times:
        if current_time - ping_times[sequence] > 5000:  # 5 秒超时
            to_remove.append(sequence)
    
    for sequence in to_remove:
        ping_times.erase(sequence)

func get_average_rtt() -> float:
    # 获取平均 RTT
    if rtt_history.size() == 0:
        return 0.0
    
    var total = 0.0
    for rtt in rtt_history:
        total += rtt
    
    return total / rtt_history.size()

func get_jitter() -> float:
    # 获取抖动
    if rtt_history.size() < 2:
        return 0.0
    
    var jitter = 0.0
    for i in range(1, rtt_history.size()):
        jitter += abs(rtt_history[i] - rtt_history[i - 1])
    
    return jitter / (rtt_history.size() - 1)
```

### 4.2 延迟补偿

```gdscript
# 延迟补偿
class_name LagCompensator

extends Node

var latency_measurer: LatencyMeasurer
var history_buffer: Array = []  # 状态历史
var history_duration_ms: int = 1000

func _ready():
    latency_measurer = LatencyMeasurer.new()
    add_child(latency_measurer)

func _process(delta):
    # 记录状态历史
    _record_state()
    
    # 清理过期历史
    _cleanup_history()

func _record_state():
    # 记录状态
    var state = {
        "timestamp": Time.get_ticks_msec(),
        "data": _get_current_state()
    }
    history_buffer.append(state)

func _get_current_state() -> Dictionary:
    # 获取当前状态
    return {}

func _cleanup_history():
    # 清理过期历史
    var current_time = Time.get_ticks_msec()
    var cutoff = current_time - history_duration_ms
    
    history_buffer = history_buffer.filter(func(s): return s.timestamp > cutoff)

func get_state_at_time(target_time: int) -> Dictionary:
    # 获取指定时间的状态
    if history_buffer.size() == 0:
        return {}
    
    # 找到最接近的快照
    var closest_state = history_buffer[0]
    var closest_diff = abs(closest_state.timestamp - target_time)
    
    for state in history_buffer:
        var diff = abs(state.timestamp - target_time)
        if diff < closest_diff:
            closest_diff = diff
            closest_state = state
    
    return closest_state.data

func compensate_for_latency(action_data: Dictionary) -> Dictionary:
    # 补偿延迟
    var rtt = latency_measurer.current_rtt
    var one_way_latency = rtt / 2
    
    # 计算客户端发送时的服务器时间
    var client_send_time = Time.get_ticks_msec() - one_way_latency
    
    # 获取那个时间的状态
    var compensated_state = get_state_at_time(client_send_time)
    
    # 应用动作
    var result = _apply_action(compensated_state, action_data)
    
    return result

func _apply_action(state: Dictionary, action: Dictionary) -> Dictionary:
    # 应用动作到状态
    return state
```

### 4.3 客户端预测

```gdscript
# 客户端预测
class_name ClientPrediction

extends Node

var predicted_position: Vector3 = Vector3.ZERO
var server_position: Vector3 = Vector3.ZERO
var input_buffer: Array = []
var last_confirmed_input: int = -1

func _process(delta):
    # 应用本地输入
    _apply_local_input(delta)
    
    # 检查服务器确认
    _check_server_confirmation()

func _apply_local_input(delta):
    # 应用本地输入（立即响应）
    var input = {
        "sequence": input_buffer.size(),
        "timestamp": Time.get_ticks_msec(),
        "actions": _get_input_actions()
    }
    
    input_buffer.append(input)
    
    # 立即应用输入到预测位置
    predicted_position = _apply_input_to_position(predicted_position, input.actions, delta)

func _check_server_confirmation():
    # 检查服务器确认
    # 当收到服务器状态时，比较预测和实际
    pass

func reconcile_with_server(server_state: Dictionary, last_input: int):
    # 与服务器调和
    server_position = server_state.get("position", Vector3.ZERO)
    last_confirmed_input = last_input
    
    # 如果差异太大，纠正
    var diff = predicted_position.distance_to(server_position)
    if diff > 0.5:
        # 需要纠正
        _correct_prediction(server_state)

func _correct_prediction(server_state: Dictionary):
    # 纠正预测
    predicted_position = server_state.get("position", Vector3.ZERO)
    
    # 重新应用未确认的输入
    for i in range(last_confirmed_input + 1, input_buffer.size()):
        var input = input_buffer[i]
        predicted_position = _apply_input_to_position(predicted_position, input.actions, 1.0 / 60.0)

func _apply_input_to_position(position: Vector3, actions: Dictionary, delta: float) -> Vector3:
    # 应用输入到位置
    var move_direction = Vector3.ZERO
    
    if actions.get("move_forward", false):
        move_direction.z -= 1
    if actions.get("move_backward", false):
        move_direction.z += 1
    if actions.get("move_left", false):
        move_direction.x -= 1
    if actions.get("move_right", false):
        move_direction.x += 1
    
    if move_direction.length() > 0:
        move_direction = move_direction.normalized()
    
    var speed = 5.0
    return position + move_direction * speed * delta

func _get_input_actions() -> Dictionary:
    return {
        "move_forward": Input.is_action_pressed("move_forward"),
        "move_backward": Input.is_action_pressed("move_backward"),
        "move_left": Input.is_action_pressed("move_left"),
        "move_right": Input.is_action_pressed("move_right")
    }
```

---

## 5. 预测和回滚

### 5.1 状态回滚

```gdscript
# 状态回滚
class_name StateRollback

extends Node

var state_history: Array = []
var max_history: int = 120  # 2 秒 @ 60Hz

func _process(delta):
    # 记录状态
    _record_state()
    
    # 清理过期历史
    _cleanup_history()

func _record_state():
    # 记录状态
    var state = {
        "frame": _get_current_frame(),
        "timestamp": Time.get_ticks_msec(),
        "data": _get_game_state()
    }
    state_history.append(state)

func _get_current_frame() -> int:
    # 获取当前帧
    return Engine.get_process_frames()

func _get_game_state() -> Dictionary:
    # 获取游戏状态
    return {}

func _cleanup_history():
    # 清理过期历史
    while state_history.size() > max_history:
        state_history.pop_front()

func rollback_to_frame(target_frame: int) -> Dictionary:
    # 回滚到指定帧
    for state in state_history:
        if state.frame == target_frame:
            return state.data
    
    return {}

func rollback_to_time(target_time: int) -> Dictionary:
    # 回滚到指定时间
    var closest_state = null
    var closest_diff = INF
    
    for state in state_history:
        var diff = abs(state.timestamp - target_time)
        if diff < closest_diff:
            closest_diff = diff
            closest_state = state
    
    return closest_state.data if closest_state else {}

func fast_forward(from_state: Dictionary, inputs: Array, target_frame: int) -> Dictionary:
    # 快进到目标帧
    var current_state = from_state.duplicate(true)
    
    for input in inputs:
        current_state = _apply_input(current_state, input)
    
    return current_state

func _apply_input(state: Dictionary, input: Dictionary) -> Dictionary:
    # 应用输入到状态
    return state
```

### 5.2 预测回滚系统

```gdscript
# 预测回滚系统
class_name PredictionRollbackSystem

extends Node

var state_rollback: StateRollback
var input_buffer: Array = []
var confirmed_input: int = -1

func _ready():
    state_rollback = StateRollback.new()
    add_child(state_rollback)

func _process(delta):
    # 收集输入
    _collect_input()
    
    # 应用预测
    _apply_prediction()

func _collect_input():
    # 收集输入
    var input = {
        "frame": Engine.get_process_frames(),
        "timestamp": Time.get_ticks_msec(),
        "actions": _get_input_actions()
    }
    input_buffer.append(input)

func _apply_prediction():
    # 应用预测
    var current_input = input_buffer[-1] if input_buffer.size() > 0 else null
    if current_input:
        _apply_local_input(current_input.actions)

func receive_server_state(server_state: Dictionary, last_confirmed_input: int):
    # 接收服务器状态
    confirmed_input = last_confirmed_input
    
    # 回滚到确认的输入
    var rollback_state = state_rollback.rollback_to_frame(_get_frame_for_input(last_confirmed_input))
    
    if not rollback_state.is_empty():
        # 重新应用未确认的输入
        for i in range(last_confirmed_input + 1, input_buffer.size()):
            var input = input_buffer[i]
            rollback_state = _apply_input_to_state(rollback_state, input.actions)
        
        # 应用纠正后的状态
        _apply_state(rollback_state)

func _get_frame_for_input(input_sequence: int) -> int:
    # 获取输入对应的帧
    if input_sequence >= 0 and input_sequence < input_buffer.size():
        return input_buffer[input_sequence].frame
    return 0

func _apply_input_to_state(state: Dictionary, actions: Dictionary) -> Dictionary:
    # 应用输入到状态
    return state

func _apply_state(state: Dictionary):
    # 应用状态
    pass

func _apply_local_input(actions: Dictionary):
    # 应用本地输入
    pass

func _get_input_actions() -> Dictionary:
    return {
        "move_forward": Input.is_action_pressed("move_forward"),
        "move_backward": Input.is_action_pressed("move_backward"),
        "move_left": Input.is_action_pressed("move_left"),
        "move_right": Input.is_action_pressed("move_right"),
        "jump": Input.is_action_just_pressed("jump"),
        "attack": Input.is_action_just_pressed("attack")
    }
```

### 5.3 帧同步

```gdscript
# 帧同步
class_name FrameSynchronizer

extends Node

@export var tick_rate: float = 60.0
var tick_timer: float = 0.0
var current_tick: int = 0
var input_buffer: Dictionary = {}  # tick -> {player_id -> input}

signal tick_executed(tick: int, inputs: Dictionary)

func _process(delta):
    tick_timer += delta
    var tick_interval = 1.0 / tick_rate
    
    while tick_timer >= tick_interval:
        tick_timer -= tick_interval
        _execute_tick()

func _execute_tick():
    # 执行帧
    var inputs = input_buffer.get(current_tick, {})
    
    # 执行游戏逻辑
    _update_game_state(inputs)
    
    tick_executed.emit(current_tick, inputs)
    current_tick += 1

func submit_input(player_id: int, input: Dictionary):
    # 提交输入
    if not input_buffer.has(current_tick):
        input_buffer[current_tick] = {}
    input_buffer[current_tick][player_id] = input
    
    # 清理旧输入
    _cleanup_old_inputs()

func _cleanup_old_inputs():
    # 清理旧输入
    var min_tick = current_tick - 120  # 保留 2 秒
    var to_remove = []
    
    for tick in input_buffer:
        if tick < min_tick:
            to_remove.append(tick)
    
    for tick in to_remove:
        input_buffer.erase(tick)

func _update_game_state(inputs: Dictionary):
    # 更新游戏状态
    for player_id in inputs:
        var input = inputs[player_id]
        _apply_player_input(player_id, input)

func _apply_player_input(player_id: int, input: Dictionary):
    # 应用玩家输入
    pass
```

---

## 6. 网络同步优化

### 6.1 优先级同步

```gdscript
# 优先级同步
class_name PrioritySynchronizer

extends Node

@export var sync_rate_high: float = 60.0
@export var sync_rate_medium: float = 30.0
@export var sync_rate_low: float = 10.0

var high_priority_objects: Array = []
var medium_priority_objects: Array = []
var low_priority_objects: Array = []

var sync_timers: Dictionary = {
    "high": 0.0,
    "medium": 0.0,
    "low": 0.0
}

func _process(delta):
    # 高优先级
    sync_timers["high"] += delta
    if sync_timers["high"] >= 1.0 / sync_rate_high:
        sync_timers["high"] = 0.0
        _sync_objects(high_priority_objects)
    
    # 中优先级
    sync_timers["medium"] += delta
    if sync_timers["medium"] >= 1.0 / sync_rate_medium:
        sync_timers["medium"] = 0.0
        _sync_objects(medium_priority_objects)
    
    # 低优先级
    sync_timers["low"] += delta
    if sync_timers["low"] >= 1.0 / sync_rate_low:
        sync_timers["low"] = 0.0
        _sync_objects(low_priority_objects)

func set_priority(object: Node, priority: String):
    # 设置优先级
    _remove_from_all_lists(object)
    
    match priority:
        "high":
            high_priority_objects.append(object)
        "medium":
            medium_priority_objects.append(object)
        "low":
            low_priority_objects.append(object)

func _remove_from_all_lists(object: Node):
    # 从所有列表移除
    high_priority_objects.erase(object)
    medium_priority_objects.erase(object)
    low_priority_objects.erase(object)

func _sync_objects(objects: Array):
    # 同步对象
    for object in objects:
        if is_instance_valid(object):
            _sync_object(object)

func _sync_object(object: Node):
    # 同步对象
    pass
```

### 6.2 可见性同步

```gdscript
# 可见性同步
class_name VisibilitySynchronizer

extends Node

@export var view_distance: float = 100.0
@export var sync_rate_visible: float = 60.0
@export var sync_rate_hidden: float = 5.0

var visible_objects: Array = []
var hidden_objects: Array = []

func _process(delta):
    # 更新可见性
    _update_visibility()
    
    # 同步可见对象
    _sync_visible_objects(delta)
    
    # 同步隐藏对象
    _sync_hidden_objects(delta)

func _update_visibility():
    # 更新可见性
    var camera = get_viewport().get_camera_3d()
    if not camera:
        return
    
    var camera_pos = camera.global_transform.origin
    
    # 重新分类对象
    var all_objects = visible_objects + hidden_objects
    visible_objects.clear()
    hidden_objects.clear()
    
    for object in all_objects:
        if is_instance_valid(object):
            var distance = object.global_transform.origin.distance_to(camera_pos)
            if distance <= view_distance:
                visible_objects.append(object)
            else:
                hidden_objects.append(object)

func _sync_visible_objects(delta):
    # 同步可见对象
    var sync_timer = 0.0
    for object in visible_objects:
        sync_timer += delta
        if sync_timer >= 1.0 / sync_rate_visible:
            sync_timer = 0.0
            _sync_object(object)

func _sync_hidden_objects(delta):
    # 同步隐藏对象
    var sync_timer = 0.0
    for object in hidden_objects:
        sync_timer += delta
        if sync_timer >= 1.0 / sync_rate_hidden:
            sync_timer = 0.0
            _sync_object(object)

func _sync_object(object: Node):
    # 同步对象
    pass
```

### 6.3 带宽优化

```gdscript
# 带宽优化
class_name SyncBandwidthOptimizer

extends Node

@export var max_bandwidth_bps: int = 50000  # 50 kbps
var current_bandwidth: float = 0.0
var bandwidth_window: Array = []

func record_sent(bytes: int):
    # 记录发送
    var current_time = Time.get_ticks_msec() / 1000.0
    bandwidth_window.append({"time": current_time, "bytes": bytes})
    _cleanup_window()
    _update_bandwidth()

func _cleanup_window():
    # 清理窗口
    var current_time = Time.get_ticks_msec() / 1000.0
    var cutoff = current_time - 1.0
    bandwidth_window = bandwidth_window.filter(func(item): return item.time > cutoff)

func _update_bandwidth():
    # 更新带宽
    var total_bytes = 0
    for item in bandwidth_window:
        total_bytes += item.bytes
    current_bandwidth = total_bytes

func can_send(bytes: int) -> bool:
    # 检查是否可以发送
    var predicted_bandwidth = (current_bandwidth + bytes) * 8
    return predicted_bandwidth <= max_bandwidth_bps

func get_optimal_sync_rate(base_rate: float) -> float:
    # 获取最佳同步率
    if current_bandwidth * 8 >= max_bandwidth_bps:
        return base_rate * 0.5  # 降低 50%
    return base_rate

func throttle_sync(rate: float) -> float:
    # 限制同步率
    var available_bandwidth = max_bandwidth_bps - (current_bandwidth * 8)
    if available_bandwidth <= 0:
        return 0.0
    
    # 计算最大允许的同步率
    var avg_packet_size = 100  # 假设平均每包 100 字节
    var max_packets_per_second = available_bandwidth / (avg_packet_size * 8)
    
    return min(rate, max_packets_per_second)
```

---

## 7. 实践：完整同步系统

### 7.1 多人游戏同步

```gdscript
# 多人游戏同步
class_name MultiplayerGameSync

extends Node

var state_sync: SnapshotSynchronizer
var input_sync: InputPredictionSynchronizer
var lag_compensator: LagCompensator
var rollback_system: PredictionRollbackSystem
var bandwidth_optimizer: SyncBandwidthOptimizer

func _ready():
    state_sync = SnapshotSynchronizer.new()
    add_child(state_sync)
    
    input_sync = InputPredictionSynchronizer.new()
    add_child(input_sync)
    
    lag_compensator = LagCompensator.new()
    add_child(lag_compensator)
    
    rollback_system = PredictionRollbackSystem.new()
    add_child(rollback_system)
    
    bandwidth_optimizer = SyncBandwidthOptimizer.new()
    add_child(bandwidth_optimizer)

func _process(delta):
    # 处理同步
    pass

func submit_input(input: Dictionary):
    # 提交输入
    input_sync.submit_input(input)

func receive_server_state(state: Dictionary):
    # 接收服务器状态
    rollback_system.receive_server_state(state, -1)

func get_predicted_state() -> Dictionary:
    # 获取预测状态
    return input_sync.predicted_state

func get_confirmed_state() -> Dictionary:
    # 获取确认状态
    return rollback_system.server_position
```

### 7.2 FPS 游戏同步

```gdscript
# FPS 游戏同步
class_name FPSGameSync

extends MultiplayerGameSync

@export var hitbox_tolerance: float = 0.1

func shoot(shoot_direction: Vector3):
    # 射击
    if multiplayer.is_server():
        # 服务器：直接处理
        _process_shot(shoot_direction)
    else:
        # 客户端：预测射击
        _predict_shot(shoot_direction)
        _send_shot_to_server(shoot_direction)

func _process_shot(direction: Vector3):
    # 处理射击（服务器）
    var hit = _check_hit(direction)
    if hit:
        _apply_damage(hit)

func _predict_shot(direction: Vector3):
    # 预测射击（客户端）
    var hit = _check_hit(direction)
    if hit:
        _show_hit_effect(hit)

func _send_shot_to_server(direction: Vector3):
    # 发送射击到服务器
    _send_shot.rpc_id(1, direction, Time.get_ticks_msec())

@rpc("server", "reliable")
func _send_shot(direction: Vector3, client_time: int):
    # 服务器收到射击
    # 使用延迟补偿
    var server_time = Time.get_ticks_msec()
    var latency = (server_time - client_time) / 2
    
    # 回滚到客户端射击时的状态
    var rollback_state = lag_compensator.get_state_at_time(client_time)
    
    # 在回滚状态中检查命中
    var hit = _check_hit_in_state(rollback_state, direction)
    
    if hit:
        _apply_damage(hit)

func _check_hit(direction: Vector3) -> Dictionary:
    # 检查命中
    return {}

func _check_hit_in_state(state: Dictionary, direction: Vector3) -> Dictionary:
    # 在指定状态中检查命中
    return {}

func _apply_damage(hit: Dictionary):
    # 应用伤害
    pass

func _show_hit_effect(hit: Dictionary):
    # 显示命中效果
    pass
```

---

## 📝 本章总结

### 核心要点

1. **状态同步适合大多数游戏**，服务器权威，客户端插值
2. **输入同步适合格斗/动作游戏**，客户端预测，服务器确认
3. **延迟补偿提升射击体验**，回滚到客户端射击时间
4. **预测和回滚处理不一致**，快速纠正状态
5. **同步优化提升性能**，优先级、可见性、带宽优化

### 关键术语

| 术语 | 解释 |
|------|------|
| State Sync | 状态同步，同步游戏状态 |
| Input Sync | 输入同步，同步玩家输入 |
| Lag Compensation | 延迟补偿，补偿网络延迟 |
| Client Prediction | 客户端预测，预测本地结果 |
| Rollback | 回滚，恢复到之前状态 |
| Snapshot | 快照，状态的时间点副本 |
| RTT | 往返时间，网络延迟 |
| Interpolation | 插值，平滑状态过渡 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot High-Level Networking](https://docs.godotengine.org/en/stable/tutorials/networking/high_level_multiplayer.html)
- **Valve Source Networking**: Source 引擎网络架构
- **Gaffer On Games**: 游戏网络编程系列文章

---

## 📋 下一章预告

**第 52 篇：网络优化**

- 网络性能分析
- 带宽优化
- 延迟优化
- 同步优化

---

*写作时间：2026-03-20*  
*字数：约 15,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 19:00*