from fastapi import FastAPI

import app.models  # noqa: F401 — register tables on Base.metadata
from app.api.auth import router as auth_router
from app.db.base import Base
from app.db.session import engine

app = FastAPI(title="MockFastAPI")
app.include_router(auth_router)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
