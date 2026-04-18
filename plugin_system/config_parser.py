import os
import configparser
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class ConfigParser:
    """配置文件解析器"""
    
    def __init__(self, plugin_path: str):
        self.plugin_path = plugin_path
        self.config_file = os.path.join(plugin_path, "config.ini")
        self.config = configparser.ConfigParser()
        self.config_metadata = {}
    
    def load(self) -> bool:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            return False
        
        # 读取配置文件
        self.config.read(self.config_file, encoding='utf-8')
        
        # 解析元数据
        self._parse_metadata()
        return True
    
    def _parse_metadata(self):
        """解析配置文件中的元数据"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(self.config_file, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except Exception:
                logger.warning(f"无法读取配置文件编码: {self.config_file}")
                return

        current_section = None
        current_metadata = {}

        for line in lines:
            line = line.strip()

            if line.startswith('[') and line.endswith(']'):
                if current_section and current_metadata:
                    self.config_metadata[current_section] = current_metadata

                current_section = line[1:-1]
                current_metadata = {
                    'title': current_section,
                    'desc': '',
                    'items': {}
                }

            elif line.startswith('#'):
                comment = line[1:].strip()
                if ':' in comment:
                    parts = comment.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip()
                        value = value.strip()

                        if current_section:
                            if key in ['title', 'desc']:
                                current_metadata[key] = value

                        elif current_metadata and 'items' in current_metadata:
                            if 'current_item' in current_metadata:
                                item_name = current_metadata['current_item']
                                if item_name not in current_metadata['items']:
                                    current_metadata['items'][item_name] = {}
                                current_metadata['items'][item_name][key] = value

            elif '=' in line and current_section:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    key = key.strip()
                    value = value.strip()

                    current_metadata['current_item'] = key

                    if key not in current_metadata['items']:
                        current_metadata['items'][key] = {
                            'title': key,
                            'desc': '',
                            'type': 'string',
                            'default': value
                        }
                    else:
                        current_metadata['items'][key]['default'] = value

        if current_section and current_metadata:
            self.config_metadata[current_section] = current_metadata
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置数据"""
        config = {}
        for section in self.config.sections():
            config[section] = {}
            for key, value in self.config[section].items():
                # 根据类型转换值
                metadata = self.get_metadata(section, key)
                if metadata and 'type' in metadata:
                    value = self._convert_value(value, metadata['type'])
                config[section][key] = value
        return config
    
    def get_metadata(self, section: str, key: str = None) -> Dict[str, Any]:
        """获取配置元数据"""
        if section not in self.config_metadata:
            return {}
        
        if key:
            section_metadata = self.config_metadata[section]
            return section_metadata.get('items', {}).get(key, {})
        else:
            return self.config_metadata[section]
    
    def get_all_metadata(self) -> Dict[str, Any]:
        """获取所有元数据"""
        return self.config_metadata
    
    def _convert_value(self, value: str, type_name: str) -> Any:
        """根据类型转换值"""
        if type_name == 'bool':
            return value.lower() in ['true', 'yes', '1', 'y']
        elif type_name == 'number':
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
        elif type_name == 'select' or type_name == 'multiselect':
            return value
        else:
            return value
    
    def save(self, config: Dict[str, Any]):
        """保存配置到文件"""
        # 更新配置
        for section, items in config.items():
            if section not in self.config:
                self.config[section] = {}
            for key, value in items.items():
                self.config[section][key] = str(value)
        
        # 保存到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            # 先写入元数据
            for section, metadata in self.config_metadata.items():
                # 写入section注释
                if 'title' in metadata or 'desc' in metadata:
                    if 'title' in metadata:
                        f.write(f"# title: {metadata['title']}\n")
                    if 'desc' in metadata:
                        f.write(f"# desc: {metadata['desc']}\n")
                    f.write('\n')
                
                # 写入section
                f.write(f"[{section}]\n")
                
                # 写入配置项
                if 'items' in metadata:
                    for key, item_metadata in metadata['items'].items():
                        # 写入配置项注释
                        for meta_key, meta_value in item_metadata.items():
                            if meta_key != 'default':
                                f.write(f"# {meta_key}: {meta_value}\n")
                        
                        # 写入配置项值
                        if section in config and key in config[section]:
                            value = config[section][key]
                        else:
                            value = item_metadata.get('default', '')
                        f.write(f"{key} = {value}\n\n")
                
                f.write('\n')