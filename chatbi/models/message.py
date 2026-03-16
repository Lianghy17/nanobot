"""消息模型"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MessageCreate(BaseModel):
    """创建消息请求"""
    conversation_id: str = Field(..., description="对话ID")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    role: str = Field(..., description="角色")
    content: str = Field(..., description="内容")
    timestamp: datetime = Field(..., description="时间戳")
    tools_used: Optional[list] = None


class Message(BaseModel):
    """内部消息模型（用于Loop队列）"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    user_channel: str = Field(..., description="用户Channel")
    user_id: str = Field(..., description="用户ID")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    @property
    def scene_code(self) -> Optional[str]:
        """获取场景编码"""
        return self.metadata.get("scene_code")
