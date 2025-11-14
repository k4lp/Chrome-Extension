"""Repository layer for database operations."""

from typing import List, Optional, TypeVar, Generic, Type
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

# Generic type for models
T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    This eliminates ~150 lines of duplicated code across repositories.
    """

    def __init__(self, model: Type[T]):
        """Initialize with model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def get_by_id(self, db: Session, item_id: int) -> Optional[T]:
        """Get item by ID.

        Args:
            db: Database session
            item_id: Item ID

        Returns:
            Item or None
        """
        return db.query(self.model).filter(self.model.id == item_id).first()

    def search(self, db: Session, query_text: str, *search_fields) -> List[T]:
        """Search items by specified fields.

        Args:
            db: Database session
            query_text: Search query
            *search_fields: Field names to search in

        Returns:
            List of matching items
        """
        search_pattern = f"%{query_text}%"
        filters = [getattr(self.model, field).ilike(search_pattern) for field in search_fields]

        # Determine order by field (prefer created_at, fallback to updated_at)
        order_by_field = self.model.created_at if hasattr(self.model, 'created_at') else self.model.updated_at

        return (
            db.query(self.model)
            .filter(or_(*filters))
            .order_by(order_by_field.desc())
            .all()
        )

    def update(self, db: Session, item_id: int, **kwargs) -> Optional[T]:
        """Update item fields.

        Args:
            db: Database session
            item_id: Item ID
            **kwargs: Fields to update

        Returns:
            Updated item or None
        """
        item = self.get_by_id(db, item_id)
        if not item:
            return None

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        # Auto-update updated_at if present
        if hasattr(item, 'updated_at'):
            item.updated_at = datetime.now()

        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, item_id: int) -> bool:
        """Delete an item.

        Args:
            db: Database session
            item_id: Item ID

        Returns:
            True if deleted, False if not found
        """
        item = self.get_by_id(db, item_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True

    def delete_all(self, db: Session) -> int:
        """Delete all items of this type.

        Args:
            db: Database session

        Returns:
            Number of items deleted
        """
        count = db.query(self.model).count()
        db.query(self.model).delete()
        db.commit()
        return count


class TaskRepository:
    """Repository for Task operations."""

    _base = BaseRepository(Task)

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
        return TaskRepository._base.get_by_id(db, task_id)

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
        return TaskRepository._base.search(db, query_text, 'content', 'notes')

    @staticmethod
    def update(db: Session, task_id: int, **kwargs) -> Optional[Task]:
        """Update task fields."""
        return TaskRepository._base.update(db, task_id, **kwargs)

    @staticmethod
    def delete(db: Session, task_id: int) -> bool:
        """Delete a task."""
        return TaskRepository._base.delete(db, task_id)

    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all tasks.

        Returns:
            Number of tasks deleted
        """
        return TaskRepository._base.delete_all(db)


class MemoryRepository:
    """Repository for Memory operations."""

    _base = BaseRepository(Memory)

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
        return MemoryRepository._base.get_by_id(db, memory_id)

    @staticmethod
    def get_all(db: Session) -> List[Memory]:
        """Get all memories."""
        return db.query(Memory).order_by(Memory.updated_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[Memory]:
        """Search memories by content or notes."""
        return MemoryRepository._base.search(db, query_text, 'content', 'notes')

    @staticmethod
    def update(db: Session, memory_id: int, **kwargs) -> Optional[Memory]:
        """Update memory fields."""
        return MemoryRepository._base.update(db, memory_id, **kwargs)

    @staticmethod
    def delete(db: Session, memory_id: int) -> bool:
        """Delete a memory."""
        return MemoryRepository._base.delete(db, memory_id)

    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all memories.

        Returns:
            Number of memories deleted
        """
        return MemoryRepository._base.delete_all(db)


class GoalRepository:
    """Repository for Goal operations."""

    _base = BaseRepository(Goal)

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
        return GoalRepository._base.get_by_id(db, goal_id)

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
        return GoalRepository._base.search(db, query_text, 'content', 'notes')

    @staticmethod
    def update(db: Session, goal_id: int, **kwargs) -> Optional[Goal]:
        """Update goal fields."""
        return GoalRepository._base.update(db, goal_id, **kwargs)

    @staticmethod
    def delete(db: Session, goal_id: int) -> bool:
        """Delete a goal."""
        return GoalRepository._base.delete(db, goal_id)

    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all goals.

        Returns:
            Number of goals deleted
        """
        return GoalRepository._base.delete_all(db)


class DatavaultRepository:
    """Repository for Datavault operations."""

    _base = BaseRepository(Datavault)

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
        return DatavaultRepository._base.get_by_id(db, item_id)

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
        return DatavaultRepository._base.search(db, query_text, 'content', 'notes')

    @staticmethod
    def update(db: Session, item_id: int, **kwargs) -> Optional[Datavault]:
        """Update datavault item fields."""
        return DatavaultRepository._base.update(db, item_id, **kwargs)

    @staticmethod
    def delete(db: Session, item_id: int) -> bool:
        """Delete a datavault item."""
        return DatavaultRepository._base.delete(db, item_id)

    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all datavault items.

        Returns:
            Number of items deleted
        """
        return DatavaultRepository._base.delete_all(db)


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
