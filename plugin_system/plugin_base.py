from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

class Plugin(ABC):
    """插件基类，所有插件必须实现此接口"""

    def __init__(self, app):
        self.app = app
        self.config = self.app.get_config(f"plugins.{self.__class__.__name__.lower()}", {})
        asyncio.create_task(self._async_init())

    async def _async_init(self):
        """异步初始化"""
        try:
            await self.init(self.config)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"插件 {self.__class__.__name__} 初始化失败: {e}", exc_info=True)

    @abstractmethod
    async def init(self, config: Dict[str, Any]):
        """初始化插件"""
        pass
    
    @abstractmethod
    async def start(self):
        """启动插件"""
        pass
    
    @abstractmethod
    async def stop(self):
        """停止插件"""
        pass
    
    @abstractmethod
    async def on_message(self, message: Dict[str, Any]):
        """接收平台原始消息"""
        pass
    
    @abstractmethod
    async def send_message(self, target: str, content: str):
        """发送消息到平台"""
        pass
    
    def on_config_reload(self):
        """配置重新加载时调用"""
        self.config = self.app.get_config(f"plugins.{self.__class__.__name__.lower()}", {})