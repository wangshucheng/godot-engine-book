# 第 49 篇：网络系统

> **本卷定位**: 第六卷 网络系统（5 篇）  
> **前置知识**: 无  
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
│  6. WebSocketPeer：WebSocket 连接对等（4.x 客户端类）        │
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
│  3. WebSocketPeer：WebSocket 连接对等（4.x 客户端 / 服务端侧）│
│  4. HTTPClient：HTTP 客户端                                 │
│  5. HTTPRequest：HTTP 请求节点                              │
│  6. TCPServer：TCP 服务器                                   │
│  7. UDPServer：UDP 服务器                                   │
│  8. ENetMultiplayerPeer：基于 ENet 的多人网络               │
│  9. MultiplayerPeer：多人网络对等基类                       │
│ 10. WebSocketMultiplayerPeer：基于 WebSocket 的多人网络     │
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

### 1.4 平台约束：Web 导出与传输层选型

浏览器**没有原生 UDP/TCP 套接字**，只有 HTTP 与 WebSocket（以及 WebRTC）。官方多人网络文档对此有明确说明：

> the HTML5 platform currently offers WebSockets and WebRTC support but lacks some of the higher-level features, as well as raw access to low-level protocols like TCP and UDP.

这直接决定了选型：

| 目标平台 | 可用的 `MultiplayerPeer` | 说明 |
|----------|--------------------------|------|
| Windows / Linux / macOS / 移动端 | `ENetMultiplayerPeer` | 基于 UDP 的可靠传输，**Web 导出不可用** |
| Web（浏览器） | `WebSocketMultiplayerPeer` | 走 WebSocket（`ws://` / `wss://`），服务端需要单独的 WebSocket 服务器（不能是 Godot 的 Web 导出客户端） |
| Web（浏览器，且需要 P2P） | `WebRTCMultiplayerPeer` | 走 WebRTC DataChannel，需要信令服务器做握手 |

具体限制：

- `ENetMultiplayerPeer` 依赖原始 UDP，**Web 导出下无法工作**。
- `WebSocketPeer.accept_stream()` 的官方文档注明：**"Not supported in Web exports due to browsers' restrictions."** —— 也就是说，4.2 节那套 `TCPServer` + `accept_stream()` 的自建 WebSocket 服务器只能跑在桌面 / 移动端。
- `WebSocketMultiplayerPeer.create_server()` 底层同样是 `TCPServer`，浏览器端无法监听端口，因此**浏览器只能当客户端**；Web 版的权威服务器要部署在常规服务器上（Godot 导出为 Linux 服务端，或任意支持 WebSocket 的后端）。
- Web 导出走 `wss://` 时，TLS 由浏览器的 WebSocket 实现提供；同时要避免混合内容（mixed content）警告，页面必须本身是 HTTPS。
- 移动端（Android）导出时必须在导出预设里勾选 `INTERNET` 权限，否则任何网络通信都会被系统拦掉（Android 与 iOS 的 `WebSocketMultiplayerPeer` 文档中都有这条提醒）。

**结论**：如果项目要同时支持 Web 和原生端，不要把传输层写死。至少要把"选哪个 `MultiplayerPeer`"抽成一个工厂函数，按运行平台返回 `ENetMultiplayerPeer` 或 `WebSocketMultiplayerPeer`；上层 RPC 与同步逻辑完全不用改。

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
        # PacketPeer 没有 put_string()，要用 put_packet() 传字节
        udp.put_packet(data.to_utf8_buffer())

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
var clients: Dictionary = {}  # peer_key -> PacketPeerUDP
var port: int = 9999

func _ready():
    server = UDPServer.new()

func _process(delta):
    # UDPServer 自身只有 poll / listen / take_connection / stop / is_listening /
    # get_local_port / is_connection_available 这几个方法；
    # 收包要用 take_connection() 拿到的 PacketPeerUDP。
    server.poll()

    # 接受新连接
    while server.is_connection_available():
        var conn: PacketPeerUDP = server.take_connection()
        var key := "%s:%d" % [conn.get_packet_ip(), conn.get_packet_port()]
        clients[key] = conn
        print("New UDP peer: ", key)

    # 处理数据包
    for key in clients.keys():
        var peer: PacketPeerUDP = clients[key]
        while peer.get_available_packet_count() > 0:
            var packet := peer.get_packet()
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
    # 停止服务器。UDPServer 用 stop()，close() 是 PacketPeer 的方法。
    server.stop()
    clients.clear()
    print("UDP Server stopped")

