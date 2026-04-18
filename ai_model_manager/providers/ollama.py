import httpx
import logging
from typing import List, Dict, Any
from ai_model_manager.provider_base import BaseProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    """Ollama提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url", "http://localhost:11434/api")
        self.client = None

    async def initialize(self):
        """初始化提供商"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=30.0
            )

    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        """聊天完成"""
        if not self.client:
            await self.initialize()

        if not messages:
            raise ValueError("消息列表不能为空")

        if not model:
            raise ValueError("模型名称不能为空")

        try:
            response = await self.client.post(
                "/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()

            if "message" not in data or "content" not in data["message"]:
                raise ValueError("API返回数据格式错误：缺少message.content字段")

            return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error("Ollama请求超时")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ollama请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama聊天完成失败: {e}")
            raise

    async def image_to_text(self, image_url: str, model: str, **kwargs) -> str:
        """图片转文字"""
        if not self.client:
            await self.initialize()

        if not image_url:
            raise ValueError("图片URL不能为空")

        if not model:
            raise ValueError("模型名称不能为空")

        try:
            messages = [
                {
                    "role": "user",
                    "content": f"What's in this image?\n![image]({image_url})"
                }
            ]
            response = await self.client.post(
                "/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()

            if "message" not in data or "content" not in data["message"]:
                raise ValueError("API返回数据格式错误：缺少message.content字段")

            return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error("Ollama请求超时")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ollama请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama图片转文字失败: {e}")
            raise

    async def stt(self, audio_url: str, model: str, **kwargs) -> str:
        """语音转文字"""
        raise NotImplementedError("STT功能需要单独实现")

    async def embed(self, text: str, model: str, **kwargs) -> List[float]:
        """文本嵌入"""
        if not self.client:
            await self.initialize()

        if not text:
            raise ValueError("文本不能为空")

        if not model:
            raise ValueError("模型名称不能为空")

        try:
            response = await self.client.post(
                "/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()

            if "embedding" not in data:
                raise ValueError("API返回数据格式错误：缺少embedding字段")

            return data["embedding"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error("Ollama请求超时")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ollama请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama文本嵌入失败: {e}")
            raise

    async def rerank(self, query: str, documents: List[str], model: str, **kwargs) -> List[Dict[str, Any]]:
        """重排序"""
        raise NotImplementedError("Rerank功能需要单独实现")