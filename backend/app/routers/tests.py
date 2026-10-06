"""Адаптивные тесты.

Логика:
- Тест собирается из банка вопросов темы (по умолчанию 10 вопросов).
- При первой попытке вопросы выбираются случайно, сбалансированно по сложности.
- Если тест провален (< PASS_THRESHOLD), следующая попытка — НОВЫЙ тест:
  * обязательно включаются все вопросы, в которых пользователь ошибся раньше;
  * остальные добираются из ещё не встречавшихся вопросов;
  * вопросы последнего провала повторно не используются, пока хватает банка.
- Порог сдачи: 70%.
"""
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Answer, Attempt, Progress, Question, Topic, User
from ..schemas import AttemptOut, QuestionPublic, SubmitIn, SubmitOut

router = APIRouter(prefix="/api", tags=["tests"])

TEST_SIZE = 10
PASS_THRESHOLD = 0.7


def _get_progress(db: Session, user: User, topic_id: int) -> Progress:
    p = (db.query(Progress)
         .filter(Progress.user_id == user.id, Progress.topic_id == topic_id).first())
    if not p:
        p = Progress(user_id=user.id, topic_id=topic_id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def _mark_read(db: Session, user: User, topic_id: int):
    p = _get_progress(db, user, topic_id)
    if p.status == "new":
        p.status = "read"
        db.commit()


def _build_question_set(db: Session, user: User, topic: Topic) -> tuple[list[Question], bool, str | None]:
    """Собирает набор вопросов для попытки. Возвращает (questions, is_retry, reason)."""
    pool = db.query(Question).filter(Question.topic_id == topic.id).all()
    if not pool:
        raise HTTPException(400, "Для этой темы банк вопросов пока пуст")
    pool_by_id = {q.id: q for q in pool}

    prev_attempts = (db.query(Attempt)
                     .filter(Attempt.user_id == user.id, Attempt.topic_id == topic.id,
                             Attempt.submitted == True)  # noqa: E712
                     .order_by(Attempt.created_at.desc()).all())

    # Первая попытка — сбалансированная случайная выборка
    if not prev_attempts:
        size = min(TEST_SIZE, len(pool))
        by_diff = {1: [], 2: [], 3: []}
        for q in pool:
            by_diff.setdefault(q.difficulty, by_diff[1]).append(q)
        for v in by_diff.values():
            random.shuffle(v)
        picked, i = [], 0
        while len(picked) < size and any(by_diff.values()):
            d = [1, 2, 3][i % 3]
            if by_diff.get(d):
                picked.append(by_diff[d].pop())
            i += 1
            if i > 100:
                break
        random.shuffle(picked)
        return picked, False, None

    # Повторная попытка после провала — адаптивный набор
    wrong_ids, seen_ids = set(), set()
    answers = (db.query(Answer)
               .filter(Answer.attempt_id.in_([a.id for a in prev_attempts])).all())
    for a in answers:
        seen_ids.add(a.question_id)
        if a.is_correct is False:
            wrong_ids.add(a.question_id)
    last_attempt_ids = set(prev_attempts[0].question_ids or [])

    size = min(TEST_SIZE, len(pool))
    picked: list[Question] = []

    # 1) сначала — ошибки прошлых попыток (не более 60% теста, чтобы остались новые вопросы)
    wrong_pool = [pool_by_id[i] for i in wrong_ids if i in pool_by_id]
    random.shuffle(wrong_pool)
    max_wrong = max(1, int(size * 0.6))
    picked.extend(wrong_pool[:max_wrong])

    # 2) добираем новыми вопросами (не из последней попытки)
    fresh = [q for q in pool if q.id not in seen_ids and q.id not in last_attempt_ids]
    random.shuffle(fresh)
    for q in fresh:
        if len(picked) >= size:
            break
        picked.append(q)

    # 3) если банка не хватает — любые не из последней попытки, затем любые
    if len(picked) < size:
        rest = [q for q in pool if q.id not in {x.id for x in picked}
                and q.id not in last_attempt_ids]
        random.shuffle(rest)
        picked.extend(rest[:size - len(picked)])
    if len(picked) < size:
        rest = [q for q in pool if q.id not in {x.id for x in picked}]
        random.shuffle(rest)
        picked.extend(rest[:size - len(picked)])

    random.shuffle(picked)
    reason = None
    if wrong_pool:
        reason = (f"Прошлый тест не сдан. В новый тест включено "
                  f"{min(len(wrong_pool), max_wrong)} вопрос(ов), где были ошибки, "
                  f"остальные — новые.")
    else:
        reason = "Новый тест с другими вопросами из банка темы."
    return picked, True, reason


@router.post("/topics/{topic_id}/read")
def mark_read(topic_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    if not db.get(Topic, topic_id):
        raise HTTPException(404, "Тема не найдена")
    _mark_read(db, user, topic_id)
    return {"ok": True}


@router.post("/topics/{topic_id}/test", response_model=AttemptOut)
def start_test(topic_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Тема не найдена")
    _mark_read(db, user, topic_id)

    questions, is_retry, reason = _build_question_set(db, user, topic)
    attempt = Attempt(user_id=user.id, topic_id=topic.id,
                      question_ids=[q.id for q in questions])
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return AttemptOut(attempt_id=attempt.id, topic_id=topic.id,
                      topic_title=topic.title,
                      questions=[QuestionPublic.model_validate(q) for q in questions],
                      is_retry=is_retry, retry_reason=reason)


def _normalize(selected, qtype: str):
    if qtype == "multiple":
        if selected is None:
            return []
        if isinstance(selected, int):
            return [selected]
        return sorted(set(selected))
    if selected is None:
        return None
    if isinstance(selected, list):
        return selected[0] if selected else None
    return selected


def _is_correct(selected, correct, qtype: str) -> bool:
    if qtype == "multiple":
        return _normalize(selected, qtype) == sorted(correct if isinstance(correct, list) else [correct])
    return selected is not None and selected == correct


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit_test(attempt_id: int, data: SubmitIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    attempt = db.get(Attempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(404, "Попытка не найдена")
    if attempt.submitted:
        raise HTTPException(400, "Тест уже проверен")

    questions = {q.id: q for q in db.query(Question)
                 .filter(Question.id.in_(attempt.question_ids)).all()}
    given = {a.question_id: a.selected for a in data.answers}

    results, correct_count = [], 0
    for qid in attempt.question_ids:
        q = questions.get(qid)
        if not q:
            continue
        sel = _normalize(given.get(qid), q.type)
        ok = _is_correct(sel, q.correct, q.type)
        correct_count += int(ok)
        db.add(Answer(attempt_id=attempt.id, question_id=qid,
                      selected=sel, is_correct=ok))
        results.append({
            "question_id": qid, "selected": sel, "correct": q.correct,
            "is_correct": ok, "text": q.text, "options": q.options,
            "explanation": q.explanation,
        })

    total = len(results) or 1
    score = round(correct_count / total, 4)
    passed = score >= PASS_THRESHOLD
    attempt.score = score
    attempt.passed = passed
    attempt.submitted = True

    p = _get_progress(db, user, attempt.topic_id)
    p.attempts_count += 1
    p.best_score = max(p.best_score, score)
    if passed:
        p.status = "passed"
    elif p.status == "new":
        p.status = "read"
    db.commit()

    hint = None
    if not passed:
        need = int(-(-(PASS_THRESHOLD * total) // 1))  # ceil
        hint = (f"Нужно минимум {need} из {total} правильных ответов (70%). "
                f"Разбери ошибки ниже и пройди новый тест — он будет "
                f"составлен с учётом твоих слабых мест.")
    return SubmitOut(attempt_id=attempt.id, score=score, passed=passed,
                     total=len(results), correct_count=correct_count,
                     results=results, can_retry=not passed, retry_hint=hint)
