"""RAG查询工具"""
import httpx
import logging
from typing import Dict, Any
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class RAGTool(BaseTool):
    """RAG知识库查询工具"""
    
    name = "rag_search"
    description = "查询RAG知识库获取文档、数据表结构、QA示例"
    
    parameters = {
        "type": "object",
        "properties": {
            "scene_code": {
                "type": "string",
                "description": "场景编码"
            },
            "query": {
                "type": "string",
                "description": "用户问题"
            },
            "type": {
                "type": "string",
                "enum": ["doc", "schema", "qa", "all"],
                "default": "all",
                "description": "查询类型: doc(文档), schema(表结构), qa(QA示例), all(全部)"
            }
        },
        "required": ["scene_code", "query"]
    }
    
    async def execute(self, scene_code: str, query: str, type: str = "all") -> Dict[str, Any]:
        """执行RAG查询"""
        try:
            logger.info(f"RAG查询: scene={scene_code}, query={query}, type={type}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://my_rag_v1",
                    json={
                        "scene_code": scene_code,
                        "query": query,
                        "type": type
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # 格式化结果
                result = {
                    "success": True,
                    "docs": data.get("docs", []),
                    "schemas": data.get("schemas", []),
                    "qa_examples": data.get("qa_examples", [])
                }
                
                logger.info(f"RAG查询成功: {len(result['docs'])} docs, {len(result['schemas'])} schemas, {len(result['qa_examples'])} qa")
                return tool_result(result)
                
        except httpx.HTTPError as e:
            logger.error(f"RAG HTTP错误: {e}")
            # 模拟返回（用于开发测试）
            return tool_result({
                "success": True,
                "docs": [
                    {
                        "title": f"关于 '{query}' 的文档",
                        "content": "这是模拟的RAG返回内容，请配置真实的RAG服务地址。",
                        "score": 0.95
                    }
                ],
                "schemas": [],
                "qa_examples": []
            })
        except Exception as e:
            logger.error(f"RAG查询失败: {e}")
            return tool_result(f"RAG查询失败: {str(e)}", success=False)
