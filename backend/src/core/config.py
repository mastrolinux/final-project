"""
Configuration Module

Manages application configuration using Pydantic Settings.
Environment variables are loaded from .env file and system environment.
Includes validation and production safety checks.
"""

from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application Settings
    
    All configuration values are loaded from environment variables.
    See env.local.template (development) or env.production.template (production).
    
    Includes production safety validations to prevent insecure defaults.
    """
    
    # Application Settings
    APP_NAME: str = "Identity and Profile Management API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database Configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Supabase Configuration
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # JWT Configuration (Auth Service)
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # SMTP Configuration (Email Sending)
    # Local: Mailpit via Supabase (no auth, plain SMTP)
    # Production: Mailgun or other SMTP provider (TLS + auth)
    SMTP_HOST: str = "127.0.0.1"
    SMTP_PORT: int = 54325  # Mailpit: 54325, Mailgun: 587
    SMTP_FROM_EMAIL: str = "noreply@identity-api.local"
    SMTP_FROM_NAME: str = "Identity Management System"
    SMTP_USER: Optional[str] = None  # Mailgun: postmaster@yourdomain.mailgun.org
    SMTP_PASSWORD: Optional[str] = None  # Mailgun: SMTP password
    SMTP_USE_TLS: bool = False  # True for production SMTP providers
    
    # Frontend URL (for email links to frontend app)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # API Base URL (for direct API testing without frontend)
    API_BASE_URL: str = "http://localhost:8000"
    
    # CORS Configuration
    ALLOWED_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8000"
    
    # Optional Features
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    REDIS_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_SECONDS: int = 300
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    APM_ENABLED: bool = False
    APM_SERVICE_NAME: str = "identity-api"
    
    # Feature Flags
    FEATURE_OAUTH_ENABLED: bool = False
    FEATURE_GUARDIAN_RELATIONSHIPS_ENABLED: bool = False
    FEATURE_CONTEXT_PROFILES_ENABLED: bool = False
    
    # Admin Configuration
    # Comma-separated list of admin user emails for bootstrap
    # These users have admin access even if is_admin=false in DB
    ADMIN_USER_EMAILS: str = ""
    
    @property
    def admin_emails(self) -> List[str]:
        """Parse admin emails from comma-separated string"""
        return [e.strip().lower() for e in self.ADMIN_USER_EMAILS.split(",") if e.strip()]
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
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
        """Validate log level is a valid Python logging level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {v}")
        return v_upper
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is a known value"""
        valid_envs = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            logger.warning(f"ENVIRONMENT '{v}' is not standard. Valid: {valid_envs}")
        return v_lower
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """
        Validate security settings for production environment.
        Ensures insecure defaults are not used in production.
        """
        if not self.is_production:
            return self
        
        # Check SECRET_KEY is not default/weak
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
        
        # Check DEBUG is disabled
        if self.DEBUG:
            raise ValueError("DEBUG must be False in production")
        
        # Check Supabase keys are set
        if not self.SUPABASE_URL or "127.0.0.1" in self.SUPABASE_URL or "localhost" in self.SUPABASE_URL:
            raise ValueError("Production SUPABASE_URL must not be localhost")
        
        if not self.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY is required in production")
        
        if not self.SUPABASE_JWT_SECRET:
            raise ValueError("SUPABASE_JWT_SECRET is required in production")
        
        # Warn about CORS
        if "localhost" in self.ALLOWED_ORIGINS_STR:
            logger.warning("Production CORS includes localhost - this may be insecure")
        
        # Log production configuration (without secrets)
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


# Global settings instance
try:
    settings = Settings()
    logger.info(f"Configuration loaded successfully for {settings.ENVIRONMENT} environment")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

