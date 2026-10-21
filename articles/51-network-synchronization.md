# 第 51 篇：网络同步

> **本卷定位**: 第六卷 网络系统（5 篇）  
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
- 了解引擎内置的场景同步方案（`MultiplayerSpawner` / `MultiplayerSynchronizer`）
- 学会输入同步方法
- 熟悉延迟补偿技术
- 掌握预测和回滚的**策略取舍**（完整实现见第 57 篇）
- 掌握网络同步优化

> **本篇与第 57 篇的分工**：第 51 篇是**同步策略总览**——讲清楚有哪些同步策略（状态 / 输入 / 快照 / 增量 / 预测 / 延迟补偿）、各自的代价与选型依据，以及 `MultiplayerAPI` / `SceneMultiplayer` 的扩展点。第 57 篇《权威服务器架构》是**服务端权威实战**——完整可跑流程 + 服务端校验 + 反作弊边界。两篇互补，不要重复读同一份代码。

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

### 1.4 MultiplayerAPI 与 SceneMultiplayer：可扩展的接口

前面所有例子都直接用 `multiplayer.xxx`，那是 `SceneTree` 给场景树配好的**默认 `MultiplayerAPI` 实例**。理解这一层，才能知道"引擎帮我们做了什么"以及"哪些能改"。

**两个类**

| 类 | 位置 | 职责 |
|----|------|------|
| `MultiplayerAPI` | `scene/main/multiplayer_api.h` | **接口**。定义 `poll()`、`rpc()`、`object_configuration_add()`、`get_remote_sender_id()` 等抽象方法与 `peer_connected` 等信号。脚本可以继承 `MultiplayerAPIExtension` 来扩展它 |
| `SceneMultiplayer` | `modules/multiplayer/scene_multiplayer.h` | **默认实现**。引擎启动时 `MultiplayerAPI::set_default_interface("SceneMultiplayer")` 指定它。额外提供 `root_path`、`auth_callback`、`server_relay`、`max_sync_packet_size` 等属性 |

**`OfflineMultiplayerPeer`：为什么单机会"假装自己在联网"**

`SceneMultiplayer` 的构造函数里默认塞了一个 `OfflineMultiplayerPeer`（`modules/multiplayer/scene_multiplayer.h`）。它永远返回"已连接"、`is_server()` 为真、不收发任何数据。于是：

- 单机跑游戏时，`multiplayer.is_server()` 直接返回 `true`，不用写 `if multiplayer.has_multiplayer_peer()` 这类分支；
- 想切成真正的联网模式，只要给 `multiplayer.multiplayer_peer` 赋一个真实的 `ENetMultiplayerPeer` 即可。

**可用的扩展点**

```gdscript
# MultiplayerAPI / SceneMultiplayer 的扩展点
class_name MultiplayerExtensionSetup

extends Node

func _ready():
    # 场景树当前使用的 MultiplayerAPI（默认是 SceneMultiplayer）
    var api := get_tree().get_multiplayer()
    # MultiplayerAPI 基类没有声明下面这些属性，它们属于 SceneMultiplayer。
    # 保留 SceneMultiplayer 的静态类型即可直接用点号访问。
    var scene_api := api as SceneMultiplayer
    if scene_api == null:
        push_warning("当前 MultiplayerAPI 不是 SceneMultiplayer，跳过扩展配置")
        return

    # 1) root_path：RPC 节点路径的解析基准。
    #    自定义 MultiplayerAPI（SceneTree.set_multiplayer()）时必须设置，
    #    否则收包会报 "Multiplayer root was not initialized"。
    scene_api.object_configuration_add(null, ^"/root/Main")

    # 2) auth_callback：新 peer 接入时先挂起，等鉴权通过再放行
    scene_api.auth_callback = _on_peer_auth
    scene_api.auth_timeout = 10.0  # 秒（默认 3.0 秒；0 表示不超时）

    # 3) server_relay：服务器是否中继客户端之间的消息（默认 true）
    scene_api.server_relay = true

    # 4) 同步包大小上限：超出后引擎会拆成多个包发送
    scene_api.max_sync_packet_size = 65536
    scene_api.max_delta_packet_size = 16384

func _on_peer_auth(peer_id: int, auth_data: PackedByteArray) -> void:
    # auth_data 里放的是登录令牌之类的凭据
    if _verify_token(auth_data):
        # 放行：引擎会正式把这个 peer 加入已连接列表
        scene_api.complete_auth(peer_id)
    # 不调用 complete_auth → 超过 auth_timeout 后引擎发
    # peer_authentication_failed 信号并断开该 peer
```

