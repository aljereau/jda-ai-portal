"""
Local development server for testing JDA Authentication System
Runs without Docker for quick testing purposes
"""

import os
import sys
import uvicorn
from app.core.config import get_settings

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the FastAPI server locally for testing"""
    settings = get_settings()
    
    # Override database URL for local SQLite testing
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    
    print("🚀 Starting JDA Authentication System...")
    print("📋 Test Users Available:")
    print("   Admin: admin@jda.com / AdminPass123!")
    print("   PM: pm@jda.com / PMPass123!")
    print("   Client: client@jda.com / ClientPass123!")
    print("")
    print("🌐 Server will be available at: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🧪 Test Interface: Open test-interface.html in your browser")
    print("")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 