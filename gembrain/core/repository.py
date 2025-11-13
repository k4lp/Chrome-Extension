"""Repository layer for database operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from .models import (
    Task,
    Memory,
    Goal,
    Datavault,
    AutomationRule,
    TaskStatus,
    GoalStatus,
    AutomationTrigger,
)


class TaskRepository:
    """Repository for Task operations."""

    @staticmethod
    def create(
        db: Session,
        content: str,
        notes: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        """Create a new task."""
        task = Task(content=content, notes=notes, status=status)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_all(db: Session, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        query = db.query(Task)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[Task]:
        """Search tasks by content or notes."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(Task)
            .filter(
                or_(
                    Task.content.ilike(search_pattern),
                    Task.notes.ilike(search_pattern),
                )
            )
            .order_by(Task.created_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, task_id: int, **kwargs) -> Optional[Task]:
        """Update task fields."""
        task = TaskRepository.get_by_id(db, task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task_id: int) -> bool:
        """Delete a task."""
        task = TaskRepository.get_by_id(db, task_id)
        if not task:
            return False
        db.delete(task)
        db.commit()
        return True


class MemoryRepository:
    """Repository for Memory operations."""

    @staticmethod
    def create(db: Session, content: str, notes: str = "") -> Memory:
        """Create a new memory."""
        memory = Memory(content=content, notes=notes)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def get_by_id(db: Session, memory_id: int) -> Optional[Memory]:
        """Get memory by ID."""
        return db.query(Memory).filter(Memory.id == memory_id).first()

    @staticmethod
    def get_all(db: Session) -> List[Memory]:
        """Get all memories."""
        return db.query(Memory).order_by(Memory.updated_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[Memory]:
        """Search memories by content or notes."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(Memory)
            .filter(
                or_(
                    Memory.content.ilike(search_pattern),
                    Memory.notes.ilike(search_pattern),
                )
            )
            .order_by(Memory.updated_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, memory_id: int, **kwargs) -> Optional[Memory]:
        """Update memory fields."""
        memory = MemoryRepository.get_by_id(db, memory_id)
        if not memory:
            return None
        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        memory.updated_at = datetime.now()
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def delete(db: Session, memory_id: int) -> bool:
        """Delete a memory."""
        memory = MemoryRepository.get_by_id(db, memory_id)
        if not memory:
            return False
        db.delete(memory)
        db.commit()
        return True


class GoalRepository:
    """Repository for Goal operations."""

    @staticmethod
    def create(
        db: Session,
        content: str,
        notes: str = "",
        status: GoalStatus = GoalStatus.PENDING,
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(content=content, notes=notes, status=status)
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def get_by_id(db: Session, goal_id: int) -> Optional[Goal]:
        """Get goal by ID."""
        return db.query(Goal).filter(Goal.id == goal_id).first()

    @staticmethod
    def get_all(db: Session, status: Optional[GoalStatus] = None) -> List[Goal]:
        """Get all goals, optionally filtered by status."""
        query = db.query(Goal)
        if status:
            query = query.filter(Goal.status == status)
        return query.order_by(Goal.created_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[Goal]:
        """Search goals by content or notes."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(Goal)
            .filter(
                or_(
                    Goal.content.ilike(search_pattern),
                    Goal.notes.ilike(search_pattern),
                )
            )
            .order_by(Goal.created_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, goal_id: int, **kwargs) -> Optional[Goal]:
        """Update goal fields."""
        goal = GoalRepository.get_by_id(db, goal_id)
        if not goal:
            return None
        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)
        goal.updated_at = datetime.now()
        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def delete(db: Session, goal_id: int) -> bool:
        """Delete a goal."""
        goal = GoalRepository.get_by_id(db, goal_id)
        if not goal:
            return False
        db.delete(goal)
        db.commit()
        return True


class DatavaultRepository:
    """Repository for Datavault operations."""

    @staticmethod
    def create(
        db: Session,
        content: str,
        filetype: str = "text",
        notes: str = "",
    ) -> Datavault:
        """Create a new datavault item."""
        item = Datavault(content=content, filetype=filetype, notes=notes)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_by_id(db: Session, item_id: int) -> Optional[Datavault]:
        """Get datavault item by ID."""
        return db.query(Datavault).filter(Datavault.id == item_id).first()

    @staticmethod
    def get_all(db: Session, filetype: Optional[str] = None) -> List[Datavault]:
        """Get all datavault items, optionally filtered by filetype."""
        query = db.query(Datavault)
        if filetype:
            query = query.filter(Datavault.filetype == filetype)
        return query.order_by(Datavault.created_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[Datavault]:
        """Search datavault items by content or notes."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(Datavault)
            .filter(
                or_(
                    Datavault.content.ilike(search_pattern),
                    Datavault.notes.ilike(search_pattern),
                )
            )
            .order_by(Datavault.created_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, item_id: int, **kwargs) -> Optional[Datavault]:
        """Update datavault item fields."""
        item = DatavaultRepository.get_by_id(db, item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.updated_at = datetime.now()
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item_id: int) -> bool:
        """Delete a datavault item."""
        item = DatavaultRepository.get_by_id(db, item_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


class AutomationRuleRepository:
    """Repository for AutomationRule operations."""

    @staticmethod
    def create(
        db: Session,
        name: str,
        trigger: AutomationTrigger,
        agent_task: str,
        enabled: bool = True,
        schedule_cron: Optional[str] = None,
    ) -> AutomationRule:
        """Create a new automation rule."""
        rule = AutomationRule(
            name=name,
            trigger=trigger,
            agent_task=agent_task,
            enabled=enabled,
            schedule_cron=schedule_cron,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[AutomationRule]:
        """Get automation rule by name."""
        return db.query(AutomationRule).filter(AutomationRule.name == name).first()

    @staticmethod
    def get_all(db: Session, enabled_only: bool = False) -> List[AutomationRule]:
        """Get all automation rules."""
        query = db.query(AutomationRule)
        if enabled_only:
            query = query.filter(AutomationRule.enabled == True)
        return query.order_by(AutomationRule.name).all()

    @staticmethod
    def update_last_run(db: Session, rule_id: int) -> Optional[AutomationRule]:
        """Update last run timestamp."""
        rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            return None
        rule.last_run_at = datetime.now()
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def update(db: Session, rule_id: int, **kwargs) -> Optional[AutomationRule]:
        """Update automation rule fields."""
        rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            return None
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete(db: Session, rule_id: int) -> bool:
        """Delete an automation rule."""
        rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            return False
        db.delete(rule)
        db.commit()
        return True
