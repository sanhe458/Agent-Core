import os
import importlib
import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque

from plugin_system.plugin_base import (
    Plugin, PluginType, PlatformPlugin, ToolPlugin, 
    ActionPlugin, MiddlewarePlugin
)
from plugin_system.config_parser import ConfigParser

logger = logging.getLogger(__name__)


class CircularDependencyError(Exception):
    """循环依赖异常"""
    pass


class PluginManager:
    """插件管理器"""

    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.platform_plugins: Dict[str, PlatformPlugin] = {}
        self.tool_plugins: Dict[str, ToolPlugin] = {}
        self.action_plugins: Dict[str, ActionPlugin] = {}
        self.middleware_plugins: Dict[str, MiddlewarePlugin] = {}
        self.plugins_dir = "plugins"
        self.plugin_configs: Dict[str, ConfigParser] = {}

    async def load_plugins(self):
        """加载所有插件"""
        logger.info("=" * 50)
        logger.info("开始扫描并加载插件...")
        logger.info("=" * 50)

        if not os.path.exists(self.plugins_dir):
            logger.warning(f"插件目录不存在: {self.plugins_dir}")
            return

        discovered_plugins = {}

        for plugin_name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            init_file = os.path.join(plugin_path, "__init__.py")

            if not os.path.isdir(plugin_path) or not os.path.exists(init_file):
                continue

            try:
                module_name = f"plugins.{plugin_name}"
                module = importlib.import_module(module_name)

                config_parser = ConfigParser(plugin_path)
                config_parser.load()
                self.plugin_configs[plugin_name] = config_parser

                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        plugin_instance = obj(self.app)
                        plugin_instance.config = config_parser.get_config()
                        discovered_plugins[plugin_name] = plugin_instance
                        logger.info(f"  [发现] 插件: {plugin_name} (类型: {plugin_instance.get_type().value})")
                        break

            except Exception as e:
                logger.error(f"  [错误] 加载插件 {plugin_name} 失败: {e}")

        load_order = self._resolve_dependencies(discovered_plugins)

        logger.info("-" * 50)
        logger.info("插件加载顺序:")
        for i, plugin_name in enumerate(load_order, 1):
            logger.info(f"  {i}. {plugin_name}")
        logger.info("-" * 50)

        for plugin_name in load_order:
            plugin = discovered_plugins[plugin_name]
            try:
                plugin.on_register()
                self._register_plugin(plugin_name, plugin)
                logger.info(f"  [成功] 插件已注册: {plugin_name}")
            except Exception as e:
                logger.error(f"  [失败] 插件注册失败: {plugin_name} - {e}")

        logger.info("=" * 50)
        logger.info(f"插件加载完成: 共加载 {len(self.plugins)} 个插件")
        logger.info(f"  - 平台插件: {len(self.platform_plugins)}")
        logger.info(f"  - 工具插件: {len(self.tool_plugins)}")
        logger.info(f"  - 动作插件: {len(self.action_plugins)}")
        logger.info(f"  - 中间件插件: {len(self.middleware_plugins)}")
        logger.info("=" * 50)

    def _resolve_dependencies(self, plugins: Dict[str, Plugin]) -> List[str]:
        """解析插件依赖，按拓扑顺序返回加载顺序"""
        depends_on: Dict[str, List[str]] = {}

        for plugin_name, plugin in plugins.items():
            deps = []
            config = plugin.config if hasattr(plugin, 'config') else {}

            if 'dependencies' in config:
                deps = config['dependencies'].get('depends_on', [])
                if isinstance(deps, str):
                    deps = [d.strip() for d in deps.split(',') if d.strip()]

            if config:
                for section in config.values():
                    if isinstance(section, dict):
                        val = section.get('depends_on', '')
                        if val:
                            if isinstance(val, str):
                                deps = [d.strip() for d in val.split(',') if d.strip()]
                            elif isinstance(val, list):
                                deps = val

            depends_on[plugin_name] = [d for d in deps if d in plugins]

        for plugin_name, deps in depends_on.items():
            for dep in deps:
                if dep not in plugins:
                    logger.warning(f"插件 {plugin_name} 依赖的插件 {dep} 不存在，已忽略")
                    depends_on[plugin_name].remove(dep)

        in_degree: Dict[str, int] = {p: 0 for p in plugins}
        adj_list: Dict[str, List[str]] = defaultdict(list)

        for plugin_name, deps in depends_on.items():
            in_degree[plugin_name] = len(deps)
            for dep in deps:
                adj_list[dep].append(plugin_name)

        queue = deque([p for p, d in in_degree.items() if d == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        unresolved = [p for p in plugins if p not in result]

        if unresolved:
            circular_deps = set()
            for plugin_name in unresolved:
                visited = set()
                stack = [plugin_name]
                while stack:
                    current = stack[-1]
                    if current in visited:
                        circular_deps.add(current)
                        break
                    visited.add(current)
                    for dep in depends_on.get(current, []):
                        if dep in unresolved:
                            stack.append(dep)
                    if stack[-1] == current:
                        stack.pop()

            if circular_deps:
                logger.warning(f"检测到循环依赖，涉及插件: {circular_deps}")
                result.extend(unresolved)

        return result

    def _register_plugin(self, plugin_name: str, plugin: Plugin):
        """将插件注册到对应类型的字典中"""
        self.plugins[plugin_name] = plugin

        plugin_type = plugin.get_type()
        if plugin_type == PluginType.PLATFORM:
            self.platform_plugins[plugin_name] = plugin
        elif plugin_type == PluginType.TOOL:
            self.tool_plugins[plugin_name] = plugin
        elif plugin_type == PluginType.ACTION:
            self.action_plugins[plugin_name] = plugin
        elif plugin_type == PluginType.MIDDLEWARE:
            self.middleware_plugins[plugin_name] = plugin

    async def start_plugins(self):
        """启动所有插件"""
        logger.info("正在启动插件...")
        for name, plugin in self.plugins.items():
            try:
                await plugin.start()
                logger.info(f"  [启动成功] {name}")
            except Exception as e:
                logger.error(f"  [启动失败] {name}: {e}")

    async def stop_plugins(self):
        """停止所有插件"""
        logger.info("正在停止插件...")

        middleware_names = list(self.middleware_plugins.keys())
        for name in reversed(middleware_names):
            try:
                await self.middleware_plugins[name].stop()
                logger.info(f"  [停止] 中间件插件: {name}")
            except Exception as e:
                logger.error(f"  [停止失败] 中间件插件 {name}: {e}")

        for name, plugin in self.plugins.items():
            if name not in self.middleware_plugins:
                try:
                    await plugin.stop()
                    logger.info(f"  [停止成功] {name}")
                except Exception as e:
                    logger.error(f"  [停止失败] {name}: {e}")

    async def reload_plugins(self):
        """重新加载插件配置"""
        logger.info("正在重新加载插件配置...")
        for name, plugin in self.plugins.items():
            try:
                plugin.on_config_reload()
                logger.info(f"  [重载成功] {name}")
            except Exception as e:
                logger.error(f"  [重载失败] {name}: {e}")

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取指定名称的插件"""
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

    def save_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """保存插件配置"""
        if plugin_name in self.plugin_configs:
            try:
                self.plugin_configs[plugin_name].save(config)
                if plugin_name in self.plugins:
                    self.plugins[plugin_name].config = config
                logger.info(f"插件 {plugin_name} 配置已保存")
                return True
            except Exception as e:
                logger.error(f"保存插件 {plugin_name} 配置失败: {e}")
                return False
        return False

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """按类型获取插件"""
        type_map = {
            PluginType.PLATFORM: self.platform_plugins,
            PluginType.TOOL: self.tool_plugins,
            PluginType.ACTION: self.action_plugins,
            PluginType.MIDDLEWARE: self.middleware_plugins,
        }
        plugins_dict = type_map.get(plugin_type, {})
        return list(plugins_dict.values())

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """收集所有工具定义"""
        all_tools = []
        for plugin_name, plugin in self.tool_plugins.items():
            try:
                for tool in plugin.tools:
                    tool_copy = tool.copy()
                    tool_copy['source_plugin'] = plugin_name
                    all_tools.append(tool_copy)
                logger.debug(f"从插件 {plugin_name} 收集到 {len(plugin.tools)} 个工具")
            except Exception as e:
                logger.error(f"收集插件 {plugin_name} 工具失败: {e}")
        logger.info(f"共收集 {len(all_tools)} 个工具定义")
        return all_tools

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行指定工具"""
        for plugin_name, plugin in self.tool_plugins.items():
            if tool_name in [t.get('name') for t in plugin.tools]:
                try:
                    result = await plugin.execute_tool(tool_name, params)
                    logger.info(f"工具 {tool_name} 执行完成 (来源: {plugin_name})")
                    return result
                except Exception as e:
                    logger.error(f"执行工具 {tool_name} 失败: {e}")
                    raise

        raise ValueError(f"工具 {tool_name} 不存在")

    def get_all_actions(self) -> Dict[str, Dict[str, Any]]:
        """收集所有动作定义"""
        all_actions = {}
        for plugin_name, plugin in self.action_plugins.items():
            try:
                for action_name, action_def in plugin.actions.items():
                    full_name = f"{plugin_name}.{action_name}"
                    action_copy = action_def.copy()
                    action_copy['source_plugin'] = plugin_name
                    all_actions[full_name] = action_copy
                logger.debug(f"从插件 {plugin_name} 收集到 {len(plugin.actions)} 个动作")
            except Exception as e:
                logger.error(f"收集插件 {plugin_name} 动作失败: {e}")
        logger.info(f"共收集 {len(all_actions)} 个动作定义")
        return all_actions

    async def execute_action(self, action_name: str, params: Dict[str, Any]) -> Any:
        """执行指定动作"""
        parts = action_name.split('.', 1)
        if len(parts) == 2:
            plugin_name, local_action_name = parts
            if plugin_name in self.action_plugins:
                plugin = self.action_plugins[plugin_name]
                if local_action_name in plugin.actions:
                    result = await plugin.execute_action(local_action_name, params)
                    logger.info(f"动作 {action_name} 执行完成")
                    return result

        for plugin_name, plugin in self.action_plugins.items():
            if action_name in plugin.actions:
                result = await plugin.execute_action(action_name, params)
                logger.info(f"动作 {action_name} 执行完成 (来源: {plugin_name})")
                return result

        raise ValueError(f"动作 {action_name} 不存在")

    def get_middlewares(self) -> List[MiddlewarePlugin]:
        """获取中间件列表（按优先级排序）"""
        middlewares = list(self.middleware_plugins.values())
        middlewares.sort(key=lambda m: m.priority)
        logger.debug(f"获取到 {len(middlewares)} 个中间件，按优先级排序")
        return middlewares

    def get_platform_plugins(self) -> Dict[str, PlatformPlugin]:
        """获取所有平台插件（向后兼容）"""
        return self.platform_plugins.copy()

    def get_tool_plugins(self) -> Dict[str, ToolPlugin]:
        """获取所有工具插件（向后兼容）"""
        return self.tool_plugins.copy()

    def get_action_plugins(self) -> Dict[str, ActionPlugin]:
        """获取所有动作插件（向后兼容）"""
        return self.action_plugins.copy()

    def get_middleware_plugins(self) -> Dict[str, MiddlewarePlugin]:
        """获取所有中间件插件（向后兼容）"""
        return self.middleware_plugins.copy()
