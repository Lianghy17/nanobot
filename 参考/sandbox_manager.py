"""沙箱管理器 - 管理会话级别的本地沙箱"""
import asyncio
import logging
import uuid
import os
import subprocess
import sys
import tempfile
import shutil
import threading
import queue
import json
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from pathlib import Path
from ..config import chatbi_config

logger = logging.getLogger(__name__)


class PersistentPythonKernel:
    """
    持久化 Python 内核 - 使用 jupyter_client 保持会话状态
    
    特性：
    - 变量跨执行保持
    - 导入自动持久化
    - 自动注入常用库
    """
    
    # 自动注入的常用库
    AUTO_IMPORTS = """
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import warnings
warnings.filterwarnings('ignore')
print("✅ 常用库已导入: pd, np, plt")
"""
    
    def __init__(self, conversation_id: str, working_dir: str):
        self.conversation_id = conversation_id
        self.working_dir = working_dir
        self._kernel_manager = None
        self._kernel_client = None
        self._execution_count = 0
        self._created_at = datetime.now()
        
    def start(self):
        """启动持久化 Jupyter 内核"""
        try:
            from jupyter_client import KernelManager
            
            # 创建内核管理器
            self._kernel_manager = KernelManager(kernel_name='python3')
            self._kernel_manager.start_kernel(cwd=self.working_dir)
            
            # 获取内核客户端
            self._kernel_client = self._kernel_manager.client()
            self._kernel_client.start_channels()
            
            # 注入常用导入
            self._execute_silent(self.AUTO_IMPORTS)
            
            logger.info(f"[Kernel:{self.conversation_id}] 持久化内核已启动")
            
        except ImportError as e:
            logger.error(f"[Kernel:{self.conversation_id}] jupyter_client 未安装: {e}")
            raise RuntimeError("请安装 jupyter_client: pip install jupyter_client ipykernel")
        except Exception as e:
            logger.error(f"[Kernel:{self.conversation_id}] 启动内核失败: {e}")
            raise
    
    def _execute_silent(self, code: str) -> bool:
        """静默执行代码（不返回结果）"""
        try:
            self._kernel_client.execute(code, silent=True)
            # 等待执行完成
            while True:
                msg = self._kernel_client.get_shell_msg(timeout=5)
                if msg['content']['status'] == 'ok':
                    return True
                elif msg['content']['status'] == 'error':
                    logger.warning(f"[Kernel:{self.conversation_id}] 静默执行失败: {msg['content'].get('evalue')}")
                    return False
        except Exception as e:
            logger.error(f"[Kernel:{self.conversation_id}] 静默执行异常: {e}")
            return False
    
    def execute(self, code: str, timeout: int = 60) -> dict:
        """
        执行代码并返回结果
        
        Returns:
            {
                'success': bool,
                'output': str,
                'error': str or None,
                'execution_count': int,
                'variables': dict
            }
        """
        if not self._kernel_client:
            logger.warning(f"[Kernel:{self.conversation_id}] 内核未启动，重新启动")
            self.start()
            
        self._execution_count += 1
        exec_id = self._execution_count
        
        try:
            # 执行代码
            self._kernel_client.execute(code)
            
            # 收集输出
            output_lines = []
            error_msg = None
            start_time = datetime.now()
            outputs = []
            
            while True:
                # 检查超时
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    logger.warning(f"[Kernel:{self.conversation_id}] 执行超时({timeout}s)，重启内核")
                    self.restart()
                    return {
                        'success': False,
                        'output': '',
                        'error': f'执行超时（{timeout}秒），内核已重启',
                        'execution_count': exec_id,
                        'variables': {}
                    }
                
                # 获取 IOPub 消息（输出）
                try:
                    msg = self._kernel_client.get_iopub_msg(timeout=0.1)
                except Exception:
                    continue
                
                msg_type = msg['header']['msg_type']
                
                # 执行完成
                if msg_type == 'status' and msg['content']['execution_state'] == 'idle':
                    break
                    
                # 执行错误
                if msg_type == 'error':
                    error_data = msg['content']
                    error_msg = '\n'.join(error_data.get('traceback', error_data.get('evalue', '')))
                    logger.warning(f"[Kernel:{self.conversation_id}] 执行错误: {error_msg[:200]}")
                    
                # 流式输出
                if msg_type == 'stream':
                    content = msg['content'].get('text', '')
                    output_lines.append(content)
                    
                # 输出结果（print/表达式的值）
                if msg_type == 'execute_result':
                    content = msg['content'].get('data', {}).get('text/plain', '')
                    output_lines.append(content)
                    
                # 显示数据（dataframe 等）
                if msg_type == 'display_data':
                    content = msg['content'].get('data', {})
                    if 'text/plain' in content:
                        output_lines.append(content['text/plain'])
            
            # 获取当前变量
            variables = self._get_variables()
            
            success = error_msg is None
            output = '\n'.join(output_lines)
            
            if success:
                logger.debug(f"[Kernel:{self.conversation_id}] 执行成功: exec_count={exec_id}, output_len={len(output)}")
            else:
                logger.warning(f"[Kernel:{self.conversation_id}] 执行失败: exec_count={exec_id}")
            
            return {
                'success': success,
                'output': output,
                'error': error_msg,
                'execution_count': exec_id,
                'variables': variables
            }
            
        except Exception as e:
            logger.error(f"[Kernel:{self.conversation_id}] 执行异常: {e}", exc_info=True)
            # 重启内核
            self.restart()
            return {
                'success': False,
                'output': '',
                'error': f'执行异常: {str(e)}',
                'execution_count': exec_id,
                'variables': {}
            }
    
    def _get_variables(self) -> dict:
        """获取当前内核中的变量列表（静默方式）"""
        try:
            # 使用 IPython 的内核命令获取变量
            code = """
# 静默获取变量列表
import sys
from IPython import get_ipython

if get_ipython() is None:
    # 非 IPython 环境
    variables = {}
else:
    # 使用 IPython 的 namespace 获取变量
    shell = get_ipython()
    user_ns = shell.user_ns
    variables = {}

    # 使用 list() 创建副本，避免迭代时修改字典导致的 RuntimeError
    for name, value in list(user_ns.items()):
        # 过滤 IPython 内置变量和特殊变量
        if name.startswith('_'):
            continue
        if name in ['In', 'Out', 'exit', 'quit', 'get_ipython', 'sys', 'json', 'shell', 'user_ns', 'variables']:
            continue

        try:
            var_type = type(value).__name__
            # 过滤掉一些不需要的类型
            if var_type in ['module', 'function', 'type', 'builtin_function_or_method']:
                continue
            variables[name] = var_type
        except:
            pass

variables
"""
            self._kernel_client.execute(code, silent=False)

            # 收集输出
            import json
            variable_json = None
            while True:
                try:
                    msg = self._kernel_client.get_iopub_msg(timeout=5)
                    msg_type = msg['header']['msg_type']
                    
                    if msg_type == 'execute_result':
                        # 获取表达式的返回值
                        content = msg['content'].get('data', {}).get('text/plain', '')
                        # 解析变量字典
                        try:
                            variables = eval(content)
                            return variables if isinstance(variables, dict) else {}
                        except:
                            pass
                    
                    if msg_type == 'status' and msg['content']['execution_state'] == 'idle':
                        break
                except Exception:
                    pass
                    
            return {}

        except Exception as e:
            logger.debug(f"[Kernel:{self.conversation_id}] 获取变量列表失败: {e}")
            return {}
    
    def restart(self):
        """重启内核"""
        self.close()
        self._execution_count = 0
        self.start()
        logger.info(f"[Kernel:{self.conversation_id}] 内核已重启")
    
    def close(self):
        """关闭内核"""
        try:
            if self._kernel_client:
                self._kernel_client.stop_channels()
                self._kernel_client = None
                
            if self._kernel_manager:
                self._kernel_manager.shutdown_kernel()
                self._kernel_manager = None
                
            logger.info(f"[Kernel:{self.conversation_id}] 内核已关闭")
            
        except Exception as e:
            logger.error(f"[Kernel:{self.conversation_id}] 关闭内核失败: {e}")
    
    def is_alive(self) -> bool:
        """检查内核是否存活"""
        if not self._kernel_manager:
            return False
        return self._kernel_manager.is_alive()


