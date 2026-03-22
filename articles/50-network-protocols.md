# 第 40 篇：网络通信协议

> **本卷定位**: 第六卷 网络系统（8 篇）  
> **前置知识**: 第 49 章 网络系统  
> **难度等级**: ⭐⭐⭐⭐⭐ 专家级

---

## 📖 本章导读

网络通信协议是网络系统的核心，定义了数据如何在网络中传输、打包、解包以及如何处理错误。理解各种网络协议的特性和适用场景，对于构建高效、可靠的网络应用至关重要。

本章将深入探讨 TCP、UDP、WebSocket 等主流网络协议的细节，以及如何在 Godot 中高效实现和优化这些协议。

---

## 🎯 学习目标

- 理解 TCP 协议的详细机制
- 掌握 UDP 协议的特性
- 学会 WebSocket 协议应用
- 熟悉自定义协议设计
- 掌握协议优化技术

---

## 1. TCP 协议详解

### 1.1 TCP 协议基础

```
TCP 协议特性:
┌─────────────────────────────────────────────────────────────┐
│                      TCP 协议特性                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 面向连接：建立连接后传输数据                           │
│  2. 可靠传输：保证数据完整到达                             │
│  3. 有序传输：数据按发送顺序到达                           │
│  4. 流量控制：防止发送方压倒接收方                         │
│  5. 拥塞控制：防止网络拥塞                                 │
│  6. 全双工：双向同时通信                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 TCP 连接管理

```gdscript
# TCP 连接管理器
class_name TCPConnectionManager

extends Node

var tcp: StreamPeerTCP
var connection_state: int = 0  # 0: None, 1: Connecting, 2: Connected, 3: Error

enum State {
    NONE,
    CONNECTING,
    CONNECTED,
    ERROR
}

func _ready():
    tcp = StreamPeerTCP.new()
    tcp.set_no_delay(true)  # 禁用 Nagle 算法，降低延迟

func _process(delta):
    tcp.poll()
    _update_state()

func _update_state():
    var status = tcp.get_status()
    match status:
        StreamPeerTCP.STATUS_NONE:
            connection_state = State.NONE
        StreamPeerTCP.STATUS_CONNECTING:
            connection_state = State.CONNECTING
        StreamPeerTCP.STATUS_CONNECTED:
            connection_state = State.CONNECTED
        StreamPeerTCP.STATUS_ERROR:
            connection_state = State.ERROR

func connect_to_host(ip: String, port: int):
    # 连接到主机
    tcp.connect_to_host(ip, port)

func disconnect_from_host():
    # 断开连接
    tcp.disconnect_from_host()

func send_data(data: PackedByteArray) -> Error:
    # 发送数据
    return tcp.put_data(data)

func send_string(data: String) -> Error:
    # 发送字符串
    return tcp.put_string(data)

func receive_data() -> PackedByteArray:
    # 接收数据
    var result = tcp.get_data(tcp.get_available_bytes())
    if result[0] == OK:
        return result[1]
    return PackedByteArray()

func receive_string() -> String:
    # 接收字符串
    return tcp.get_string()

func get_connection_state() -> int:
    return connection_state

func is_connected() -> bool:
    return connection_state == State.CONNECTED
```

### 1.3 TCP 数据包格式

```gdscript
# TCP 数据包格式
class_name TCPPacketFormat

# 数据包结构:
# [4 bytes: length][data]

static func pack_data(data: PackedByteArray) -> PackedByteArray:
    # 打包数据（添加长度前缀）
    var packet = PackedByteArray()
    
    # 添加长度（4 字节，大端序）
    var length = data.size()
    packet.append((length >> 24) & 0xFF)
    packet.append((length >> 16) & 0xFF)
    packet.append((length >> 8) & 0xFF)
    packet.append(length & 0xFF)
    
    # 添加数据
    packet.append_array(data)
    
    return packet

static func unpack_data(packet: PackedByteArray) -> PackedByteArray:
    # 解包数据（移除长度前缀）
    if packet.size() < 4:
        return PackedByteArray()
    
    # 读取长度
    var length = (packet[0] << 24) | (packet[1] << 16) | (packet[2] << 8) | packet[3]
    
    # 返回数据
    return packet.slice(4, 4 + length)

static func pack_string(data: String) -> PackedByteArray:
    # 打包字符串
    return pack_data(data.to_utf8_buffer())

static func unpack_string(packet: PackedByteArray) -> String:
    # 解包字符串
    var data = unpack_data(packet)
    return data.get_string_from_utf8()

static func pack_variant(data: Variant) -> PackedByteArray:
    # 打包变体
    return pack_data(var_to_bytes(data))

static func unpack_variant(packet: PackedByteArray) -> Variant:
    # 解包变体
    var data = unpack_data(packet)
    return bytes_to_var(data)
```

### 1.4 TCP 消息协议

```gdscript
# TCP 消息协议
class_name TCPMessageProtocol

