from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User, UserProgress
from app.routes.auth import get_current_user
from app.schemas.schemas import ProgressRead, ProgressUpdateRequest
from app.services.persistence import require_owned_module, upsert_progress

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=list[ProgressRead])
def list_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProgress]:
    return (
        db.query(UserProgress)
        .filter(UserProgress.user_id == current_user.id)
        .order_by(UserProgress.updated_at.desc())
        .all()
    )


@router.post("", response_model=ProgressRead)
def save_progress(
    payload: ProgressUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProgress:
    require_owned_module(db, current_user, payload.module_id)
    progress = upsert_progress(
        db,
        user_id=current_user.id,
        module_id=payload.module_id,
        status=payload.status,
        quiz_score=payload.quiz_score,
    )
    db.commit()
    db.refresh(progress)
    return progress


@router.get("/{module_id}", response_model=ProgressRead | None)
def get_module_progress(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProgress | None:
    require_owned_module(db, current_user, module_id)
    return (
        db.query(UserProgress)
        .filter(UserProgress.user_id == current_user.id, UserProgress.module_id == module_id)
        .first()
    )
