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
        
        self.fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._register_routes()
    
    async def start(self):
        """启动WebUI服务器"""
        self.config = self.app.get_config("webui", {})
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8000)
        
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
    
    def _get_character_system(self):
        """获取人物系统"""
        try:
            if hasattr(self.app, 'message_pipeline'):
                return getattr(self.app.message_pipeline, 'character_system', None)
        except:
            pass
        return None
    
    def _get_character_recognition(self):
        """获取人物识别服务"""
        try:
            if hasattr(self.app, 'message_pipeline'):
                return getattr(self.app.message_pipeline, 'character_recognition', None)
        except:
            pass
        return None
    
    def _register_routes(self):
        """注册路由"""
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        @self.fastapi_app.get("/")
        async def index():
            """主页"""
            html_path = os.path.join(templates_dir, "index.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"message": "Welcome to AI仿人类程序!"}
        
        @self.fastapi_app.get("/characters.html")
        async def characters_page():
            """人物管理页面"""
            html_path = os.path.join(templates_dir, "characters.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        @self.fastapi_app.get("/config.html")
        async def config_page():
            """配置管理页面"""
            html_path = os.path.join(templates_dir, "config.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        @self.fastapi_app.get("/plugins.html")
        async def plugins_page():
            """插件管理页面"""
            html_path = os.path.join(templates_dir, "plugins.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        @self.fastapi_app.get("/models.html")
        async def models_page():
            """模型管理页面"""
            html_path = os.path.join(templates_dir, "models.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        @self.fastapi_app.get("/logs.html")
        async def logs_page():
            """日志页面"""
            html_path = os.path.join(templates_dir, "logs.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        @self.fastapi_app.get("/webui/")
        async def webui_index():
            """WebUI主页"""
            html_path = os.path.join(templates_dir, "index.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"message": "Welcome to AI仿人类程序!"}
        
        @self.fastapi_app.get("/webui/index.html")
        async def webui_index_html():
            """WebUI主页 (带html后缀)"""
            html_path = os.path.join(templates_dir, "index.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"message": "Welcome to AI仿人类程序!"}
        
        @self.fastapi_app.get("/webui/{page}")
        async def webui_page(page: str):
            """WebUI其他页面"""
            if not page.endswith('.html'):
                page = f"{page}.html"
            html_path = os.path.join(templates_dir, page)
            if os.path.exists(html_path):
                return FileResponse(html_path)
            return {"error": "Page not found"}
        
        static_path = os.path.join(os.path.dirname(__file__), "static")
        css_path = os.path.join(os.path.dirname(__file__), "css")
        js_path = os.path.join(os.path.dirname(__file__), "js")
        
        for path in [static_path, css_path, js_path]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        
        static_path = os.path.join(os.path.dirname(__file__), "static")
        self.fastapi_app.mount("/static", StaticFiles(directory=static_path), name="static")
        
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
            try:
                while True:
                    await asyncio.sleep(1)
                    await websocket.send_text("日志流功能待实现")
            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                await websocket.close()
        
        @self.fastapi_app.get("/api/characters")
        async def get_characters():
            """获取所有人物"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            characters = await char_system.get_all_characters()
            return {
                "characters": [char.to_dict() for char in characters],
                "total": len(characters)
            }
        
        @self.fastapi_app.get("/api/characters/{character_id}")
        async def get_character(character_id: str):
            """获取单个人物详情"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            character = await char_system.get_character(character_id)
            if not character:
                raise HTTPException(status_code=404, detail="人物不存在")
            
            return character.to_dict()
        
        @self.fastapi_app.post("/api/characters")
        async def create_character(data: Dict[str, Any]):
            """创建新人物"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            try:
                character = await char_system.create_character(
                    name=data.get("name", "未知人物"),
                    description=data.get("description", ""),
                    platform=data.get("platform"),
                    source=data.get("source")
                )
                return character.to_dict()
            except Exception as e:
                logger.error(f"创建人物失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.put("/api/characters/{character_id}")
        async def update_character(character_id: str, data: Dict[str, Any]):
            """更新人物信息"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            try:
                character = await char_system.update_character(character_id, data)
                if not character:
                    raise HTTPException(status_code=404, detail="人物不存在")
                return character.to_dict()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"更新人物失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.delete("/api/characters/{character_id}")
        async def delete_character(character_id: str):
            """删除人物"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            try:
                success = await char_system.delete_character(character_id)
                if not success:
                    raise HTTPException(status_code=404, detail="人物不存在")
                return {"status": "success"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"删除人物失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.post("/api/characters/merge")
        async def merge_characters(data: Dict[str, str]):
            """合并两个人物"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            
            if not source_id or not target_id:
                raise HTTPException(status_code=400, detail="缺少 source_id 或 target_id")
            
            try:
                character = await char_system.merge_characters(source_id, target_id)
                if not character:
                    raise HTTPException(status_code=404, detail="人物不存在")
                return character.to_dict()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"合并人物失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/characters/{character_id}/relationships")
        async def get_character_relationships(character_id: str):
            """获取人物关系"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            try:
                relationships = await char_system.get_character_relationships(character_id)
                return {"relationships": relationships}
            except Exception as e:
                logger.error(f"获取人物关系失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.post("/api/relationships")
        async def add_relationship(data: Dict[str, Any]):
            """添加人物关系"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            relation_type = data.get("type", "未知")
            description = data.get("description", "")
            bidirectional = data.get("bidirectional", False)
            
            if not source_id or not target_id:
                raise HTTPException(status_code=400, detail="缺少 source_id 或 target_id")
            
            try:
                success = await char_system.add_relationship(
                    source_id, target_id, relation_type, description, bidirectional
                )
                if not success:
                    raise HTTPException(status_code=400, detail="添加关系失败")
                return {"status": "success"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"添加关系失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.delete("/api/relationships")
        async def remove_relationship(data: Dict[str, str]):
            """删除人物关系"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            relation_type = data.get("type")
            
            if not source_id or not target_id:
                raise HTTPException(status_code=400, detail="缺少 source_id 或 target_id")
            
            try:
                success = await char_system.remove_relationship(source_id, target_id, relation_type)
                return {"status": "success" if success else "not_found"}
            except Exception as e:
                logger.error(f"删除关系失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/relationships/network")
        async def get_relationship_network():
            """获取关系网络"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            try:
                network = await char_system.get_relationship_network()
                return network
            except Exception as e:
                logger.error(f"获取关系网络失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/characters/search")
        async def search_characters(q: str = ""):
            """搜索人物"""
            char_system = self._get_character_system()
            if not char_system:
                raise HTTPException(status_code=503, detail="人物系统未初始化")
            
            if not q:
                return {"characters": []}
            
            try:
                results = await char_system.search_characters(q)
                return {"characters": [char.to_dict() for char in results]}
            except Exception as e:
                logger.error(f"搜索人物失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/characters/suggestions/merge")
        async def get_merge_suggestions():
            """获取合并建议"""
            char_recognition = self._get_character_recognition()
            if not char_recognition:
                raise HTTPException(status_code=503, detail="人物识别服务未初始化")
            
            try:
                suggestions = await char_recognition.suggest_merges()
                return {"suggestions": suggestions}
            except Exception as e:
                logger.error(f"获取合并建议失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/characters/{char1}/check-same/{char2}")
        async def check_same_character(char1: str, char2: str):
            """检查两个人名是否为同一人"""
            char_recognition = self._get_character_recognition()
            if not char_recognition:
                raise HTTPException(status_code=503, detail="人物识别服务未初始化")
            
            try:
                result = await char_recognition.check_character_identity(char1, char2)
                return result
            except Exception as e:
                logger.error(f"检查人物同一性失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.fastapi_app.get("/api/statistics")
        async def get_statistics():
            """获取统计信息"""
            char_system = self._get_character_system()
            if not char_system:
                return {
                    "total_characters": 0,
                    "total_relationships": 0,
                    "by_platform": {},
                    "relation_types": {},
                    "top_mentioned": []
                }
            
            try:
                stats = await char_system.get_statistics()
                return stats
            except Exception as e:
                logger.error(f"获取统计信息失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def on_config_updated(self):
        """配置更新回调"""
        self.config = self.app.get_config("webui", {})
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8000)
        logger.info("WebUI配置已更新")