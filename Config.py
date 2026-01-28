"""
Application Configuration Settings
===================================

Centralized configuration management using Pydantic Settings.
All settings can be overridden via environment variables.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==========================================
    # Application Settings
    # ==========================================
    APP_ENV: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=4, description="Number of workers")
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ==========================================
    # API Keys
    # ==========================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google API key for LangExtract")
    
    # Pinecone settings
    PINECONE_API_KEY: Optional[str] = Field(default=None, description="Pinecone API key")
    PINECONE_ENVIRONMENT: str = Field(default="us-east-1", description="Pinecone environment")
    PINECONE_INDEX_NAME: str = Field(default="knowledge-base", description="Pinecone index name")
    PINECONE_NAMESPACE: str = Field(default="default", description="Pinecone namespace")
    
    # ==========================================
    # Redis Settings
    # ==========================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend")
    
    # ==========================================
    # File Upload Settings
    # ==========================================
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, description="Maximum upload size in MB")
    UPLOAD_DIR: str = Field(default="/app/uploads", description="Upload directory")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "docx", "pptx", "xlsx", "txt", "md", "html", "png", "jpg", "jpeg"],
        description="Allowed file types"
    )
    
    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ft.strip().lower() for ft in v.split(",")]
        return v
    
    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # ==========================================
    # Model Settings
    # ==========================================
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    EMBEDDING_DIMENSION: int = Field(default=384, description="Embedding dimension")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model for RAG")
    LANGEXTRACT_MODEL: str = Field(default="gemini-2.5-flash", description="LangExtract model")
    
    # ==========================================
    # RAG Settings
    # ==========================================
    CHUNK_SIZE: int = Field(default=1000, description="Document chunk size")
    CHUNK_OVERLAP: int = Field(default=200, description="Chunk overlap")
    TOP_K_RESULTS: int = Field(default=5, description="Number of results to return")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Minimum similarity score")
    
    # PageIndex settings
    PAGEINDEX_MAX_PAGES_PER_NODE: int = Field(default=10, description="Max pages per PageIndex node")
    PAGEINDEX_MAX_TOKENS_PER_NODE: int = Field(default=20000, description="Max tokens per PageIndex node")
    
    # ==========================================
    # PII Protection Settings
    # ==========================================
    PII_DETECTION_ENABLED: bool = Field(default=True, description="Enable PII detection")
    PII_CATEGORIES: List[str] = Field(
        default=["password", "api_key", "credit_card", "ssn", "email", "phone"],
        description="PII categories to detect"
    )
    
    @field_validator("PII_CATEGORIES", mode="before")
    @classmethod
    def parse_pii_categories(cls, v):
        if isinstance(v, str):
            return [cat.strip().lower() for cat in v.split(",")]
        return v
    
    # ==========================================
    # Security Settings
    # ==========================================
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    
    # ==========================================
    # Cache Settings
    # ==========================================
    CACHE_TTL_SECONDS: int = Field(default=3600, description="Cache TTL in seconds")
    EMBEDDING_CACHE_ENABLED: bool = Field(default=True, description="Enable embedding cache")


# Global settings instance
settings = Settings()