from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Course, Module, User, UserProgress
from app.schemas.schemas import CourseCreate, CourseOutlinePayload, ModuleContentPayload, ModuleOutline


PASSING_SCORE = 70


def _module_payload_to_fields(module_payload: ModuleOutline | ModuleContentPayload) -> dict[str, Any]:
    data = module_payload.model_dump(mode="json")
    subtopics = data.get("subtopic_titles")
    if subtopics is None:
        subtopics = [
            subtopic.get("title")
            for subtopic in data.get("subtopics", [])
            if isinstance(subtopic, dict) and subtopic.get("title")
        ]

    content_json = data if data.get("response_type") == "MODULE_CONTENT" else None
    content_body = None
    if content_json:
        content_body = "\n\n".join(
            subtopic.get("content_markdown", "")
            for subtopic in content_json.get("subtopics", [])
            if isinstance(subtopic, dict) and subtopic.get("content_markdown")
        ) or None

    return {
        "module_number": data.get("module_number"),
        "title": data.get("module_title") or "Untitled Module",
        "subtopic_titles": subtopics or [],
        "content_json": content_json,
        "content_body": content_body,
        "module_quiz": data.get("module_quiz") or [],
    }


def create_course_from_payload(
    db: Session,
    *,
    user: User,
    payload: CourseCreate | CourseOutlinePayload,
    source_session_id: str | None = None,
) -> Course:
    if isinstance(payload, CourseOutlinePayload):
        course_title = payload.course_title
        subject = payload.subject
        modules = payload.modules
        outline_json = payload.model_dump(mode="json")
    else:
        course_title = payload.course_title
        subject = payload.subject
        modules = payload.modules
        source_session_id = payload.source_session_id or source_session_id
        outline_json = {
            "response_type": "COURSE_OUTLINE",
            "course_title": payload.course_title,
            "subject": payload.subject,
            "modules": [module.model_dump(mode="json") for module in payload.modules],
        }

    course = Course(
        user_id=user.id,
        title=course_title,
        subject=subject,
        source_session_id=source_session_id,
        outline_json=outline_json,
    )
    db.add(course)
    db.flush()

    for module_payload in modules:
        fields = _module_payload_to_fields(module_payload)
        db.add(Module(course_id=course.id, subject=subject, **fields))

    db.flush()
    first_module = (
        db.query(Module)
        .filter(Module.course_id == course.id)
        .order_by(Module.module_number.asc().nulls_last(), Module.id.asc())
        .first()
    )
    if first_module:
        upsert_progress(db, user_id=user.id, module_id=first_module.id, status="UNLOCKED")

    db.commit()
    db.refresh(course)
    return course


def replace_course_modules(db: Session, course: Course, modules: list[ModuleOutline | ModuleContentPayload]) -> None:
    for module in list(course.modules):
        db.delete(module)
    db.flush()
    for module_payload in modules:
        fields = _module_payload_to_fields(module_payload)
        db.add(Module(course_id=course.id, subject=course.subject, **fields))


def require_owned_course(db: Session, user: User, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == user.id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


def require_owned_module(db: Session, user: User, module_id: int) -> Module:
    module = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Module.id == module_id, Course.user_id == user.id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


def upsert_progress(
    db: Session,
    *,
    user_id: int,
    module_id: int,
    status: str,
    quiz_score: int | None = None,
    increment_attempts: bool = False,
) -> UserProgress:
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.module_id == module_id)
        .first()
    )
    if not progress:
        progress = UserProgress(user_id=user_id, module_id=module_id, status=status)
        db.add(progress)

    progress.status = status
    if quiz_score is not None:
        progress.quiz_score = quiz_score
    if increment_attempts:
        progress.attempts = (progress.attempts or 0) + 1
    if status in {"COMPLETED", "PASSED"}:
        progress.passed_at = datetime.now(timezone.utc)
    db.flush()
    return progress


def get_next_module(db: Session, module: Module) -> Module | None:
    if not module.course_id:
        return None
    return (
        db.query(Module)
        .filter(Module.course_id == module.course_id, Module.module_number > (module.module_number or 0))
        .order_by(Module.module_number.asc(), Module.id.asc())
        .first()
    )


def update_module_content(db: Session, module: Module, payload: ModuleContentPayload) -> Module:
    fields = _module_payload_to_fields(payload)
    for field_name, field_value in fields.items():
        setattr(module, field_name, field_value)
    db.flush()
    return module
