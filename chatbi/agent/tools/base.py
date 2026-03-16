"""工具基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any


def tool_result(result: Any, success: bool = True) -> Dict[str, Any]:
    """格式化工具结果"""
    return {
        "success": success,
        "result": result
    }


class BaseTool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    
    def __init__(self):
        self.user_channel: str = ""
    
    def set_context(self, user_channel: str):
        """设置上下文"""
        self.user_channel = user_channel
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    def get_definition(self) -> Dict[str, Any]:
        """获取工具定义（用于LLM）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
