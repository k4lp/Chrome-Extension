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

    PENDING = "pending"
    ONGOING = "ongoing"
    PAUSED = "paused"
    COMPLETED = "completed"


class GoalStatus(str, enum.Enum):
    """Goal status enum."""

    PENDING = "pending"
    COMPLETED = "completed"


class AutomationTrigger(str, enum.Enum):
    """Automation trigger enum."""

    ON_APP_START = "on_app_start"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


class Task(Base):
    """Task model for iterative reasoning workflow."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)  # What needs to be done
    notes = Column(Text, default="")  # LLM annotations
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status})>"


class Memory(Base):
    """Memory model for storing hints, clues, and data."""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)  # Memory content
    notes = Column(Text, default="")  # LLM annotations
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Memory(id={self.id})>"


class Goal(Base):
    """Goal model for final output verification."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)  # Goal description
    notes = Column(Text, default="")  # LLM annotations
    status = Column(SQLEnum(GoalStatus), default=GoalStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, status={self.status})>"


class Datavault(Base):
    """Datavault model for storing large blobs of data."""

    __tablename__ = "datavault"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)  # Large blob (code/text/output)
    filetype = Column(String(50), default="text")  # text, py, js, json, md, etc.
    notes = Column(Text, default="")  # LLM annotations
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Datavault(id={self.id}, filetype={self.filetype})>"


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