**`object_configuration_add()` 到底做了什么**

它是 `MultiplayerAPI` 基类上的公开方法（`object_configuration_remove()` 是配对的移除）。按官方文档，它有两个用途：

1. **`SceneTree` 用它配置根路径**：`object_configuration_add(null, <NodePath>)` 表示"把 `<NodePath>` 设为本 MultiplayerAPI 的根路径"，传空 `NodePath` 则是清除。
2. **实现类用它登记"需要同步的对象 + 配置"**：`SceneMultiplayer` 的实现里，如果 `configuration` 是 `MultiplayerSpawner`，就走生成/销毁流程；如果是 `MultiplayerSynchronizer`，就走属性同步流程。`MultiplayerSpawner` 与 `MultiplayerSynchronizer` 正是靠这对 API 与引擎接上的——这也就是下一节（2.4）的内容。

**什么时候该自己写 `MultiplayerAPIExtension`**

只有在以下情况才值得：

- 需要**替换**整个 RPC 路由（例如自研压缩/加密层、或做"服务器不中继"的直连拓扑）；
- 需要在 RPC 之外接管原始包（`SceneMultiplayer` 的 `peer_packet` 信号与 `send_bytes()` 已经能满足大部分需求）；
- 需要在**同一个进程里同时跑服务器和客户端**（用 `SceneTree.set_multiplayer()` 给不同子树挂不同的 `MultiplayerAPI`）。

否则，老老实实用默认的 `SceneMultiplayer` + `@rpc`，别去重造轮子。

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

# 服务端权威状态必须用 authority 模式：
# 用 any_peer 时任意客户端都能调用它，把伪造状态广播给其他人
@rpc("authority", "call_remote", "unreliable")
func _sync_state(state: Dictionary) -> void:
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

# 同样是服务端下发的权威增量，用 authority 模式
@rpc("authority", "call_remote", "unreliable")
func _sync_delta(delta: Dictionary) -> void:
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

# 快照是权威状态，只能由服务端下发
@rpc("authority", "call_remote", "unreliable")
func _send_snapshot(snapshot: Dictionary) -> void:
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
        
        # 插值。两个快照的时间戳可能相同（同一毫秒内产生了两帧），
        # 此时分母为 0，t 会变成 INF / NaN 并污染整个插值结果。
        # 用 maxi(1, ...) 兜底，保证分母至少为 1 毫秒。
        var span := maxi(1, snapshot2.timestamp - snapshot1.timestamp)
        var t := clampf(float(target_time - snapshot1.timestamp) / float(span), 0.0, 1.0)
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

### 2.4 引擎内置方案：MultiplayerSpawner 与 MultiplayerSynchronizer

前面 2.1–2.3 讲的是**自研 RPC 同步**：自己决定发什么、用什么频率发、怎么插值。但 Godot 4 其实自带了一套场景同步方案，能覆盖大部分"不需要自定义协议"的项目。**先搞清内置方案能做到什么，再决定要不要自己写。**