extends Node

var tcp: StreamPeerTCP
var receive_buffer: PackedByteArray = PackedByteArray()

signal message_received(message: Dictionary)
signal connected
signal disconnected

func _ready():
    tcp = StreamPeerTCP.new()
    tcp.set_no_delay(true)

func _process(delta):
    tcp.poll()
    
    if tcp.get_status() == StreamPeerTCP.STATUS_CONNECTED:
        # 接收数据
        while tcp.get_available_bytes() > 0:
            var data = tcp.get_data(tcp.get_available_bytes())
            if data[0] == OK:
                receive_buffer.append_array(data[1])
                _process_buffer()

func _process_buffer():
    # 处理接收缓冲区
    while receive_buffer.size() >= 4:
        # 读取消息长度
        var length = (receive_buffer[0] << 24) | (receive_buffer[1] << 16) | (receive_buffer[2] << 8) | receive_buffer[3]
        
        # 检查是否有完整消息
        if receive_buffer.size() >= 4 + length:
            # 提取消息数据
            var message_data = receive_buffer.slice(4, 4 + length)
            receive_buffer = receive_buffer.slice(4 + length)
            
            # 解析消息
            var message = bytes_to_var(message_data)
            if message is Dictionary:
                message_received.emit(message)
        else:
            break

func connect_to_server(ip: String, port: int):
    tcp.connect_to_host(ip, port)

func disconnect_from_server():
    tcp.disconnect_from_host()

func send_message(message: Dictionary):
    if tcp.get_status() == StreamPeerTCP.STATUS_CONNECTED:
        var data = var_to_bytes(message)
        var length = data.size()
        
        # 构建数据包
        var packet = PackedByteArray()
        packet.append((length >> 24) & 0xFF)
        packet.append((length >> 16) & 0xFF)
        packet.append((length >> 8) & 0xFF)
        packet.append(length & 0xFF)
        packet.append_array(data)
        
        tcp.put_data(packet)
```

---

## 2. UDP 协议详解

### 2.1 UDP 协议基础

```
UDP 协议特性:
┌─────────────────────────────────────────────────────────────┐
│                      UDP 协议特性                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 无连接：不需要建立连接                                 │
│  2. 不可靠：不保证数据到达                                 │
│  3. 无序：数据可能乱序到达                                 │
│  4. 低延迟：没有握手和确认开销                             │
│  5. 轻量级：包头小，开销低                                 │
│  6. 支持广播：可以发送到多个接收者                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 UDP 数据包格式

```gdscript
# UDP 数据包格式
class_name UDPPacketFormat

# UDP 数据包结构:
# [2 bytes: sequence][1 byte: type][data]

enum PacketType {
    DATA = 0,
    ACK = 1,
    NACK = 2,
    PING = 3,
    PONG = 4
}

static func pack_data(sequence: int, type: int, data: PackedByteArray) -> PackedByteArray:
    # 打包 UDP 数据
    var packet = PackedByteArray()
    
    # 序列号（2 字节）
    packet.append((sequence >> 8) & 0xFF)
    packet.append(sequence & 0xFF)
    
    # 类型（1 字节）
    packet.append(type & 0xFF)
    
    # 数据
    packet.append_array(data)
    
    return packet

static func unpack_data(packet: PackedByteArray) -> Dictionary:
    # 解包 UDP 数据
    if packet.size() < 3:
        return {}
    
    # 读取序列号
    var sequence = (packet[0] << 8) | packet[1]
    
    # 读取类型
    var type = packet[2]
    
    # 读取数据
    var data = packet.slice(3)
    
    return {
        "sequence": sequence,
        "type": type,
        "data": data
    }

static func pack_ack(sequence: int) -> PackedByteArray:
    # 打包确认包
    return pack_data(sequence, PacketType.ACK, PackedByteArray())

static func pack_nack(sequence: int) -> PackedByteArray:
    # 打包否认包
    return pack_data(sequence, PacketType.NACK, PackedByteArray())

static func pack_ping(timestamp: int) -> PackedByteArray:
    # 打包 Ping 包
    var data = PackedByteArray()
    data.append((timestamp >> 24) & 0xFF)
    data.append((timestamp >> 16) & 0xFF)
    data.append((timestamp >> 8) & 0xFF)
    data.append(timestamp & 0xFF)
    return pack_data(0, PacketType.PING, data)

static func pack_pong(timestamp: int) -> PackedByteArray:
    # 打包 Pong 包
    var data = PackedByteArray()
    data.append((timestamp >> 24) & 0xFF)
    data.append((timestamp >> 16) & 0xFF)
    data.append((timestamp >> 8) & 0xFF)
    data.append(timestamp & 0xFF)
    return pack_data(0, PacketType.PONG, data)
```

### 2.3 可靠 UDP 实现

