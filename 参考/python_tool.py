"""Python执行工具"""
import re
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from .base import BaseTool, tool_result

logger = logging.getLogger(__name__)


class PythonTool(BaseTool):
    """Python代码执行工具（会话级本地沙箱）

    特性：
    - 自动注入常用库导入（matplotlib, pandas, numpy等）
    - 自动检测并保存matplotlib/seaborn图像
    - 沙箱环境隔离
    """

    name = "execute_python"
    description = """在会话专属的本地沙箱中执行Python代码。

【必须导入所需包】
生成的代码必须在开头显式导入所有需要的库，例如：
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
```
不要省略导入语句，保持代码完整性。

【绘图规范】重要！
1. 必须在代码开头设置matplotlib后端和中文字体：
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
   plt.rcParams['axes.unicode_minus'] = False
2. 禁止使用 plt.show()，图像会自动保存为PNG文件
3. 多张图请合并为1个图，使用 plt.subplots() 子图模式展示
4. 无需调用 plt.savefig()，系统会自动保存所有图像
5. 支持中文标题和标签

【代码示例】
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes[0, 0].plot(data1)
axes[0, 1].bar(categories, values)
axes[1, 0].scatter(x, y)
axes[1, 1].hist(data)
plt.tight_layout()

【注意事项】
- 每次执行是独立进程，变量不会跨执行保留
- 数据处理优先使用 pandas
- 复杂计算注意设置 timeout 参数（默认60秒）
"""

    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python代码"
            },
            "timeout": {
                "type": "integer",
                "default": 60,
                "description": "超时时间（秒）"
            }
        },
        "required": ["code"]
    }

    def __init__(self):
        super().__init__()
        self.conversation_id = None
        self.sandbox_manager = None

    def set_context(self, user_channel: str):
        """设置上下文"""
        self.user_channel = user_channel
        # 延迟导入避免循环依赖
        from ...core.sandbox_manager import SandboxManager
        self.sandbox_manager = SandboxManager()

    def set_conversation_id(self, conversation_id: str):
        """设置当前会话ID"""
        self.conversation_id = conversation_id

    def _preprocess_code(self, code: str) -> str:
        """
        预处理代码：
        1. 移除matplotlib的过时参数
        2. 自动注入常用库导入
        3. 自动检测并保存图像
        """
        # 1. 移除 matplotlib stem() 的过时参数
        code = code.replace("use_line_collection=True", "")
        code = code.replace("use_line_collection=False", "")
        code = code.replace("use_line_collection=True,", "")
        code = code.replace("use_line_collection=False,", "")

        # 2. 检测是否需要注入导入
        imports_to_add = []

        # 检测matplotlib使用
        if re.search(r'\bplt\.', code) or re.search(r'matplotlib\.pyplot', code):
            if 'import matplotlib' not in code and 'from matplotlib' not in code:
                imports_to_add.append("import matplotlib.pyplot as plt")

        # 检测pandas使用
        if re.search(r'\bpd\.', code) or re.search(r'\bpandas\.', code):
            if 'import pandas' not in code and 'from pandas' not in code:
                imports_to_add.append("import pandas as pd")

        # 检测numpy使用
        if re.search(r'\bnp\.', code) or re.search(r'\bnumpy\.', code):
            if 'import numpy' not in code and 'from numpy' not in code:
                imports_to_add.append("import numpy as np")

        # 检测seaborn使用
        if re.search(r'\bsns\.', code) or re.search(r'\bseaborn\.', code):
            if 'import seaborn' not in code and 'from seaborn' not in code:
                imports_to_add.append("import seaborn as sns")

        # 3. 检测是否需要添加中文字体设置和图像自动保存
        has_matplotlib = 'plt.' in code or 'matplotlib' in code
        has_savefig = 'savefig' in code or 'to_file' in code

        # 图像自动保存代码
        auto_save_code = ""
        if has_matplotlib and not has_savefig:
            # 检测是否有plt.show()但没有savefig
            auto_save_code = '''
# 自动保存图像
import os
for fig_num in plt.get_fignums():
    fig = plt.figure(fig_num)
    if not hasattr(fig, '_auto_saved'):
        filename = f'auto_figure_{fig_num}.png'
        fig.savefig(filename, dpi=150, bbox_inches='tight', facecolor='white')
        fig._auto_saved = True
        print(f"图像已自动保存: {filename}")
'''

        # matplotlib中文字体设置
        matplotlib_setup = ""
        if has_matplotlib:
            matplotlib_setup = '''# 设置matplotlib中文字体和样式
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
'''

        # 警告过滤
        warning_filter = "import warnings\nwarnings.filterwarnings('ignore')\n"

        # 组装最终代码
        parts = []

        # 添加警告过滤
        if 'warnings' not in code:
            parts.append(warning_filter)

        # 添加matplotlib设置（如果有matplotlib使用）
        if has_matplotlib and 'matplotlib.use' not in code:
            # 如果已经有import matplotlib，替换掉
            if 'import matplotlib' in code:
                # 不添加，让原代码的import生效
                pass
            else:
                parts.append(matplotlib_setup)

        # 添加其他导入
        for imp in imports_to_add:
            # 避免重复添加
            if imp.split()[-1] not in code:  # 检查别名是否已存在
                parts.append(imp + "\n")

        # 添加原始代码
        parts.append(code)

        # 添加自动保存代码
        if auto_save_code:
            parts.append(auto_save_code)

        final_code = "".join(parts)

        logger.debug(f"[代码预处理] 原始长度: {len(code)}, 处理后长度: {len(final_code)}")
        return final_code

    async def execute(self, code: str, timeout: int = 60) -> Dict[str, Any]:
        """在会话专属的本地沙箱中执行Python代码"""
        if not self.conversation_id:
            return tool_result("错误: 未设置会话ID，无法获取沙箱", success=False)

        # 预处理代码
        code = self._preprocess_code(code)

        # 获取会话专属沙箱
        session = await self.sandbox_manager.get_sandbox(self.conversation_id)

        if not session:
            logger.error(f"[沙箱: 无|workspace: 无|会话: {self.conversation_id}] 无法获取沙箱")
            return tool_result("错误: 无法创建沙箱", success=False)

        # 构造沙箱信息前缀
        sandbox_info = f"[沙箱: {session.sandbox.sandbox_id}|workspace: {session.sandbox.temp_dir}/workspace|会话: {self.conversation_id}]"
        logger.info(f"{sandbox_info} 开始执行代码, timeout={timeout}s, code_length={len(code)}")

        try:
            # 在沙箱中执行代码
            result = await session.execute_code(code, timeout)

            if result["success"]:
                logger.info(f"{sandbox_info} 执行成功")
                # 处理生成的文件
                files = result.get("files", [])
                file_info = []
                for file_data in files:
                    info = {
                        "filename": file_data["filename"],
                        "type": file_data["type"],
                        "size": file_data["size"],
                        "path": file_data.get("filename"),
                        "url": file_data.get("url"),
                        "in_sandbox": True
                    }
                    # 传递 base64 数据（如果有）
                    if file_data.get("base64"):
                        info["base64"] = file_data["base64"]
                        info["url"] = file_data["base64"]  # 优先使用 base64
                    file_info.append(info)

                response_data = {
                    "success": True,
                    "output": result["output"],
                    "error": result["error"],
                    "sandbox_type": "local_process",
                    "sandbox_id": session.sandbox.sandbox_id,
                    "files": file_info
                }

                return tool_result(response_data)
            else:
                logger.error(f"{sandbox_info} 执行失败, error={result['error']}")
                return tool_result(f"执行失败: {result['error']}", success=False)

        except Exception as e:
            logger.error(f"{sandbox_info} 执行异常, error={e}")
            return tool_result(f"执行异常: {str(e)}", success=False)
