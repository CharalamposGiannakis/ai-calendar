from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, SessionLocal, engine
from app.routers import categories, events
from app.seed import seed_default_categories

import app.models  # noqa: F401


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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {
        "message": "AI Calendar API is running.",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}