```gdscript
# 可靠 UDP 实现
class_name ReliableUDP

extends Node

var udp: PacketPeerUDP
var sequence: int = 0
var ack_sequence: int = 0
var pending_packets: Dictionary = {}  # sequence -> {data, time}
var received_packets: Array = []
var rtt_samples: Array = []

const MAX_PENDING = 100
const TIMEOUT_MS = 1000
const MAX_RTT_SAMPLES = 60

signal packet_delivered(sequence: int)
signal packet_lost(sequence: int)

func _ready():
    udp = PacketPeerUDP.new()

func _process(delta):
    # 处理接收的包
    while udp.get_available_packet_count() > 0:
        var packet = udp.get_packet()
        _handle_packet(packet)
    
    # 检查超时
    _check_timeouts()

func _handle_packet(packet: PackedByteArray):
    var parsed = UDPPacketFormat.unpack_data(packet)
    
    if parsed.is_empty():
        return
    
    var type = parsed.type
    var seq = parsed.sequence
    
    match type:
        UDPPacketFormat.PacketType.DATA:
            # 发送确认
            _send_ack(seq)
            # 处理数据
            _on_data_received(seq, parsed.data)
        
        UDPPacketFormat.PacketType.ACK:
            # 处理确认
            _handle_ack(seq)
        
        UDPPacketFormat.PacketType.NACK:
            # 处理否认
            _handle_nack(seq)
        
        UDPPacketFormat.PacketType.PING:
            # 处理 Ping
            _handle_ping(parsed.data)
        
        UDPPacketFormat.PacketType.PONG:
            # 处理 Pong
            _handle_pong(parsed.data)

func _send_data(data: PackedByteArray):
    # 发送数据
    if sequence > 65535:
        sequence = 0
    
    var packet = UDPPacketFormat.pack_data(sequence, UDPPacketFormat.PacketType.DATA, data)
    udp.put_packet(packet)
    
    # 保存到待确认队列
    pending_packets[sequence] = {
        "data": data,
        "time": Time.get_ticks_msec()
    }
    
    sequence += 1

func _send_ack(seq: int):
    # 发送确认
    var packet = UDPPacketFormat.pack_ack(seq)
    udp.put_packet(packet)

func _handle_ack(seq: int):
    # 处理确认
    if pending_packets.has(seq):
        pending_packets.erase(seq)
        packet_delivered.emit(seq)

func _handle_nack(seq: int):
    # 处理否认（重传）
    if pending_packets.has(seq):
        var pending = pending_packets[seq]
        _send_data(pending.data)
        pending_packets[seq]["time"] = Time.get_ticks_msec()

func _check_timeouts():
    # 检查超时
    var current_time = Time.get_ticks_msec()
    var to_remove = []
    
    for seq in pending_packets:
        var pending = pending_packets[seq]
        if current_time - pending.time > TIMEOUT_MS:
            to_remove.append(seq)
            # 重传
            _send_data(pending.data)
            pending_packets[seq]["time"] = current_time
    
    # 限制重传次数
    if pending_packets.size() > MAX_PENDING:
        # 丢弃最老的包
        var oldest_seq = -1
        var oldest_time = current_time
        for seq in pending_packets:
            if pending_packets[seq].time < oldest_time:
                oldest_time = pending_packets[seq].time
                oldest_seq = seq
        if oldest_seq >= 0:
            pending_packets.erase(oldest_seq)
            packet_lost.emit(oldest_seq)

func _handle_ping(data: PackedByteArray):
    # 处理 Ping
    if data.size() >= 4:
        var timestamp = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        var packet = UDPPacketFormat.pack_pong(timestamp)
        udp.put_packet(packet)

func _handle_pong(data: PackedByteArray):
    # 处理 Pong
    if data.size() >= 4:
        var timestamp = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        var rtt = Time.get_ticks_msec() - timestamp
        rtt_samples.append(rtt)
        if rtt_samples.size() > MAX_RTT_SAMPLES:
            rtt_samples.pop_front()

func get_average_rtt() -> float:
    # 获取平均 RTT
    if rtt_samples.size() == 0:
        return 0.0
    
    var total = 0.0
    for rtt in rtt_samples:
        total += rtt
    
    return total / rtt_samples.size()

func send_reliable(data: PackedByteArray):
    # 发送可靠数据
    _send_data(data)

func connect_to_host(ip: String, port: int):
    udp.connect_to_host(ip, port)

func listen(port: int):
    udp.bind(port)
```

---

## 3. WebSocket 协议详解

### 3.1 WebSocket 协议基础

```
WebSocket 协议特性:
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket 协议特性                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 全双工：双向同时通信                                   │
│  2. 基于 HTTP：使用 HTTP 握手                              │
│  3. 持久连接：连接保持打开                                 │
│  4. 低开销：包头小（2-14 字节）                            │
│  5. 支持文本和二进制：多种数据类型                         │
│  6. 跨域支持：浏览器友好                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 WebSocket 帧格式

```gdscript
# WebSocket 帧格式
class_name WebSocketFrameFormat

