"""Action tools for executing agent decisions."""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
import time
import traceback

from gembrain.core.services import (
    TaskService,
    MemoryService,
    GoalService,
    DatavaultService,
)
from gembrain.core.models import TaskStatus, GoalStatus
from gembrain.agents.code_executor import CodeExecutor
from gembrain.agents.code_api import GemBrainAPI


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
        "create_task",
        "update_task",
        "create_memory",
        "update_memory",
        "create_goal",
        "update_goal",
        "datavault_store",
        "datavault_update",
    }

    # Actions that should not be retried (destructive or query actions)
    NON_RETRYABLE_ACTIONS = {
        "delete_task",
        "delete_memory",
        "delete_goal",
        "datavault_delete",
        "execute_code",
        "list_tasks",
        "search_tasks",
        "list_memories",
        "search_memories",
        "list_goals",
        "search_goals",
        "datavault_list",
        "datavault_search",
        "log",
    }

    def __init__(
        self,
        db: Session,
        enable_code_execution: bool = True,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        progress_callback: Optional[Callable] = None,
    ):
        """Initialize action executor.

        Args:
            db: Database session
            enable_code_execution: Whether to allow code execution
            max_retries: Maximum number of retries for failed actions
            retry_delay: Delay between retries in seconds
            progress_callback: Optional callback for progress updates (for UI)
        """
        self.db = db
        self.task_service = TaskService(db)
        self.memory_service = MemoryService(db)
        self.goal_service = GoalService(db)
        self.datavault_service = DatavaultService(db)
        self.enable_code_execution = enable_code_execution
        self.progress_callback = progress_callback

        # Create GemBrain API for code execution
        if enable_code_execution:
            services = {
                "task_service": self.task_service,
                "memory_service": self.memory_service,
                "goal_service": self.goal_service,
                "datavault_service": self.datavault_service,
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
            "create_task": ["content"],
            "update_task": ["task_id"],
            "delete_task": ["task_id"],
            "get_task": ["task_id"],
            "log": ["content"],
            "list_tasks": [],
            "search_tasks": ["query"],
            "create_memory": ["content"],
            "update_memory": ["memory_id"],
            "delete_memory": ["memory_id"],
            "get_memory": ["memory_id"],
            "list_memories": [],
            "search_memories": ["query"],
            "create_goal": ["content"],
            "update_goal": ["goal_id"],
            "delete_goal": ["goal_id"],
            "get_goal": ["goal_id"],
            "list_goals": [],
            "search_goals": ["query"],
            "datavault_store": ["content"],
            "datavault_get": ["item_id"],
            "datavault_update": ["item_id"],
            "datavault_delete": ["item_id"],
            "datavault_list": [],
            "datavault_search": ["query"],
            "execute_code": ["code"],
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
        start_time = time.time()
        last_error = None
        retry_count = 0

        # Determine if action is retryable
        is_retryable = action_type in self.RETRYABLE_ACTIONS
        max_attempts = self.max_retries + 1 if is_retryable else 1

        for attempt in range(max_attempts):
            try:
                result = handler(action)
                result.retry_count = retry_count
                result.execution_time = time.time() - start_time
                return result

            except Exception as e:
                last_error = e
                retry_count += 1
                error_msg = str(e)
                error_trace = traceback.format_exc()

                logger.error(f"✗ EXECUTION ERROR (attempt {attempt + 1}/{max_attempts}): {error_msg}")
                logger.debug(f"Traceback: {error_trace}")

                # Rollback database on error
                try:
                    self.db.rollback()
                    logger.info("🔄 Rolled back database session")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback: {rollback_error}")

                # If not retryable or last attempt, fail
                if not is_retryable or attempt == max_attempts - 1:
                    return ActionResult(
                        success=False,
                        action_type=action_type,
                        message=f"Failed after {retry_count} retries: {error_msg}",
                        retry_count=retry_count,
                        execution_time=time.time() - start_time,
                        error_details=error_trace,
                    )

                # Wait before retry
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                logger.info(f"↻ Retrying {action_type} (attempt {attempt + 2}/{max_attempts})")

        # Should not reach here, but handle it
        return ActionResult(
            success=False,
            action_type=action_type,
            message=f"Failed: {last_error}",
            retry_count=retry_count,
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
        logger.info("-" * 60)
        logger.info(f"EXECUTING ACTION: {action_type}")
        logger.info(f"Parameters: {action}")

        # Emit action_start event for UI
        if self.progress_callback:
            self.progress_callback({
                "type": "action_start",
                "action_type": action_type,
                "details": str(action),
                "action_data": action,
            })

        # Validate action
        validation_error = self._validate_action(action)
        if validation_error:
            logger.error(f"VALIDATION ERROR: {validation_error}")
            result = ActionResult(False, action_type, validation_error)

            # Emit failure event
            if self.progress_callback:
                self.progress_callback({
                    "type": "action_result",
                    "action_type": action_type,
                    "success": False,
                    "message": validation_error,
                })

            return result

        # Route to appropriate handler
        handlers = {
            # Task actions
            "create_task": self._create_task,
            "update_task": self._update_task,
            "delete_task": self._delete_task,
            "get_task": self._get_task,
            "list_tasks": self._list_tasks,
            "search_tasks": self._search_tasks,
            # Memory actions
            "create_memory": self._create_memory,
            "update_memory": self._update_memory,
            "delete_memory": self._delete_memory,
            "get_memory": self._get_memory,
            "list_memories": self._list_memories,
            "search_memories": self._search_memories,
            # Goal actions
            "create_goal": self._create_goal,
            "update_goal": self._update_goal,
            "delete_goal": self._delete_goal,
            "get_goal": self._get_goal,
            "list_goals": self._list_goals,
            "search_goals": self._search_goals,
            # Datavault actions
            "datavault_store": self._datavault_store,
            "datavault_get": self._datavault_get,
            "datavault_update": self._datavault_update,
            "datavault_delete": self._datavault_delete,
            "datavault_list": self._datavault_list,
            "datavault_search": self._datavault_search,
            # Code execution
            "execute_code": self._execute_code,
            # Utility
            "log": self._log_action,
        }

        handler = handlers.get(action_type)
        if not handler:
            logger.error(f"Unknown action type: {action_type}")
            result = ActionResult(False, action_type, f"Unknown action type: {action_type}")

            # Emit failure event
            if self.progress_callback:
                self.progress_callback({
                    "type": "action_result",
                    "action_type": action_type,
                    "success": False,
                    "message": f"Unknown action type: {action_type}",
                })

            return result

        # Execute with retry logic
        result = self._execute_with_retry(action_type, handler, action)

        # Emit action_result event for UI
        if self.progress_callback:
            self.progress_callback({
                "type": "action_result",
                "action_type": action_type,
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })

        return result

    def execute_actions(self, actions: List[Dict[str, Any]], progress_callback: Optional[Callable] = None) -> List[ActionResult]:
        """Execute multiple actions.

        Args:
            actions: List of action dictionaries
            progress_callback: Optional callback for progress updates (overrides instance callback)

        Returns:
            List of ActionResults
        """
        # Use provided callback or fall back to instance callback
        old_callback = self.progress_callback
        if progress_callback is not None:
            self.progress_callback = progress_callback

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

        # Restore original callback
        self.progress_callback = old_callback

        return results

    # =========================================================================
    # TASK ACTION HANDLERS
    # =========================================================================

    def _create_task(self, action: Dict[str, Any]) -> ActionResult:
        """Create a task."""
        content = action.get("content")
        notes = action.get("notes", "")
        status = action.get("status", "pending")

        try:
            status_enum = TaskStatus(status)
        except ValueError:
            return ActionResult(False, "create_task", f"Invalid status: {status}")

        task = self.task_service.create_task(content, notes, status_enum)
        return ActionResult(
            True,
            "create_task",
            f"Created task {task.id}",
            {
                "task_id": task.id,
                "content": task.content,
                "status": task.status.value,
            },
        )

    def _update_task(self, action: Dict[str, Any]) -> ActionResult:
        """Update a task."""
        task_id = action.get("task_id")
        kwargs = {}

        if "content" in action:
            kwargs["content"] = action["content"]
        if "notes" in action:
            kwargs["notes"] = action["notes"]
        if "status" in action:
            try:
                kwargs["status"] = TaskStatus(action["status"])
            except ValueError:
                return ActionResult(False, "update_task", f"Invalid status: {action['status']}")

        task = self.task_service.update_task(task_id, **kwargs)
        if not task:
            return ActionResult(False, "update_task", f"Task {task_id} not found")

        return ActionResult(
            True,
            "update_task",
            f"Updated task {task.id}",
            {
                "task_id": task.id,
                "content": task.content,
                "status": task.status.value,
            },
        )

    def _delete_task(self, action: Dict[str, Any]) -> ActionResult:
        """Delete a task."""
        task_id = action.get("task_id")
        success = self.task_service.delete_task(task_id)

        if success:
            return ActionResult(True, "delete_task", f"Deleted task {task_id}")
        return ActionResult(False, "delete_task", f"Task {task_id} not found")

    def _get_task(self, action: Dict[str, Any]) -> ActionResult:
        """Get a task by ID."""
        task_id = action.get("task_id")
        task = self.task_service.get_task(task_id)

        if not task:
            return ActionResult(False, "get_task", f"Task {task_id} not found")

        return ActionResult(
            True,
            "get_task",
            f"Retrieved task {task_id}",
            {
                "task_id": task.id,
                "content": task.content,
                "notes": task.notes,
                "status": task.status.value,
            },
        )

    def _list_tasks(self, action: Dict[str, Any]) -> ActionResult:
        """List all tasks."""
        status_filter = action.get("status")
        limit = action.get("limit", 50)

        try:
            status_enum = TaskStatus(status_filter) if status_filter else None
        except ValueError:
            return ActionResult(False, "list_tasks", f"Invalid status: {status_filter}")

        tasks = self.task_service.get_all_tasks(status_enum)[:limit]
        return ActionResult(
            True,
            "list_tasks",
            f"Found {len(tasks)} tasks",
            {
                "tasks": [
                    {
                        "id": t.id,
                        "content": t.content,
                        "status": t.status.value,
                    }
                    for t in tasks
                ]
            },
        )

    def _search_tasks(self, action: Dict[str, Any]) -> ActionResult:
        """Search tasks."""
        query = action.get("query")
        limit = action.get("limit", 20)

        tasks = self.task_service.search_tasks(query)[:limit]
        return ActionResult(
            True,
            "search_tasks",
            f"Found {len(tasks)} matching tasks",
            {
                "tasks": [
                    {
                        "id": t.id,
                        "content": t.content,
                        "notes": t.notes,
                        "status": t.status.value,
                    }
                    for t in tasks
                ]
            },
        )

    # =========================================================================
    # MEMORY ACTION HANDLERS
    # =========================================================================

    def _create_memory(self, action: Dict[str, Any]) -> ActionResult:
        """Create a memory."""
        content = action.get("content")
        notes = action.get("notes", "")

        memory = self.memory_service.create_memory(content, notes)
        return ActionResult(
            True,
            "create_memory",
            f"Created memory {memory.id}",
            {
                "memory_id": memory.id,
                "content": memory.content,
            },
        )

    def _update_memory(self, action: Dict[str, Any]) -> ActionResult:
        """Update a memory."""
        memory_id = action.get("memory_id")
        kwargs = {}

        if "content" in action:
            kwargs["content"] = action["content"]
        if "notes" in action:
            kwargs["notes"] = action["notes"]

        memory = self.memory_service.update_memory(memory_id, **kwargs)
        if not memory:
            return ActionResult(False, "update_memory", f"Memory {memory_id} not found")

        return ActionResult(
            True,
            "update_memory",
            f"Updated memory {memory.id}",
            {
                "memory_id": memory.id,
                "content": memory.content,
            },
        )

    def _delete_memory(self, action: Dict[str, Any]) -> ActionResult:
        """Delete a memory."""
        memory_id = action.get("memory_id")
        success = self.memory_service.delete_memory(memory_id)

        if success:
            return ActionResult(True, "delete_memory", f"Deleted memory {memory_id}")
        return ActionResult(False, "delete_memory", f"Memory {memory_id} not found")

    def _get_memory(self, action: Dict[str, Any]) -> ActionResult:
        """Get a memory by ID."""
        memory_id = action.get("memory_id")
        memory = self.memory_service.get_memory(memory_id)

        if not memory:
            return ActionResult(False, "get_memory", f"Memory {memory_id} not found")

        return ActionResult(
            True,
            "get_memory",
            f"Retrieved memory {memory_id}",
            {
                "memory_id": memory.id,
                "content": memory.content,
                "notes": memory.notes,
            },
        )

    def _list_memories(self, action: Dict[str, Any]) -> ActionResult:
        """List all memories."""
        limit = action.get("limit", 50)

        memories = self.memory_service.get_all_memories()[:limit]
        return ActionResult(
            True,
            "list_memories",
            f"Found {len(memories)} memories",
            {
                "memories": [
                    {
                        "id": m.id,
                        "content": m.content,
                    }
                    for m in memories
                ]
            },
        )

    def _search_memories(self, action: Dict[str, Any]) -> ActionResult:
        """Search memories."""
        query = action.get("query")
        limit = action.get("limit", 20)

        memories = self.memory_service.search_memories(query)[:limit]
        return ActionResult(
            True,
            "search_memories",
            f"Found {len(memories)} matching memories",
            {
                "memories": [
                    {
                        "id": m.id,
                        "content": m.content,
                        "notes": m.notes,
                    }
                    for m in memories
                ]
            },
        )

    # =========================================================================
    # GOAL ACTION HANDLERS
    # =========================================================================

    def _create_goal(self, action: Dict[str, Any]) -> ActionResult:
        """Create a goal."""
        content = action.get("content")
        notes = action.get("notes", "")
        status = action.get("status", "pending")

        try:
            status_enum = GoalStatus(status)
        except ValueError:
            return ActionResult(False, "create_goal", f"Invalid status: {status}")

        goal = self.goal_service.create_goal(content, notes, status_enum)
        return ActionResult(
            True,
            "create_goal",
            f"Created goal {goal.id}",
            {
                "goal_id": goal.id,
                "content": goal.content,
                "status": goal.status.value,
            },
        )

    def _update_goal(self, action: Dict[str, Any]) -> ActionResult:
        """Update a goal."""
        goal_id = action.get("goal_id")
        kwargs = {}

        if "content" in action:
            kwargs["content"] = action["content"]
        if "notes" in action:
            kwargs["notes"] = action["notes"]
        if "status" in action:
            try:
                kwargs["status"] = GoalStatus(action["status"])
            except ValueError:
                return ActionResult(False, "update_goal", f"Invalid status: {action['status']}")

        goal = self.goal_service.update_goal(goal_id, **kwargs)
        if not goal:
            return ActionResult(False, "update_goal", f"Goal {goal_id} not found")

        return ActionResult(
            True,
            "update_goal",
            f"Updated goal {goal.id}",
            {
                "goal_id": goal.id,
                "content": goal.content,
                "status": goal.status.value,
            },
        )

    def _delete_goal(self, action: Dict[str, Any]) -> ActionResult:
        """Delete a goal."""
        goal_id = action.get("goal_id")
        success = self.goal_service.delete_goal(goal_id)

        if success:
            return ActionResult(True, "delete_goal", f"Deleted goal {goal_id}")
        return ActionResult(False, "delete_goal", f"Goal {goal_id} not found")

    def _get_goal(self, action: Dict[str, Any]) -> ActionResult:
        """Get a goal by ID."""
        goal_id = action.get("goal_id")
        goal = self.goal_service.get_goal(goal_id)

        if not goal:
            return ActionResult(False, "get_goal", f"Goal {goal_id} not found")

        return ActionResult(
            True,
            "get_goal",
            f"Retrieved goal {goal_id}",
            {
                "goal_id": goal.id,
                "content": goal.content,
                "notes": goal.notes,
                "status": goal.status.value,
            },
        )

    def _list_goals(self, action: Dict[str, Any]) -> ActionResult:
        """List all goals."""
        status_filter = action.get("status")
        limit = action.get("limit", 50)

        try:
            status_enum = GoalStatus(status_filter) if status_filter else None
        except ValueError:
            return ActionResult(False, "list_goals", f"Invalid status: {status_filter}")

        goals = self.goal_service.get_all_goals(status_enum)[:limit]
        return ActionResult(
            True,
            "list_goals",
            f"Found {len(goals)} goals",
            {
                "goals": [
                    {
                        "id": g.id,
                        "content": g.content,
                        "status": g.status.value,
                    }
                    for g in goals
                ]
            },
        )

    def _search_goals(self, action: Dict[str, Any]) -> ActionResult:
        """Search goals."""
        query = action.get("query")
        limit = action.get("limit", 20)

        goals = self.goal_service.search_goals(query)[:limit]
        return ActionResult(
            True,
            "search_goals",
            f"Found {len(goals)} matching goals",
            {
                "goals": [
                    {
                        "id": g.id,
                        "content": g.content,
                        "notes": g.notes,
                        "status": g.status.value,
                    }
                    for g in goals
                ]
            },
        )

    # =========================================================================
    # DATAVAULT ACTION HANDLERS
    # =========================================================================

    def _serialize_datavault_item(self, item, *, include_content: bool = False) -> Dict[str, Any]:
        """Create a consistent metadata dict for datavault items."""
        if not item:
            return {}

        content = getattr(item, "content", "") or ""
        data: Dict[str, Any] = {
            "item_id": item.id,
            "datavault_id": item.id,
            "filetype": getattr(item, "filetype", "text"),
            "notes": getattr(item, "notes", ""),
            "content_length": len(content),
        }

        created_at = getattr(item, "created_at", None)
        updated_at = getattr(item, "updated_at", None)
        if created_at:
            data["created_at"] = created_at.isoformat()
        if updated_at:
            data["updated_at"] = updated_at.isoformat()

        if include_content:
            data["content"] = content

        return data

    def _datavault_store(self, action: Dict[str, Any]) -> ActionResult:
        """Store content in datavault."""
        content = action.get("content")
        filetype = action.get("filetype", "text")
        notes = action.get("notes", "")

        item = self.datavault_service.store_item(content, filetype, notes)
        return ActionResult(
            True,
            "datavault_store",
            f"Stored datavault item {item.id}",
            self._serialize_datavault_item(item),
        )

    def _datavault_get(self, action: Dict[str, Any]) -> ActionResult:
        """Get datavault item."""
        item_id = action.get("item_id")
        item = self.datavault_service.get_item(item_id)

        if not item:
            missing = {"item_id": item_id, "datavault_id": item_id}
            return ActionResult(False, "datavault_get", f"Datavault item {item_id} not found", missing)

        return ActionResult(
            True,
            "datavault_get",
            f"Retrieved datavault item {item_id}",
            self._serialize_datavault_item(item, include_content=True),
        )

    def _datavault_update(self, action: Dict[str, Any]) -> ActionResult:
        """Update datavault item."""
        item_id = action.get("item_id")
        kwargs = {}

        if "content" in action:
            kwargs["content"] = action["content"]
        if "filetype" in action:
            kwargs["filetype"] = action["filetype"]
        if "notes" in action:
            kwargs["notes"] = action["notes"]

        item = self.datavault_service.update_item(item_id, **kwargs)
        if not item:
            missing = {"item_id": item_id, "datavault_id": item_id}
            return ActionResult(False, "datavault_update", f"Datavault item {item_id} not found", missing)

        data = self._serialize_datavault_item(item)
        data["updated"] = True
        return ActionResult(
            True,
            "datavault_update",
            f"Updated datavault item {item.id}",
            data,
        )

    def _datavault_delete(self, action: Dict[str, Any]) -> ActionResult:
        """Delete datavault item."""
        item_id = action.get("item_id")
        success = self.datavault_service.delete_item(item_id)
        data = {"item_id": item_id, "datavault_id": item_id, "deleted": success}

        if success:
            return ActionResult(True, "datavault_delete", f"Deleted datavault item {item_id}", data)
        return ActionResult(False, "datavault_delete", f"Datavault item {item_id} not found", data)

    def _datavault_list(self, action: Dict[str, Any]) -> ActionResult:
        """List datavault items."""
        filetype_filter = action.get("filetype")
        limit = action.get("limit", 50)

        items = self.datavault_service.get_all_items(filetype_filter)[:limit]
        return ActionResult(
            True,
            "datavault_list",
            f"Found {len(items)} datavault items",
            {
                "items": [self._serialize_datavault_item(i) for i in items]
            },
        )

    def _datavault_search(self, action: Dict[str, Any]) -> ActionResult:
        """Search datavault items."""
        query = action.get("query")
        limit = action.get("limit", 20)

        items = self.datavault_service.search_items(query)[:limit]

        def _add_preview(item):
            data = self._serialize_datavault_item(item)
            content = item.content or ""
            preview = content[:200]
            if len(content) > 200:
                preview = preview.rstrip() + "..."
            data["content_preview"] = preview
            return data

        return ActionResult(
            True,
            "datavault_search",
            f"Found {len(items)} matching datavault items",
            {
                "items": [_add_preview(i) for i in items]
            },
        )

    # =========================================================================
    # CODE EXECUTION
    # =========================================================================

    def _execute_code(self, action: Dict[str, Any]) -> ActionResult:
        """Execute Python code."""
        if not self.enable_code_execution:
            return ActionResult(False, "execute_code", "Code execution is disabled")

        code = action.get("code")

        # Emit code_execution_start event for UI
        if self.progress_callback:
            self.progress_callback({
                "type": "code_execution_start",
                "code": code,
            })

        # Execute code with GemBrain API
        try:
            exec_result = self.code_executor.execute(code)

            # Extract values from result dictionary
            success = exec_result["success"]
            stdout = exec_result["stdout"]
            stderr = exec_result["stderr"]
            result = exec_result["result"]
            error = exec_result["error"]
            exec_time = exec_result["execution_time"]

            result_data = {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "result": result,
                "error": error,
                "execution_time": exec_time,
            }

            # Emit code_execution_result event for UI
            if self.progress_callback:
                self.progress_callback({
                    "type": "code_execution_result",
                    "data": result_data,
                })

            return ActionResult(
                success,
                "execute_code",
                "Code executed successfully" if success else "Code execution failed",
                result_data,
            )
        except Exception as e:
            error_data = {
                "success": False,
                "error": str(e),
            }

            # Emit code_execution_result event for UI (with error)
            if self.progress_callback:
                self.progress_callback({
                    "type": "code_execution_result",
                    "data": error_data,
                })

            return ActionResult(
                False,
                "execute_code",
                f"Code execution error: {e}",
                error_data,
            )

    # =========================================================================
    # UTILITY ACTIONS
    # =========================================================================

    def _log_action(self, action: Dict[str, Any]) -> ActionResult:
        """Record a log entry for debugging/traceability."""
        content = action.get("content", "")
        level = action.get("level", "info").lower()
        log_map = {
            "debug": logger.debug,
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
        }
        log_func = log_map.get(level, logger.info)
        log_func(f"[ACTION LOG] {content}")
        return ActionResult(True, "log", f"Logged message at {level}", {"content": content})
