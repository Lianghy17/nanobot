"""消息处理器"""
import os
from typing import Optional
import logging
from ..models import Message
from .agent_wrapper import AgentWrapper, TaskCancelledException
from .conversation_manager import ConversationManager
from .sse_manager import sse_manager

logger = logging.getLogger(__name__)


class MessageProcessor:
    """消息处理器 - 处理用户消息并调用Agent（单例模式）"""

    _instance: Optional["MessageProcessor"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.agent_wrapper = AgentWrapper()
        self.conversation_manager = ConversationManager()
    
    async def process(self, message: Message):
        """处理消息"""
        pid = os.getpid()
        print(f"\n{'='*80}")
        print(f"[PID:{pid}] [终端输出] 处理消息: {message.id}, conv_id={message.conversation_id}")
        print(f"{'='*80}\n")
        logger.info(f"[PID:{pid}] 处理消息: {message.id}, conv_id={message.conversation_id}")

        # 检查消息是否已被取消
        if sse_manager.is_cancelled(message.id):
            logger.info(f"消息已被取消，跳过处理: {message.id}")
            await sse_manager.send_event(
                message.conversation_id,
                "processing_cancelled",
                {
                    "message_id": message.id,
                    "content": "任务已被取消"
                }
            )
            # 清除取消标记
            sse_manager.clear_cancelled(message.id)
            return

        # 发送处理开始事件
        await sse_manager.send_event(
            message.conversation_id,
            "processing_started",
            {
                "message_id": message.id,
                "content": message.content
            }
        )

        # 保存用户消息
        self.conversation_manager.add_message(
            conversation_id=message.conversation_id,
            user_channel=message.user_channel,
            role="user",
            content=message.content,
            metadata=message.metadata or {}
        )

        # 发送用户消息已保存事件
        await sse_manager.send_event(
            message.conversation_id,
            "user_message_saved",
            {
                "message_id": message.id,
                "content": message.content
            }
        )

        # 获取对话信息
        conversation = self.conversation_manager.get(
            message.conversation_id,
            message.user_channel
        )

        if not conversation:
            logger.error(f"对话不存在: {message.conversation_id}")
            # 发送错误事件
            await sse_manager.send_event(
                message.conversation_id,
                "error",
                {
                    "message": "对话不存在",
                    "conversation_id": message.conversation_id
                }
            )
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

                # 发送处理完成事件
                files_data = response.get("metadata", {}).get("files", [])
                metadata = response.get("metadata", {})
                logger.info(f"[SSE] 发送处理完成事件, files数量: {len(files_data)}, files: {files_data}, metadata: {metadata}")

                await sse_manager.send_event(
                    message.conversation_id,
                    "processing_completed",
                    {
                        "message_id": message.id,
                        "content": response.get("content", ""),
                        "tools_used": response.get("tools_used", []),
                        "files": files_data,
                        "metadata": metadata
                    }
                )

                logger.info(f"消息处理完成: {message.id}")
            else:
                logger.warning(f"Agent未返回响应: {message.id}")
                # 发送无响应事件
                await sse_manager.send_event(
                    message.conversation_id,
                    "error",
                    {
                        "message": "Agent未返回响应",
                        "message_id": message.id
                    }
                )

        except Exception as e:
            logger.error(f"处理消息失败: {message.id}, error={e}")

            # 保存错误消息（除非是任务取消）
            if not isinstance(e, TaskCancelledException):
                self.conversation_manager.add_message(
                    conversation_id=message.conversation_id,
                    user_channel=message.user_channel,
                    role="assistant",
                    content=f"抱歉，处理您的请求时发生错误：{str(e)}",
                    metadata={"error": True}
                )

                # 发送错误事件
                await sse_manager.send_event(
                    message.conversation_id,
                    "error",
                    {
                        "message": f"处理您的请求时发生错误：{str(e)}",
                        "message_id": message.id
                    }
                )
            else:
                # 任务被取消
                logger.info(f"任务已被取消: {message.id}")
                # 保存取消消息
                self.conversation_manager.add_message(
                    conversation_id=message.conversation_id,
                    user_channel=message.user_channel,
                    role="assistant",
                    content="任务已被取消",
                    metadata={"cancelled": True}
                )

                # 发送取消事件
                await sse_manager.send_event(
                    message.conversation_id,
                    "processing_cancelled",
                    {
                        "message_id": message.id,
                        "content": "任务已被取消"
                    }
                )

            # 清除取消标记
            sse_manager.clear_cancelled(message.id)
