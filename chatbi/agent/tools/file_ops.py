"""文件操作工具"""
from pathlib import Path
from typing import Dict, Any
import logging
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """文件读取工具"""
    
    name = "read_file"
    description = "读取用户上传的文件内容"
    
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径（相对于用户目录）"
            },
            "limit": {
                "type": "integer",
                "default": 100,
                "description": "读取行数限制"
            }
        },
        "required": ["file_path"]
    }
    
    async def execute(self, file_path: str, limit: int = 100) -> Dict[str, Any]:
        """读取文件"""
        try:
            # 构建完整路径
            user_dir = Path(f"/workspace/files/{self.user_channel}")
            full_path = user_dir / file_path
            
            if not full_path.exists():
                return tool_result(f"文件不存在: {file_path}", success=False)
            
            # 安全检查：确保在用户目录内
            try:
                full_path.resolve().relative_to(user_dir.resolve())
            except ValueError:
                return tool_result("拒绝访问：路径超出用户目录", success=False)
            
            # 读取文件
            lines = []
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    lines.append(line.rstrip('\n'))
            
            content = '\n'.join(lines)
            logger.info(f"读取文件成功: {file_path} ({len(lines)} 行)")
            return tool_result({
                "success": True,
                "content": content,
                "lines_read": len(lines),
                "file_path": file_path
            })
            
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return tool_result(f"读取文件失败: {str(e)}", success=False)


class WriteFileTool(BaseTool):
    """文件写入工具"""
    
    name = "write_file"
    description = "写入文件到用户目录（用于保存Python代码、分析结果等）"
    
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径（相对于用户目录）"
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
    
    async def execute(self, file_path: str, content: str, description: str = "") -> Dict[str, Any]:
        """写入文件"""
        try:
            # 构建完整路径
            user_dir = Path(f"/workspace/files/{self.user_channel}")
            full_path = user_dir / file_path
            
            # 安全检查：确保在用户目录内
            try:
                full_path.resolve().relative_to(user_dir.resolve())
            except ValueError:
                return tool_result("拒绝访问：路径超出用户目录", success=False)
            
            # 创建父目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"写入文件成功: {file_path} ({len(content)} 字节)")
            return tool_result({
                "success": True,
                "file_path": str(full_path.relative_to(user_dir)),
                "size": len(content),
                "description": description
            })
            
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return tool_result(f"写入文件失败: {str(e)}", success=False)