| | 引擎内置（`MultiplayerSpawner` + `MultiplayerSynchronizer`） | 自研 RPC（本节 2.1–2.3） |
|---|---|---|
| 谁生成对象 | `MultiplayerSpawner` 按场景路径在所有端生成 | 自己写 RPC，自己 `add_child` |
| 属性同步 | 在编辑器里勾选要同步的属性（`SceneReplicationConfig`） | 自己定义状态字典、手工序列化 |
| 增量同步 | 引擎自动 diff，只发变化的属性 | 自己实现 delta 计算 |
| 传输模式 | 按属性配置：`REPLICATION_MODE_ALWAYS`（不可靠）/ `ON_CHANGE`（可靠）/ `NEVER` | 自己给每个 RPC 指定 `@rpc` 的 `transfer_mode` |
| 兴趣管理（AOI） | 内置 `visibility` 过滤 + `update_visibility()` | 自己实现（见 6.2 节） |
| 自定义线格式 | 不支持，固定用引擎的 `Variant` 编码 | 完全可控（第 50 篇） |
| 代码量 | 少，配置为主 | 多，但灵活 |

**`MultiplayerSpawner`：对象的生成与销毁**

```gdscript
# MultiplayerSpawner：让权威端生成的节点在所有端自动出现
class_name SpawnerController

extends Node

@onready var spawner: MultiplayerSpawner = $MultiplayerSpawner

func _ready():
    # 把可生成的场景路径登记进去
    # 权威端（服务器）把这些场景作为 spawn_path 的直接子节点加入时，
    # 所有端都会自动生成同一个场景实例。
    spawner.add_spawnable_scene("res://actors/Player.tscn")
    spawner.add_spawnable_scene("res://actors/Enemy.tscn")

    # spawn_path：生成结果的挂载根节点
    spawner.spawn_path = ^"../Actors"

    # spawn_limit：最多允许生成多少个（含自定义 spawn），0 表示不限
    spawner.spawn_limit = 64

    spawner.spawned.connect(_on_spawned)
    spawner.despawned.connect(_on_despawned)

func _on_spawned(node: Node) -> void:
    # 只在非权威端触发（权威端是"发起方"）
    print("远端生成了：", node.name)

func _on_despawned(node: Node) -> void:
    print("远端销毁了：", node.name)
```

**自定义生成**：如果对象不是固定场景（例如需要服务器决定生成参数），用 `spawn(data)` + `spawn_function`：

```gdscript
func _ready():
    # 自定义生成：服务器调用 spawn()，所有端的 spawn_function 都会被调用
    spawner.spawn_function = _spawn_from_data

func _spawn_from_data(data: Variant) -> Node:
    # 返回一个**还没有加入场景树**的节点，引擎会自动把它挂到 spawn_path 下
    var enemy := Enemy.new()
    enemy.setup(data)
    return enemy
```

**`MultiplayerSynchronizer`：属性的自动同步**

```gdscript
# MultiplayerSynchronizer：自动同步属性
class_name SynchronizerController

extends Node

@onready var synchronizer: MultiplayerSynchronizer = $MultiplayerSynchronizer

func _ready():
    # root_path：被同步的属性相对于哪个节点。
    # 默认是 ".."（父节点）。如果同步器挂在玩家节点下，就是同步父节点的属性。
    synchronizer.root_path = ^".."

    # 用代码配置要同步的属性（也可以在编辑器里勾选）
    var config := SceneReplicationConfig.new()
    config.add_property(^"position")
    config.add_property(^"velocity")
    config.add_property(^"health")
    config.property_set_replication_mode(^"position", SceneReplicationConfig.REPLICATION_MODE_ALWAYS)
    config.property_set_replication_mode(^"velocity", SceneReplicationConfig.REPLICATION_MODE_ALWAYS)
    config.property_set_replication_mode(^"health", SceneReplicationConfig.REPLICATION_MODE_ON_CHANGE)
    # 生成时也把初始值发过去
    config.property_set_spawn(^"health", true)
    synchronizer.replication_config = config

    # replication_interval：全量同步间隔（秒）。0 = 每个网络帧都同步。
    synchronizer.replication_interval = 0.05
    # delta_interval：增量同步间隔（秒）。0 = 每个网络帧都尝试增量。
    # 注意属性名是 delta_interval，没有 "delta" 这个属性。
    synchronizer.delta_interval = 0.05
```

**三种复制模式的含义**

