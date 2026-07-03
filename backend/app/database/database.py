from __future__ import annotations

import os
from typing import Any, Iterator, TypeVar

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.models import Base, ChatMessage, ChatSession, Course, Module, QuizSubmission, User, UserProgress  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logging = __import__("logging")
    logging.getLogger(__name__).warning("No DATABASE_URL found; falling back to local SQLite for hackathon/demo convenience.")
    DATABASE_URL = "sqlite:///./edubyte.db"
# Automatically fix raw 'postgres://' strings if provided by cloud hosting environments
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ModelType = TypeVar("ModelType")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if DATABASE_URL is None:
        raise ValueError("DATABASE_URL is not set. Cannot initialize the database.")
    if DATABASE_URL.startswith("sqlite"):
        _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "modules" in table_names:
        module_columns = {column["name"] for column in inspector.get_columns("modules")}
        module_additions = {
            "course_id": "INTEGER",
            "module_number": "INTEGER",
            "subtopic_titles": "JSON NOT NULL DEFAULT '[]'",
            "content_json": "JSON",
            "module_quiz": "JSON NOT NULL DEFAULT '[]'",
            "updated_at": "DATETIME",
        }
        _add_missing_sqlite_columns("modules", module_columns, module_additions)

    if "chat_sessions" in table_names:
        chat_columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
        _add_missing_sqlite_columns("chat_sessions", chat_columns, {"created_at": "DATETIME"})

    if "user_progress" in table_names:
        progress_columns = {column["name"] for column in inspector.get_columns("user_progress")}
        _add_missing_sqlite_columns(
            "user_progress",
            progress_columns,
            {"attempts": "INTEGER NOT NULL DEFAULT 0", "passed_at": "DATETIME"},
        )


def _add_missing_sqlite_columns(table_name: str, existing_columns: set[str], desired_columns: dict[str, str]) -> None:
    with engine.begin() as connection:
        for column_name, column_sql in desired_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_record(db: Session, obj: ModelType) -> ModelType:
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_record(db: Session, model: type[ModelType], record_id: Any) -> ModelType | None:
    return db.get(model, record_id)


def list_records(db: Session, model: type[ModelType], offset: int = 0, limit: int = 100) -> list[ModelType]:
    return db.query(model).offset(offset).limit(limit).all()


def update_record(db: Session, obj: ModelType, data: dict[str, Any]) -> ModelType:
    for field_name, field_value in data.items():
        setattr(obj, field_name, field_value)

    db.commit()
    db.refresh(obj)
    return obj


def delete_record(db: Session, obj: object) -> None:
    db.delete(obj)
    db.commit()
