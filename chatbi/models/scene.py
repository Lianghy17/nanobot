"""场景模型"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Scene(BaseModel):
    """场景模型"""
    scene_code: str = Field(..., description="场景编码")
    scene_name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    supported_skills: List[str] = Field(..., description="支持的技能列表")
    default_model: str = Field(..., description="默认LLM模型")
    max_iterations: int = Field(..., description="最大迭代次数")
