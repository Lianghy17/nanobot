"""ChatBI配置管理"""
import os
import json
import logging
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """获取项目根目录"""
    current = Path(__file__).resolve()
    # 向上查找直到找到nanobot目录
    for parent in current.parents:
        if parent.name == "nanobot" or (parent / "prd").exists():
            return parent
    return current.parent


def load_chatbi_config() -> Dict[str, Any]:
    """加载ChatBI专用配置文件"""
    config_path = get_project_root() / "config" / "chatbi.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_name: str = "ChatBI"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # LLM配置（环境变量优先，配置文件为备选）
    llm_model: str = Field(default="gpt-4", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")

    # Loop队列配置
    loop_workers: int = Field(default=1, env="LOOP_WORKERS")
    queue_max_size: int = Field(default=1000, env="QUEUE_MAX_SIZE")

    # 项目根目录
    project_root: Path = Field(default_factory=get_project_root)

    # 文件配置
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB

    # 工作空间路径（使用项目目录下的workspace）
    workspace_path: str = Field(default=str(get_project_root() / "workspace"), env="WORKSPACE_PATH")

    @property
    def upload_path(self) -> str:
        """上传路径"""
        return str(Path(self.workspace_path) / "files")

    @property
    def sessions_path(self) -> str:
        """会话路径"""
        return str(Path(self.workspace_path) / "sessions")

    # 外部服务
    rag_api_url: str = Field(default="http://my_rag_v1", env="RAG_API_URL")
    sql_api_url: str = Field(default="http://my_hive_sql_exec", env="SQL_API_URL")

    # CORS配置
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ChatBIConfig:
    """ChatBI专用配置管理器"""

    def __init__(self):
        self._config = load_chatbi_config()

    @property
    def llm_api_base(self) -> str:
        """LLM API基础URL"""
        return os.getenv("LLM_API_BASE", self._config.get("llm", {}).get("api_base", "http://localhost:8000/v1"))

    @property
    def llm_api_key(self) -> str:
        """LLM API密钥"""
        return os.getenv("LLM_API_KEY", self._config.get("llm", {}).get("api_key", "no-key"))

    @property
    def llm_model(self) -> str:
        """LLM模型名称"""
        return os.getenv("LLM_MODEL", self._config.get("llm", {}).get("model", "gpt-4"))

    @property
    def llm_temperature(self) -> float:
        """LLM温度参数"""
        return float(os.getenv("LLM_TEMPERATURE", str(self._config.get("llm", {}).get("temperature", 0.7))))

    @property
    def llm_max_tokens(self) -> int:
        """LLM最大token数"""
        return int(os.getenv("LLM_MAX_TOKENS", str(self._config.get("llm", {}).get("max_tokens", 4096))))

    @property
    def llm_timeout(self) -> int:
        """LLM超时时间"""
        return int(os.getenv("LLM_TIMEOUT", str(self._config.get("llm", {}).get("timeout", 60))))

    @property
    def sandbox_api_key(self) -> str:
        """沙箱API密钥"""
        return os.getenv("SANDBOX_API_KEY", self._config.get("sandbox", {}).get("api_key", ""))

    @property
    def sandbox_domain(self) -> str:
        """沙箱API域名"""
        return os.getenv("SANDBOX_DOMAIN", self._config.get("sandbox", {}).get("domain", "https://api.opensandbox.io"))

    @property
    def sandbox_image(self) -> str:
        """沙箱镜像"""
        return os.getenv("SANDBOX_IMAGE", self._config.get("sandbox", {}).get("image", "python:3.11"))

    @property
    def agent_max_iterations(self) -> int:
        """Agent最大迭代次数"""
        return self._config.get("agent", {}).get("max_iterations", 10)

    @property
    def agent_max_history_messages(self) -> int:
        """Agent最大历史消息数"""
        return self._config.get("agent", {}).get("max_history_messages", 20)

    @property
    def agent_system_prompt_template(self) -> str:
        """Agent系统提示模板"""
        # 优先从文件加载
        prompt_file = self._config.get("agent", {}).get("system_prompt_file")
        if prompt_file:
            try:
                # 尝试从 config/system_prompts 目录加载
                base_dir = Path(get_project_root()) / self._config.get("system_prompts", {}).get("base_dir", "config/system_prompts")
                file_path = base_dir / prompt_file

                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        return f.read()
                else:
                    # 尝试直接使用相对路径
                    file_path = get_project_root() / prompt_file
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as f:
                            return f.read()
            except Exception as e:
                logger.warning(f"加载系统提示词文件失败: {prompt_file}, error={e}")

        # 回退到配置中的模板
        return self._config.get("agent", {}).get(
            "system_prompt_template",
            "你是一个数据分析助手，当前场景是{scene_name}（{scene_code}）。可以使用以下工具：{tool_names}。请根据用户的问题，选择合适的工具进行数据查询和分析。优先使用python代码编写能力，并执行获得结果。"
        )

    @property
    def tools_config(self) -> Dict[str, Dict[str, Any]]:
        """工具配置"""
        return self._config.get("tools", {})

    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取特定工具的配置"""
        return self.tools_config.get(tool_name)

    @property
    def current_time(self) -> str:
        """获取格式化的当前时间"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def runtime_environment(self) -> str:
        """获取运行环境信息"""
        python_version = platform.python_version()
        system = platform.system()
        return f"Python {python_version} on {system}"


# 全局配置实例
settings = Settings()
chatbi_config = ChatBIConfig()

# 确保目录存在
def ensure_directories():
    """确保工作目录存在"""
    Path(settings.upload_path).mkdir(parents=True, exist_ok=True)
    Path(settings.sessions_path).mkdir(parents=True, exist_ok=True)
    Path(settings.workspace_path).mkdir(parents=True, exist_ok=True)

# 初始化时调用
ensure_directories()
