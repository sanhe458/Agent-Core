import asyncio
import logging
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class WebUIServer:
    """WebUI服务器"""
    
    def __init__(self, app):
        self.app = app
        self.fastapi_app = FastAPI()
        self.config = app.get_config("webui", {})
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8000)
        self.server = None
        
        # 配置CORS
        self.fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
    
    async def start(self):
        """启动WebUI服务器"""
        logger.info(f"正在启动WebUI服务器，监听 {self.host}:{self.port}...")

        if not self.port or not isinstance(self.port, int):
            logger.error(f"端口配置无效: {self.port}")
            return

        if self.port < 1 or self.port > 65535:
            logger.error(f"端口号超出有效范围: {self.port}")
            return

        try:
            config = uvicorn.Config(
                app=self.fastapi_app,
                host=self.host,
                port=self.port,
                log_level="info"
            )

            self.server = uvicorn.Server(config)

            asyncio.create_task(self.server.serve())
            logger.info(f"WebUI服务器已启动: http://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"启动WebUI服务器失败: {e}")
    
    async def stop(self):
        """停止WebUI服务器"""
        if self.server:
            logger.info("正在停止WebUI服务器...")
            await self.server.shutdown()
    
    def _register_routes(self):
        """注册路由"""
        # 主页路由
        @self.fastapi_app.get("/")
        async def index():
            """主页"""
            html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"message": "Welcome to AI仿人类程序!"}
        
        # 静态文件路由
        static_path = os.path.join(os.path.dirname(__file__), "static")
        css_path = os.path.join(os.path.dirname(__file__), "css")
        js_path = os.path.join(os.path.dirname(__file__), "js")
        
        # 确保目录存在
        for path in [static_path, css_path, js_path]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        
        # 挂载静态文件
        static_path = os.path.join(os.path.dirname(__file__), "static")
        self.fastapi_app.mount("/static", StaticFiles(directory=static_path), name="static")
        
        # API路由
        @self.fastapi_app.get("/api/config")
        async def get_config():
            """获取配置"""
            return self.app.get_config()
        
        @self.fastapi_app.post("/api/config")
        async def update_config(config: Dict[str, Any]):
            """更新配置"""
            try:
                await self.app.config_manager.save(config)
                logger.info("配置已保存")
                return {"status": "success"}
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # 插件配置API
        @self.fastapi_app.get("/api/plugins/{plugin_name}/config")
        async def get_plugin_config(plugin_name: str):
            """获取插件配置"""
            config = self.app.plugin_manager.get_plugin_config(plugin_name)
            metadata = self.app.plugin_manager.get_plugin_config_metadata(plugin_name)
            return {"config": config, "metadata": metadata}
        
        @self.fastapi_app.post("/api/plugins/{plugin_name}/config")
        async def update_plugin_config(plugin_name: str, config: Dict[str, Any]):
            """更新插件配置"""
            try:
                success = self.app.plugin_manager.save_plugin_config(plugin_name, config)
                if success:
                    return {"status": "success"}
                else:
                    raise HTTPException(status_code=404, detail=f"插件 {plugin_name} 不存在")
            except Exception as e:
                logger.error(f"保存插件配置失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.post("/api/reload")
        async def reload_config():
            """手动触发重载"""
            self.app.config_manager.reload()
            return {"status": "success"}
        
        @self.fastapi_app.get("/api/models")
        async def get_models():
            """列出所有可用模型及其状态"""
            models = {}
            for provider_name, provider in self.app.ai_model_manager.providers.items():
                models[provider_name] = {
                    "status": "online",
                    "models": self.app.get_config(f"ai_providers.{provider_name}.models", {})
                }
            return models
        
        @self.fastapi_app.post("/api/chat")
        async def test_chat(messages: List[Dict[str, str]]):
            """模拟发送消息（测试用）"""
            try:
                if not isinstance(messages, list):
                    raise HTTPException(status_code=400, detail="消息必须是列表")
                for msg in messages:
                    if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                        raise HTTPException(status_code=400, detail="每条消息必须包含 role 和 content 字段")
                response = await self.app.ai_model_manager.chat_completion(messages, "main")
                return {"response": response}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"聊天测试失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.websocket("/ws/logs")
        async def websocket_logs(websocket: WebSocket):
            """日志流"""
            await websocket.accept()
            # 这里简化处理，实际需要实现日志实时推送
            try:
                while True:
                    await asyncio.sleep(1)
                    await websocket.send_text("日志流功能待实现")
            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                await websocket.close()
    
    async def on_config_updated(self):
        """配置更新回调"""
        # 更新配置
        self.config = self.app.get_config("webui", {})
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8000)
        logger.info("WebUI配置已更新")