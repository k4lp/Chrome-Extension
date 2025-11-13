"""JSON utilities for GemBrain."""

import json
import re
from typing import Any, Dict, Optional


def extract_json_block(text: str, block_name: str = "actions") -> Optional[Dict[str, Any]]:
    """Extract JSON from a fenced code block in text.

    Args:
        text: Text containing fenced code block
        block_name: Name of the code block (e.g., 'actions')

    Returns:
        Parsed JSON dictionary or None if not found
    """
    # Pattern to match ```block_name ... ```
    pattern = rf"```{block_name}\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return None

    try:
        json_str = match.group(1).strip()
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def parse_actions_from_response(response: str) -> Dict[str, Any]:
    """Parse actions JSON block from agent response.

    Args:
        response: Agent response text

    Returns:
        Dictionary with 'reply' and 'actions' keys
    """
    # Extract actions block
    actions_data = extract_json_block(response, "actions")

    # Remove the actions block from the reply
    reply = re.sub(r"```actions\s*\n.*?\n```", "", response, flags=re.DOTALL).strip()

    return {
        "reply": reply,
        "actions": actions_data.get("actions", []) if actions_data else [],
    }


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def pretty_json(data: Any) -> str:
    """Format data as pretty JSON.

    Args:
        data: Data to format

    Returns:
        Pretty JSON string
    """
    return json.dumps(data, indent=2, ensure_ascii=False)
