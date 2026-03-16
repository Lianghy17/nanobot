"""ChatBI API路由"""
from .conversations import router as conversations_router
from .messages import router as messages_router
from .scenes import router as scenes_router
from .files import router as files_router

__all__ = [
    "conversations_router",
    "messages_router",
    "scenes_router",
    "files_router",
]
