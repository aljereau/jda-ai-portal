"""
Password service for secure password hashing and verification.
Uses bcrypt for password security with configurable rounds.
"""
from typing import Union
import bcrypt
import structlog
from ..core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class PasswordService:
    """
    Service for handling password operations.
    Provides secure password hashing and verification using bcrypt.
    """
    
    def __init__(self, rounds: int = 12):
        """
        Initialize password service.
        
        Args:
            rounds: Number of bcrypt rounds (default: 12, recommended: 10-15)
        """
        self.rounds = rounds
        logger.info("🔐 Password service initialized", bcrypt_rounds=rounds)
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Convert password to bytes
        password_bytes = password.encode('utf-8')
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Convert back to string for storage
        hashed_password = hashed.decode('utf-8')
        
        logger.info("🔒 Password hashed successfully")
        
        return hashed_password
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Stored bcrypt hash
            
        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed_password:
            logger.warning("Password verification failed: empty password or hash")
            return False
        
        try:
            # Convert to bytes
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verify password
            is_valid = bcrypt.checkpw(password_bytes, hashed_bytes)
            
            if is_valid:
                logger.info("✅ Password verification successful")
            else:
                logger.warning("❌ Password verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error("Password verification error", error=str(e))
            return False
    
    def is_password_strong(self, password: str) -> tuple[bool, list[str]]:
        """
        Check if password meets strength requirements.
        
        Args:
            password: Password to check
            
        Returns:
            Tuple of (is_strong, list_of_issues)
        """
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            issues.append("Password must be less than 128 characters long")
        
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one digit")
        
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        if not any(c in special_chars for c in password):
            issues.append("Password must contain at least one special character")
        
        # Check for common patterns
        common_patterns = [
            "password", "123456", "qwerty", "admin", "user",
            "letmein", "welcome", "monkey", "dragon"
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                issues.append(f"Password cannot contain common pattern: {pattern}")
                break
        
        is_strong = len(issues) == 0
        
        if is_strong:
            logger.info("✅ Password strength check passed")
        else:
            logger.warning("⚠️ Password strength check failed", issues=issues)
        
        return is_strong, issues
    
    def generate_password_reset_token(self) -> str:
        """
        Generate a secure token for password reset.
        
        Returns:
            Secure random token string
        """
        import secrets
        token = secrets.token_urlsafe(32)
        
        logger.info("🔑 Password reset token generated")
        
        return token
    
    def check_password_history(self, password: str, password_history: list[str]) -> bool:
        """
        Check if password was used recently (password history).
        
        Args:
            password: New password to check
            password_history: List of recent password hashes
            
        Returns:
            True if password is not in history, False if it was used recently
        """
        for old_hash in password_history:
            if self.verify_password(password, old_hash):
                logger.warning("⚠️ Password reuse detected")
                return False
        
        logger.info("✅ Password not in recent history")
        return True


# Global password service instance
password_service = PasswordService(rounds=settings.BCRYPT_ROUNDS if hasattr(settings, 'BCRYPT_ROUNDS') else 12) 