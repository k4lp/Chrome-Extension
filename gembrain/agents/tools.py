"""Action tools for executing agent decisions."""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
import time
import traceback

from ..core.services import (
    NoteService,
    TaskService,
    ProjectService,
    MemoryService,
    VaultService,
)
from ..core.models import TaskStatus, VaultItemType
from .code_executor import CodeExecutor
from .code_api import GemBrainAPI


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    action_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    execution_time: float = 0.0
    error_details: Optional[str] = None


class ActionExecutor:
    """Executes actions from agent responses with robust error handling."""

    # Actions that support retry on failure
    RETRYABLE_ACTIONS = {
        "create_note",
        "update_note",
        "create_project",
        "update_memory",
        "add_vault_item",
        "add_task",
        "update_task",
    }

    # Actions that should not be retried (destructive or query actions)
    NON_RETRYABLE_ACTIONS = {
        "delete_note",
        "delete_task",
        "archive_note",
        "execute_code",
        "list_notes",
        "search_notes",
    }

    def __init__(
        self,
        db: Session,
        enable_code_execution: bool = True,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        """Initialize action executor.

        Args:
            db: Database session
            enable_code_execution: Whether to allow code execution
            max_retries: Maximum number of retries for failed actions
            retry_delay: Delay between retries in seconds
        """
        self.db = db
        self.note_service = NoteService(db)
        self.task_service = TaskService(db)
        self.project_service = ProjectService(db)
        self.memory_service = MemoryService(db)
        self.vault_service = VaultService(db)
        self.enable_code_execution = enable_code_execution

        # Create GemBrain API for code execution
        if enable_code_execution:
            services = {
                "note_service": self.note_service,
                "task_service": self.task_service,
                "project_service": self.project_service,
                "memory_service": self.memory_service,
                "vault_service": self.vault_service,
            }
            gembrain_api = GemBrainAPI(db, services)
            self.code_executor = CodeExecutor(gembrain_api)
            logger.info("✓ Code executor initialized with GemBrain API access")
        else:
            self.code_executor = None

        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _validate_action(self, action: Dict[str, Any]) -> Optional[str]:
        """Validate action parameters.

        Args:
            action: Action dictionary

        Returns:
            Error message if invalid, None if valid
        """
        action_type = action.get("type")
        if not action_type:
            return "Missing action type"

        # Type-specific validation
        required_fields = {
            "create_note": ["title"],
            "update_note": ["note_id"],
            "archive_note": ["note_id"],
            "delete_note": ["note_id"],
            "add_task": ["title"],
            "update_task": ["task_id"],
            "complete_task": ["task_id"],
            "delete_task": ["task_id"],
            "create_project": ["name"],
            "update_memory": ["key", "content"],
            "add_vault_item": ["title", "path_or_url"],
            "execute_code": ["code"],
            "list_notes": [],
            "search_notes": ["query"],
            "list_tasks": [],
            "search_tasks": ["query"],
            "list_projects": [],
            "vault_store": ["title", "content"],
            "vault_get": ["item_id"],
            "vault_search": ["query"],
        }

        if action_type in required_fields:
            for field in required_fields[action_type]:
                if not action.get(field):
                    return f"Missing required field: {field}"

        return None

    def _execute_with_retry(
        self, action_type: str, handler: Callable, action: Dict[str, Any]
    ) -> ActionResult:
        """Execute action with retry logic.

        Args:
            action_type: Type of action
            handler: Handler function
            action: Action parameters

        Returns:
            ActionResult
        """
        # Determine if action is retryable
        is_retryable = action_type in self.RETRYABLE_ACTIONS
        max_attempts = self.max_retries + 1 if is_retryable else 1

        last_error = None
        start_time = time.time()

        for attempt in range(max_attempts):
            try:
                # Execute the handler
                result = handler(action)

                # If successful, add timing and return
                if result.success:
                    result.execution_time = time.time() - start_time
                    result.retry_count = attempt
                    return result

                # If failed but not retryable, return immediately
                if not is_retryable:
                    result.execution_time = time.time() - start_time
                    return result

                # Failed but retryable - store error and retry
                last_error = result.message
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"⚠️ Action failed (attempt {attempt + 1}/{max_attempts}): {result.message}"
                    )
                    logger.warning(f"Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue

                # All retries exhausted
                result.execution_time = time.time() - start_time
                result.retry_count = attempt
                return result

            except SQLAlchemyError as e:
                # Database error - rollback and retry if applicable
                self.db.rollback()
                last_error = f"Database error: {str(e)}"
                logger.error(f"❌ Database error in action {action_type}: {e}")

                if is_retryable and attempt < max_attempts - 1:
                    logger.warning(f"Retrying after database error (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(self.retry_delay)
                    continue

                return ActionResult(
                    False,
                    action_type,
                    f"Database error after {attempt + 1} attempts: {str(e)}",
                    error_details=traceback.format_exc(),
                    retry_count=attempt,
                    execution_time=time.time() - start_time,
                )

            except Exception as e:
                # General error
                last_error = str(e)
                logger.error(f"❌ Error in action {action_type}: {e}")
                logger.error(traceback.format_exc())

                if is_retryable and attempt < max_attempts - 1:
                    logger.warning(f"Retrying after error (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(self.retry_delay)
                    continue

                return ActionResult(
                    False,
                    action_type,
                    f"Error after {attempt + 1} attempts: {str(e)}",
                    error_details=traceback.format_exc(),
                    retry_count=attempt,
                    execution_time=time.time() - start_time,
                )

        # Should never reach here, but just in case
        return ActionResult(
            False,
            action_type,
            f"Failed after {max_attempts} attempts: {last_error}",
            retry_count=max_attempts - 1,
            execution_time=time.time() - start_time,
        )

    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a single action with validation and retry logic.

        Args:
            action: Action dictionary with type and parameters

        Returns:
            ActionResult
        """
        action_type = action.get("type", "unknown")

        # Log action start
        logger.info("─" * 60)
        logger.info(f"EXECUTING ACTION: {action_type}")
        logger.info(f"Parameters: {action}")

        # Validate action
        validation_error = self._validate_action(action)
        if validation_error:
            logger.error(f"✗ VALIDATION ERROR: {validation_error}")
            return ActionResult(False, action_type, validation_error)

        # Route to appropriate handler
        handlers = {
            "create_note": self._create_note,
            "update_note": self._update_note,
            "archive_note": self._archive_note,
            "delete_note": self._delete_note,
            "add_task": self._add_task,
            "update_task": self._update_task,
            "complete_task": self._complete_task,
            "delete_task": self._delete_task,
            "create_project": self._create_project,
            "update_memory": self._update_memory,
            "add_vault_item": self._add_vault_item,
            "execute_code": self._execute_code,
            "list_notes": self._list_notes,
            "search_notes": self._search_notes,
            "list_tasks": self._list_tasks,
            "search_tasks": self._search_tasks,
            "list_projects": self._list_projects,
            "vault_store": self._vault_store,
            "vault_get": self._vault_get,
            "vault_search": self._vault_search,
            "vault_list": self._vault_list,
            "vault_update": self._vault_update,
            "vault_delete": self._vault_delete,
        }

        handler = handlers.get(action_type)
        if not handler:
            logger.error(f"Unknown action type: {action_type}")
            return ActionResult(False, action_type, f"Unknown action type: {action_type}")

        # Execute with retry logic
        result = self._execute_with_retry(action_type, handler, action)

        # Log final result
        if result.success:
            logger.info(
                f"✓ ACTION SUCCESS ({result.execution_time:.3f}s, "
                f"{result.retry_count} retries): {result.message}"
            )
        else:
            logger.error(
                f"✗ ACTION FAILED ({result.execution_time:.3f}s, "
                f"{result.retry_count} retries): {result.message}"
            )

        return result

    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """Execute multiple actions.

        Args:
            actions: List of action dictionaries

        Returns:
            List of ActionResults
        """
        logger.warning("=" * 60)
        logger.warning(f"EXECUTING ACTION BATCH: {len(actions)} actions")
        logger.warning("=" * 60)

        results = []
        for i, action in enumerate(actions, 1):
            logger.info(f"Action {i}/{len(actions)}")
            result = self.execute_action(action)
            results.append(result)

        # Summary
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        logger.warning("=" * 60)
        logger.warning(f"BATCH COMPLETE: {success_count} succeeded, {fail_count} failed")
        logger.warning("=" * 60)

        return results

    # Note actions
    def _create_note(self, action: Dict[str, Any]) -> ActionResult:
        """Create a note."""
        title = action.get("title")
        if not title:
            return ActionResult(False, "create_note", "Missing title")

        content = action.get("content", "")
        tags = action.get("tags", [])
        pinned = action.get("pinned", False)

        note = self.note_service.create_note(title, content, tags, pinned)
        return ActionResult(
            True,
            "create_note",
            f"Created note: {note.title}",
            {"note_id": note.id, "title": note.title},
        )

    def _update_note(self, action: Dict[str, Any]) -> ActionResult:
        """Update a note."""
        note_id = action.get("note_id")
        if not note_id:
            return ActionResult(False, "update_note", "Missing note_id")

        update_fields = {}
        for field in ["title", "content", "tags"]:
            if field in action:
                update_fields[field] = action[field]

        if not update_fields:
            return ActionResult(False, "update_note", "No fields to update")

        note = self.note_service.update_note(note_id, **update_fields)
        if not note:
            return ActionResult(False, "update_note", f"Note {note_id} not found")

        return ActionResult(True, "update_note", f"Updated note: {note.title}")

    def _archive_note(self, action: Dict[str, Any]) -> ActionResult:
        """Archive a note."""
        note_id = action.get("note_id")
        if not note_id:
            return ActionResult(False, "archive_note", "Missing note_id")

        note = self.note_service.archive_note(note_id)
        if not note:
            return ActionResult(False, "archive_note", f"Note {note_id} not found")

        return ActionResult(True, "archive_note", f"Archived note: {note.title}")

    def _delete_note(self, action: Dict[str, Any]) -> ActionResult:
        """Delete a note."""
        note_id = action.get("note_id")
        if not note_id:
            return ActionResult(False, "delete_note", "Missing note_id")

        success = self.note_service.delete_note(note_id)
        if not success:
            return ActionResult(False, "delete_note", f"Note {note_id} not found")

        return ActionResult(True, "delete_note", f"Deleted note {note_id}")

    # Task actions
    def _add_task(self, action: Dict[str, Any]) -> ActionResult:
        """Add a task."""
        title = action.get("title")
        if not title:
            return ActionResult(False, "add_task", "Missing title")

        due_date = None
        if "due_date" in action:
            due_date_str = action["due_date"]
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                return ActionResult(False, "add_task", f"Invalid due_date format: {due_date_str}")

        project_name = action.get("project_name")
        note_title = action.get("note_title")

        # Resolve note_id from note_title if provided
        note_id = None
        if note_title:
            notes = self.note_service.search_notes(note_title)
            if notes:
                note_id = notes[0].id

        task = self.task_service.create_task(
            title=title,
            due_date=due_date,
            note_id=note_id,
            project_name=project_name,
        )

        return ActionResult(
            True,
            "add_task",
            f"Created task: {task.title}",
            {"task_id": task.id, "title": task.title},
        )

    def _update_task(self, action: Dict[str, Any]) -> ActionResult:
        """Update a task."""
        task_id = action.get("task_id")
        if not task_id:
            return ActionResult(False, "update_task", "Missing task_id")

        update_fields = {}
        for field in ["title", "status", "due_date"]:
            if field in action:
                value = action[field]
                if field == "status":
                    try:
                        value = TaskStatus(value)
                    except ValueError:
                        return ActionResult(
                            False, "update_task", f"Invalid status: {value}"
                        )
                elif field == "due_date" and value:
                    try:
                        value = datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        return ActionResult(
                            False, "update_task", f"Invalid due_date format: {value}"
                        )
                update_fields[field] = value

        if not update_fields:
            return ActionResult(False, "update_task", "No fields to update")

        task = self.task_service.update_task(task_id, **update_fields)
        if not task:
            return ActionResult(False, "update_task", f"Task {task_id} not found")

        return ActionResult(True, "update_task", f"Updated task: {task.title}")

    def _complete_task(self, action: Dict[str, Any]) -> ActionResult:
        """Complete a task."""
        task_id = action.get("task_id")
        if not task_id:
            return ActionResult(False, "complete_task", "Missing task_id")

        task = self.task_service.complete_task(task_id)
        if not task:
            return ActionResult(False, "complete_task", f"Task {task_id} not found")

        return ActionResult(True, "complete_task", f"Completed task: {task.title}")

    def _delete_task(self, action: Dict[str, Any]) -> ActionResult:
        """Delete a task."""
        task_id = action.get("task_id")
        if not task_id:
            return ActionResult(False, "delete_task", "Missing task_id")

        success = self.task_service.delete_task(task_id)
        if not success:
            return ActionResult(False, "delete_task", f"Task {task_id} not found")

        return ActionResult(True, "delete_task", f"Deleted task {task_id}")

    # Project actions
    def _create_project(self, action: Dict[str, Any]) -> ActionResult:
        """Create a project."""
        name = action.get("name")
        if not name:
            return ActionResult(False, "create_project", "Missing name")

        description = action.get("description", "")
        tags = action.get("tags", [])

        project = self.project_service.create_project(name, description, tags=tags)
        return ActionResult(
            True,
            "create_project",
            f"Created project: {project.name}",
            {"project_id": project.id, "name": project.name},
        )

    # Memory actions
    def _update_memory(self, action: Dict[str, Any]) -> ActionResult:
        """Update memory."""
        key = action.get("key")
        content = action.get("content")

        if not key or not content:
            return ActionResult(False, "update_memory", "Missing key or content")

        importance = action.get("importance", 3)
        memory = self.memory_service.update_memory(key, content, importance)

        return ActionResult(
            True,
            "update_memory",
            f"Updated memory: {memory.key}",
            {"key": memory.key},
        )

    # Vault actions
    def _add_vault_item(self, action: Dict[str, Any]) -> ActionResult:
        """Add vault item."""
        title = action.get("title")
        item_type = action.get("type", "other")
        path_or_url = action.get("path_or_url")

        if not title or not path_or_url:
            return ActionResult(False, "add_vault_item", "Missing title or path_or_url")

        try:
            vault_type = VaultItemType(item_type)
        except ValueError:
            vault_type = VaultItemType.OTHER

        item = self.vault_service.add_item(title, vault_type, path_or_url)
        return ActionResult(
            True,
            "add_vault_item",
            f"Added vault item: {item.title}",
            {"item_id": item.id, "title": item.title},
        )

    # Code execution action
    def _execute_code(self, action: Dict[str, Any]) -> ActionResult:
        """Execute Python code.

        Args:
            action: Action with 'code' field

        Returns:
            ActionResult with execution output
        """
        if not self.enable_code_execution:
            return ActionResult(
                False,
                "execute_code",
                "Code execution is disabled in settings",
            )

        code = action.get("code")
        if not code:
            return ActionResult(False, "execute_code", "Missing code field")

        # Execute the code
        result = self.code_executor.execute(code)

        if result["success"]:
            output_parts = []
            if result["stdout"]:
                output_parts.append(f"Output: {result['stdout']}")
            if result["result"] is not None:
                output_parts.append(f"Result: {result['result']}")

            exec_time = result.get("execution_time", 0)
            message = (
                f"Code executed in {exec_time:.3f}s. "
                + ("\n".join(output_parts) if output_parts else "No output")
            )

            return ActionResult(
                True,
                "execute_code",
                message,
                {
                    "execution_id": result.get("execution_id"),
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "result": str(result["result"]) if result["result"] is not None else None,
                    "execution_time": exec_time,
                },
            )
        else:
            return ActionResult(
                False,
                "execute_code",
                f"Execution failed: {result['error']}",
                {
                    "execution_id": result.get("execution_id"),
                    "error": result["error"],
                    "stderr": result["stderr"],
                    "execution_time": result.get("execution_time", 0),
                },
            )

    # Query/List actions for retrieving IDs and data
    def _list_notes(self, action: Dict[str, Any]) -> ActionResult:
        """List all notes with their IDs.

        Returns:
            ActionResult with list of notes
        """
        limit = action.get("limit", 50)
        include_archived = action.get("include_archived", False)

        notes = self.note_service.get_all_notes()

        if not include_archived:
            notes = [n for n in notes if not n.archived]

        notes = notes[:limit]

        notes_data = [
            {
                "id": note.id,
                "title": note.title,
                "tags": note.tags,
                "pinned": note.pinned,
                "archived": note.archived,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            }
            for note in notes
        ]

        return ActionResult(
            True,
            "list_notes",
            f"Retrieved {len(notes_data)} notes",
            {"notes": notes_data, "count": len(notes_data)},
        )

    def _search_notes(self, action: Dict[str, Any]) -> ActionResult:
        """Search notes by query.

        Args:
            action: Action with 'query' field

        Returns:
            ActionResult with matching notes
        """
        query = action.get("query", "")
        limit = action.get("limit", 20)

        notes = self.note_service.search_notes(query)[:limit]

        notes_data = [
            {
                "id": note.id,
                "title": note.title,
                "content": note.content[:200] + "..." if len(note.content) > 200 else note.content,
                "tags": note.tags,
                "pinned": note.pinned,
                "archived": note.archived,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            }
            for note in notes
        ]

        return ActionResult(
            True,
            "search_notes",
            f"Found {len(notes_data)} notes matching '{query}'",
            {"notes": notes_data, "count": len(notes_data), "query": query},
        )

    def _list_tasks(self, action: Dict[str, Any]) -> ActionResult:
        """List all tasks with their IDs.

        Returns:
            ActionResult with list of tasks
        """
        limit = action.get("limit", 50)
        status_filter = action.get("status")  # Optional: todo, doing, done, stale

        tasks = self.task_service.get_all_tasks()

        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
                tasks = [t for t in tasks if t.status == status_enum]
            except ValueError:
                pass

        tasks = tasks[:limit]

        tasks_data = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "project_name": task.project.name if task.project else None,
                "note_id": task.note_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at if hasattr(task, "updated_at") else task.created_at.isoformat(),
            }
            for task in tasks
        ]

        return ActionResult(
            True,
            "list_tasks",
            f"Retrieved {len(tasks_data)} tasks",
            {"tasks": tasks_data, "count": len(tasks_data)},
        )

    def _search_tasks(self, action: Dict[str, Any]) -> ActionResult:
        """Search tasks by query.

        Args:
            action: Action with 'query' field

        Returns:
            ActionResult with matching tasks
        """
        query = action.get("query", "")
        limit = action.get("limit", 20)

        tasks = self.task_service.search_tasks(query)[:limit]

        tasks_data = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "project_name": task.project.name if task.project else None,
                "note_id": task.note_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at if hasattr(task, "updated_at") else task.created_at.isoformat(),
            }
            for task in tasks
        ]

        return ActionResult(
            True,
            "search_tasks",
            f"Found {len(tasks_data)} tasks matching '{query}'",
            {"tasks": tasks_data, "count": len(tasks_data), "query": query},
        )

    def _list_projects(self, action: Dict[str, Any]) -> ActionResult:
        """List all projects with their IDs.

        Returns:
            ActionResult with list of projects
        """
        limit = action.get("limit", 50)

        projects = self.project_service.get_all_projects()[:limit]

        projects_data = [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "tags": project.tags,
                "task_count": len(project.tasks) if hasattr(project, "tasks") else 0,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            }
            for project in projects
        ]

        return ActionResult(
            True,
            "list_projects",
            f"Retrieved {len(projects_data)} projects",
            {"projects": projects_data, "count": len(projects_data)},
        )

    # Vault actions for intermediate storage
    def _vault_store(self, action: Dict[str, Any]) -> ActionResult:
        """Store data in vault (intermediate results).

        Args:
            action: Action with 'title' and 'content' fields

        Returns:
            ActionResult with vault item info
        """
        title = action.get("title", "")
        content = action.get("content", "")
        item_type = action.get("type", "snippet")

        try:
            vault_type = VaultItemType(item_type)
        except ValueError:
            vault_type = VaultItemType.SNIPPET

        item = self.vault_service.add_item(title, vault_type, content)

        return ActionResult(
            True,
            "vault_store",
            f"Stored vault item: {item.title}",
            {
                "item_id": item.id,
                "title": item.title,
                "type": item.type.value,
            },
        )

    def _vault_get(self, action: Dict[str, Any]) -> ActionResult:
        """Retrieve vault item by ID.

        Args:
            action: Action with 'item_id' field

        Returns:
            ActionResult with vault item data
        """
        item_id = action.get("item_id")

        item = self.vault_service.get_item(item_id)

        if not item:
            return ActionResult(
                False,
                "vault_get",
                f"Vault item {item_id} not found",
            )

        return ActionResult(
            True,
            "vault_get",
            f"Retrieved vault item: {item.title}",
            {
                "item_id": item.id,
                "title": item.title,
                "type": item.type.value,
                "path_or_url": item.path_or_url,
                "item_metadata": item.item_metadata,
            },
        )

    def _vault_search(self, action: Dict[str, Any]) -> ActionResult:
        """Search vault items.

        Args:
            action: Action with 'query' field

        Returns:
            ActionResult with matching vault items
        """
        query = action.get("query", "")
        limit = action.get("limit", 20)

        items = self.vault_service.search_items(query)[:limit]

        items_data = [
            {
                "item_id": item.id,
                "title": item.title,
                "type": item.type.value,
                "path_or_url": item.path_or_url[:100] + "..." if len(item.path_or_url) > 100 else item.path_or_url,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]

        return ActionResult(
            True,
            "vault_search",
            f"Found {len(items_data)} vault items matching '{query}'",
            {"items": items_data, "count": len(items_data), "query": query},
        )

    def _vault_list(self, action: Dict[str, Any]) -> ActionResult:
        """List all vault items.

        Args:
            action: Action with optional 'item_type' and 'limit' fields

        Returns:
            ActionResult with list of vault items
        """
        item_type = action.get("item_type")
        limit = action.get("limit", 50)

        # Convert string type to enum if provided
        vault_type = None
        if item_type:
            try:
                vault_type = VaultItemType(item_type)
            except ValueError:
                return ActionResult(
                    False,
                    "vault_list",
                    f"Invalid vault item type: {item_type}",
                )

        items = self.vault_service.get_all_items(vault_type)[:limit]

        items_data = [
            {
                "item_id": item.id,
                "title": item.title,
                "type": item.type.value,
                "path_or_url": item.path_or_url[:100] + "..." if len(item.path_or_url) > 100 else item.path_or_url,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]

        return ActionResult(
            True,
            "vault_list",
            f"Listed {len(items_data)} vault items" + (f" of type {item_type}" if item_type else ""),
            {"items": items_data, "count": len(items_data)},
        )

    def _vault_update(self, action: Dict[str, Any]) -> ActionResult:
        """Update vault item.

        Args:
            action: Action with 'item_id' and update fields

        Returns:
            ActionResult with updated item info
        """
        item_id = action.get("item_id")
        if not item_id:
            return ActionResult(
                False,
                "vault_update",
                "Missing required field: item_id",
            )

        # Extract update fields
        update_fields = {}
        if "title" in action:
            update_fields["title"] = action["title"]
        if "path_or_url" in action:
            update_fields["path_or_url"] = action["path_or_url"]
        if "item_metadata" in action:
            update_fields["item_metadata"] = action["item_metadata"]

        if not update_fields:
            return ActionResult(
                False,
                "vault_update",
                "No fields to update",
            )

        item = self.vault_service.update_item(item_id, **update_fields)

        if not item:
            return ActionResult(
                False,
                "vault_update",
                f"Vault item {item_id} not found",
            )

        return ActionResult(
            True,
            "vault_update",
            f"Updated vault item: {item.title}",
            {
                "item_id": item.id,
                "title": item.title,
                "type": item.type.value,
            },
        )

    def _vault_delete(self, action: Dict[str, Any]) -> ActionResult:
        """Delete vault item.

        Args:
            action: Action with 'item_id' field

        Returns:
            ActionResult indicating success
        """
        item_id = action.get("item_id")
        if not item_id:
            return ActionResult(
                False,
                "vault_delete",
                "Missing required field: item_id",
            )

        success = self.vault_service.delete_item(item_id)

        if not success:
            return ActionResult(
                False,
                "vault_delete",
                f"Vault item {item_id} not found",
            )

        return ActionResult(
            True,
            "vault_delete",
            f"Deleted vault item {item_id}",
            {"item_id": item_id},
        )
