"""
User management API endpoints for profile management and user operations.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import structlog

from ...core.database import get_db
from ...core.security import (
    get_current_user, get_current_admin_user, get_current_manager_or_admin,
    require_self_or_admin
)
from ...models.user import User, UserRole, UserStatus
from ...schemas.user import (
    UserResponse, UserUpdate, UserAdminUpdate, UserListResponse,
    ChangePassword, Message, UserStatsResponse
)
from ...services.auth_service import auth_service, AuthenticationError
from ...services.password_service import password_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user's profile."""
    logger.info("👤 Profile requested", user_id=current_user.id)
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update current user's profile."""
    try:
        # Update user fields
        update_data = profile_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info("✅ Profile updated", user_id=current_user.id, fields=list(update_data.keys()))
        
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        db.rollback()
        logger.error("❌ Profile update failed", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile update failed")


@router.post("/me/change-password", response_model=Message)
async def change_my_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Message:
    """Change current user's password."""
    try:
        auth_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
            db
        )
        
        logger.info("✅ Password changed", user_id=current_user.id)
        return Message(message="Password changed successfully")
        
    except AuthenticationError as e:
        logger.warning("❌ Password change failed", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_self_or_admin(user_id)),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get user by ID (self or admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    logger.info("👤 User retrieved", user_id=user_id, requester_id=current_user.id)
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: int,
    profile_data: UserUpdate,
    current_user: User = Depends(require_self_or_admin(user_id)),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update user by ID (self or admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        # Update user fields
        update_data = profile_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info("✅ User updated", user_id=user_id, updater_id=current_user.id)
        return UserResponse.from_orm(user)
        
    except Exception as e:
        db.rollback()
        logger.error("❌ User update failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User update failed")


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    current_user: User = Depends(get_current_manager_or_admin),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """List users with pagination and filtering (manager/admin only)."""
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    logger.info("📋 Users listed", count=len(users), total=total, requester_id=current_user.id)
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.put("/{user_id}/admin", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    admin_data: UserAdminUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Admin update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        # Update user fields (including admin-only fields)
        update_data = admin_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info("✅ Admin user update", user_id=user_id, admin_id=current_user.id)
        return UserResponse.from_orm(user)
        
    except Exception as e:
        db.rollback()
        logger.error("❌ Admin user update failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User update failed")


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Message:
    """Deactivate user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate own account")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.deactivate()
    db.commit()
    
    logger.info("🔒 User deactivated", user_id=user_id, admin_id=current_user.id)
    return Message(message="User deactivated successfully")


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Message:
    """Activate user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.activate()
    db.commit()
    
    logger.info("✅ User activated", user_id=user_id, admin_id=current_user.id)
    return Message(message="User activated successfully")


@router.get("/stats/overview", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserStatsResponse:
    """Get user statistics (admin only)."""
    from datetime import datetime, timedelta
    
    # Get counts
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = db.query(User).filter(User.is_active == False).count()
    pending_verification = db.query(User).filter(User.is_verified == False).count()
    
    # Role counts
    admins = db.query(User).filter(User.role == UserRole.ADMIN).count()
    project_managers = db.query(User).filter(User.role == UserRole.PROJECT_MANAGER).count()
    clients = db.query(User).filter(User.role == UserRole.CLIENT).count()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.query(User).filter(User.created_at >= thirty_days_ago).count()
    
    logger.info("📊 User stats requested", admin_id=current_user.id)
    
    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        pending_verification=pending_verification,
        admins=admins,
        project_managers=project_managers,
        clients=clients,
        recent_registrations=recent_registrations
    ) 