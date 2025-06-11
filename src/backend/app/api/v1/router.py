"""
Main API router for JDA AI Portal v1 endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from .auth import router as auth_router
from .users import router as users_router

settings = get_settings()

# Create main API router
api_router = APIRouter()

# Include authentication and user management routers
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(users_router, tags=["User Management"])


@api_router.get("/", tags=["System"])
async def root():
    """
    API root endpoint with basic information.
    """
    return {
        "message": "JDA AI-Guided Project Portal API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.is_development else None,
    }


@api_router.get("/status", tags=["System"])
async def api_status(db: Session = Depends(get_db)):
    """
    Detailed API status including database connectivity.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "api_status": "operational",
        "database_status": db_status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "authentication": "operational",
            "user_management": "operational", 
            "jwt_tokens": "enabled",
            "role_based_access": "enabled",
            "ai_integration": bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY),
            "file_uploads": True,
            "real_time_features": True,
        },
    }


# Placeholder for future route modules
# These will be implemented in subsequent blocks
"""
Future endpoints to be added:

# Authentication & Users
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Project Management
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(clients.router, prefix="/clients", tags=["Clients"])

# AI Features
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["Proposals"])

# Integrations
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
""" 