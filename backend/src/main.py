"""
Identity and Profile Management API - Main Application

This is the main FastAPI application entry point for the Identity and Profile Management API system.
A thesis project designed to handle complex digital identity across cultural, contextual, and regulatory boundaries.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api.v1.router import api_router

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Identity and Profile Management API - Multi-context, privacy oriented identity system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """
    Basic health check endpoint
    
    Returns basic service status information.
    For detailed health information, use /health/detailed
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check endpoint
    
    Checks the health of all system components:
    - Application status
    - Database connection (PostgreSQL via SQLAlchemy)
    - Supabase connection and configuration
    - Database tables existence
    
    Returns comprehensive status for monitoring and debugging.
    """
    from src.core.database import (
        check_db_connection,
        check_supabase_connection,
        check_database_tables
    )
    
    # Check database connection
    db_health = check_db_connection()
    
    # Check Supabase connection
    supabase_health = check_supabase_connection()
    
    # Check database tables
    tables_health = check_database_tables()
    
    # Determine overall status
    overall_status = "healthy"
    if db_health["status"] == "unhealthy":
        overall_status = "unhealthy"
    elif supabase_health["status"] == "unhealthy":
        overall_status = "degraded"
    elif tables_health["status"] in ["incomplete", "error"]:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": "2025-01-04T00:00:00Z",  # Will be dynamic in production
        "components": {
            "database": db_health,
            "supabase": supabase_health,
            "tables": tables_health
        }
    }


@app.get("/")
async def root():
    """
    Root endpoint
    
    Provides basic API information and navigation.
    """
    return {
        "message": "Identity and Profile Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

