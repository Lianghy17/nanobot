"""文件操作工具"""
from pathlib import Path
from typing import Dict, Any
import logging
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """文件读取工具 - 在沙箱中读取文件"""

    name = "read_file"
    description = "读取沙箱中的文件内容"

    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径（相对于沙箱workspace目录）"
            },
            "limit": {
                "type": "integer",
                "default": 100,
                "description": "读取行数限制"
            }
        },
        "required": ["file_path"]
    }

    def __init__(self):
        super().__init__()
        self.conversation_id = None
        self.sandbox_manager = None

    def set_context(self, user_channel: str):
        """设置上下文"""
        self.user_channel = user_channel
        from ...core.sandbox_manager import SandboxManager
        self.sandbox_manager = SandboxManager()

    def set_conversation_id(self, conversation_id: str):
        """设置当前会话ID"""
        self.conversation_id = conversation_id

    async def execute(self, file_path: str, limit: int = 100) -> Dict[str, Any]:
        """从沙箱中读取文件"""
        try:
            if not self.conversation_id:
                return tool_result("错误: 未设置会话ID，无法获取沙箱", success=False)

            # 获取会话专属沙箱
            session = await self.sandbox_manager.get_sandbox(self.conversation_id)
            if not session:
                return tool_result("错误: 无法获取沙箱", success=False)

            # 构造沙箱信息前缀
            sandbox_info = f"[沙箱: {session.sandbox.sandbox_id}|workspace: {session.sandbox.temp_dir}/workspace|会话: {self.conversation_id}]"

            # 在沙箱中读取文件
            success, content, error_msg = await session.sandbox.read_file(file_path, limit)

            if not success:
                logger.error(f"{sandbox_info} 读取文件失败: {file_path}, error={error_msg}")
                return tool_result(error_msg, success=False)

            # 限制内容大小，防止token爆炸
            max_chars = 5000  # 最多5000字符
            content_truncated = False
            original_length = len(content)
            
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n... [内容已截断，原长度: {original_length} 字符，请使用更小的limit参数或直接访问文件]"
                content_truncated = True
                logger.warning(f"{sandbox_info} 文件内容过大，已截断: {file_path} ({original_length} -> {max_chars} 字符)")

            logger.info(f"{sandbox_info} 读取文件成功: {file_path}")
            return tool_result({
                "success": True,
                "content": content,
                "file_path": file_path,
                "sandbox_type": "local",
                "content_truncated": content_truncated,
                "original_length": original_length if content_truncated else len(content)
            })

        except Exception as e:
            logger.error(f"[沙箱: 无|workspace: 无|会话: {self.conversation_id}] 读取文件异常: {file_path}, error={e}")
            return tool_result(f"读取文件异常: {str(e)}", success=False)


class WriteFileTool(BaseTool):
    """文件写入工具 - 在沙箱中写入文件"""

    name = "write_file"
    description = "写入文件到沙箱（用于保存Python代码、分析结果等）"

    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径（相对于沙箱workspace目录）"
            },
            "content": {
                "type": "string",
                "description": "文件内容"
            },
            "description": {
                "type": "string",
                "description": "文件说明"
            }
        },
        "required": ["file_path", "content"]
    }

    def __init__(self):
        super().__init__()
        self.conversation_id = None
        self.sandbox_manager = None

    def set_context(self, user_channel: str):
        """设置上下文"""
        self.user_channel = user_channel
        from ...core.sandbox_manager import SandboxManager
        self.sandbox_manager = SandboxManager()

    def set_conversation_id(self, conversation_id: str):
        """设置当前会话ID"""
        self.conversation_id = conversation_id

    async def execute(self, file_path: str, content: str, description: str = "") -> Dict[str, Any]:
        """写入文件到沙箱"""
        try:
            if not self.conversation_id:
                return tool_result("错误: 未设置会话ID，无法获取沙箱", success=False)

            # 获取会话专属沙箱
            session = await self.sandbox_manager.get_sandbox(self.conversation_id)
            if not session:
                return tool_result("错误: 无法获取沙箱", success=False)

            # 构造沙箱信息前缀
            sandbox_info = f"[沙箱: {session.sandbox.sandbox_id}|workspace: {session.sandbox.temp_dir}/workspace|会话: {self.conversation_id}]"

            # 在沙箱中写入文件
            await session.sandbox.write_file(file_path, content)

            logger.info(f"{sandbox_info} 写入文件成功: {file_path} ({len(content)} 字节)")
            return tool_result({
                "success": True,
                "file_path": file_path,
                "size": len(content),
                "description": description,
                "sandbox_type": "local"
            })

        except Exception as e:
            logger.error(f"[沙箱: 无|workspace: 无|会话: {self.conversation_id}] 写入文件失败: {file_path}, error={e}")
            return tool_result(f"写入文件失败: {str(e)}", success=False)
