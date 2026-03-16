"""文件API"""
import uuid
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = "web_default_user"
):
    """上传文件"""
    try:
        # 验证文件大小
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制（最大{settings.max_file_size / 1024 / 1024}MB）"
            )
        
        # 生成文件路径
        user_channel = f"web_{user_id}"
        user_dir = Path(settings.upload_path) / user_channel
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix
        unique_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = user_dir / unique_name
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"文件上传成功: {file.filename} -> {file_path} ({len(content)} bytes)")
        
        return {
            "success": True,
            "file_path": unique_name,
            "original_name": file.filename,
            "file_size": len(content),
            "upload_time": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail="文件上传失败")


@router.get("/")
async def list_files(
    user_id: str = "web_default_user"
):
    """获取用户文件列表"""
    try:
        user_channel = f"web_{user_id}"
        user_dir = Path(settings.upload_path) / user_channel
        
        if not user_dir.exists():
            return {"files": []}
        
        files = []
        for file_path in user_dir.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "file_path": file_path.name,
                    "file_size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # 按修改时间倒序
        files.sort(key=lambda x: x["modified_at"], reverse=True)
        
        return {"files": files}
    
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取文件列表失败")


@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    user_id: str = "web_default_user"
):
    """删除文件"""
    try:
        user_channel = f"web_{user_id}"
        full_path = Path(settings.upload_path) / user_channel / file_path
        
        # 安全检查
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查是否在用户目录内
        user_dir = Path(settings.upload_path) / user_channel
        try:
            full_path.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="拒绝访问")
        
        # 删除文件
        full_path.unlink()
        
        logger.info(f"文件删除成功: {file_path}")
        return {"success": True, "message": "文件已删除"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail="删除文件失败")
