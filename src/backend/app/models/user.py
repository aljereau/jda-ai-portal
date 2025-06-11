"""
User model for JDA AI Portal authentication system.
Implements comprehensive user management with roles and relationships.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class UserRole(str, enum.Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"  
    CLIENT = "client"


class UserStatus(str, enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Primary key identifier
        email: Unique email address for login
        hashed_password: Bcrypt hashed password
        first_name: User's first name
        last_name: User's last name
        role: User role for RBAC (admin, project_manager, client)
        status: Account status (active, inactive, suspended, pending_verification)
        is_active: Quick active status check
        is_verified: Email verification status
        last_login: Timestamp of last successful login
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
        profile_picture_url: Optional profile picture URL
        phone_number: Optional phone number
        company: Optional company affiliation
        bio: Optional user biography
        timezone: User's timezone preference
        projects: Relationship to user's projects
        created_projects: Projects created by this user
    """
    
    __tablename__ = "users"
    
    # Primary Fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    profile_picture_url = Column(String(500), nullable=True)
    phone_number = Column(String(20), nullable=True)
    company = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Role and Status
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships (to be implemented in future phases)
    # projects = relationship("Project", secondary="project_users", back_populates="members")
    # created_projects = relationship("Project", back_populates="created_by")
    # client_profile = relationship("Client", back_populates="user", uselist=False)
    
    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_project_manager(self) -> bool:
        """Check if user has project manager role."""
        return self.role == UserRole.PROJECT_MANAGER
    
    @property
    def is_client(self) -> bool:
        """Check if user has client role."""
        return self.role == UserRole.CLIENT
    
    @property
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    
    @property
    def can_create_projects(self) -> bool:
        """Check if user can create projects."""
        return self.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    
    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.status = UserStatus.INACTIVE
    
    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.status = UserStatus.ACTIVE
    
    def suspend(self) -> None:
        """Suspend the user account."""
        self.is_active = False
        self.status = UserStatus.SUSPENDED
    
    def verify_email(self) -> None:
        """Mark user email as verified."""
        self.is_verified = True
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE


class RefreshToken(Base):
    """
    Refresh token model for JWT token management.
    Stores refresh tokens for secure token renewal.
    """
    
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", backref="refresh_tokens")
    
    def __repr__(self) -> str:
        """String representation of RefreshToken."""
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if refresh token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if refresh token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True 