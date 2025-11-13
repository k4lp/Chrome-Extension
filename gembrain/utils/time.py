"""Time and date utilities."""

from datetime import datetime, timedelta
from typing import Optional


def now() -> datetime:
    """Get current datetime.

    Returns:
        Current datetime
    """
    return datetime.now()


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string.

    Args:
        dt: Datetime to format
        format_str: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime from string.

    Args:
        dt_str: Datetime string
        format_str: Format string

    Returns:
        Parsed datetime
    """
    return datetime.strptime(dt_str, format_str)


def days_ago(days: int) -> datetime:
    """Get datetime N days ago.

    Args:
        days: Number of days ago

    Returns:
        Datetime N days ago
    """
    return now() - timedelta(days=days)


def is_older_than(dt: datetime, days: int) -> bool:
    """Check if datetime is older than N days.

    Args:
        dt: Datetime to check
        days: Number of days

    Returns:
        True if older than N days
    """
    return dt < days_ago(days)


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago').

    Args:
        dt: Datetime to format

    Returns:
        Relative time string
    """
    diff = now() - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
