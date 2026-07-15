"""配置管理，从 .env 文件和环境变量读取"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM 文本 ---
    llm_api_key: str = "sk-"
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"

    # --- LLM 多模态（轴体图片识别）---
    vision_api_key: str = "sk-"
    vision_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    vision_model: str = "qwen-vl-max"

    # --- Embedding ---
    embedding_api_key: str = "sk-"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    # --- ChromaDB ---
    chroma_persist_dir: str = "./data/chroma"

    # --- PostgreSQL（会话持久化）---
    pg_connection_string: str = "postgresql+asyncpg://user:pass@localhost:5432/oprag"

    # --- 检索参数 ---
    hybrid_top_k: int = 10
    rerank_top_k: int = 3
    retrieval_score_threshold: float = 0.6

    # --- 服务 ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- 安全 ---
    api_key: str = ""  # H5 页面携带的 API Key，空表示不启用认证

    # --- 速率限制 ---
    global_qps: int = 10
    session_qps: int = 2
    buyer_daily_limit: int = 200


settings = Settings()
