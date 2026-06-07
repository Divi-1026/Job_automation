import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.routers import auth, users, files, profile, jobs
from app.services.scraper_service import start_periodic_scraping
from app.services.job_cleanup import run_cleanup_every_24h
from app.routers import credentials

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

# Import models so SQLAlchemy creates tables
import app.models.user  # noqa
import app.models.job   # noqa

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start background tasks (global scraping and cleanup)
    asyncio.create_task(start_periodic_scraping())
    asyncio.create_task(run_cleanup_every_24h())
    yield
    await engine.dispose()

app = FastAPI(
    title="ApplyAI API",
    description="Backend for AI-powered job application automation.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for resumes
os.makedirs(os.path.join(UPLOAD_DIR, "resumes"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(credentials.router)

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "ApplyAI API is running 🚀"}

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}