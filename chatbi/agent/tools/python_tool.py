"""Python执行工具"""
from pathlib import Path
from typing import Dict, Any, Optional
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

    def _preprocess_code(self, code: str) -> str:
        """预处理代码，处理兼容性问题"""
        # 移除 matplotlib stem() 的过时参数 use_line_collection
        code = code.replace("use_line_collection=True", "")
        code = code.replace("use_line_collection=False", "")
        code = code.replace("use_line_collection=True,", "")
        code = code.replace("use_line_collection=False,", "")
        return code

    async def execute(self, code: str, timeout: int = 60) -> Dict[str, Any]:
        """在会话专属的本地沙箱中执行Python代码"""
        if not self.conversation_id:
            return tool_result("错误: 未设置会话ID，无法获取沙箱", success=False)

        logger.info(f"[本地沙箱执行] conversation_id={self.conversation_id}, timeout={timeout}s, code_length={len(code)}")

        # 预处理代码：移除 matplotlib 的过时参数
        code = self._preprocess_code(code)

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

                # 处理生成的文件
                files = result.get("files", [])
                file_info = []
                for file_data in files:
                    # 保存文件到会话目录
                    saved_path = await self._save_file_to_conversation(file_data)
                    if saved_path:
                        file_info.append({
                            "filename": file_data["filename"],
                            "type": file_data["type"],
                            "size": file_data["size"],
                            "path": saved_path
                        })

                response_data = {
                    "success": True,
                    "output": result["output"],
                    "error": result["error"],
                    "sandbox_type": "local_process",
                    "sandbox_id": session.sandbox.sandbox_id,
                    "files": file_info
                }

                return tool_result(response_data)
            else:
                logger.error(f"[本地沙箱执行] 执行失败: {self.conversation_id}, error={result['error']}")
                return tool_result(f"执行失败: {result['error']}", success=False)

        except Exception as e:
            logger.error(f"[本地沙箱执行] 执行异常: {self.conversation_id}, error={e}")
            return tool_result(f"执行异常: {str(e)}", success=False)

    async def _save_file_to_conversation(self, file_data: dict) -> Optional[str]:
        """保存文件到会话目录"""
        try:
            from pathlib import Path
            from ..config import settings

            # 构建保存路径
            conversation_dir = Path(self.user_channel) / self.conversation_id
            full_path = Path(settings.sessions_path) / conversation_dir
            full_path.mkdir(parents=True, exist_ok=True)

            file_path = full_path / file_data["filename"]

            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_data["content"])

            # 返回相对路径用于API访问
            relative_path = str(conversation_dir / file_data["filename"])
            logger.info(f"保存文件: {file_data['filename']} -> {relative_path}")
            return relative_path

        except Exception as e:
            logger.error(f"保存文件失败: {file_data['filename']}, error={e}")
            return None
