# 第 39 篇：网络系统

> **本卷定位**: 第六卷 网络系统（8 篇）  
> **前置知识**: 第 48 章 音频效果器  
> **难度等级**: ⭐⭐⭐⭐ 高级

---

## 📖 本章导读

网络系统是多人游戏和在线应用的核心组件，负责处理玩家之间的通信、数据同步、状态同步等关键功能。一个优秀的网络系统能够提供低延迟、高可靠性的网络体验。

Godot 提供了完整的网络系统，包括 TCP、UDP、WebSocket、HTTP 等多种网络协议，以及高级的网络同步和 RPC 系统。本章将深入探讨这些技术的实现和优化。

---

## 🎯 学习目标

- 理解网络系统的基本概念
- 掌握 TCP/UDP 网络通信
- 学会 WebSocket 应用
- 熟悉 HTTP 请求处理
- 掌握网络同步技术
- 掌握网络系统优化

---

## 1. 网络系统基础

### 1.1 网络系统类型

```
网络系统类型:
┌─────────────────────────────────────────────────────────────┐
│                      网络系统类型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. TCP 网络：可靠连接，适合数据传输                        │
│  2. UDP 网络：快速传输，适合实时游戏                        │
│  3. WebSocket：浏览器兼容，适合 Web 游戏                    │
│  4. HTTP/HTTPS：Web API，适合数据请求                      │
│  5. ENet：可靠 UDP，适合多人游戏                           │
│  6. WebSocketServer：WebSocket 服务器                      │
│  7. TCPServer：TCP 服务器                                   │
│  8. UDPServer：UDP 服务器                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 网络系统组件

```
网络系统组件:
┌─────────────────────────────────────────────────────────────┐
│                      网络系统组件                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. StreamPeerTCP：TCP 流对等                              │
│  2. PacketPeerUDP：UDP 包对等                              │
│  3. WebSocket：WebSocket 客户端                             │
│  4. WebSocketServer：WebSocket 服务器                       │
│  5. HTTPClient：HTTP 客户端                                 │
│  6. HTTPRequest：HTTP 请求节点                              │
│  7. TCPServer：TCP 服务器                                   │
│  8. UDPServer：UDP 服务器                                   │
│  9. NetworkedMultiplayerENet：ENet 多人网络                │
│  10. NetworkedMultiplayerPeer：多人网络对等                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 网络系统流程

```
网络系统处理流程:
┌─────────────────────────────────────────────────────────────┐
│                      网络系统处理流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 创建网络连接（TCP/UDP/WebSocket）                      │
│  2. 连接到服务器或监听端口                                 │
│  3. 发送/接收数据                                          │
│  4. 处理网络事件（连接、断开、数据）                       │
│  5. 同步游戏状态                                           │
│  6. 处理网络延迟和丢包                                     │
│  7. 断开连接并清理资源                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. TCP 网络

### 2.1 StreamPeerTCP

```gdscript
# TCP 客户端
class_name TCPClient

extends Node

var tcp: StreamPeerTCP
var connected: bool = false
var server_ip: String = "127.0.0.1"
var server_port: int = 9999

func _ready():
    tcp = StreamPeerTCP.new()
    tcp.set_no_delay(true)  # 禁用 Nagle 算法

func _process(delta):
    # 轮询 TCP 连接
    tcp.poll()
    
    var status = tcp.get_status()
    match status:
        StreamPeerTCP.STATUS_NONE:
            pass  # 未连接
        StreamPeerTCP.STATUS_CONNECTING:
            pass  # 连接中
        StreamPeerTCP.STATUS_CONNECTED:
            if not connected:
                connected = true
                _on_connected()
        StreamPeerTCP.STATUS_ERROR:
            if connected:
                connected = false
                _on_disconnected()

func connect_to_server(ip: String, port: int):
    # 连接到服务器
    server_ip = ip
    server_port = port
    tcp.connect_to_host(ip, port)

func disconnect_from_server():
    # 断开连接
    tcp.disconnect_from_host()
    connected = false

func send_data(data: String):
    # 发送数据
    if connected:
        tcp.put_string(data)

func send_bytes(data: PackedByteArray):
    # 发送字节
    if connected:
        tcp.put_data(data)

func receive_data() -> String:
    # 接收数据
    if connected:
        return tcp.get_string()
    return ""

func _on_connected():
    print("Connected to server")

