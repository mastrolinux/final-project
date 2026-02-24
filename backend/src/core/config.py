"""
Application configuration via Pydantic Settings with production safety checks.
"""

from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    APP_NAME: str = "Identity and Profile Management API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_PUBLIC_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    SMTP_HOST: str = "127.0.0.1"
    SMTP_PORT: int = 54325
    SMTP_FROM_EMAIL: str = "noreply@identity-api.local"
    SMTP_FROM_NAME: str = "Identity Management System"
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = False
    
    FRONTEND_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8000"

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    REDIS_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_SECONDS: int = 300
    
    SENTRY_DSN: Optional[str] = None
    APM_ENABLED: bool = False
    APM_SERVICE_NAME: str = "identity-api"
    
    DELETION_RETENTION_DAYS: int = 30

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/social/google/callback"

    DOCUMENT_ENCRYPTION_KEY: str = ""

    ADMIN_USER_EMAILS: str = ""
    
    @property
    def admin_emails(self) -> List[str]:
        """Parse ADMIN_USER_EMAILS into a list."""
        return [e.strip().lower() for e in self.ADMIN_USER_EMAILS.split(",") if e.strip()]
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS_STR into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(",") if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {v}")
        return v_upper
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            logger.warning(f"ENVIRONMENT '{v}' is not standard. Valid: {valid_envs}")
        return v_lower
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Reject insecure defaults in production."""
        if not self.is_production:
            return self
        
        insecure_secret_patterns = [
            "change-this",
            "secret-key",
            "your-secret",
            "development",
            "local",
        ]
        if any(pattern in self.SECRET_KEY.lower() for pattern in insecure_secret_patterns):
            raise ValueError(
                "Production SECRET_KEY appears to be insecure or default. "
                "Generate a strong key with: openssl rand -hex 32"
            )
        
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "Production SECRET_KEY must be at least 32 characters long"
            )
        
        if self.DEBUG:
            raise ValueError("DEBUG must be False in production")
        
        if not self.SUPABASE_URL or "127.0.0.1" in self.SUPABASE_URL or "localhost" in self.SUPABASE_URL:
            raise ValueError("Production SUPABASE_URL must not be localhost")
        
        if not self.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY is required in production")
        
        if not self.SUPABASE_JWT_SECRET:
            raise ValueError("SUPABASE_JWT_SECRET is required in production")
        
        if "localhost" in self.ALLOWED_ORIGINS_STR:
            logger.warning("Production CORS includes localhost - this may be insecure")
        
        logger.info(f"Production configuration validated for: {self.APP_NAME}")
        logger.info(f"Environment: {self.ENVIRONMENT}")
        logger.info(f"Debug mode: {self.DEBUG}")
        logger.info(f"Supabase URL: {self.SUPABASE_URL}")
        
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


try:
    settings = Settings()  # type: ignore[call-arg]
    logger.info(f"Configuration loaded successfully for {settings.ENVIRONMENT} environment")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

