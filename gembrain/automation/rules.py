"""Automation rule definitions and helpers."""

from typing import Dict, Any, List
from ..core.models import AutomationTrigger


# Predefined automation rule templates
AUTOMATION_TEMPLATES = [
    {
        "name": "daily_review",
        "trigger": AutomationTrigger.DAILY,
        "schedule_cron": "0 22 * * *",  # 10 PM daily
        "agent_task": "Create a daily review note summarizing today's activities, tasks, and insights.",
        "description": "Creates a daily review note every evening",
    },
    {
        "name": "weekly_review",
        "trigger": AutomationTrigger.WEEKLY,
        "schedule_cron": "0 10 * * 0",  # 10 AM on Sunday
        "agent_task": "Create a weekly review note summarizing the week's progress, learnings, and plan for next week.",
        "description": "Creates a comprehensive weekly review every Sunday",
    },
    {
        "name": "morning_planning",
        "trigger": AutomationTrigger.DAILY,
        "schedule_cron": "0 8 * * *",  # 8 AM daily
        "agent_task": "Review today's tasks and create a brief morning planning note with priorities.",
        "description": "Creates a morning planning note with today's priorities",
    },
    {
        "name": "resurface_old_notes",
        "trigger": AutomationTrigger.DAILY,
        "schedule_cron": "0 9 * * *",  # 9 AM daily
        "agent_task": "Find notes that haven't been updated in 30+ days and suggest which should be revisited.",
        "description": "Resurfaces old notes that may need attention",
    },
    {
        "name": "project_check_in",
        "trigger": AutomationTrigger.WEEKLY,
        "schedule_cron": "0 14 * * 1",  # 2 PM on Monday
        "agent_task": "Review all active projects and create status updates with next steps.",
        "description": "Weekly project status check-in",
    },
]


def get_automation_template(name: str) -> Dict[str, Any]:
    """Get automation template by name.

    Args:
        name: Template name

    Returns:
        Template dictionary or empty dict if not found
    """
    for template in AUTOMATION_TEMPLATES:
        if template["name"] == name:
            return template.copy()
    return {}


def get_all_templates() -> List[Dict[str, Any]]:
    """Get all automation templates.

    Returns:
        List of template dictionaries
    """
    return [t.copy() for t in AUTOMATION_TEMPLATES]


def validate_cron(cron_str: str) -> bool:
    """Validate cron expression.

    Args:
        cron_str: Cron expression to validate

    Returns:
        True if valid
    """
    try:
        from apscheduler.triggers.cron import CronTrigger

        CronTrigger.from_crontab(cron_str)
        return True
    except Exception:
        return False