# WebSocket 帧结构:
# [1 byte: FIN + RSV + Opcode]
# [1 byte: MASK + Payload length]
# [0-8 bytes: Extended payload length]
# [0-4 bytes: Masking key]
# [n bytes: Payload data]

enum Opcode {
    CONTINUATION = 0x0,
    TEXT = 0x1,
    BINARY = 0x2,
    CLOSE = 0x8,
    PING = 0x9,
    PONG = 0xA
}

static func pack_frame(opcode: int, data: PackedByteArray, masked: bool = false) -> PackedByteArray:
    # 打包 WebSocket 帧
    var frame = PackedByteArray()
    
    # 第一字节：FIN + RSV + Opcode
    var byte1 = 0x80 | opcode  # FIN=1, RSV=0
    frame.append(byte1)
    
    # 第二字节：MASK + Payload length
    var length = data.size()
    var byte2 = 0x00
    if masked:
        byte2 = 0x80
    
    if length < 126:
        byte2 |= length
        frame.append(byte2)
    elif length < 65536:
        byte2 |= 126
        frame.append(byte2)
        frame.append((length >> 8) & 0xFF)
        frame.append(length & 0xFF)
    else:
        byte2 |= 127
        frame.append(byte2)
        for i in range(7, -1, -1):
            frame.append((length >> (i * 8)) & 0xFF)
    
    # 如果需要掩码
    if masked:
        # 生成随机掩码
        var mask_key = PackedByteArray()
        for i in range(4):
            mask_key.append(randi() & 0xFF)
        frame.append_array(mask_key)
        
        # 应用掩码到数据
        var masked_data = PackedByteArray()
        for i in range(data.size()):
            masked_data.append(data[i] ^ mask_key[i % 4])
        frame.append_array(masked_data)
    else:
        frame.append_array(data)
    
    return frame

static func unpack_frame(frame: PackedByteArray) -> Dictionary:
    # 解包 WebSocket 帧
    if frame.size() < 2:
        return {}
    
    var offset = 0
    
    # 第一字节
    var byte1 = frame[offset]
    offset += 1
    var fin = (byte1 >> 7) & 0x01
    var opcode = byte1 & 0x0F
    
    # 第二字节
    var byte2 = frame[offset]
    offset += 1
    var masked = (byte2 >> 7) & 0x01
    var length = byte2 & 0x7F
    
    # 扩展长度
    if length == 126:
        if frame.size() < offset + 2:
            return {}
        length = (frame[offset] << 8) | frame[offset + 1]
        offset += 2
    elif length == 127:
        if frame.size() < offset + 8:
            return {}
        length = 0
        for i in range(8):
            length = (length << 8) | frame[offset + i]
        offset += 8
    
    # 掩码键
    var mask_key = PackedByteArray()
    if masked:
        if frame.size() < offset + 4:
            return {}
        for i in range(4):
            mask_key.append(frame[offset])
            offset += 1
    
    # 数据
    if frame.size() < offset + length:
        return {}
    var data = frame.slice(offset, offset + length)
    
    # 解掩码
    if masked and mask_key.size() == 4:
        for i in range(data.size()):
            data[i] = data[i] ^ mask_key[i % 4]
    
    return {
        "fin": fin,
        "opcode": opcode,
        "length": length,
        "data": data
    }
```

### 3.3 WebSocket 客户端实现

```gdscript
# WebSocket 客户端实现
class_name WebSocketClientImpl

extends Node

var ws: WebSocket
var connection_state: int = 0

enum State {
    CONNECTING,
    OPEN,
    CLOSING,
    CLOSED
}

signal connected
signal disconnected
signal text_received(text: String)
signal binary_received(data: PackedByteArray)
signal error_occurred(code: int)

func _ready():
    ws = WebSocket.new()

func _process(delta):
    ws.poll()
    _update_state()

func _update_state():
    var state = ws.get_ready_state()
    match state:
        WebSocket.STATE_CONNECTING:
            connection_state = State.CONNECTING
        WebSocket.STATE_OPEN:
            if connection_state != State.OPEN:
                connection_state = State.OPEN
                connected.emit()
            _process_messages()
        WebSocket.STATE_CLOSING:
            connection_state = State.CLOSING
        WebSocket.STATE_CLOSED:
            if connection_state != State.CLOSED:
                connection_state = State.CLOSED
                disconnected.emit()

func _process_messages():
    while ws.get_available_packet_count() > 0:
        var packet = ws.get_packet()
        var frame = WebSocketFrameFormat.unpack_frame(packet)
        
        if frame.is_empty():
            continue
        
        match frame.opcode:
            WebSocketFrameFormat.Opcode.TEXT:
                text_received.emit(frame.data.get_string_from_utf8())
            WebSocketFrameFormat.Opcode.BINARY:
                binary_received.emit(frame.data)
            WebSocketFrameFormat.Opcode.PING:
                # 自动回复 Pong
                var pong_frame = WebSocketFrameFormat.pack_frame(WebSocketFrameFormat.Opcode.PONG, frame.data)
                ws.send(pong_frame)
            WebSocketFrameFormat.Opcode.PONG:
                pass  # 忽略 Pong
            WebSocketFrameFormat.Opcode.CLOSE:
                ws.close()

