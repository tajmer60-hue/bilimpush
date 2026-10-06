"""Прогресс пользователя: дашборд, слабые темы, история."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Attempt, Progress, Section, Subject, Topic, User
from ..schemas import DashboardOut, TopicProgressOut

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topics_total = db.query(func.count(Topic.id)).scalar() or 0
    progs = db.query(Progress).filter(Progress.user_id == user.id).all()
    passed = [p for p in progs if p.status == "passed"]
    read = [p for p in progs if p.status in ("read", "passed")]
    attempts = db.query(Attempt).filter(Attempt.user_id == user.id,
                                        Attempt.submitted == True).all()  # noqa: E712
    avg = round(sum(a.score or 0 for a in attempts) / len(attempts), 3) if attempts else 0.0

    # разбивка по предметам
    rows = (db.query(Subject.id, Subject.title, Subject.icon, Topic.id)
            .join(Section, Section.subject_id == Subject.id)
            .join(Topic, Topic.section_id == Section.id).all())
    subj_topics: dict[int, dict] = {}
    for sid, stitle, sicon, tid in rows:
        d = subj_topics.setdefault(sid, {"title": stitle, "icon": sicon,
                                         "total": 0, "passed": 0})
        d["total"] += 1
    prog_by_topic = {p.topic_id: p for p in progs}
    for sid, _, _, tid in rows:
        p = prog_by_topic.get(tid)
        if p and p.status == "passed":
            subj_topics[sid]["passed"] += 1
    by_subject = [dict(subject_id=sid, **d) for sid, d in subj_topics.items()]

    # слабые темы (читал, но не сдал)
    topic_map = {t.id: t for t in db.query(Topic).all()}
    subj_of_topic = {}
    for sid, _, _, tid in rows:
        subj_of_topic[tid] = subj_topics[sid]["title"]
    weak = []
    for p in progs:
        t = topic_map.get(p.topic_id)
        if t and p.status != "passed" and p.attempts_count > 0:
            weak.append(TopicProgressOut(
                topic_id=t.id, title=t.title,
                subject=subj_of_topic.get(t.id, ""), status=p.status,
                best_score=p.best_score, attempts_count=p.attempts_count))
    weak.sort(key=lambda w: w.best_score)

    recent = []
    for a in sorted(attempts, key=lambda x: x.created_at, reverse=True)[:10]:
        t = topic_map.get(a.topic_id)
        recent.append({"topic_id": a.topic_id,
                       "title": t.title if t else "—",
                       "score": a.score, "passed": a.passed,
                       "date": a.created_at.isoformat()})

    return DashboardOut(topics_total=topics_total, topics_passed=len(passed),
                        topics_read=len(read), tests_taken=len(attempts),
                        avg_score=avg, by_subject=by_subject,
                        weak_topics=weak[:5], recent=recent)
