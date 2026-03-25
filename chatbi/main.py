"""ChatBI主应用"""
import time
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# 在导入配置前设置环境变量（调试模式：1个worker）
os.environ["LOOP_WORKERS"] = "1"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# 确保可以导入父包的模块（支持直接运行）
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi.config import settings
from chatbi.api import conversations_router, messages_router, scenes_router, files_router, sse_router, patterns_router, qa_templates_router
from chatbi.core.loop_queue import LoopQueue
from chatbi.core.message_processor import MessageProcessor
from chatbi.core.sandbox_manager import SandboxManager


# 配置日志
def setup_logger():
    """配置logging日志系统"""
    # 确保日志目录存在
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器 - INFO级别
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除所有现有的handler
    root_logger.handlers.clear()

    # 设置 uvicorn 和 fastapi 的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # 创建控制台输出handler（使用 stderr 避免 uvicorn 干扰）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 创建文件输出handler
    file_handler = logging.FileHandler(
        str(logs_dir / "chatbi.log"),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # 测试终端输出
    import os
    pid = os.getpid()
    print(f"\n{'='*80}")
    print(f"[终端输出测试] 进程ID: {pid}")
    print(f"[终端输出测试] 日志系统已配置，级别: INFO")
    print(f"[终端输出测试] 日志目录: {logs_dir}")
    print(f"{'='*80}\n")

    logging.info(f"[PID:{pid}] 日志系统已配置，级别: INFO")
    logging.info(f"[PID:{pid}] 日志目录: {logs_dir}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ChatBI - 对话式数据分析平台"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])
app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
app.include_router(scenes_router, prefix="/api/scenes", tags=["scenes"])
app.include_router(files_router, tags=["files"])
app.include_router(sse_router, prefix="/api/sse", tags=["sse"])
app.include_router(patterns_router, prefix="/api/patterns", tags=["patterns"])
app.include_router(qa_templates_router, prefix="/api/qa", tags=["qa"])

# 挂载静态文件服务（前端文件）
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")

# 挂载workspace/files静态文件服务
files_path = Path(__file__).parent.parent / "workspace" / "files"
if files_path.exists():
    app.mount("/files", StaticFiles(directory=str(files_path)), name="files")
    logging.info(f"静态文件服务已挂载: /files -> {files_path}")
else:
    logging.warning(f"workspace/files目录不存在: {files_path}")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"全局异常: {exc}")
    return {
        "success": False,
        "error": str(exc)
    }


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logging.info(f"{settings.app_name} v{settings.app_version} 启动中...")

    # 初始化Loop队列
    loop_queue = LoopQueue.get_instance()
    message_processor = MessageProcessor()
    loop_queue.set_processor(message_processor)
    await loop_queue.start(num_workers=settings.loop_workers)

    # 启动沙箱管理器
    sandbox_manager = SandboxManager()
    await sandbox_manager.start()
    logging.info("沙箱管理器已启动")

    logging.info(f"{settings.app_name} 启动完成")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logging.info(f"{settings.app_name} 正在关闭...")

    # 停止Loop队列
    loop_queue = LoopQueue.get_instance()
    await loop_queue.stop()

    # 停止沙箱管理器
    sandbox_manager = SandboxManager()
    await sandbox_manager.stop()
    logging.info("沙箱管理器已停止")

    logging.info(f"{settings.app_name} 已关闭")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    loop_queue = LoopQueue.get_instance()
    sandbox_manager = SandboxManager()
    sandbox_stats = sandbox_manager.get_stats()

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "queue_size": loop_queue.size(),
        "sandboxes": sandbox_stats
    }


# 沙箱管理端点
@app.get("/api/sandboxes/stats")
async def sandbox_stats():
    """沙箱统计信息"""
    sandbox_manager = SandboxManager()
    return sandbox_manager.get_stats()


@app.get("/api/sandboxes/list")
async def sandbox_list():
    """列出所有活跃沙箱"""
    sandbox_manager = SandboxManager()
    return sandbox_manager.list_sandboxes()


# 首页
@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    try:
        # 尝试读取前端HTML文件
        frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
        if frontend_path.exists():
            return FileResponse(str(frontend_path))
        
        # 如果不存在，返回简单的欢迎页面
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.app_name}</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Welcome to {settings.app_name} v{settings.app_version}</h1>
            <p>对话式数据分析平台</p>
            <p>API文档: <a href="/docs">Swagger UI</a></p>
        </body>
        </html>
        """)
    except Exception as e:
        logging.error(f"返回首页失败: {e}")
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>")


if __name__ == "__main__":
    import uvicorn

    # 在运行前配置日志
    setup_logger()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        workers=1,  # 强制单worker模式（调试必需）
        reload=settings.debug,
        log_level="info",  # 使用info级别
        access_log=True   # 启用访问日志
    )
