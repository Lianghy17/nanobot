"""消息API"""
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from ..models.message import MessageCreate
from ..core.conversation_manager import ConversationManager
from ..core.loop_queue import LoopQueue

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageResponse(BaseModel):
    """消息响应"""
    message_id: str
    conversation_id: str
    status: str
    message: Optional[str] = None


# 依赖注入
def get_conversation_manager():
    return ConversationManager()


def get_loop_queue():
    return LoopQueue.get_instance()


@router.post("/", response_model=MessageResponse)
async def send_message(
    request: MessageCreate,
    background_tasks: BackgroundTasks,
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager),
    loop_queue: LoopQueue = Depends(get_loop_queue)
):
    """发送消息"""
    try:
        user_channel = f"web_{user_id}"
        
        # 验证对话是否存在
        conversation = conv_manager.get(request.conversation_id, user_channel)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 生成消息ID
        message_id = f"msg_{uuid.uuid4().hex}"
        
        # 创建消息对象
        from ..models.message import Message
        message = Message(
            id=message_id,
            conversation_id=request.conversation_id,
            user_channel=user_channel,
            user_id=user_id,
            content=request.content,
            metadata=request.metadata or {}
        )
        
        # 入队处理
        await loop_queue.enqueue(message)
        
        logger.info(f"消息已入队: {message_id}, conv_id={request.conversation_id}")
        
        return MessageResponse(
            message_id=message_id,
            conversation_id=request.conversation_id,
            status="queued",
            message="消息已发送，正在处理中..."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """获取对话的消息历史"""
    try:
        user_channel = f"web_{user_id}"
        conversation = conv_manager.get(conversation_id, user_channel)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tools_used": msg.tools_used,
                    "metadata": msg.metadata
                }
                for msg in conversation.messages
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取消息历史失败")
