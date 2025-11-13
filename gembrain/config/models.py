"""Configuration models using Pydantic."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import os


class APIConfig(BaseModel):
    """API and model configuration."""

    gemini_api_key: str = Field(default="", description="Gemini API key")
    default_model: str = Field(default="gemini-1.5-pro", description="Default Gemini model")
    max_output_tokens: int = Field(default=8192, ge=1, le=32768, description="Maximum output tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")
    system_prompt_variant: str = Field(
        default="second_brain", description="System prompt variant to use"
    )


class StorageConfig(BaseModel):
    """Storage and backup configuration."""

    db_path: str = Field(
        default_factory=lambda: str(Path.home() / ".gembrain" / "gembrain.db"),
        description="Path to SQLite database",
    )
    backup_dir: str = Field(
        default_factory=lambda: str(Path.home() / ".gembrain" / "backups"),
        description="Backup directory",
    )
    auto_backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    auto_backup_interval_hours: int = Field(
        default=24, ge=1, le=168, description="Backup interval in hours"
    )

    @field_validator("db_path", "backup_dir")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand user home directory in paths."""
        return os.path.expanduser(v)


class AgentBehaviorConfig(BaseModel):
    """Agent behavior configuration."""

    auto_structured_actions: bool = Field(
        default=False, description="Auto-apply agent's suggested actions"
    )
    ask_before_destructive: bool = Field(
        default=True, description="Confirm before destructive changes"
    )
    max_actions_per_message: int = Field(
        default=10, ge=1, le=50, description="Maximum actions per message"
    )
    memory_update_threshold_importance: int = Field(
        default=3, ge=1, le=5, description="Minimum importance for memory updates"
    )
    include_context_notes: bool = Field(
        default=True, description="Include related notes in context"
    )
    include_context_tasks: bool = Field(
        default=True, description="Include related tasks in context"
    )
    max_context_items: int = Field(
        default=10, ge=1, le=50, description="Maximum context items to include"
    )
    enable_code_execution: bool = Field(
        default=True, description="Allow agent to execute Python code with full system access"
    )


class AutomationConfig(BaseModel):
    """Automation rules configuration."""

    daily_review_enabled: bool = Field(default=False, description="Enable daily review")
    daily_review_time: str = Field(default="22:00", description="Daily review time (HH:MM)")
    weekly_review_enabled: bool = Field(default=False, description="Enable weekly review")
    weekly_review_day: int = Field(
        default=6, ge=0, le=6, description="Weekly review day (0=Mon, 6=Sun)"
    )
    weekly_review_time: str = Field(default="10:00", description="Weekly review time (HH:MM)")
    resurface_notes_enabled: bool = Field(default=False, description="Enable note resurfacing")
    resurface_notes_age_days: int = Field(
        default=30, ge=1, le=365, description="Age threshold for resurfacing notes"
    )
    resurface_notes_count: int = Field(
        default=3, ge=1, le=10, description="Number of notes to resurface"
    )

    @field_validator("daily_review_time", "weekly_review_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format is HH:MM."""
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
        except ValueError as e:
            raise ValueError(f"Invalid time format: {e}")
        return v


class UIConfig(BaseModel):
    """UI appearance configuration."""

    theme: Literal["light", "dark"] = Field(default="light", description="UI theme")
    font_family: str = Field(default="Segoe UI", description="Font family")
    font_size: int = Field(default=10, ge=8, le=24, description="Base font size")
    compact_mode: bool = Field(default=False, description="Enable compact UI mode")
    window_width: int = Field(default=1400, ge=800, le=3840, description="Window width")
    window_height: int = Field(default=900, ge=600, le=2160, description="Window height")
    show_context_panel: bool = Field(default=True, description="Show context panel")
    markdown_preview: bool = Field(default=True, description="Enable markdown preview")


class Settings(BaseModel):
    """Root settings model."""

    api: APIConfig = Field(default_factory=APIConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    agent_behavior: AgentBehaviorConfig = Field(default_factory=AgentBehaviorConfig)
    automations: AutomationConfig = Field(default_factory=AutomationConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "ignore"