func _on_disconnected():
    print("Disconnected from server")
```

### 2.2 TCPServer

```gdscript
# TCP 服务器
class_name TCPServerController

extends Node

var server: TCPServer
var clients: Array = []
var port: int = 9999

func _ready():
    server = TCPServer.new()

func _process(delta):
    # 监听新连接
    if server.is_connection_available():
        var client = server.take_connection()
        clients.append(client)
        _on_client_connected(clients.size() - 1)
    
    # 处理客户端数据
    for i in range(clients.size() - 1, -1, -1):
        var client: StreamPeerTCP = clients[i]
        client.poll()
        
        if client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
            clients.remove_at(i)
            _on_client_disconnected(i)
        else:
            var data = client.get_string()
            if data != "":
                _on_client_data(i, data)

func start_server(port: int):
    # 启动服务器
    self.port = port
    var error = server.listen(port)
    if error == OK:
        print("Server started on port ", port)
    else:
        print("Failed to start server: ", error)

func stop_server():
    # 停止服务器
    server.stop()
    clients.clear()
    print("Server stopped")

func send_to_client(client_idx: int, data: String):
    # 发送到客户端
    if client_idx >= 0 and client_idx < clients.size():
        clients[client_idx].put_string(data)

func send_to_all(data: String):
    # 发送到所有客户端
    for client in clients:
        client.put_string(data)

func _on_client_connected(client_idx: int):
    print("Client connected: ", client_idx)

func _on_client_disconnected(client_idx: int):
    print("Client disconnected: ", client_idx)

func _on_client_data(client_idx: int, data: String):
    print("Client ", client_idx, " data: ", data)
```

### 2.3 TCP 聊天示例

```gdscript
# TCP 聊天客户端
class_name TCPChatClient

extends TCPClient

signal message_received(message: String)
signal connected_to_server
signal disconnected_from_server

func _on_connected():
    connected = true
    connected_to_server.emit()

func _on_disconnected():
    connected = false
    disconnected_from_server.emit()

func send_message(message: String):
    # 发送消息
    if connected:
        send_data("MSG:" + message)

func _process(delta):
    super._process(delta)
    
    if connected:
        var data = receive_data()
        if data != "":
            if data.begins_with("MSG:"):
                message_received.emit(data.substr(4))
```

---

## 3. UDP 网络

### 3.1 PacketPeerUDP

```gdscript
# UDP 客户端
class_name UDPClient

extends Node

var udp: PacketPeerUDP
var connected: bool = false
var server_ip: String = "127.0.0.1"
var server_port: int = 9999

func _ready():
    udp = PacketPeerUDP.new()

func _process(delta):
    # 处理 UDP 包
    while udp.get_available_packet_count() > 0:
        var packet = udp.get_packet()
        _on_packet_received(packet)

func connect_to_server(ip: String, port: int):
    # 连接到服务器
    server_ip = ip
    server_port = port
    udp.connect_to_host(ip, port)
    connected = true

func disconnect_from_server():
    # 断开连接
    udp.close()
    connected = false

func send_data(data: PackedByteArray):
    # 发送数据
    if connected:
        udp.put_packet(data)

func send_string(data: String):
    # 发送字符串
    if connected:
        udp.put_string(data)

func receive_packet() -> PackedByteArray:
    # 接收包
    if udp.get_available_packet_count() > 0:
        return udp.get_packet()
    return PackedByteArray()

func _on_packet_received(packet: PackedByteArray):
    print("Received packet: ", packet.size(), " bytes")
```

### 3.2 UDPServer

```gdscript
# UDP 服务器
class_name UDPServerController

extends Node

var server: UDPServer
var clients: Dictionary = {}  # peer_id -> PacketPeerUDP
var port: int = 9999

func _ready():
    server = UDPServer.new()

func _process(delta):
    # 监听新连接
    server.poll()
    
    # 处理数据包
    while server.get_available_packet_count() > 0:
        var packet = server.get_packet()
        var peer = server.get_packet_peer()
        _on_packet_received(peer, packet)

func start_server(port: int):
    # 启动服务器
    self.port = port
    var error = server.listen(port)
    if error == OK:
        print("UDP Server started on port ", port)
    else:
        print("Failed to start UDP server: ", error)

func stop_server():
    # 停止服务器
    server.close()
    clients.clear()
    print("UDP Server stopped")

