"""Схемы запросов/ответов API."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_admin: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- Content ----------
class QuestionPublic(BaseModel):
    id: int
    type: str
    text: str
    options: list
    difficulty: int

    class Config:
        from_attributes = True


class TopicBrief(BaseModel):
    id: int
    title: str
    grade_min: int
    grade_max: int
    questions_count: int = 0
    status: str = "new"
    best_score: float = 0.0

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    id: int
    title: str
    topics: list[TopicBrief]

    class Config:
        from_attributes = True


class SubjectOut(BaseModel):
    id: int
    title: str
    icon: str
    color: str
    sections: list[SectionOut]

    class Config:
        from_attributes = True


class TopicFull(BaseModel):
    id: int
    title: str
    grade_min: int
    grade_max: int
    theory: str
    questions_count: int = 0
    status: str = "new"
    best_score: float = 0.0
    attempts_count: int = 0

    class Config:
        from_attributes = True


# ---------- Tests ----------
class AttemptOut(BaseModel):
    attempt_id: int
    topic_id: int
    topic_title: str = ""
    questions: list[QuestionPublic]
    is_retry: bool = False
    retry_reason: str | None = None


class AnswerIn(BaseModel):
    question_id: int
    selected: int | list[int] | None = None


class SubmitIn(BaseModel):
    answers: list[AnswerIn]


class QuestionResult(BaseModel):
    question_id: int
    selected: int | list[int] | None
    correct: int | list[int]
    is_correct: bool
    text: str
    options: list
    explanation: str


class SubmitOut(BaseModel):
    attempt_id: int
    score: float
    passed: bool
    total: int
    correct_count: int
    results: list[QuestionResult]
    can_retry: bool
    retry_hint: str | None = None


# ---------- Progress ----------
class TopicProgressOut(BaseModel):
    topic_id: int
    title: str
    subject: str
    status: str
    best_score: float
    attempts_count: int


class DashboardOut(BaseModel):
    topics_total: int
    topics_passed: int
    topics_read: int
    tests_taken: int
    avg_score: float
    by_subject: list[dict]
    weak_topics: list[TopicProgressOut]
    recent: list[dict]