func send_to_peer(peer_key: String, data: PackedByteArray):
    # 发送到对等点：PacketPeerUDP.put_packet()
    if clients.has(peer_key):
        clients[peer_key].put_packet(data)

func send_to_all(data: PackedByteArray):
    # 发送到所有对等点
    for peer_key in clients.keys():
        clients[peer_key].put_packet(data)

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

> **类名说明（Godot 3.x → 4.x）**：Godot 3.x 的 `WebSocket`（客户端）与 `WebSocketServer`（服务器）在 **4.x 中已被移除**，官方类参考中不存在 `class_websocket.html` / `class_websocketserver.html`。4.x 里：
> - 客户端 / 服务端侧的**单条连接**用 `WebSocketPeer`（`modules/websocket/websocket_peer.h`，以 `ClassDB::register_custom_instance_class` 注册，因此用 `WebSocketPeer.new()` 实例化）；
> - 面向多人游戏的**对等体**用 `WebSocketMultiplayerPeer`（`modules/websocket/websocket_multiplayer_peer.h`）；
> - 4.x **没有内置 WebSocket 服务器类**，服务端要用 `TCPServer` + `WebSocketPeer.accept_stream()` 自行搭建（见 4.2 节）。

### 4.1 WebSocket 客户端

```gdscript
# WebSocket 客户端
class_name WebSocketClientController

extends Node

var ws: WebSocketPeer
var connected: bool = false
var url: String = "ws://localhost:9999"

signal connected_to_server
signal disconnected_from_server
signal data_received(data: String)
signal binary_received(data: PackedByteArray)

func _ready():
    ws = WebSocketPeer.new()

func _process(delta):
    # WebSocketPeer 必须持续 poll 才会推进握手与收包
    ws.poll()

    var state = ws.get_ready_state()
    match state:
        WebSocketPeer.STATE_OPEN:
            if not connected:
                connected = true
                connected_to_server.emit()

            # get_available_packet_count / get_packet 来自 PacketPeer 基类
            while ws.get_available_packet_count() > 0:
                var packet = ws.get_packet()
                # was_string_packet() 判断上一帧是文本帧还是二进制帧
                if ws.was_string_packet():
                    data_received.emit(packet.get_string_from_utf8())
                else:
                    binary_received.emit(packet)

        WebSocketPeer.STATE_CLOSING:
            # 继续 poll 才能完成关闭握手
            pass

        WebSocketPeer.STATE_CLOSED:
            if connected:
                connected = false
                disconnected_from_server.emit()
                print("WebSocket closed: ", ws.get_close_code(), " ", ws.get_close_reason())

func connect_to_server(server_url: String, protocols: PackedStringArray = []):
    # 连接到服务器
    url = server_url
    # 子协议必须先声明，connect_to_url 的第二参是 TLSOptions，不是子协议数组
    ws.supported_protocols = protocols
    var err := ws.connect_to_url(server_url)
    if err != OK:
        push_error("WebSocket 连接失败：%d" % err)

func disconnect_from_server():
    # 断开连接
    ws.close()
    connected = false

func send_data(data: String):
    # 发送文本帧
    if connected:
        ws.send_text(data)

func send_binary(data: PackedByteArray):
    # 发送二进制帧（send 的第二参 write_mode 默认是 WRITE_MODE_BINARY）
    if connected:
        ws.send(data, WebSocketPeer.WRITE_MODE_BINARY)
```

**要点**

- `connect_to_url(url, tls_client_options)` 的**第二实参是 `TLSOptions`**（4.3 签名：`connect_to_url(const String &p_url, Ref<TLSOptions> p_options = Ref<TLSOptions>())`），不是子协议数组；子协议要写 `WebSocketPeer.supported_protocols` **属性**（没有同名 setter 方法）。
- 文本用 `send_text()`，二进制用 `send()` / `put_packet()`；`wss://` 的 TLS 由 `TLSOptions` 校验证书。
- `get_ready_state()` 的四个常量是 `WebSocketPeer.STATE_CONNECTING / STATE_OPEN / STATE_CLOSING / STATE_CLOSED`。