class LocalSandbox:
    """本地进程沙箱（使用持久化内核）"""

    def __init__(self, sandbox_id: str, conversation_id: str):
        self.sandbox_id = sandbox_id
        self.conversation_id = conversation_id
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.temp_dir = None
        self.env = None
        self._kernel: Optional[PersistentPythonKernel] = None  # 持久化内核
        self._copied_files = set()  # 已复制的文件集合（避免重复复制）

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
        workspace_dir = os.path.join(self.temp_dir, 'workspace')
        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'tmp'), exist_ok=True)

        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {workspace_dir}|会话: {self.conversation_id}]"
        logger.info(f"{sandbox_info} 初始化沙箱")

        # 启动持久化内核
        self._kernel = PersistentPythonKernel(self.conversation_id, workspace_dir)
        self._kernel.start()
        logger.info(f"{sandbox_info} 持久化内核已启动")

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
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
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
        """执行代码（使用持久化内核）"""
        self.last_used = datetime.now()

        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"

        # 检查内核是否存活
        if not self._kernel or not self._kernel.is_alive():
            logger.warning(f"{sandbox_info} 内核未启动，重新初始化")
            self._kernel = PersistentPythonKernel(self.conversation_id, os.path.join(self.temp_dir, 'workspace'))
            self._kernel.start()

        try:
            # 使用持久化内核执行代码
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._kernel.execute(code, timeout)
            )

            success = result['success']
            output = result['output'] or ""

            # 收集生成的文件
            generated_files = self._collect_generated_files()

            return {
                "success": success,
                "output": output,
                "error": result.get('error'),
                "exit_code": 0 if success else 1,
                "files": generated_files,
                "execution_count": result.get('execution_count', 0),
                "variables": result.get('variables', {})
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
        """收集生成的文件（图片、CSV、Excel等），并复制到workspace/files
        
        注意：只复制新生成的文件，避免重复复制原始数据文件
        """
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
            '.html': 'text/html',
            '.htm': 'text/html',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
        }

        if not os.path.exists(workspace_dir):
            return generated_files

        # 获取 workspace/files 目录路径
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        files_dir = project_root / "workspace" / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        files_dir = str(files_dir)
        
        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"

        # 遍历工作目录，收集生成的文件
        for filename in os.listdir(workspace_dir):
            if filename == 'analysis.py':
                continue  # 跳过代码文件

            file_path = os.path.join(workspace_dir, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()

                if ext in supported_extensions:
                    # 检查文件是否已复制过（避免重复复制原始数据文件）
                    if filename in self._copied_files:
                        logger.debug(f"{sandbox_info} 文件已复制过，跳过: {filename}")
                        continue
                    
                    # 读取文件内容（小文件）
                    file_size = os.path.getsize(file_path)
                    content = None

                    if file_size < 10 * 1024 * 1024:  # 小于10MB
                        with open(file_path, 'rb') as f:
                            content = f.read()

                    logger.info(f"{sandbox_info} 准备复制文件: {filename}, 目标目录: {files_dir}")

                    # 生成唯一的文件名（避免冲突）
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{self.conversation_id}_{timestamp}_{filename}"
                    target_path = os.path.join(files_dir, unique_filename)

                    # 复制文件
                    try:
                        with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
                            dst.write(src.read())

                        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
                        logger.info(f"{sandbox_info} 复制文件到workspace/files: {filename} -> {unique_filename}")

                        # 标记该文件已复制
                        self._copied_files.add(filename)

                        file_info = {
                            'filename': filename,  # 原始文件名
                            'unique_filename': unique_filename,  # 唯一文件名
                            'type': supported_extensions[ext],
                            'size': file_size,
                            'local_path': f'/files/{unique_filename}',  # 本地静态URL（备用）
                        }
                        
                        # 图片文件上传到图片服务器
                        if supported_extensions[ext].startswith('image/') and content:
                            logger.info(f"{sandbox_info} 检测到图片文件，准备上传到图片服务器...")
                            try:
                                from ..config import chatbi_config
                                logger.info(f"{sandbox_info} 图片服务器配置: enabled={chatbi_config.image_server_enabled}, url={chatbi_config.image_server_url}")
                                if chatbi_config.image_server_enabled:
                                    import httpx
                                    import base64
                                    
                                    # 上传到图片服务器
                                    base64_data = base64.b64encode(content).decode('utf-8')
                                    logger.info(f"{sandbox_info} 图片base64编码完成，大小: {len(base64_data)} 字符")
                                    
                                    with httpx.Client(timeout=chatbi_config.image_server_upload_timeout) as client:
                                        response = client.post(
                                            f"{chatbi_config.image_server_url}/upload/base64",
                                            json={
                                                "base64": f"data:{supported_extensions[ext]};base64,{base64_data}",
                                                "filename": filename,
                                                "conversation_id": self.conversation_id
                                            }
                                        )
                                        
                                        logger.info(f"{sandbox_info} 图片服务器响应: status={response.status_code}")
                                        
                                        if response.status_code == 200:
                                            result = response.json()
                                            file_info['url'] = result.get('url', file_info['local_path'])
                                            file_info['image_id'] = result.get('image_id')
                                            logger.info(f"{sandbox_info} 图片上传成功: {filename} -> {file_info['url']}")
                                        else:
                                            logger.warning(f"{sandbox_info} 图片上传失败: {response.text}")
                                            file_info['url'] = file_info['local_path']
                                else:
                                    logger.info(f"{sandbox_info} 图片服务器未启用，使用本地路径")
                                    file_info['url'] = file_info['local_path']
                            except Exception as e:
                                logger.warning(f"{sandbox_info} 图片上传异常: {e}", exc_info=True)
                                file_info['url'] = file_info['local_path']
                        else:
                            logger.info(f"{sandbox_info} 非图片文件或内容为空，使用本地路径")
                            file_info['url'] = file_info['local_path']
                        
                        # 移除 local_path，避免混淆
                        if 'local_path' in file_info:
                            del file_info['local_path']
                            
                        generated_files.append(file_info)
                    except Exception as e:
                        sandbox_info = f"[沙箱: {self.sandbox_id}|workspace: {self.temp_dir}/workspace|会话: {self.conversation_id}]"
                        logger.error(f"{sandbox_info} 复制文件失败: {filename}, error={e}")

                        # 复制失败，仍然返回文件信息（但不包含URL）
                        generated_files.append({
                            'filename': filename,
                            'type': supported_extensions[ext],
                            'size': file_size,
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
            # 关闭持久化内核
            if self._kernel:
                self._kernel.close()
                self._kernel = None
                
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