func send_to_peer(peer: int, data: PackedByteArray):
    # 发送到对等点
    server.put_packet_to_peer(peer, data)

func send_to_all(data: PackedByteArray):
    # 发送到所有对等点
    for peer in clients:
        server.put_packet_to_peer(peer, data)

func _on_packet_received(peer: int, packet: PackedByteArray):
    if not clients.has(peer):
        clients[peer] = true
        _on_client_connected(peer)
    
    print("Received from peer ", peer, ": ", packet.size(), " bytes")
```

### 3.3 UDP 游戏同步示例

```gdscript
# UDP 游戏同步
class_name UDPGameSync

extends UDPClient

signal state_updated(state: Dictionary)

var local_state: Dictionary = {}
var remote_state: Dictionary = {}

func send_state(state: Dictionary):
    # 发送状态
    local_state = state
    var data = var_to_bytes(state)
    send_data(data)

func _on_packet_received(packet: PackedByteArray):
    var state = bytes_to_var(packet)
    if state is Dictionary:
        remote_state = state
        state_updated.emit(state)

func get_remote_state() -> Dictionary:
    return remote_state

func interpolate_state(from: Dictionary, to: Dictionary, t: float) -> Dictionary:
    # 插值状态
    var result = {}
    for key in from:
        if from[key] is Vector3 and to.has(key):
            result[key] = from[key].lerp(to[key], t)
        elif from[key] is float and to.has(key):
            result[key] = lerp(from[key], to[key], t)
        else:
            result[key] = from[key]
    return result
```

---

## 4. WebSocket

### 4.1 WebSocket 客户端

```gdscript
# WebSocket 客户端
class_name WebSocketClientController

extends Node

var ws: WebSocket
var connected: bool = false
var url: String = "ws://localhost:9999"

signal connected_to_server
signal disconnected_from_server
signal data_received(data: String)

func _ready():
    ws = WebSocket.new()

func _process(delta):
    ws.poll()
    
    var state = ws.get_ready_state()
    match state:
        WebSocket.STATE_OPEN:
            if not connected:
                connected = true
                connected_to_server.emit()
            
            # 处理接收的数据
            while ws.get_available_packet_count() > 0:
                var packet = ws.get_packet()
                data_received.emit(packet.get_string_from_utf8())
        
        WebSocket.STATE_CLOSED:
            if connected:
                connected = false
                disconnected_from_server.emit()

func connect_to_server(server_url: String):
    # 连接到服务器
    url = server_url
    ws.connect_to_url(server_url)

func disconnect_from_server():
    # 断开连接
    ws.close()
    connected = false

func send_data(data: String):
    # 发送数据
    if connected:
        ws.send_text(data)

func send_binary(data: PackedByteArray):
    # 发送二进制数据
    if connected:
        ws.send(data)
```

### 4.2 WebSocketServer

```gdscript
# WebSocket 服务器
class_name WebSocketServerController

extends Node

var server: WebSocketServer
var clients: Dictionary = {}  # peer_id -> WebSocket
var port: int = 9999

signal client_connected(peer_id: int)
signal client_disconnected(peer_id: int)
signal client_data(peer_id: int, data: String)

func _ready():
    server = WebSocketServer.new()

func _process(delta):
    server.poll()
    
    # 处理客户端
    for peer_id in server.get_peers():
        var ws = server.get_peer(peer_id)
        ws.poll()
        
        var state = ws.get_ready_state()
        if state == WebSocket.STATE_OPEN:
            if not clients.has(peer_id):
                clients[peer_id] = ws
                client_connected.emit(peer_id)
            
            # 处理数据
            while ws.get_available_packet_count() > 0:
                var packet = ws.get_packet()
                client_data.emit(peer_id, packet.get_string_from_utf8())
        
        elif state == WebSocket.STATE_CLOSED:
            if clients.has(peer_id):
                clients.erase(peer_id)
                client_disconnected.emit(peer_id)

func start_server(server_port: int):
    # 启动服务器
    port = server_port
    var error = server.listen(port)
    if error == OK:
        print("WebSocket Server started on port ", port)
    else:
        print("Failed to start WebSocket server: ", error)

func stop_server():
    # 停止服务器
    server.stop()
    clients.clear()
    print("WebSocket Server stopped")

