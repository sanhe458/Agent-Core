import time
from typing import Dict, List, Any

class Session:
    """会话类"""
    
    def __init__(self, session_id: str, ttl: int = 3600):
        self.session_id = session_id
        self.history: List[Dict[str, str]] = []
        self.last_activity = time.time()
        self.ttl = ttl
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取历史消息"""
        return self.history
    
    def update_history(self, history: List[Dict[str, str]]):
        """更新历史消息"""
        # 限制历史消息长度
        max_history = 50  # 可配置
        if len(history) > max_history:
            self.history = history[-max_history:]
        else:
            self.history = history
        self.last_activity = time.time()
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return time.time() - self.last_activity > self.ttl

class SessionManager:
    """会话管理器"""
    
    def __init__(self, app):
        self.app = app
        self.sessions: Dict[str, Session] = {}
        self.default_ttl = 3600  # 1小时
    
    def get_session(self, session_id: str) -> Session:
        """获取会话，如果不存在则创建"""
        if session_id not in self.sessions or self.sessions[session_id].is_expired():
            self.sessions[session_id] = Session(session_id, self.default_ttl)
        return self.sessions[session_id]
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        expired_sessions = [session_id for session_id, session in self.sessions.items() if session.is_expired()]
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def get_all_sessions(self) -> Dict[str, Session]:
        """获取所有会话"""
        return dict(self.sessions)