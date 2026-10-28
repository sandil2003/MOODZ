from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from app.database import init_db, close_db
from app.redis_client import close_redis
from app.routes import health, chat, history, mood, auth
from app.core.telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting MOOD AI Agent...")
    await init_db()
    print("✅ Database initialized")
    print("✅ Redis client ready")
    
    # Initialize AgentOps Telemetry
    try:
        setup_telemetry()
        print("✅ AgentOps Telemetry initialized")
    except Exception as e:
        print(f"⚠️ [AgentOps] Telemetry init warning: {e}")
        
    yield
    
    # Shutdown
    print("🛑 Shutting down MOOD AI Agent...")
    await close_db()
    await close_redis()
    print("✅ Cleanup completed")


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-powered mood analysis and recommendation system",
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(health.test_router, prefix="/api")
app.include_router(chat.chat_router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(mood.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        dict: API information
    """
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/api/info")
async def api_info():
    """
    API information endpoint.
    
    Returns:
        dict: Detailed API information
    """
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "description": "AI-powered mood analysis and recommendation system",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "health_db": "/health/db",
            "health_redis": "/health/redis",
            "chat": "/api/moods/chat",
            "chat_stream": "/api/moodschat/stream"
        },
        "integrations": {
            "openai": "configured" if settings.openai_api_key else "not configured",
            "pinecone": "configured" if settings.pinecone_api_key else "not configured",
            "agentops": "enabled"
        }
    }


@app.get("/v1/models")
async def list_v1_models():
    """Compatibility endpoint for external OpenAI-compatible clients and dev tools."""
    return {
        "object": "list",
        "data": [
            {
                "id": "moodz-ai-agent",
                "object": "model",
                "created": 1700000000,
                "owned_by": "moodz"
            }
        ]
    }
