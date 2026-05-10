import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from plugin_system.plugin_base import ToolPlugin

logger = logging.getLogger(__name__)


class ExampleToolPlugin(ToolPlugin):
    """示例工具插件"""

    def __init__(self, app):
        super().__init__(app)
        self.is_enabled = True

    def get_capabilities(self) -> Dict[str, Any]:
        """返回插件能力"""
        capabilities = super().get_capabilities()
        capabilities.update({
            "title": "示例工具插件",
            "desc": "提供天气查询和当前时间获取的示例工具",
        })
        return capabilities

    async def init(self, config: Dict[str, Any]):
        """初始化插件并注册工具"""
        logger.info("示例工具插件初始化中...")
        await super().init(config)

        self.is_enabled = config.get("enabled", True)

        if self.is_enabled:
            self._register_tools()
        else:
            logger.info("示例工具插件已禁用")

    def _register_tools(self):
        """注册所有工具"""
        logger.info("开始注册工具...")

        self.register_tool(
            name="get_weather",
            description="获取指定城市的当前天气信息",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                    }
                },
                "required": ["city"]
            },
            handler=self.get_weather
        )
        logger.info("工具 get_weather 已注册")

        self.register_tool(
            name="get_time",
            description="获取当前的日期和时间",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.get_time
        )
        logger.info("工具 get_time 已注册")

        logger.info(f"共注册了 {len(self._tools)} 个工具")

    async def get_weather(self, city: str) -> Dict[str, Any]:
        """获取城市天气（示例实现）"""
        logger.info(f"正在获取 {city} 的天气信息...")

        await asyncio.sleep(0.1)

        weather_data = {
            "city": city,
            "temperature": 22,
            "condition": "晴",
            "humidity": 65,
            "wind_speed": "3级",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"{city} 天气查询完成: {weather_data['condition']}, {weather_data['temperature']}°C")
        return weather_data

    async def get_time(self) -> Dict[str, Any]:
        """获取当前时间"""
        logger.info("正在获取当前时间...")

        now = datetime.now()

        time_data = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": now.timestamp(),
            "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
            "timezone": "Asia/Shanghai"
        }

        logger.info(f"当前时间: {time_data['date']} {time_data['time']}")
        return time_data

    async def start(self):
        """启动插件"""
        await super().start()
        logger.info("示例工具插件已成功启动")

    async def stop(self):
        """停止插件"""
        logger.info("示例工具插件正在停止...")
        await super().stop()
        logger.info("示例工具插件已停止")
