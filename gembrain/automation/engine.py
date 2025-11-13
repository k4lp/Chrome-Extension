"""Automation engine using APScheduler."""

from typing import Optional, Dict, Any
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from loguru import logger

from ..config.models import Settings
from ..agents.orchestrator import Orchestrator
from ..core.services import TaskService, MemoryService, AutomationService
from ..core.models import AutomationTrigger


class AutomationEngine:
    """Manages and runs automated tasks."""

    def __init__(self, db: Session, orchestrator: Orchestrator, settings: Settings):
        """Initialize automation engine.

        Args:
            db: Database session
            orchestrator: Orchestrator instance
            settings: Application settings
        """
        self.db = db
        self.orchestrator = orchestrator
        self.settings = settings
        self.scheduler = BackgroundScheduler()

        # Services
        self.task_service = TaskService(db)
        self.memory_service = MemoryService(db)
        self.automation_service = AutomationService(db)

    def start(self) -> None:
        """Start the automation engine."""
        logger.info("Starting automation engine")

        # Schedule daily review
        if self.settings.automations.daily_review_enabled:
            self._schedule_daily_review()

        # Schedule weekly review
        if self.settings.automations.weekly_review_enabled:
            self._schedule_weekly_review()

        # Schedule note resurfacing
        if self.settings.automations.resurface_notes_enabled:
            self._schedule_note_resurfacing()

        # Load custom automation rules from database
        self._load_custom_rules()

        # Start scheduler
        self.scheduler.start()
        logger.info("Automation engine started")

    def stop(self) -> None:
        """Stop the automation engine."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Automation engine stopped")

    def run_automation_now(self, automation_name: str) -> None:
        """Manually trigger an automation.

        Args:
            automation_name: Name of automation to run
        """
        logger.info(f"Manually running automation: {automation_name}")

        if automation_name == "daily_review":
            self._run_daily_review()
        elif automation_name == "weekly_review":
            self._run_weekly_review()
        elif automation_name == "resurface_notes":
            self._run_note_resurfacing()
        else:
            # Check custom rules
            rule = self.automation_service.get_rule(automation_name)
            if rule:
                self._run_custom_rule(rule.id, rule.agent_task)
            else:
                logger.warning(f"Unknown automation: {automation_name}")

    def _schedule_daily_review(self) -> None:
        """Schedule daily review automation."""
        time_parts = self.settings.automations.daily_review_time.split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])

        self.scheduler.add_job(
            self._run_daily_review,
            CronTrigger(hour=hour, minute=minute),
            id="daily_review",
            name="Daily Review",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily review at {self.settings.automations.daily_review_time}")

    def _schedule_weekly_review(self) -> None:
        """Schedule weekly review automation."""
        time_parts = self.settings.automations.weekly_review_time.split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])
        day_of_week = self.settings.automations.weekly_review_day

        self.scheduler.add_job(
            self._run_weekly_review,
            CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
            id="weekly_review",
            name="Weekly Review",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled weekly review on day {day_of_week} at {self.settings.automations.weekly_review_time}"
        )

    def _schedule_note_resurfacing(self) -> None:
        """Schedule note resurfacing automation."""
        # Run daily at 9 AM
        self.scheduler.add_job(
            self._run_note_resurfacing,
            CronTrigger(hour=9, minute=0),
            id="resurface_notes",
            name="Resurface Notes",
            replace_existing=True,
        )
        logger.info("Scheduled note resurfacing daily at 9:00 AM")

    def _load_custom_rules(self) -> None:
        """Load custom automation rules from database."""
        rules = self.automation_service.get_all_rules(enabled_only=True)

        for rule in rules:
            if rule.trigger == AutomationTrigger.DAILY and rule.schedule_cron:
                try:
                    trigger = CronTrigger.from_crontab(rule.schedule_cron)
                    self.scheduler.add_job(
                        lambda r=rule: self._run_custom_rule(r.id, r.agent_task),
                        trigger,
                        id=f"custom_{rule.name}",
                        name=rule.name,
                        replace_existing=True,
                    )
                    logger.info(f"Scheduled custom rule: {rule.name}")
                except Exception as e:
                    logger.error(f"Error scheduling rule {rule.name}: {e}")

    def _run_daily_review(self) -> None:
        """Run daily review automation."""
        logger.info("Running daily review")

        try:
            # Gather today's context
            today_tasks = self.task_service.get_today_tasks()
            recent_memories = self.memory_service.get_all_memories(limit=5)

            # Build context
            context = {}

            if today_tasks:
                from ..core.models import TaskStatus

                completed = [t for t in today_tasks if t.status == TaskStatus.COMPLETED]
                pending = [t for t in today_tasks if t.status != TaskStatus.COMPLETED]

                context["Today's Tasks"] = (
                    f"Completed ({len(completed)}):\n"
                    + "\n".join([f"- {t.content[:100]}" for t in completed])
                    + f"\n\nPending ({len(pending)}):\n"
                    + "\n".join([f"- {t.content[:100]}" for t in pending])
                )

            if recent_memories:
                context["Recent Memories"] = "\n".join(
                    [f"- {m.content[:100]} (updated {m.updated_at.date()})" for m in recent_memories]
                )

            # Agent task
            agent_task = """Create a brief daily review summarizing:
1. Tasks completed today
2. Tasks still pending
3. Key insights from today's memories
4. Any reflections or learnings

Store the review summary in the datavault with filetype 'md' and notes 'daily-review'."""

            # Run orchestrator
            response = self.orchestrator.run_automation(
                automation_name="daily_review",
                agent_task=agent_task,
                context=context,
            )

            if response.error:
                logger.error(f"Daily review failed: {response.error}")
            else:
                logger.info(f"Daily review completed: {len(response.actions)} actions executed")

        except Exception as e:
            logger.error(f"Error in daily review: {e}")

    def _run_weekly_review(self) -> None:
        """Run weekly review automation."""
        logger.info("Running weekly review")

        try:
            # Gather week's context
            from ..utils.time import days_ago
            from ..core.models import TaskStatus

            week_start = days_ago(7)

            # Get all tasks from the week
            all_tasks = self.task_service.get_all_tasks()
            week_tasks = [t for t in all_tasks if t.created_at >= week_start]

            # Get recent memories
            recent_memories = self.memory_service.get_all_memories(limit=20)
            week_memories = [m for m in recent_memories if m.updated_at >= week_start]

            # Build context
            context = {}

            if week_tasks:
                completed = [t for t in week_tasks if t.status == TaskStatus.COMPLETED]
                pending = [
                    t for t in week_tasks if t.status in (TaskStatus.PENDING, TaskStatus.ONGOING)
                ]

                context["This Week's Tasks"] = (
                    f"Completed ({len(completed)}):\n"
                    + "\n".join([f"- {t.content[:100]}" for t in completed[:20]])
                    + f"\n\nStill Open ({len(pending)}):\n"
                    + "\n".join([f"- {t.content[:100]}" for t in pending[:20]])
                )

            if week_memories:
                context["This Week's Memories"] = "\n".join(
                    [f"- {m.content[:100]} ({m.updated_at.date()})" for m in week_memories[:15]]
                )

            # Agent task
            agent_task = """Create a comprehensive weekly review summarizing:
1. Tasks completed this week
2. Tasks still in progress
3. Key learnings and insights from memories
4. Challenges encountered
5. Focus areas for next week

Store the review summary in the datavault with filetype 'md' and notes 'weekly-review'."""

            # Run orchestrator
            response = self.orchestrator.run_automation(
                automation_name="weekly_review",
                agent_task=agent_task,
                context=context,
            )

            if response.error:
                logger.error(f"Weekly review failed: {response.error}")
            else:
                logger.info(f"Weekly review completed: {len(response.actions)} actions executed")

        except Exception as e:
            logger.error(f"Error in weekly review: {e}")

    def _run_note_resurfacing(self) -> None:
        """Run memory resurfacing automation."""
        logger.info("Running memory resurfacing")

        try:
            # Get all memories
            all_memories = self.memory_service.get_all_memories(
                limit=self.settings.automations.resurface_notes_count
            )

            if not all_memories:
                logger.info("No memories to resurface")
                return

            # Filter old memories (older than specified days)
            from ..utils.time import days_ago
            cutoff_date = days_ago(self.settings.automations.resurface_notes_age_days)
            old_memories = [m for m in all_memories if m.updated_at < cutoff_date]

            if not old_memories:
                logger.info("No old memories to resurface")
                return

            # Build context
            context = {
                "Old Memories to Resurface": "\n".join(
                    [
                        f"- [{m.id}] {m.content[:200]}... (last updated: {m.updated_at.date()})"
                        for m in old_memories
                    ]
                )
            }

            # Agent task
            agent_task = f"""Review these old memories that haven't been updated in {self.settings.automations.resurface_notes_age_days} days.

For each memory, decide:
1. Should it be brought back to attention? Create a task if yes.
2. Should it be updated with new information? Update the memory.
3. Is it still relevant? Delete if no longer needed.

Be thoughtful - only resurface truly valuable insights."""

            # Run orchestrator
            response = self.orchestrator.run_automation(
                automation_name="resurface_notes",
                agent_task=agent_task,
                context=context,
            )

            if response.error:
                logger.error(f"Memory resurfacing failed: {response.error}")
            else:
                logger.info(
                    f"Memory resurfacing completed: {len(response.actions)} actions executed"
                )

        except Exception as e:
            logger.error(f"Error in memory resurfacing: {e}")

    def _run_custom_rule(self, rule_id: int, agent_task: str) -> None:
        """Run a custom automation rule.

        Args:
            rule_id: Rule ID
            agent_task: Task for agent
        """
        logger.info(f"Running custom rule {rule_id}")

        try:
            # Run orchestrator with the custom task
            response = self.orchestrator.run_automation(
                automation_name=f"custom_{rule_id}",
                agent_task=agent_task,
                context={},
            )

            # Update last run time
            self.automation_service.update_last_run(rule_id)

            if response.error:
                logger.error(f"Custom rule {rule_id} failed: {response.error}")
            else:
                logger.info(
                    f"Custom rule {rule_id} completed: {len(response.actions)} actions executed"
                )

        except Exception as e:
            logger.error(f"Error in custom rule {rule_id}: {e}")