| 模式 | 行为 | 传输 |
|------|------|------|
| `REPLICATION_MODE_NEVER` | 不同步 | — |
| `REPLICATION_MODE_ALWAYS` | 每次 process 都发一次更新 | **不可靠**（丢了就丢了，下一帧覆盖） |
| `REPLICATION_MODE_ON_CHANGE` | 值变化时才发 | **可靠** |

**兴趣管理（AOI）**

```gdscript
# 只把节点同步给"看得见它"的 peer
func _ready():
    synchronizer.public_visibility = false  # 默认对所有 peer 可见
    # 加一个过滤器：返回 true 表示该 peer 看不见这个对象
    synchronizer.add_visibility_filter(_is_visible_to_peer)
    # VISIBILITY_PROCESS_IDLE / PHYSICS / NONE
    synchronizer.visibility_update_mode = MultiplayerSynchronizer.VISIBILITY_PROCESS_IDLE

func _is_visible_to_peer(peer_id: int) -> bool:
    # 4.3 的语义：过滤器返回 true 表示**不可见**
    return distance_to_peer(peer_id) > 200.0

func _on_player_moved():
    # 位置变了要重新算可见性
    synchronizer.update_visibility()
```

**内置方案的硬限制**（官方文档明确列出）

- `Object` 类型的属性（例如 `Resource`）**不能**同步。
- 各个 peer 上唯一的值——比如 `Object.get_instance_id()`、`RID`——同步过去也没有意义（对端上的 ID 根本不是同一个对象）。
- 同步是**属性级**的，不支持"自定义序列化"。如果你需要第 50 篇那套紧凑线格式，内置方案给不了。

**什么时候仍然要自己写 RPC**：需要自定义压缩/加密、需要把"位置"以比 `Variant` 编码更省的方式传输、需要回滚式预测、需要跨语言互操作的自定义协议——这些都要退回自研 RPC 方案。

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

# 客户端 → 服务器：mode 只能取 any_peer 或 authority，
# "server" 并不是合法取值。用 any_peer 让任意客户端都能上报输入，
# 服务器再用 multiplayer.get_remote_sender_id() 归属到具体玩家。
@rpc("any_peer", "call_remote", "reliable")
func _sync_input_to_server(input: Dictionary) -> void:
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

func _ready() -> void:
    # 定期发送 Ping；定时回调不能与 @rpc 方法同名，否则会自我递归
    var timer := Timer.new()
    timer.wait_time = 1.0
    timer.timeout.connect(_request_ping)
    add_child(timer)
    timer.start()

func _process(_delta: float) -> void:
    # 清理超时的 Ping
    _cleanup_old_pings()

func _request_ping() -> void:
    if multiplayer.is_server():
        return
    ping_sequence += 1
    ping_times[ping_sequence] = Time.get_ticks_msec()
    # 客户端 → 服务器：把「自己的序号」发上去
    _receive_ping.rpc_id(1, ping_sequence)

# 服务器收到 Ping：把「客户端发来的序号」原样回传。
# 若回传服务器自己的计数器，客户端永远匹配不上记录，RTT 必然错误。
@rpc("any_peer", "call_remote", "reliable")
func _receive_ping(sequence: int) -> void:
    if not multiplayer.is_server():
        return
    _receive_pong.rpc_id(multiplayer.get_remote_sender_id(), sequence)

# 客户端收到 Pong：用序号取回发送时刻再算 RTT
@rpc("authority", "call_remote", "reliable")
func _receive_pong(sequence: int) -> void:
    if multiplayer.is_server() or not ping_times.has(sequence):
        return

    var rtt := Time.get_ticks_msec() - int(ping_times[sequence])
    ping_times.erase(sequence)
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

> **本节定位**：第 51 篇是**同步策略总览**，只讲"有哪些策略、各自的代价与适用场景"；**完整的可运行实现**（含状态回滚、重放、平滑校正）在第 57 篇《权威服务器架构》§2。

> ⚠️ 文中出现的毫秒数为示意值（未附测试环境），实际延迟取决于网络与项目设置。

客户端预测要解决的问题只有一个：**本地操作的响应不能等一个来回**。玩家按下 W，角色必须立刻动，而不是等 80 ms 后服务器的状态回传。

