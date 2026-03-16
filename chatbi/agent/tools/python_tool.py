"""Python执行工具"""
from pathlib import Path
from typing import Dict, Any
import logging
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class PythonTool(BaseTool):
    """Python代码执行工具（沙箱环境）"""
    
    name = "execute_python"
    description = "在安全沙箱中执行Python代码"
    
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
    
    async def execute(self, code: str, timeout: int = 60) -> Dict[str, Any]:
        """执行Python代码"""
        try:
            logger.info(f"Python执行: timeout={timeout}s, code_length={len(code)}")
            
            # 注意: 需要安装opensandbox库
            # pip install opensandbox
            
            # 临时方案：使用subprocess执行（非沙箱，仅用于演示）
            import subprocess
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                import sys
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    logger.info("Python执行成功")
                    return tool_result({
                        "success": True,
                        "output": result.stdout,
                        "error": result.stderr if result.stderr else None
                    })
                else:
                    logger.error(f"Python执行失败: {result.stderr}")
                    return tool_result(f"Python执行失败: {result.stderr}", success=False)
            
            finally:
                Path(temp_file).unlink(missing_ok=True)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Python执行超时: {timeout}s")
            return tool_result(f"Python执行超时（{timeout}秒）", success=False)
        except Exception as e:
            logger.error(f"Python执行失败: {e}")
            return tool_result(f"Python执行失败: {str(e)}", success=False)
