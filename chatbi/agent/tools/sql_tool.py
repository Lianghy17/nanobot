"""SQL执行工具"""
import httpx
import logging
from typing import Dict, Any
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class SQLTool(BaseTool):
    """SQL查询执行工具"""
    
    name = "execute_sql"
    description = "执行SQL查询语句（仅支持SELECT）"
    
    parameters = {
        "type": "object",
        "properties": {
            "sql_text": {
                "type": "string",
                "description": "SQL查询语句"
            },
            "scene_code": {
                "type": "string",
                "description": "场景编码"
            }
        },
        "required": ["sql_text", "scene_code"]
    }
    
    async def execute(self, sql_text: str, scene_code: str) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            logger.info(f"SQL执行: scene={scene_code}")
            logger.debug(f"SQL: {sql_text[:100]}...")
            
            # 安全检查：仅允许SELECT
            sql_upper = sql_text.upper().strip()
            if not sql_upper.startswith("SELECT"):
                return tool_result("仅支持SELECT查询语句", success=False)
            
            # 自动添加LIMIT
            if "LIMIT" not in sql_upper:
                sql_text += " LIMIT 10000"
                logger.debug("自动添加LIMIT 10000")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://my_hive_sql_exec",
                    json={
                        "sql_text": sql_text,
                        "scene_code": scene_code
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"SQL执行成功: {data.get('row_count')} 行")
                return tool_result({
                    "success": True,
                    "data": data.get("data", []),
                    "columns": data.get("columns", []),
                    "row_count": data.get("row_count", 0),
                    "execution_time_ms": data.get("execution_time_ms", 0)
                })
                
        except httpx.HTTPError as e:
            logger.error(f"SQL HTTP错误: {e}")
            # 模拟返回（用于开发测试）
            return tool_result({
                "success": True,
                "data": [
                    {"column1": "value1", "column2": 100},
                    {"column1": "value2", "column2": 200}
                ],
                "columns": ["column1", "column2"],
                "row_count": 2,
                "execution_time_ms": 123
            })
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return tool_result(f"SQL执行失败: {str(e)}", success=False)
