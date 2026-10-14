import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
# from app.routers import extension
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.staticfiles import StaticFiles


from app.database import (
    engine,
    Base,
)


# ---------------------------------------------------------
# Import all models BEFORE create_all
# ---------------------------------------------------------

import app.models.user
import app.models.job
import app.models.platform_credential


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

from app.routers import (
    auth,
    users,
    profile,
    jobs,
    credentials,
    extension,
)


# ---------------------------------------------------------
# Upload directory
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_DIR = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "uploads",
    )
)


# ---------------------------------------------------------
# Lifespan
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    # ---------------------------------------------
    # Create tables that do not exist.
    #
    # IMPORTANT:
    # create_all DOES NOT modify existing columns.
    # We will run migration separately.
    # ---------------------------------------------

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )


    print(
        "✅ Database connected"
    )

    print(
        "✅ CareerSync API started"
    )


    # -------------------------------------------------
    # DO NOT start scraping here.
    #
    # Celery Beat handles:
    # - global scraping
    # - 7 day cleanup
    # -------------------------------------------------

    yield


    await engine.dispose()

    print(
        "🛑 Database connection closed"
    )


# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------

app = FastAPI(

    title="CareerSync API",

    description=(
        "AI-powered job discovery, "
        "semantic matching and "
        "application automation platform."
    ),

    version="1.0.0",

    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Resume static files
# ---------------------------------------------------------

RESUME_DIR = os.path.join(
    UPLOAD_DIR,
    "resumes",
)

os.makedirs(
    RESUME_DIR,
    exist_ok=True,
)


app.mount(

    "/uploads",

    StaticFiles(
        directory=UPLOAD_DIR
    ),

    name="uploads",
)


# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------

app.include_router(
    auth.router
)

app.include_router(
    users.router
)

app.include_router(
    profile.router
)

app.include_router(
    jobs.router
)

app.include_router(
    credentials.router
)

app.include_router(
    extension.router
)

# ---------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------

@app.get(
    "/",
    tags=["Health"],
)
async def root():

    return {

        "status": "ok",

        "message":
            "CareerSync API is running 🚀",

    }


@app.get(
    "/health",
    tags=["Health"],
)
async def health():

    return {

        "status": "healthy",

    }