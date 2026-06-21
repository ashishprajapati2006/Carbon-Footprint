import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import get_db, init_db_indexes
from core.settings import EnvironmentType
from api import auth, footprint, bill, room, coach, twin, gamification, report
from middleware.security_headers import SecurityHeadersMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_db()
    await init_db_indexes(db)
    yield

# Configure logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="EcoPilot AI - Green Platform API",
    description="Backend API powering carbon analysis, image scans, and AI coaching.",
    version="1.0.0",
    lifespan=lifespan
)

# Register Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://carbon-footprint-dun.vercel.app",
        settings.next_public_api_url,
    ],
    allow_origin_regex=r"https://carbon-footprint-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    if settings.environment == EnvironmentType.PRODUCTION:
        detail = "Internal Server Error"
    else:
        detail = f"Internal Server Error: {str(exc)}"
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "type": type(exc).__name__
        }
    )

# Register routes
app.include_router(auth.router, prefix="/api")
app.include_router(footprint.router, prefix="/api")
app.include_router(bill.router, prefix="/api")
app.include_router(room.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(twin.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")
app.include_router(report.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "EcoPilot AI Backend",
        "environment": settings.environment
    }

@app.get("/health")
async def health_check():
    db = await get_db()
    if hasattr(db, "_collections"):
        db_status = "healthy (mock-in-memory)"
    else:
        try:
            await db.command('ping')
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {e}"
            
    from ai.gemini_ai import GeminiAIService
    gemini = GeminiAIService()
    ai_status = "mock-offline" if gemini.is_mock else "healthy"
    
    overall = "healthy"
    if "unhealthy" in db_status:
        overall = "unhealthy"
        
    return {
        "status": overall,
        "database": db_status,
        "ai_service": ai_status,
        "environment": settings.environment
    }
