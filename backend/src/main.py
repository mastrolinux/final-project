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
    description="Identity and Profile Management API - Multi-context, GDPR-compliant identity system",
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
    Health check endpoint
    
    Returns basic service status information.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
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

