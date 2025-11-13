"""Logging configuration for GemBrain."""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(data_dir: Path, debug: bool = False) -> None:
    """Configure logging for the application.

    Args:
        data_dir: Data directory for log files
        debug: Enable debug logging
    """
    # Remove default logger
    logger.remove()

    # Console logging
    log_level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # File logging
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Main log file (rotated)
    logger.add(
        log_dir / "gembrain.log",
        rotation="10 MB",
        retention="1 week",
        compression="zip",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )

    # Error log file
    logger.add(
        log_dir / "error.log",
        rotation="10 MB",
        retention="2 weeks",
        compression="zip",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}\n{exception}",
    )

    logger.info(f"Logging initialized (debug={debug})")
