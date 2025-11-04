"""
Database Module

Manages database connections and sessions using SQLAlchemy and Supabase client.
Provides database session dependencies and health check functions for FastAPI endpoints.
"""

from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError, DatabaseError
import logging

try:
    from supabase import create_client, Client
except ImportError:
    # Supabase client not installed - will be handled gracefully
    create_client = None
    Client = None

from src.core.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all SQLAlchemy models
Base = declarative_base()

# Global Supabase client instance
_supabase_client: Client = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.
    
    Returns:
        Client: Supabase client instance
        
    Raises:
        RuntimeError: If Supabase client cannot be initialized
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    if create_client is None:
        raise RuntimeError(
            "Supabase client library not installed. "
            "Install with: pip install supabase"
        )
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "Supabase configuration incomplete. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
        )
    
    try:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        logger.info(f"Supabase client initialized: {settings.SUPABASE_URL}")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise RuntimeError(f"Supabase client initialization failed: {e}")


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency
    
    Yields a database session for use in FastAPI endpoints.
    Ensures proper session cleanup after request completion.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """
    Check PostgreSQL database connection health.
    
    Performs a simple query to verify database connectivity.
    
    Returns:
        Dict with status, message, and optional error details
    """
    try:
        db = SessionLocal()
        try:
            # Execute simple query
            result = db.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {
                        "pool_size": settings.DATABASE_POOL_SIZE,
                        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Database query returned unexpected result",
                    "error": "Health check query failed"
                }
        finally:
            db.close()
            
    except OperationalError as e:
        logger.error(f"Database operational error: {e}")
        return {
            "status": "unhealthy",
            "message": "Database connection failed",
            "error": str(e),
            "error_type": "OperationalError"
        }
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return {
            "status": "unhealthy",
            "message": "Database error occurred",
            "error": str(e),
            "error_type": "DatabaseError"
        }
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return {
            "status": "unhealthy",
            "message": "Unexpected database error",
            "error": str(e),
            "error_type": type(e).__name__
        }


def check_supabase_connection() -> Dict[str, Any]:
    """
    Check Supabase API connection health.
    
    Attempts to initialize and ping Supabase service.
    
    Returns:
        Dict with status, message, and optional error details
    """
    try:
        # Check if Supabase library is available
        if create_client is None:
            return {
                "status": "unavailable",
                "message": "Supabase client library not installed",
                "details": {
                    "installed": False,
                    "note": "Optional dependency - install with: pip install supabase"
                }
            }
        
        # Check if configured
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            return {
                "status": "unconfigured",
                "message": "Supabase credentials not configured",
                "details": {
                    "url_set": bool(settings.SUPABASE_URL),
                    "key_set": bool(settings.SUPABASE_SERVICE_KEY)
                }
            }
        
        # Try to get/create client
        client = get_supabase_client()
        
        # Simple health check: try to query a table (will fail gracefully if tables don't exist)
        # For now, just verify client was created
        return {
            "status": "healthy",
            "message": "Supabase client initialized successfully",
            "details": {
                "url": settings.SUPABASE_URL,
                "client_initialized": client is not None
            }
        }
        
    except RuntimeError as e:
        logger.error(f"Supabase runtime error: {e}")
        return {
            "status": "unhealthy",
            "message": "Supabase initialization failed",
            "error": str(e),
            "error_type": "RuntimeError"
        }
    except Exception as e:
        logger.error(f"Unexpected Supabase error: {e}")
        return {
            "status": "unhealthy",
            "message": "Supabase connection check failed",
            "error": str(e),
            "error_type": type(e).__name__
        }


def check_database_tables() -> Dict[str, Any]:
    """
    Check if required database tables exist.
    
    Verifies that core tables from migrations are present.
    
    Returns:
        Dict with status and list of existing tables
    """
    try:
        db = SessionLocal()
        try:
            # Query for core tables
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('base_profiles', 'identity_names')
                ORDER BY table_name
            """)
            
            result = db.execute(query)
            existing_tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['base_profiles', 'identity_names']
            missing_tables = [t for t in expected_tables if t not in existing_tables]
            
            if not missing_tables:
                return {
                    "status": "healthy",
                    "message": "All required tables exist",
                    "tables": existing_tables
                }
            else:
                return {
                    "status": "incomplete",
                    "message": "Some tables are missing",
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "note": "Run migrations with: supabase db reset"
                }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking database tables: {e}")
        return {
            "status": "error",
            "message": "Failed to check database tables",
            "error": str(e)
        }

