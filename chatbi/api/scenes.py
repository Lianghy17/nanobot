"""场景API"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Dict

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/")
async def get_scenes():
    """获取所有场景列表"""
    try:
        config_path = Path("/config/scenes.json")
        if not config_path.exists():
            # 使用相对路径
            config_path = Path(__file__).parent.parent.parent / "config" / "scenes.json"
        
        if not config_path.exists():
            logger.warning(f"场景配置文件不存在: {config_path}")
            return {"scenes": []}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {"scenes": data.get("scenes", [])}
    
    except Exception as e:
        logger.error(f"获取场景列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取场景列表失败")


@router.get("/{scene_code}")
async def get_scene(scene_code: str):
    """获取指定场景的详细信息"""
    try:
        config_path = Path("/config/scenes.json")
        if not config_path.exists():
            config_path = Path(__file__).parent.parent.parent / "config" / "scenes.json"
        
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="场景配置文件不存在")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for scene in data.get("scenes", []):
            if scene.get("scene_code") == scene_code:
                return scene
        
        raise HTTPException(status_code=404, detail=f"场景不存在: {scene_code}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取场景详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取场景详情失败")
