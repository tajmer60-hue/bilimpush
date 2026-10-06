"""Начальное наполнение БД контентом из backend/content/*.json и создание админа."""
import json
import os
from pathlib import Path

from .database import SessionLocal
from .models import Question, Subject, User
from .routers.admin import import_subject_payload
from .security import hash_password

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

ADMIN_EMAIL = os.environ.get("BILIM_ADMIN_EMAIL", "admin@bilim.kz")
ADMIN_PASSWORD = os.environ.get("BILIM_ADMIN_PASSWORD", "admin123")


def seed_content():
    db = SessionLocal()
    try:
        for f in sorted(CONTENT_DIR.glob("*.json")):
            payload = json.loads(f.read_text(encoding="utf-8"))
            import_subject_payload(db, payload)
    finally:
        db.close()


def ensure_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == ADMIN_EMAIL).first():
            db.add(User(name="Администратор", email=ADMIN_EMAIL,
                        password_hash=hash_password(ADMIN_PASSWORD),
                        is_admin=True))
            db.commit()
    finally:
        db.close()


def stats() -> dict:
    db = SessionLocal()
    try:
        return {"subjects": db.query(Subject).count(),
                "questions": db.query(Question).count()}
    finally:
        db.close()
