from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import Base, SessionLocal, engine
from app.routers import categories, events
from app.seed import seed_default_categories

import app.models  # noqa: F401

STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_default_categories(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title="AI Calendar API",
    version="0.1.0",
    description="Backend starter for the AI Calendar project.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(events.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api-info")
def api_info():
    return {
        "message": "AI Calendar API is running.",
        "docs_url": "/docs",
        "health_url": "/health",
    }

@app.get("/")
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")
