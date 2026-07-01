from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

# Many-to-Many Association Table for the Knowledge Graph
# Maps which Module is a prerequisite for another Module
prerequisite_edges = Table(
    "prerequisite_edges",
    Base.metadata,
    Column("parent_id", Integer, ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", Integer, ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=False, nullable=False, index=True) # Set unique=True if names must be unique
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, unique=True, nullable=True, index=True) # Optional for WhatsApp integration
    password_hash = Column(String, nullable=False)
    
    # 💡 FIX: Wrapped in lambda to evaluate dynamically on creation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    progress_records = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)  # e.g., "Mathematics", "Computer Science"
    content_body = Column(String, nullable=True) # The core AI-generated study material
    
    # 💡 FIX: Wrapped in lambda
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Graph Relationship: Self-referential many-to-many
    # 💡 FIX: Explicitly used class string names to prevent binding compilation errors
    prerequisites = relationship(
        "Module",
        secondary=prerequisite_edges,
        primaryjoin="Module.id == prerequisite_edges.c.child_id",
        secondaryjoin="Module.id == prerequisite_edges.c.parent_id",
        backref="dependent_modules"
    )
    
    progress_records = relationship("UserProgress", back_populates="module", cascade="all, delete-orphan")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    
    # Adaptive states: 'LOCKED', 'UNLOCKED', 'COMPLETED'
    status = Column(String, default="LOCKED", nullable=False)
    quiz_score = Column(Integer, nullable=True) # Out of 100, stored when they pass the gate
    
    # 💡 FIX: Dynamic timestamp parameters on both standard insert and record update actions
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="progress_records")
    module = relationship("Module", back_populates="progress_records")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # 💡 FIX: Moved comment back to its correct context field
    session_id = Column(String, unique=True, nullable=False, index=True) # Generated UUID or WhatsApp Phone Number
    
    # Dynamically generated chat title for user-facing history lists
    title = Column(String(255), default="New Chat", nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Store complete raw chat history as a highly optimized compressed JSONB Array
    history_meta = Column(JSONB, default=[], nullable=False) 
    
    # 💡 FIX: Setup dynamically executed callables
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="chat_sessions")