### 4.2 WebSocket 服务端（TCPServer + accept_stream）

4.x 删除了 `WebSocketServer` 类。服务端的正确做法是：先用 `TCPServer` 接受 TCP 连接，再把流交给 `WebSocketPeer.accept_stream()` 完成 HTTP 握手。

```gdscript
# WebSocket 服务端（4.x：无内置 WebSocketServer 类）
class_name WebSocketHostController

extends Node

var tcp_server: TCPServer
# peer_id -> WebSocketPeer（已完成握手并进入 STATE_OPEN）
var clients: Dictionary = {}
var port: int = 9999

signal client_connected(peer_id: int)
signal client_disconnected(peer_id: int)
signal client_data(peer_id: int, data: String)

func _ready():
    tcp_server = TCPServer.new()

func _process(delta):
    # 1. 接受新的 TCP 连接
    while tcp_server.is_connection_available():
        var stream := tcp_server.take_connection()
        if stream == null:
            continue
        # accept_stream 会用该 TCP 流完成 WebSocket 握手
        var ws := WebSocketPeer.new()
        if ws.accept_stream(stream) != OK:
            push_warning("WebSocket 握手失败")
            continue
        clients[stream.get_instance_id()] = ws

    # 2. 推进每个连接的状态并收包
    for key in clients.keys():
        var ws: WebSocketPeer = clients[key]
        ws.poll()

        match ws.get_ready_state():
            WebSocketPeer.STATE_OPEN:
                while ws.get_available_packet_count() > 0:
                    var packet := ws.get_packet()
                    if ws.was_string_packet():
                        client_data.emit(key, packet.get_string_from_utf8())
            WebSocketPeer.STATE_CLOSED:
                clients.erase(key)
                client_disconnected.emit(key)

func start_server(server_port: int):
    port = server_port
    var error := tcp_server.listen(port)
    if error == OK:
        print("WebSocket Server started on port ", port)
    else:
        push_error("启动 WebSocket 服务器失败：%d" % error)

func stop_server():
    tcp_server.stop()
    clients.clear()
    print("WebSocket Server stopped")

func send_to_peer(peer_id: int, data: String):
    if clients.has(peer_id):
        clients[peer_id].send_text(data)

func send_to_all(data: String):
    for peer_id in clients:
        send_to_peer(peer_id, data)
```

**要点**

- `accept_stream(stream)` 要求传入 `TCPServer.take_connection()` 取到的 `StreamPeerTCP`，或 `StreamPeerTLS.accept_stream()` 得到的 TLS 流；它会自己完成 HTTP Upgrade 握手，之后 `poll()` 才能进入 `STATE_OPEN`。
- 该方法**在 Web 导出中不可用**（浏览器限制），Web 端请改用 `WebSocketMultiplayerPeer`。
- 上面用 `stream.get_instance_id()` 作为 peer 键只是为了示例；实际项目应自己维护一个自增 ID 到 peer 的映射。

**如果只是想跑多人游戏而不打算自己实现协议**：直接用 `WebSocketMultiplayerPeer` 即可，它是现成的 `MultiplayerPeer` 实现：

