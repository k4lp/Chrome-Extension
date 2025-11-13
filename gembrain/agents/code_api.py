"""API bindings for Python code execution - allows executed code to use GemBrain features."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class GemBrainAPI:
    """API for code execution to interact with GemBrain data structures.

    This allows executed code to directly create/update/delete notes, tasks, etc.
    instead of returning large data to the LLM which can hit token limits.
    """

    def __init__(self, db_session, services: Dict[str, Any]):
        """Initialize API with database session and services.

        Args:
            db_session: SQLAlchemy database session
            services: Dictionary of service instances
        """
        self.db = db_session
        self.note_service = services.get("note_service")
        self.task_service = services.get("task_service")
        self.project_service = services.get("project_service")
        self.memory_service = services.get("memory_service")
        self.vault_service = services.get("vault_service")

    # Note Operations
    def create_note(self, title: str, content: str = "", tags: List[str] = None, pinned: bool = False):
        """Create a new note.

        Args:
            title: Note title
            content: Note content (markdown)
            tags: List of tags
            pinned: Whether to pin the note

        Returns:
            Note object with id, title, etc.
        """
        try:
            note = self.note_service.create_note(title, content, tags or [], pinned)
            logger.info(f"📝 Code created note: {note.title} (id={note.id})")
            return {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "created_at": note.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create note: {e}")
            raise

    def search_notes(self, query: str, limit: int = 20):
        """Search for notes.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching notes
        """
        notes = self.note_service.search_notes(query)[:limit]
        return [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "tags": n.tags,
                "pinned": n.pinned,
                "archived": n.archived,
            }
            for n in notes
        ]

    def update_note(self, note_id: int, **kwargs):
        """Update an existing note.

        Args:
            note_id: Note ID
            **kwargs: Fields to update (title, content, tags)

        Returns:
            Updated note object
        """
        note = self.note_service.update_note(note_id, **kwargs)
        if note:
            logger.info(f"📝 Code updated note: {note.title} (id={note.id})")
            return {"id": note.id, "title": note.title, "content": note.content}
        return None

    def delete_note(self, note_id: int):
        """Delete a note.

        Args:
            note_id: Note ID to delete

        Returns:
            True if successful
        """
        success = self.note_service.delete_note(note_id)
        if success:
            logger.info(f"🗑️ Code deleted note id={note_id}")
        return success

    # Task Operations
    def create_task(self, title: str, due_date: Optional[str] = None, project_name: Optional[str] = None):
        """Create a new task.

        Args:
            title: Task title
            due_date: Due date (YYYY-MM-DD format)
            project_name: Project name

        Returns:
            Task object
        """
        due_date_obj = None
        if due_date:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")

        task = self.task_service.create_task(
            title=title,
            due_date=due_date_obj,
            project_name=project_name,
        )
        logger.info(f"✓ Code created task: {task.title} (id={task.id})")
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }

    def search_tasks(self, query: str, limit: int = 20):
        """Search for tasks.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching tasks
        """
        tasks = self.task_service.search_tasks(query)[:limit]
        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "project_name": t.project.name if t.project else None,
            }
            for t in tasks
        ]

    def complete_task(self, task_id: int):
        """Mark a task as complete.

        Args:
            task_id: Task ID

        Returns:
            Updated task object
        """
        task = self.task_service.complete_task(task_id)
        if task:
            logger.info(f"✓ Code completed task: {task.title} (id={task.id})")
            return {"id": task.id, "title": task.title, "status": task.status.value}
        return None

    def delete_task(self, task_id: int):
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if successful
        """
        success = self.task_service.delete_task(task_id)
        if success:
            logger.info(f"🗑️ Code deleted task id={task_id}")
        return success

    # Project Operations
    def create_project(self, name: str, description: str = "", tags: List[str] = None):
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            tags: List of tags

        Returns:
            Project object
        """
        project = self.project_service.create_project(name, description, tags or [])
        logger.info(f"📁 Code created project: {project.name} (id={project.id})")
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "tags": project.tags,
        }

    def list_projects(self, limit: int = 50):
        """List all projects.

        Args:
            limit: Maximum results

        Returns:
            List of projects
        """
        projects = self.project_service.get_all_projects()[:limit]
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "tags": p.tags,
            }
            for p in projects
        ]

    # Memory Operations
    def store_memory(self, key: str, content: str, importance: int = 3):
        """Store or update a memory.

        Args:
            key: Memory key
            content: Memory content
            importance: Importance level (1-5)

        Returns:
            Memory object
        """
        memory = self.memory_service.update_memory(key, content, importance)
        logger.info(f"🧠 Code stored memory: {key}")
        return {
            "key": memory.key,
            "content": memory.content,
            "importance": memory.importance,
        }

    def get_memory(self, key: str):
        """Retrieve a memory by key.

        Args:
            key: Memory key

        Returns:
            Memory content or None
        """
        memory = self.memory_service.get_memory(key)
        if memory:
            return {"key": memory.key, "content": memory.content, "importance": memory.importance}
        return None

    def list_memories(self, importance_threshold: int = 1):
        """List all memories above importance threshold.

        Args:
            importance_threshold: Minimum importance

        Returns:
            List of memories
        """
        memories = self.memory_service.get_all_memories(min_importance=importance_threshold)
        return [
            {
                "key": m.key,
                "content": m.content,
                "importance": m.importance,
            }
            for m in memories
        ]

    # Vault Operations (for intermediate data storage)
    def vault_store(self, title: str, content: str, item_type: str = "snippet"):
        """Store data in vault (useful for intermediate results).

        Args:
            title: Item title
            content: Item content/data
            item_type: Type (snippet, file, url, other)

        Returns:
            Vault item object
        """
        from ..core.models import VaultItemType

        try:
            vault_type = VaultItemType(item_type)
        except ValueError:
            vault_type = VaultItemType.SNIPPET

        item = self.vault_service.add_item(title, vault_type, content)
        logger.info(f"💾 Code stored vault item: {title} (id={item.id})")
        return {
            "id": item.id,
            "title": item.title,
            "type": item.type.value,
            "path_or_url": item.path_or_url,
        }

    def vault_get(self, item_id: int):
        """Retrieve a vault item by ID.

        Args:
            item_id: Vault item ID

        Returns:
            Vault item object
        """
        item = self.vault_service.get_item(item_id)
        if item:
            return {
                "id": item.id,
                "title": item.title,
                "type": item.type.value,
                "path_or_url": item.path_or_url,
                "item_metadata": item.item_metadata,
            }
        return None

    def vault_search(self, query: str, limit: int = 20):
        """Search vault items.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching vault items
        """
        items = self.vault_service.search_items(query)[:limit]
        return [
            {
                "id": i.id,
                "title": i.title,
                "type": i.type.value,
                "path_or_url": i.path_or_url,
            }
            for i in items
        ]

    def vault_list(self, item_type: str = None, limit: int = 50):
        """List all vault items.

        Args:
            item_type: Optional filter by type (snippet, file, url, other)
            limit: Maximum results

        Returns:
            List of vault items
        """
        from ..core.models import VaultItemType

        vault_type = None
        if item_type:
            try:
                vault_type = VaultItemType(item_type)
            except ValueError:
                logger.warning(f"Invalid vault item type: {item_type}")

        items = self.vault_service.get_all_items(vault_type)[:limit]
        return [
            {
                "id": i.id,
                "title": i.title,
                "type": i.type.value,
                "path_or_url": i.path_or_url,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ]

    def vault_update(self, item_id: int, **kwargs):
        """Update a vault item.

        Args:
            item_id: Vault item ID
            **kwargs: Fields to update (title, path_or_url, item_metadata)

        Returns:
            Updated vault item or None
        """
        item = self.vault_service.update_item(item_id, **kwargs)
        if item:
            logger.info(f"📝 Code updated vault item: {item.title} (id={item.id})")
            return {
                "id": item.id,
                "title": item.title,
                "type": item.type.value,
                "path_or_url": item.path_or_url,
            }
        return None

    def vault_delete(self, item_id: int):
        """Delete a vault item.

        Args:
            item_id: Vault item ID

        Returns:
            True if successful
        """
        success = self.vault_service.delete_item(item_id)
        if success:
            logger.info(f"🗑️ Code deleted vault item id={item_id}")
        return success

    # Utility methods
    def log(self, message: str, level: str = "info"):
        """Log a message from code.

        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        log_func = getattr(logger, level, logger.info)
        log_func(f"[CODE] {message}")

    def commit(self):
        """Commit database changes (usually automatic but can be explicit)."""
        self.db.commit()
        logger.info("💾 Code committed database changes")


