from typing import Any, Dict, List, Mapping, Optional, TypedDict
from typing_extensions import NotRequired

class NapCatIncomingSegment(TypedDict):
    type: str
    data: Mapping[str, Any]

class NapCatHostMessageSegment(TypedDict):
    type: str
    data: Any
    hash: NotRequired[str]
    binary_data_base64: NotRequired[str]

NapCatActionParams = Mapping[str, Any]
NapCatActionParamsInput = Optional[Mapping[str, Any]]
NapCatActionResponse = Dict[str, Any]
NapCatIdInput = int | str
NapCatMutablePayload = Dict[str, Any]
NapCatOptionalIdInput = int | str | None
NapCatPayload = Mapping[str, Any]
NapCatPayloadDict = Dict[str, Any]
NapCatPayloadList = List[Dict[str, Any]]
NapCatIncomingSegments = List[NapCatIncomingSegment]
NapCatSegment = NapCatHostMessageSegment
NapCatSegments = List[NapCatHostMessageSegment]

class InternalMessage(TypedDict):
    platform: str
    user_id: str
    session_id: str
    content_type: str
    content: str
    reply_to: Optional[str]
    raw_message: Optional[Dict[str, Any]]

class SendMessageParams(TypedDict):
    message_type: str
    user_id: Optional[int]
    group_id: Optional[int]
    message: str | List[NapCatSegment]
    auto_escape: Optional[bool]

class MessageSegment(TypedDict):
    type: str
    data: Dict[str, Any]
