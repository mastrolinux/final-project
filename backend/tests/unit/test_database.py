"""Tests for database connection, health checks, and Supabase client initialization."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import DatabaseError, OperationalError

from src.core.database import (
    check_database_tables,
    check_db_connection,
    check_supabase_connection,
    get_supabase_client,
)


@patch("src.core.database.SessionLocal")
def test_check_db_connection_healthy(mock_session):
    """Test database connection check when database is healthy"""
    mock_db = Mock()
    mock_result = Mock()
    mock_result.fetchone.return_value = (1,)
    mock_db.execute.return_value = mock_result
    mock_session.return_value = mock_db

    result = check_db_connection()

    assert result["status"] == "healthy"
    assert result["message"] == "Database connection successful"
    assert "details" in result


@patch("src.core.database.SessionLocal")
def test_check_db_connection_operational_error(mock_session):
    """Test database connection check when OperationalError occurs"""
    mock_db = Mock()
    mock_db.execute.side_effect = OperationalError("Connection failed", None, None)
    mock_session.return_value = mock_db

    result = check_db_connection()

    assert result["status"] == "unhealthy"
    assert result["message"] == "Database connection failed"
    assert result["error_type"] == "OperationalError"


@patch("src.core.database.SessionLocal")
def test_check_db_connection_database_error(mock_session):
    """Test database connection check when DatabaseError occurs"""
    mock_db = Mock()
    mock_db.execute.side_effect = DatabaseError("Database error", None, None)
    mock_session.return_value = mock_db

    result = check_db_connection()

    assert result["status"] == "unhealthy"
    assert result["message"] == "Database error occurred"
    assert result["error_type"] == "DatabaseError"


@patch("src.core.database.create_client", None)
def test_check_supabase_connection_unavailable():
    """Test Supabase connection check when library not installed"""
    result = check_supabase_connection()

    assert result["status"] == "unavailable"
    assert result["message"] == "Supabase client library not installed"
    assert result["details"]["installed"] is False


@patch("src.core.database.settings")
@patch("src.core.database.create_client", MagicMock())
def test_check_supabase_connection_unconfigured(mock_settings):
    """Test Supabase connection check when not configured"""
    mock_settings.SUPABASE_URL = ""
    mock_settings.SUPABASE_SERVICE_KEY = ""

    result = check_supabase_connection()

    assert result["status"] == "unconfigured"
    assert result["message"] == "Supabase credentials not configured"


@patch("src.core.database.SessionLocal")
def test_check_database_tables(mock_session):
    """Test database tables check"""
    mock_db = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [("base_profiles",), ("identity_names",)]
    mock_db.execute.return_value = mock_result
    mock_session.return_value = mock_db

    result = check_database_tables()

    assert result["status"] == "healthy"
    assert result["message"] == "All required tables exist"
    assert "tables" in result


@patch("src.core.database.SessionLocal")
def test_check_database_tables_error(mock_session):
    """Test database tables check when error occurs"""
    mock_db = Mock()
    mock_db.execute.side_effect = Exception("Query failed")
    mock_session.return_value = mock_db

    result = check_database_tables()

    assert result["status"] == "error"
    assert result["message"] == "Failed to check database tables"


@patch("src.core.database.create_client")
@patch("src.core.database.settings")
def test_get_supabase_client_success(mock_settings, mock_create_client):
    """Test successful Supabase client creation"""
    mock_settings.SUPABASE_URL = "http://test.supabase.co"
    mock_settings.SUPABASE_SERVICE_KEY = "test-key"
    mock_client = Mock()
    mock_create_client.return_value = mock_client

    import src.core.database

    src.core.database._supabase_client = None

    client = get_supabase_client()

    assert client is not None
    mock_create_client.assert_called_once_with("http://test.supabase.co", "test-key")


@patch("src.core.database.create_client", None)
def test_get_supabase_client_not_installed():
    """Test Supabase client creation when library not installed"""
    import src.core.database

    src.core.database._supabase_client = None

    with pytest.raises(RuntimeError, match="not installed"):
        get_supabase_client()


@patch("src.core.database.create_client")
@patch("src.core.database.settings")
def test_get_supabase_client_missing_config(mock_settings, mock_create_client):
    """Test Supabase client creation with missing configuration"""
    mock_settings.SUPABASE_URL = ""
    mock_settings.SUPABASE_SERVICE_KEY = ""

    import src.core.database

    src.core.database._supabase_client = None

    with pytest.raises(RuntimeError, match="incomplete"):
        get_supabase_client()
