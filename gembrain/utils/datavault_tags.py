"""Utilities for expanding datavault reference tags inside agent outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List, Optional, Protocol
from loguru import logger


TAG_PATTERN = re.compile(
    r"\[\[datavault:(?P<id>\d+)(?:\|(?P<label>[^\]]+))?\]\]",
    re.IGNORECASE,
)


class DatavaultServiceProtocol(Protocol):
    """Subset of DatavaultService needed for rendering."""

    def get_item(self, item_id: int):  # pragma: no cover - Protocol signature only
        ...


@dataclass
class TagReference:
    """Represents a single datavault tag discovered in text."""

    item_id: int
    label: Optional[str]
    start: int
    end: int


@dataclass
class RenderedItem:
    """Metadata about a rendered datavault item."""

    item_id: int
    heading: str
    content_length: int
    truncated: bool


@dataclass
class RenderResult:
    """Result of rendering datavault tags."""

    rendered_text: str
    items: List[RenderedItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def parse_datavault_tags(text: str) -> List[TagReference]:
    """Parse datavault tags from text."""
    tags: List[TagReference] = []
    for match in TAG_PATTERN.finditer(text or ""):
        try:
            item_id = int(match.group("id"))
        except (TypeError, ValueError):
            continue
        label = match.group("label")
        tags.append(
            TagReference(
                item_id=item_id,
                label=label.strip() if label else None,
                start=match.start(),
                end=match.end(),
            )
        )
    return tags


def render_datavault_tags(
    text: str,
    datavault_service: DatavaultServiceProtocol,
    *,
    max_chars_per_item: int = 5000,
    heading_level: int = 3,
) -> RenderResult:
    """Render datavault tags into full markdown content."""
    if not text:
        return RenderResult(rendered_text="")

    items: List[RenderedItem] = []
    warnings: List[str] = []
    heading_prefix = "#" * max(1, heading_level)

    def _replace(match: re.Match) -> str:
        raw_id = match.group("id")
        label = match.group("label")
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            warning = f"Invalid datavault tag id '{raw_id}'"
            logger.warning(warning)
            warnings.append(warning)
            return f"**[Invalid datavault tag: {raw_id}]**"

        item = None
        try:
            item = datavault_service.get_item(item_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            warning = f"Failed to load datavault item {item_id}: {exc}"
            logger.error(warning)
            warnings.append(warning)

        if not item:
            warning = f"Datavault item {item_id} not found"
            logger.warning(warning)
            warnings.append(warning)
            return f"**[Missing datavault item {item_id}]**"

        heading = (
            (label or "").strip()
            or (item.notes.strip() if getattr(item, "notes", "").strip() else "")
            or f"Datavault Item {item_id}"
        )

        content = getattr(item, "content", "") or ""
        truncated = False
        if max_chars_per_item and len(content) > max_chars_per_item:
            content = content[:max_chars_per_item].rstrip() + "\n\n… (truncated)"
            truncated = True
            warning = (
                f"Datavault item {item_id} truncated to {max_chars_per_item} chars"
            )
            warnings.append(warning)
            logger.info(warning)

        block = (
            f"\n{heading_prefix} {heading} (Datavault #{item_id})\n\n"
            f"{content}\n\n---\n"
        )

        items.append(
            RenderedItem(
                item_id=item_id,
                heading=heading,
                content_length=len(content),
                truncated=truncated,
            )
        )
        return block

    rendered = TAG_PATTERN.sub(_replace, text)
    return RenderResult(rendered_text=rendered, items=items, warnings=warnings)

