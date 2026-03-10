"""Scene configuration for ChatBI."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SceneConfig:
    """Configuration for a ChatBI scene."""
    
    scene_code: str
    scene_name: str
    description: str
    system_prompt: str
    enabled_skills: list[str] = field(default_factory=list)
    skill_configs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# Predefined scene configurations
DEFAULT_SCENES: dict[str, SceneConfig] = {
    "sales_analysis": SceneConfig(
        scene_code="sales_analysis",
        scene_name="销售数据分析",
        description="用于销售数据的查询、分析和预测",
        system_prompt="""你是一个专业的销售数据分析助手。你可以帮助用户：
- 查询销售数据和指标
- 分析销售趋势
- 进行销售预测
- 生成销售报告

请根据用户的问题选择合适的工具，提供准确、专业的回答。""",
        enabled_skills=["mysql_query", "knowledge_search", "schema_search", "qa_search", "time_series_forecast"],
    ),
    "user_behavior": SceneConfig(
        scene_code="user_behavior",
        scene_name="用户行为分析",
        description="用于用户行为数据的查询和分析",
        system_prompt="""你是一个专业的用户行为分析助手。你可以帮助用户：
- 查询用户行为数据
- 分析用户活跃度
- 计算用户留存率
- 分析用户路径

请根据用户的问题选择合适的工具，提供准确、专业的回答。""",
        enabled_skills=["hive_query", "knowledge_search", "schema_search", "qa_search"],
    ),
    "general_bi": SceneConfig(
        scene_code="general_bi",
        scene_name="通用数据查询",
        description="用于通用的数据查询和分析",
        system_prompt="""你是一个专业的数据查询助手。你可以帮助用户：
- 查询各类数据
- 了解数据结构
- 获取业务知识
- 回答常见问题

请根据用户的问题选择合适的工具，提供准确、专业的回答。""",
        enabled_skills=["mysql_query", "hive_query", "knowledge_search", "schema_search", "qa_search"],
    ),
}
