"""文件API - 提供文件下载和访问（从沙箱中）"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Optional

from ..core.sandbox_manager import SandboxManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/download/{user_channel}/{conversation_id}/{filename}")
async def download_file(
    user_channel: str,
    conversation_id: str,
    filename: str
):
    """从沙箱下载文件"""
    try:
        # 获取沙箱管理器
        sandbox_manager = SandboxManager()
        session = await sandbox_manager.get_sandbox(conversation_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"沙箱不存在或已过期: {conversation_id}")

        # 从沙箱获取文件
        success, content, error_msg = await session.sandbox.get_file(filename)

        if not success:
            raise HTTPException(status_code=404, detail=error_msg or f"文件不存在: {filename}")

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

        ext = Path(filename).suffix.lower()
        media_type = mime_types.get(ext, 'application/octet-stream')

        # 返回文件内容
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
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
    """列出沙箱中的所有文件"""
    try:
        # 获取沙箱管理器
        sandbox_manager = SandboxManager()
        session = await sandbox_manager.get_sandbox(conversation_id)

        if not session:
            # 沙箱不存在或已过期，返回空列表
            return {
                "success": True,
                "files": [],
                "count": 0,
                "message": "沙箱不存在或已过期"
            }

        # 从沙箱获取文件列表
        files = await session.sandbox.list_files()

        # 如果指定了文件类型，进行过滤
        if file_type:
            files = [f for f in files if f['type'] == file_type]

        # 添加下载URL
        for file_info in files:
            file_info["download_url"] = f"/api/files/download/{user_channel}/{conversation_id}/{file_info['filename']}"

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
