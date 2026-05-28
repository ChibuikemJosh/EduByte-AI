from datetime import datetime
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
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, unique=True, nullable=True, index=True) # Optional for WhatsApp integration
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(datetime.timezone.utc))

    # Relationships
    progress_records = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)  # e.g., "Mathematics", "Computer Science"
    content_body = Column(String, nullable=True) # The core AI-generated study material
    created_at = Column(DateTime, default=datetime.now(datetime.timezone.utc))

    # Graph Relationship: Self-referential many-to-many
    prerequisites = relationship(
        "Module",
        secondary=prerequisite_edges,
        primaryjoin=id == prerequisite_edges.c.child_id,
        secondaryjoin=id == prerequisite_edges.c.parent_id,
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
    updated_at = Column(DateTime, default=datetime.now(datetime.timezone.utc), onupdate=datetime.now(datetime.timezone.utc))

    # Relationships
    user = relationship("User", back_populates="progress_records")
    module = relationship("Module", back_populates="progress_records")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True) # Generated UUID or WhatsApp Phone Number
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Store complete raw chat history as a highly optimized compressed JSONB Array
    # Matches perfectly with what your classmate's TurboQuant or basic history state needs.
    history_meta = Column(JSONB, default=[], nullable=False) 
    updated_at = Column(DateTime, default=datetime.now(datetime.timezone.utc), onupdate=datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="chat_sessions")