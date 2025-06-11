"""
Simple test server for JDA Authentication System
Minimal dependencies for quick testing
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Simple FastAPI app for testing
app = FastAPI(
    title="JDA Auth Test Server",
    description="Simple test server for authentication endpoints",
    version="1.0.0"
)

# Enable CORS for browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Test server running"}

@app.get("/")
async def root():
    return {"message": "JDA Auth Test Server - Go to /docs to see available endpoints"}

if __name__ == "__main__":
    print("🚀 Starting Simple Test Server...")
    print("🌐 Server: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(
        "run_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 