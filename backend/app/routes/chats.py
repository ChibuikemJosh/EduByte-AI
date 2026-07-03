from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import ChatMessage, ChatSession, User
from app.routes.auth import get_current_user
from app.schemas.schemas import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
    ChatSessionUpdate,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def _require_session(db: Session, current_user: User, session_id: str) -> ChatSession:
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return chat_session


@router.post("", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSession:
    session_id = payload.session_id or str(uuid4())
    existing = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chat session already exists")

    chat_session = ChatSession(session_id=session_id, title=payload.title, user_id=current_user.id, history_meta=[])
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


@router.get("", response_model=list[ChatSessionRead])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


@router.get("/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSession:
    return _require_session(db, current_user, session_id)


@router.patch("/{session_id}", response_model=ChatSessionRead)
def update_chat_session(
    session_id: str,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSession:
    chat_session = _require_session(db, current_user, session_id)
    if payload.title is not None:
        chat_session.title = payload.title
    db.commit()
    db.refresh(chat_session)
    return chat_session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    chat_session = _require_session(db, current_user, session_id)
    db.delete(chat_session)
    db.commit()


@router.post("/{session_id}/messages", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def create_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessage:
    chat_session = _require_session(db, current_user, session_id)
    message = ChatMessage(
        session_id=chat_session.id,
        role=payload.role,
        content=payload.content,
        payload_json=payload.payload_json,
    )
    db.add(message)
    history_meta = list(chat_session.history_meta or [])
    history_meta.append({"role": payload.role, "content": payload.content})
    chat_session.history_meta = history_meta[-30:]
    db.commit()
    db.refresh(message)
    return message


@router.get("/{session_id}/messages", response_model=list[ChatMessageRead])
def list_chat_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    chat_session = _require_session(db, current_user, session_id)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
