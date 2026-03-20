"""SSE API"""
import logging
import asyncio
import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..core.sse_manager import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def event_generator(conversation_id: str):
    """生成SSE事件"""
    try:
        # 创建消息队列
        queue = asyncio.Queue()

        # 注册连接
        connection = sse_manager.add_connection(conversation_id, queue)

        logger.info(f"[SSE] 客户端连接: conversation_id={conversation_id}")

        try:
            # 发送连接成功事件
            yield {
                "event": "connected",
                "data": json.dumps({
                    "conversation_id": conversation_id,
                    "message": "连接已建立"
                }, ensure_ascii=False)
            }

            # 持续发送事件
            while True:
                # 等待新事件（超时30秒发送心跳）
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 发送事件（data需要是JSON字符串）
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"], ensure_ascii=False),
                        "id": event["id"],
                        "retry": event["retry"]
                    }

                except asyncio.TimeoutError:
                    # 发送心跳事件
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                    }

        finally:
            # 客户端断开连接时清理
            sse_manager.remove_connection(conversation_id)
            logger.info(f"[SSE] 客户端断开: conversation_id={conversation_id}")

    except Exception as e:
        logger.error(f"[SSE] 事件生成器异常: {e}")
        raise


@router.get("/stream/{conversation_id}")
async def stream_conversation(conversation_id: str):
    """
    SSE流式端点
    客户端建立连接后，服务器会主动推送消息处理状态
    """
    return EventSourceResponse(
        event_generator(conversation_id),
        media_type="text/event-stream"
    )


@router.get("/stats")
async def get_sse_stats():
    """获取SSE连接统计"""
    return sse_manager.get_stats()
