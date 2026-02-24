"""Identity and Profile Management API - Main Application."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.encryption import configure_encryption_service
from src.core.storage import (
    SupabaseDocumentStorageClient,
    SupabaseStorageClient,
    configure_document_storage_client,
    configure_storage_client,
)
from src.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Identity and Profile Management API - Multi-context, privacy oriented identity system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
    configure_storage_client(
        SupabaseStorageClient(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            public_url=settings.SUPABASE_PUBLIC_URL,
        )
    )
    configure_document_storage_client(
        SupabaseDocumentStorageClient(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            public_url=settings.SUPABASE_PUBLIC_URL,
        )
    )

if settings.DOCUMENT_ENCRYPTION_KEY:
    configure_encryption_service(settings.DOCUMENT_ENCRYPTION_KEY)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Basic health check. Use /health/detailed for component status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check covering database, Supabase, and table status."""
    from src.core.database import (
        check_db_connection,
        check_supabase_connection,
        check_database_tables
    )
    
    db_health = check_db_connection()
    supabase_health = check_supabase_connection()
    tables_health = check_database_tables()

    # Supabase client is optional; only "unhealthy" (not "unavailable") degrades status
    overall_status = "healthy"
    if db_health["status"] == "unhealthy":
        overall_status = "unhealthy"
    elif tables_health["status"] in ["incomplete", "error"]:
        overall_status = "degraded"
    elif supabase_health["status"] == "unhealthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_health,
            "supabase": supabase_health,
            "tables": tables_health
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information and navigation links."""
    return {
        "message": "Identity and Profile Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

