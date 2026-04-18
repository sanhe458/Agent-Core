import asyncio
import logging
from typing import Dict, List
from plugin_system.plugin_manager import PluginManager
from config_manager.config_manager import ConfigManager
from ai_model_manager.model_manager import AIModelManager
from message_pipeline.message_pipeline import MessagePipeline
from webui.webui_server import WebUIServer

logger = logging.getLogger(__name__)

class Application:
    """核心应用类，管理整个程序的生命周期"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config_manager.app = self  # 设置app引用
        self.plugin_manager = PluginManager(self)
        self.ai_model_manager = AIModelManager(self)
        self.message_pipeline = MessagePipeline(self)
        self.webui_server = WebUIServer(self)
        self.is_running = False
    
    async def start(self):
        """启动应用"""
        logger.info("正在启动AI仿人类程序...")

        try:
            await self.config_manager.load()
            logger.info("配置加载完成")
        except Exception as e:
            logger.error(f"加载配置失败: {e}", exc_info=True)
            raise

        try:
            await self.ai_model_manager.initialize()
            logger.info("AI模型管理器初始化完成")
        except Exception as e:
            logger.error(f"初始化AI模型管理器失败: {e}", exc_info=True)
            raise

        try:
            await self.plugin_manager.load_plugins()
            logger.info("插件加载完成")
        except Exception as e:
            logger.error(f"加载插件失败: {e}", exc_info=True)

        try:
            await self.message_pipeline.start()
            logger.info("消息处理管道启动完成")
        except Exception as e:
            logger.error(f"启动消息处理管道失败: {e}", exc_info=True)
            raise

        try:
            await self.webui_server.start()
            logger.info("WebUI服务启动完成")
        except Exception as e:
            logger.error(f"启动WebUI服务失败: {e}", exc_info=True)

        try:
            await self.plugin_manager.start_plugins()
            logger.info("插件启动完成")
        except Exception as e:
            logger.error(f"启动插件失败: {e}", exc_info=True)

        self.is_running = True
        logger.info("AI仿人类程序启动完成！")
    
    async def stop(self):
        """停止应用"""
        logger.info("正在停止AI仿人类程序...")

        try:
            if hasattr(self.webui_server, 'stop'):
                await self.webui_server.stop()
                logger.info("WebUI服务已停止")
        except Exception as e:
            logger.error(f"停止WebUI服务时出错: {e}")

        try:
            if hasattr(self.plugin_manager, 'stop_plugins'):
                await self.plugin_manager.stop_plugins()
                logger.info("插件已停止")
        except Exception as e:
            logger.error(f"停止插件时出错: {e}")

        try:
            if hasattr(self.message_pipeline, 'stop'):
                await self.message_pipeline.stop()
                logger.info("消息处理管道已停止")
        except Exception as e:
            logger.error(f"停止消息处理管道时出错: {e}")

        try:
            if hasattr(self.ai_model_manager, 'cleanup'):
                await self.ai_model_manager.cleanup()
                logger.info("AI模型管理器已清理")
        except Exception as e:
            logger.error(f"清理AI模型管理器时出错: {e}")

        try:
            if hasattr(self.config_manager, 'stop_watching'):
                self.config_manager.stop_watching()
                logger.info("配置监控已停止")
        except Exception as e:
            logger.error(f"停止配置监控时出错: {e}")

        self.is_running = False
        logger.info("AI仿人类程序已停止")
    
    def get_config(self, key: str = None, default=None):
        """获取配置"""
        return self.config_manager.get(key, default)
    
    def on_config_updated(self):
        """配置更新回调"""
        logger.info("配置已更新，正在重新加载...")
        asyncio.create_task(self._reload_components())
    
    async def _reload_components(self):
        """重新加载组件"""
        # 重新初始化AI模型管理器
        await self.ai_model_manager.initialize()
        # 重新加载插件配置
        await self.plugin_manager.reload_plugins()
        # 通知WebUI
        await self.webui_server.on_config_updated()