"""QA模板API路由"""
import logging
import json
from fastapi import APIRouter, HTTPException
from typing import Optional
import os

from ..config import chatbi_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/templates/{scene_code}")
async def get_qa_templates(scene_code: str):
    """获取场景的QA模板"""
    try:
        # 构建模板文件路径
        template_path = os.path.join(
            chatbi_config.config_dir,
            "QA模板库",
            scene_code,
            "templates.json"
        )
        
        logger.info(f"[GET /api/qa/templates/{scene_code}] template_path={template_path}")
        
        # 检查文件是否存在
        if not os.path.exists(template_path):
            logger.warning(f"QA模板文件不存在: {template_path}")
            return {
                "status": "success",
                "scene_code": scene_code,
                "templates": [],
                "categories": {}
            }
        
        # 读取模板文件
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "templates": template_data.get("templates", []),
            "categories": template_data.get("categories", {})
        }
    except Exception as e:
        logger.error(f"获取QA模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取QA模板失败: {str(e)}")


@router.get("/templates/{scene_code}/{template_id}")
async def get_qa_template_detail(scene_code: str, template_id: str):
    """获取QA模板详情"""
    try:
        # 构建模板文件路径
        template_path = os.path.join(
            chatbi_config.config_dir,
            "QA模板库",
            scene_code,
            "templates.json"
        )
        
        logger.info(f"[GET /api/qa/templates/{scene_code}/{template_id}]")
        
        # 检查文件是否存在
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail=f"场景 {scene_code} 的模板文件不存在")
        
        # 读取模板文件
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # 查找指定模板
        templates = template_data.get("templates", [])
        template = next((t for t in templates if t.get("id") == template_id), None)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "template": template
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取QA模板详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取QA模板详情失败: {str(e)}")


@router.get("/schema/{scene_code}")
async def get_scene_schema(scene_code: str):
    """获取场景的表结构"""
    try:
        # 构建schema文件路径
        schema_path = os.path.join(
            chatbi_config.config_dir,
            "表schema",
            scene_code,
            f"{scene_code}_schema.json"
        )
        
        logger.info(f"[GET /api/qa/schema/{scene_code}] schema_path={schema_path}")
        
        # 检查文件是否存在
        if not os.path.exists(schema_path):
            logger.warning(f"Schema文件不存在: {schema_path}")
            return {
                "status": "success",
                "scene_code": scene_code,
                "tables": [],
                "relationships": []
            }
        
        # 读取schema文件
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_data = json.load(f)
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "tables": schema_data.get("tables", []),
            "relationships": schema_data.get("relationships", [])
        }
    except Exception as e:
        logger.error(f"获取场景Schema失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景Schema失败: {str(e)}")


@router.get("/knowledge/{scene_code}")
async def get_scene_knowledge(scene_code: str):
    """获取场景的知识库"""
    try:
        # 构建知识库路径
        knowledge_dir = os.path.join(
            chatbi_config.config_dir,
            "知识库",
            scene_code
        )
        
        logger.info(f"[GET /api/qa/knowledge/{scene_code}] knowledge_dir={knowledge_dir}")
        
        # 检查目录是否存在
        if not os.path.exists(knowledge_dir):
            logger.warning(f"知识库目录不存在: {knowledge_dir}")
            return {
                "status": "success",
                "scene_code": scene_code,
                "files": []
            }
        
        # 列出知识库文件
        files = []
        for filename in os.listdir(knowledge_dir):
            if filename.endswith('.md'):
                file_path = os.path.join(knowledge_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files.append({
                    "filename": filename,
                    "title": content.split('\n')[0].replace('#', '').strip(),
                    "content": content
                })
        
        return {
            "status": "success",
            "scene_code": scene_code,
            "files": files
        }
    except Exception as e:
        logger.error(f"获取场景知识库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取场景知识库失败: {str(e)}")
