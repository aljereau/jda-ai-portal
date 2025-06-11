"""
Admin user management endpoints for system administration.
Provides comprehensive admin tools for user management and system oversight.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import structlog

from ...core.database import get_db
from ...core.security import get_current_admin_user
from ...core.permissions import Permission, PermissionManager
from ...models.user import User, UserRole, UserStatus, RefreshToken
from ...schemas.user import (
    UserResponse, UserAdminUpdate, UserListResponse, Message,
    UserStatsResponse, UserCreate
)
from ...services.auth_service import auth_service, AuthenticationError
from ...services.jwt_service import jwt_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Management"])


@router.get("/users/advanced", response_model=UserListResponse)
async def admin_list_users_advanced(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    search: Optional[str] = Query(None, description="Search by email, name, or company"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """Advanced user listing with comprehensive filtering and sorting (admin only)."""
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term)) |
            (User.company.ilike(search_term))
        )
    
    # Apply sorting
    if hasattr(User, sort_by):
        sort_column = getattr(User, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    logger.info(
        "👑 Admin advanced user list",
        count=len(users),
        total=total,
        admin_id=current_user.id,
        filters={
            "role": role.value if role else None,
            "status": status.value if status else None,
            "search": search
        }
    )
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/users/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Create new user as admin (admin only)."""
    try:
        # Admin can create users with any role
        user, tokens = auth_service.register_user(user_data, db)
        
        # Note: tokens are generated but not returned to admin for security
        
        logger.info(
            "👑 Admin user creation",
            created_user_id=user.id,
            created_user_email=user.email,
            created_user_role=user.role.value,
            admin_id=current_user.id
        )
        
        return UserResponse.from_orm(user)
        
    except AuthenticationError as e:
        logger.warning("❌ Admin user creation failed", error=str(e), admin_id=current_user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def admin_change_user_role(
    user_id: int,
    new_role: UserRole,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Change user role (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change own role")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    old_role = user.role
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    logger.info("👑 Admin role change", target_user_id=user_id, old_role=old_role.value, new_role=new_role.value)
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def admin_change_user_status(
    user_id: int,
    new_status: UserStatus,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Change user status (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change own status")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.status = new_status
    user.is_active = new_status == UserStatus.ACTIVE
    db.commit()
    db.refresh(user)
    
    logger.info("👑 Admin status change", target_user_id=user_id, new_status=new_status.value)
    return UserResponse.from_orm(user)


@router.post("/users/{user_id}/verify", response_model=Message)
async def admin_verify_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Message:
    """Manually verify user email (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.is_verified:
        return Message(message="User is already verified")
    
    user.verify_email()
    db.commit()
    
    logger.info(
        "👑 Admin user verification",
        target_user_id=user_id,
        admin_id=current_user.id
    )
    
    return Message(message="User verified successfully")


@router.post("/users/{user_id}/force-logout", response_model=Message)
async def admin_force_logout_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Message:
    """Force logout user from all sessions (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    sessions_revoked = jwt_service.revoke_all_user_tokens(user_id, db)
    
    logger.info("👑 Admin force logout", target_user_id=user_id, sessions_revoked=sessions_revoked)
    return Message(message=f"User logged out from {sessions_revoked} session(s)")


@router.get("/users/{user_id}/sessions", response_model=dict)
async def admin_get_user_sessions(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get user's active sessions (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get active refresh tokens
    active_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()
    
    sessions = []
    for token in active_tokens:
        sessions.append({
            "token_id": token.id,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "is_expired": token.is_expired
        })
    
    logger.info(
        "👑 Admin session query",
        target_user_id=user_id,
        active_sessions=len(sessions),
        admin_id=current_user.id
    )
    
    return {
        "user_id": user_id,
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@router.get("/stats/system", response_model=dict)
async def admin_get_system_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get system statistics (admin only)."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Role distribution
    role_stats = {}
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        role_stats[role.value] = count
    
    logger.info("👑 Admin system stats requested", admin_id=current_user.id)
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "role_distribution": role_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/maintenance/cleanup-tokens", response_model=Message)
async def admin_cleanup_expired_tokens(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Message:
    """Cleanup expired refresh tokens (admin only)."""
    cleaned_count = jwt_service.cleanup_expired_tokens(db)
    
    logger.info(
        "👑 Admin token cleanup",
        tokens_cleaned=cleaned_count,
        admin_id=current_user.id
    )
    
    return Message(message=f"Cleaned up {cleaned_count} expired tokens") 