"""Channel基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseChannel(ABC):
    """Channel基类"""
    
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
    
    @abstractmethod
    async def authenticate(self, token: str) -> Dict[str, Any]:
        """认证"""
        pass
    
    @abstractmethod
    def get_user_id(self, request: Dict[str, Any]) -> str:
        """从请求中获取用户ID"""
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, content: str, metadata: Optional[Dict] = None):
        """发送消息"""
        pass
