import logging
from typing import Dict, List, Optional, Any
from ai_model_manager.provider_base import BaseProvider
from ai_model_manager.providers.openai import OpenAIProvider
from ai_model_manager.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

class AIModelManager:
    """AI模型管理器"""
    
    def __init__(self, app):
        self.app = app
        self.providers: Dict[str, BaseProvider] = {}
        self.routers: List[Dict[str, Any]] = []
    
    async def initialize(self):
        """初始化模型管理器"""
        logger.info("正在初始化AI模型管理器...")

        self.providers.clear()
        self.routers.clear()

        ai_providers = self.app.get_config("ai_providers", [])
        self.routers = self.app.get_config("routers", [])

        if not ai_providers:
            logger.warning("未配置任何AI提供商")

        for provider_config in ai_providers:
            if not isinstance(provider_config, dict):
                logger.warning(f"提供商配置格式错误: {provider_config}")
                continue

            try:
                provider_name = provider_config.get("name")
                if not provider_name:
                    logger.warning(f"提供商缺少名称: {provider_config}")
                    continue

                provider_type = provider_config.get("type", "openai")

                if provider_type == "openai":
                    provider = OpenAIProvider(provider_config)
                elif provider_type == "ollama":
                    provider = OllamaProvider(provider_config)
                else:
                    logger.warning(f"未知的提供商类型: {provider_type}")
                    continue

                await provider.initialize()
                self.providers[provider_name] = provider
                logger.info(f"成功注册提供商: {provider_name}")
            except Exception as e:
                logger.error(f"注册提供商失败: {e}", exc_info=True)
    
    async def cleanup(self):
        """清理资源"""
        for provider in self.providers.values():
            await provider.cleanup()
    
    async def chat_completion(self, messages: List[Dict[str, str]], model_role: str = "main", **kwargs) -> str:
        """聊天完成"""
        if not messages:
            logger.warning("消息列表为空")
            return "抱歉，发送的消息为空。"

        primary_routers = sorted(
            [r for r in self.routers if r.get("model_role") == model_role and not r.get("fallback", False)],
            key=lambda x: x.get("priority", 100)
        )

        fallback_routers = [r for r in self.routers if r.get("model_role") == model_role and r.get("fallback", False)]

        all_routers = primary_routers + fallback_routers

        if not all_routers:
            logger.error(f"未找到可用的 {model_role} 模型")
            return "抱歉，暂时无法提供回复。"

        for router in all_routers:
            provider_name = router.get("provider")
            if not provider_name:
                continue

            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"提供商 {provider_name} 不存在或未初始化")
                continue

            models_config = self.app.get_config(f"ai_providers.{provider_name}.models", {})
            model = models_config.get(model_role) if isinstance(models_config, dict) else None

            if not model:
                logger.warning(f"提供商 {provider_name} 中未找到模型角色 {model_role}")
                continue

            try:
                logger.info(f"尝试使用模型: {provider_name}.{model}")
                return await provider.chat_completion(messages, model, **kwargs)
            except Exception as e:
                logger.error(f"使用模型 {provider_name}.{model} 失败: {e}", exc_info=True)
                continue

        return "抱歉，所有模型都不可用，请稍后再试。"
    
    async def image_to_text(self, image_url: str, model_role: str = "image_to_text", **kwargs) -> str:
        """图片转文字"""
        provider, model = self._get_model_for_role(model_role)
        if not provider or not model:
            logger.error(f"未找到可用的 {model_role} 模型")
            return ""
        
        try:
            return await provider.image_to_text(image_url, model, **kwargs)
        except Exception as e:
            logger.error(f"图片转文字失败: {e}")
            return ""
    
    async def stt(self, audio_url: str, model_role: str = "stt", **kwargs) -> str:
        """语音转文字"""
        provider, model = self._get_model_for_role(model_role)
        if not provider or not model:
            logger.error(f"未找到可用的 {model_role} 模型")
            return ""
        
        try:
            return await provider.stt(audio_url, model, **kwargs)
        except Exception as e:
            logger.error(f"语音转文字失败: {e}")
            return ""
    
    async def embed(self, text: str, model_role: str = "embedding", **kwargs) -> List[float]:
        """文本嵌入"""
        provider, model = self._get_model_for_role(model_role)
        if not provider or not model:
            logger.error(f"未找到可用的 {model_role} 模型")
            return []
        
        try:
            return await provider.embed(text, model, **kwargs)
        except Exception as e:
            logger.error(f"文本嵌入失败: {e}")
            return []
    
    async def rerank(self, query: str, documents: List[str], model_role: str = "rerank", **kwargs) -> List[Dict[str, Any]]:
        """重排序"""
        provider, model = self._get_model_for_role(model_role)
        if not provider or not model:
            logger.error(f"未找到可用的 {model_role} 模型")
            return []
        
        try:
            return await provider.rerank(query, documents, model, **kwargs)
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return []
    
    def _get_model_for_role(self, model_role: str) -> tuple[Optional[BaseProvider], Optional[str]]:
        """根据角色获取模型"""
        # 按优先级排序路由器
        sorted_routers = sorted(self.routers, key=lambda x: x.get("priority", 100))
        
        for router in sorted_routers:
            if router.get("model_role") == model_role and not router.get("fallback", False):
                provider_name = router.get("provider")
                provider = self.providers.get(provider_name)
                if provider:
                    # 获取该提供商的对应模型
                    models_config = self.app.get_config(f"ai_providers.{provider_name}.models", {})
                    model = models_config.get(model_role) if isinstance(models_config, dict) else None
                    if model:
                        return provider, model
        
        return None, None
    
    def _get_fallback_model(self, model_role: str) -> tuple[Optional[BaseProvider], Optional[str]]:
        """获取fallback模型"""
        for router in self.routers:
            if router.get("model_role") == model_role and router.get("fallback", False):
                provider_name = router.get("provider")
                provider = self.providers.get(provider_name)
                if provider:
                    # 获取该提供商的对应模型
                    models_config = self.app.get_config(f"ai_providers.{provider_name}.models", {})
                    model = models_config.get(model_role) if isinstance(models_config, dict) else None
                    if model:
                        return provider, model
        
        return None, None