from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"


class EmbeddingProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"


class ChunkingStrategy(str, Enum):
    FIXED = "fixed"
    SEMANTIC = "semantic"
    PARENT_CHILD = "parent_child"


class VectorStoreProvider(str, Enum):
    CHROMA = "chroma"
    PGVECTOR = "pgvector"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "mistral:7b-instruct"
    base_url: str = "http://localhost:11434"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    timeout: int = Field(default=120, gt=0)
    api_key: str | None = None


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    provider: EmbeddingProvider = EmbeddingProvider.OLLAMA
    model: str = "nomic-embed-text"
    base_url: str = "http://localhost:11434"
    batch_size: int = Field(default=32, gt=0)
    dimensions: int = Field(default=768, gt=0)
    api_key: str | None = None


class ChunkingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHUNKING_")

    strategy: ChunkingStrategy = ChunkingStrategy.PARENT_CHILD
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=64, ge=0)
    parent_chunk_size: int = Field(default=2048, gt=0)

    @field_validator("chunk_overlap")
    @classmethod
    def overlap_smaller_than_chunk(cls, v: int, info: object) -> int:
        # info.data may not have chunk_size yet during validation order
        return v


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_")

    k: int = Field(default=6, gt=0)
    fetch_k: int = Field(default=20, gt=0)
    use_reranker: bool = True
    use_hybrid: bool = True
    bm25_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    use_hyde: bool = False
    use_multi_query: bool = True
    cache_ttl: int = Field(default=3600, gt=0)
    cache_similarity_threshold: float = Field(default=0.95, ge=0.0, le=1.0)


class VectorStoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VECTORSTORE_")

    provider: VectorStoreProvider = VectorStoreProvider.CHROMA
    persist_dir: Path = ROOT_DIR / ".chroma"
    collection_prefix: str = "rag"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = "localhost"
    port: int = Field(default=5432, gt=0)
    name: str = "ragdb"
    user: str = "postgres"
    password: str = "postgres"
    pool_size: int = Field(default=10, gt=0)
    max_overflow: int = Field(default=20, ge=0)

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = Field(default=6379, gt=0)
    db: int = Field(default=0, ge=0)
    password: str | None = None
    max_connections: int = Field(default=50, gt=0)

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = "0.0.0.0"  # noqa: S104  # nosec B104
    port: int = Field(default=8000, gt=0)
    workers: int = Field(default=4, gt=0)
    rate_limit_per_minute: int = Field(default=60, gt=0)
    max_upload_size_mb: int = Field(default=50, gt=0)
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=60, gt=0)


class MonitoringSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONITORING_")

    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    prometheus_enabled: bool = True
    prometheus_port: int = Field(default=9090, gt=0)


class EvaluationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVAL_")

    ragas_sample_size: int = Field(default=50, gt=0)
    experiment_tracking: bool = True
    experiments_dir: Path = ROOT_DIR / "data" / "experiments"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "rag-pipeline-demo"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"  # development | staging | production

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    vectorstore: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    api: APISettings = Field(default_factory=APISettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)

    @classmethod
    def from_yaml(cls, path: Path = ROOT_DIR / "config.yaml") -> Settings:
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f)
        flat: dict[str, Any] = {}
        for section, values in data.items():
            if isinstance(values, dict):
                for k, v in values.items():
                    flat[f"{section}__{k}"] = v
            else:
                flat[section] = values
        return cls(**flat)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_yaml()
