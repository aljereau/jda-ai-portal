"""
Configuration management for JDA AI Portal Backend.
Uses Pydantic Settings for type-safe environment variable handling.
"""
from functools import lru_cache
from typing import List, Optional, Any, Dict
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    All settings can be overridden via environment variables.
    """
    
    # Application Settings
    PROJECT_NAME: str = "JDA AI-Guided Project Portal"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Enterprise AI-guided project management platform"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    
    # Security Settings
    SECRET_KEY: str = Field(
        default="dev_secret_key_change_in_production",
        description="Secret key for JWT token signing"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT access token expiration time")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, description="JWT refresh token expiration time")  # 7 days
    ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./test.db",
        description="Database connection URL"
    )
    
    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and sessions"
    )
    
    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # Trusted Hosts
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0"],
        description="Allowed host headers"
    )
    
    # Email Settings
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # AI Integration Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for GPT integration")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key for Claude integration")
    DEFAULT_AI_MODEL: str = Field(default="gpt-4", description="Default AI model to use")
    MAX_AI_TOKENS: int = Field(default=4000, description="Maximum tokens for AI responses")
    
    # File Upload Settings
    MAX_UPLOAD_SIZE: int = Field(default=50 * 1024 * 1024, description="Maximum file upload size in bytes (50MB)")
    UPLOAD_DIR: str = Field(default="uploads", description="Directory for file uploads")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=[".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"],
        description="Allowed file extensions for uploads"
    )
    
    # Background Tasks
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )
    
    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # External Integrations
    READ_AI_API_KEY: Optional[str] = Field(default=None, description="Read.ai API key for meeting transcriptions")
    SLACK_BOT_TOKEN: Optional[str] = Field(default=None, description="Slack bot token for notifications")
    SLACK_SIGNING_SECRET: Optional[str] = Field(default=None, description="Slack signing secret")
    
    # Project Management
    DEFAULT_PROJECT_PHASES: List[str] = Field(
        default=["Intake & Proposal", "Discovery", "Design & Build", "Deployment"],
        description="Default project phases"
    )
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be 'development', 'staging', or 'production'")
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Any) -> List[str]:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def parse_file_types(cls, v: Any) -> List[str]:
        """Parse allowed file types from string or list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    @property
    def upload_path(self) -> Path:
        """Get upload directory path."""
        return Path(self.UPLOAD_DIR)
    
    def get_database_url(self) -> str:
        """Get database URL with proper encoding."""
        return self.DATABASE_URL
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration settings."""
        return {
            "openai_api_key": self.OPENAI_API_KEY,
            "anthropic_api_key": self.ANTHROPIC_API_KEY,
            "default_model": self.DEFAULT_AI_MODEL,
            "max_tokens": self.MAX_AI_TOKENS,
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid re-reading environment variables.
    """
    return Settings()

# Create global settings instance
settings = get_settings() 