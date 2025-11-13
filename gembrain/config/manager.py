"""Configuration manager for loading and saving settings."""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

from .models import Settings
from .defaults import DEFAULT_SETTINGS


class ConfigManager:
    """Manages loading, saving, and validating configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_path: Path to config file. Defaults to ~/.gembrain/config.json
        """
        if config_path is None:
            config_path = Path.home() / ".gembrain" / "config.json"
        self.config_path = Path(config_path)
        self._settings: Optional[Settings] = None

    def load(self) -> Settings:
        """Load settings from file or create defaults.

        Returns:
            Settings object
        """
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, creating defaults")
            settings = self._create_default()
            self.save(settings)
            return settings

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = Settings(**data)
            self._settings = settings
            logger.info(f"Loaded settings from {self.config_path}")
            return settings
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            logger.info("Falling back to default settings")
            return self._create_default()

    def save(self, settings: Settings) -> bool:
        """Save settings to file.

        Args:
            settings: Settings object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_path = self.config_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.config_path)
            self._settings = settings
            logger.info(f"Saved settings to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config to {self.config_path}: {e}")
            return False

    def _create_default(self) -> Settings:
        """Create default settings.

        Returns:
            Default Settings object
        """
        return Settings(**DEFAULT_SETTINGS)

    def get_data_dir(self) -> Path:
        """Get the main data directory.

        Returns:
            Path to data directory
        """
        return self.config_path.parent

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        data_dir = self.get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)

        # Load settings to get configured paths
        if self._settings is None:
            self._settings = self.load()

        # Create database directory
        db_path = Path(self._settings.storage.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup directory
        backup_dir = Path(self._settings.storage.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Ensured all required directories exist")

    def reset_to_defaults(self) -> Settings:
        """Reset settings to defaults.

        Returns:
            Default Settings object
        """
        settings = self._create_default()
        self.save(settings)
        logger.info("Reset settings to defaults")
        return settings

    @property
    def settings(self) -> Settings:
        """Get current settings (lazy load).

        Returns:
            Current Settings object
        """
        if self._settings is None:
            self._settings = self.load()
        return self._settings


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Path] = None) -> ConfigManager:
    """Get global config manager instance.

    Args:
        config_path: Optional custom config path

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_settings() -> Settings:
    """Get current settings.

    Returns:
        Current Settings object
    """
    return get_config_manager().settings
