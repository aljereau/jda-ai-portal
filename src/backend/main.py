"""
JDA AI-Guided Project Portal - Main FastAPI Application
Entry point for the backend API server
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.database import create_tables
from app.api.v1.router import api_router

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan events handler.
    Manages startup and shutdown procedures.
    """
    # Startup
    logger.info("🚀 Starting JDA AI Portal Backend", version="1.0.0")
    
    try:
        # Initialize database tables
        await create_tables()
        logger.info("✅ Database tables initialized")
        
        # Additional startup tasks can be added here
        # - Connect to external services
        # - Initialize caches
        # - Load ML models
        
        logger.info("🎯 Backend startup completed successfully")
        
    except Exception as e:
        logger.error("❌ Failed to start backend", error=str(e), exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down JDA AI Portal Backend")
    
    # Cleanup tasks
    # - Close database connections
    # - Close external service connections
    # - Save caches
    
    logger.info("✅ Backend shutdown completed")


# Create FastAPI application instance
app = FastAPI(
    title="JDA AI-Guided Project Portal API",
    description="""
    Enterprise-grade AI-guided project management portal for JDA's consultancy operations.
    
    ## Features
    * 🤖 AI-powered proposal generation
    * 📊 Dynamic project management hubs
    * 🔐 Enterprise authentication & authorization
    * 📝 Meeting transcription integration
    * 🔄 Real-time collaboration tools
    
    ## Phases
    * **Intake & Proposal**: Client onboarding and proposal generation
    * **Discovery**: Requirements gathering and project scoping
    * **Design & Build**: Development and implementation
    * **Deployment**: Go-live and support
    """,
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Log all incoming requests with correlation IDs for tracing.
    """
    import uuid
    correlation_id = str(uuid.uuid4())
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    # Log incoming request
    logger.info(
        "🌐 Incoming request",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id,
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host if request.client else None,
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    logger.info(
        "📤 Response sent",
        status_code=response.status_code,
        correlation_id=correlation_id,
    )
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        "💥 Unhandled exception",
        error=str(exc),
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "correlation_id": correlation_id,
            "error_type": "InternalServerError",
        },
        headers={"X-Correlation-ID": correlation_id},
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "service": "JDA AI Portal Backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    """
    Development server entry point.
    Production deployment should use a proper ASGI server.
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info",
        access_log=True,
    ) 