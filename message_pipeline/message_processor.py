import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, app):
        self.app = app
        self.character_system = None
        self.character_recognition = None
    
    def set_character_system(self, character_system, character_recognition):
        """设置人物系统"""
        self.character_system = character_system
        self.character_recognition = character_recognition
    
    async def preprocess(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """预处理消息"""
        content = message.get("content", "")
        content = self._filter_sensitive_words(content)
        
        command = self._parse_command(content)
        if command:
            message["command"] = command
        
        content = self._replace_variables(content, message)
        
        message["content"] = content
        return message
    
    async def postprocess(self, response: str) -> str:
        """后处理回复"""
        response = self._format_response(response)
        return response
    
    async def process_characters(self, content: str, platform: str = None, source: str = None) -> Optional[str]:
        """处理消息中的人物识别和上下文生成"""
        if not self.character_recognition or not content:
            return None
        
        try:
            registered_chars = await self.character_recognition.process_and_register_characters(
                text=content,
                platform=platform,
                source=source
            )
            
            if registered_chars and self.character_system:
                character_ids = [c.id for c in registered_chars]
                
                await self.character_recognition.analyze_conversation_context(
                    messages=[{"content": content}],
                    platform=platform
                )
                
                return self.character_system.generate_context_for_characters(character_ids)
        
        except Exception as e:
            logger.error(f"处理人物识别时出错: {e}")
        
        return None
    
    def enhance_context_with_characters(self, messages: list, platform: str = None) -> tuple[list, str]:
        """增强消息上下文中的角色信息"""
        if not self.character_recognition or not messages:
            return messages, ""
        
        try:
            result = self.character_recognition.analyze_conversation_context(
                messages=messages,
                platform=platform
            )
            
            character_context = result.get("context", "")
            relationships = result.get("relationships", [])
            
            if relationships and self.character_system:
                for rel in relationships:
                    asyncio_run = self._get_asyncio_run()
                    if asyncio_run:
                        asyncio_run(self.character_system.add_relationship(
                            source_id=rel["source_id"],
                            target_id=rel["target_id"],
                            relation_type=rel["type"],
                            bidirectional=False
                        ))
            
            return messages, character_context
        
        except Exception as e:
            logger.error(f"增强上下文时出错: {e}")
        
        return messages, ""
    
    def _get_asyncio_run(self):
        """获取asyncio.run方法"""
        import asyncio
        try:
            return asyncio.get_event_loop().run_until_complete
        except:
            return None
    
    def _filter_sensitive_words(self, content: str) -> str:
        """过滤敏感词"""
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