"""消息处理器"""
from typing import Dict, Any
import logging
from ..models import Message
from .agent_wrapper import AgentWrapper
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class MessageProcessor:
    """消息处理器 - 处理用户消息并调用Agent"""
    
    def __init__(self):
        self.agent_wrapper = AgentWrapper()
        self.conversation_manager = ConversationManager()
    
    async def process(self, message: Message):
        """处理消息"""
        print(f"\n{'='*80}")
        print(f"[终端输出] 处理消息: {message.id}, conv_id={message.conversation_id}")
        print(f"{'='*80}\n")
        logger.info(f"处理消息: {message.id}, conv_id={message.conversation_id}")
        
        # 保存用户消息
        self.conversation_manager.add_message(
            conversation_id=message.conversation_id,
            user_channel=message.user_channel,
            role="user",
            content=message.content,
            metadata=message.metadata or {}
        )
        
        # 获取对话信息
        conversation = self.conversation_manager.get(
            message.conversation_id,
            message.user_channel
        )
        
        if not conversation:
            logger.error(f"对话不存在: {message.conversation_id}")
            return
        
        # 调用Agent处理
        try:
            response = await self.agent_wrapper.process(
                conversation=conversation,
                message=message
            )
            
            if response:
                # 保存助手回复
                self.conversation_manager.add_message(
                    conversation_id=message.conversation_id,
                    user_channel=message.user_channel,
                    role="assistant",
                    content=response.get("content", ""),
                    tools_used=response.get("tools_used"),
                    tool_calls=response.get("tool_calls"),
                    metadata=response.get("metadata", {})
                )
                
                logger.info(f"消息处理完成: {message.id}")
            else:
                logger.warning(f"Agent未返回响应: {message.id}")
                
        except Exception as e:
            logger.error(f"处理消息失败: {message.id}, error={e}")
            
            # 保存错误消息
            self.conversation_manager.add_message(
                conversation_id=message.conversation_id,
                user_channel=message.user_channel,
                role="assistant",
                content=f"抱歉，处理您的请求时发生错误：{str(e)}",
                metadata={"error": True}
            )
