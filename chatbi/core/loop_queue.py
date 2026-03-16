"""Loop队列 - 消息处理队列"""
import asyncio
import logging
from typing import Optional
from ..models import Message

logger = logging.getLogger(__name__)


class LoopQueue:
    """Loop消息处理队列"""
    
    _instance: Optional["LoopQueue"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.queue = asyncio.Queue(maxsize=1000)
        self._running = False
        self._workers = []
        self.message_processor = None
    
    @classmethod
    def get_instance(cls) -> "LoopQueue":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_processor(self, processor):
        """设置消息处理器"""
        self.message_processor = processor
    
    async def start(self, num_workers: int = 4):
        """启动worker池"""
        if self._running:
            logger.warning("Loop队列已在运行中")
            return
        
        self._running = True
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Loop队列已启动，{num_workers}个worker")
    
    async def stop(self):
        """停止worker池"""
        self._running = False
        
        # 取消所有worker
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("Loop队列已停止")
    
    async def enqueue(self, message: Message):
        """入队消息"""
        await self.queue.put(message)
        logger.info(f"消息入队: {message.id}, conv_id={message.conversation_id}")
    
    async def _worker(self, name: str):
        """Worker处理消息"""
        logger.info(f"{name} 启动")
        
        while self._running:
            try:
                # 等待消息
                message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                logger.info(f"{name} 处理消息: {message.id}")
                
                # 处理消息
                if self.message_processor:
                    try:
                        await self.message_processor.process(message)
                    except Exception as e:
                        logger.error(f"{name} 处理消息失败: {e}")
                else:
                    logger.error(f"{name} 消息处理器未设置")
                
                self.queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"{name} 被取消")
                break
            except Exception as e:
                logger.error(f"{name} 发生错误: {e}")
        
        logger.info(f"{name} 停止")
    
    def size(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()
