#!/usr/bin/env python3
"""Test script to identify import issues"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'backend'))

print("Testing imports...")

try:
    print("1. Testing FastAPI import...")
    from fastapi import FastAPI
    print("✅ FastAPI import successful")
except Exception as e:
    print(f"❌ FastAPI import failed: {e}")
    sys.exit(1)

try:
    print("2. Testing app.core imports...")
    from app.core.config import settings
    print("✅ Config import successful")
except Exception as e:
    print(f"❌ Config import failed: {e}")

try:
    print("3. Testing app.models imports...")
    from app.models.user import User
    print("✅ User model import successful")
except Exception as e:
    print(f"❌ User model import failed: {e}")

try:
    print("4. Testing app.services imports...")
    from app.services.auth_service import auth_service
    print("✅ Auth service import successful")
except Exception as e:
    print(f"❌ Auth service import failed: {e}")

try:
    print("5. Testing main app import...")
    from app.main import app
    print("✅ Main app import successful")
    print("🎉 All imports successful! Server should work.")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    import traceback
    traceback.print_exc()

print("Import test complete.") 