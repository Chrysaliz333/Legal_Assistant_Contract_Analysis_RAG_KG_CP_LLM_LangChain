"""
Application Settings and Configuration
Uses Pydantic Settings for environment variable management
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ============================================================================
    # APPLICATION
    # ============================================================================
    APP_NAME: str = "Legal Assistant Multi-Session Continuity"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # ============================================================================
    # DATABASE - PostgreSQL (Optional for Streamlit deployment)
    # ============================================================================
    DATABASE_URL: str = "sqlite:///legal_assistant.db"  # Default to SQLite
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DATABASE_ECHO: bool = False  # Set to True to log SQL queries

    # ============================================================================
    # REDIS - Cache and Session Management
    # ============================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL_TRANSFORMATION: int = 3600  # 1 hour for rationale transformations
    REDIS_TTL_SESSION: int = 86400  # 24 hours for session data

    # ============================================================================
    # AI API KEYS
    # ============================================================================
    ANTHROPIC_API_KEY: str = ""  # Optional - for Claude models
    OPENAI_API_KEY: str  # Required - for OpenAI models

    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.3  # Low temperature for consistent legal analysis
    CLAUDE_TIMEOUT: int = 60  # API timeout in seconds
    CLAUDE_MAX_RETRIES: int = 3

    # ============================================================================
    # TAVILY AI - Legal Research (Existing)
    # ============================================================================
    TAVILY_API_KEY: Optional[str] = None

    # ============================================================================
    # VECTOR DATABASE - Chroma
    # ============================================================================
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_POLICIES: str = "policies"
    CHROMA_COLLECTION_REJECTIONS: str = "rejected_clauses"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # Dimension for MiniLM

    # ============================================================================
    # SECURITY (Optional for Streamlit deployment)
    # ============================================================================
    SECRET_KEY: str = "demo-secret-key-change-in-production"  # Default for demo
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ============================================================================
    # FILE STORAGE
    # ============================================================================
    FILE_STORAGE_PATH: str = "./storage"
    FILE_STORAGE_TYPE: str = "local"  # local, s3
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".docx", ".pdf", ".doc"]

    # S3 Configuration (if FILE_STORAGE_TYPE = "s3")
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None

    # ============================================================================
    # BACKGROUND TASKS - Celery
    # ============================================================================
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    # ============================================================================
    # MONITORING & OBSERVABILITY
    # ============================================================================
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # OpenTelemetry
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "legal-assistant"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # ============================================================================
    # LOGGING
    # ============================================================================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # json, text
    LOG_FILE_PATH: Optional[str] = "./logs/app.log"

    # ============================================================================
    # ANALYSIS SETTINGS
    # ============================================================================
    # REQ-DR-001: Severity thresholds
    SEVERITY_HIGH_THRESHOLD: float = 0.7
    SEVERITY_CRITICAL_THRESHOLD: float = 0.9

    # REQ-VC-006: Semantic similarity threshold for rejection blocklist
    REJECTION_SIMILARITY_THRESHOLD: float = 0.85

    # REQ-PD-001: Policy drift detection threshold
    DRIFT_ALERT_THRESHOLD: float = 0.75
    DRIFT_CHECK_INTERVAL_HOURS: int = 1

    # REQ-OE-001: Obligation extraction
    OBLIGATION_REMINDER_DAYS_BEFORE: int = 7

    # ============================================================================
    # PERSONALITY AGENT DEFAULTS (REQ-PA-006)
    # ============================================================================
    DEFAULT_TONE: str = "concise"  # concise, verbose, balanced
    DEFAULT_FORMALITY: str = "legal"  # legal, plain_english
    DEFAULT_AGGRESSIVENESS: str = "balanced"  # strict, balanced, flexible
    DEFAULT_AUDIENCE: str = "internal"  # internal, counterparty

    # ============================================================================
    # PERFORMANCE
    # ============================================================================
    MAX_CONCURRENT_ANALYSES: int = 5
    ANALYSIS_TIMEOUT_SECONDS: int = 300  # 5 minutes
    MAX_CLAUSE_LENGTH: int = 10000  # Characters
    BATCH_SIZE_FINDINGS: int = 50

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    # ============================================================================
    # TESTING
    # ============================================================================
    TESTING: bool = False
    TEST_DATABASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get database URL based on environment"""
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        if self.is_production():
            # In production, use only allowed origins
            return self.CORS_ORIGINS
        return ["*"]  # Allow all in development


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Using lru_cache ensures we only read .env once
    """
    return Settings()


# Global settings instance
settings = get_settings()
