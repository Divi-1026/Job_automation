import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.routers import auth, users, files, profile, jobs

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

# Import all models so SQLAlchemy registers them before creating tables
import app.models.user  # noqa: F401
import app.models.job   # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup (dev convenience – use Alembic in prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="ApplyAI API",
    description="Backend for the AI-powered job application automation tool.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default port
        "http://localhost:5174",   # Vite fallback port (when 5173 is taken)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded resumes) ─────────────────────────────────────────
os.makedirs(os.path.join(UPLOAD_DIR, "resumes"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)
app.include_router(profile.router)
app.include_router(jobs.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "ApplyAI API is running 🚀"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
