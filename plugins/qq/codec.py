import re
import logging
from typing import Any, Dict, List, Optional, Union
from .types import NapCatSegment, NapCatSegments, InternalMessage, MessageSegment
from .constants import (
    SEGMENT_TYPE_TEXT, SEGMENT_TYPE_IMAGE, SEGMENT_TYPE_AT,
    SEGMENT_TYPE_REPLY, SEGMENT_TYPE_FACE, SEGMENT_TYPE_VOICE,
    MESSAGE_TYPE_PRIVATE, MESSAGE_TYPE_GROUP
)

logger = logging.getLogger(__name__)

CQ_PATTERN = re.compile(r'\[CQ:([^,\]]+)(?:,([^\]]*))?\]')

def parse_cq_code(cq_str: str) -> Dict[str, str]:
    result = {}
    if not cq_str:
        return result
    for item in cq_str.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            result[key] = value
    return result

def decode_cq_code(text: str) -> List[Dict[str, Any]]:
    segments = []
    last_end = 0
    for match in CQ_PATTERN.finditer(text):
        if match.start() > last_end:
            content = text[last_end:match.start()]
            if content:
                segments.append({"type": SEGMENT_TYPE_TEXT, "data": {"text": content}})
        cq_type = match.group(1)
        cq_data = parse_cq_code(match.group(2) or "")
        segments.append({"type": cq_type, "data": cq_data})
        last_end = match.end()
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append({"type": SEGMENT_TYPE_TEXT, "data": {"text": remaining}})
    return segments if segments else [{"type": SEGMENT_TYPE_TEXT, "data": {"text": text}}]

def encode_cq_code(segment: Dict[str, Any]) -> str:
    seg_type = segment.get("type", "")
    seg_data = segment.get("data", {})
    if seg_type == SEGMENT_TYPE_TEXT:
        text = seg_data.get("text", "")
        return text.replace('[', '&#91;').replace(']', '&#93;').replace(',', '&#44;')
    params = ','.join(f"{k}={v}" for k, v in seg_data.items())
    return f"[CQ:{seg_type},{params}]" if params else f"[CQ:{seg_type}]"

def segments_to_string(segments: Union[List[Dict[str, Any]], str]) -> str:
    if isinstance(segments, str):
        return segments
    return ''.join(encode_cq_code(seg) for seg in segments)

class MessageCodec:
    def __init__(self, logger_instance=None):
        self.logger = logger_instance or logger

    def decode_message(self, raw_message: Dict[str, Any]) -> InternalMessage:
        message_type = raw_message.get("message_type", MESSAGE_TYPE_PRIVATE)
        sender = raw_message.get("sender", {})
        user_id = str(sender.get("user_id", ""))
        group_id = str(raw_message.get("group_id", ""))
        
        if message_type == MESSAGE_TYPE_GROUP:
            session_id = group_id
        else:
            session_id = user_id
        
        raw_msg = raw_message.get("message", "")
        if isinstance(raw_msg, str):
            segments = decode_cq_code(raw_msg)
        else:
            segments = raw_msg
        
        content_type = self._detect_content_type(segments)
        content = self._extract_text_content(segments)
        reply_to = None
        reply_msg_id = raw_message.get("reply")
        if reply_msg_id:
            reply_to = str(reply_msg_id)
        
        return {
            "platform": "qq",
            "user_id": user_id,
            "session_id": session_id,
            "content_type": content_type,
            "content": content,
            "reply_to": reply_to,
            "raw_message": {
                **raw_message,
                "segments": segments
            }
        }

    def _detect_content_type(self, segments: List[Dict[str, Any]]) -> str:
        for seg in segments:
            seg_type = seg.get("type", "")
            if seg_type in (SEGMENT_TYPE_IMAGE, SEGMENT_TYPE_VOICE):
                return seg_type
        return "text"

    def _extract_text_content(self, segments: List[Dict[str, Any]]) -> str:
        parts = []
        for seg in segments:
            seg_type = seg.get("type", "")
            seg_data = seg.get("data", {})
            if seg_type == SEGMENT_TYPE_TEXT:
                parts.append(seg_data.get("text", ""))
            elif seg_type == SEGMENT_TYPE_AT:
                at_qq = seg_data.get("qq", "")
                if at_qq == "all":
                    parts.append("@全体成员")
                else:
                    parts.append(f"@{at_qq}")
            elif seg_type == SEGMENT_TYPE_FACE:
                parts.append(f"[表情:{seg_data.get('id', '')}]")
            elif seg_type == SEGMENT_TYPE_IMAGE:
                parts.append("[图片]")
            elif seg_type == SEGMENT_TYPE_VOICE:
                parts.append("[语音]")
        return ''.join(parts).strip() or ""

    def encode_send_message(self, content: str, target: str, session_id: str = None) -> Dict[str, Any]:
        if session_id and session_id.isdigit():
            return {
                "action": "send_msg",
                "params": {
                    "message_type": MESSAGE_TYPE_GROUP,
                    "group_id": int(session_id),
                    "message": content
                }
            }
        elif target.isdigit():
            return {
                "action": "send_msg",
                "params": {
                    "message_type": MESSAGE_TYPE_PRIVATE,
                    "user_id": int(target),
                    "message": content
                }
            }
        else:
            return {
                "action": "send_msg",
                "params": {
                    "message_type": MESSAGE_TYPE_PRIVATE,
                    "user_id": int(target),
                    "message": content
                }
            }

    def build_outbound_action(self, message: Dict[str, Any], route: Dict[str, Any] = None) -> tuple[str, Dict[str, Any]]:
        content = message.get("content", "")
        target = message.get("target", "")
        message_type = message.get("message_type", "")
        group_id = message.get("group_id")
        user_id = message.get("user_id")
        if message_type == MESSAGE_TYPE_GROUP or group_id:
            return ("send_group_msg", {
                "group_id": int(group_id or target),
                "message": content,
                "auto_escape": False
            })
        elif message_type == MESSAGE_TYPE_PRIVATE or user_id:
            return ("send_private_msg", {
                "user_id": int(user_id or target),
                "message": content,
                "auto_escape": False
            })
        else:
            return ("send_private_msg", {
                "user_id": int(target),
                "message": content,
                "auto_escape": False
            })
