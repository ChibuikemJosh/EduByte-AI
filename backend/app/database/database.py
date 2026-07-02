from __future__ import annotations

import os
from typing import Any, Iterator, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.models import Base, ChatSession, Module, User, UserProgress  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edubyte.db")
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
