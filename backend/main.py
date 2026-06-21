import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import get_db, init_db_indexes
from api import auth, footprint, bill, room, coach, twin, gamification

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

# Register routes
app.include_router(auth.router, prefix="/api")
app.include_router(footprint.router, prefix="/api")
app.include_router(bill.router, prefix="/api")
app.include_router(room.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(twin.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "EcoPilot AI Backend",
        "environment": settings.environment
    }
