# 第 57 篇：权威服务器架构

> **本卷定位**: 第六卷 网络系统（新增高优先级篇）  
> **前置知识**: 第 51 章 网络同步  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

权威服务器架构是多人游戏安全性和一致性的基石。在这种架构下，服务器作为游戏状态的最终仲裁者，负责验证所有关键操作，防止作弊，并确保所有玩家看到一致的游戏世界。

本章将深入探讨权威服务器的实现、客户端预测、服务器回滚、延迟补偿等核心技术。

---

## 🎯 学习目标

- 理解权威服务器架构原理
- 掌握客户端预测技术
- 学会服务器回滚机制
- 熟悉延迟补偿方法
- 实施反作弊基础
- 掌握性能优化

---

## 1. 权威服务器基础

### 1.1 架构对比

```
网络架构对比:
┌─────────────────────────────────────────────────────────────┐
│ 架构类型      │ 优点              │ 缺点              │ 适用      │
├─────────────────────────────────────────────────────────────┤
│ 权威服务器    │ 防作弊、一致性高  │ 延迟敏感、服务器负载 │ FPS、MOBA │
│ P2P 主机      │ 延迟低、简单      │ 易作弊、主机优势   │ 格斗、本地 │
│ 混合架构      │ 平衡性能和安全性  │ 实现复杂          │ MMO、生存 │
└─────────────────────────────────────────────────────────────┘

权威服务器原则:
1. 服务器是真相来源（Source of Truth）
2. 客户端只负责表现和输入
3. 关键逻辑在服务器执行
4. 客户端预测 + 服务器校正
```

### 1.2 服务器架构设计

```gdscript
# 权威服务器基础架构
class_name AuthoritativeServer

extends Node

# 游戏状态
var game_state: Dictionary = {}
var player_states: Dictionary = {}

# 配置
@export var tick_rate: int = 60  # 服务器更新频率
@export var max_players: int = 16

var tick_counter: int = 0
var delta_accumulator: float = 0.0

func _ready():
    # 服务器只监听，不渲染
    Engine.max_fps = tick_rate
    
    # 初始化游戏状态
    _initialize_game_state()

func _process(delta):
    delta_accumulator += delta
    
    # 固定时间步长更新
    var tick_delta = 1.0 / tick_rate
    while delta_accumulator >= tick_delta:
        _server_tick(tick_delta)
        delta_accumulator -= tick_delta

func _server_tick(delta):
    tick_counter += 1
    
    # 1. 处理客户端输入
    _process_client_inputs()
    
    # 2. 更新游戏逻辑
    _update_game_logic(delta)
    
    # 3. 验证和反作弊
    _validate_actions()
    
    # 4. 广播状态给客户端
    _broadcast_state()

func _process_client_inputs():
    # 从所有客户端收集输入
    for peer_id in get_multiplayer_api().get_connected_peers():
        var input = _receive_input(peer_id)
        if input:
            _apply_input(peer_id, input)

func _validate_actions():
    # 验证玩家动作是否合法
    for player_id in player_states:
        var state = player_states[player_id]
        
        # 速度检查
        if state.velocity.length() > MAX_SPEED:
            _correct_player(player_id, "speed_hack")
        
        # 位置检查
        if _is_position_invalid(state.position):
            _correct_player(player_id, "position_hack")

func _broadcast_state():
    # 发送游戏状态给所有客户端
    var state_data = _serialize_game_state()
    rpc("_receive_server_state", state_data)
```

---

## 2. 客户端预测（Client-side Prediction）

### 2.1 预测原理

```
客户端预测流程:
┌─────────────────────────────────────────────────────────────┐
│  客户端                          │  服务器                  │
├─────────────────────────────────────────────────────────────┤
│  1. 玩家按下移动键                                          │
│  2. 立即执行移动（预测）                                    │
│  3. 发送输入到服务器 ──────────────────────────────────→   │
│                                  │  4. 服务器验证并执行     │
│  ←──────────────────────────────  5. 返回权威状态           │
│  6. 比较预测和权威状态                                      │
│  7. 如有差异，平滑校正                                      │
└─────────────────────────────────────────────────────────────┘

关键问题:
- 预测错误时的校正（回滚）
- 输入延迟的处理
- 状态同步的平滑过渡
```

### 2.2 预测实现

