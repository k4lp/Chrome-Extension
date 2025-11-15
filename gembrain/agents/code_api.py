"""API bindings for Python code execution - allows executed code to use GemBrain features."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class GemBrainAPI:
    """API for code execution to interact with GemBrain data structures.

    This allows executed code to directly create/update/delete tasks, memories, goals,
    and datavault items without returning large data to the LLM (avoiding token limits).
    """

    def __init__(self, db_session, services: Dict[str, Any]):
        """Initialize API with database session and services.

        Args:
            db_session: SQLAlchemy database session
            services: Dictionary of service instances
        """
        self.db = db_session
        self.task_service = services.get("task_service")
        self.memory_service = services.get("memory_service")
        self.goal_service = services.get("goal_service")
        self.datavault_service = services.get("datavault_service")

    # =========================================================================
    # HELPER METHODS (Reduce ~200 lines of duplicated dictification logic)
    # =========================================================================

    def _to_dict_basic(self, item, include_updated_at: bool = False) -> Dict[str, Any]:
        """Convert item to basic dict (id, content, notes, created_at).

        Args:
            item: Model instance
            include_updated_at: Include updated_at field

        Returns:
            Dictionary representation
        """
        result = {
            "id": item.id,
            "content": item.content,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
        }
        if include_updated_at:
            result["updated_at"] = item.updated_at.isoformat()
        return result

    def _to_dict_with_status(self, item, include_updated_at: bool = False) -> Dict[str, Any]:
        """Convert item with status to dict.

        Args:
            item: Model instance with status field
            include_updated_at: Include updated_at field

        Returns:
            Dictionary representation
        """
        result = self._to_dict_basic(item, include_updated_at)
        result["status"] = item.status.value
        return result

    def _to_dict_list(self, items, has_status: bool = False) -> List[Dict[str, Any]]:
        """Convert list of items to dicts.

        Args:
            items: List of model instances
            has_status: Whether items have status field

        Returns:
            List of dictionaries
        """
        if has_status:
            return [self._to_dict_with_status(item) for item in items]
        else:
            return [self._to_dict_basic(item) for item in items]

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    def create_task(self, content: str, notes: str = "", status: str = "pending"):
        """Create a new task.

        Args:
            content: What needs to be done
            notes: LLM annotations/notes about the task
            status: pending|ongoing|paused|completed

        Returns:
            Task dict with id, task_id, content, notes, status, created_at
        """
        try:
            from gembrain.core.models import TaskStatus
            status_enum = TaskStatus(status)
            task = self.task_service.create_task(content, notes, status_enum)
            logger.info(f"✅ Code created task: {task.id}")
            return {
                "id": task.id,
                "task_id": task.id,  # For backwards compatibility
                "content": task.content,
                "notes": task.notes,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise

    def get_task(self, task_id: int):
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task dict or None
        """
        task = self.task_service.get_task(task_id)
        if task:
            return {
                "id": task.id,
                "content": task.content,
                "notes": task.notes,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
        return None

    def list_tasks(self, status: Optional[str] = None, limit: int = 50):
        """List all tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending/ongoing/paused/completed)
            limit: Maximum results

        Returns:
            List of task dicts
        """
        from gembrain.core.models import TaskStatus
        status_enum = TaskStatus(status) if status else None
        tasks = self.task_service.get_all_tasks(status_enum)[:limit]
        return [
            {
                "id": t.id,
                "content": t.content,
                "notes": t.notes,
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]

    def search_tasks(self, query: str, limit: int = 20):
        """Search tasks by content or notes.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching task dicts
        """
        tasks = self.task_service.search_tasks(query)[:limit]
        return [
            {
                "id": t.id,
                "content": t.content,
                "notes": t.notes,
                "status": t.status.value,
            }
            for t in tasks
        ]

    def update_task(self, task_id: int, content: Optional[str] = None, notes: Optional[str] = None, status: Optional[str] = None):
        """Update a task.

        Args:
            task_id: Task ID
            content: New content
            notes: New notes
            status: New status (pending/ongoing/paused/completed)

        Returns:
            Updated task dict or None
        """
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if notes is not None:
            kwargs["notes"] = notes
        if status is not None:
            from gembrain.core.models import TaskStatus
            kwargs["status"] = TaskStatus(status)

        task = self.task_service.update_task(task_id, **kwargs)
        if task:
            logger.info(f"✅ Code updated task: {task.id}")
            return {
                "id": task.id,
                "content": task.content,
                "notes": task.notes,
                "status": task.status.value,
            }
        return None

    def delete_task(self, task_id: int):
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            Dict with success status
        """
        success = self.task_service.delete_task(task_id)
        if success:
            logger.info(f"Code deleted task: {task_id}")
        return {"success": success, "task_id": task_id}

    # =========================================================================
    # MEMORY OPERATIONS
    # =========================================================================

    def create_memory(self, content: str, notes: str = ""):
        """Create a new memory.

        Args:
            content: Memory content (hints, clues, data)
            notes: LLM annotations about the memory

        Returns:
            Memory dict with id, content, notes, created_at
        """
        try:
            memory = self.memory_service.create_memory(content, notes)
            logger.info(f"Code created memory: {memory.id}")
            return {
                "id": memory.id,
                "memory_id": memory.id,
                "content": memory.content,
                "notes": memory.notes,
                "created_at": memory.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            raise

    def get_memory(self, memory_id: int):
        """Get memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory dict or None
        """
        memory = self.memory_service.get_memory(memory_id)
        if memory:
            return {
                "id": memory.id,
                "content": memory.content,
                "notes": memory.notes,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
            }
        return None

    def list_memories(self, limit: int = 50):
        """List all memories.

        Args:
            limit: Maximum results

        Returns:
            List of memory dicts
        """
        memories = self.memory_service.get_all_memories()[:limit]
        return [
            {
                "id": m.id,
                "content": m.content,
                "notes": m.notes,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ]

    def search_memories(self, query: str, limit: int = 20):
        """Search memories by content or notes.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memory dicts
        """
        memories = self.memory_service.search_memories(query)[:limit]
        return [
            {
                "id": m.id,
                "content": m.content,
                "notes": m.notes,
            }
            for m in memories
        ]

    def update_memory(self, memory_id: int, content: Optional[str] = None, notes: Optional[str] = None):
        """Update a memory.

        Args:
            memory_id: Memory ID
            content: New content
            notes: New notes

        Returns:
            Updated memory dict or None
        """
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if notes is not None:
            kwargs["notes"] = notes

        memory = self.memory_service.update_memory(memory_id, **kwargs)
        if memory:
            logger.info(f"Code updated memory: {memory.id}")
            return {
                "id": memory.id,
                "memory_id": memory.id,
                "content": memory.content,
                "notes": memory.notes,
            }
        return None

    def delete_memory(self, memory_id: int):
        """Delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Dict with success status
        """
        success = self.memory_service.delete_memory(memory_id)
        if success:
            logger.info(f"Code deleted memory: {memory_id}")
        return {"success": success, "memory_id": memory_id}

    # =========================================================================
    # GOAL OPERATIONS
    # =========================================================================

    def create_goal(self, content: str, notes: str = "", status: str = "pending"):
        """Create a new goal.

        Args:
            content: Goal description
            notes: LLM annotations about the goal
            status: pending|completed

        Returns:
            Goal dict with id, content, notes, status, created_at
        """
        try:
            from gembrain.core.models import GoalStatus
            status_enum = GoalStatus(status)
            goal = self.goal_service.create_goal(content, notes, status_enum)
            logger.info(f"🎯 Code created goal: {goal.id}")
            return {
                "id": goal.id,
                "content": goal.content,
                "notes": goal.notes,
                "status": goal.status.value,
                "created_at": goal.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            raise

    def get_goal(self, goal_id: int):
        """Get goal by ID.

        Args:
            goal_id: Goal ID

        Returns:
            Goal dict or None
        """
        goal = self.goal_service.get_goal(goal_id)
        if goal:
            return {
                "id": goal.id,
                "content": goal.content,
                "notes": goal.notes,
                "status": goal.status.value,
                "created_at": goal.created_at.isoformat(),
                "updated_at": goal.updated_at.isoformat(),
            }
        return None

    def list_goals(self, status: Optional[str] = None, limit: int = 50):
        """List all goals, optionally filtered by status.

        Args:
            status: Filter by status (pending/completed)
            limit: Maximum results

        Returns:
            List of goal dicts
        """
        from gembrain.core.models import GoalStatus
        status_enum = GoalStatus(status) if status else None
        goals = self.goal_service.get_all_goals(status_enum)[:limit]
        return [
            {
                "id": g.id,
                "content": g.content,
                "notes": g.notes,
                "status": g.status.value,
                "created_at": g.created_at.isoformat(),
            }
            for g in goals
        ]

    def search_goals(self, query: str, limit: int = 20):
        """Search goals by content or notes.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching goal dicts
        """
        goals = self.goal_service.search_goals(query)[:limit]
        return [
            {
                "id": g.id,
                "content": g.content,
                "notes": g.notes,
                "status": g.status.value,
            }
            for g in goals
        ]

    def update_goal(self, goal_id: int, content: Optional[str] = None, notes: Optional[str] = None, status: Optional[str] = None):
        """Update a goal.

        Args:
            goal_id: Goal ID
            content: New content
            notes: New notes
            status: New status (pending/completed)

        Returns:
            Updated goal dict or None
        """
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if notes is not None:
            kwargs["notes"] = notes
        if status is not None:
            from gembrain.core.models import GoalStatus
            kwargs["status"] = GoalStatus(status)

        goal = self.goal_service.update_goal(goal_id, **kwargs)
        if goal:
            logger.info(f"🎯 Code updated goal: {goal.id}")
            return {
                "id": goal.id,
                "content": goal.content,
                "notes": goal.notes,
                "status": goal.status.value,
            }
        return None

    def delete_goal(self, goal_id: int):
        """Delete a goal.

        Args:
            goal_id: Goal ID

        Returns:
            Dict with success status
        """
        success = self.goal_service.delete_goal(goal_id)
        if success:
            logger.info(f"🗑️ Code deleted goal: {goal_id}")
        return {"success": success, "goal_id": goal_id}

    # =========================================================================
    # DATAVAULT OPERATIONS
    # =========================================================================

    def datavault_store(self, content: str, filetype: str = "text", notes: str = ""):
        """Store content in datavault.

        Args:
            content: Content to store (large blob - code, text, output, etc.)
            filetype: File type (text, py, js, json, md, etc.)
            notes: LLM annotations about the stored content

        Returns:
            Datavault item dict with id, datavault_id, filetype, notes, created_at
        """
        try:
            item = self.datavault_service.store_item(content, filetype, notes)
            logger.info(f"💾 Code stored datavault item: {item.id} (type: {filetype})")
            return {
                "id": item.id,
                "datavault_id": item.id,  # For backwards compatibility
                "filetype": item.filetype,
                "notes": item.notes,
                "content_length": len(content),
                "created_at": item.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to store datavault item: {e}")
            raise

    def datavault_get(self, item_id: int):
        """Get datavault item by ID.

        Args:
            item_id: Datavault item ID

        Returns:
            Datavault item dict with full content, or error dict if not found
        """
        item = self.datavault_service.get_item(item_id)
        if item:
            return {
                "id": item.id,
                "datavault_id": item.id,  # Add for backwards compatibility
                "content": item.content,
                "filetype": item.filetype,
                "notes": item.notes,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
        # Return error dict instead of None to prevent NoneType errors
        return {
            "error": f"Datavault item {item_id} not found",
            "id": None,
            "datavault_id": None,
        }

    def datavault_list(self, filetype: Optional[str] = None, limit: int = 50):
        """List datavault items, optionally filtered by filetype.

        Args:
            filetype: Filter by filetype (text, py, js, etc.)
            limit: Maximum results

        Returns:
            List of datavault item dicts (without full content)
        """
        items = self.datavault_service.get_all_items(filetype)[:limit]
        return [
            {
                "id": i.id,
                "filetype": i.filetype,
                "notes": i.notes,
                "content_length": len(i.content),
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ]

    def datavault_search(self, query: str, limit: int = 20):
        """Search datavault items by content or notes.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching datavault item dicts
        """
        items = self.datavault_service.search_items(query)[:limit]
        return [
            {
                "id": i.id,
                "filetype": i.filetype,
                "notes": i.notes,
                "content_preview": i.content[:200] if len(i.content) > 200 else i.content,
            }
            for i in items
        ]

    def datavault_update(self, item_id: int, content: Optional[str] = None, filetype: Optional[str] = None, notes: Optional[str] = None):
        """Update a datavault item.

        Args:
            item_id: Datavault item ID
            content: New content
            filetype: New filetype
            notes: New notes

        Returns:
            Updated item dict or error dict if not found
        """
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if filetype is not None:
            kwargs["filetype"] = filetype
        if notes is not None:
            kwargs["notes"] = notes

        item = self.datavault_service.update_item(item_id, **kwargs)
        if item:
            logger.info(f"💾 Code updated datavault item: {item.id}")
            return {
                "id": item.id,
                "datavault_id": item.id,  # Add for backwards compatibility
                "filetype": item.filetype,
                "notes": item.notes,
                "content_length": len(item.content),
                "updated_at": item.updated_at.isoformat(),
            }
        # Return error dict instead of None
        return {
            "error": f"Datavault item {item_id} not found",
            "id": None,
            "datavault_id": None,
        }

    def datavault_delete(self, item_id: int):
        """Delete a datavault item.

        Args:
            item_id: Datavault item ID

        Returns:
            Dict with success status
        """
        success = self.datavault_service.delete_item(item_id)
        if success:
            logger.info(f"🗑️ Code deleted datavault item: {item_id}")
        return {
            "success": success,
            "item_id": item_id,
            "datavault_id": item_id,  # Add for backwards compatibility
        }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def log(self, message: str, level: str = "info"):
        """Log a message.

        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if level == "warning":
            logger.warning(f"[CODE] {message}")
        elif level == "error":
            logger.error(f"[CODE] {message}")
        else:
            logger.info(f"[CODE] {message}")

    def commit(self):
        """Explicitly commit database changes.

        Usually not needed as changes are auto-committed, but available if needed.
        """
        try:
            self.db.commit()
            logger.info("✅ Code explicitly committed database changes")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit: {e}")
            raise
