"""Админка: импорт контента из JSON, управление вопросами и темами."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_admin_user
from ..models import Question, Section, Subject, Topic, User

router = APIRouter(prefix="/api/admin", tags=["admin"])

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"


class QuestionIn(BaseModel):
    topic_id: int
    type: str = "single"
    text: str
    options: list[str] = []
    correct: int | list[int]
    difficulty: int = 1
    explanation: str = ""


class TopicIn(BaseModel):
    section_id: int
    title: str
    grade_min: int = 5
    grade_max: int = 11
    theory: str = ""


def import_subject_payload(db: Session, payload: dict) -> dict:
    """Импорт одного предмета из JSON-файла контента (идемпотентно по title)."""
    subj = db.query(Subject).filter(Subject.title == payload["title"]).first()
    if not subj:
        subj = Subject(title=payload["title"], icon=payload.get("icon", "📘"),
                       color=payload.get("color", "#4f7cff"),
                       order=payload.get("order", 0))
        db.add(subj)
        db.commit()
        db.refresh(subj)

    stats = {"sections": 0, "topics": 0, "questions": 0}
    for s_i, sec_data in enumerate(payload.get("sections", [])):
        sec = (db.query(Section)
               .filter(Section.subject_id == subj.id,
                       Section.title == sec_data["title"]).first())
        if not sec:
            sec = Section(subject_id=subj.id, title=sec_data["title"],
                          order=sec_data.get("order", s_i))
            db.add(sec)
            db.commit()
            db.refresh(sec)
        stats["sections"] += 1

        for t_i, t_data in enumerate(sec_data.get("topics", [])):
            topic = (db.query(Topic)
                     .filter(Topic.section_id == sec.id,
                             Topic.title == t_data["title"]).first())
            if not topic:
                topic = Topic(section_id=sec.id, title=t_data["title"],
                              grade_min=t_data.get("grade_min", 5),
                              grade_max=t_data.get("grade_max", 11),
                              theory=t_data.get("theory", ""),
                              order=t_data.get("order", t_i))
                db.add(topic)
                db.commit()
                db.refresh(topic)
            else:
                topic.theory = t_data.get("theory", topic.theory)
                db.commit()
            stats["topics"] += 1

            existing_texts = {q.text for q in db.query(Question)
                              .filter(Question.topic_id == topic.id).all()}
            for q_data in t_data.get("questions", []):
                if q_data["text"] in existing_texts:
                    continue
                db.add(Question(
                    topic_id=topic.id,
                    type=q_data.get("type", "single"),
                    text=q_data["text"],
                    options=q_data.get("options", []),
                    correct=q_data["correct"],
                    difficulty=q_data.get("difficulty", 1),
                    explanation=q_data.get("explanation", ""),
                ))
                existing_texts.add(q_data["text"])
                stats["questions"] += 1
    db.commit()
    return stats


@router.post("/import-all")
def import_all(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    """Импорт всех JSON-файлов из папки backend/content."""
    total = {"files": 0, "sections": 0, "topics": 0, "questions": 0}
    for f in sorted(CONTENT_DIR.glob("*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        stats = import_subject_payload(db, payload)
        total["files"] += 1
        for k in ("sections", "topics", "questions"):
            total[k] += stats[k]
    return total


@router.post("/import-file")
async def import_file(file: UploadFile, db: Session = Depends(get_db),
                      _: User = Depends(get_admin_user)):
    try:
        payload = json.loads((await file.read()).decode("utf-8"))
    except Exception:
        raise HTTPException(400, "Файл должен быть валидным JSON")
    return import_subject_payload(db, payload)


@router.post("/questions", status_code=201)
def add_question(data: QuestionIn, db: Session = Depends(get_db),
                 _: User = Depends(get_admin_user)):
    if not db.get(Topic, data.topic_id):
        raise HTTPException(404, "Тема не найдена")
    q = Question(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id}


@router.delete("/questions/{qid}")
def delete_question(qid: int, db: Session = Depends(get_db),
                    _: User = Depends(get_admin_user)):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404, "Вопрос не найден")
    db.delete(q)
    db.commit()
    return {"ok": True}


@router.post("/topics", status_code=201)
def add_topic(data: TopicIn, db: Session = Depends(get_db),
              _: User = Depends(get_admin_user)):
    if not db.get(Section, data.section_id):
        raise HTTPException(404, "Раздел не найден")
    t = Topic(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id}