```gdscript
# 客户端预测控制器
class_name ClientPredictionController

extends CharacterBody3D

@export var prediction_enabled: bool = true
@export var smoothing_factor: float = 0.2

# 输入历史（用于回滚）
var input_history: Array = []
var max_history_size: int = 60  # 保存 1 秒（60 帧）

# 状态
var predicted_position: Vector3 = Vector3.ZERO
var server_position: Vector3 = Vector3.ZERO
var last_processed_input: int = 0

func _ready():
    set_process(true)

func _physics_process(delta):
    # 获取玩家输入
    var input = _get_player_input()
    
    if prediction_enabled:
        # 客户端立即执行（预测）
        _apply_input_local(input)
        
        # 保存输入历史
        _save_input_to_history(input)
        
        # 发送输入到服务器
        _send_input_to_server(input)
    else:
        # 非预测模式：等待服务器状态
        pass
    
    # 移动角色
    move_and_slide()

func _get_player_input() -> Dictionary:
    return {
        "input_id": Time.get_ticks_msec(),
        "forward": Input.get_axis("ui_up", "ui_down"),
        "right": Input.get_axis("ui_left", "ui_right"),
        "jump": Input.is_action_pressed("ui_accept"),
        "timestamp": Time.get_ticks_msec()
    }

func _apply_input_local(input: Dictionary):
    # 本地预测移动
    var direction = Vector3(input.right, 0, input.forward).normalized()
    velocity = direction * 5.0
    
    if input.jump and is_on_floor():
        velocity.y = 3.0
    
    predicted_position = global_transform.origin

func _save_input_to_history(input: Dictionary):
    input_history.append(input)
    
    # 限制历史记录大小
    if input_history.size() > max_history_size:
        input_history.pop_front()

func _send_input_to_server(input: Dictionary):
    # 发送输入到服务器（使用 RPC）
    rpc_id(1, "_server_receive_input", input)

# 接收服务器状态校正
@rpc("any_peer", "call_remote", "reliable")
func _receive_server_state(state_data: Dictionary):
    if not prediction_enabled:
        return
    
    server_position = Vector3(
        state_data.position_x,
        state_data.position_y,
        state_data.position_z
    )
    
    var server_input_id = state_data.last_processed_input
    
    # 回滚未确认的输入
    _rollback_to_server_state(server_input_id)
    
    # 平滑校正位置
    _smooth_correction()

func _rollback_to_server_state(server_input_id: int):
    # 找到服务器已处理的最后一个输入
    var inputs_to_replay = []
    
    # 从历史中找出未确认的输入
    for input in input_history:
        if input.input_id > server_input_id:
            inputs_to_replay.append(input)
    
    # 回滚到服务器状态
    global_transform.origin = server_position
    
    # 重新应用未确认的输入
    for input in inputs_to_replay:
        _apply_input_local(input)

func _smooth_correction():
    # 平滑插值到预测位置
    var correction = predicted_position - server_position
    
    if correction.length() > 0.1:
        # 差异较大，需要平滑校正
        global_transform.origin = global_transform.origin.lerp(
            predicted_position, 
            smoothing_factor
        )
```

---

## 3. 服务器回滚（Server Reconciliation）

### 3.1 回滚机制

```
服务器回滚流程:
┌─────────────────────────────────────────────────────────────┐
│  1. 服务器保存状态历史（最近 N 帧）                          │
│  2. 收到客户端输入（带时间戳）                               │
│  3. 回滚到输入对应的历史状态                                 │
│  4. 重新执行输入                                             │
│  5. 更新当前状态                                             │
│  6. 发送校正给客户端                                         │
└─────────────────────────────────────────────────────────────┘

状态历史管理:
- 环形缓冲区保存最近状态
- 每个状态包含：位置、速度、输入 ID、时间戳
- 自动清理过期状态
```

### 3.2 回滚实现

