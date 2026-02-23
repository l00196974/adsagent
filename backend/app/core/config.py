from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # OpenAI API配置（MiniMax兼容）
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL", None)

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")

    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    primary_model: str = os.getenv("PRIMARY_MODEL", "glm-4.6-flash")
    reasoning_model: str = os.getenv("REASONING_MODEL", "qwen3-32b")
    max_tokens_per_request: int = int(os.getenv("MAX_TOKENS_PER_REQUEST", "30000"))

    # LLM并行处理配置
    max_llm_workers: int = int(os.getenv("MAX_LLM_WORKERS", "4"))  # 最大并发LLM调用数

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