func connect_to_url(url: String, protocols: PackedStringArray = []):
    ws.connect_to_url(url, protocols)

func disconnect_from_url():
    ws.close()

func send_text(text: String):
    if connection_state == State.OPEN:
        ws.send_text(text)

func send_binary(data: PackedByteArray):
    if connection_state == State.OPEN:
        ws.send(data)

func get_state() -> int:
    return connection_state
```

---

## 4. 自定义协议设计

### 4.1 二进制协议设计

```gdscript
# 二进制协议设计
class_name BinaryProtocol

# 协议格式:
# [1 byte: version]
# [2 bytes: message type]
# [4 bytes: sequence]
# [4 bytes: timestamp]
# [n bytes: payload]

const VERSION = 1

static func pack_message(msg_type: int, sequence: int, payload: PackedByteArray) -> PackedByteArray:
    # 打包消息
    var packet = PackedByteArray()
    
    # 版本
    packet.append(VERSION)
    
    # 消息类型（2 字节）
    packet.append((msg_type >> 8) & 0xFF)
    packet.append(msg_type & 0xFF)
    
    # 序列号（4 字节）
    packet.append((sequence >> 24) & 0xFF)
    packet.append((sequence >> 16) & 0xFF)
    packet.append((sequence >> 8) & 0xFF)
    packet.append(sequence & 0xFF)
    
    # 时间戳（4 字节）
    var timestamp = Time.get_ticks_msec()
    packet.append((timestamp >> 24) & 0xFF)
    packet.append((timestamp >> 16) & 0xFF)
    packet.append((timestamp >> 8) & 0xFF)
    packet.append(timestamp & 0xFF)
    
    # 负载
    packet.append_array(payload)
    
    return packet

static func unpack_message(packet: PackedByteArray) -> Dictionary:
    # 解包消息
    if packet.size() < 13:
        return {}
    
    var offset = 0
    
    # 版本
    var version = packet[offset]
    offset += 1
    
    if version != VERSION:
        return {}
    
    # 消息类型
    var msg_type = (packet[offset] << 8) | packet[offset + 1]
    offset += 2
    
    # 序列号
    var sequence = (packet[offset] << 24) | (packet[offset + 1] << 16) | (packet[offset + 2] << 8) | packet[offset + 3]
    offset += 4
    
    # 时间戳
    var timestamp = (packet[offset] << 24) | (packet[offset + 1] << 16) | (packet[offset + 2] << 8) | packet[offset + 3]
    offset += 4
    
    # 负载
    var payload = packet.slice(offset)
    
    return {
        "version": version,
        "type": msg_type,
        "sequence": sequence,
        "timestamp": timestamp,
        "payload": payload
    }

static func calculate_checksum(data: PackedByteArray) -> int:
    # 计算校验和
    var sum = 0
    for byte in data:
        sum += byte
    return sum & 0xFFFF
```

### 4.2 消息类型定义

```gdscript
# 消息类型定义
class_name MessageTypes

# 消息类型
enum Type {
    # 系统消息 (0-99)
    PING = 0,
    PONG = 1,
    ACK = 2,
    NACK = 3,
    
    # 连接消息 (100-199)
    CONNECT_REQUEST = 100,
    CONNECT_RESPONSE = 101,
    DISCONNECT = 102,
    
    # 游戏消息 (200-299)
    PLAYER_JOIN = 200,
    PLAYER_LEAVE = 201,
    PLAYER_STATE = 202,
    GAME_STATE = 203,
    
    # 聊天消息 (300-399)
    CHAT_MESSAGE = 300,
    CHAT_BROADCAST = 301,
    
    # 错误消息 (400-499)
    ERROR = 400
}

static func get_type_name(type: int) -> String:
    match type:
        Type.PING: return "PING"
        Type.PONG: return "PONG"
        Type.ACK: return "ACK"
        Type.NACK: return "NACK"
        Type.CONNECT_REQUEST: return "CONNECT_REQUEST"
        Type.CONNECT_RESPONSE: return "CONNECT_RESPONSE"
        Type.DISCONNECT: return "DISCONNECT"
        Type.PLAYER_JOIN: return "PLAYER_JOIN"
        Type.PLAYER_LEAVE: return "PLAYER_LEAVE"
        Type.PLAYER_STATE: return "PLAYER_STATE"
        Type.GAME_STATE: return "GAME_STATE"
        Type.CHAT_MESSAGE: return "CHAT_MESSAGE"
        Type.CHAT_BROADCAST: return "CHAT_BROADCAST"
        Type.ERROR: return "ERROR"
        _: return "UNKNOWN"