# This will be injected into the code execution namespace
def get_api_docs():
    """Get API documentation for reference in code."""
    return """
GemBrain API Documentation
==========================

Available as 'gb' variable in your code.

Notes:
  gb.create_note(title, content="", tags=[], pinned=False)
  gb.search_notes(query, limit=20)
  gb.update_note(note_id, title=..., content=..., tags=...)
  gb.delete_note(note_id)

Tasks:
  gb.create_task(title, due_date=None, project_name=None)
  gb.search_tasks(query, limit=20)
  gb.complete_task(task_id)
  gb.delete_task(task_id)

Projects:
  gb.create_project(name, description="", tags=[])
  gb.list_projects(limit=50)

Memory:
  gb.store_memory(key, content, importance=3)
  gb.get_memory(key)
  gb.list_memories(importance_threshold=1)

Vault (for intermediate data):
  gb.vault_store(title, content, item_type="snippet")
  gb.vault_get(item_id)
  gb.vault_search(query, limit=20)
  gb.vault_delete(item_id)

Utilities:
  gb.log(message, level="info")
  gb.commit()

Example:
  # Store intermediate results
  gb.vault_store("analysis_results", json.dumps(results))

  # Create tasks from analysis
  for item in to_do_list:
      gb.create_task(item["title"], item["due_date"])

  # Store summary as note
  gb.create_note("Analysis Summary", summary_text, tags=["analysis"])
"""
