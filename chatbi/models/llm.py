"""LLM响应模型"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    id: str = Field(..., description="工具调用ID")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class UsageInfo(BaseModel):
    """使用量信息"""
    prompt_tokens: int = Field(default=0, description="提示词token数")
    completion_tokens: int = Field(default=0, description="完成token数")
    total_tokens: int = Field(default=0, description="总token数")


class LLMResponse(BaseModel):
    """LLM响应"""
    content: Optional[str] = Field(None, description="响应内容")
    tool_calls: List[ToolCallRequest] = Field(default_factory=list, description="工具调用列表")
    finish_reason: str = Field(default="stop", description="结束原因")
    usage: UsageInfo = Field(default_factory=UsageInfo, description="使用量信息")
    reasoning_content: Optional[str] = Field(None, description="推理内容（如果有）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