```

### 4.3 协议处理器

```gdscript
# 协议处理器
class_name ProtocolHandler

extends Node

var sequence: int = 0
var pending_acks: Dictionary = {}

signal message_handled(type: int, data: Dictionary)

func _ready():
    pass

func send_ping(peer):
    # 发送 Ping
    var payload = PackedByteArray()
    var timestamp = Time.get_ticks_msec()
    payload.append((timestamp >> 24) & 0xFF)
    payload.append((timestamp >> 16) & 0xFF)
    payload.append((timestamp >> 8) & 0xFF)
    payload.append(timestamp & 0xFF)
    _send_message(peer, MessageTypes.Type.PING, payload)

func send_pong(peer, timestamp: int):
    # 发送 Pong
    var payload = PackedByteArray()
    payload.append((timestamp >> 24) & 0xFF)
    payload.append((timestamp >> 16) & 0xFF)
    payload.append((timestamp >> 8) & 0xFF)
    payload.append(timestamp & 0xFF)
    _send_message(peer, MessageTypes.Type.PONG, payload)

func send_connect_request(peer, player_name: String):
    # 发送连接请求
    var payload = player_name.to_utf8_buffer()
    _send_message(peer, MessageTypes.Type.CONNECT_REQUEST, payload)

func send_player_state(peer, state: Dictionary):
    # 发送玩家状态
    var payload = var_to_bytes(state)
    _send_message(peer, MessageTypes.Type.PLAYER_STATE, payload)

func send_chat_message(peer, message: String):
    # 发送聊天消息
    var payload = message.to_utf8_buffer()
    _send_message(peer, MessageTypes.Type.CHAT_MESSAGE, payload)

func _send_message(peer, msg_type: int, payload: PackedByteArray):
    # 发送消息
    sequence += 1
    var packet = BinaryProtocol.pack_message(msg_type, sequence, payload)
    # 实际发送逻辑（取决于底层传输）
    _on_packet_sent(sequence)

func _on_packet_sent(seq: int):
    # 包已发送
    pending_acks[seq] = Time.get_ticks_msec()

func handle_message(msg: Dictionary):
    # 处理消息
    var type = msg.type
    
    match type:
        MessageTypes.Type.PING:
            _handle_ping(msg)
        MessageTypes.Type.PONG:
            _handle_pong(msg)
        MessageTypes.Type.ACK:
            _handle_ack(msg)
        MessageTypes.Type.CONNECT_REQUEST:
            _handle_connect_request(msg)
        MessageTypes.Type.PLAYER_STATE:
            _handle_player_state(msg)
        MessageTypes.Type.CHAT_MESSAGE:
            _handle_chat_message(msg)
        _:
            message_handled.emit(type, msg)

func _handle_ping(msg: Dictionary):
    # 处理 Ping
    var timestamp = bytes_to_int(msg.payload.slice(0, 4))
    # 回复 Pong
    # send_pong(peer, timestamp)

func _handle_pong(msg: Dictionary):
    # 处理 Pong
    var timestamp = bytes_to_int(msg.payload.slice(0, 4))
    var rtt = Time.get_ticks_msec() - timestamp
    # 记录 RTT

func _handle_ack(msg: Dictionary):
    # 处理确认
    var seq = bytes_to_int(msg.payload.slice(0, 4))
    if pending_acks.has(seq):
        pending_acks.erase(seq)

func _handle_connect_request(msg: Dictionary):
    # 处理连接请求
    var player_name = msg.payload.get_string_from_utf8()
    message_handled.emit(MessageTypes.Type.CONNECT_REQUEST, {"name": player_name})

func _handle_player_state(msg: Dictionary):
    # 处理玩家状态
    var state = bytes_to_var(msg.payload)
    message_handled.emit(MessageTypes.Type.PLAYER_STATE, state)

func _handle_chat_message(msg: Dictionary):
    # 处理聊天消息
    var message = msg.payload.get_string_from_utf8()
    message_handled.emit(MessageTypes.Type.CHAT_MESSAGE, {"message": message})

func bytes_to_int(data: PackedByteArray) -> int:
    if data.size() < 4:
        return 0
    return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
```

---

## 5. 协议优化

### 5.1 数据压缩

```gdscript
# 数据压缩优化
class_name ProtocolCompression

static func compress_packet(data: PackedByteArray) -> PackedByteArray:
    # 压缩数据包
    if data.size() < 100:
        # 小数据不压缩
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

static func decompress_packet(data: PackedByteArray) -> PackedByteArray:
    # 解压数据包
    if data.size() == 0:
        return data
    
    if data[0] == 0x01:
        # 压缩数据
        return data.slice(1).decompress_dynamic(-1, FileAccess.COMPRESSION_DEFLATE)
    
    return data

static func should_compress(data: PackedByteArray) -> bool:
    # 判断是否应该压缩
    return data.size() > 100
```

### 5.2 数据序列化优化

```gdscript
# 数据序列化优化
class_name ProtocolSerialization

