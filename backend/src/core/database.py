"""
Database connection management, session dependencies, and health checks.
"""

from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError, DatabaseError
import logging

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

from src.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

_supabase_client: Client = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
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
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """Check PostgreSQL database connection health."""
    try:
        db = SessionLocal()
        try:
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
    """Check Supabase API connection health."""
    try:
        if create_client is None:
            return {
                "status": "unavailable",
                "message": "Supabase client library not installed",
                "details": {
                    "installed": False,
                    "note": "Optional dependency - install with: pip install supabase"
                }
            }
        
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            return {
                "status": "unconfigured",
                "message": "Supabase credentials not configured",
                "details": {
                    "url_set": bool(settings.SUPABASE_URL),
                    "key_set": bool(settings.SUPABASE_SERVICE_KEY)
                }
            }
        
        client = get_supabase_client()
        return {
            "status": "healthy",
            "message": "Supabase client initialized successfully",
            "details": {
                "url": settings.SUPABASE_URL,
                "client_initialized": client is not None
            }
        }
        
    except RuntimeError as e:
        logger.warning(f"Supabase client unavailable (non-critical): {e}")
        return {
            "status": "unavailable",
            "message": "Supabase client unavailable (non-critical - using direct PostgreSQL)",
            "note": "System fully functional with direct PostgreSQL connection",
            "error": str(e),
            "error_type": "RuntimeError"
        }
    except Exception as e:
        logger.warning(f"Supabase client error (non-critical): {e}")
        return {
            "status": "unavailable",
            "message": "Supabase client unavailable (non-critical - using direct PostgreSQL)",
            "note": "System fully functional with direct PostgreSQL connection",
            "error": str(e),
            "error_type": type(e).__name__
        }


def check_database_tables() -> Dict[str, Any]:
    """Check if required database tables exist."""
    try:
        db = SessionLocal()
        try:
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

