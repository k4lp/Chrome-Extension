"""Repository layer for database operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from .models import (
    Note,
    Task,
    Project,
    Memory,
    VaultItem,
    AutomationRule,
    TaskStatus,
    ProjectStatus,
    VaultItemType,
    AutomationTrigger,
)


class NoteRepository:
    """Repository for Note operations."""

    @staticmethod
    def create(
        db: Session,
        title: str,
        content: str = "",
        tags: str = "",
        pinned: bool = False,
    ) -> Note:
        """Create a new note."""
        note = Note(title=title, content=content, tags=tags, pinned=pinned)
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def get_by_id(db: Session, note_id: int) -> Optional[Note]:
        """Get note by ID."""
        return db.query(Note).filter(Note.id == note_id).first()

    @staticmethod
    def get_all(db: Session, include_archived: bool = False) -> List[Note]:
        """Get all notes."""
        query = db.query(Note)
        if not include_archived:
            query = query.filter(Note.archived == False)
        return query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str, include_archived: bool = False) -> List[Note]:
        """Search notes by title or content."""
        search_pattern = f"%{query_text}%"
        query = db.query(Note).filter(
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
                Note.tags.ilike(search_pattern),
            )
        )
        if not include_archived:
            query = query.filter(Note.archived == False)
        return query.order_by(Note.updated_at.desc()).all()

    @staticmethod
    def get_by_tags(db: Session, tags: List[str]) -> List[Note]:
        """Get notes by tags."""
        query = db.query(Note).filter(Note.archived == False)
        for tag in tags:
            query = query.filter(Note.tags.ilike(f"%{tag}%"))
        return query.order_by(Note.updated_at.desc()).all()

    @staticmethod
    def get_recent(db: Session, limit: int = 10) -> List[Note]:
        """Get recently updated notes."""
        return (
            db.query(Note)
            .filter(Note.archived == False)
            .order_by(Note.updated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_older_than(db: Session, days: int, limit: int = 10) -> List[Note]:
        """Get notes older than N days."""
        from ..utils.time import days_ago

        cutoff = days_ago(days)
        return (
            db.query(Note)
            .filter(Note.archived == False, Note.updated_at < cutoff)
            .order_by(Note.updated_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, note_id: int, **kwargs) -> Optional[Note]:
        """Update note fields."""
        note = NoteRepository.get_by_id(db, note_id)
        if not note:
            return None
        for key, value in kwargs.items():
            if hasattr(note, key):
                setattr(note, key, value)
        note.updated_at = datetime.now()
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def delete(db: Session, note_id: int) -> bool:
        """Delete a note."""
        note = NoteRepository.get_by_id(db, note_id)
        if not note:
            return False
        db.delete(note)
        db.commit()
        return True


class TaskRepository:
    """Repository for Task operations."""

    @staticmethod
    def create(
        db: Session,
        title: str,
        status: TaskStatus = TaskStatus.TODO,
        due_date: Optional[datetime] = None,
        note_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            title=title,
            status=status,
            due_date=due_date,
            note_id=note_id,
            project_id=project_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_all(db: Session) -> List[Task]:
        """Get all tasks."""
        return db.query(Task).order_by(Task.created_at.desc()).all()

    @staticmethod
    def get_by_status(db: Session, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return db.query(Task).filter(Task.status == status).order_by(Task.created_at.desc()).all()

    @staticmethod
    def get_by_project(db: Session, project_id: int) -> List[Task]:
        """Get tasks by project."""
        return (
            db.query(Task)
            .filter(Task.project_id == project_id)
            .order_by(Task.created_at.desc())
            .all()
        )

    @staticmethod
    def get_today(db: Session) -> List[Task]:
        """Get tasks due today."""
        today = datetime.now().date()
        return (
            db.query(Task)
            .filter(
                and_(
                    Task.due_date.isnot(None),
                    Task.status != TaskStatus.DONE,
                )
            )
            .filter(
                and_(
                    Task.due_date >= datetime.combine(today, datetime.min.time()),
                    Task.due_date < datetime.combine(today, datetime.max.time()),
                )
            )
            .all()
        )

    @staticmethod
    def get_overdue(db: Session) -> List[Task]:
        """Get overdue tasks."""
        now = datetime.now()
        return (
            db.query(Task)
            .filter(
                and_(
                    Task.due_date.isnot(None),
                    Task.due_date < now,
                    Task.status != TaskStatus.DONE,
                )
            )
            .all()
        )

    @staticmethod
    def search(db: Session, query_text: str) -> List[Task]:
        """Search tasks by title."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(Task)
            .filter(Task.title.ilike(search_pattern))
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
        # Set completed_at when status changes to DONE
        if "status" in kwargs and kwargs["status"] == TaskStatus.DONE:
            task.completed_at = datetime.now()
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


