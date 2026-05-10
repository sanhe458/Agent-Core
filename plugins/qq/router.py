import logging
from typing import Any, Callable, Dict, List, Optional
from .constants import (
    POST_TYPE_MESSAGE, POST_TYPE_NOTICE, POST_TYPE_META_EVENT,
    MESSAGE_TYPE_GROUP, MESSAGE_TYPE_PRIVATE,
    META_EVENT_TYPE_LIFETIME, META_EVENT_TYPE_HEARTBEAT
)
from .codec import MessageCodec

logger = logging.getLogger(__name__)

class NapCatEventRouter:
    def __init__(
        self,
        logger_instance: logging.Logger = None,
        gateway_name: str = "napcat",
        on_message: Callable[[Dict[str, Any]], Any] = None,
        on_connected: Callable[[], Any] = None,
        on_disconnected: Callable[[], Any] = None,
        group_list: List[int] = None,
        private_list: List[int] = None,
        ban_user_id: List[int] = None
    ):
        self._logger = logger_instance or logger
        self._gateway_name = gateway_name
        self._on_message = on_message
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._codec = MessageCodec(logger_instance)
        self._group_list = group_list or []
        self._private_list = private_list or []
        self._ban_user_id = ban_user_id or []
        self._login_info: Dict[str, Any] = {}
        self._runtime_bundle = None

    def bind_runtime(self, runtime_bundle) -> None:
        self._runtime_bundle = runtime_bundle

    def reset_caches(self) -> None:
        self._login_info.clear()

    async def handle_payload(self, payload: Dict[str, Any]) -> None:
        post_type = payload.get("post_type", "")
        if post_type == POST_TYPE_MESSAGE:
            await self._handle_message_event(payload)
        elif post_type == POST_TYPE_NOTICE:
            await self._handle_notice_event(payload)
        elif post_type == POST_TYPE_META_EVENT:
            await self._handle_meta_event(payload)
        else:
            self._logger.debug(f"Unknown post_type: {post_type}")

    async def handle_connected(self) -> None:
        self._logger.info(f"{self._gateway_name} connection established")
        if self._on_connected:
            try:
                await self._on_connected()
            except Exception as e:
                self._logger.error(f"Connected callback error: {e}")
        try:
            if self._runtime_bundle and hasattr(self._runtime_bundle, 'action_service'):
                result = await self._runtime_bundle.action_service.get_login_info()
                if result.get("success"):
                    self._login_info = result.get("result", {})
                    self._logger.info(f"Login info: {self._login_info.get('nickname', 'unknown')}")
        except Exception as e:
            self._logger.warning(f"Failed to get login info: {e}")

    async def handle_disconnected(self) -> None:
        self._logger.info(f"{self._gateway_name} connection lost")
        if self._on_disconnected:
            try:
                await self._on_disconnected()
            except Exception as e:
                self._logger.error(f"Disconnected callback error: {e}")

    async def _handle_message_event(self, payload: Dict[str, Any]) -> None:
        message_type = payload.get("message_type", "")
        sub_type = payload.get("sub_type", "")
        user_id = int(payload.get("user_id") or payload.get("sender", {}).get("user_id", 0))
        group_id = int(payload.get("group_id", 0))
        if self._should_filter_message(message_type, user_id, group_id):
            self._logger.debug(f"Message filtered: type={message_type}, user_id={user_id}, group_id={group_id}")
            return
        try:
            internal_message = self._codec.decode_message(payload)
            if self._on_message:
                await self._on_message(internal_message)
            else:
                self._logger.debug(f"Message received: {internal_message.get('content', '')[:100]}")
        except Exception as e:
            self._logger.error(f"Message handling error: {e}", exc_info=True)

    def _should_filter_message(self, message_type: str, user_id: int, group_id: int) -> bool:
        if user_id in self._ban_user_id:
            return True
        if message_type == MESSAGE_TYPE_GROUP:
            if self._group_list and group_id not in self._group_list:
                return True
        elif message_type == MESSAGE_TYPE_PRIVATE:
            if self._private_list and user_id not in self._private_list:
                return True
        return False

    async def _handle_notice_event(self, payload: Dict[str, Any]) -> None:
        notice_type = payload.get("notice_type", "")
        self._logger.debug(f"Notice event: {notice_type}")
        if notice_type == "friend_add":
            self._logger.info(f"Friend added: {payload.get('user_id')}")
        elif notice_type == "friend_recall":
            self._logger.info(f"Message recalled: {payload.get('message_id')}")
        elif notice_type == "group_increase":
            self._logger.info(f"Member joined group {payload.get('group_id')}: {payload.get('user_id')}")
        elif notice_type == "group_decrease":
            self._logger.info(f"Member left group {payload.get('group_id')}: {payload.get('user_id')}")

    async def _handle_meta_event(self, payload: Dict[str, Any]) -> None:
        meta_type = payload.get("meta_event_type", "")
        if meta_type == META_EVENT_TYPE_LIFETIME:
            self._logger.debug(f"Lifecycle event: {payload.get('sub_type')}")
        elif meta_type == META_EVENT_TYPE_HEARTBEAT:
            self._logger.debug(f"Heartbeat: interval={payload.get('interval')}ms")

    async def emit_natural_lift_notice(self) -> None:
        self._logger.info("Natural connection lift notice received")

    async def handle_heartbeat_timeout(self) -> None:
        self._logger.warning("Heartbeat timeout detected")
