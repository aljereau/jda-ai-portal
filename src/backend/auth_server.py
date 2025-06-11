"""
Full Authentication Server for JDA System
Includes all auth endpoints with in-memory data for testing
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
import jwt

# Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI app
app = FastAPI(
    title="JDA Authentication System",
    description="Full authentication system with JWT tokens",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# In-memory data store (for testing)
users_db: Dict[str, dict] = {}
refresh_tokens: Dict[str, dict] = {}

# Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "client"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Initialize test users
def init_test_users():
    test_users = [
        {"email": "admin@jda.com", "password": "AdminPass123!", "full_name": "Admin User", "role": "admin"},
        {"email": "pm@jda.com", "password": "PMPass123!", "full_name": "Project Manager", "role": "project_manager"},
        {"email": "client@jda.com", "password": "ClientPass123!", "full_name": "Client User", "role": "client"},
    ]
    
    for user_data in test_users:
        user_id = user_data["email"]  # Use email as ID for simplicity
        users_db[user_id] = {
            "id": user_id,
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "password_hash": hash_password(user_data["password"]),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }

# Endpoints
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "JDA Auth Server running"}

@app.post("/api/v1/auth/register")
def register_user(user_data: UserRegistration):
    # Check if user exists
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = user_data.email
    users_db[user_id] = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "password_hash": hash_password(user_data.password),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Create token
    token_data = {"sub": user_id, "email": user_data.email, "role": user_data.role}
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user_id,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=True
        )
    }

@app.post("/api/v1/auth/login")
def login_user(login_data: UserLogin):
    # Find user
    user = users_db.get(login_data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token_data = {"sub": user["id"], "email": user["email"], "role": user["role"]}
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"]
        )
    }

@app.get("/api/v1/auth/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user["is_active"]
    )

@app.get("/api/v1/users/")
def list_users(current_user: dict = Depends(get_current_user)):
    # Simple auth check
    if current_user["role"] not in ["admin", "project_manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return [
        UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"]
        )
        for user in users_db.values()
    ]

@app.get("/api/v1/admin/stats")
def get_admin_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "total_users": len(users_db),
        "active_users": len([u for u in users_db.values() if u["is_active"]]),
        "user_roles": {
            "admin": len([u for u in users_db.values() if u["role"] == "admin"]),
            "project_manager": len([u for u in users_db.values() if u["role"] == "project_manager"]),
            "client": len([u for u in users_db.values() if u["role"] == "client"]),
        }
    }

# Initialize on startup
@app.on_event("startup")
def startup_event():
    init_test_users()
    print("✅ Test users initialized")

if __name__ == "__main__":
    print("🚀 Starting JDA Authentication Server...")
    print("📋 Test Users Available:")
    print("   Admin: admin@jda.com / AdminPass123!")
    print("   PM: pm@jda.com / PMPass123!")
    print("   Client: client@jda.com / ClientPass123!")
    print("")
    print("🌐 Server: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🧪 Test Interface: Open test-interface.html in your browser")
    print("")
    
    uvicorn.run(
        "auth_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 