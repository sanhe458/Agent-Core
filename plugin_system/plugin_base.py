import logging
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PluginType(Enum):
    PLATFORM = "platform"
    TOOL = "tool"
    ACTION = "action"
    MIDDLEWARE = "middleware"


class Plugin(ABC):
    """插件基类，所有插件必须实现此接口"""

    def __init__(self, app):
        self.app = app
        self.config: Dict[str, Any] = {}
        logger.info(f"插件 {self.__class__.__name__} 已创建")

    @abstractmethod
    def get_type(self) -> PluginType:
        """返回插件类型"""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """返回插件能力描述"""
        return {
            "name": self.__class__.__name__,
            "type": self.get_type().value,
        }

    def on_register(self):
        """插件注册时调用"""
        logger.info(f"插件 {self.__class__.__name__} 已注册")
        self.config = self.app.get_config(f"plugins.{self.__class__.__name__.lower()}", {})

    @abstractmethod
    async def init(self, config: Dict[str, Any]):
        """异步初始化插件"""
        pass

    @abstractmethod
    async def start(self):
        """异步启动插件"""
        pass

    @abstractmethod
    async def stop(self):
        """异步停止插件"""
        pass

    def on_config_reload(self):
        """配置重新加载时调用"""
        self.config = self.app.get_config(f"plugins.{self.__class__.__name__.lower()}", {})
        logger.info(f"插件 {self.__class__.__name__} 配置已重新加载")


class PlatformPlugin(Plugin):
    """平台适配器插件基类"""

    def get_type(self) -> PluginType:
        return PluginType.PLATFORM

    @abstractmethod
    async def on_message(self, message: Dict[str, Any]):
        """接收平台原始消息"""
        pass

    @abstractmethod
    async def send_message(self, target: str, content: str):
        """发送消息到平台"""
        pass

    async def init(self, config: Dict[str, Any]):
        """初始化平台插件"""
        logger.info(f"平台插件 {self.__class__.__name__} 初始化中...")
        self.config = config

    async def start(self):
        """启动平台插件"""
        logger.info(f"平台插件 {self.__class__.__name__} 已启动")

    async def stop(self):
        """停止平台插件"""
        logger.info(f"平台插件 {self.__class__.__name__} 已停止")


class ToolPlugin(Plugin):
    """工具插件基类"""

    def __init__(self, app):
        super().__init__(app)
        self._tools: List[Dict[str, Any]] = []
        self._tool_handlers: Dict[str, callable] = {}

    def get_type(self) -> PluginType:
        return PluginType.TOOL

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """工具定义列表"""
        return self._tools

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], handler: callable):
        """注册工具"""
        tool_def = {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
        self._tools.append(tool_def)
        self._tool_handlers[name] = handler
        logger.info(f"工具插件 {self.__class__.__name__} 注册工具: {name}")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行指定工具"""
        if tool_name not in self._tool_handlers:
            logger.warning(f"工具 {tool_name} 不存在")
            raise ValueError(f"工具 {tool_name} 不存在")

        handler = self._tool_handlers[tool_name]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            logger.info(f"工具 {tool_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """返回工具插件能力"""
        capabilities = super().get_capabilities()
        capabilities["tools"] = [t["name"] for t in self._tools]
        return capabilities

    async def init(self, config: Dict[str, Any]):
        """初始化工具插件"""
        logger.info(f"工具插件 {self.__class__.__name__} 初始化中...")
        self.config = config

    async def start(self):
        """启动工具插件"""
        logger.info(f"工具插件 {self.__class__.__name__} 已启动，共 {len(self._tools)} 个工具")

    async def stop(self):
        """停止工具插件"""
        logger.info(f"工具插件 {self.__class__.__name__} 已停止")


class ActionPlugin(Plugin):
    """动作插件基类"""

    def __init__(self, app):
        super().__init__(app)
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._action_handlers: Dict[str, callable] = {}

    def get_type(self) -> PluginType:
        return PluginType.ACTION

    @property
    def actions(self) -> Dict[str, Dict[str, Any]]:
        """动作定义字典"""
        return self._actions

    def register_action(self, name: str, description: str, parameters: Dict[str, Any], handler: callable):
        """注册动作"""
        action_def = {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
        self._actions[name] = action_def
        self._action_handlers[name] = handler
        logger.info(f"动作插件 {self.__class__.__name__} 注册动作: {name}")

    async def execute_action(self, action_name: str, params: Dict[str, Any]) -> Any:
        """执行指定动作"""
        if action_name not in self._action_handlers:
            logger.warning(f"动作 {action_name} 不存在")
            raise ValueError(f"动作 {action_name} 不存在")

        handler = self._action_handlers[action_name]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            logger.info(f"动作 {action_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"动作 {action_name} 执行失败: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """返回动作插件能力"""
        capabilities = super().get_capabilities()
        capabilities["actions"] = list(self._actions.keys())
        return capabilities

    async def init(self, config: Dict[str, Any]):
        """初始化动作插件"""
        logger.info(f"动作插件 {self.__class__.__name__} 初始化中...")
        self.config = config

    async def start(self):
        """启动动作插件"""
        logger.info(f"动作插件 {self.__class__.__name__} 已启动，共 {len(self._actions)} 个动作")

    async def stop(self):
        """停止动作插件"""
        logger.info(f"动作插件 {self.__class__.__name__} 已停止")


class MiddlewarePlugin(Plugin):
    """中间件插件基类"""

    def __init__(self, app):
        super().__init__(app)
        self._priority: int = 100

    def get_type(self) -> PluginType:
        return PluginType.MIDDLEWARE

    @property
    def priority(self) -> int:
        """优先级，数值越小优先级越高"""
        return self._priority

    @priority.setter
    def priority(self, value: int):
        self._priority = value

    def pre_process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """预处理消息，返回 None 表示不处理，返回修改后的消息继续处理"""
        return message

    def post_process(self, result: Any) -> Any:
        """后处理结果"""
        return result

    def on_error(self, error: Exception, message: Optional[Dict[str, Any]] = None) -> Any:
        """错误处理，返回处理结果或抛出异常"""
        logger.error(f"中间件 {self.__class__.__name__} 处理错误: {error}")
        raise error

    def get_capabilities(self) -> Dict[str, Any]:
        """返回中间件插件能力"""
        capabilities = super().get_capabilities()
        capabilities["priority"] = self._priority
        return capabilities

    async def init(self, config: Dict[str, Any]):
        """初始化中间件插件"""
        logger.info(f"中间件插件 {self.__class__.__name__} 初始化中 (优先级: {self._priority})...")
        self.config = config
        if "priority" in config:
            self._priority = config["priority"]

    async def start(self):
        """启动中间件插件"""
        logger.info(f"中间件插件 {self.__class__.__name__} 已启动 (优先级: {self._priority})")

    async def stop(self):
        """停止中间件插件"""
        logger.info(f"中间件插件 {self.__class__.__name__} 已停止")
