"""Web前端Channel适配器"""
from typing import Dict, Any, Optional
import jwt
from loguru import logger
from .base import BaseChannel


class WebChannel(BaseChannel):
    """Web前端Channel"""
    
    def __init__(self):
        super().__init__("web")
        self.jwt_secret = "chatbi-secret-key"  # 实际应用中应从配置读取
    
    async def authenticate(self, token: str) -> Dict[str, Any]:
        """JWT Token认证"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if user_id:
                logger.info(f"Web认证成功: user_id={user_id}")
                return {"user_id": user_id, "valid": True}
            else:
                logger.warning(f"Web认证失败: 无效的token")
                return {"user_id": None, "valid": False}
        except jwt.ExpiredSignatureError:
            logger.warning("Web认证失败: Token已过期")
            return {"user_id": None, "valid": False}
        except jwt.InvalidTokenError:
            logger.warning("Web认证失败: 无效的token")
            return {"user_id": None, "valid": False}
    
    def get_user_id(self, request: Dict[str, Any]) -> str:
        """从请求中获取用户ID"""
        # 对于演示，直接返回默认用户ID
        # 实际应用中应该从JWT token或session中获取
        user_id = request.get("user_id", "web_default_user")
        logger.debug(f"获取用户ID: {user_id}")
        return user_id
    
    async def send_message(self, chat_id: str, content: str, metadata: Optional[Dict] = None):
        """发送消息（Web Channel通过WebSocket或HTTP返回）"""
        # 实际应用中应该通过WebSocket推送
        # 这里暂时只记录日志
        logger.debug(f"Web发送消息: chat_id={chat_id}, content={content[:50]}...")
