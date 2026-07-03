from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import ChatSession, User
from app.routes.auth import get_current_user
from app.schemas.schemas import ChatRequest, EduByteAIResponse, ModuleContentPayload
from app.services.ai_engine import AIEngineService

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_HISTORY_TURNS = 30


class ModuleHydrationRequest(BaseModel):
    session_id: str = Field(..., description="Existing chat session id for contextual generation")
    module_number: int = Field(..., ge=1)
    module_title: str = Field(..., min_length=1)
    subtopic_titles: list[str] = Field(..., min_length=1)


def _get_or_create_chat_session(db: Session, current_user: User, session_id: str) -> ChatSession:
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if chat_session:
        return chat_session

    chat_session = ChatSession(session_id=session_id, user_id=current_user.id)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def _compact_assistant_content(response: EduByteAIResponse | ModuleContentPayload) -> str:
    response_data = response.model_dump(mode="json")
    payload = response_data.get("payload", response_data)
    response_type = response_data.get("response_type") or payload.get("response_type")
    summary: dict[str, Any] = {
        "response_type": response_type,
        "message": response_data.get("message", ""),
    }

    if isinstance(payload, dict):
        if payload.get("course_title"):
            summary["course_title"] = payload.get("course_title")
        if payload.get("quiz_title"):
            summary["quiz_title"] = payload.get("quiz_title")
        if payload.get("module_title"):
            summary["module_title"] = payload.get("module_title")
        if payload.get("clarification_text"):
            summary["clarification_text"] = payload.get("clarification_text")
        if payload.get("answer"):
            summary["answer"] = payload.get("answer")

        modules = payload.get("modules")
        if isinstance(modules, list):
            summary["modules"] = [
                {
                    "module_number": module.get("module_number"),
                    "module_title": module.get("module_title"),
                    "subtopic_titles": module.get("subtopic_titles")
                    or [subtopic.get("title") for subtopic in module.get("subtopics", []) if isinstance(subtopic, dict)],
                }
                for module in modules
                if isinstance(module, dict)
            ]

        subtopics = payload.get("subtopics")
        if isinstance(subtopics, list):
            summary["subtopics"] = [
                subtopic.get("title") for subtopic in subtopics if isinstance(subtopic, dict) and subtopic.get("title")
            ]

    return json.dumps(summary, ensure_ascii=False)


def _append_history_turns(chat_session: ChatSession, user_message: str, assistant_content: str) -> None:
    history_meta = list(chat_session.history_meta or [])
    history_meta.extend(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_content},
        ]
    )
    chat_session.history_meta = history_meta[-MAX_HISTORY_TURNS:]


@router.post("/chat", response_model=EduByteAIResponse)
async def chat_with_ai(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EduByteAIResponse:
    chat_session = _get_or_create_chat_session(db, current_user, payload.session_id)

    try:
        response = await AIEngineService.process_user_intent(
            current_message=payload.message,
            history_meta=chat_session.history_meta or [],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI generation failed before a normalized EduByte response could be produced.",
        ) from exc

    _append_history_turns(chat_session, payload.message, _compact_assistant_content(response))
    db.commit()
    db.refresh(chat_session)
    return response


@router.post("/modules/hydrate", response_model=ModuleContentPayload)
async def hydrate_module_content(
    payload: ModuleHydrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModuleContentPayload:
    chat_session = _get_or_create_chat_session(db, current_user, payload.session_id)

    try:
        response = await AIEngineService.generate_module_content_block(
            module_number=payload.module_number,
            module_title=payload.module_title,
            subtopic_titles=payload.subtopic_titles,
            history_meta=chat_session.history_meta or [],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Module content generation failed.",
        ) from exc

    assistant_content = _compact_assistant_content(response)
    _append_history_turns(
        chat_session,
        f"Hydrate module {payload.module_number}: {payload.module_title}",
        assistant_content,
    )
    db.commit()
    db.refresh(chat_session)
    return response
