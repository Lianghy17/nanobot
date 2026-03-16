"""Python执行工具"""
from pathlib import Path
from typing import Dict, Any
import logging
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class PythonTool(BaseTool):
    """Python代码执行工具（会话级本地沙箱）"""

    name = "execute_python"
    description = "在会话专属的本地沙箱中执行Python代码"

    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python代码"
            },
            "timeout": {
                "type": "integer",
                "default": 60,
                "description": "超时时间（秒）"
            }
        },
        "required": ["code"]
    }

    def __init__(self):
        super().__init__()
        self.conversation_id = None
        self.sandbox_manager = None

    def set_context(self, user_channel: str):
        """设置上下文"""
        self.user_channel = user_channel
        # 延迟导入避免循环依赖
        from ...core.sandbox_manager import SandboxManager
        self.sandbox_manager = SandboxManager()

    def set_conversation_id(self, conversation_id: str):
        """设置当前会话ID"""
        self.conversation_id = conversation_id

    async def execute(self, code: str, timeout: int = 60) -> Dict[str, Any]:
        """在会话专属的本地沙箱中执行Python代码"""
        if not self.conversation_id:
            return tool_result("错误: 未设置会话ID，无法获取沙箱", success=False)

        logger.info(f"[本地沙箱执行] conversation_id={self.conversation_id}, timeout={timeout}s, code_length={len(code)}")

        # 获取会话专属沙箱
        session = await self.sandbox_manager.get_sandbox(self.conversation_id)

        if not session:
            logger.error(f"无法获取沙箱: {self.conversation_id}")
            return tool_result("错误: 无法创建沙箱", success=False)

        try:
            # 在沙箱中执行代码
            result = await session.execute_code(code, timeout)

            if result["success"]:
                logger.info(f"[本地沙箱执行] 执行成功: {self.conversation_id}")
                return tool_result({
                    "success": True,
                    "output": result["output"],
                    "error": result["error"],
                    "sandbox_type": "local_process",
                    "sandbox_id": session.sandbox.sandbox_id
                })
            else:
                logger.error(f"[本地沙箱执行] 执行失败: {self.conversation_id}, error={result['error']}")
                return tool_result(f"执行失败: {result['error']}", success=False)

        except Exception as e:
            logger.error(f"[本地沙箱执行] 执行异常: {self.conversation_id}, error={e}")
            return tool_result(f"执行异常: {str(e)}", success=False)