func send_to_peer(peer_id: int, data: String):
    # 发送到对等点
    if server.has_peer(peer_id):
        server.get_peer(peer_id).send_text(data)

func send_to_all(data: String):
    # 发送到所有对等点
    for peer_id in clients:
        send_to_peer(peer_id, data)
```

---

## 5. HTTP 请求

### 5.1 HTTPClient

```gdscript
# HTTP 客户端
class_name HTTPClientController

extends Node

var http: HTTPClient
var connected: bool = false

func _ready():
    http = HTTPClient.new()

func _process(delta):
    http.poll()
    
    var status = http.get_status()
    match status:
        HTTPClient.STATUS_CONNECTING:
            pass
        HTTPClient.STATUS_CONNECTED:
            connected = true
        HTTPClient.STATUS_REQUESTING:
            pass
        HTTPClient.STATUS_BODY:
            # 处理响应体
            var response = http.get_response_body_as_string()
            _on_response(response)
        HTTPClient.STATUS_DISCONNECTED:
            connected = false

func request(url: String, method: int = HTTPClient.METHOD_GET, headers: PackedStringArray = [], body: String = ""):
    # 发送请求
    var uri = URI.new()
    uri.parse(url)
    
    http.connect_to_host(uri.get_host(), uri.get_port())
    
    # 等待连接
    while http.get_status() == HTTPClient.STATUS_CONNECTING or http.get_status() == HTTPClient.STATUS_CONNECTED:
        http.poll()
        await get_tree().process_frame
    
    # 发送请求
    if method == HTTPClient.METHOD_GET:
        http.request(method, url, headers)
    else:
        http.request(method, url, headers, body)

func _on_response(response: String):
    print("Response: ", response)
```

### 5.2 HTTPRequest 节点

```gdscript
# HTTPRequest 节点封装
class_name HTTPRequestWrapper

extends HTTPRequest

signal request_completed_with_data(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray)

func _ready():
    request_completed.connect(_on_request_completed)

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
    request_completed_with_data.emit(result, response_code, headers, body)

func get_json(url: String):
    # GET 请求 JSON
    request(url)

func post_json(url: String, data: Dictionary):
    # POST 请求 JSON
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(data)
    request(url, headers, HTTPClient.METHOD_POST, body)

func parse_json_response(body: PackedByteArray) -> Dictionary:
    # 解析 JSON 响应
    var json = JSON.new()
    var error = json.parse(body.get_string_from_utf8())
    if error == OK:
        return json.data
    return {}
```

### 5.3 REST API 客户端

```gdscript
# REST API 客户端
class_name RESTAPIClient

extends Node

var base_url: String = "https://api.example.com"
var http_request: HTTPRequest

signal api_response(endpoint: String, data: Dictionary)

func _ready():
    http_request = HTTPRequest.new()
    add_child(http_request)
    http_request.request_completed.connect(_on_request_completed)

func get(endpoint: String):
    # GET 请求
    http_request.request(base_url + endpoint)

func post(endpoint: String, data: Dictionary):
    # POST 请求
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(data)
    http_request.request(base_url + endpoint, headers, HTTPClient.METHOD_POST, body)

func put(endpoint: String, data: Dictionary):
    # PUT 请求
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(data)
    http_request.request(base_url + endpoint, headers, HTTPClient.METHOD_PUT, body)

func delete(endpoint: String):
    # DELETE 请求
    http_request.request(base_url + endpoint, [], HTTPClient.METHOD_DELETE)

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
    var json = JSON.new()
    var error = json.parse(body.get_string_from_utf8())
    var data = json.data if error == OK else {}
    
    # 提取 endpoint
    var endpoint = http_request.get_requested_url().replace(base_url, "")
    api_response.emit(endpoint, data)
```

---

## 6. 多人游戏网络

### 6.1 NetworkedMultiplayerENet

```gdscript
# ENet 多人网络
class_name ENetMultiplayer

extends Node

var peer: NetworkedMultiplayerENet
var is_server: bool = false
var port: int = 9999

signal server_started
signal server_stopped
signal connected_to_server
signal disconnected_from_server
signal peer_connected(id: int)
signal peer_disconnected(id: int)

func _ready():
    multiplayer.peer_connected.connect(_on_peer_connected)
    multiplayer.peer_disconnected.connect(_on_peer_disconnected)
    multiplayer.connected_to_server.connect(_on_connected_to_server)
    multiplayer.connection_failed.connect(_on_connection_failed)