static func pack_vector3(v: Vector3) -> PackedByteArray:
    # 打包 Vector3（12 字节）
    var data = PackedByteArray()
    
    # X（4 字节 float）
    var x_bytes = encode_float(v.x)
    data.append_array(x_bytes)
    
    # Y（4 字节 float）
    var y_bytes = encode_float(v.y)
    data.append_array(y_bytes)
    
    # Z（4 字节 float）
    var z_bytes = encode_float(v.z)
    data.append_array(z_bytes)
    
    return data

static func unpack_vector3(data: PackedByteArray) -> Vector3:
    # 解包 Vector3
    if data.size() < 12:
        return Vector3.ZERO
    
    var x = decode_float(data.slice(0, 4))
    var y = decode_float(data.slice(4, 8))
    var z = decode_float(data.slice(8, 12))
    
    return Vector3(x, y, z)

static func pack_quaternion(q: Quaternion) -> PackedByteArray:
    # 打包 Quaternion（16 字节）
    var data = PackedByteArray()
    data.append_array(encode_float(q.x))
    data.append_array(encode_float(q.y))
    data.append_array(encode_float(q.z))
    data.append_array(encode_float(q.w))
    return data

static func unpack_quaternion(data: PackedByteArray) -> Quaternion:
    # 解包 Quaternion
    if data.size() < 16:
        return Quaternion.IDENTITY
    
    var x = decode_float(data.slice(0, 4))
    var y = decode_float(data.slice(4, 8))
    var z = decode_float(data.slice(8, 12))
    var w = decode_float(data.slice(12, 16))
    
    return Quaternion(x, y, z, w)

static func pack_transform3d(t: Transform3D) -> PackedByteArray:
    # 打包 Transform3D（48 字节）
    var data = PackedByteArray()
    data.append_array(pack_vector3(t.origin))
    data.append_array(pack_vector3(t.basis.x))
    data.append_array(pack_vector3(t.basis.y))
    data.append_array(pack_vector3(t.basis.z))
    return data

static func unpack_transform3d(data: PackedByteArray) -> Transform3D:
    # 解包 Transform3D
    if data.size() < 48:
        return Transform3D.IDENTITY
    
    var origin = unpack_vector3(data.slice(0, 12))
    var x = unpack_vector3(data.slice(12, 24))
    var y = unpack_vector3(data.slice(24, 36))
    var z = unpack_vector3(data.slice(36, 48))
    
    return Transform3D(Basis(x, y, z), origin)

static func encode_float(value: float) -> PackedByteArray:
    # 编码 float
    var data = PackedByteArray()
    data.resize(4)
    data.encode_float(0, value)
    return data

static func decode_float(data: PackedByteArray) -> float:
    # 解码 float
    return data.decode_float(0)
```

### 5.3 带宽优化

```gdscript
# 带宽优化
class_name BandwidthOptimizer

@export var max_bandwidth_bps: int = 100000  # 100 kbps
var current_bandwidth: float = 0.0
var bandwidth_window: Array = []
var window_size: float = 1.0  # 1 秒窗口

func record_sent(bytes: int):
    # 记录发送的字节
    var current_time = Time.get_ticks_msec() / 1000.0
    bandwidth_window.append({"time": current_time, "bytes": bytes})
    _cleanup_window(current_time)
    _update_bandwidth()

func _cleanup_window(current_time: float):
    # 清理过期数据
    var cutoff = current_time - window_size
    bandwidth_window = bandwidth_window.filter(func(item): return item.time > cutoff)

func _update_bandwidth():
    # 更新带宽
    var total_bytes = 0
    for item in bandwidth_window:
        total_bytes += item.bytes
    current_bandwidth = total_bytes / window_size

func can_send(bytes: int) -> bool:
    # 检查是否可以发送
    var predicted = (current_bandwidth + bytes) / window_size
    return predicted * 8 <= max_bandwidth_bps

func get_delay_for_bytes(bytes: int) -> float:
    # 获取发送延迟
    if current_bandwidth * 8 >= max_bandwidth_bps:
        return 1.0
    
    var available = (max_bandwidth_bps / 8.0) - current_bandwidth
    if available <= 0:
        return 1.0
    
    return float(bytes) / available
```

---

## 6. 实践：完整协议系统

### 6.1 游戏网络协议

```gdscript
# 游戏网络协议
class_name GameNetworkProtocol

extends ProtocolHandler

enum GameMessageType {
    PLAYER_MOVE = 500,
    PLAYER_ACTION = 501,
    GAME_SYNC = 502,
    SCORE_UPDATE = 503
}

func send_player_move(peer, position: Vector3, rotation: float):
    # 发送玩家移动
    var payload = PackedByteArray()
    payload.append_array(ProtocolSerialization.pack_vector3(position))
    payload.append_array(encode_float(rotation))
    _send_message(peer, GameMessageType.PLAYER_MOVE, payload)

