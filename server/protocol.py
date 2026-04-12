"""
WebSocket 通信协议定义。

所有 Client ↔ Server 消息都通过此协议序列化/反序列化。
一条 WebSocket 连接通过 channel_id 承载多路并发流量。

消息类型（type 字段）：

  控制类：
    register      Client → Server  注册，携带 client_id 和 token
    rules_push    Server → Client  下发/更新隧道规则
    heartbeat     双向             保活
    heartbeat_ack 双向             保活响应

  HTTP 隧道类：
    http_request  Server → Client  转发 HTTP 请求
    http_response Client → Server  回传 HTTP 响应

  TCP 隧道类：
    tcp_open      Server → Client  通知 Client 建立本地 TCP 连接
    tcp_data      双向             传输 TCP 数据（base64 编码）
    tcp_close     双向             关闭 TCP 连接

消息结构：
{
    "type":       str,           # 消息类型，见上
    "channel_id": str | None,    # HTTP/TCP 消息必填，control 消息可为 None
    "data":       str | None,    # base64 编码的原始字节（HTTP/TCP数据）
    "payload":    dict | None    # 结构化数据（register、rules_push 等控制消息）
}
"""
import json
import base64
from enum import Enum


class MsgType(str, Enum):
    # 控制类
    REGISTER       = "register"
    RULES_PUSH     = "rules_push"
    HEARTBEAT      = "heartbeat"
    HEARTBEAT_ACK  = "heartbeat_ack"

    # HTTP 隧道类
    HTTP_REQUEST   = "http_request"
    HTTP_RESPONSE  = "http_response"

    # TCP 隧道类
    TCP_OPEN       = "tcp_open"
    TCP_DATA       = "tcp_data"
    TCP_CLOSE      = "tcp_close"


def encode(msg_type: MsgType, channel_id: str = None,
           data: bytes = None, payload: dict = None) -> str:
    """构造 WebSocket 文本帧"""
    pass


def decode(raw: str) -> dict:
    """解析 WebSocket 文本帧，返回 dict"""
    pass


def encode_data(b: bytes) -> str:
    """bytes → base64 字符串"""
    return base64.b64encode(b).decode()


def decode_data(s: str) -> bytes:
    """base64 字符串 → bytes"""
    return base64.b64decode(s)