```gdscript
# 服务器端回滚系统
class_name ServerReconciliationSystem

extends Node

# 状态历史（环形缓冲区）
var state_history: Array = []
var max_history_size: int = 120  # 保存 2 秒（60 FPS）

# 玩家状态
var player_histories: Dictionary = {}

func _ready():
    pass

func save_state(player_id: String, state: Dictionary):
    # 保存当前状态到历史
    if not player_histories.has(player_id):
        player_histories[player_id] = []
    
    var history = player_histories[player_id]
    
    history.append({
        "state": state.duplicate(),
        "tick": get_server_tick(),
        "timestamp": Time.get_ticks_msec()
    })
    
    # 清理过期历史
    while history.size() > max_history_size:
        history.pop_front()

func process_client_input(player_id: String, input: Dictionary):
    var input_tick = input.tick
    var current_tick = get_server_tick()
    
    # 检查输入是否过期
    if current_tick - input_tick > max_history_size:
        print("Input too old, ignoring")
        return
    
    # 找到输入对应的历史状态
    var history = player_histories[player_id]
    var base_state = _find_state_at_tick(history, input_tick)
    
    if not base_state:
        # 状态已过期，使用当前状态
        base_state = history[-1] if history.size() > 0 else null
    
    # 回滚到历史状态
    _restore_player_state(player_id, base_state["state"])
    
    # 重新执行从历史 tick 到当前的所有输入
    _replay_inputs(player_id, input_tick, current_tick)
    
    # 应用客户端输入
    _apply_input(player_id, input)
    
    # 保存新状态
    save_state(player_id, _get_player_state(player_id))
    
    # 发送校正给客户端
    _send_correction_to_client(player_id)

func _find_state_at_tick(history: Array, target_tick: int) -> Dictionary:
    # 二分查找目标 tick 的状态
    for state_entry in history:
        if state_entry["tick"] == target_tick:
            return state_entry
    
    # 如果找不到精确匹配，找最近的
    var closest = null
    var min_diff = INF
    
    for state_entry in history:
        var diff = abs(state_entry["tick"] - target_tick)
        if diff < min_diff:
            min_diff = diff
            closest = state_entry
    
    return closest

func _restore_player_state(player_id: String, state: Dictionary):
    var player = get_player_node(player_id)
    if player:
        player.global_transform.origin = Vector3(
            state.position_x,
            state.position_y,
            state.position_z
        )
        player.velocity = Vector3(
            state.velocity_x,
            state.velocity_y,
            state.velocity_z
        )

func _replay_inputs(player_id: String, from_tick: int, to_tick: int):
    # 重新执行中间的所有输入
    # 这需要服务器存储所有输入
    pass

func _send_correction_to_client(player_id: String):
    var player = get_player_node(player_id)
    var state = _get_player_state(player_id)
    
    # 发送权威状态给客户端
    rpc_id(player_id, "_receive_server_state", state)
```

---

## 4. 延迟补偿（Lag Compensation）

### 4.1 延迟补偿原理

```
延迟补偿（Lag Compensation）:
┌─────────────────────────────────────────────────────────────┐
│  问题：客户端 A 射击客户端 B，但 B 已经移动                  │
│                                                             │
│  解决方案：                                                  │
│  1. 客户端发送射击请求（带时间戳）                           │
│  2. 服务器回滚到射击时刻                                     │
│  3. 在历史状态下检测命中                                     │
│  4. 应用伤害                                                 │
│  5. 恢复到当前状态                                           │
└─────────────────────────────────────────────────────────────┘

关键公式:
回滚时间 = 当前时间 - (客户端时间戳 + RTT/2)
```

### 4.2 延迟补偿实现

```gdscript
# 延迟补偿射击系统
class_name LagCompensationShooting

extends Node

# 保存所有玩家的历史位置
var player_history: Dictionary = {}
var history_duration: float = 1.0  # 保存 1 秒

func _ready():
    set_process(true)

func _process(delta):
    # 每帧记录所有玩家位置
    _record_all_players()

func _record_all_players():
    var players = get_tree().get_nodes_in_group("players")
    
    for player in players:
        var player_id = player.name
        
        if not player_history.has(player_id):
            player_history[player_id] = []
        
        player_history[player_id].append({
            "position": player.global_transform.origin,
            "timestamp": Time.get_ticks_msec(),
            "hitbox": _get_hitbox_data(player)
        })
        
        # 清理过期历史
        _cleanup_history(player_id)

func _cleanup_history(player_id: String):
    var history = player_history[player_id]
    var current_time = Time.get_ticks_msec()
    var max_age = history_duration * 1000
    
    while history.size() > 0 and (current_time - history[0]["timestamp"]) > max_age:
        history.pop_front()

# 处理射击请求（服务器端）
func process_shot_request(shooter_id: String, shot_data: Dictionary):
    var shot_timestamp = shot_data.timestamp
    var rtt = shot_data.rtt  # 往返时间
    
    # 计算回滚时间
    var rollback_time = shot_timestamp + (rtt / 2)
    
    # 回滚所有玩家到射击时刻
    var rollback_positions = _get_positions_at_time(rollback_time)
    
    # 检测命中
    var hits = _check_hits_at_positions(shooter_id, shot_data, rollback_positions)
    
    # 应用伤害
    for hit in hits:
        _apply_damage(hit.player_id, hit.damage)
    
    # 发送命中结果
    _send_hit_results(hits)

func _get_positions_at_time(target_time: int) -> Dictionary:
    var positions = {}
    
    for player_id in player_history:
        var history = player_history[player_id]
        
        # 找到最接近目标时间的位置
        var closest = _find_closest_in_history(history, target_time)
        if closest:
            positions[player_id] = closest["position"]
    
    return positions

func _find_closest_in_history(history: Array, target_time: int) -> Dictionary:
    var closest = null
    var min_diff = INF
    
    for entry in history:
        var diff = abs(entry["timestamp"] - target_time)
        if diff < min_diff:
            min_diff = diff
            closest = entry
    
    return closest

func _check_hits_at_positions(shooter_id: String, shot_data: Dictionary, 
                               positions: Dictionary) -> Array:
    var hits = []
    var shooter_pos = positions.get(shooter_id, Vector3.ZERO)
    
    # 射线检测
    var from = shooter_pos
    var to = shot_data.direction * shot_data.range
    
    for player_id in positions:
        if player_id == shooter_id:
            continue
        
        var target_pos = positions[player_id]
        
        # 简化的命中检测
        var distance = from.distance_to(target_pos)
        if distance < 1.0:  # 命中
            hits.append({
                "player_id": player_id,
                "damage": shot_data.damage,
                "position": target_pos
            })
    
    return hits
```

