"""
Authentication service for user registration, login, and authentication management.
Combines JWT and password services for comprehensive authentication functionality.
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import structlog

from ..models.user import User, UserRole, UserStatus
from ..schemas.user import UserCreate, UserLogin, UserResponse, UserLoginResponse
from .jwt_service import jwt_service
from .password_service import password_service
from ..core.database import get_db

logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthService:
    """
    Service for handling user authentication operations.
    Manages user registration, login, token refresh, and authentication validation.
    """
    
    def __init__(self):
        self.jwt_service = jwt_service
        self.password_service = password_service
    
    def register_user(self, user_data: UserCreate, db: Session) -> Tuple[User, Dict[str, str]]:
        """
        Register a new user with authentication tokens.
        
        Args:
            user_data: User registration data
            db: Database session
            
        Returns:
            Tuple of (User object, tokens dictionary)
            
        Raises:
            AuthenticationError: If registration fails
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                logger.warning("Registration failed: email already exists", email=user_data.email)
                raise AuthenticationError("Email already registered")
            
            # Validate password strength
            is_strong, issues = self.password_service.is_password_strong(user_data.password)
            if not is_strong:
                logger.warning("Registration failed: weak password", issues=issues)
                raise AuthenticationError(f"Password requirements not met: {', '.join(issues)}")
            
            # Hash password
            hashed_password = self.password_service.hash_password(user_data.password)
            
            # Create user
            db_user = User(
                email=user_data.email,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone_number=user_data.phone_number,
                company=user_data.company,
                bio=user_data.bio,
                timezone=user_data.timezone,
                role=user_data.role,
                status=UserStatus.ACTIVE,
                is_active=True,
                is_verified=False  # Will be verified later via email
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Generate authentication tokens
            tokens = self._generate_user_tokens(db_user, db)
            
            logger.info(
                "✅ User registered successfully",
                user_id=db_user.id,
                email=db_user.email,
                role=db_user.role.value
            )
            
            return db_user, tokens
            
        except IntegrityError as e:
            db.rollback()
            logger.error("Database integrity error during registration", error=str(e))
            raise AuthenticationError("Registration failed due to data conflict")
        except Exception as e:
            db.rollback()
            logger.error("Unexpected error during registration", error=str(e))
            raise AuthenticationError(f"Registration failed: {str(e)}")
    
    def authenticate_user(self, login_data: UserLogin, db: Session) -> Tuple[User, Dict[str, str]]:
        """
        Authenticate user with email and password.
        
        Args:
            login_data: User login credentials
            db: Database session
            
        Returns:
            Tuple of (User object, tokens dictionary)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Get user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            logger.warning("Authentication failed: user not found", email=login_data.email)
            raise AuthenticationError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            logger.warning("Authentication failed: user inactive", user_id=user.id)
            raise AuthenticationError("Account is inactive")
        
        # Check user status
        if user.status == UserStatus.SUSPENDED:
            logger.warning("Authentication failed: user suspended", user_id=user.id)
            raise AuthenticationError("Account is suspended")
        
        # Verify password
        if not self.password_service.verify_password(login_data.password, user.hashed_password):
            logger.warning("Authentication failed: invalid password", user_id=user.id)
            raise AuthenticationError("Invalid email or password")
        
        # Update last login
        user.update_last_login()
        db.commit()
        
        # Generate authentication tokens
        tokens = self._generate_user_tokens(user, db)
        
        logger.info(
            "✅ User authenticated successfully",
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        
        return user, tokens
    
    def refresh_user_tokens(self, refresh_token: str, db: Session) -> Optional[Dict[str, str]]:
        """
        Refresh user authentication tokens.
        
        Args:
            refresh_token: Refresh token string
            db: Database session
            
        Returns:
            New tokens dictionary or None if invalid
        """
        tokens = self.jwt_service.refresh_access_token(refresh_token, db)
        
        if tokens:
            logger.info("✅ Tokens refreshed successfully")
        else:
            logger.warning("❌ Token refresh failed")
        
        return tokens
    
    def logout_user(self, refresh_token: str, db: Session) -> bool:
        """
        Logout user by revoking refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
            db: Database session
            
        Returns:
            True if logout successful, False otherwise
        """
        success = self.jwt_service.revoke_refresh_token(refresh_token, db)
        
        if success:
            logger.info("✅ User logged out successfully")
        else:
            logger.warning("❌ Logout failed")
        
        return success
    
    def logout_all_sessions(self, user_id: int, db: Session) -> int:
        """
        Logout user from all sessions by revoking all refresh tokens.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            Number of tokens revoked
        """
        count = self.jwt_service.revoke_all_user_tokens(user_id, db)
        
        logger.info(
            "✅ All user sessions logged out",
            user_id=user_id,
            sessions_revoked=count
        )
        
        return count
    
    def get_current_user(self, token: str, db: Session) -> Optional[User]:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            db: Database session
            
        Returns:
            User object or None if invalid
        """
        user_id = self.jwt_service.get_user_id_from_token(token)
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            logger.warning("Current user lookup failed", user_id=user_id)
            return None
        
        return user
    
    def change_password(self, user_id: int, current_password: str, new_password: str, db: Session) -> bool:
        """
        Change user password with validation.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            db: Database session
            
        Returns:
            True if password changed successfully, False otherwise
            
        Raises:
            AuthenticationError: If password change fails
        """
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify current password
        if not self.password_service.verify_password(current_password, user.hashed_password):
            logger.warning("Password change failed: invalid current password", user_id=user_id)
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password strength
        is_strong, issues = self.password_service.is_password_strong(new_password)
        if not is_strong:
            logger.warning("Password change failed: weak new password", user_id=user_id, issues=issues)
            raise AuthenticationError(f"New password requirements not met: {', '.join(issues)}")
        
        # Check if new password is different from current
        if self.password_service.verify_password(new_password, user.hashed_password):
            logger.warning("Password change failed: same as current", user_id=user_id)
            raise AuthenticationError("New password must be different from current password")
        
        # Hash new password
        hashed_password = self.password_service.hash_password(new_password)
        
        # Update password
        user.hashed_password = hashed_password
        db.commit()
        
        # Revoke all existing tokens to force re-authentication
        self.logout_all_sessions(user_id, db)
        
        logger.info("✅ Password changed successfully", user_id=user_id)
        
        return True
    
    def verify_user_permissions(self, user: User, required_role: UserRole) -> bool:
        """
        Verify if user has required role permissions.
        
        Args:
            user: User object
            required_role: Required role level
            
        Returns:
            True if user has sufficient permissions
        """
        role_hierarchy = {
            UserRole.CLIENT: 1,
            UserRole.PROJECT_MANAGER: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        has_permission = user_level >= required_level
        
        if not has_permission:
            logger.warning(
                "Permission denied",
                user_id=user.id,
                user_role=user.role.value,
                required_role=required_role.value
            )
        
        return has_permission
    
    def _generate_user_tokens(self, user: User, db: Session) -> Dict[str, str]:
        """
        Generate JWT tokens for authenticated user.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Dictionary with access and refresh tokens
        """
        # Create access token data
        access_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "full_name": user.full_name
        }
        
        # Generate tokens
        access_token = self.jwt_service.create_access_token(access_token_data)
        refresh_token = self.jwt_service.create_refresh_token(user.id, db)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


# Global authentication service instance
auth_service = AuthService() 