```gdscript
var peer := WebSocketMultiplayerPeer.new()
peer.create_client("ws://127.0.0.1:9999")   # 客户端
# peer.create_server(9999)                   # 服务端
multiplayer.multiplayer_peer = peer
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
            # HTTPRequest 没有 get_response_body_as_string()，
            # 响应体要从 request_completed 信号给的字节数组里取
            var response = body.get_string_from_utf8()
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
    
    # 构造相对路径：主机与端口已经由 connect_to_host() 指定，
    # HTTPClient.request() 的 url 参数必须是「路径 + 查询串」，
    # 传完整 URL 会拼出 "GET https://host/path HTTP/1.1" 这样的非法请求行。
    var path := uri.get_path()
    if path.is_empty():
        path = "/"
    var query := uri.get_query()
    if not query.is_empty():
        path += "?" + query
    
    # 发送请求
    if method == HTTPClient.METHOD_GET:
        http.request(method, path, headers)
    else:
        http.request(method, path, headers, body)

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
# HTTPRequest 没有 get_requested_url()，请求哪个 endpoint 需要自己记录
var _pending_endpoint: String = ""

signal api_response(endpoint: String, data: Dictionary)

func _ready():
    http_request = HTTPRequest.new()
    add_child(http_request)
    http_request.request_completed.connect(_on_request_completed)

func get(endpoint: String):
    # GET 请求
    _pending_endpoint = endpoint
    http_request.request(base_url + endpoint)

func post(endpoint: String, data: Dictionary):
    # POST 请求
    _pending_endpoint = endpoint
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(data)
    http_request.request(base_url + endpoint, headers, HTTPClient.METHOD_POST, body)

func put(endpoint: String, data: Dictionary):
    # PUT 请求
    _pending_endpoint = endpoint
    var headers = ["Content-Type: application/json"]
    var body = JSON.stringify(data)
    http_request.request(base_url + endpoint, headers, HTTPClient.METHOD_PUT, body)

func delete(endpoint: String):
    # DELETE 请求
    _pending_endpoint = endpoint
    http_request.request(base_url + endpoint, [], HTTPClient.METHOD_DELETE)

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
    var json = JSON.new()
    var error = json.parse(body.get_string_from_utf8())
    var data = json.data if error == OK else {}
    
    # HTTPRequest 4.3 只提供 request/request_raw/cancel_request/get_downloaded_bytes/
    # get_body_size/get_http_client_status/set_* ，没有 get_requested_url()；
    # 因此 endpoint 由调用方在发请求前写入 _pending_endpoint。
    api_response.emit(_pending_endpoint, data)
```

---

## 6. 多人游戏网络

### 6.1 ENetMultiplayerPeer

```gdscript
# ENet 多人网络
class_name ENetMultiplayer

extends Node

var peer: ENetMultiplayerPeer
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
    multiplayer.server_disconnected.connect(_on_server_disconnected)

func create_server(server_port: int, max_clients: int = 32,
                   max_channels: int = 0, in_bandwidth: int = 0, out_bandwidth: int = 0):
    # 创建服务器
    # 4.3 签名：create_server(port, max_clients=32, max_channels=0, in_bandwidth=0, out_bandwidth=0)
    port = server_port
    peer = ENetMultiplayerPeer.new()
    var error = peer.create_server(port, max_clients, max_channels, in_bandwidth, out_bandwidth)
    if error == OK:
        is_server = true
        multiplayer.multiplayer_peer = peer
        server_started.emit()
        print("Server started on port ", port)
    else:
        print("Failed to create server: ", error)

func join_server(ip: String, server_port: int,
                 channel_count: int = 0, in_bandwidth: int = 0, out_bandwidth: int = 0):
    # 加入服务器
    # 4.3 签名：create_client(address, port, channel_count=0, in_bandwidth=0, out_bandwidth=0, local_port=0)
    port = server_port
    peer = ENetMultiplayerPeer.new()
    var error = peer.create_client(ip, port, channel_count, in_bandwidth, out_bandwidth)
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

func _on_server_disconnected():
    disconnected_from_server.emit()
```

**ENet 可调参数（4.3 头文件 `modules/enet/enet_multiplayer_peer.h`）**

| 参数 | 位置 | 语义 |
|------|------|------|
| `max_clients` | `create_server` 第 2 参 | 最大连接数，默认 32 |
| `max_channels` | `create_server` 第 3 参 | ENet 通道数上限；**0 表示不限制**（ENet 上限 255） |
| `channel_count` | `create_client` 第 3 参 | 客户端向服务器申请的通道数，语义同上 |
| `in_bandwidth` | 第 4 参 | **入站**限速，单位 **字节/秒**；0 表示不限制 |
| `out_bandwidth` | 第 5 参 | **出站**限速，单位 **字节/秒**；0 表示不限制 |

**通道语义**

