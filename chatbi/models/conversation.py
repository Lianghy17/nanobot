"""对话和消息模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ConversationStatus(str, Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Message(BaseModel):
    """消息模型"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    tools_used: Optional[List[str]] = Field(default=None, description="使用的工具列表")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具调用详情")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(BaseModel):
    """对话模型"""
    conversation_id: str = Field(..., description="对话ID")
    user_channel: str = Field(..., description="用户Channel标识")
    scene_code: str = Field(..., description="场景编码")
    scene_name: str = Field(..., description="场景名称")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="状态")
    messages: List[Message] = Field(default_factory=list, description="消息列表")
    last_consolidated: int = Field(default=0, description="已整合到memory的消息数量")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="会话元数据")
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息"""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_history(self, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取历史消息"""
        messages = self.messages[-max_messages:] if max_messages else self.messages
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