**三种基本策略**

| 策略 | 本地是否立即表现 | 谁说了算 | 典型代价 | 适用 |
|------|------------------|----------|----------|------|
| **服务器权威**（纯状态同步） | 否，等服务器回包 | 服务器 | 操作有 RTT 级别的延迟；手感最"硬" | 回合制、卡牌、策略 |
| **客户端预测 + 服务器校正** | 是 | 服务器（但会纠正你） | 预测错了要回滚重放，可能出现"橡皮筋" | 动作、FPS、第三人称 |
| **延迟补偿**（服务端回溯判定） | 是（本地直接命中反馈） | 服务器按**过去**的世界状态判定 | 需要服务器保存历史状态；被"背后打"仍会挨打 | FPS、射击 |

**三者的组合关系**

- 预测解决的是**本地响应**；延迟补偿解决的是**命中判定**。两者正交，一个项目通常同时用。
- 权威始终在服务器。客户端预测只是"先斩后奏"，服务器一旦给出不同结论，客户端必须接受并纠正。
- 是否用预测，取决于**本地表现与权威结果的偏差能否被平滑吸收**。偏差过大时（低延迟服务器 + 复杂物理）可以关掉预测，改用"输入延迟补偿"（故意晚一点执行输入，让服务器结果接近本地直觉）。

**代价表**

| 引入的东西 | 换来什么 | 付出什么 |
|------------|----------|----------|
| 输入缓冲（保存已发出但未确认的输入） | 能重放 | 内存 + 一套序号管理 |
| 权威状态比对 | 能发现预测错了 | 每帧比对，或由服务器下发"已处理到第几号输入" |
| 回滚 + 重放 | 纠正后的状态正确 | 帧率尖刺、状态必须可确定性重放 |
| 平滑校正 | 视觉上不突兀 | 校正被"抹平"期间，本地与权威仍有微小分歧 |

**选型建议**

- 移动端 / 动作游戏：**开预测**，把校正阈值设小（几厘米），让它表现为"平滑吸附"而不是"瞬移"。
- 竞技射击：**开预测 + 延迟补偿**，且要保证服务器与客户端的移动积分完全一致（同一套公式、同一 tick 率），否则预测会持续被纠正。
- 回合制 / 策略：**不要预测**。多一层状态一致性风险，换来的响应提升几乎为零。

→ 完整实现（输入缓冲、状态比对、回滚重放、平滑校正）见**第 57 篇 §2「客户端预测」**。

---

## 5. 预测和回滚

### 5.1 状态回滚

> **本节定位**：第 51 篇只给**策略与代价**；回滚的完整可运行实现（状态历史环形缓冲、输入重放、校正下发）在第 57 篇《权威服务器架构》§3。

回滚要解决的是"**预测错了怎么办**"。三种做法，粒度不同，代价差别很大：

| 粒度 | 回滚什么 | 重放什么 | 内存 | 适合 |
|------|----------|----------|------|------|
| **帧回滚**（frame rollback） | 最近 N 帧的完整世界快照 | 这 N 帧的全部输入 | 高（整世界 × N） | 小地图、2D 平台跳跃 |
| **实体级状态回滚** | 相关实体的状态 | 相关实体的输入 | 中 | 动作游戏、载具 |
| **输入重放**（不存快照） | 不回滚状态，直接从权威状态重算 | 未确认的输入 | 低 | 位置类状态（可由输入完全推导） |

**关键前提**：回滚要求"**同样的输入必须产生同样的结果**"。

- 客户端与服务器必须用**同一套移动公式**（同一个函数、同一套常量、同一 tick 率）；
- 任何**非确定性因素**（`randi()`、系统时间、依赖浮点误差的物理引擎内部状态、遍历顺序）都会让重放结果与原始结果不一致，表现为"回滚后位置又跳了一下"；
- 因此"纯函数化"的游戏逻辑是回滚的前提：移动 = f(位置, 速度, 输入, dt)，而不是"读一下 `Input.is_action_pressed()` 然后 move_and_slide()"。

