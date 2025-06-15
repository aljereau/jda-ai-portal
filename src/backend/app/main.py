"""
JDA Proposal Maker - Main FastAPI Application

This module serves as the main entry point for the FastAPI application,
setting up all routes, middleware, and core configurations.
"""

from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from pathlib import Path

# Add the app directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

# Import API routers
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.proposals import router as proposals_router
from api.v1.client_portal import router as client_portal_router
from api.v1.team_dashboard import router as team_dashboard_router
from api.v1.file_management import router as file_management_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="JDA Proposal Maker API",
    description="AI-powered proposal generation and management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(proposals_router, prefix="/api/v1/proposals", tags=["Proposals"])
app.include_router(client_portal_router, prefix="/api/v1", tags=["Client Portal"])
app.include_router(team_dashboard_router, prefix="/api/v1", tags=["Team Dashboard"])
app.include_router(file_management_router, prefix="/api/v1", tags=["File Management"])

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint returning API information."""
    return {
        "message": "JDA Proposal Maker API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring and testing."""
    try:
        # You can add more health checks here (database, external services, etc.)
        return {
            "status": "healthy",
            "service": "JDA Proposal Maker API",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error"
        }
    )

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting JDA Proposal Maker API...")
    logger.info("API documentation available at /docs")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down JDA Proposal Maker API...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 