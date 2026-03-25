"""工具执行器 - 工具注册、上下文设置、执行和结果处理"""
import json
import logging
from typing import Dict, Any, List, Optional
from ..config import chatbi_config
from ..agent.tools import RAGTool, SQLTool, PythonTool, ReadFileTool, WriteFileTool
from .memory import MemoryStore
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolExecutor:
    """工具执行器 - 管理工具的注册、上下文和执行"""

    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self.memory_store: Optional[MemoryStore] = None
        self._register_tools()

    def _register_tools(self):
        """注册工具"""
        self._tools = {
            "rag_search": RAGTool(),
            "execute_sql": SQLTool(),
            "execute_python": PythonTool(),
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
        }
        logger.info(f"注册工具: {list(self._tools.keys())}")

    def set_tool_context(self, user_channel: str, conversation_id: str = None):
        """设置所有工具的上下文"""
        memory_key = f"conv:{conversation_id}" if conversation_id else None
        self.memory_store = MemoryStore(Path(chatbi_config.workspace_path), memory_key=memory_key)

        for tool in self._tools.values():
            tool.set_context(user_channel)
            if hasattr(tool, 'set_conversation_id') and conversation_id:
                tool.set_conversation_id(conversation_id)

    def get_tool_definitions(self, scene_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取工具的定义，可按场景过滤"""
        if scene_code:
            supported_skills = chatbi_config.get_scene_supported_skills(scene_code)
            if supported_skills:
                logger.info(f"[场景工具过滤] 场景={scene_code}, 支持的工具={supported_skills}")
                return [
                    self._tools[skill].get_definition()
                    for skill in supported_skills
                    if skill in self._tools
                ]
        return [tool.get_definition() for tool in self._tools.values()]

    def get_tool_names(self, scene_code: Optional[str] = None) -> str:
        """获取工具名称列表（逗号分隔），用于系统提示"""
        if scene_code:
            supported_skills = chatbi_config.get_scene_supported_skills(scene_code)
            if supported_skills:
                return ", ".join(supported_skills)
        return ", ".join(self._tools.keys())

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """执行工具并返回结果字符串"""
        if tool_name not in self._tools:
            logger.error(f"[工具执行] 工具 '{tool_name}' 不存在")
            return f"Error: Tool '{tool_name}' not found"

        tool = self._tools[tool_name]

        try:
            logger.info("=" * 80)
            logger.info(f"[工具执行] 开始执行: {tool_name}")
            logger.info(f"[工具执行] 参数: {json.dumps(tool_args, ensure_ascii=False)}")

            result = await tool.execute(**tool_args)

            if result.get("success"):
                result_str = json.dumps(result.get("result"), ensure_ascii=False)
                logger.info(f"[工具执行] 成功: {result_str[:200]}{'...' if len(result_str) > 200 else ''}")
                logger.info("=" * 80)
                return result_str
            else:
                error_msg = result.get("result", "Unknown error")
                logger.error(f"[工具执行] 失败: {tool_name}, 错误: {error_msg}")
                logger.info("=" * 80)
                return f"Error: {error_msg}"

        except Exception as e:
            logger.error(f"[工具执行] 异常: {tool_name}, 错误: {e}", exc_info=True)
            logger.info("=" * 80)
            return f"Error: {str(e)}"

    @staticmethod
    def compress_tool_result(result: str, tool_name: str) -> str:
        """压缩工具结果（防止token爆炸）"""
        max_length = chatbi_config.agent_max_tool_result_length

        if len(result) <= max_length:
            return result

        if tool_name == "execute_python":
            try:
                result_obj = json.loads(result)
                if isinstance(result_obj, dict) and "files" in result_obj:
                    files_info = result_obj["files"]
                    compressed = json.dumps({
                        "success": result_obj.get("success"),
                        "output": result_obj.get("output", "")[:500],
                        "files": files_info,
                        "_truncated": True,
                        "_original_length": len(result)
                    }, ensure_ascii=False)
                    return compressed
            except (json.JSONDecodeError, TypeError):
                pass
            return result[:max_length] + f"\n\n... [结果已截断，原长度: {len(result)} 字符]"

        elif tool_name == "read_file":
            return result

        else:
            return result[:max_length] + f"\n\n... [结果已截断，原长度: {len(result)} 字符]"

    @staticmethod
    def extract_files_from_tool_results(tool_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从工具结果中提取文件信息"""
        files = []
        logger.info(f"[文件提取] 开始提取，tool_messages数量: {len(tool_messages)}")

        for idx, msg in enumerate(tool_messages):
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                try:
                    result = json.loads(content)
                    if isinstance(result, dict):
                        if "files" in result:
                            extracted = result["files"]
                            logger.info(f"[文件提取] 找到文件（格式1）: {len(extracted)} 个")
                            files.extend(extracted)
                        elif "result" in result and isinstance(result["result"], dict):
                            result_data = result["result"]
                            if "files" in result_data:
                                extracted = result_data["files"]
                                logger.info(f"[文件提取] 找到文件（格式2）: {len(extracted)} 个")
                                files.extend(extracted)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"[文件提取] 解析工具结果失败: {e}")

        logger.info(f"[文件提取] 提取完成，共找到 {len(files)} 个文件")
        return files
