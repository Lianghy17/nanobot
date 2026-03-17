"""文件API - 提供文件下载和访问"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/download/{user_channel}/{conversation_id}/{filename}")
async def download_file(
    user_channel: str,
    conversation_id: str,
    filename: str
):
    """下载会话中的文件"""
    try:
        # 构建文件路径
        file_path = Path(settings.sessions_path) / user_channel / conversation_id / filename

        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

        # 检查是否是文件（不是目录）
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="路径不是文件")

        # 根据文件扩展名确定 MIME 类型
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
        }

        ext = file_path.suffix.lower()
        media_type = mime_types.get(ext, 'application/octet-stream')

        # 返回文件
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {user_channel}/{conversation_id}/{filename}, error={e}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")


@router.get("/list/{user_channel}/{conversation_id}")
async def list_files(
    user_channel: str,
    conversation_id: str,
    file_type: Optional[str] = None
):
    """列出会话中的所有文件"""
    try:
        # 构建会话目录路径
        conversation_dir = Path(settings.sessions_path) / user_channel / conversation_id

        # 检查目录是否存在
        if not conversation_dir.exists():
            return {
                "success": True,
                "files": [],
                "count": 0
            }

        # 收集文件信息
        files = []
        for file_path in conversation_dir.iterdir():
            if file_path.is_file():
                # 如果指定了文件类型，进行过滤
                if file_type:
                    if file_path.suffix.lower().replace('.', '') != file_type:
                        continue

                file_info = {
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "type": file_path.suffix.lower().replace('.', ''),
                    "download_url": f"/api/files/download/{user_channel}/{conversation_id}/{file_path.name}"
                }
                files.append(file_info)

        # 按文件名排序
        files.sort(key=lambda x: x["filename"])

        return {
            "success": True,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        logger.error(f"列出文件失败: {user_channel}/{conversation_id}, error={e}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")
