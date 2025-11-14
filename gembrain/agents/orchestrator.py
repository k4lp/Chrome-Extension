"""Main orchestrator for agent interactions."""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from loguru import logger

from .gemini_client import GeminiClient
from .prompts import get_system_prompt
from .tools import ActionExecutor, ActionResult
from .iterative_reasoner import IterativeReasoner, ReasoningSession
from ..config.models import Settings
from ..core.services import TaskService, MemoryService, GoalService
from ..utils.json_utils import parse_actions_from_response


@dataclass
class UIContext:
    """Context from the UI."""

    active_panel: str = "chat"
    # Note: current_note_id and current_project_id removed - Notes/Projects no longer exist


@dataclass
class OrchestratorResponse:
    """Response from orchestrator."""

    reply_text: str
    actions: List[Dict[str, Any]]
    action_results: Optional[List[ActionResult]] = None
    error: Optional[str] = None
    final_output_metadata: Optional[Dict[str, Any]] = None


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
        self.action_executor = ActionExecutor(
            db, enable_code_execution=settings.agent_behavior.enable_code_execution
        )

        # Services for building context
        self.task_service = TaskService(db)
        self.memory_service = MemoryService(db)
        self.goal_service = GoalService(db)

    def reconfigure(self, settings: Settings) -> None:
        """Reconfigure with new settings.

        Args:
            settings: New settings
        """
        self.settings = settings
        self.gemini_client.reconfigure(settings)
        # Recreate action executor with new settings
        self.action_executor = ActionExecutor(
            self.db, enable_code_execution=settings.agent_behavior.enable_code_execution
        )

    def run_user_message(
        self,
        user_message: str,
        ui_context: Optional[UIContext] = None,
        auto_apply_actions: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> OrchestratorResponse:
        """Process user message and return response with actions.

        Args:
            user_message: User's message
            ui_context: Optional UI context
            auto_apply_actions: Whether to automatically apply actions
            progress_callback: Optional callback for progress updates (used in iterative mode)

        Returns:
            OrchestratorResponse
        """
        try:
            # Check if iterative reasoning is enabled
            if self.settings.agent_behavior.enable_iterative_reasoning:
                logger.info("🧠 Iterative reasoning is ENABLED - using iterative mode")

                # Run iterative reasoning
                session, approved = self.run_iterative_reasoning(
                    user_query=user_message,
                    max_iterations=self.settings.agent_behavior.max_reasoning_iterations,
                    verification_model=self.settings.agent_behavior.verification_model,
                    ui_context=ui_context,
                    progress_callback=progress_callback,
                )

                # Use rendered final output as reply, with layered fallbacks
                reply_text = session.final_output
                if not reply_text or reply_text.strip() == "":
                    if session.raw_final_output:
                        reply_text = session.raw_final_output
                        logger.warning("Rendered final output empty - falling back to raw text")
                    elif session.verification_result and session.verification_result.get("session_summary"):
                        reply_text = session.verification_result["session_summary"]
                        logger.info("dY"? Using verification session_summary as fallback output")
                    else:
                        reply_text = "Reasoning completed but no output generated."
                        logger.warning("?s??,? No final_output and no verification summary available")
                # Extract actions from all iterations
                actions = []
                for iteration in session.iterations:
                    if iteration.actions_taken:
                        actions.extend(iteration.actions_taken)

                logger.info(f"📊 Iterative reasoning: {len(session.iterations)} iterations, {len(actions)} total actions")
                logger.info(f"✅ Verification: {'APPROVED' if approved else 'FAILED'}")

                # Optionally execute actions
                action_results = None
                if auto_apply_actions and actions:
                    action_results = self._execute_actions(actions, progress_callback=progress_callback)

                final_output_metadata = {
                    "sources": session.final_output_sources,
                    "warnings": session.final_output_warnings,
                    "raw_final_output": session.raw_final_output,
                    "verification_approved": approved,
                }

                return OrchestratorResponse(
                    reply_text=reply_text,
                    actions=actions,
                    action_results=action_results,
                    final_output_metadata=final_output_metadata,
                )

            # Standard mode (iterative reasoning disabled)
            logger.info("💬 Iterative reasoning is DISABLED - using standard mode")

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
                action_results = self._execute_actions(actions, progress_callback=progress_callback)

            return OrchestratorResponse(
                reply_text=reply_text,
                actions=actions,
                action_results=action_results,
                final_output_metadata=None,
            )

        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return OrchestratorResponse(
                reply_text="",
                actions=[],
                error=str(e),
                final_output_metadata=None,
            )

    def apply_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """Apply a list of actions.

        Args:
            actions: List of action dictionaries

        Returns:
            List of ActionResults
        """
        return self._execute_actions(actions)

    def run_iterative_reasoning(
        self,
        user_query: str,
        max_iterations: int = 50,
        verification_model: Optional[str] = None,
        ui_context: Optional[UIContext] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[ReasoningSession, bool]:
        """Run iterative reasoning with verification.

        Args:
            user_query: User's query
            max_iterations: Maximum iterations to run
            verification_model: Optional separate model for verification
            ui_context: Optional UI context
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (ReasoningSession, verification_approved)
        """
        logger.info(f"🧠 Starting iterative reasoning: {user_query}")

        # Build initial context
        initial_context = self._build_context(ui_context)

        # Create reasoner
        reasoner = IterativeReasoner(
            gemini_client=self.gemini_client,
            settings=self.settings,
            action_handler=self.action_executor,
            max_iterations=max_iterations,
        )

        # Run reasoning iterations
        session = reasoner.reason(user_query, initial_context, progress_callback)

        logger.info(
            f"✅ Reasoning completed: {len(session.iterations)} iterations, "
            f"Final output: {len(session.final_output or '')} chars"
        )

        # Run verification
        logger.info("🔍 Running verification...")
        verification_result = reasoner.verify(session, verification_model)

        approved = verification_result.get("approved", False)

        if approved:
            logger.info("✅ Verification PASSED - Output approved")
        else:
            logger.warning("❌ Verification FAILED - Output needs more work")
            logger.warning(f"Reason: {verification_result.get('verdict', 'Unknown')}")

        return session, approved

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
                final_output_metadata=None,
            )

        except Exception as e:
            logger.error(f"Error in automation {automation_name}: {e}")
            return OrchestratorResponse(
                reply_text="",
                actions=[],
                error=str(e),
                final_output_metadata=None,
            )

    def _build_context(self, ui_context: Optional[UIContext] = None) -> List[str]:
        """Build context blocks for agent.

        Args:
            ui_context: Optional UI context

        Returns:
            List of context blocks
        """
        blocks = []

        # Add memories (small hints and clues)
        if self.settings.agent_behavior.include_context_notes:
            memories = self.memory_service.get_all_memories()
            # Limit to most recent
            memories = memories[: self.settings.agent_behavior.max_context_items]
            if memories:
                memory_text = "\n".join([f"- [{m.id}] {m.content}" for m in memories])
                blocks.append(f"Long-term memories:\n{memory_text}")

        # Add open tasks
        if self.settings.agent_behavior.include_context_tasks:
            from ..core.models import TaskStatus

            pending_tasks = self.task_service.get_all_tasks(TaskStatus.PENDING)
            ongoing_tasks = self.task_service.get_all_tasks(TaskStatus.ONGOING)
            all_open = pending_tasks + ongoing_tasks

            # Limit tasks
            all_open = all_open[: self.settings.agent_behavior.max_context_items]

            if all_open:
                tasks_text = "\n".join(
                    [f"- [{t.id}] {t.content[:100]}... ({t.status.value})" for t in all_open]
                )
                blocks.append(f"Open tasks:\n{tasks_text}")

        # Add pending goals
        from ..core.models import GoalStatus

        pending_goals = self.goal_service.get_all_goals(GoalStatus.PENDING)
        pending_goals = pending_goals[: self.settings.agent_behavior.max_context_items]

        if pending_goals:
            goals_text = "\n".join([f"- [{g.id}] {g.content}" for g in pending_goals])
            blocks.append(f"Pending goals:\n{goals_text}")

        # Add current UI context
        if ui_context:
            blocks.append(f"Current UI panel: {ui_context.active_panel}")

        return blocks

    def _execute_actions(self, actions: List[Dict[str, Any]], progress_callback: Optional[callable] = None) -> List[ActionResult]:
        """Execute actions with safety checks.

        Args:
            actions: List of actions to execute
            progress_callback: Optional callback for progress updates

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

        # Execute actions with progress callback
        return self.action_executor.execute_actions(actions, progress_callback=progress_callback)

    def is_configured(self) -> bool:
        """Check if orchestrator is properly configured.

        Returns:
            True if configured and ready
        """
        return self.gemini_client.is_configured()
