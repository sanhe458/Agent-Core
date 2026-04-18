from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseProvider(ABC):
    """AI模型提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name")
    
    async def initialize(self):
        """初始化提供商"""
        pass
    
    async def cleanup(self):
        """清理资源"""
        pass
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        """聊天完成"""
        pass
    
    @abstractmethod
    async def image_to_text(self, image_url: str, model: str, **kwargs) -> str:
        """图片转文字"""
        pass
    
    @abstractmethod
    async def stt(self, audio_url: str, model: str, **kwargs) -> str:
        """语音转文字"""
        pass
    
    @abstractmethod
    async def embed(self, text: str, model: str, **kwargs) -> List[float]:
        """文本嵌入"""
        pass
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[str], model: str, **kwargs) -> List[Dict[str, Any]]:
        """重排序"""
        pass