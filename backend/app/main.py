"""Точка входа FastAPI: API + раздача фронтенда."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import admin, auth, content, progress, tests
from .seed import ensure_admin, seed_content

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bilim+", version="1.0.0",
              description="Школьная база Казахстана: теория + адаптивные тесты")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(tests.router)
app.include_router(progress.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    seed_content()
    ensure_admin()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Bilim+"}


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
