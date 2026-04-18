import os
import importlib
import logging
from typing import Dict, List, Any
from plugin_system.plugin_base import Plugin
from plugin_system.config_parser import ConfigParser

logger = logging.getLogger(__name__)

class PluginManager:
    """插件管理器"""
    
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugins_dir = "plugins"
        self.plugin_configs: Dict[str, ConfigParser] = {}
    
    async def load_plugins(self):
        """加载所有插件"""
        logger.info("正在加载插件...")
        
        # 扫描插件目录
        if not os.path.exists(self.plugins_dir):
            logger.warning("插件目录不存在")
            return
        
        for plugin_name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            if os.path.isdir(plugin_path) and os.path.exists(os.path.join(plugin_path, "__init__.py")):
                try:
                    # 导入插件模块
                    module_name = f"plugins.{plugin_name}"
                    module = importlib.import_module(module_name)
                    
                    # 加载插件配置
                    plugin_path = os.path.join(self.plugins_dir, plugin_name)
                    config_parser = ConfigParser(plugin_path)
                    config_parser.load()
                    self.plugin_configs[plugin_name] = config_parser
                    
                    # 查找Plugin子类
                    for name, obj in module.__dict__.items():
                        if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                            # 创建插件实例
                            plugin = obj(self.app)
                            # 加载插件配置
                            plugin.config = config_parser.get_config()
                            self.plugins[plugin_name] = plugin
                            logger.info(f"成功加载插件: {plugin_name}")
                            break
                except Exception as e:
                    logger.error(f"加载插件 {plugin_name} 失败: {e}")
    
    async def start_plugins(self):
        """启动所有插件"""
        for name, plugin in self.plugins.items():
            try:
                await plugin.start()
                logger.info(f"插件 {name} 启动成功")
            except Exception as e:
                logger.error(f"插件 {name} 启动失败: {e}")
    
    async def stop_plugins(self):
        """停止所有插件"""
        for name, plugin in self.plugins.items():
            try:
                await plugin.stop()
                logger.info(f"插件 {name} 停止成功")
            except Exception as e:
                logger.error(f"插件 {name} 停止失败: {e}")
    
    async def reload_plugins(self):
        """重新加载插件配置"""
        for name, plugin in self.plugins.items():
            try:
                plugin.on_config_reload()
                logger.info(f"插件 {name} 配置已重新加载")
            except Exception as e:
                logger.error(f"插件 {name} 配置重新加载失败: {e}")
    
    def get_plugin(self, name: str) -> Plugin:
        """获取插件"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> List[Plugin]:
        """获取所有插件"""
        return list(self.plugins.values())
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        if plugin_name in self.plugin_configs:
            return self.plugin_configs[plugin_name].get_config()
        return {}
    
    def get_plugin_config_metadata(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置元数据"""
        if plugin_name in self.plugin_configs:
            return self.plugin_configs[plugin_name].get_all_metadata()
        return {}
    
    def save_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """保存插件配置"""
        if plugin_name in self.plugin_configs:
            try:
                self.plugin_configs[plugin_name].save(config)
                # 更新插件实例的配置
                if plugin_name in self.plugins:
                    self.plugins[plugin_name].config = config
                logger.info(f"插件 {plugin_name} 配置已保存")
                return True
            except Exception as e:
                logger.error(f"保存插件 {plugin_name} 配置失败: {e}")
                return False
        return False