- Godot 在 ENet 通道 **0（可靠）与 1（非可靠）** 上保留了两条系统通道，`@rpc` 未指定 `transfer_channel` 时按传输模式落到对应的那条上。
- `@rpc` 的 `transfer_channel = 1, 2, 3…` 会映射到 ENet 通道 `2, 3, 4…`（引擎内部偏移 2）。
- 因此**可用通道数 = `max_channels` - 2**（减去两条系统通道）。只打算用默认通道时保持 0（不限制）即可；刻意限制通道数可以防止客户端滥用额外通道。
- 限速语义：`in_bandwidth` / `out_bandwidth` 不只是"发送速率"上限，ENet 用它计算可靠传输的**窗口大小**（`windowSize`），设得过小会让可靠通道吞吐骤降。

> ⚠️ **已知参数错位（4.3 / 4.4 / 4.5 都存在）**：这些版本的 `ENetMultiplayerPeer.create_server()` 在调用底层 `ENetConnection.create_host_bound()` 时把 `max_channels` 传到了"入站带宽"槽位上，导致服务端 `max_channels` 不生效（ENet 通道数始终取上限 255）、而 `in_bandwidth` 被忽略。**master 分支已修正为正确映射**（`create_host_bound(bind_ip, port, max_clients, max_channels + 2, in_bandwidth, out_bandwidth)`）。需要精确控制通道数时，请在创建后用 `peer.get_host().get_max_channels()` 校验实际值；客户端侧的 `channel_count` 不受此影响。

**可靠 / 非可靠通道怎么选**

| 场景 | `transfer_mode` | 说明 |
|------|----------------|------|
| 聊天、房间状态、生成/销毁 | `"reliable"` | 确认重传，代价是延迟；通道 0 的可靠分支 |
| 位置、姿态、输入上报 | `"unreliable"` | 不重传，丢了就丢了，下一帧会覆盖 |
| 需要顺序但不重传 | `"unreliable_ordered"` | 乱序到达的旧包会被丢弃，**包大小不一致时容易连带丢包** |
| 聊天与玩法要互不阻塞 | `"reliable"` + `transfer_channel = 1` | 聊天走独立通道，不会拖累可靠通道的确认流 |

### 6.2 RPC 系统

```gdscript
# RPC 示例
class_name RPCExample

extends Node

# 本卷统一使用三参式写法：@rpc(mode, sync, transfer_mode)
# 第四个位置 transfer_channel 需要时再补，且必须放在最后。

@rpc("any_peer", "call_remote", "reliable")
func player_joined(player_id: int, player_name: String):
    # 玩家加入
    print("Player joined: ", player_name, " (ID: ", player_id, ")")

@rpc("authority", "call_remote", "reliable")
func player_left(player_id: int):
    # 玩家离开
    print("Player left: ", player_id)

@rpc("any_peer", "call_remote", "unreliable")
func player_position(player_id: int, position: Vector3):
    # 玩家位置
    _update_player_position(player_id, position)

@rpc("authority", "call_remote", "reliable")
func spawn_player(player_id: int, spawn_position: Vector3):
    # 生成玩家
    _spawn_player(player_id, spawn_position)

@rpc("any_peer", "call_remote", "reliable")
func chat_message(player_id: int, message: String):
    # 聊天消息
    print("Player ", player_id, ": ", message)

# 走独立通道的聊天 RPC：通道 1 与默认通道（0）互不干扰，
# 聊天包不会被可靠通道的确认流拖住。
@rpc("any_peer", "call_remote", "reliable", 1)
func chat_message_on_channel(player_id: int, message: String):
    print("[chat ch1] Player ", player_id, ": ", message)

func _update_player_position(player_id: int, position: Vector3):
    # 更新玩家位置
    pass

func _spawn_player(player_id: int, spawn_position: Vector3):
    # 生成玩家
    pass
```

**`@rpc` 四个位置的确切含义**

官方注解签名是 `@rpc(mode, sync, transfer_mode, transfer_channel)`。解析器按**关键字类别**而不是位置来匹配参数，因此 `@rpc("any_peer", "reliable")` 这种两参式也能跑，但第二个字符串会被识别成 `sync` 而不是 `transfer_mode`——极易误读。**本卷一律写三参式**，需要自定义通道时再补第四个位置。

