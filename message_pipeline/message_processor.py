import re
from typing import Dict, Any

class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, app):
        self.app = app
    
    async def preprocess(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """预处理消息"""
        # 1. 敏感词过滤
        content = message.get("content", "")
        content = self._filter_sensitive_words(content)
        
        # 2. 指令解析
        command = self._parse_command(content)
        if command:
            message["command"] = command
        
        # 3. 变量替换
        content = self._replace_variables(content, message)
        
        message["content"] = content
        return message
    
    async def postprocess(self, response: str) -> str:
        """后处理回复"""
        # 1. 格式化输出
        response = self._format_response(response)
        
        # 2. 命令插件处理
        # 这里可以添加命令插件的处理逻辑
        
        return response
    
    def _filter_sensitive_words(self, content: str) -> str:
        """过滤敏感词"""
        # 简单的敏感词过滤，实际应用中可能需要更复杂的实现
        sensitive_words = ["敏感词1", "敏感词2"]
        for word in sensitive_words:
            content = content.replace(word, "***")
        return content
    
    def _parse_command(self, content: str) -> str:
        """解析命令"""
        # 解析以/开头的命令
        match = re.match(r"^/(\w+)", content)
        if match:
            return match.group(1)
        return None
    
    def _replace_variables(self, content: str, message: Dict[str, Any]) -> str:
        """替换变量"""
        # 替换变量，如 {user_id}, {platform} 等
        variables = {
            "user_id": message.get("user_id", ""),
            "platform": message.get("platform", ""),
            "session_id": message.get("session_id", "")
        }
        
        for var, value in variables.items():
            content = content.replace(f"{{{var}}}", value)
        
        return content
    
    def _format_response(self, response: str) -> str:
        """格式化回复"""
        # 简单的格式化，实际应用中可能需要更复杂的实现
        # 例如，处理Markdown格式，添加表情等
        return response