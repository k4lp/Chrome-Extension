"""High-level services for business logic."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .repository import (
    NoteRepository,
    TaskRepository,
    ProjectRepository,
    MemoryRepository,
    VaultItemRepository,
    AutomationRuleRepository,
)
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
from loguru import logger


class NoteService:
    """Service for note operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_note(
        self,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
        pinned: bool = False,
    ) -> Note:
        """Create a new note.

        Args:
            title: Note title
            content: Note content (markdown)
            tags: List of tags
            pinned: Whether to pin the note

        Returns:
            Created note
        """
        tags_str = ",".join(tags) if tags else ""
        note = NoteRepository.create(self.db, title, content, tags_str, pinned)
        logger.info(f"Created note: {note.title}")
        return note

    def get_note(self, note_id: int) -> Optional[Note]:
        """Get note by ID."""
        return NoteRepository.get_by_id(self.db, note_id)

    def get_all_notes(self, include_archived: bool = False) -> List[Note]:
        """Get all notes."""
        return NoteRepository.get_all(self.db, include_archived)

    def search_notes(self, query: str, include_archived: bool = False) -> List[Note]:
        """Search notes."""
        return NoteRepository.search(self.db, query, include_archived)

    def get_recent_notes(self, limit: int = 10) -> List[Note]:
        """Get recently updated notes."""
        return NoteRepository.get_recent(self.db, limit)

    def get_notes_for_resurfacing(self, days: int = 30, limit: int = 3) -> List[Note]:
        """Get old notes that should be resurfaced."""
        return NoteRepository.get_older_than(self.db, days, limit)

    def update_note(self, note_id: int, **kwargs) -> Optional[Note]:
        """Update note."""
        return NoteRepository.update(self.db, note_id, **kwargs)

    def archive_note(self, note_id: int) -> Optional[Note]:
        """Archive a note."""
        return self.update_note(note_id, archived=True)

    def pin_note(self, note_id: int, pinned: bool = True) -> Optional[Note]:
        """Pin or unpin a note."""
        return self.update_note(note_id, pinned=pinned)

    def delete_note(self, note_id: int) -> bool:
        """Delete a note."""
        return NoteRepository.delete(self.db, note_id)


