"""独立图片服务器

功能：
- 接收图片上传（从 ChatBI）
- 生成唯一 URL
- 提供图片访问服务

启动方式：
    python -m chatbi.services.image_server

默认端口：8081
"""
import os
import sys
import uuid
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 配置
IMAGE_SERVER_HOST = os.getenv("IMAGE_SERVER_HOST", "localhost")
IMAGE_SERVER_PORT = int(os.getenv("IMAGE_SERVER_PORT", "8081"))
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "workspace/images"))

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="Image Server", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保图片目录存在
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def startup():
    logger.info(f"图片服务器启动: http://{IMAGE_SERVER_HOST}:{IMAGE_SERVER_PORT}")
    logger.info(f"图片存储目录: {IMAGE_DIR.absolute()}")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "image_server"}


@app.post("/upload")
async def upload_image(
    file: Optional[UploadFile] = File(None),
    base64_data: Optional[str] = None,
    filename: Optional[str] = None,
    conversation_id: Optional[str] = None
):
    """
    上传图片
    
    支持两种方式：
    1. 文件上传：multipart/form-data
    2. base64 上传：JSON body
    
    返回：
    - image_id: 图片唯一 ID
    - url: 可访问的 URL
    """
    try:
        image_id = f"img_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 检查是否有有效的文件上传（file 不为 None 且有内容）
        if file is not None and hasattr(file, 'filename') and file.filename:
            # 文件上传方式
            ext = Path(file.filename).suffix or '.png'
            stored_filename = f"{image_id}_{timestamp}{ext}"
            stored_path = IMAGE_DIR / stored_filename
            
            content = await file.read()
            stored_path.write_bytes(content)
            
            original_filename = file.filename
            size = len(content)
            
        elif base64_data:
            # base64 上传方式
            # 处理 data URL 格式
            if base64_data.startswith('data:'):
                header, base64_part = base64_data.split(',', 1)
                # 从 header 中提取 MIME 类型
                mime = header.split(':')[1].split(';')[0]
                ext_map = {
                    'image/png': '.png',
                    'image/jpeg': '.jpg',
                    'image/gif': '.gif',
                    'image/svg+xml': '.svg',
                }
                ext = ext_map.get(mime, '.png')
            else:
                base64_part = base64_data
                ext = '.png'
            
            stored_filename = f"{image_id}_{timestamp}{ext}"
            stored_path = IMAGE_DIR / stored_filename
            
            content = base64.b64decode(base64_part)
            stored_path.write_bytes(content)
            
            original_filename = filename or f"image{ext}"
            size = len(content)
            
        else:
            raise HTTPException(status_code=400, detail="需要提供 file 或 base64_data")
        
        # 生成 URL
        url = f"http://{IMAGE_SERVER_HOST}:{IMAGE_SERVER_PORT}/images/{stored_filename}"
        
        # 保存元数据
        metadata = {
            "image_id": image_id,
            "stored_filename": stored_filename,
            "original_filename": original_filename,
            "size": size,
            "url": url,
            "conversation_id": conversation_id,
            "created_at": datetime.now().isoformat()
        }
        metadata_path = IMAGE_DIR / f"{stored_filename}.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        
        logger.info(f"图片上传成功: {original_filename} -> {stored_filename}, size={size}")
        
        return {
            "success": True,
            "image_id": image_id,
            "filename": stored_filename,
            "original_filename": original_filename,
            "url": url,
            "size": size
        }
        
    except Exception as e:
        logger.error(f"上传图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/base64")
async def upload_base64(data: dict):
    """
    base64 上传接口（JSON body）
    
    Body:
    {
        "base64": "data:image/png;base64,...",
        "filename": "chart.png",
        "conversation_id": "conv_xxx"
    }
    """
    base64_data = data.get("base64")
    filename = data.get("filename")
    conversation_id = data.get("conversation_id")
    
    if not base64_data:
        raise HTTPException(status_code=400, detail="需要提供 base64 数据")
    
    return await upload_image(
        base64_data=base64_data,
        filename=filename,
        conversation_id=conversation_id
    )


@app.get("/images/{filename}")
async def get_image(filename: str):
    """获取图片"""
    file_path = IMAGE_DIR / filename
    
    if not file_path.exists():
        logger.warning(f"图片不存在: {filename}")
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 确定 MIME 类型
    ext = Path(filename).suffix.lower()
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
    }
    media_type = mime_map.get(ext, 'application/octet-stream')
    
    logger.debug(f"返回图片: {filename}")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@app.get("/images/{filename}/info")
async def get_image_info(filename: str):
    """获取图片信息"""
    metadata_path = IMAGE_DIR / f"{filename}.json"
    
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="图片信息不存在")
    
    return json.loads(metadata_path.read_text())


@app.delete("/images/{filename}")
async def delete_image(filename: str):
    """删除图片"""
    file_path = IMAGE_DIR / filename
    metadata_path = IMAGE_DIR / f"{filename}.json"
    
    deleted = False
    
    if file_path.exists():
        file_path.unlink()
        deleted = True
    
    if metadata_path.exists():
        metadata_path.unlink()
    
    if not deleted:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    logger.info(f"图片已删除: {filename}")
    
    return {"success": True, "message": "图片已删除"}


@app.get("/list")
async def list_images(conversation_id: Optional[str] = None, limit: int = 100):
    """列出图片"""
    images = []
    
    for f in IMAGE_DIR.glob("*.json"):
        if len(images) >= limit:
            break
        
        try:
            metadata = json.loads(f.read_text())
            if conversation_id and metadata.get("conversation_id") != conversation_id:
                continue
            images.append(metadata)
        except:
            pass
    
    # 按创建时间排序（最新的在前）
    images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "success": True,
        "count": len(images),
        "images": images
    }


def main():
    """启动服务器"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=IMAGE_SERVER_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
