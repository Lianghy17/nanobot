"""沙箱管理器 - 管理会话级别的本地沙箱"""
import asyncio
import logging
import uuid
import os
import subprocess
import sys
import tempfile
import shutil
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from ..config import chatbi_config

logger = logging.getLogger(__name__)


class LocalSandbox:
    """本地进程沙箱（最小开销方案）"""

    def __init__(self, sandbox_id: str, conversation_id: str):
        self.sandbox_id = sandbox_id
        self.conversation_id = conversation_id
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.temp_dir = None
        self.env = None

    async def init(self):
        """初始化沙箱环境"""
        # 创建独立的临时工作目录
        self.temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{self.conversation_id}_")

        # 设置隔离的环境变量
        self.env = {
            'PATH': os.environ.get('PATH', ''),
            'PYTHONPATH': self.temp_dir,  # 仅限临时目录
            'HOME': self.temp_dir,  # 家目录指向临时目录
            'TMPDIR': self.temp_dir,
            # 限制系统环境
            'USER': 'sandbox_user',
        }

        # 创建必要的目录结构
        os.makedirs(os.path.join(self.temp_dir, 'workspace'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'tmp'), exist_ok=True)

        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
        logger.info(f"{sandbox_info} 初始化沙箱")

    async def write_file(self, filename: str, content: str):
        """写入文件到沙箱"""
        if not self.temp_dir:
            raise RuntimeError("沙箱未初始化")

        file_path = os.path.join(self.temp_dir, 'workspace', filename)
        # 确保父目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
        logger.debug(f"{sandbox_info} 写入文件: {filename}")

    async def read_file(self, filename: str, limit: int = 100) -> tuple[bool, str, str]:
        """
        从沙箱读取文件

        Args:
            filename: 文件名（相对于workspace目录）
            limit: 读取行数限制

        Returns:
            (success, content, error_message)
        """
        if not self.temp_dir:
            return False, "", "沙箱未初始化"

        file_path = os.path.join(self.temp_dir, 'workspace', filename)

        if not os.path.exists(file_path):
            return False, "", f"文件不存在: {filename}"

        if not os.path.isfile(file_path):
            return False, "", f"路径不是文件: {filename}"

        try:
            lines = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    lines.append(line.rstrip('\n'))

            content = '\n'.join(lines)
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.debug(f"{sandbox_info} 读取文件成功: {filename} ({len(lines)} 行)")
            return True, content, ""

        except Exception as e:
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.error(f"{sandbox_info} 读取文件失败: {filename}, error={e}")
            return False, "", f"读取文件失败: {str(e)}"

    async def list_files(self) -> list:
        """
        列出沙箱中的所有文件

        Returns:
            文件列表，每个文件包含 filename, size, type
        """
        if not self.temp_dir:
            return []

        files = []
        workspace_dir = os.path.join(self.temp_dir, 'workspace')

        if not os.path.exists(workspace_dir):
            return files

        # 支持的文件扩展名
        supported_extensions = {
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }

        for root, dirs, filenames in os.walk(workspace_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()

                    if ext in supported_extensions:
                        # 计算相对路径
                        rel_path = os.path.relpath(file_path, workspace_dir)

                        files.append({
                            'filename': rel_path.replace('\\', '/'),  # 统一使用正斜杠
                            'size': os.path.getsize(file_path),
                            'type': ext.replace('.', ''),
                            'full_path': file_path
                        })

        return files

    async def upload_file(self, filename: str, content: bytes) -> tuple[bool, str, str]:
        """
        上传文件到沙箱

        Args:
            filename: 文件名
            content: 文件内容（二进制）

        Returns:
            (success, relative_path, error_message)
        """
        if not self.temp_dir:
            return False, "", "沙箱未初始化"

        try:
            file_path = os.path.join(self.temp_dir, 'workspace', filename)
            # 确保父目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(content)

            # 返回相对路径
            rel_path = filename.replace('\\', '/')
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.info(f"{sandbox_info} 上传文件成功: {filename} ({len(content)} 字节)")
            return True, rel_path, ""

        except Exception as e:
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.error(f"{sandbox_info} 上传文件失败: {filename}, error={e}")
            return False, "", f"上传文件失败: {str(e)}"

    async def get_file(self, filename: str) -> tuple[bool, bytes, str]:
        """
        从沙箱获取文件内容（二进制）

        Args:
            filename: 文件名

        Returns:
            (success, content, error_message)
        """
        if not self.temp_dir:
            return False, b"", "沙箱未初始化"

        file_path = os.path.join(self.temp_dir, 'workspace', filename)

        if not os.path.exists(file_path):
            return False, b"", f"文件不存在: {filename}"

        if not os.path.isfile(file_path):
            return False, b"", f"路径不是文件: {filename}"

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.debug(f"{sandbox_info} 获取文件成功: {filename} ({len(content)} 字节)")
            return True, content, ""

        except Exception as e:
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.error(f"{sandbox_info} 获取文件失败: {filename}, error={e}")
            return False, b"", f"获取文件失败: {str(e)}"

    async def execute_code(self, code: str, timeout: int = 60) -> dict:
        """执行代码"""
        self.last_used = datetime.now()

        # 写入代码文件
        filename = 'analysis.py'
        await self.write_file(filename, code)

        # 执行代码
        code_path = os.path.join(self.temp_dir, 'workspace', filename)

        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"

        try:
            # 使用 subprocess 执行，添加资源限制
            if sys.platform != 'win32':
                # Unix 系统：设置资源限制
                result = subprocess.run(
                    [sys.executable, '-u', code_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=os.path.join(self.temp_dir, 'workspace'),
                    env=self.env,
                    preexec_fn=self._limit_resources
                )
            else:
                # Windows 系统：无法设置资源限制
                result = subprocess.run(
                    [sys.executable, '-u', code_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=os.path.join(self.temp_dir, 'workspace'),
                    env=self.env
                )

            success = result.returncode == 0
            output = result.stdout if result.stdout else ""

            # 收集生成的文件
            generated_files = self._collect_generated_files()

            return {
                "success": success,
                "output": output,
                "error": result.stderr if result.stderr else None,
                "exit_code": result.returncode,
                "files": generated_files
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"{sandbox_info} 执行超时（{timeout}秒）")
            return {
                "success": False,
                "output": "",
                "error": f"执行超时（{timeout}秒）",
                "exit_code": -1,
                "files": []
            }
        except Exception as e:
            logger.error(f"{sandbox_info} 执行失败: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": f"执行失败: {str(e)}",
                "exit_code": -1,
                "files": []
            }

    def _collect_generated_files(self) -> list:
        """收集生成的文件（图片、CSV、Excel等）"""
        if not self.temp_dir:
            return []

        generated_files = []
        workspace_dir = os.path.join(self.temp_dir, 'workspace')

        # 支持的文件扩展名
        supported_extensions = {
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
        }

        if not os.path.exists(workspace_dir):
            return generated_files

        # 遍历工作目录，收集生成的文件
        for filename in os.listdir(workspace_dir):
            if filename == 'analysis.py':
                continue  # 跳过代码文件

            file_path = os.path.join(workspace_dir, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()

                if ext in supported_extensions:
                    # 读取文件内容（小文件）
                    file_size = os.path.getsize(file_path)
                    content = None

                    if file_size < 10 * 1024 * 1024:  # 小于10MB
                        with open(file_path, 'rb') as f:
                            content = f.read()

                    generated_files.append({
                        'filename': filename,
                        'type': supported_extensions[ext],
                        'size': file_size,
                        'content': content  # base64编码会在API层处理
                    })

        return generated_files

    def _limit_resources(self):
        """设置资源限制（仅在 Unix 系统有效）"""
        import resource

        try:
            # 限制内存为 512MB
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            # 限制 CPU 时间
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
            # 限制打开文件数
            resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))
            # 限制进程数
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
        except (ValueError, resource.error) as e:
            logger.debug(f"无法设置资源限制: {e}")

    async def close(self):
        """关闭沙箱"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                # 清理临时目录
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
                logger.info(f"{sandbox_info} 关闭沙箱, 清理目录")
        except Exception as e:
            sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
            logger.error(f"{sandbox_info} 关闭沙箱失败, error={e}")


class SandboxSession:
    """沙箱会话封装"""

    def __init__(self, sandbox: LocalSandbox, conversation_id: str, last_used: datetime):
        self.sandbox = sandbox
        self.conversation_id = conversation_id
        self.last_used = last_used
        self.created_at = datetime.now()

    async def execute_code(self, code: str, timeout: int = 60) -> dict:
        """执行代码"""
        self.last_used = datetime.now()
        return await self.sandbox.execute_code(code, timeout)

    async def close(self):
        """关闭沙箱"""
        await self.sandbox.close()


class SandboxManager:
    """沙箱管理器 - 单例模式"""

    _instance: Optional["SandboxManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # 会话ID -> SandboxSession
        self._sandboxes: Dict[str, SandboxSession] = {}

        # 配置
        self._timeout_minutes = 20  # 20分钟超时
        self._cleanup_interval = 60  # 60秒清理一次
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动沙箱管理器"""
        if self._running:
            logger.warning("沙箱管理器已在运行")
            return

        self._running = True
        logger.info("本地沙箱管理器已启动（使用最小开销的进程隔离方案）")

        # 启动定时清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """停止沙箱管理器"""
        if not self._running:
            return

        self._running = False

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有沙箱
        await self.close_all()

        logger.info("本地沙箱管理器已停止")

    async def get_sandbox(self, conversation_id: str) -> Optional[SandboxSession]:
        """
        获取或创建会话的专属沙箱

        Args:
            conversation_id: 会话ID

        Returns:
            SandboxSession 实例
        """
        # 如果已存在，更新使用时间
        if conversation_id in self._sandboxes:
            self._sandboxes[conversation_id].last_used = datetime.now()
            session = self._sandboxes[conversation_id]
            sandbox_info = f"[沙箱: {session.sandbox.sandbox_id}|workspace: {session.sandbox.temp_dir}/workspace|会话: {conversation_id}]"
            logger.debug(f"{sandbox_info} 复用沙箱")
            return self._sandboxes[conversation_id]

        # 创建新沙箱
        try:
            sandbox_id = f"sbx_{uuid.uuid4().hex[:8]}"
            local_sandbox = LocalSandbox(sandbox_id, conversation_id)
            await local_sandbox.init()

            session = SandboxSession(
                sandbox=local_sandbox,
                conversation_id=conversation_id,
                last_used=datetime.now()
            )

            self._sandboxes[conversation_id] = session
            sandbox_info = f"[沙箱: {sandbox_id}|workspace: {local_sandbox.temp_dir}/workspace|会话: {conversation_id}]"
            logger.info(f"{sandbox_info} 创建新沙箱, 当前活跃沙箱数: {len(self._sandboxes)}")

            return session

        except Exception as e:
            logger.error(f"[沙箱: 无|workspace: 无|会话: {conversation_id}] 创建沙箱失败, error={e}")
            return None

    async def close_sandbox(self, conversation_id: str):
        """关闭指定会话的沙箱"""
        if conversation_id not in self._sandboxes:
            return

        session = self._sandboxes.pop(conversation_id)
        sandbox_info = f"[沙箱: {session.sandbox.sandbox_id}|workspace: {session.sandbox.temp_dir}/workspace|会话: {conversation_id}]"
        await session.close()
        logger.info(f"{sandbox_info} 主动关闭沙箱, 剩余沙箱数: {len(self._sandboxes)}")

    async def close_all(self):
        """关闭所有沙箱"""
        for conversation_id, session in list(self._sandboxes.items()):
            await session.close()

        self._sandboxes.clear()
        logger.info("已关闭所有沙箱")

    async def _cleanup_loop(self):
        """定时清理超时沙箱"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务异常: {e}")

    async def _cleanup_expired(self):
        """清理超时的沙箱"""
        if not self._sandboxes:
            return

        now = datetime.now()
        timeout_threshold = timedelta(minutes=self._timeout_minutes)

        expired = []
        for conversation_id, session in self._sandboxes.items():
            if now - session.last_used > timeout_threshold:
                expired.append(conversation_id)

        if expired:
            logger.info(f"发现 {len(expired)} 个超时沙箱: {expired}")

            for conversation_id in expired:
                await self.close_sandbox(conversation_id)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_sandboxes": len(self._sandboxes),
            "timeout_minutes": self._timeout_minutes,
            "cleanup_interval": self._cleanup_interval,
            "running": self._running,
            "sandbox_type": "local_process"
        }

    def list_sandboxes(self) -> list:
        """列出所有活跃沙箱"""
        return [
            {
                "conversation_id": conv_id,
                "sandbox_id": session.sandbox.sandbox_id,
                "last_used": session.last_used.isoformat(),
                "created_at": session.created_at.isoformat(),
                "idle_minutes": (datetime.now() - session.last_used).total_seconds() / 60
            }
            for conv_id, session in self._sandboxes.items()
        ]
