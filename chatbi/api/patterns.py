"""Scene模板API路由 - 只使用scenes.json中的配置"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional

from ..core.template_loader import SceneTemplateLoader
from ..core.intent_analyzer import IntentAnalyzer
from ..core.llm_client import LLMClient
from ..config import chatbi_config
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()


def get_template_loader():
    """获取模板加载器实例"""
    scenes_config_path = Path(chatbi_config.config_dir) / "scenes.json"
    return SceneTemplateLoader(str(scenes_config_path))


@router.get("/catalog")
async def get_template_catalog(scene_code: Optional[str] = None):
    """获取模板目录"""
    try:
        template_loader = get_template_loader()
        catalog = template_loader.get_template_catalog(scene_code)
        
        return {
            "status": "success",
            "catalog": catalog
        }
    except Exception as e:
        logger.error(f"获取模板目录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模板目录失败: {str(e)}")


@router.get("/scenes")
async def get_all_scenes():
    """获取所有场景"""
    try:
        template_loader = get_template_loader()
        scenes = template_loader.get_all_scenes()
        
        return {
            "status": "success",
            "scenes": scenes
        }
    except Exception as e:
        logger.error(f"获取场景列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景列表失败: {str(e)}")


@router.get("/scenes/{scene_code}")
async def get_scene_detail(scene_code: str):
    """获取场景详情"""
    try:
        template_loader = get_template_loader()
        scene = template_loader.get_scene(scene_code)
        templates = template_loader.get_scene_templates(scene_code)
        
        if not scene:
            raise HTTPException(status_code=404, detail=f"场景 {scene_code} 不存在")
        
        return {
            "status": "success",
            "scene": scene,
            "templates": [
                {
                    "id": t.template_id,
                    "name": t.name,
                    "description": t.description
                }
                for t in templates
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取场景详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景详情失败: {str(e)}")


@router.get("/templates/{template_id}")
async def get_template_detail(template_id: str):
    """获取模板详情"""
    try:
        template_loader = get_template_loader()
        template = template_loader.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        
        return {
            "status": "success",
            "template": {
                "id": template.template_id,
                "name": template.name,
                "description": template.description,
                "sql_template": template.sql_template,
                "params_schema": template.params_schema,
                "user_prompt": template.user_prompt,
                "important_notes": template.important_notes,
                "examples": template.examples
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模板详情失败: {str(e)}")


@router.post("/analyze")
async def analyze_intent(request: Dict[str, Any]):
    """分析用户意图(匹配Template)"""
    try:
        user_query = request.get("query")
        scene_code = request.get("scene_code")
        context = request.get("context", {})
        
        if not user_query:
            raise HTTPException(status_code=400, detail="缺少query参数")
        
        # 初始化组件（使用SceneTemplateLoader）
        template_loader = get_template_loader()
        llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout,
            thinking_disabled=chatbi_config.llm_thinking_disabled
        )
        
        intent_analyzer = IntentAnalyzer(llm_client, template_loader)
        
        # 分析意图
        result = await intent_analyzer.analyze(user_query, scene_code, context)
        
        return {
            "status": "success",
            "result": {
                "intent_type": result.intent_type,
                "matched_template": result.matched_template,
                "template_name": result.template_config.name if result.template_config else None,
                "template_description": result.template_config.description if result.template_config else None,
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
    """根据Template和参数构建SQL"""
    try:
        template_id = request.get("template_id") or request.get("pattern_id")
        params = request.get("params", {})
        context = request.get("context", {})
        
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id或pattern_id参数")
        
        # 初始化组件（使用SceneTemplateLoader）
        template_loader = get_template_loader()
        from ..core.sql_builder import PatternSQLBuilder
        sql_builder = PatternSQLBuilder(template_loader)
        
        # 构建SQL
        sql, error = sql_builder.build(template_id, params, context)
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            "status": "success",
            "template_id": template_id,
            "sql": sql,
            "params": params
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL构建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SQL构建失败: {str(e)}")


@router.get("/scene/{scene_code}/templates")
async def get_scene_templates(scene_code: str):
    """获取场景支持的Templates"""
    try:
        template_loader = get_template_loader()
        templates = template_loader.get_scene_templates(scene_code)
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "supported_templates": [
                {
                    "id": t.template_id,
                    "name": t.name,
                    "description": t.description
                }
                for t in templates
            ]
        }
    except Exception as e:
        logger.error(f"获取场景支持的Templates失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景支持的Templates失败: {str(e)}")


@router.get("/hot-questions")
async def get_hot_questions(scene_code: Optional[str] = None):
    """获取热门问题(按场景)"""
    logger.info(f"[GET /api/patterns/hot-questions] scene_code={scene_code}")
    try:
        template_loader = get_template_loader()
        
        # 获取场景的模板
        hot_questions = []
        if scene_code:
            templates = template_loader.get_scene_templates(scene_code)
        else:
            templates = list(template_loader.get_all_templates().values())
        
        # 为每个模板生成示例问题
        for template in templates[:5]:  # 限制返回前5个模板
            if template.examples:
                for example in template.examples[:1]:  # 每个模板最多1个示例
                    hot_questions.append({
                        "template_id": template.template_id,
                        "template_name": template.name,
                        "question": example,
                        "default_params": {}
                    })
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "hot_questions": hot_questions,
            "total": len(hot_questions)
        }
    except Exception as e:
        logger.error(f"获取热门问题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取热门问题失败: {str(e)}")
