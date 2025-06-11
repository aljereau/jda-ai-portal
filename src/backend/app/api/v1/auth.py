"""
Authentication API endpoints for user registration, login, and token management.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from ...core.database import get_db
from ...core.security import get_current_user, optional_auth
from ...models.user import User
from ...schemas.user import (
    UserCreate, UserLogin, UserLoginResponse, UserResponse,
    TokenRefresh, TokenResponse, Message
)
from ...services.auth_service import auth_service, AuthenticationError

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> UserLoginResponse:
    """Register a new user account."""
    try:
        user, tokens = auth_service.register_user(user_data, db)
        
        logger.info("✅ User registration successful", user_id=user.id, email=user.email)
        
        return UserLoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            user=UserResponse.from_orm(user)
        )
        
    except AuthenticationError as e:
        logger.warning("❌ User registration failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=UserLoginResponse)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)) -> UserLoginResponse:
    """Authenticate user with email and password."""
    try:
        user, tokens = auth_service.authenticate_user(login_data, db)
        
        logger.info("✅ User login successful", user_id=user.id)
        
        return UserLoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            user=UserResponse.from_orm(user)
        )
        
    except AuthenticationError as e:
        logger.warning("❌ User login failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(token_data: TokenRefresh, db: Session = Depends(get_db)) -> TokenResponse:
    """Refresh access token using refresh token."""
    tokens = auth_service.refresh_user_tokens(token_data.refresh_token, db)
    
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    return TokenResponse(**tokens)


@router.post("/logout", response_model=Message)
async def logout_user(
    token_data: TokenRefresh,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Message:
    """Logout user by revoking refresh token."""
    auth_service.logout_user(token_data.refresh_token, db)
    logger.info("✅ User logout successful", user_id=current_user.id)
    return Message(message="Logout successful")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.from_orm(current_user) 