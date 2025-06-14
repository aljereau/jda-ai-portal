"""
Database configuration and session management.
Handles SQLAlchemy setup, connection management, and model imports.
"""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jda_portal.db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=settings.is_development,  # Log SQL queries in development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for ORM models
Base = declarative_base()

# Metadata for database introspection
metadata = MetaData()


async def create_tables():
    """
    Create all database tables.
    This will be called during application startup.
    """
    try:
        logger.info("🗄️ Creating database tables")
        
        # Import all models here to ensure they're registered
        from app.models import user, project, client  # noqa: F401
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error("❌ Failed to create database tables", error=str(e))
        raise


def get_db() -> Generator:
    """
    Dependency to get database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_database_connection():
    """
    Check if database connection is working.
    """
    try:
        db = SessionLocal()
        # Try to execute a simple query
        db.execute("SELECT 1")
        db.close()
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.error("❌ Database connection failed", error=str(e))
        return False


def drop_tables() -> None:
    """
    Drop all database tables.
    Used for testing and development reset.
    """
    Base.metadata.drop_all(bind=engine)


def init_database() -> None:
    """
    Initialize database with tables and default data.
    """
    create_tables()
    print("Database initialized successfully!") 