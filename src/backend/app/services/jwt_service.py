"""
JWT service for token generation, validation, and refresh.
Handles all JWT-related operations for authentication.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import structlog

from ..core.config import get_settings
from ..core.database import get_db
from ..models.user import User, RefreshToken

logger = structlog.get_logger(__name__)
settings = get_settings()


class JWTService:
    """
    Service for handling JWT token operations.
    Manages access token and refresh token lifecycle.
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_minutes = settings.REFRESH_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Dictionary containing user data to encode
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.info(
            "🔑 Access token created",
            user_id=data.get("sub"),
            expires_at=expire.isoformat(),
            token_type="access"
        )
        
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int, db: Session) -> str:
        """
        Create a refresh token and store it in the database.
        
        Args:
            user_id: User ID for the token
            db: Database session
            
        Returns:
            Refresh token string
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(minutes=self.refresh_token_expire_minutes)
        
        # Store in database
        db_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        
        logger.info(
            "🔄 Refresh token created",
            user_id=user_id,
            token_id=db_token.id,
            expires_at=expires_at.isoformat()
        )
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access":
                logger.warning("Invalid token type", token_type=payload.get("type"))
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning("Token expired", exp=exp)
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Extract user ID from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID or None if invalid
        """
        payload = self.verify_token(token)
        if payload:
            try:
                return int(payload.get("sub"))
            except (ValueError, TypeError):
                logger.warning("Invalid user ID in token", sub=payload.get("sub"))
        return None
    
    def verify_refresh_token(self, token: str, db: Session) -> Optional[RefreshToken]:
        """
        Verify a refresh token from the database.
        
        Args:
            token: Refresh token string
            db: Database session
            
        Returns:
            RefreshToken object if valid, None otherwise
        """
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False
        ).first()
        
        if not db_token:
            logger.warning("Refresh token not found", token_preview=token[:8] + "...")
            return None
        
        if db_token.is_expired:
            logger.warning("Refresh token expired", token_id=db_token.id)
            return None
        
        return db_token
    
    def refresh_access_token(self, refresh_token: str, db: Session) -> Optional[Dict[str, str]]:
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: Refresh token string
            db: Database session
            
        Returns:
            Dictionary with new access and refresh tokens, or None if invalid
        """
        db_token = self.verify_refresh_token(refresh_token, db)
        if not db_token:
            return None
        
        # Get user
        user = db.query(User).filter(User.id == db_token.user_id).first()
        if not user or not user.is_active:
            logger.warning("User not found or inactive", user_id=db_token.user_id)
            return None
        
        # Create new access token
        access_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "full_name": user.full_name
        }
        new_access_token = self.create_access_token(access_token_data)
        
        # Create new refresh token
        new_refresh_token = self.create_refresh_token(user.id, db)
        
        # Revoke old refresh token
        db_token.revoke()
        db.commit()
        
        logger.info(
            "🔄 Tokens refreshed",
            user_id=user.id,
            old_token_id=db_token.id
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    
    def revoke_refresh_token(self, token: str, db: Session) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token: Refresh token string
            db: Database session
            
        Returns:
            True if revoked successfully, False otherwise
        """
        db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        
        if db_token:
            db_token.revoke()
            db.commit()
            
            logger.info("🔒 Refresh token revoked", token_id=db_token.id)
            return True
        
        return False
    
    def revoke_all_user_tokens(self, user_id: int, db: Session) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            Number of tokens revoked
        """
        tokens = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).all()
        
        count = 0
        for token in tokens:
            token.revoke()
            count += 1
        
        db.commit()
        
        logger.info(
            "🔒 All user tokens revoked",
            user_id=user_id,
            tokens_revoked=count
        )
        
        return count
    
    def cleanup_expired_tokens(self, db: Session) -> int:
        """
        Clean up expired refresh tokens from database.
        
        Args:
            db: Database session
            
        Returns:
            Number of tokens cleaned up
        """
        expired_tokens = db.query(RefreshToken).filter(
            RefreshToken.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_tokens)
        
        for token in expired_tokens:
            db.delete(token)
        
        db.commit()
        
        logger.info("🧹 Expired tokens cleaned up", tokens_removed=count)
        
        return count


# Global JWT service instance
jwt_service = JWTService() 