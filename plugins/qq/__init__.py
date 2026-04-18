import asyncio
import logging
import json
import websockets as Server
import http
from plugin_system.plugin_base import Plugin

logger = logging.getLogger(__name__)

class QQPlugin(Plugin):
    """QQ插件适配器"""

    def __init__(self, app):
        super().__init__(app)
        self.is_running = False
        self.worker_task = None
        self.message_process_task = None
        self.server_connection = None
        self.websocket_server = None
        self.message_queue = asyncio.Queue()
        # 初始化默认配置
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8080)
        self.token = self.config.get("token", "")
        
    async def init(self, config):
        """初始化插件

        Args:
            config: 插件配置，来源于 config.yaml
        """
        logger.info("QQ插件初始化")
        # 加载配置
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8080)
        self.token = self.config.get("token", "")

    async def start(self):
        """启动插件

        启动异步任务来监听和处理消息
        """
        logger.info("QQ插件启动")
        self.is_running = True
        # 启动WebSocket服务器
        self.worker_task = asyncio.create_task(self._start_websocket_server())
        # 启动消息处理任务
        self.message_process_task = asyncio.create_task(self._message_process())

    async def stop(self):
        """停止插件

        清理资源，取消异步任务
        """
        logger.info("QQ插件停止")
        self.is_running = False
        
        # 关闭WebSocket服务器
        if self.websocket_server:
            try:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
            except Exception as e:
                logger.error(f"关闭WebSocket服务器失败: {e}")
        
        # 取消任务
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        if self.message_process_task:
            self.message_process_task.cancel()
            try:
                await self.message_process_task
            except asyncio.CancelledError:
                pass

    async def on_message(self, message: dict):
        """接收平台原始消息并转发到消息管道

        Args:
            message: 平台原始消息，格式为：
                {
                    "platform": str,      # 平台名称，如 "telegram"
                    "user_id": str,       # 用户ID
                    "session_id": str,    # 会话ID
                    "content_type": str,  # 内容类型: "text", "image", "voice"
                    "content": str,       # 消息内容
                    "reply_to": str       # 可选，回复目标
                }
        """
        internal_message = {
            "platform": "qq",
            "user_id": message.get("user_id", ""),
            "session_id": message.get("session_id", ""),
            "content_type": message.get("content_type", "text"),
            "content": message.get("content", ""),
            "reply_to": message.get("reply_to")
        }
        await self.app.message_pipeline.process_message(internal_message)

    async def send_message(self, target: str, content: str):
        """发送消息到平台

        Args:
            target: 目标用户/会话ID
            content: 消息内容
        """
        logger.info(f"发送消息到 {target}: {content}")
        # 实现具体的发送逻辑
        if self.server_connection:
            try:
                # 构建消息发送请求
                payload = json.dumps({
                    "action": "send_msg",
                    "params": {
                        "message_type": "private",
                        "user_id": int(target),
                        "message": content
                    },
                    "echo": str(asyncio.get_event_loop().time())
                })
                await self.server_connection.send(payload)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")

    async def _start_websocket_server(self):
        """启动WebSocket服务器"""
        async def message_recv(server_connection: Server.ServerConnection):
            self.server_connection = server_connection
            try:
                async for raw_message in server_connection:
                    logger.debug(f"收到消息: {raw_message[:500]}..." if len(raw_message) > 500 else raw_message)
                    try:
                        decoded_message = json.loads(raw_message)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}, 原始消息: {raw_message[:200]}")
                        continue

                    if not isinstance(decoded_message, dict):
                        logger.warning(f"消息格式错误，期望字典类型: {type(decoded_message)}")
                        continue

                    post_type = decoded_message.get("post_type")
                    if post_type in ["message", "notice", "meta_event"]:
                        await self.message_queue.put(decoded_message)
            except asyncio.CancelledError:
                logger.debug("WebSocket连接被取消")
                raise
            except Exception as e:
                logger.error(f"WebSocket处理错误: {e}")

        def check_token(conn, request):
            if not self.token or self.token.strip() == "":
                return None
            auth_header = request.headers.get("Authorization")
            if auth_header != f"Bearer {self.token}":
                return Server.Response(
                    status=http.HTTPStatus.UNAUTHORIZED,
                    headers=Server.Headers([("Content-Type", "text/plain")]),
                    body=b"Unauthorized\n"
                )
            return None

        try:
            async with Server.serve(
                message_recv,
                self.host,
                self.port,
                max_size=2**26,
                process_request=check_token
            ) as server:
                self.websocket_server = server
                logger.info(f"QQ插件WebSocket服务器启动成功! 监听: ws://{self.host}:{self.port}")
                await server.serve_forever()
        except OSError as e:
            if e.errno == 10048 or "address already in use" in str(e).lower():
                logger.error(f"端口 {self.port} 已被占用")
            else:
                logger.error(f"WebSocket服务器启动失败: {e}")
        except Exception as e:
            logger.error(f"WebSocket服务器异常: {e}")

    async def _message_process(self):
        """处理消息队列中的消息"""
        while self.is_running:
            try:
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                post_type = message.get("post_type")
                if post_type == "message":
                    await self._handle_message(message)
                elif post_type == "notice":
                    await self._handle_notice(message)
                elif post_type == "meta_event":
                    await self._handle_meta_event(message)

                self.message_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"消息处理错误: {e}", exc_info=True)
                try:
                    self.message_queue.task_done()
                except Exception:
                    pass

    async def _handle_message(self, message):
        """处理消息事件"""
        message_type = message.get("message_type")
        if message_type == "private":
            # 私聊消息
            user_id = message.get("sender", {}).get("user_id")
            content = message.get("raw_message", "")
            await self.on_message({
                "user_id": str(user_id),
                "session_id": str(user_id),
                "content_type": "text",
                "content": content
            })
        elif message_type == "group":
            # 群聊消息
            group_id = message.get("group_id")
            user_id = message.get("sender", {}).get("user_id")
            content = message.get("raw_message", "")
            await self.on_message({
                "user_id": str(user_id),
                "session_id": str(group_id),
                "content_type": "text",
                "content": content
            })

    async def _handle_notice(self, message):
        """处理通知事件"""
        notice_type = message.get("notice_type")
        logger.debug(f"收到通知事件: {notice_type}")

    async def _handle_meta_event(self, message):
        """处理元事件"""
        meta_event_type = message.get("meta_event_type")
        logger.debug(f"收到元事件: {meta_event_type}")