func create_server(server_port: int, max_clients: int = 32):
    # 创建服务器
    port = server_port
    peer = NetworkedMultiplayerENet.new()
    var error = peer.create_server(port, max_clients)
    if error == OK:
        is_server = true
        multiplayer.multiplayer_peer = peer
        server_started.emit()
        print("Server started on port ", port)
    else:
        print("Failed to create server: ", error)

func join_server(ip: String, server_port: int):
    # 加入服务器
    port = server_port
    peer = NetworkedMultiplayerENet.new()
    var error = peer.create_client(ip, port)
    if error == OK:
        is_server = false
        multiplayer.multiplayer_peer = peer
        print("Joining server at ", ip, ":", port)
    else:
        print("Failed to join server: ", error)

func stop_network():
    # 停止网络
    if peer:
        peer.close()
        peer = null
    multiplayer.multiplayer_peer = null
    is_server = false
    server_stopped.emit()

func _on_peer_connected(id: int):
    peer_connected.emit(id)

func _on_peer_disconnected(id: int):
    peer_disconnected.emit(id)

func _on_connected_to_server():
    connected_to_server.emit()

func _on_connection_failed():
    disconnected_from_server.emit()
```

### 6.2 RPC 系统

```gdscript
# RPC 示例
class_name RPCExample

extends Node

@rpc("any_peer", "reliable")
func player_joined(player_id: int, player_name: String):
    # 玩家加入
    print("Player joined: ", player_name, " (ID: ", player_id, ")")

@rpc("authority", "reliable")
func player_left(player_id: int):
    # 玩家离开
    print("Player left: ", player_id)

@rpc("any_peer", "unreliable")
func player_position(player_id: int, position: Vector3):
    # 玩家位置
    _update_player_position(player_id, position)

@rpc("authority", "reliable")
func spawn_player(player_id: int, spawn_position: Vector3):
    # 生成玩家
    _spawn_player(player_id, spawn_position)

@rpc("any_peer", "reliable")
func chat_message(player_id: int, message: String):
    # 聊天消息
    print("Player ", player_id, ": ", message)

func _update_player_position(player_id: int, position: Vector3):
    # 更新玩家位置
    pass

func _spawn_player(player_id: int, spawn_position: Vector3):
    # 生成玩家
    pass
```

### 6.3 网络同步

```gdscript
# 网络同步
class_name NetworkSynchronizer

extends Node

@export var sync_interval: float = 0.05  # 20Hz
var sync_timer: float = 0.0

@rpc("any_peer", "unreliable")
func sync_state(state: Dictionary):
    # 同步状态
    _apply_state(state)

func _process(delta):
    if multiplayer.is_server():
        sync_timer += delta
        if sync_timer >= sync_interval:
            sync_timer = 0.0
            _broadcast_state()

func _broadcast_state():
    # 广播状态
    var state = _get_game_state()
    sync_state.rpc(state)

func _get_game_state() -> Dictionary:
    # 获取游戏状态
    return {
        "players": _get_player_states(),
        "time": Time.get_ticks_msec()
    }

func _get_player_states() -> Array:
    # 获取玩家状态
    var states = []
    # 收集所有玩家状态
    return states

func _apply_state(state: Dictionary):
    # 应用状态
    if state.has("players"):
        for player_state in state.players:
            _apply_player_state(player_state)

func _apply_player_state(state: Dictionary):
    # 应用玩家状态
    pass
```

---

## 7. 网络系统优化

### 7.1 网络性能监控

```gdscript
# 网络性能监控
class_name NetworkPerformanceMonitor

extends Node

var packets_sent: int = 0
var packets_received: int = 0
var bytes_sent: int = 0
var bytes_received: int = 0
var rtt_history: Array = []

func _ready():
    # 开始监控
    start_monitoring()

func start_monitoring():
    var timer = Timer.new()
    timer.wait_time = 1.0
    timer.connect("timeout", self, "_update_stats")
    add_child(timer)
    timer.start()

func _update_stats():
    # 更新统计
    # 这里可以从网络对等点获取实际统计
    pass

func record_packet_sent(bytes: int):
    packets_sent += 1
    bytes_sent += bytes

func record_packet_received(bytes: int):
    packets_received += 1
    bytes_received += bytes

