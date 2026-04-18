import asyncio
import logging
from typing import Dict, Any, List
from message_pipeline.session_manager import SessionManager
from message_pipeline.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class MessagePipeline:
    """消息处理管道"""
    
    def __init__(self, app):
        self.app = app
        self.session_manager = SessionManager(app)
        self.message_processor = MessageProcessor(app)
        self.message_queue = asyncio.Queue()
        self.is_running = False
        self.worker_task = None
    
    async def start(self):
        """启动消息处理管道"""
        logger.info("正在启动消息处理管道...")
        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_messages())
    
    async def stop(self):
        """停止消息处理管道"""
        logger.info("正在停止消息处理管道...")
        self.is_running = False
        if self.worker_task:
            await self.worker_task
    
    async def process_message(self, message: Dict[str, Any]):
        """处理消息"""
        await self.message_queue.put(message)
    
    async def _process_messages(self):
        """处理消息队列"""
        while self.is_running:
            try:
                # 使用超时，以便在is_running为False时能够退出
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    await self._process_single_message(message)
                    self.message_queue.task_done()
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                logger.error(f"处理消息失败: {e}")
    
    async def _process_single_message(self, message: Dict[str, Any]):
        """处理单条消息"""
        try:
            session_id = message.get("session_id")
            if not session_id:
                platform = message.get("platform")
                user_id = message.get("user_id")
                if not platform or not user_id:
                    logger.warning(f"消息缺少必要的 platform 或 user_id 字段: {message}")
                    return
                session_id = f"{platform}_{user_id}"

            session = self.session_manager.get_session(session_id)

            processed_message = await self.message_processor.preprocess(message)

            content_type = processed_message.get("content_type", "text")
            content = processed_message.get("content", "")

            if not content and content_type != "image" and content_type != "voice":
                logger.warning(f"消息内容为空: {message}")
                return

            messages = session.get_history()
            messages.append({"role": "user", "content": content})

            if content_type == "text":
                response = await self.app.ai_model_manager.chat_completion(messages, "main")
            elif content_type == "image":
                image_description = await self.app.ai_model_manager.image_to_text(content, "image_to_text")
                if image_description:
                    messages[-1]["content"] = f"图片内容: {image_description}"
                    response = await self.app.ai_model_manager.chat_completion(messages, "main")
                else:
                    response = "抱歉，无法理解图片内容。"
            elif content_type == "voice":
                text = await self.app.ai_model_manager.stt(content, "stt")
                if text:
                    messages[-1]["content"] = text
                    response = await self.app.ai_model_manager.chat_completion(messages, "main")
                else:
                    response = "抱歉，无法理解语音内容。"
            else:
                response = await self.app.ai_model_manager.chat_completion(messages, "main")

            processed_response = await self.message_processor.postprocess(response)

            messages.append({"role": "assistant", "content": processed_response})
            session.update_history(messages)

            platform = message.get("platform")
            target = message.get("user_id")

            if platform and target:
                plugin = self.app.plugin_manager.get_plugin(platform)
                if plugin:
                    try:
                        await plugin.send_message(target, processed_response)
                        logger.info(f"回复已发送到 {platform}: {target}")
                    except Exception as e:
                        logger.error(f"发送回复失败: {e}")

            self.session_manager.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"处理消息时发生异常: {e}", exc_info=True)