import logging
from typing import Any, Dict, List, Optional

from plugin_system.plugin_base import MiddlewarePlugin

logger = logging.getLogger(__name__)


class ExampleMiddlewarePlugin(MiddlewarePlugin):
    """示例中间件插件"""

    def __init__(self, app):
        super().__init__(app)
        self._priority = 50
        self._blocked_words: List[str] = []
        self._verbose_logging = False

    async def init(self, config: Dict[str, Any]):
        """初始化插件"""
        logger.info(f"中间件插件 {self.__class__.__name__} 初始化中 (优先级: {self._priority})...")

        if "general" in config:
            general_config = config["general"]

            if "priority" in general_config:
                self._priority = int(general_config["priority"])

            blocked_words_str = general_config.get("blocked_words", "")
            if blocked_words_str:
                self._blocked_words = [word.strip() for word in blocked_words_str.split(",") if word.strip()]

        if "logging" in config:
            logging_config = config["logging"]
            self._verbose_logging = logging_config.get("verbose_logging", False)

        logger.info(f"示例中间件插件已加载 {len(self._blocked_words)} 个阻塞词: {self._blocked_words}")

    def pre_process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """预处理消息，检查是否包含阻塞词"""
        if not message:
            return message

        content = message.get("content", "")
        user_id = message.get("user_id", "unknown")
        session_id = message.get("session_id", "unknown")

        if self._verbose_logging:
            logger.debug(f"[示例中间件] 预处理消息 - 用户: {user_id}, 会话: {session_id}, 内容: {content[:50]}")

        for blocked_word in self._blocked_words:
            if blocked_word.lower() in content.lower():
                logger.info(f"[示例中间件] 消息被拦截 - 用户: {user_id}, 会话: {session_id}, 包含阻塞词: {blocked_word}")
                return None

        if self._verbose_logging:
            logger.debug(f"[示例中间件] 消息通过预处理")

        return message

    def post_process(self, result: Any) -> Any:
        """后处理结果，记录处理结果日志"""
        if self._verbose_logging:
            logger.debug(f"[示例中间件] 后处理结果: {result}")

        logger.info(f"[示例中间件] 处理完成，结果类型: {type(result).__name__}")
        return result

    def on_error(self, error: Exception, message: Optional[Dict[str, Any]] = None) -> Any:
        """错误处理，记录错误日志"""
        user_id = message.get("user_id", "unknown") if message else "unknown"
        session_id = message.get("session_id", "unknown") if message else "unknown"

        logger.error(f"[示例中间件] 处理错误 - 用户: {user_id}, 会话: {session_id}, 错误: {str(error)}")
        raise error

    async def start(self):
        """启动插件"""
        logger.info(f"示例中间件插件 {self.__class__.__name__} 已启动 (优先级: {self._priority})")

    async def stop(self):
        """停止插件"""
        logger.info(f"示例中间件插件 {self.__class__.__name__} 已停止")