| 位置 | 名称 | 取值 | 含义 |
|------|------|------|------|
| 1 | `mode` | `"authority"` / `"any_peer"` | `"authority"`：只有该节点的**多人权威**（默认是服务器）能远程调用；可用 `Node.set_multiplayer_authority()` 逐节点改。`"any_peer"`：任意客户端都能调用，适合上报玩家输入 |
| 2 | `sync` | `"call_remote"` / `"call_local"` | `"call_remote"`：本端不执行（服务器同时也是玩家时需要 `"call_local"`） |
| 3 | `transfer_mode` | `"unreliable"` / `"unreliable_ordered"` / `"reliable"` | 见下方"可靠 / 非可靠通道怎么选" |
| 4 | `transfer_channel` | 整数，0 起 | 0 = 默认通道；1、2、3… = 额外通道。**必须放在最后** |

**`transfer_channel` 语义**

- 默认通道（索引 0）实际上对应**三条**独立通道：可靠 / 非可靠有序 / 非可靠各一条，互不阻塞（这是 ENet 的通道 0 与 1）。
- `transfer_channel = 1` 会把这条 RPC 送到**独立的 ENet 通道**上（引擎内部映射到 ENet 通道 2），与默认通道的可靠确认流完全分离。典型用法：把聊天 / 语音这类"重要但不紧急"的可靠消息挪到独立通道，避免它阻塞玩法数据的可靠确认。
- 通道数量受 `ENetMultiplayerPeer.create_server()` 的 `max_channels` 限制（见 6.1 节），可用通道数 = `max_channels - 2`。
- 官方文档提醒：`unreliable_ordered` 在**包大小不一致**时容易连带丢包（迟到的旧包被丢弃会连带影响后续包），如果要用有序非可靠传输，最好把同类数据放在同一通道上，使该通道上的包大小尽量一致。

### 6.3 网络同步

```gdscript
# 网络同步（自研 RPC 方案）
# 类名不叫 NetworkSynchronizer，以免与引擎内置的 MultiplayerSynchronizer 概念混淆。
class_name RpcStateSynchronizer

extends Node

@export var sync_interval: float = 0.05  # 20Hz
var sync_timer: float = 0.0

# 服务端广播权威状态：mode 必须是 authority，
# 用 any_peer 会让任意客户端都能在客户端上调用这个"接收权威状态"的接口。
@rpc("authority", "call_remote", "unreliable")
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

### 6.4 断线重连、超时与心跳

`peer.close()` 只是"主动断开"，它**不覆盖**真实网络里的断线。客户端与服务端都要能识别"连接没了"，并决定是重连、回到大厅还是直接退出。

**MultiplayerAPI 提供的四个连接信号**（客户端侧）：

| 信号 | 何时发出 | 典型处理 |
|------|----------|----------|
| `connected_to_server()` | 握手成功，已连上服务器 | 进入游戏场景 |
| `connection_failed()` | 尝试连接但失败（服务器没起 / 地址错 / 被拒绝） | 提示并退避重试 |
| `server_disconnected()` | 已连接后服务器消失 | 清空本地状态，退避重连 |
| `peer_connected(id)` / `peer_disconnected(id)` | 任一 peer 加入 / 离开 | 维护玩家列表（两端都会收到） |

```gdscript
# 断线重连 + 心跳
class_name ReconnectingClient

extends Node

const SERVER_URL := "127.0.0.1"
const SERVER_PORT := 9999
const PING_INTERVAL := 2.0
const PONG_TIMEOUT := 6.0
# 退避序列（秒）：失败后依次等待，重试成功则重置
const BACKOFF := [1.0, 2.0, 4.0, 8.0, 15.0]

var peer: ENetMultiplayerPeer
var attempt: int = 0
var last_pong_ms: int = 0
var reconnect_timer: Timer

signal connection_state_changed(state: String)

func _ready():
    multiplayer.connected_to_server.connect(_on_connected)
    multiplayer.connection_failed.connect(_on_failed)
    multiplayer.server_disconnected.connect(_on_disconnected)

    reconnect_timer = Timer.new()
    reconnect_timer.one_shot = true
    reconnect_timer.timeout.connect(_try_connect)
    add_child(reconnect_timer)

    _try_connect()