class ProjectRepository:
    """Repository for Project operations."""

    @staticmethod
    def create(
        db: Session,
        name: str,
        description: str = "",
        status: ProjectStatus = ProjectStatus.ACTIVE,
        tags: str = "",
    ) -> Project:
        """Create a new project."""
        project = Project(name=name, description=description, status=status, tags=tags)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Project]:
        """Get project by name."""
        return db.query(Project).filter(Project.name == name).first()

    @staticmethod
    def get_all(db: Session, status: Optional[ProjectStatus] = None) -> List[Project]:
        """Get all projects, optionally filtered by status."""
        query = db.query(Project)
        if status:
            query = query.filter(Project.status == status)
        return query.order_by(Project.updated_at.desc()).all()

    @staticmethod
    def update(db: Session, project_id: int, **kwargs) -> Optional[Project]:
        """Update project fields."""
        project = ProjectRepository.get_by_id(db, project_id)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        project.updated_at = datetime.now()
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project_id: int) -> bool:
        """Delete a project."""
        project = ProjectRepository.get_by_id(db, project_id)
        if not project:
            return False
        db.delete(project)
        db.commit()
        return True


class MemoryRepository:
    """Repository for Memory operations."""

    @staticmethod
    def create(db: Session, key: str, content: str, importance: int = 3) -> Memory:
        """Create a new memory."""
        memory = Memory(key=key, content=content, importance=importance)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def get_by_key(db: Session, key: str) -> Optional[Memory]:
        """Get memory by key."""
        return db.query(Memory).filter(Memory.key == key).first()

    @staticmethod
    def get_all(db: Session, min_importance: int = 1) -> List[Memory]:
        """Get all memories with minimum importance."""
        return (
            db.query(Memory)
            .filter(Memory.importance >= min_importance)
            .order_by(Memory.importance.desc(), Memory.updated_at.desc())
            .all()
        )

    @staticmethod
    def upsert(db: Session, key: str, content: str, importance: int = 3) -> Memory:
        """Create or update memory."""
        memory = MemoryRepository.get_by_key(db, key)
        if memory:
            memory.content = content
            memory.importance = importance
            memory.updated_at = datetime.now()
            db.commit()
            db.refresh(memory)
            return memory
        else:
            return MemoryRepository.create(db, key, content, importance)

    @staticmethod
    def delete(db: Session, key: str) -> bool:
        """Delete a memory."""
        memory = MemoryRepository.get_by_key(db, key)
        if not memory:
            return False
        db.delete(memory)
        db.commit()
        return True


class VaultItemRepository:
    """Repository for VaultItem operations."""

    @staticmethod
    def create(
        db: Session,
        title: str,
        type: VaultItemType,
        path_or_url: str,
        item_metadata: str = "{}",
    ) -> VaultItem:
        """Create a new vault item."""
        item = VaultItem(title=title, type=type, path_or_url=path_or_url, item_metadata=item_metadata)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_by_id(db: Session, item_id: int) -> Optional[VaultItem]:
        """Get vault item by ID."""
        return db.query(VaultItem).filter(VaultItem.id == item_id).first()

    @staticmethod
    def get_all(db: Session, type: Optional[VaultItemType] = None) -> List[VaultItem]:
        """Get all vault items, optionally filtered by type."""
        query = db.query(VaultItem)
        if type:
            query = query.filter(VaultItem.type == type)
        return query.order_by(VaultItem.created_at.desc()).all()

    @staticmethod
    def search(db: Session, query_text: str) -> List[VaultItem]:
        """Search vault items by title or path_or_url."""
        search_pattern = f"%{query_text}%"
        return (
            db.query(VaultItem)
            .filter(
                or_(
                    VaultItem.title.ilike(search_pattern),
                    VaultItem.path_or_url.ilike(search_pattern),
                )
            )
            .order_by(VaultItem.created_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, item_id: int, **kwargs) -> Optional[VaultItem]:
        """Update vault item fields.

        Args:
            db: Database session
            item_id: Vault item ID
            **kwargs: Fields to update (title, path_or_url, item_metadata)

        Returns:
            Updated vault item or None
        """
        item = VaultItemRepository.get_by_id(db, item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item_id: int) -> bool:
        """Delete a vault item."""
        item = VaultItemRepository.get_by_id(db, item_id)
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
