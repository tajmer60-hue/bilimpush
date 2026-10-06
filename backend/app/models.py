"""Модели базы данных: пользователи, предметы, разделы, темы, вопросы, попытки, прогресс."""
from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), unique=True)
    icon: Mapped[str] = mapped_column(String(16), default="📘")
    color: Mapped[str] = mapped_column(String(20), default="#4f7cff")
    order: Mapped[int] = mapped_column(Integer, default=0)

    sections: Mapped[list["Section"]] = relationship(back_populates="subject",
                                                     cascade="all, delete-orphan",
                                                     order_by="Section.order")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    order: Mapped[int] = mapped_column(Integer, default=0)

    subject: Mapped[Subject] = relationship(back_populates="sections")
    topics: Mapped[list["Topic"]] = relationship(back_populates="section",
                                                 cascade="all, delete-orphan",
                                                 order_by="Topic.order")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    grade_min: Mapped[int] = mapped_column(Integer, default=5)
    grade_max: Mapped[int] = mapped_column(Integer, default=11)
    theory: Mapped[str] = mapped_column(Text, default="")  # HTML-разметка теории
    order: Mapped[int] = mapped_column(Integer, default=0)

    section: Mapped[Section] = relationship(back_populates="topics")
    questions: Mapped[list["Question"]] = relationship(back_populates="topic",
                                                       cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), default="single")  # single | multiple | truefalse
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct = mapped_column(JSON)  # индекс (single) или список индексов (multiple)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1..3
    explanation: Mapped[str] = mapped_column(Text, default="")

    topic: Mapped[Topic] = relationship(back_populates="questions")


class Attempt(Base):
    """Попытка прохождения теста по теме."""
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    question_ids: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    selected = mapped_column(JSON, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Progress(Base):
    """Сводный прогресс пользователя по теме."""
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "topic_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new | read | passed
    best_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)
