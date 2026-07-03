from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Course, Module, User
from app.routes.auth import get_current_user
from app.schemas.schemas import CourseCreate, CourseDetail, CourseRead, CourseUpdate, ModuleCreate, ModuleRead, ModuleUpdate
from app.services.persistence import create_course_from_payload, replace_course_modules, require_owned_course

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    return create_course_from_payload(db, user=current_user, payload=payload)


@router.get("", response_model=list[CourseRead])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Course]:
    return (
        db.query(Course)
        .filter(Course.user_id == current_user.id)
        .order_by(Course.updated_at.desc())
        .all()
    )


@router.get("/{course_id}", response_model=CourseDetail)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    return require_owned_course(db, current_user, course_id)


@router.patch("/{course_id}", response_model=CourseDetail)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    course = require_owned_course(db, current_user, course_id)
    if payload.course_title is not None:
        course.title = payload.course_title
        course.outline_json = {**(course.outline_json or {}), "course_title": payload.course_title}
    if payload.subject is not None:
        course.subject = payload.subject
        course.outline_json = {**(course.outline_json or {}), "subject": payload.subject}
    if payload.modules is not None:
        replace_course_modules(db, course, payload.modules)
        course.outline_json = {
            **(course.outline_json or {}),
            "modules": [module.model_dump(mode="json") for module in payload.modules],
        }
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    course = require_owned_course(db, current_user, course_id)
    db.delete(course)
    db.commit()


@router.post("/{course_id}/modules", response_model=ModuleRead, status_code=status.HTTP_201_CREATED)
def create_course_module(
    course_id: int,
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Module:
    course = require_owned_course(db, current_user, course_id)
    content_json = payload.content.model_dump(mode="json") if payload.content else None
    module_quiz = content_json.get("module_quiz", []) if content_json else []
    module = Module(
        course_id=course.id,
        module_number=payload.module_number,
        title=payload.module_title,
        subject=course.subject,
        subtopic_titles=payload.subtopic_titles,
        content_json=content_json,
        module_quiz=module_quiz,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.patch("/{course_id}/modules/{module_id}", response_model=ModuleRead)
def update_course_module(
    course_id: int,
    module_id: int,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Module:
    course = require_owned_course(db, current_user, course_id)
    module = db.query(Module).filter(Module.id == module_id, Module.course_id == course.id).first()
    if not module:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if payload.module_number is not None:
        module.module_number = payload.module_number
    if payload.module_title is not None:
        module.title = payload.module_title
    if payload.subtopic_titles is not None:
        module.subtopic_titles = payload.subtopic_titles
    if payload.content is not None:
        content_json = payload.content.model_dump(mode="json")
        module.content_json = content_json
        module.module_quiz = content_json.get("module_quiz", [])
    db.commit()
    db.refresh(module)
    return module


@router.delete("/{course_id}/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_module(
    course_id: int,
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    course = require_owned_course(db, current_user, course_id)
    module = db.query(Module).filter(Module.id == module_id, Module.course_id == course.id).first()
    if module:
        db.delete(module)
        db.commit()
