"""对话管理API"""
import json
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pathlib import Path
from pydantic import BaseModel

from ..core.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)
from ..core.loop_queue import LoopQueue
from ..channels.web_channel import WebChannel

router = APIRouter()


class ConversationCreateRequest(BaseModel):
    """创建对话请求"""
    scene_code: str


class ConversationResponse(BaseModel):
    """对话响应"""
    conversation_id: str
    scene_code: str
    scene_name: str
    created_at: str


# 依赖注入
def get_conversation_manager():
    return ConversationManager()


def get_loop_queue():
    return LoopQueue.get_instance()


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    user_id: str = "web_default_user",  # 实际应用中从JWT获取
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """创建新对话"""
    try:
        # 加载场景配置
        scene_config = _load_scene_config(request.scene_code)
        if not scene_config:
            raise HTTPException(status_code=400, detail=f"场景不存在: {request.scene_code}")
        
        # 生成用户Channel标识
        user_channel = f"web_{user_id}"
        
        # 创建对话
        conversation = conv_manager.create(
            user_channel=user_channel,
            scene_code=scene_config["scene_code"],
            scene_name=scene_config["scene_name"],
            user_id=user_id
        )
        
        logger.info(f"创建对话: {conversation.conversation_id}")
        
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            scene_code=conversation.scene_code,
            scene_name=conversation.scene_name,
            created_at=conversation.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail="创建对话失败")


@router.get("/", response_model=List[dict])
async def list_conversations(
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """获取用户的对话列表"""
    try:
        user_channel = f"web_{user_id}"
        conversations = conv_manager.list_by_user(user_channel)
        
        return [
            {
                "conversation_id": conv.conversation_id,
                "scene_name": conv.scene_name,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(conv.messages),
                "title": conv.messages[0].content[:50] if conv.messages else "新对话"
            }
            for conv in conversations
        ]
    
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话列表失败")


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """获取对话详情（包含消息列表）"""
    try:
        user_channel = f"web_{user_id}"
        conversation = conv_manager.get(conversation_id, user_channel)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {
            "conversation_id": conversation.conversation_id,
            "scene_code": conversation.scene_code,
            "scene_name": conversation.scene_name,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tools_used": msg.tools_used
                }
                for msg in conversation.messages
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话详情失败")


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """获取对话的消息列表（兼容前端调用）"""
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
        logger.error(f"获取对话消息列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话消息列表失败")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = "web_default_user",
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """删除对话"""
    try:
        user_channel = f"web_{user_id}"
        success = conv_manager.delete(conversation_id, user_channel)
        
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        logger.info(f"删除对话: {conversation_id}")
        return {"success": True, "message": "对话已删除"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail="删除对话失败")


def _load_scene_config(scene_code: str) -> dict:
    """加载场景配置"""
    try:
        config_path = Path("/config/scenes.json")
        if not config_path.exists():
            # 使用相对路径
            config_path = Path(__file__).parent.parent.parent / "config" / "scenes.json"
        
        if not config_path.exists():
            logger.warning(f"场景配置文件不存在: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for scene in data.get("scenes", []):
            if scene.get("scene_code") == scene_code:
                return scene
        
        return None
    
    except Exception as e:
        logger.error(f"加载场景配置失败: {e}")
        return None
