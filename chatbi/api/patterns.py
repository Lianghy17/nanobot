"""Pattern API路由"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional

from ..core.pattern_loader import PatternLoader
from ..core.intent_analyzer import IntentAnalyzer
from ..core.llm_client import LLMClient
from ..config import chatbi_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/catalog")
async def get_pattern_catalog():
    """获取Pattern目录"""
    try:
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        catalog = pattern_loader.get_pattern_catalog()
        
        return {
            "status": "success",
            "catalog": catalog,
            "categories": pattern_loader._config.get("categories", {}),
            "global_settings": pattern_loader._config.get("global_settings", {})
        }
    except Exception as e:
        logger.error(f"获取Pattern目录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取Pattern目录失败: {str(e)}")


@router.get("/{pattern_id}")
async def get_pattern_detail(pattern_id: str):
    """获取Pattern详情"""
    try:
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        pattern = pattern_loader.get_pattern(pattern_id)
        
        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
        
        # 获取热门模板
        hot_templates = pattern_loader.get_hot_templates(pattern_id)
        
        return {
            "status": "success",
            "pattern": {
                "id": pattern.id,
                "name": pattern.name,
                "description": pattern.description,
                "category": pattern.category,
                "complexity": pattern.complexity,
                "time_mode": pattern.time_mode,
                "space_mode": pattern.space_mode,
                "sql_template": pattern.sql_template,
                "features": pattern.features,
                "required_tables": pattern.required_tables,
                "optional_features": pattern.optional_features,
                "params_schema": pattern.params_schema,
                "hot_templates": hot_templates
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Pattern详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取Pattern详情失败: {str(e)}")


@router.get("/{pattern_id}/templates")
async def get_pattern_templates(pattern_id: str):
    """获取Pattern的热门问题模板"""
    try:
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        pattern = pattern_loader.get_pattern(pattern_id)
        
        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
        
        hot_templates = pattern_loader.get_hot_templates(pattern_id)
        
        return {
            "status": "success",
            "pattern_id": pattern_id,
            "templates": hot_templates
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Pattern模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取Pattern模板失败: {str(e)}")


@router.post("/analyze")
async def analyze_intent(request: Dict[str, Any]):
    """分析用户意图(匹配Pattern)"""
    try:
        user_query = request.get("query")
        scene_code = request.get("scene_code")
        context = request.get("context", {})
        
        if not user_query:
            raise HTTPException(status_code=400, detail="缺少query参数")
        
        # 初始化组件
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout,
            thinking_disabled=chatbi_config.llm_thinking_disabled
        )
        
        intent_analyzer = IntentAnalyzer(llm_client, pattern_loader)
        
        # 分析意图
        result = await intent_analyzer.analyze(user_query, scene_code, context)
        
        return {
            "status": "success",
            "result": {
                "intent_type": result.intent_type,
                "matched_pattern": result.matched_pattern,
                "pattern_name": result.pattern_config.name if result.pattern_config else None,
                "pattern_description": result.pattern_config.description if result.pattern_config else None,
                "confidence": result.confidence,
                "params": result.params,
                "clarification_needed": result.clarification_needed,
                "clarification_questions": result.clarification_questions,
                "description": result.description
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"意图分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"意图分析失败: {str(e)}")


@router.post("/build-sql")
async def build_sql(request: Dict[str, Any]):
    """根据Pattern和参数构建SQL"""
    try:
        pattern_id = request.get("pattern_id")
        params = request.get("params", {})
        context = request.get("context", {})
        
        if not pattern_id:
            raise HTTPException(status_code=400, detail="缺少pattern_id参数")
        
        # 初始化组件
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        from ..core.sql_builder import PatternSQLBuilder
        sql_builder = PatternSQLBuilder(pattern_loader)
        
        # 构建SQL
        sql, error = sql_builder.build(pattern_id, params, context)
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            "status": "success",
            "pattern_id": pattern_id,
            "sql": sql,
            "params": params
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL构建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SQL构建失败: {str(e)}")


@router.get("/scene/{scene_code}/supported")
async def get_scene_supported_patterns(scene_code: str):
    """获取场景支持的Patterns"""
    try:
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        
        # TODO: 从场景配置中读取支持的patterns
        # 目前返回所有patterns
        all_patterns = pattern_loader.get_all_patterns()
        
        # 过滤场景支持的patterns
        # 这里可以添加场景特定的过滤逻辑
        supported_patterns = list(all_patterns.values())
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "supported_patterns": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "complexity": p.complexity
                }
                for p in supported_patterns
            ]
        }
    except Exception as e:
        logger.error(f"获取场景支持的Patterns失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景支持的Patterns失败: {str(e)}")


@router.get("/hot-questions")
async def get_hot_questions(scene_code: Optional[str] = None):
    """获取热门问题(按场景)"""
    logger.info(f"[GET /api/patterns/hot-questions] scene_code={scene_code}")
    try:
        # 简化版本：直接返回测试数据
        return {
            "status": "success",
            "scene_code": scene_code,
            "hot_questions": [
                {
                    "pattern_id": "point_query",
                    "pattern_name": "点查",
                    "question": "查询今天的销售额",
                    "template": "查询{{time_point}}的{{metric}}",
                    "default_params": {"metric": "销售额", "time_point": "今天"}
                }
            ],
            "total": 1
        }
    except Exception as e:
        logger.error(f"获取热门问题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取热门问题失败: {str(e)}")
