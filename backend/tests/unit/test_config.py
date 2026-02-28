"""Tests for configuration loading, validation, and production safety checks."""

import os

import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_defaults():
    """Test that settings load with defaults"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "test-secure-key-for-testing"
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("DEBUG", None)
    os.environ.pop("LOG_LEVEL", None)

    settings = Settings()

    assert settings.APP_NAME == "Identity and Profile Management API"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    # LOG_LEVEL may come from .env file (Pydantic BaseSettings reads it)
    assert settings.LOG_LEVEL in ["INFO", "DEBUG"]


def test_database_url_validation():
    """Test DATABASE_URL validation"""
    os.environ["SECRET_KEY"] = "test-secret-key"

    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
    settings = Settings()
    assert settings.DATABASE_URL.startswith("postgresql://")

    with pytest.raises(ValidationError):
        os.environ["DATABASE_URL"] = "mysql://user:pass@localhost/db"
        Settings()


def test_log_level_validation():
    """Test LOG_LEVEL validation"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "test-secret-key"

    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        os.environ["LOG_LEVEL"] = level
        settings = Settings()
        assert settings.LOG_LEVEL == level

    with pytest.raises(ValidationError):
        os.environ["LOG_LEVEL"] = "INVALID"
        Settings()


def test_environment_validation():
    """Test ENVIRONMENT validation"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"

    for env in ["development", "staging", "test"]:
        os.environ["ENVIRONMENT"] = env
        os.environ["SECRET_KEY"] = "test-secure-key-for-testing"
        settings = Settings()
        assert settings.ENVIRONMENT == env.lower()

    os.environ["ENVIRONMENT"] = "production"
    os.environ["SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    os.environ["DEBUG"] = "false"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"
    settings = Settings()
    assert settings.ENVIRONMENT == "production"


def test_is_production_property():
    """Test is_production property"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"

    os.environ["ENVIRONMENT"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"
    os.environ["SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

    settings = Settings()
    assert settings.is_production is True

    os.environ["ENVIRONMENT"] = "development"
    os.environ["SECRET_KEY"] = "test-secure-key-for-testing"
    settings = Settings()
    assert settings.is_production is False


def test_is_development_property():
    """Test is_development property"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"

    os.environ["ENVIRONMENT"] = "development"
    os.environ["SECRET_KEY"] = "test-secure-key-for-testing"
    settings = Settings()
    assert settings.is_development is True

    os.environ["ENVIRONMENT"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"
    os.environ["SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

    settings = Settings()
    assert settings.is_development is False


def test_allowed_origins_property():
    """Test ALLOWED_ORIGINS property parses comma-separated string"""
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ALLOWED_ORIGINS_STR"] = (
        "http://localhost:3000,http://localhost:8000,https://example.com"
    )

    settings = Settings()
    assert len(settings.ALLOWED_ORIGINS) == 3
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
    assert "https://example.com" in settings.ALLOWED_ORIGINS


def test_production_security_validation_fails_with_weak_secret():
    """Test production security validation fails with weak SECRET_KEY"""
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "weak-secret"  # Too short and has weak pattern
    os.environ["DEBUG"] = "false"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings()


def test_production_security_validation_fails_with_debug_enabled():
    """Test production security validation fails with DEBUG=True"""
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    os.environ["DEBUG"] = "true"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"

    with pytest.raises(ValidationError, match="DEBUG"):
        Settings()


def test_production_security_validation_fails_with_localhost_supabase():
    """Test production security validation fails with localhost Supabase URL"""
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://test@localhost/test"
    os.environ["SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    os.environ["DEBUG"] = "false"
    os.environ["SUPABASE_URL"] = "http://127.0.0.1:54321"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"

    with pytest.raises(ValidationError, match="localhost"):
        Settings()


@pytest.fixture(autouse=True)
def cleanup_env():
    """Clean up environment variables after each test"""
    yield
    env_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "ENVIRONMENT",
        "DEBUG",
        "LOG_LEVEL",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_JWT_SECRET",
        "ALLOWED_ORIGINS_STR",
    ]
    for var in env_vars:
        os.environ.pop(var, None)
