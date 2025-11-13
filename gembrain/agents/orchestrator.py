"""Main orchestrator for agent interactions."""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from loguru import logger

from .gemini_client import GeminiClient
from .prompts import get_system_prompt
from .tools import ActionExecutor, ActionResult
from ..config.models import Settings
from ..core.services import NoteService, TaskService, ProjectService, MemoryService
from ..utils.json_utils import parse_actions_from_response


@dataclass
class UIContext:
    """Context from the UI."""

    current_note_id: Optional[int] = None
    current_project_id: Optional[int] = None
    active_panel: str = "chat"


@dataclass
class OrchestratorResponse:
    """Response from orchestrator."""

    reply_text: str
    actions: List[Dict[str, Any]]
    action_results: Optional[List[ActionResult]] = None
    error: Optional[str] = None


class Orchestrator:
    """Orchestrates agent interactions and action execution."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize orchestrator.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings
        self.gemini_client = GeminiClient(settings)
        self.action_executor = ActionExecutor(db)

        # Services for building context
        self.note_service = NoteService(db)
        self.task_service = TaskService(db)
        self.project_service = ProjectService(db)
        self.memory_service = MemoryService(db)

    def reconfigure(self, settings: Settings) -> None:
        """Reconfigure with new settings.

        Args:
            settings: New settings
        """
        self.settings = settings
        self.gemini_client.reconfigure(settings)

    def run_user_message(
        self,
        user_message: str,
        ui_context: Optional[UIContext] = None,
        auto_apply_actions: bool = False,
    ) -> OrchestratorResponse:
        """Process user message and return response with actions.

        Args:
            user_message: User's message
            ui_context: Optional UI context
            auto_apply_actions: Whether to automatically apply actions

        Returns:
            OrchestratorResponse
        """
        try:
            # Build context
            context_blocks = self._build_context(ui_context)

            # Get system prompt
            system_prompt = get_system_prompt(self.settings.api.system_prompt_variant)

            # Call Gemini
            logger.info(f"Processing user message: {user_message[:100]}...")
            response_text = self.gemini_client.generate(
                system_prompt=system_prompt,
                user_message=user_message,
                context_blocks=context_blocks,
            )

            # Parse actions from response
            parsed = parse_actions_from_response(response_text)
            reply_text = parsed["reply"]
            actions = parsed["actions"]

            logger.info(f"Parsed {len(actions)} actions from response")

            # Optionally execute actions
            action_results = None
            if auto_apply_actions and actions:
                action_results = self._execute_actions(actions)

            return OrchestratorResponse(
                reply_text=reply_text,
                actions=actions,
                action_results=action_results,
            )

        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return OrchestratorResponse(
                reply_text="",
                actions=[],
                error=str(e),
            )

    def apply_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """Apply a list of actions.

        Args:
            actions: List of action dictionaries

        Returns:
            List of ActionResults
        """
        return self._execute_actions(actions)

    def run_automation(
        self,
        automation_name: str,
        agent_task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestratorResponse:
        """Run an automation task.

        Args:
            automation_name: Name of automation
            agent_task: Task description for agent
            context: Optional context dictionary

        Returns:
            OrchestratorResponse
        """
        try:
            # Build context from provided data
            context_blocks = []
            if context:
                for key, value in context.items():
                    context_blocks.append(f"{key}:\n{value}")

            # Get system prompt
            system_prompt = get_system_prompt(self.settings.api.system_prompt_variant)

            # Call Gemini with automation task
            logger.info(f"Running automation: {automation_name}")
            response_text = self.gemini_client.generate(
                system_prompt=system_prompt,
                user_message=agent_task,
                context_blocks=context_blocks,
            )

            # Parse and execute actions
            parsed = parse_actions_from_response(response_text)
            reply_text = parsed["reply"]
            actions = parsed["actions"]

            # Auto-apply actions for automations
            action_results = None
            if actions:
                action_results = self._execute_actions(actions)

            logger.info(f"Automation {automation_name} completed with {len(actions)} actions")

            return OrchestratorResponse(
                reply_text=reply_text,
                actions=actions,
                action_results=action_results,
            )

        except Exception as e:
            logger.error(f"Error in automation {automation_name}: {e}")
            return OrchestratorResponse(
                reply_text="",
                actions=[],
                error=str(e),
            )

    def _build_context(self, ui_context: Optional[UIContext] = None) -> List[str]:
        """Build context blocks for agent.

        Args:
            ui_context: Optional UI context

        Returns:
            List of context blocks
        """
        blocks = []

        # Add memories
        if self.settings.agent_behavior.include_context_notes:
            memories = self.memory_service.get_all_memories(
                min_importance=self.settings.agent_behavior.memory_update_threshold_importance
            )
            if memories:
                memory_text = "\n".join([f"- {m.key}: {m.content}" for m in memories])
                blocks.append(f"Long-term memories:\n{memory_text}")

        # Add recent notes
        if self.settings.agent_behavior.include_context_notes:
            recent_notes = self.note_service.get_recent_notes(
                limit=self.settings.agent_behavior.max_context_items
            )
            if recent_notes:
                notes_text = "\n".join(
                    [f"- [{n.id}] {n.title} (updated: {n.updated_at})" for n in recent_notes]
                )
                blocks.append(f"Recent notes:\n{notes_text}")

        # Add open tasks
        if self.settings.agent_behavior.include_context_tasks:
            from ..core.models import TaskStatus

            open_tasks = self.task_service.get_tasks_by_status(TaskStatus.TODO)
            doing_tasks = self.task_service.get_tasks_by_status(TaskStatus.DOING)
            all_open = open_tasks + doing_tasks

            # Limit tasks
            all_open = all_open[: self.settings.agent_behavior.max_context_items]

            if all_open:
                tasks_text = "\n".join(
                    [
                        f"- [{t.id}] {t.title} ({t.status.value})"
                        + (f" - Due: {t.due_date.date()}" if t.due_date else "")
                        for t in all_open
                    ]
                )
                blocks.append(f"Open tasks:\n{tasks_text}")

        # Add current UI context
        if ui_context:
            context_parts = []

            if ui_context.current_note_id:
                note = self.note_service.get_note(ui_context.current_note_id)
                if note:
                    context_parts.append(f"Currently viewing note: {note.title}")

            if ui_context.current_project_id:
                project = self.project_service.get_project(ui_context.current_project_id)
                if project:
                    context_parts.append(f"Currently viewing project: {project.name}")

            if context_parts:
                blocks.append("Current UI context:\n" + "\n".join(context_parts))

        return blocks

    def _execute_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """Execute actions with safety checks.

        Args:
            actions: List of actions to execute

        Returns:
            List of ActionResults
        """
        # Check max actions limit
        max_actions = self.settings.agent_behavior.max_actions_per_message
        if len(actions) > max_actions:
            logger.warning(
                f"Too many actions ({len(actions)}), limiting to {max_actions}"
            )
            actions = actions[:max_actions]

        # Execute actions
        return self.action_executor.execute_actions(actions)

    def is_configured(self) -> bool:
        """Check if orchestrator is properly configured.

        Returns:
            True if configured and ready
        """
        return self.gemini_client.is_configured()
