"""
Pydantic schemas for user data validation and serialization.
Handles request/response models for user authentication and management.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
import re

from ..models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")
    phone_number: Optional[str] = Field(None, max_length=20, description="User's phone number")
    company: Optional[str] = Field(None, max_length=200, description="User's company")
    bio: Optional[str] = Field(None, max_length=1000, description="User biography")
    timezone: str = Field("UTC", max_length=50, description="User's timezone")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if v is not None:
            # Basic phone number validation (digits, spaces, hyphens, parentheses, plus)
            if not re.match(r'^[\+]?[\d\s\-\(\)]+$', v):
                raise ValueError('Invalid phone number format')
        return v
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate name fields."""
        if not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip()


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="User's password (min 8 characters)"
    )
    role: UserRole = Field(UserRole.CLIENT, description="User role")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=1000)
    timezone: Optional[str] = Field(None, max_length=50)
    profile_picture_url: Optional[str] = Field(None, max_length=500)
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if v is not None:
            if not re.match(r'^[\+]?[\d\s\-\(\)]+$', v):
                raise ValueError('Invalid phone number format')
        return v
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate name fields."""
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip() if v else v


class UserAdminUpdate(UserUpdate):
    """Schema for admin user updates (includes role and status)."""
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response data."""
    id: int
    role: UserRole
    status: UserStatus
    is_active: bool
    is_verified: bool
    profile_picture_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserLoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")


class ChangePassword(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="New password"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="New password"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class Message(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message")


class UserStatsResponse(BaseModel):
    """Schema for user statistics (admin endpoint)."""
    total_users: int
    active_users: int
    inactive_users: int
    pending_verification: int
    admins: int
    project_managers: int
    clients: int
    recent_registrations: int  # Last 30 days 