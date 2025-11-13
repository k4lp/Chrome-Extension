"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from .db import Base


class TaskStatus(str, enum.Enum):
    """Task status enum."""

    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    STALE = "stale"


class ProjectStatus(str, enum.Enum):
    """Project status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class VaultItemType(str, enum.Enum):
    """Vault item type enum."""

    FILE = "file"
    URL = "url"
    SNIPPET = "snippet"
    OTHER = "other"


class AutomationTrigger(str, enum.Enum):
    """Automation trigger enum."""

    ON_APP_START = "on_app_start"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


class Note(Base):
    """Note model."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    tags = Column(String(1000), default="")  # Comma-separated tags
    pinned = Column(Boolean, default=False, index=True)
    archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    tasks = relationship("Task", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Note(id={self.id}, title='{self.title}')>"


class Task(Base):
    """Task model."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Foreign keys
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    note = relationship("Note", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status={self.status})>"


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(
        SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE, nullable=False, index=True
    )
    tags = Column(String(1000), default="")  # Comma-separated tags
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status={self.status})>"


class Memory(Base):
    """Memory (long-term facts) model."""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=3, nullable=False)  # 1-5 scale
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Memory(id={self.id}, key='{self.key}', importance={self.importance})>"


class VaultItem(Base):
    """Vault item model."""

    __tablename__ = "vault_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    type = Column(SQLEnum(VaultItemType), default=VaultItemType.OTHER, nullable=False, index=True)
    path_or_url = Column(String(2000), nullable=False)
    metadata = Column(Text, default="{}")  # JSON string
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<VaultItem(id={self.id}, title='{self.title}', type={self.type})>"


class AutomationRule(Base):
    """Automation rule model."""

    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    trigger = Column(
        SQLEnum(AutomationTrigger), default=AutomationTrigger.MANUAL, nullable=False, index=True
    )
    schedule_cron = Column(String(100), nullable=True)  # For custom schedules
    agent_task = Column(Text, nullable=False)  # Instruction for agent
    last_run_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<AutomationRule(id={self.id}, name='{self.name}', enabled={self.enabled})>"
