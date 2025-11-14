"""High-level services for business logic."""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

from .repository import (
    TaskRepository,
    MemoryRepository,
    GoalRepository,
    DatavaultRepository,
    AutomationRuleRepository,
)
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
from loguru import logger


class TaskService:
    """Service for task operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        content: str,
        notes: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        """Create a new task.

        Args:
            content: Task content (what needs to be done)
            notes: LLM annotations
            status: Task status

        Returns:
            Created task
        """
        task = TaskRepository.create(self.db, content, notes, status)
        logger.info(f"Created task: {task.id}")
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        return TaskRepository.get_by_id(self.db, task_id)

    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        return TaskRepository.get_all(self.db, status)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks filtered by status.

        Args:
            status: Task status to filter by

        Returns:
            List of tasks with the specified status
        """
        return self.get_all_tasks(status)

    def get_today_tasks(self) -> List[Task]:
        """Get tasks created or updated today.

        Returns:
            List of tasks from today
        """
        today = date.today()
        all_tasks = TaskRepository.get_all(self.db)

        # Filter tasks created or updated today
        today_tasks = [
            task for task in all_tasks
            if (task.created_at.date() == today or task.updated_at.date() == today)
        ]

        return today_tasks

    def search_tasks(self, query: str) -> List[Task]:
        """Search tasks by content or notes."""
        return TaskRepository.search(self.db, query)

    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Update task."""
        return TaskRepository.update(self.db, task_id, **kwargs)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        return TaskRepository.delete(self.db, task_id)


class MemoryService:
    """Service for memory operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_memory(self, content: str, notes: str = "") -> Memory:
        """Create a new memory.

        Args:
            content: Memory content
            notes: LLM annotations

        Returns:
            Created memory
        """
        memory = MemoryRepository.create(self.db, content, notes)
        logger.info(f"Created memory: {memory.id}")
        return memory

    def get_memory(self, memory_id: int) -> Optional[Memory]:
        """Get memory by ID."""
        return MemoryRepository.get_by_id(self.db, memory_id)

    def get_all_memories(self, limit: Optional[int] = None) -> List[Memory]:
        """Get all memories.

        Args:
            limit: Optional limit on number of memories to return

        Returns:
            List of memories (limited if specified)
        """
        memories = MemoryRepository.get_all(self.db)
        if limit:
            return memories[:limit]
        return memories

    def search_memories(self, query: str) -> List[Memory]:
        """Search memories by content or notes."""
        return MemoryRepository.search(self.db, query)

    def update_memory(self, memory_id: int, **kwargs) -> Optional[Memory]:
        """Update memory."""
        return MemoryRepository.update(self.db, memory_id, **kwargs)

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory."""
        return MemoryRepository.delete(self.db, memory_id)


class GoalService:
    """Service for goal operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_goal(
        self,
        content: str,
        notes: str = "",
        status: GoalStatus = GoalStatus.PENDING,
    ) -> Goal:
        """Create a new goal.

        Args:
            content: Goal description
            notes: LLM annotations
            status: Goal status

        Returns:
            Created goal
        """
        goal = GoalRepository.create(self.db, content, notes, status)
        logger.info(f"Created goal: {goal.id}")
        return goal

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """Get goal by ID."""
        return GoalRepository.get_by_id(self.db, goal_id)

    def get_all_goals(self, status: Optional[GoalStatus] = None) -> List[Goal]:
        """Get all goals, optionally filtered by status."""
        return GoalRepository.get_all(self.db, status)

    def search_goals(self, query: str) -> List[Goal]:
        """Search goals by content or notes."""
        return GoalRepository.search(self.db, query)

    def update_goal(self, goal_id: int, **kwargs) -> Optional[Goal]:
        """Update goal."""
        return GoalRepository.update(self.db, goal_id, **kwargs)

    def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal."""
        return GoalRepository.delete(self.db, goal_id)


class DatavaultService:
    """Service for datavault operations."""

    def __init__(self, db: Session):
        self.db = db

    def store_item(
        self,
        content: str,
        filetype: str = "text",
        notes: str = "",
    ) -> Datavault:
        """Store item in datavault.

        Args:
            content: Content to store (large blob)
            filetype: File type (text, py, js, json, md, etc.)
            notes: LLM annotations

        Returns:
            Created datavault item
        """
        item = DatavaultRepository.create(self.db, content, filetype, notes)
        logger.info(f"Stored datavault item: {item.id} (type: {filetype})")
        return item

    def get_item(self, item_id: int) -> Optional[Datavault]:
        """Get datavault item by ID."""
        return DatavaultRepository.get_by_id(self.db, item_id)

    def get_all_items(self, filetype: Optional[str] = None) -> List[Datavault]:
        """Get all datavault items, optionally filtered by filetype."""
        return DatavaultRepository.get_all(self.db, filetype)

    def search_items(self, query: str) -> List[Datavault]:
        """Search datavault items by content or notes."""
        return DatavaultRepository.search(self.db, query)

    def update_item(self, item_id: int, **kwargs) -> Optional[Datavault]:
        """Update datavault item."""
        item = DatavaultRepository.update(self.db, item_id, **kwargs)
        if item:
            logger.info(f"Updated datavault item: {item.id}")
        return item

    def delete_item(self, item_id: int) -> bool:
        """Delete datavault item."""
        success = DatavaultRepository.delete(self.db, item_id)
        if success:
            logger.info(f"Deleted datavault item: {item_id}")
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