**代价表**

| 引入的东西 | 换来什么 | 付出什么 |
|------------|----------|----------|
| 状态历史缓冲 | 能回到过去 | 内存 = 实体数 × 状态大小 × 保留帧数 |
| 输入重放 | 纠正后状态自洽 | 重放本身消耗 CPU，帧率尖刺 |
| 权威 tick 序号 | 知道该回到哪一帧 | 服务器要随状态一起下发"已处理到第几号输入" |
| 校正平滑 | 视觉上不突兀 | 校正期间本地与权威仍有微小分歧 |

→ 完整实现见**第 57 篇 §3「服务器回滚」**。

### 5.2 预测回滚系统

预测回滚是一条**流水线**，四个环节缺一不可：

```
客户端                                        服务器
  │                                              │
  │ ① 采样输入 → 记入 input_buffer（带序号）        │
  │ ② 立即本地应用（预测）                          │
  │ ③ 输入上报 ─────────────────────────────────→  │
  │                                              │ ④ 按序号执行
  │                                              │ ⑤ 记录 tick 与已处理序号
  │ ⑥ 收到权威状态 + 已处理序号 ─────────────────  │
  │                                              │
  │ ⑦ 对比预测 vs 权威                             │
  │ ⑧ 差异超阈值 → 回滚到权威状态                  │
  │ ⑨ 重放 input_buffer 中未确认的输入              │
  │ ⑩ 平滑校正（避免瞬移）                         │
```

| 环节 | 缺了会怎样 |
|------|------------|
| ① 输入带序号 | ⑧ 无法判断"哪些输入还没被服务器处理" |
| ② 立即本地应用 | 失去预测的意义（回到纯服务器权威） |
| ⑤ 下发已处理序号 | ⑧ 无法定位回滚目标 |
| ⑧⑨ 回滚 + 重放 | 客户端状态与服务器长期漂移 |
| ⑩ 平滑校正 | 每次纠正都表现为"瞬移"，观感极差 |

**回滚窗口怎么定**

窗口必须覆盖"一个来回"：客户端发出输入后，到收到服务器的确认，最坏情况是 `RTT + 抖动` 再加上服务器的处理排队延迟。因此历史保留长度 ≈ `(RTT + 抖动) × 帧率`，再留一点余量。窗口太小会出现"要回滚的帧已经被覆盖"，窗口太大则线性增加内存。

**重放为什么不稳定**

重放时如果游戏逻辑里有 `randi()`、`Time.get_ticks_msec()`、依赖字典遍历顺序的逻辑，重放出的结果会和第一次不同。工程上的常见做法是：把随机数改成**带种子的确定性随机**（`RandomNumberGenerator` + 固定 seed），把时间改成**来自 tick 计数**而不是系统时钟。

→ 完整实现见**第 57 篇 §3「服务器回滚」**。

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

### 6.4 插值、外推与同步策略的取值方法论

这一节回答三个具体问题：**快照多久发一次？客户端落后多少时间渲染？没有新数据时最多能猜多久？**

#### 6.4.1 三个量的相互约束

| 量 | 含义 | 谁决定 |
|----|------|--------|
| `T_send` 快照间隔 | 服务器多久发一次状态 | 服务器 |
| `B` 插值缓冲 | 客户端故意落后服务器多少毫秒渲染 | 客户端 |
| `E` 外推上限 | 没有新快照时，最多用旧速度"猜"多久 | 客户端 |

约束关系：

1. **`B` 必须大于 `T_send` + 抖动**。缓冲里至少要能凑出**两个**快照才能插值；如果 `B < T_send`，客户端永远只有一个可用快照，插值退化成外推（也就是"猜"），误差立刻变大。
2. **`E` 必须远小于 `B`**。外推是在没有证据的情况下继续猜，猜得越久越离谱；网络卡顿时客户端会"飞出去"，等新快照到达时橡皮筋会非常难看。
3. **`T_send` 决定带宽**。状态大小固定时，带宽 ∝ `1 / T_send`。把 20 Hz 提到 60 Hz，带宽就是 3 倍。