func send_player_action(peer, action: int):
    # 发送玩家动作
    var payload = PackedByteArray()
    payload.append((action >> 24) & 0xFF)
    payload.append((action >> 16) & 0xFF)
    payload.append((action >> 8) & 0xFF)
    payload.append(action & 0xFF)
    _send_message(peer, GameMessageType.PLAYER_ACTION, payload)

func send_game_sync(peer, game_state: Dictionary):
    # 发送游戏同步
    var payload = var_to_bytes(game_state)
    _send_message(peer, GameMessageType.GAME_SYNC, payload)

func send_score_update(peer, player_id: int, score: int):
    # 发送分数更新
    var payload = PackedByteArray()
    payload.append((player_id >> 24) & 0xFF)
    payload.append((player_id >> 16) & 0xFF)
    payload.append((player_id >> 8) & 0xFF)
    payload.append(player_id & 0xFF)
    payload.append((score >> 24) & 0xFF)
    payload.append((score >> 16) & 0xFF)
    payload.append((score >> 8) & 0xFF)
    payload.append(score & 0xFF)
    _send_message(peer, GameMessageType.SCORE_UPDATE, payload)

func encode_float(value: float) -> PackedByteArray:
    var data = PackedByteArray()
    data.resize(4)
    data.encode_float(0, value)
    return data
```

### 6.2 协议测试工具

```gdscript
# 协议测试工具
class_name ProtocolTestTool

extends Node

var test_results: Dictionary = {}

func test_binary_protocol():
    # 测试二进制协议
    var payload = "Hello, World!".to_utf8_buffer()
    var packet = BinaryProtocol.pack_message(MessageTypes.Type.CHAT_MESSAGE, 1, payload)
    var unpacked = BinaryProtocol.unpack_message(packet)
    
    test_results["binary_protocol"] = {
        "passed": unpacked.type == MessageTypes.Type.CHAT_MESSAGE and unpacked.payload.get_string_from_utf8() == "Hello, World!",
        "original_size": payload.size(),
        "packet_size": packet.size()
    }

func test_websocket_frame():
    # 测试 WebSocket 帧
    var data = "Test".to_utf8_buffer()
    var frame = WebSocketFrameFormat.pack_frame(WebSocketFrameFormat.Opcode.TEXT, data)
    var unpacked = WebSocketFrameFormat.unpack_frame(frame)
    
    test_results["websocket_frame"] = {
        "passed": unpacked.opcode == WebSocketFrameFormat.Opcode.TEXT and unpacked.data.get_string_from_utf8() == "Test",
        "original_size": data.size(),
        "frame_size": frame.size()
    }

func test_compression():
    # 测试压缩
    var data = "This is a test message that should compress well.".repeat(10).to_utf8_buffer()
    var compressed = ProtocolCompression.compress_packet(data)
    var decompressed = ProtocolCompression.decompress_packet(compressed)
    
    test_results["compression"] = {
        "passed": decompressed == data,
        "original_size": data.size(),
        "compressed_size": compressed.size(),
        "ratio": 1.0 - (float(compressed.size()) / float(data.size()))
    }

func run_all_tests():
    # 运行所有测试
    test_binary_protocol()
    test_websocket_frame()
    test_compression()
    
    # 打印结果
    print("Protocol Test Results:")
    for test_name in test_results:
        var result = test_results[test_name]
        print("- ", test_name, ": ", "PASSED" if result.passed else "FAILED")
        for key in result:
            if key != "passed":
                print("  - ", key, ": ", result[key])
```

---

## 📝 本章总结

### 核心要点

1. **TCP 提供可靠连接**，适合需要保证数据完整性的场景
2. **UDP 提供低延迟**，适合实时游戏和流媒体
3. **WebSocket 提供 Web 兼容**，适合浏览器游戏
4. **自定义协议设计**，根据需求优化协议格式
5. **协议优化技术**，包括压缩、序列化、带宽优化

### 关键术语

| 术语 | 解释 |
|------|------|
| TCP | 传输控制协议，可靠连接 |
| UDP | 用户数据报协议，快速传输 |
| WebSocket | Web 套接字，双向通信 |
| RTT | 往返时间，网络延迟 |
| ACK | 确认包，确认数据接收 |
| NACK | 否认包，请求重传 |
| Ping/Pong | 心跳检测，测量延迟 |

---

## 🔗 延伸阅读

- **官方文档**: [Godot Networking](https://docs.godotengine.org/en/stable/tutorials/networking/index.html)
- **RFC 793**: TCP 协议规范
- **RFC 768**: UDP 协议规范
- **RFC 6455**: WebSocket 协议规范

---

## 📋 下一章预告

**第 51 篇：网络同步**

- 状态同步
- 输入同步
- 延迟补偿
- 预测和回滚

---

*写作时间：2026-03-20*  
*字数：约 14,000 字*  
*状态：✅ 完成*

---

*最后更新：2026-03-20 18:00*