class TaskService:
    """Service for task operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        title: str,
        status: TaskStatus = TaskStatus.TODO,
        due_date: Optional[datetime] = None,
        note_id: Optional[int] = None,
        project_id: Optional[int] = None,
        project_name: Optional[str] = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title
            status: Task status
            due_date: Due date
            note_id: Associated note ID
            project_id: Associated project ID
            project_name: Associate by project name (creates if doesn't exist)

        Returns:
            Created task
        """
        # Resolve project_name to project_id
        if project_name and not project_id:
            project = ProjectRepository.get_by_name(self.db, project_name)
            if not project:
                project = ProjectRepository.create(self.db, project_name)
                logger.info(f"Created new project: {project_name}")
            project_id = project.id

        task = TaskRepository.create(self.db, title, status, due_date, note_id, project_id)
        logger.info(f"Created task: {task.title}")
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        return TaskRepository.get_by_id(self.db, task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return TaskRepository.get_all(self.db)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return TaskRepository.get_by_status(self.db, status)

    def get_tasks_by_project(self, project_id: int) -> List[Task]:
        """Get tasks by project."""
        return TaskRepository.get_by_project(self.db, project_id)

    def get_today_tasks(self) -> List[Task]:
        """Get tasks due today."""
        return TaskRepository.get_today(self.db)

    def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks."""
        return TaskRepository.get_overdue(self.db)

    def search_tasks(self, query: str) -> List[Task]:
        """Search tasks by title."""
        return TaskRepository.search(self.db, query)

    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Update task."""
        return TaskRepository.update(self.db, task_id, **kwargs)

    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark task as completed."""
        return self.update_task(task_id, status=TaskStatus.DONE)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        return TaskRepository.delete(self.db, task_id)


class ProjectService:
    """Service for project operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_project(
        self,
        name: str,
        description: str = "",
        status: ProjectStatus = ProjectStatus.ACTIVE,
        tags: Optional[List[str]] = None,
    ) -> Project:
        """Create a new project."""
        tags_str = ",".join(tags) if tags else ""
        project = ProjectRepository.create(self.db, name, description, status, tags_str)
        logger.info(f"Created project: {project.name}")
        return project

    def get_project(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        return ProjectRepository.get_by_id(self.db, project_id)

    def get_project_by_name(self, name: str) -> Optional[Project]:
        """Get project by name."""
        return ProjectRepository.get_by_name(self.db, name)

    def get_all_projects(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        """Get all projects."""
        return ProjectRepository.get_all(self.db, status)

    def get_project_summary(self, project_id: int) -> Dict[str, Any]:
        """Get project summary with tasks."""
        project = self.get_project(project_id)
        if not project:
            return {}

        tasks = TaskRepository.get_by_project(self.db, project_id)
        return {
            "project": project,
            "total_tasks": len(tasks),
            "completed_tasks": len([t for t in tasks if t.status == TaskStatus.DONE]),
            "active_tasks": len(
                [t for t in tasks if t.status in (TaskStatus.TODO, TaskStatus.DOING)]
            ),
        }

    def update_project(self, project_id: int, **kwargs) -> Optional[Project]:
        """Update project."""
        return ProjectRepository.update(self.db, project_id, **kwargs)

    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        return ProjectRepository.delete(self.db, project_id)


class MemoryService:
    """Service for memory operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_memory(self, key: str, content: str, importance: int = 3) -> Memory:
        """Create a new memory."""
        memory = MemoryRepository.create(self.db, key, content, importance)
        logger.info(f"Created memory: {key}")
        return memory

    def update_memory(self, key: str, content: str, importance: int = 3) -> Memory:
        """Create or update memory."""
        memory = MemoryRepository.upsert(self.db, key, content, importance)
        logger.info(f"Updated memory: {key}")
        return memory

    def get_memory(self, key: str) -> Optional[Memory]:
        """Get memory by key."""
        return MemoryRepository.get_by_key(self.db, key)

    def get_all_memories(self, min_importance: int = 1) -> List[Memory]:
        """Get all memories."""
        return MemoryRepository.get_all(self.db, min_importance)

    def delete_memory(self, key: str) -> bool:
        """Delete a memory."""
        return MemoryRepository.delete(self.db, key)


class VaultService:
    """Service for vault operations."""

    def __init__(self, db: Session):
        self.db = db

    def add_item(
        self,
        title: str,
        type: VaultItemType,
        path_or_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultItem:
        """Add item to vault."""
        import json

        item_metadata = json.dumps(metadata) if metadata else "{}"
        item = VaultItemRepository.create(self.db, title, type, path_or_url, item_metadata)
        logger.info(f"Added vault item: {title}")
        return item

    def get_item(self, item_id: int) -> Optional[VaultItem]:
        """Get vault item by ID."""
        return VaultItemRepository.get_by_id(self.db, item_id)

    def get_all_items(self, type: Optional[VaultItemType] = None) -> List[VaultItem]:
        """Get all vault items."""
        return VaultItemRepository.get_all(self.db, type)

    def search_items(self, query: str) -> List[VaultItem]:
        """Search vault items by title or path_or_url."""
        return VaultItemRepository.search(self.db, query)

    def update_item(self, item_id: int, **kwargs) -> Optional[VaultItem]:
        """Update vault item.

        Args:
            item_id: Vault item ID
            **kwargs: Fields to update

        Returns:
            Updated vault item or None
        """
        item = VaultItemRepository.update(self.db, item_id, **kwargs)
        if item:
            logger.info(f"Updated vault item: {item.title} (id={item.id})")
        return item

    def delete_item(self, item_id: int) -> bool:
        """Delete vault item."""
        success = VaultItemRepository.delete(self.db, item_id)
        if success:
            logger.info(f"Deleted vault item (id={item_id})")
        return success


class AutomationService:
    """Service for automation operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_rule(
        self,
        name: str,
        trigger: AutomationTrigger,
        agent_task: str,
        enabled: bool = True,
        schedule_cron: Optional[str] = None,
    ) -> AutomationRule:
        """Create automation rule."""
        rule = AutomationRuleRepository.create(
            self.db, name, trigger, agent_task, enabled, schedule_cron
        )
        logger.info(f"Created automation rule: {name}")
        return rule

    def get_rule(self, name: str) -> Optional[AutomationRule]:
        """Get automation rule by name."""
        return AutomationRuleRepository.get_by_name(self.db, name)

    def get_all_rules(self, enabled_only: bool = False) -> List[AutomationRule]:
        """Get all automation rules."""
        return AutomationRuleRepository.get_all(self.db, enabled_only)

    def update_last_run(self, rule_id: int) -> Optional[AutomationRule]:
        """Update last run timestamp."""
        return AutomationRuleRepository.update_last_run(self.db, rule_id)

    def enable_rule(self, rule_id: int, enabled: bool = True) -> Optional[AutomationRule]:
        """Enable or disable rule."""
        return AutomationRuleRepository.update(self.db, rule_id, enabled=enabled)

    def delete_rule(self, rule_id: int) -> bool:
        """Delete automation rule."""
        return AutomationRuleRepository.delete(self.db, rule_id)