> ⚠️ 常见起点（**示意值，未附测试环境**）：`T_send = 50 ms`（20 Hz）、`B = 100–200 ms`（≥ 2–4 个快照间隔）、`E = 50–100 ms`（≤ `B / 2`）。真实取值必须在自己的网络条件下用第 52 篇的监控器实测抖动后确定。

#### 6.4.2 抖动下的一阶与二阶外推

外推就是"没有新快照时，用已有信息预测未来"。

| | 一阶外推（线性） | 二阶外推（带加速度） |
|---|---|---|
| 公式 | `p += v * dt` | `p += v * dt + 0.5 * a * dt²` |
| 需要的量 | 位置 + 速度 | 位置 + 速度 + 加速度 |
| 误差阶 | 与加速度成正比 | 与加速度的变化率成正比 |
| 对抖动的敏感度 | 低 | **高**（差分求导会放大噪声） |
| 起步 / 刹车阶段 | 明显落后或超前 | 明显更准 |
| 匀速阶段 | 足够准 | 没有额外收益 |

**结论**：抖动大的链路（移动网络、跨区）用一阶；网络稳定但动作有加速度变化（赛车、跳跃）可以用二阶，但必须对加速度做**限幅与平滑**，否则噪声会被积分放大成可见的抖动。

**外推必须衰减**：外推的时间越长越不可信，所以要让外推步长随时间逐渐缩小，而不是等速跑到底。

```gdscript
# 插值 + 衰减外推
class_name InterpolatingExtrapolator

extends Node

@export var snapshot_interval_ms: int = 50   # T_send
@export var buffer_time_ms: int = 150        # B
@export var max_extrapolation_ms: int = 100  # E

var snapshots: Array = []  # [{ "timestamp": int, "state": Dictionary }]

func push_snapshot(timestamp: int, state: Dictionary) -> void:
    snapshots.append({"timestamp": timestamp, "state": state})
    while snapshots.size() > 2 and snapshots[1].timestamp < timestamp - buffer_time_ms * 2:
        snapshots.pop_front()

func sample(now_ms: int) -> Dictionary:
    if snapshots.size() < 2:
        return snapshots[-1]["state"] if not snapshots.is_empty() else {}

    # 渲染时刻 = 当前时间 - 缓冲
    var render_time := now_ms - buffer_time_ms

    var s1: Dictionary = snapshots[0]
    var s2: Dictionary = snapshots[1]
    for i in range(snapshots.size() - 1):
        if snapshots[i]["timestamp"] <= render_time and snapshots[i + 1]["timestamp"] >= render_time:
            s1 = snapshots[i]
            s2 = snapshots[i + 1]
            break

    var span := maxi(1, int(s2["timestamp"]) - int(s1["timestamp"]))
    var t := clampf(float(render_time - int(s1["timestamp"])) / float(span), 0.0, 1.0)

    # t > 1 说明渲染时刻已经越过最新快照 → 进入外推
    if t <= 1.0:
        return _lerp_state(s1["state"], s2["state"], t)

    # 外推：以第二段的速度继续走，并随时间衰减外推步长
    var over_ms := render_time - int(s2["timestamp"])
    if over_ms > max_extrapolation_ms:
        over_ms = max_extrapolation_ms  # 超出上限就停下，不猜了

    var velocity: Vector3 = _velocity_between(s1["state"], s2["state"], span)
    # 衰减系数：外推越久，实际推进量越小
    var decay := 1.0 - (float(over_ms) / float(max(1, max_extrapolation_ms))) * 0.5
    return _apply_offset(s2["state"], velocity * (float(over_ms) / 1000.0) * decay)

func _lerp_state(a: Dictionary, b: Dictionary, t: float) -> Dictionary:
    var result := a.duplicate(true)
    for key in a:
        if b.has(key) and a[key] is Vector3 and b[key] is Vector3:
            result[key] = a[key].lerp(b[key], t)
    return result

func _velocity_between(a: Dictionary, b: Dictionary, span_ms: int) -> Vector3:
    if a.has("position") and b.has("position"):
        return (b["position"] - a["position"]) / (float(span_ms) / 1000.0)
    return Vector3.ZERO

func _apply_offset(state: Dictionary, offset: Vector3) -> Dictionary:
    var result := state.duplicate(true)
    if result.has("position"):
        result["position"] = result["position"] + offset
    return result
```

