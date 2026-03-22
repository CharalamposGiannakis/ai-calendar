from fastapi import FastAPI

from app.db import Base, engine
from app.routers import categories, events

import app.models  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Calendar API",
    version="0.1.0",
    description="Backend starter for the AI Calendar project.",
)

app.include_router(categories.router)
app.include_router(events.router)


@app.get("/health")
def health():
    return {"status": "ok"}