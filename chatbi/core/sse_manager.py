"""SSE连接管理器"""
import asyncio
import logging
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SSEConnection:
    """SSE连接"""

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.created_at = datetime.now()

    async def send(self, event_type: str, data: Dict[str, Any]):
        """发送事件"""
        await self.queue.put({
            "event": event_type,
            "data": data,
            "retry": 3000,
            "id": str(datetime.now().timestamp())
        })


class SSEManager:
    """SSE连接管理器（单例模式）"""

    _instance: Optional["SSEManager"] = None
    _connections: Dict[str, SSEConnection] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

    def add_connection(self, conversation_id: str, queue: asyncio.Queue) -> SSEConnection:
        """添加SSE连接"""
        connection = SSEConnection(queue)
        self._connections[conversation_id] = connection
        logger.info(f"[SSE] 新连接: conversation_id={conversation_id}, 当前连接数={len(self._connections)}")
        return connection

    def remove_connection(self, conversation_id: str):
        """移除SSE连接"""
        if conversation_id in self._connections:
            del self._connections[conversation_id]
            logger.info(f"[SSE] 连接已移除: conversation_id={conversation_id}, 剩余连接数={len(self._connections)}")

    def get_connection(self, conversation_id: str) -> Optional[SSEConnection]:
        """获取SSE连接"""
        return self._connections.get(conversation_id)

    def has_connection(self, conversation_id: str) -> bool:
        """检查是否存在连接"""
        return conversation_id in self._connections

    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return {
            "total_connections": len(self._connections),
            "conversations": list(self._connections.keys())
        }

    async def send_event(self, conversation_id: str, event_type: str, data: Dict[str, Any]):
        """向指定对话发送事件"""
        connection = self.get_connection(conversation_id)
        if connection:
            try:
                await connection.send(event_type, data)
                logger.info(f"[SSE] 发送事件成功: conversation_id={conversation_id}, event={event_type}")
            except Exception as e:
                logger.error(f"[SSE] 发送事件失败: conversation_id={conversation_id}, error={e}")
                # 移除失败的连接
                self.remove_connection(conversation_id)
        else:
            logger.warning(f"[SSE] 无连接: conversation_id={conversation_id}, event={event_type}, 当前连接数={len(self._connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """向所有连接广播事件"""
        for conversation_id in list(self._connections.keys()):
            await self.send_event(conversation_id, event_type, data)


# 全局单例
sse_manager = SSEManager()