#### 6.4.3 快照 / 增量 / 状态同步 的选型表

| 方案 | 每帧发什么 | 带宽 | 丢一个包的后果 | 适用 |
|------|------------|------|----------------|------|
| **全量快照** | 全部状态 | 高 | 下一个快照自愈 | 状态小、对象少、更新频繁 |
| **增量** | 只有变化的字段 | 低 | **状态永久错位**（直到下一个全量） | 必须配周期性全量兜底 |
| **引擎状态同步**（`MultiplayerSynchronizer`） | 引擎自动 diff 的属性 | 中 | 引擎内部处理 | 常规属性同步（见 2.4 节） |
| **输入同步** | 只传输入 | 最低 | 丢输入 → 少走一步 | 确定性模拟（格斗、帧同步） |

**增量的致命陷阱**：增量丢包会让接收端的状态**永久性地**和发送端不一致（因为缺的那块再也不会被重发）。所以用增量就必须有兜底：

- 周期性全量快照（例如每 2–5 秒一次，或每 N 个增量一次）；
- 或者关键状态走可靠通道、只有可丢失的状态走增量；
- 或者在增量里带上"基线序号"，接收端发现基线对不上就请求全量。

**状态同步 vs 输入同步的判据**：只有当**输入能唯一决定状态**、且**所有端执行同一套确定性逻辑**时，输入同步才比状态同步省。反之一律选状态同步——因为客户端可以伪造输入（见第 57 篇 §5）。

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
var bandwidth_optimizer: SyncBandwidthOptimizer

func _ready():
    state_sync = SnapshotSynchronizer.new()
    add_child(state_sync)
    
    input_sync = InputPredictionSynchronizer.new()
    add_child(input_sync)
    
    lag_compensator = LagCompensator.new()
    add_child(lag_compensator)
    
    bandwidth_optimizer = SyncBandwidthOptimizer.new()
    add_child(bandwidth_optimizer)

func _process(delta):
    # 处理同步
    pass

func submit_input(input: Dictionary) -> void:
    # 输入先写入缓冲区，预测由 InputPredictionSynchronizer._process() 自动完成。
    # 注意：InputPredictionSynchronizer 并没有 submit_input() 方法。
    input_sync.input_buffer.append(input)

func receive_server_state(state: Dictionary) -> void:
    # 已确认的输入序号由服务器随状态一起下发，不要硬编码为 -1。
    # 校正逻辑（回滚 + 重放 + 平滑）见第 57 篇 §2 的完整实现。
    var last_confirmed := int(state.get("last_processed_input", -1))
    input_sync.reconcile_state(state)

func get_predicted_state() -> Dictionary:
    # 预测状态由 InputPredictionSynchronizer 维护
    return input_sync.predicted_state

func get_confirmed_state() -> Dictionary:
    # 确认状态同样在 InputPredictionSynchronizer 上
    return input_sync.confirmed_state
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

@rpc("any_peer", "call_remote", "reliable")
func _send_shot(direction: Vector3, client_time: int) -> void:
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
4. **预测和回滚处理不一致**，本篇讲策略与代价，完整实现在第 57 篇
5. **引擎内置 `MultiplayerSpawner` + `MultiplayerSynchronizer`** 能覆盖大部分场景同步需求
6. **同步优化提升性能**，优先级、可见性、带宽优化

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
*字数：约 4,100 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*  

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）


**上一篇**: [第 57 篇：权威服务器架构](/articles/57-authoritative-server.md)
**下一篇**: [第 52 篇：网络优化](/articles/52-network-optimization.md)
---

*最后更新：2026-03-20 19:00*
