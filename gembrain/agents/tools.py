"""Action tools for executing agent decisions."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from ..core.services import (
    NoteService,
    TaskService,
    ProjectService,
    MemoryService,
    VaultService,
)
from ..core.models import TaskStatus, VaultItemType
from .code_executor import CodeExecutor


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    action_type: str
    message: str
    data: Optional[Dict[str, Any]] = None


class ActionExecutor:
    """Executes actions from agent responses."""

    def __init__(self, db: Session, enable_code_execution: bool = True):
        """Initialize action executor.

        Args:
            db: Database session
            enable_code_execution: Whether to allow code execution
        """
        self.db = db
        self.note_service = NoteService(db)
        self.task_service = TaskService(db)
        self.project_service = ProjectService(db)
        self.memory_service = MemoryService(db)
        self.vault_service = VaultService(db)
        self.enable_code_execution = enable_code_execution
        self.code_executor = CodeExecutor() if enable_code_execution else None

    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """Execute a single action.

        Args:
            action: Action dictionary with type and parameters

        Returns:
            ActionResult
        """
        action_type = action.get("type")
        if not action_type:
            return ActionResult(False, "unknown", "Missing action type")

        # Log action start
        logger.info("─" * 60)
        logger.info(f"EXECUTING ACTION: {action_type}")
        logger.info(f"Parameters: {action}")

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
        }

        handler = handlers.get(action_type)
        if not handler:
            logger.error(f"Unknown action type: {action_type}")
            return ActionResult(False, action_type, f"Unknown action type: {action_type}")

        try:
            result = handler(action)

            # Log result
            if result.success:
                logger.info(f"✓ ACTION SUCCESS: {result.message}")
            else:
                logger.error(f"✗ ACTION FAILED: {result.message}")

            return result
        except Exception as e:
            logger.error(f"✗ ERROR executing action {action_type}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ActionResult(False, action_type, f"Error: {str(e)}")

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
