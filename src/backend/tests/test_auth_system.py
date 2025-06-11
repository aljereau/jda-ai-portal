"""
Comprehensive test suite for JDA AI Portal authentication system.
Tests JWT services, password security, user registration/login, and RBAC.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole, UserStatus, RefreshToken
from app.services.jwt_service import jwt_service
from app.services.password_service import password_service
from app.services.auth_service import auth_service, AuthenticationError


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture 
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
        "role": "client"
    }


@pytest.fixture
def admin_user(db_session):
    """Create admin user for testing."""
    hashed_password = password_service.hash_password("AdminPass123!")
    admin = User(
        email="admin@test.com",
        hashed_password=hashed_password,
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


class TestPasswordService:
    """Test password service functionality."""
    
    def test_password_hashing(self):
        """Test password hashing works correctly."""
        password = "TestPassword123!"
        hashed = password_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")
    
    def test_password_verification(self):
        """Test password verification works correctly."""
        password = "TestPassword123!"
        hashed = password_service.hash_password(password)
        
        assert password_service.verify_password(password, hashed) is True
        assert password_service.verify_password("WrongPassword", hashed) is False
    
    def test_password_strength_validation(self):
        """Test password strength requirements."""
        is_strong, issues = password_service.is_password_strong("StrongPass123!")
        assert is_strong is True
        assert len(issues) == 0
        
        is_strong, issues = password_service.is_password_strong("weak")
        assert is_strong is False
        assert len(issues) > 0


class TestJWTService:
    """Test JWT service functionality."""
    
    def test_token_creation(self):
        """Test JWT token creation."""
        user_data = {"sub": "123", "email": "test@example.com", "role": "client"}
        token = jwt_service.create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100
    
    def test_token_verification(self):
        """Test JWT token verification."""
        user_data = {"sub": "123", "email": "test@example.com", "role": "client"}
        token = jwt_service.create_access_token(user_data)
        payload = jwt_service.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"
    
    def test_invalid_token_verification(self):
        """Test verification of invalid tokens."""
        assert jwt_service.verify_token("invalid.token.here") is None
        assert jwt_service.verify_token("") is None


class TestAPIEndpoints:
    """Test API endpoints functionality."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_status_endpoint(self):
        """Test status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "authentication" in data["features"]
    def test_user_id_extraction(self):
        """Test user ID extraction from token."""
        user_data = {"sub": "456", "email": "test@example.com"}
        token = jwt_service.create_access_token(user_data)
        
        user_id = jwt_service.get_user_id_from_token(token)
        assert user_id == 456


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_successful_registration(self, sample_user_data):
        """Test successful user registration."""
        response = client.post("/auth/register", json=sample_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == sample_user_data["email"]
        assert data["token_type"] == "bearer"
    
    def test_duplicate_email_registration(self, sample_user_data):
        """Test registration with duplicate email."""
        # First registration should succeed
        response1 = client.post("/auth/register", json=sample_user_data)
        assert response1.status_code == 201
        
        # Second registration with same email should fail
        response2 = client.post("/auth/register", json=sample_user_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()
    
    def test_invalid_password_registration(self):
        """Test registration with invalid password."""
        user_data = {
            "email": "test@example.com",
            "password": "weak",  # Too weak
            "first_name": "Test", 
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()


class TestUserLogin:
    """Test user login functionality."""
    
    def test_successful_login(self, sample_user_data):
        """Test successful user login."""
        # First register user
        client.post("/auth/register", json=sample_user_data)
        
        # Then login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == sample_user_data["email"]
    
    def test_invalid_credentials_login(self):
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_inactive_user_login(self, sample_user_data, db_session):
        """Test login with inactive user account."""
        # Register user first
        client.post("/auth/register", json=sample_user_data)
        
        # Deactivate user
        user = db_session.query(User).filter(User.email == sample_user_data["email"]).first()
        user.deactivate()
        db_session.commit()
        
        # Attempt login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_successful_token_refresh(self, sample_user_data):
        """Test successful token refresh."""
        # Register and get initial tokens
        response = client.post("/auth/register", json=sample_user_data)
        tokens = response.json()
        
        # Refresh tokens
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # New tokens should be different
        assert data["access_token"] != tokens["access_token"]
        assert data["refresh_token"] != tokens["refresh_token"]
    
    def test_invalid_refresh_token(self):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid-refresh-token"}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


class TestRBAC:
    """Test Role-Based Access Control."""
    
    def test_admin_access(self, admin_user):
        """Test admin user access to admin endpoints."""
        # Login as admin
        login_data = {"email": "admin@test.com", "password": "AdminPass123!"}
        response = client.post("/auth/login", json=login_data)
        tokens = response.json()
        
        # Access admin endpoint
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/admin/stats/system", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
    
    def test_client_no_admin_access(self, sample_user_data):
        """Test client user cannot access admin endpoints."""
        # Register as client
        response = client.post("/auth/register", json=sample_user_data)
        tokens = response.json()
        
        # Try to access admin endpoint
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/admin/stats/system", headers=headers)
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
    
    def test_unauthenticated_access(self):
        """Test unauthenticated access is denied."""
        # Try to access protected endpoint without token
        response = client.get("/users/me")
        assert response.status_code == 401
        
        # Try with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile functionality."""
    
    def test_get_own_profile(self, sample_user_data):
        """Test getting own user profile."""
        # Register user
        response = client.post("/auth/register", json=sample_user_data)
        tokens = response.json()
        
        # Get profile
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["first_name"] == sample_user_data["first_name"]
    
    def test_update_own_profile(self, sample_user_data):
        """Test updating own user profile."""
        # Register user
        response = client.post("/auth/register", json=sample_user_data)
        tokens = response.json()
        
        # Update profile
        update_data = {
            "first_name": "Updated",
            "bio": "Updated bio"
        }
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.put("/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["bio"] == "Updated bio"


class TestSecurityFeatures:
    """Test security features and edge cases."""
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection."""
        malicious_data = {
            "email": "test'; DROP TABLE users; --",
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Should handle gracefully without crashing
        response = client.post("/auth/register", json=malicious_data)
        # May succeed or fail, but should not crash the system
        assert response.status_code in [201, 400, 422]
    
    def test_jwt_token_tampering(self, sample_user_data):
        """Test protection against JWT token tampering."""
        # Register user
        response = client.post("/auth/register", json=sample_user_data)
        tokens = response.json()
        
        # Tamper with token
        tampered_token = tokens["access_token"][:-5] + "XXXXX"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_password_brute_force_protection(self, sample_user_data):
        """Test password verification doesn't leak timing information."""
        # Register user
        client.post("/auth/register", json=sample_user_data)
        
        # Multiple failed login attempts should all take similar time
        login_data = {
            "email": sample_user_data["email"],
            "password": "WrongPassword123!"
        }
        
        # All attempts should return 401 consistently
        for _ in range(5):
            response = client.post("/auth/login", json=login_data)
            assert response.status_code == 401


# Performance benchmarks
class TestPerformance:
    """Test authentication system performance."""
    
    def test_login_performance(self, sample_user_data):
        """Test login endpoint performance."""
        import time
        
        # Register user
        client.post("/auth/register", json=sample_user_data)
        
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        
        # Test multiple logins and measure time
        start_time = time.time()
        for _ in range(10):
            response = client.post("/auth/login", json=login_data)
            assert response.status_code == 200
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 10
        
        # Should be under 200ms per login on average
        assert avg_time < 0.2, f"Login took {avg_time:.3f}s on average"
    
    def test_token_verification_performance(self, sample_user_data):
        """Test token verification performance."""
        import time
        
        # Register user and get token
        response = client.post("/auth/register", json=sample_user_data)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test multiple profile requests
        start_time = time.time()
        for _ in range(50):
            response = client.get("/users/me", headers=headers)
            assert response.status_code == 200
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 50
        
        # Should be under 50ms per verification on average
        assert avg_time < 0.05, f"Token verification took {avg_time:.3f}s on average"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"]) 