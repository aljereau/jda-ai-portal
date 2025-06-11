"""
Security dependencies for FastAPI route protection.
Provides JWT authentication and role-based access control.
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog

from .database import get_db
from ..models.user import User, UserRole
from ..services.auth_service import auth_service
from ..services.jwt_service import jwt_service

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        logger.warning("Authentication failed: no credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Get user from token
        user = auth_service.get_current_user(credentials.credentials, db)
        
        if not user:
            logger.warning("Authentication failed: invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning("Authentication failed: user inactive", user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user account",
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (alias for get_current_user).
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user with admin role.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current admin user
        
    Raises:
        HTTPException: If user doesn't have admin role
    """
    if not current_user.is_admin:
        logger.warning(
            "Authorization failed: admin required",
            user_id=current_user.id,
            user_role=current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_current_manager_or_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user with project manager or admin role.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current manager or admin user
        
    Raises:
        HTTPException: If user doesn't have sufficient privileges
    """
    if not current_user.can_manage_users:
        logger.warning(
            "Authorization failed: manager or admin required",
            user_id=current_user.id,
            user_role=current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project manager or admin privileges required"
        )
    
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not auth_service.verify_user_permissions(current_user, required_role):
            logger.warning(
                "Authorization failed: insufficient role",
                user_id=current_user.id,
                user_role=current_user.role.value,
                required_role=required_role.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher required"
            )
        
        return current_user
    
    return role_checker


def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require user to have verified email.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current verified user
        
    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.is_verified:
        logger.warning(
            "Authorization failed: email verification required",
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user


def require_self_or_admin(user_id: int):
    """
    Dependency factory for self-or-admin access control.
    Allows users to access their own data or admins to access any data.
    
    Args:
        user_id: Target user ID
        
    Returns:
        Dependency function that checks access permissions
    """
    async def access_checker(current_user: User = Depends(get_current_user)) -> User:
        # Allow admin access
        if current_user.is_admin:
            return current_user
        
        # Allow self access
        if current_user.id == user_id:
            return current_user
        
        logger.warning(
            "Authorization failed: self or admin access required",
            current_user_id=current_user.id,
            target_user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: can only access own data"
        )
    
    return access_checker


def optional_auth(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns user if valid token provided, None otherwise.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        user = auth_service.get_current_user(credentials.credentials, db)
        return user if user and user.is_active else None
    except Exception:
        return None


# Dependency aliases for common use cases
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
CurrentManagerOrAdmin = Annotated[User, Depends(get_current_manager_or_admin)]
OptionalUser = Annotated[Optional[User], Depends(optional_auth)]

# Role-based dependencies
RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
RequireManager = Annotated[User, Depends(require_role(UserRole.PROJECT_MANAGER))]
RequireClient = Annotated[User, Depends(require_role(UserRole.CLIENT))] 