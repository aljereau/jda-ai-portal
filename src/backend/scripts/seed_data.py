"""
Database seed script for JDA AI Portal.
Creates sample users with different roles for testing authentication and RBAC.
"""
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import structlog

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.models.user import User, UserRole, UserStatus
from app.services.password_service import password_service

logger = structlog.get_logger(__name__)
settings = get_settings()


def create_sample_users(db: Session) -> None:
    """Create sample users for testing."""
    
    # Sample user data
    sample_users = [
        {
            "email": "admin@jda-portal.com",
            "password": "AdminPass123!",
            "first_name": "JDA",
            "last_name": "Administrator",
            "role": UserRole.ADMIN,
            "company": "JDA Consulting",
            "is_verified": True,
            "bio": "System administrator for JDA AI Portal"
        },
        {
            "email": "pm@jda-portal.com", 
            "password": "ProjectManager123!",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "role": UserRole.PROJECT_MANAGER,
            "company": "JDA Consulting",
            "phone_number": "+1-555-0123",
            "is_verified": True,
            "bio": "Senior project manager with 8+ years experience"
        },
        {
            "email": "client1@testcompany.com",
            "password": "ClientPass123!",
            "first_name": "Michael",
            "last_name": "Chen",
            "role": UserRole.CLIENT,
            "company": "Tech Innovations Inc",
            "phone_number": "+1-555-0456",
            "is_verified": True,
            "bio": "CTO looking for AI integration solutions"
        },
        {
            "email": "client2@smallbiz.com",
            "password": "ClientPass123!",
            "first_name": "Emily",
            "last_name": "Rodriguez",
            "role": UserRole.CLIENT,
            "company": "Small Business Solutions",
            "phone_number": "+1-555-0789",
            "is_verified": False,
            "bio": "Business owner seeking automation"
        },
        {
            "email": "pm2@jda-portal.com",
            "password": "ProjectManager123!",
            "first_name": "David",
            "last_name": "Williams",
            "role": UserRole.PROJECT_MANAGER,
            "company": "JDA Consulting",
            "phone_number": "+1-555-0321",
            "is_verified": True,
            "bio": "Technical project manager specializing in AI projects"
        },
        {
            "email": "client3@enterprise.com",
            "password": "ClientPass123!",
            "first_name": "Jennifer",
            "last_name": "Thompson",
            "role": UserRole.CLIENT,
            "company": "Enterprise Corp",
            "phone_number": "+1-555-0654",
            "is_verified": True,
            "bio": "VP of Operations driving digital transformation"
        },
        {
            "email": "suspended@test.com",
            "password": "TestPass123!",
            "first_name": "Suspended",
            "last_name": "User",
            "role": UserRole.CLIENT,
            "company": "Test Company",
            "status": UserStatus.SUSPENDED,
            "is_active": False,
            "is_verified": True,
            "bio": "Test user for suspended account testing"
        }
    ]
    
    created_users = []
    
    for user_data in sample_users:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            logger.info(f"User {user_data['email']} already exists, skipping")
            continue
        
        # Hash password
        password = user_data.pop("password")
        hashed_password = password_service.hash_password(password)
        
        # Create user
        user = User(
            hashed_password=hashed_password,
            status=user_data.get("status", UserStatus.ACTIVE),
            is_active=user_data.get("is_active", True),
            **user_data
        )
        
        db.add(user)
        created_users.append(user)
        
        logger.info(
            f"Created user: {user.email} ({user.role.value})",
            email=user.email,
            role=user.role.value,
            company=user.company
        )
    
    db.commit()
    
    # Refresh users to get IDs
    for user in created_users:
        db.refresh(user)
    
    logger.info(f"✅ Created {len(created_users)} sample users")
    
    return created_users


def print_user_credentials():
    """Print sample user credentials for testing."""
    
    credentials = [
        ("Admin User", "admin@jda-portal.com", "AdminPass123!", "Full system access"),
        ("Project Manager 1", "pm@jda-portal.com", "ProjectManager123!", "User and project management"),
        ("Project Manager 2", "pm2@jda-portal.com", "ProjectManager123!", "Technical project management"),
        ("Client 1 (Verified)", "client1@testcompany.com", "ClientPass123!", "Verified client account"),
        ("Client 2 (Unverified)", "client2@smallbiz.com", "ClientPass123!", "Unverified client account"),
        ("Client 3 (Enterprise)", "client3@enterprise.com", "ClientPass123!", "Enterprise client account"),
        ("Suspended User", "suspended@test.com", "TestPass123!", "Suspended account for testing")
    ]
    
    print("\n" + "="*80)
    print("🔐 JDA AI PORTAL - SAMPLE USER CREDENTIALS")
    print("="*80)
    print(f"{'Name':<20} {'Email':<25} {'Password':<20} {'Description'}")
    print("-"*80)
    
    for name, email, password, description in credentials:
        print(f"{name:<20} {email:<25} {password:<20} {description}")
    
    print("-"*80)
    print("🌐 Test these credentials at: http://localhost:8000/docs")
    print("📊 Admin Dashboard: /admin/stats/system")
    print("👤 User Profile: /users/me")
    print("🔄 Token Refresh: /auth/refresh")
    print("="*80 + "\n")


def main():
    """Main function to seed database."""
    try:
        # Create database engine
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG_SQL if hasattr(settings, 'DEBUG_SQL') else False
        )
        
        # Create tables (if they don't exist)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
        # Create session
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Create sample users
            logger.info("🌱 Starting database seeding...")
            created_users = create_sample_users(db)
            
            # Print credentials for testing
            print_user_credentials()
            
            logger.info("✅ Database seeding completed successfully!")
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Database seeding failed: {str(e)}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"💥 Failed to seed database: {str(e)}")
        return False


if __name__ == "__main__":
    import sys
    sys.path.append(".")
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    success = main()
    sys.exit(0 if success else 1) 