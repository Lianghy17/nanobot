"""ChatBI API路由"""
from .conversations import router as conversations_router
from .messages import router as messages_router
from .scenes import router as scenes_router
from .files import router as files_router
from .sse import router as sse_router
from .patterns import router as patterns_router
from .qa_templates import router as qa_templates_router

__all__ = [
    "conversations_router",
    "messages_router",
    "scenes_router",
    "files_router",
    "sse_router",
    "patterns_router",
    "qa_templates_router",
]
