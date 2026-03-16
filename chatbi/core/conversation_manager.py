"""对话管理器"""
import json
import uuid
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from ..config import settings
from ..models import Conversation, ConversationStatus, Message

logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        self.sessions_path = Path(settings.sessions_path)
        self.sessions_path.mkdir(parents=True, exist_ok=True)
    
    def _get_conversation_path(self, user_channel: str, conversation_id: str) -> Path:
        """获取对话文件路径"""
        user_dir = self.sessions_path / user_channel
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / f"{conversation_id}.json"
    
    def create(self, user_channel: str, scene_code: str, scene_name: str, **metadata) -> Conversation:
        """创建新对话"""
        conversation_id = f"conv_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        conversation = Conversation(
            conversation_id=conversation_id,
            user_channel=user_channel,
            scene_code=scene_code,
            scene_name=scene_name,
            metadata=metadata
        )
        
        self.save(conversation)
        logger.info(f"创建对话: {conversation_id}, user={user_channel}, scene={scene_code}")
        return conversation
    
    def get(self, conversation_id: str, user_channel: str) -> Optional[Conversation]:
        """获取对话"""
        file_path = self._get_conversation_path(user_channel, conversation_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Conversation(**data)
        except Exception as e:
            logger.error(f"加载对话失败: {conversation_id}, error={e}")
            return None
    
    def list_by_user(self, user_channel: str, limit: int = 50) -> List[Conversation]:
        """列出用户的所有对话"""
        user_dir = self.sessions_path / user_channel
        
        if not user_dir.exists():
            return []
        
        conversations = []
        for file_path in sorted(user_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if len(conversations) >= limit:
                break
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conv = Conversation(**data)
                if conv.status != ConversationStatus.DELETED:
                    conversations.append(conv)
            except Exception as e:
                logger.warning(f"加载对话文件失败: {file_path}, error={e}")
        
        return conversations
    
    def save(self, conversation: Conversation):
        """保存对话"""
        file_path = self._get_conversation_path(conversation.user_channel, conversation.conversation_id)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation.dict(), f, ensure_ascii=False, indent=2, default=str)
        
        logger.debug(f"保存对话: {conversation.conversation_id}")
    
    def add_message(self, conversation_id: str, user_channel: str, role: str, content: str, **kwargs):
        """添加消息"""
        conversation = self.get(conversation_id, user_channel)
        if not conversation:
            logger.error(f"对话不存在: {conversation_id}")
            return
        
        conversation.add_message(role=role, content=content, **kwargs)
        self.save(conversation)
    
    def delete(self, conversation_id: str, user_channel: str) -> bool:
        """删除对话"""
        conversation = self.get(conversation_id, user_channel)
        if not conversation:
            return False
        
        conversation.status = ConversationStatus.DELETED
        self.save(conversation)
        logger.info(f"删除对话: {conversation_id}")
        return True
    
    def archive(self, conversation_id: str, user_channel: str) -> bool:
        """归档对话"""
        conversation = self.get(conversation_id, user_channel)
        if not conversation:
            return False
        
        conversation.status = ConversationStatus.ARCHIVED
        self.save(conversation)
        logger.info(f"归档对话: {conversation_id}")
        return True
