import asyncio
import logging
from plugin_system.plugin_base import Plugin

logger = logging.getLogger(__name__)

class ConsolePlugin(Plugin):
    """控制台插件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.is_running = False
        self.input_task = None
    
    async def init(self, config):
        """初始化插件"""
        logger.info("控制台插件初始化")
    
    async def start(self):
        """启动插件"""
        logger.info("控制台插件启动")
        self.is_running = True
        self.input_task = asyncio.create_task(self._read_input())
    
    async def stop(self):
        """停止插件"""
        logger.info("控制台插件停止")
        self.is_running = False
        if self.input_task:
            self.input_task.cancel()
    
    async def on_message(self, message):
        """接收平台原始消息"""
        # 转换为内部消息格式
        internal_message = {
            "platform": "console",
            "user_id": message.get("user_id", "console"),
            "session_id": message.get("session_id", "console_session"),
            "content_type": message.get("content_type", "text"),
            "content": message.get("content", ""),
            "reply_to": message.get("reply_to")
        }
        
        # 发送到消息管道
        await self.app.message_pipeline.process_message(internal_message)
    
    async def send_message(self, target, content):
        """发送消息到平台"""
        logger.info(f"控制台回复: {content}")
        print(f"AI: {content}")
    
    async def _read_input(self):
        """读取用户输入"""
        while self.is_running:
            try:
                # 阻塞读取输入（Windows兼容）
                import sys
                
                # 读取输入
                content = await asyncio.to_thread(sys.stdin.readline)
                content = content.strip()
                if content:
                    # 创建消息
                    message = {
                        "user_id": "console",
                        "session_id": "console_session",
                        "content_type": "text",
                        "content": content
                    }
                    await self.on_message(message)
            except Exception as e:
                logger.error(f"读取输入失败: {e}")
                await asyncio.sleep(1)