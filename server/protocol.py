"""
WebSocket 通信协议。
一条 WebSocket 连接通过 channel_id 多路复用，承载 control / http / tcp / udp 四类消息。
"""
import json
import base64
import uuid
from enum import Enum


class MsgType(str, Enum):
    REGISTER      = "register"
    RULES_PUSH    = "rules_push"
    HEARTBEAT     = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    HTTP_REQUEST  = "http_request"
    HTTP_RESPONSE = "http_response"
    TCP_OPEN      = "tcp_open"
    TCP_OPENED    = "tcp_opened"
    TCP_DATA      = "tcp_data"
    TCP_CLOSE     = "tcp_close"
    UDP_OPEN      = "udp_open"
    UDP_DATA      = "udp_data"
    UDP_CLOSE     = "udp_close"


def encode(msg_type: str, channel_id: str = None,
           data: bytes = None, payload: dict = None) -> str:
    msg = {"type": msg_type}
    if channel_id:
        msg["channel_id"] = channel_id
    if data is not None:
        msg["data"] = base64.b64encode(data).decode()
    if payload is not None:
        msg["payload"] = payload
    return json.dumps(msg, ensure_ascii=False)


def decode(raw: str) -> dict:
    return json.loads(raw)


def decode_data(s: str) -> bytes:
    return base64.b64decode(s)


def new_channel_id() -> str:
    return str(uuid.uuid4())
