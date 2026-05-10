import asyncio
import logging
from typing import Any, Dict, Optional

from plugin_system.plugin_base import Plugin
from .transport import NapCatTransportClient, NapCatServerConfig
from .router import NapCatEventRouter
from .action_service import NapCatActionService, RuntimeBundle
from .codec import MessageCodec
from .constants import NAPCAT_GATEWAY_NAME, MESSAGE_TYPE_GROUP

logger = logging.getLogger(__name__)

class QQPlugin(Plugin):
    def __init__(self, app):
        super().__init__(app)
        self.is_running = False
        self._transport: Optional[NapCatTransportClient] = None
        self._event_router: Optional[NapCatEventRouter] = None
        self._action_service: Optional[NapCatActionService] = None
        self._runtime_bundle: Optional[RuntimeBundle] = None
        self._codec = MessageCodec(logger)
        self._server_config: Optional[NapCatServerConfig] = None

    async def init(self, config: Dict[str, Any]) -> None:
        logger.info("QQ 插件初始化")
        self._load_config(config)
        self._ensure_runtime_components()

    def _load_config(self, config: Dict[str, Any]) -> None:
        server_config = config.get("server", {})
        message_config = config.get("message", {})
        host = server_config.get("host", "localhost")
        port = server_config.get("port", 3000)
        token = server_config.get("token", "")
        reconnect_delay = server_config.get("reconnect_delay", 5.0)
        heartbeat_interval = server_config.get("heartbeat_interval", 30.0)
        action_timeout = server_config.get("action_timeout", 30.0)
        self._server_config = NapCatServerConfig(
            host=host,
            port=port,
            token=token,
            reconnect_delay=reconnect_delay,
            heartbeat_interval=heartbeat_interval,
            action_timeout=action_timeout
        )
        group_list = [int(x) for x in message_config.get("group_list", [])]
        private_list = [int(x) for x in message_config.get("private_list", [])]
        ban_user_id = [int(x) for x in message_config.get("ban_user_id", [])]
        self._event_router = NapCatEventRouter(
            logger_instance=logger,
            gateway_name=NAPCAT_GATEWAY_NAME,
            on_message=self._handle_internal_message,
            on_connected=self._on_napcat_connected,
            on_disconnected=self._on_napcat_disconnected,
            group_list=group_list,
            private_list=private_list,
            ban_user_id=ban_user_id
        )

    def _ensure_runtime_components(self) -> None:
        if self._transport is None:
            self._transport = NapCatTransportClient(
                logger_instance=logger,
                on_connection_opened=self._event_router.handle_connected,
                on_connection_closed=self._event_router.handle_disconnected,
                on_payload=self._event_router.handle_payload,
            )
        if self._action_service is None:
            self._action_service = NapCatActionService(self._transport, logger)
        if self._runtime_bundle is None:
            self._runtime_bundle = RuntimeBundle()
            self._runtime_bundle.transport = self._transport
            self._runtime_bundle.action_service = self._action_service
            self._runtime_bundle.codec = self._codec
            self._runtime_bundle.router = self._event_router
        self._event_router.bind_runtime(self._runtime_bundle)

    async def start(self) -> None:
        logger.info("QQ 插件启动")
        if not NapCatTransportClient.is_available():
            logger.error("aiohttp not available. Please install: pip install aiohttp>=3.9.0")
            return
        self._ensure_runtime_components()
        self._transport.configure(self._server_config)
        try:
            await self._transport.start()
            self.is_running = True
            logger.info(f"QQ 插件已连接 NapCat: ws://{self._server_config.host}:{self._server_config.port}")
        except Exception as e:
            logger.error(f"QQ 插件启动失败: {e}")

    async def stop(self) -> None:
        logger.info("QQ 插件停止")
        self.is_running = False
        if self._transport:
            await self._transport.stop()
        if self._event_router:
            self._event_router.reset_caches()

    async def on_message(self, message: Dict[str, Any]) -> None:
        internal_message = {
            "platform": "qq",
            "user_id": message.get("user_id", ""),
            "session_id": message.get("session_id", ""),
            "content_type": message.get("content_type", "text"),
            "content": message.get("content", ""),
            "reply_to": message.get("reply_to"),
            "raw_message": message.get("raw_message", {})
        }
        if self.app and hasattr(self.app, 'message_pipeline'):
            await self.app.message_pipeline.process_message(internal_message)
        else:
            logger.debug(f"Message received: {internal_message.get('content', '')[:100]}")

    async def send_message(self, target: str, content: str) -> Dict[str, Any]:
        logger.info(f"发送消息到 {target}: {content[:50]}...")
        if not self._action_service:
            logger.error("Action service not initialized")
            return {"success": False, "error": "Not connected"}
        try:
            if self._is_group_target(target):
                group_id = int(target)
                result = await self._action_service.send_group_msg(group_id, content)
            else:
                user_id = int(target)
                result = await self._action_service.send_private_msg(user_id, content)
            if result.success:
                logger.info(f"消息发送成功")
            else:
                logger.warning(f"消息发送失败: {result.error}")
            return result.to_dict()
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return {"success": False, "error": str(e)}

    def _is_group_target(self, target: str) -> bool:
        return target.isdigit() and self._event_router and hasattr(self._event_router, '_group_list')

    async def _handle_internal_message(self, internal_message: Dict[str, Any]) -> None:
        try:
            await self.on_message(internal_message)
        except Exception as e:
            logger.error(f"处理内部消息失败: {e}")

    async def _on_napcat_connected(self) -> None:
        logger.info("NapCat 连接已建立")
        try:
            login_result = await self._action_service.get_login_info()
            if login_result.success:
                login_data = login_result.result
                nickname = login_data.get("nickname", "Unknown")
                user_id = login_data.get("user_id", "Unknown")
                logger.info(f"登录信息: {nickname} (ID: {user_id})")
        except Exception as e:
            logger.warning(f"获取登录信息失败: {e}")

    async def _on_napcat_disconnected(self) -> None:
        logger.warning("NapCat 连接已断开")

    async def call_action(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.call_api(action, params)
        return result.to_dict()

    async def get_group_list(self) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.get_group_list()
        return result.to_dict()

    async def get_friend_list(self) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.get_friend_list()
        return result.to_dict()

    async def get_group_members(self, group_id: int) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.get_group_member_list(group_id)
        return result.to_dict()

    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.set_group_ban(group_id, user_id, duration)
        return result.to_dict()

    async def set_group_kick(self, group_id: int, user_id: int) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.set_group_kick(group_id, user_id)
        return result.to_dict()

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True) -> Dict[str, Any]:
        if not self._action_service:
            return {"success": False, "error": "Not connected"}
        result = await self._action_service.set_group_admin(group_id, user_id, enable)
        return result.to_dict()

    def on_config_reload(self) -> None:
        super().on_config_reload()
        self._load_config(self.config)
        if self.is_running:
            asyncio.create_task(self._restart_connection())

    async def _restart_connection(self) -> None:
        logger.info("正在重启 NapCat 连接...")
        if self._transport:
            await self._transport.stop()
        self._transport = None
        self._action_service = None
        self._runtime_bundle = None
        await asyncio.sleep(1)
        await self.start()
