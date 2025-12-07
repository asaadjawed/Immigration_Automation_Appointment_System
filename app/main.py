"""
FastAPI main application.
Entry point for the Immigration Office Automation System.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router
from app.database import engine, Base

# Create database tables (in production, use Alembic migrations)
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Automated email workflow system for immigration office",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Immigration Office Automation System",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print(f"Starting {settings.APP_NAME}...")
    print(f"Debug mode: {settings.DEBUG}")
    
    # Create necessary directories
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.GUIDELINES_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
    
    print("Application started successfully!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