---

## 5. 反作弊基础

### 5.1 常见作弊类型

```
常见作弊类型:
┌─────────────────────────────────────────────────────────────┐
│ 作弊类型        │ 检测方法                  │ 防御措施      │
├─────────────────────────────────────────────────────────────┤
│ 速度外挂        │ 服务器速度验证            │ 强制校正      │
│ 位置外挂        │ 边界和碰撞验证            │ 回滚位置      │
│ 自瞄            │ 准星移动分析              │ 服务器验证    │
│ 透视            │ 无法完全防御              │ 信息隐藏      │
│ 数据修改        │ 客户端完整性检查          │ 关键逻辑服务器│
└─────────────────────────────────────────────────────────────┘
```

### 5.2 反作弊实现

```gdscript
# 基础反作弊系统
class_name BasicAntiCheat

extends Node

# 验证配置
@export var max_speed: float = 10.0
@export var max_acceleration: float = 50.0
@export var teleport_threshold: float = 5.0

var player_metrics: Dictionary = {}

func _ready():
    pass

func validate_player_action(player_id: String, action: Dictionary) -> bool:
    match action.type:
        "move":
            return _validate_movement(player_id, action)
        "shoot":
            return _validate_shooting(player_id, action)
        "interact":
            return _validate_interaction(player_id, action)
    
    return true

func _validate_movement(player_id: String, action: Dictionary) -> bool:
    var metrics = _get_or_create_metrics(player_id)
    
    # 速度检查
    var distance = action.new_position.distance_to(metrics.last_position)
    var time_delta = (action.timestamp - metrics.last_timestamp) / 1000.0
    
    if time_delta > 0:
        var speed = distance / time_delta
        
        if speed > max_speed:
            print("Speed hack detected: ", speed)
            _flag_player(player_id, "speed_hack")
            return false
    
    # 加速度检查
    var acceleration = (speed - metrics.last_speed) / time_delta
    
    if abs(acceleration) > max_acceleration:
        print("Acceleration hack detected: ", acceleration)
        _flag_player(player_id, "acceleration_hack")
        return false
    
    # 更新指标
    metrics.last_position = action.new_position
    metrics.last_speed = speed
    metrics.last_timestamp = action.timestamp
    
    return true

func _validate_shooting(player_id: String, action: Dictionary) -> bool:
    # 检查射击频率
    var metrics = _get_or_create_metrics(player_id)
    var time_since_last_shot = action.timestamp - metrics.last_shot_timestamp
    
    if time_since_last_shot < 100:  # 最小射击间隔 100ms
        print("Rapid fire hack detected")
        _flag_player(player_id, "rapid_fire")
        return false
    
    metrics.last_shot_timestamp = action.timestamp
    return true

func _flag_player(player_id: String, cheat_type: String):
    # 记录作弊行为
    print("Player ", player_id, " flagged for: ", cheat_type)
    
    # 可以采取行动：警告、踢出、封禁
    # _kick_player(player_id)
```

---

## 📝 本章总结

### 核心要点

1. **权威服务器是真相来源**，所有关键逻辑在服务器执行
2. **客户端预测减少感知延迟**，立即响应玩家输入
3. **服务器回滚处理预测错误**，平滑校正状态
4. **延迟补偿提升射击精度**，回滚到射击时刻检测
5. **反作弊保护游戏公平**，服务器验证关键操作

### 关键术语

| 术语 | 解释 |
|------|------|
| Authoritative Server | 权威服务器，游戏状态的最终仲裁者 |
| Client Prediction | 客户端预测，立即执行本地输入 |
| Server Reconciliation | 服务器回滚，重新执行历史输入 |
| Lag Compensation | 延迟补偿，回滚检测命中 |
| Anti-Cheat | 反作弊，检测和防止作弊行为 |

---

*写作时间：2026-03-21*  
*字数：约 7,500 字*  
*状态：✅ 完成*
