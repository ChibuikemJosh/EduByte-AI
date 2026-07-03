from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Many-to-Many Association Table for the Knowledge Graph
# Maps which Module is a prerequisite for another Module
prerequisite_edges = Table(
    "prerequisite_edges",
    Base.metadata,
    Column("parent_id", Integer, ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", Integer, ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=False, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, unique=True, nullable=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    progress_records = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    content_body = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    prerequisites = relationship(
        "Module",
        secondary=prerequisite_edges,
        primaryjoin="Module.id == prerequisite_edges.c.child_id",
        secondaryjoin="Module.id == prerequisite_edges.c.parent_id",
        backref="dependent_modules",
    )

    progress_records = relationship("UserProgress", back_populates="module", cascade="all, delete-orphan")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="LOCKED", nullable=False)
    quiz_score = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="progress_records")
    module = relationship("Module", back_populates="progress_records")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String(255), default="New Chat", nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    history_meta = Column(JSON, default=list, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="chat_sessions")
