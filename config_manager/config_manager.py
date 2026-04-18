import os
import yaml
import logging
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更处理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory and event.src_path.endswith('.yaml'):
            logger.info(f"配置文件变更: {event.src_path}")
            self.config_manager.reload()

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_dir = "config"
        self.config_files = ["config.yaml", "models.yaml"]
        self.config: Dict[str, Any] = {}
        self.observer = Observer()
        self.change_handler = ConfigChangeHandler(self)
        self._watching = False
    
    async def load(self):
        """加载配置"""
        logger.info("正在加载配置...")
        
        # 加载主配置文件
        for config_file in self.config_files:
            file_path = os.path.join(self.config_dir, config_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        if config_data:
                            self._merge_config(self.config, config_data)
                    logger.info(f"成功加载配置文件: {config_file}")
                except Exception as e:
                    logger.error(f"加载配置文件 {config_file} 失败: {e}")
        
        # 加载插件配置
        plugins_dir = os.path.join(self.config_dir, "plugins")
        if os.path.exists(plugins_dir):
            for plugin_name in os.listdir(plugins_dir):
                plugin_config_file = os.path.join(plugins_dir, plugin_name, "config.yaml")
                if os.path.exists(plugin_config_file):
                    try:
                        with open(plugin_config_file, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                            if config_data:
                                self.config.setdefault("plugins", {})
                                self.config["plugins"][plugin_name] = config_data
                        logger.info(f"成功加载插件配置: {plugin_name}")
                    except Exception as e:
                        logger.error(f"加载插件配置 {plugin_name} 失败: {e}")
        
        # 确保新数据结构存在
        if 'providers' not in self.config:
            self.config['providers'] = []
        if 'models' not in self.config:
            self.config['models'] = []
        if 'router' not in self.config:
            self.config['router'] = {}
        
        # 启动文件监控
        self.start_watching()
    
    def reload(self):
        """重新加载配置"""
        logger.info("正在重新加载配置...")
        new_config = {}
        
        # 重新加载所有配置文件
        for config_file in self.config_files:
            file_path = os.path.join(self.config_dir, config_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        if config_data:
                            self._merge_config(new_config, config_data)
                except Exception as e:
                    logger.error(f"重新加载配置文件 {config_file} 失败: {e}")
        
        # 重新加载插件配置
        plugins_dir = os.path.join(self.config_dir, "plugins")
        if os.path.exists(plugins_dir):
            for plugin_name in os.listdir(plugins_dir):
                plugin_config_file = os.path.join(plugins_dir, plugin_name, "config.yaml")
                if os.path.exists(plugin_config_file):
                    try:
                        with open(plugin_config_file, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                            if config_data:
                                new_config.setdefault("plugins", {})
                                new_config["plugins"][plugin_name] = config_data
                    except Exception as e:
                        logger.error(f"重新加载插件配置 {plugin_name} 失败: {e}")
        
        # 确保新数据结构存在
        if 'providers' not in new_config:
            new_config['providers'] = []
        if 'models' not in new_config:
            new_config['models'] = []
        if 'router' not in new_config:
            new_config['router'] = {}
        
        # 替换配置
        self.config = new_config
        
        # 通知应用配置已更新
        if hasattr(self, 'app'):
            self.app.on_config_updated()
    
    def start_watching(self):
        """开始监控配置文件"""
        if self._watching:
            logger.warning("配置监控已经在运行")
            return

        try:
            if os.path.exists(self.config_dir):
                self.observer.schedule(self.change_handler, self.config_dir, recursive=True)
                self.observer.start()
                self._watching = True
                logger.info("配置文件监控已启动")
            else:
                logger.warning(f"配置目录不存在: {self.config_dir}")
        except Exception as e:
            logger.error(f"启动配置监控失败: {e}")

    def stop_watching(self):
        """停止监控配置文件"""
        if not self._watching:
            return

        try:
            self.observer.stop()
            self.observer.join(timeout=5)
            self._watching = False
            logger.info("配置文件监控已停止")
        except Exception as e:
            logger.error(f"停止配置监控失败: {e}")
    
    def get(self, key: str = None, default=None) -> Any:
        """获取配置值"""
        if key is None:
            return self.config
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]):
        """合并配置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    async def save(self, new_config: Dict[str, Any]):
        """保存配置到文件"""
        # 停止监控，避免保存时触发重载
        self.stop_watching()
        
        try:
            # 分离配置到不同文件
            core_config = {
                "core": new_config.get("core", {}),
                "webui": new_config.get("webui", {}),
                "plugins": new_config.get("plugins", {}),
                "providers": new_config.get("providers", []),
                "models": new_config.get("models", []),
                "router": new_config.get("router", {}),
                "personality": new_config.get("personality", {})
            }
            
            models_config = {
                "ai_providers": new_config.get("ai_providers", []),
                "routers": new_config.get("routers", [])
            }
            
            # 保存config.yaml
            config_yaml_path = os.path.join(self.config_dir, "config.yaml")
            with open(config_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(core_config, f, allow_unicode=True, default_flow_style=False)
            
            # 保存models.yaml
            models_yaml_path = os.path.join(self.config_dir, "models.yaml")
            with open(models_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(models_config, f, allow_unicode=True, default_flow_style=False)
            
            # 更新内存中的配置
            self.config = new_config
            logger.info("配置保存成功")
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
        finally:
            # 重新启动监控
            self.start_watching()
            # 通知应用配置已更新
            if hasattr(self, 'app'):
                self.app.on_config_updated()