func _try_connect():
    peer = ENetMultiplayerPeer.new()
    var err := peer.create_client(SERVER_URL, SERVER_PORT)
    if err != OK:
        push_warning("连接失败：%d" % err)
        _schedule_retry()
        return
    multiplayer.multiplayer_peer = peer
    connection_state_changed.emit("connecting")

func _schedule_retry():
    attempt = mini(attempt + 1, BACKOFF.size())
    var delay: float = BACKOFF[attempt - 1]
    reconnect_timer.start(delay)
    connection_state_changed.emit("retrying in %.0fs" % delay)

func _on_connected():
    attempt = 0  # 连上后重置退避
    last_pong_ms = Time.get_ticks_msec()
    connection_state_changed.emit("connected")

func _on_failed():
    multiplayer.multiplayer_peer = null
    _schedule_retry()

func _on_disconnected():
    multiplayer.multiplayer_peer = null
    connection_state_changed.emit("disconnected")
    _schedule_retry()
```

**心跳的作用**：ENet 本身会检测连接丢失并触发 `server_disconnected()`，但**服务端"活着但不再回你消息"**这种情况（例如中间有 NAT 设备静默丢弃、或者对端进程卡死）需要应用层心跳来发现。做法是客户端定时发一个轻量的 ping RPC，服务端收到就回 pong；客户端超过 `PONG_TIMEOUT` 没收到 pong 就主动断开并进入重连流程。

```gdscript
# 心跳（配合上面的 ReconnectingClient 使用）
@rpc("any_peer", "call_remote", "reliable")
func _heartbeat_ping(client_time_ms: int) -> void:
    if multiplayer.is_server():
        _heartbeat_pong.rpc_id(multiplayer.get_remote_sender_id(), client_time_ms)

@rpc("authority", "call_remote", "reliable")
func _heartbeat_pong(client_time_ms: int) -> void:
    if multiplayer.is_server():
        return
    last_pong_ms = Time.get_ticks_msec()
```

**超时参数在哪**

- `ENetMultiplayerPeer` 本身没有暴露"连接超时"参数，连接失败由 `connection_failed()` 通知；应用层要自己做超时兜底（例如 `create_client()` 后 10 秒仍未收到 `connected_to_server()` 就当作失败重试）。
- `WebSocketMultiplayerPeer` 有显式的 `handshake_timeout` 属性（默认 3.0 秒），超过握手机制的 peer 会被丢弃。
- 真正决定"多久算掉线"的是**应用层心跳间隔 × 容许丢失次数**，而不是引擎参数。

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
    timer.timeout.connect(_update_stats)
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
    timer.timeout.connect(_update_bandwidth)
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

var enet_peer: ENetMultiplayerPeer
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
    enet_peer = ENetMultiplayerPeer.new()
    var error = enet_peer.create_server(port, max_clients)
    if error == OK:
        is_server = true
        multiplayer.multiplayer_peer = enet_peer
        print("Server created on port ", port)

func join_server(ip: String, server_port: int):
    # 加入服务器
    port = server_port
    enet_peer = ENetMultiplayerPeer.new()
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
- **源码位置**（Godot 4.7.2）：
  - `scene/main/multiplayer_api.cpp`、`scene/main/multiplayer_peer.h` —— 多人 API 与对等体基类
  - `modules/multiplayer/` —— `scene_multiplayer.h`（场景多人实现）、`multiplayer_spawner`、`multiplayer_synchronizer`
  - `modules/enet/enet_multiplayer_peer.h`、`modules/enet/enet_connection.h` —— ENet 传输层
  - `modules/websocket/websocket_peer.h`、`modules/websocket/websocket_multiplayer_peer.h` —— WebSocket 传输层
  - `core/io/packet_peer.h`、`core/io/http_client.h` —— 传输原语
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
*字数：约 2,400 字（不含代码块）（不含代码块）*  
*状态：✅ 完成*  

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）


**上一篇**: [第 62 篇：音频分析和语音系统](/articles/62-audio-analysis-and-voice.md)
**下一篇**: [第 50 篇：网络通信协议](/articles/50-network-protocols.md)
---

*最后更新：2026-03-20 17:00*