func record_rtt(rtt_ms: float):
    rtt_history.append(rtt_ms)
    if rtt_history.size() > 60:
        rtt_history.remove_at(0)

func get_average_rtt() -> float:
    if rtt_history.size() == 0:
        return 0.0
    
    var total = 0.0
    for rtt in rtt_history:
        total += rtt
    
    return total / rtt_history.size()

func print_stats():
    print("Network Stats:")
    print("- Packets Sent: ", packets_sent)
    print("- Packets Received: ", packets_received)
    print("- Bytes Sent: ", bytes_sent)
    print("- Bytes Received: ", bytes_received)
    print("- Average RTT: ", get_average_rtt(), " ms")
```

### 7.2 网络数据压缩

```gdscript
# 网络数据压缩
class_name NetworkDataCompressor

static func compress_data(data: PackedByteArray) -> PackedByteArray:
    # 压缩数据
    return data.compress(FileAccess.COMPRESSION_DEFLATE)

static func decompress_data(data: PackedByteArray) -> PackedByteArray:
    # 解压数据
    return data.decompress_dynamic(-1, FileAccess.COMPRESSION_DEFLATE)

static func compress_variant(data: Variant) -> PackedByteArray:
    # 压缩变体数据
    var raw = var_to_bytes(data)
    return compress_data(raw)

static func decompress_variant(data: PackedByteArray) -> Variant:
    # 解压变体数据
    var raw = decompress_data(data)
    return bytes_to_var(raw)

static func get_compression_ratio(original: PackedByteArray, compressed: PackedByteArray) -> float:
    # 获取压缩比
    if original.size() == 0:
        return 0.0
    return 1.0 - (float(compressed.size()) / float(original.size()))
```

### 7.3 网络带宽优化

```gdscript
# 网络带宽优化
class_name NetworkBandwidthOptimizer

@export var max_bandwidth_kbps: int = 100
var current_bandwidth: float = 0.0
var bandwidth_history: Array = []

func _ready():
    # 开始带宽监控
    start_monitoring()

func start_monitoring():
    var timer = Timer.new()
    timer.wait_time = 0.1
    timer.connect("timeout", self, "_update_bandwidth")
    add_child(timer)
    timer.start()

func _update_bandwidth():
    # 更新带宽
    # 这里应该从网络对等点获取实际带宽
    pass

func should_send_data(data_size: int) -> bool:
    # 检查是否应该发送数据
    var predicted_bandwidth = current_bandwidth + (data_size * 8 / 1000.0)  # 转换为 kbps
    return predicted_bandwidth < max_bandwidth_kbps

func get_optimal_send_interval(data_size: int) -> float:
    # 获取最佳发送间隔
    if current_bandwidth >= max_bandwidth_kbps:
        return 1.0  # 等待 1 秒
    
    var available_bandwidth = max_bandwidth_kbps - current_bandwidth
    var bits_per_second = available_bandwidth * 1000
    var bits_needed = data_size * 8
    
    if bits_per_second <= 0:
        return 1.0
    
    return float(bits_needed) / float(bits_per_second)
```

---

## 8. 实践：完整网络系统

### 8.1 基础网络系统

```gdscript
# 基础网络系统
class_name BasicNetworkSystem

extends Node

var enet_peer: NetworkedMultiplayerENet
var is_server: bool = false
var port: int = 9999

func _ready():
    # 设置网络信号
    multiplayer.peer_connected.connect(_on_peer_connected)
    multiplayer.peer_disconnected.connect(_on_peer_disconnected)
    multiplayer.connected_to_server.connect(_on_connected_to_server)

func create_server(server_port: int, max_clients: int = 32):
    # 创建服务器
    port = server_port
    enet_peer = NetworkedMultiplayerENet.new()
    var error = enet_peer.create_server(port, max_clients)
    if error == OK:
        is_server = true
        multiplayer.multiplayer_peer = enet_peer
        print("Server created on port ", port)

func join_server(ip: String, server_port: int):
    # 加入服务器
    port = server_port
    enet_peer = NetworkedMultiplayerENet.new()
    var error = enet_peer.create_client(ip, port)
    if error == OK:
        is_server = false
        multiplayer.multiplayer_peer = enet_peer
        print("Joining server at ", ip, ":", port)

func disconnect_from_network():
    # 断开网络
    if enet_peer:
        enet_peer.close()
        enet_peer = null
    multiplayer.multiplayer_peer = null
    is_server = false

