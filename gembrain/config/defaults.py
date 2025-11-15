"""Default configuration values and presets."""

from typing import Dict, Any

# Default settings as a dictionary (useful for initialization)
DEFAULT_SETTINGS: Dict[str, Any] = {
    "api": {
        "gemini_api_key": "",
        "default_model": "gemini-1.5-pro",
        "max_output_tokens": 8192,
        "temperature": 0.7,
        "system_prompt_variant": "second_brain",
    },
    "storage": {
        "db_path": "~/.gembrain/gembrain.db",
        "backup_dir": "~/.gembrain/backups",
        "auto_backup_enabled": True,
        "auto_backup_interval_hours": 24,
    },
    "agent_behavior": {
        "auto_structured_actions": False,
        "ask_before_destructive": True,
        "max_actions_per_message": 10,
        "memory_update_threshold_importance": 3,
        "include_context_notes": True,
        "include_context_tasks": True,
        "max_context_items": 10,
        "enable_code_execution": True,
        "enable_iterative_reasoning": False,
        "max_reasoning_iterations": 50,
        "verification_model": "gemini-1.5-flash",
        "auto_verify": True,
        "verification_retry_limit": 5,
    },
    "automations": {
        "daily_review_enabled": False,
        "daily_review_time": "22:00",
        "weekly_review_enabled": False,
        "weekly_review_day": 6,
        "weekly_review_time": "10:00",
        "resurface_notes_enabled": False,
        "resurface_notes_age_days": 30,
        "resurface_notes_count": 3,
    },
    "ui": {
        "theme": "light",
        "font_family": "Segoe UI",
        "font_size": 10,
        "compact_mode": False,
        "window_width": 1400,
        "window_height": 900,
        "show_context_panel": True,
        "markdown_preview": True,
    },
}

# Available Gemini models
AVAILABLE_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash-exp",
]

# Available system prompt variants
PROMPT_VARIANTS = [
    "second_brain",
    "research_mode",
    "creative_mode",
    "analytical_mode",
]

# Theme configurations
THEMES = {
    "light": {
        "name": "Light",
        "description": "Clean, minimal light theme",
    },
    "dark": {
        "name": "Dark",
        "description": "Easy on the eyes dark theme",
    },
}

# Font families (common cross-platform fonts)
FONT_FAMILIES = [
    "Segoe UI",
    "Arial",
    "Helvetica",
    "Roboto",
    "Ubuntu",
    "SF Pro",
    "System",
]
