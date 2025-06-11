"""
Enhanced role-based permission system for JDA AI Portal.
Provides granular permissions and advanced RBAC functionality.
"""
from enum import Enum
from typing import Set, Dict, Callable, Any
from functools import wraps
from fastapi import HTTPException, status
import structlog

from ..models.user import User, UserRole

logger = structlog.get_logger(__name__)


class Permission(str, Enum):
    """Granular permissions for the system."""
    
    # User Management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # Project Management (future)
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    PROJECT_ADMIN = "project:admin"
    
    # Client Management (future)
    CLIENT_READ = "client:read"
    CLIENT_WRITE = "client:write"
    CLIENT_DELETE = "client:delete"
    CLIENT_ADMIN = "client:admin"
    
    # AI Features (future)
    AI_USE = "ai:use"
    AI_ADMIN = "ai:admin"
    
    # System Administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_ADMIN = "system:admin"


# Role-based permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.CLIENT: {
        Permission.USER_READ,  # Can read own profile
        Permission.PROJECT_READ,  # Can read assigned projects
    },
    
    UserRole.PROJECT_MANAGER: {
        Permission.USER_READ,
        Permission.USER_WRITE,  # Can manage team members
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
    },
    
    UserRole.ADMIN: {
        # Admins get all permissions
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_ADMIN,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_ADMIN,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_ADMIN,
    }
}


class PermissionManager:
    """Manages user permissions and access control."""
    
    @staticmethod
    def get_user_permissions(user: User) -> Set[Permission]:
        """
        Get all permissions for a user based on their role.
        
        Args:
            user: User object
            
        Returns:
            Set of permissions for the user
        """
        return ROLE_PERMISSIONS.get(user.role, set())
    
    @staticmethod
    def user_has_permission(user: User, permission: Permission) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user: User object
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user or not user.is_active:
            return False
        
        user_permissions = PermissionManager.get_user_permissions(user)
        has_permission = permission in user_permissions
        
        logger.debug(
            "Permission check",
            user_id=user.id,
            permission=permission.value,
            result=has_permission,
            user_role=user.role.value
        )
        
        return has_permission
    
    @staticmethod
    def user_has_any_permission(user: User, permissions: Set[Permission]) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user: User object
            permissions: Set of permissions to check
            
        Returns:
            True if user has at least one permission, False otherwise
        """
        if not user or not user.is_active:
            return False
        
        user_permissions = PermissionManager.get_user_permissions(user)
        return bool(user_permissions.intersection(permissions))
    
    @staticmethod
    def user_has_all_permissions(user: User, permissions: Set[Permission]) -> bool:
        """
        Check if user has all of the specified permissions.
        
        Args:
            user: User object
            permissions: Set of permissions to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        if not user or not user.is_active:
            return False
        
        user_permissions = PermissionManager.get_user_permissions(user)
        return permissions.issubset(user_permissions)
    
    @staticmethod
    def can_manage_user(manager: User, target_user: User) -> bool:
        """
        Check if manager can manage the target user.
        
        Rules:
        - Admins can manage anyone except other admins
        - Project managers can manage clients
        - Users cannot manage themselves for certain operations
        
        Args:
            manager: User attempting to manage
            target_user: User being managed
            
        Returns:
            True if management is allowed, False otherwise
        """
        if not manager or not manager.is_active or not target_user:
            return False
        
        # Admins can manage anyone except other admins
        if manager.is_admin:
            if target_user.is_admin and manager.id != target_user.id:
                return False
            return True
        
        # Project managers can manage clients
        if manager.is_project_manager:
            return target_user.is_client
        
        return False


def require_permission(permission: Permission):
    """
    Decorator factory for permission-based access control.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function that checks user permission
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from function parameters
            current_user = None
            
            # Look for current_user in kwargs
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                # Look for current_user in args (dependency injection)
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user:
                logger.warning("Permission check failed: no user found")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not PermissionManager.user_has_permission(current_user, permission):
                logger.warning(
                    "Permission denied",
                    user_id=current_user.id,
                    required_permission=permission.value,
                    user_role=current_user.role.value
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission.value}' required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator factory for multiple permission options.
    User needs ANY of the specified permissions.
    
    Args:
        permissions: Required permissions (user needs any one)
        
    Returns:
        Decorator function that checks user permissions
    """
    permission_set = set(permissions)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from function parameters
            current_user = None
            
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not PermissionManager.user_has_any_permission(current_user, permission_set):
                logger.warning(
                    "Permission denied",
                    user_id=current_user.id,
                    required_permissions=[p.value for p in permissions],
                    user_role=current_user.role.value
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these permissions required: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_all_permissions(*permissions: Permission):
    """
    Decorator factory for multiple required permissions.
    User needs ALL of the specified permissions.
    
    Args:
        permissions: Required permissions (user needs all)
        
    Returns:
        Decorator function that checks user permissions
    """
    permission_set = set(permissions)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from function parameters
            current_user = None
            
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not PermissionManager.user_has_all_permissions(current_user, permission_set):
                logger.warning(
                    "Permission denied",
                    user_id=current_user.id,
                    required_permissions=[p.value for p in permissions],
                    user_role=current_user.role.value
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All of these permissions required: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global permission manager instance
permission_manager = PermissionManager() 