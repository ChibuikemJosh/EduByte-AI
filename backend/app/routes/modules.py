from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import ChatSession, Module, User
from app.routes.auth import get_current_user
from app.schemas.schemas import ModuleRead
from app.services.ai_engine import AIEngineService
from app.services.persistence import require_owned_module, update_module_content

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("/{module_id}", response_model=ModuleRead)
async def get_or_hydrate_module(
    module_id: int,
    session_id: str | None = Query(default=None),
    force_refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Module:
    module = require_owned_module(db, current_user, module_id)
    if module.content_json and module.module_quiz and not force_refresh:
        return module

    history_meta = []
    if session_id:
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == session_id, ChatSession.user_id == current_user.id)
            .first()
        )
        history_meta = chat_session.history_meta if chat_session else []

    try:
        content = await AIEngineService.generate_module_content_block(
            module_number=module.module_number or 1,
            module_title=module.title,
            subtopic_titles=module.subtopic_titles or [],
            history_meta=history_meta or [],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Module hydration failed") from exc

    update_module_content(db, module, content)
    db.commit()
    db.refresh(module)
    return module
