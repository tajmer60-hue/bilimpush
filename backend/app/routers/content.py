"""Контент: предметы, разделы, темы, теория."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_optional_user
from ..models import Progress, Question, Section, Subject, Topic, User
from ..schemas import SectionOut, SubjectOut, TopicBrief, TopicFull

router = APIRouter(prefix="/api", tags=["content"])


def _progress_map(db: Session, user: User | None) -> dict[int, Progress]:
    if not user:
        return {}
    rows = db.query(Progress).filter(Progress.user_id == user.id).all()
    return {r.topic_id: r for r in rows}


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db),
                  user: User | None = Depends(get_optional_user)):
    subjects = (db.query(Subject)
                .options(joinedload(Subject.sections).joinedload(Section.topics))
                .order_by(Subject.order).all())
    counts = dict(db.query(Question.topic_id, func.count(Question.id))
                  .group_by(Question.topic_id).all())
    prog = _progress_map(db, user)

    out = []
    for s in subjects:
        sections = []
        for sec in s.sections:
            topics = []
            for t in sec.topics:
                p = prog.get(t.id)
                topics.append(TopicBrief(
                    id=t.id, title=t.title, grade_min=t.grade_min,
                    grade_max=t.grade_max, questions_count=counts.get(t.id, 0),
                    status=p.status if p else "new",
                    best_score=p.best_score if p else 0.0,
                ))
            sections.append(SectionOut(id=sec.id, title=sec.title, topics=topics))
        out.append(SubjectOut(id=s.id, title=s.title, icon=s.icon,
                              color=s.color, sections=sections))
    return out


@router.get("/subjects/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db),
                user: User | None = Depends(get_optional_user)):
    s = (db.query(Subject)
         .options(joinedload(Subject.sections).joinedload(Section.topics))
         .filter(Subject.id == subject_id).first())
    if not s:
        raise HTTPException(404, "Предмет не найден")
    return next(x for x in list_subjects(db, user) if x.id == s.id)


@router.get("/topics/{topic_id}", response_model=TopicFull)
def get_topic(topic_id: int, db: Session = Depends(get_db),
              user: User | None = Depends(get_optional_user)):
    t = db.get(Topic, topic_id)
    if not t:
        raise HTTPException(404, "Тема не найдена")
    count = db.query(func.count(Question.id)).filter(Question.topic_id == t.id).scalar() or 0
    p = _progress_map(db, user).get(t.id)
    return TopicFull(
        id=t.id, title=t.title, grade_min=t.grade_min, grade_max=t.grade_max,
        theory=t.theory, questions_count=count,
        status=p.status if p else "new",
        best_score=p.best_score if p else 0.0,
        attempts_count=p.attempts_count if p else 0,
    )
