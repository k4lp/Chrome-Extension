"""Path utilities for GemBrain."""

from pathlib import Path
from typing import Optional


def get_data_dir(custom_path: Optional[Path] = None) -> Path:
    """Get the main data directory.

    Args:
        custom_path: Optional custom data directory

    Returns:
        Path to data directory
    """
    if custom_path:
        return Path(custom_path)
    return Path.home() / ".gembrain"


def get_db_path(data_dir: Optional[Path] = None) -> Path:
    """Get the database file path.

    Args:
        data_dir: Optional data directory

    Returns:
        Path to database file
    """
    if data_dir is None:
        data_dir = get_data_dir()
    return data_dir / "gembrain.db"


def get_backup_dir(data_dir: Optional[Path] = None) -> Path:
    """Get the backup directory.

    Args:
        data_dir: Optional data directory

    Returns:
        Path to backup directory
    """
    if data_dir is None:
        data_dir = get_data_dir()
    return data_dir / "backups"


def ensure_data_directories(data_dir: Optional[Path] = None) -> None:
    """Ensure all data directories exist.

    Args:
        data_dir: Optional data directory
    """
    if data_dir is None:
        data_dir = get_data_dir()

    data_dir.mkdir(parents=True, exist_ok=True)
    get_backup_dir(data_dir).mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