func _on_peer_connected(id: int):
    print("Peer connected: ", id)

func _on_peer_disconnected(id: int):
    print("Peer disconnected: ", id)

func _on_connected_to_server():
    print("Connected to server")
```

### 8.2 高级网络系统

```gdscript
# 高级网络系统
class_name AdvancedNetworkSystem

extends Node

var basic_network: BasicNetworkSystem
var performance_monitor: NetworkPerformanceMonitor
var data_compressor: NetworkDataCompressor
var bandwidth_optimizer: NetworkBandwidthOptimizer

func _ready():
    # 初始化高级网络系统
    basic_network = BasicNetworkSystem.new()
    add_child(basic_network)
    
    performance_monitor = NetworkPerformanceMonitor.new()
    add_child(performance_monitor)
    
    data_compressor = NetworkDataCompressor.new()
    add_child(data_compressor)
    
    bandwidth_optimizer = NetworkBandwidthOptimizer.new()
    add_child(bandwidth_optimizer)

func create_server(port: int, max_clients: int = 32):
    basic_network.create_server(port, max_clients)

func join_server(ip: String, port: int):
    basic_network.join_server(ip, port)

func disconnect():
    basic_network.disconnect_from_network()

func send_compressed_data(data: Variant, peer_id: int = 0):
    # 发送压缩数据
    var compressed = data_compressor.compress_variant(data)
    performance_monitor.record_packet_sent(compressed.size())
    # 实际发送逻辑

func receive_compressed_data(data: PackedByteArray) -> Variant:
    # 接收压缩数据
    performance_monitor.record_packet_received(data.size())
    return data_compressor.decompress_variant(data)

func get_network_stats() -> Dictionary:
    return {
        "is_server": basic_network.is_server,
        "port": basic_network.port,
        "average_rtt": performance_monitor.get_average_rtt()
    }

func print_stats():
    performance_monitor.print_stats()
```

### 8.3 完整网络系统

```gdscript
# 完整网络系统
class_name FullNetworkSystem

extends Node

var basic_system: BasicNetworkSystem
var advanced_system: AdvancedNetworkSystem

func _ready():
    # 初始化完整网络系统
    basic_system = BasicNetworkSystem.new()
    add_child(basic_system)
    
    advanced_system = AdvancedNetworkSystem.new()
    add_child(advanced_system)

func create_server(port: int, max_clients: int = 32):
    advanced_system.create_server(port, max_clients)

func join_server(ip: String, port: int):
    advanced_system.join_server(ip, port)

func disconnect():
    advanced_system.disconnect()

func send_data(data: Variant, peer_id: int = 0):
    # 发送数据
    if advanced_system.bandwidth_optimizer.should_send_data(var_to_bytes(data).size()):
        advanced_system.send_compressed_data(data, peer_id)

func get_stats() -> Dictionary:
    return advanced_system.get_network_stats()

func print_stats():
    advanced_system.print_stats()
```

---

## 📝 本章总结

### 核心要点

1. **TCP 用于可靠连接**，适合数据传输
2. **UDP 用于快速传输**，适合实时游戏
3. **WebSocket 用于 Web 兼容**，适合浏览器游戏
4. **HTTP 用于 Web API**，适合数据请求
5. **ENet 用于多人游戏**，提供可靠 UDP
6. **网络优化**，包括性能监控、数据压缩、带宽优化

### 关键术语

| 术语 | 解释 |
|------|------|
| TCP | 传输控制协议，可靠连接 |
| UDP | 用户数据报协议，快速传输 |
| WebSocket | Web 套接字，双向通信 |
| HTTP | 超文本传输协议，Web 请求 |
| ENet | 可靠 UDP 库，多人游戏 |
| RPC | 远程过程调用，网络函数调用 |
| RTT | 往返时间，网络延迟 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Networking](https://docs.godotengine.org/en/stable/tutorials/networking/index.html)
- **源码位置**: `servers/`
- **技术博客**: [Godot Networking Guide](https://godotengine.org/article/networking-guide/)

---

## 📋 下一章预告

**第 50 篇：网络通信协议**

- TCP 协议详解
- UDP 协议详解
- WebSocket 协议
- 协议优化

---

*写作时间：2026-03-20*  
*字数：约 13,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 17:00*