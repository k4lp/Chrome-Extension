"""Tests for datavault tag rendering utilities."""

from dataclasses import dataclass

import pytest

from gembrain.utils.datavault_tags import (
    parse_datavault_tags,
    render_datavault_tags,
)


@dataclass
class FakeDatavaultItem:
    id: int
    content: str
    notes: str = ""


class FakeDatavaultService:
    """Simple fake that mimics DatavaultService.get_item."""

    def __init__(self, items):
        self._items = {item.id: item for item in items}

    def get_item(self, item_id: int):
        return self._items.get(item_id)


def test_parse_tags_extracts_all_matches():
    text = "Intro [[datavault:1]] and another [[Datavault:2|Plan]]."
    tags = parse_datavault_tags(text)
    assert [(t.item_id, t.label) for t in tags] == [(1, None), (2, "Plan")]


def test_render_replaces_tags_with_content():
    service = FakeDatavaultService(
        [
            FakeDatavaultItem(1, "First content", notes="Alpha"),
        ]
    )
    result = render_datavault_tags("See [[datavault:1]].", service)
    assert "First content" in result.rendered_text
    assert "Alpha" in result.rendered_text
    assert result.items[0].item_id == 1
    assert not result.warnings


def test_render_uses_custom_label():
    service = FakeDatavaultService([FakeDatavaultItem(3, "Custom data", notes="Ignored")])
    result = render_datavault_tags(
        "Start [[datavault:3|Handbook Section]].", service
    )
    assert "Handbook Section" in result.rendered_text
    assert "Ignored" not in result.rendered_text


def test_render_marks_missing_items():
    service = FakeDatavaultService([])
    result = render_datavault_tags("Missing [[datavault:99]].", service)
    assert "[Missing datavault item 99]" in result.rendered_text
    assert "99" in result.warnings[0]


def test_render_truncates_large_content():
    service = FakeDatavaultService(
        [FakeDatavaultItem(5, "x" * 20, notes="Large chunk")]
    )
    result = render_datavault_tags(
        "Data [[datavault:5]].", service, max_chars_per_item=10
    )
    assert "… (truncated)" in result.rendered_text
    assert result.items[0].truncated
    assert any("truncated" in warning for warning in result.warnings)


def test_custom_tag_prefix_is_supported():
    service = FakeDatavaultService([FakeDatavaultItem(2, "Notes content", notes="Custom")])
    result = render_datavault_tags(
        "Here [[vault:2|Doc]]", service, tag_prefix="vault"
    )
    assert "Notes content" in result.rendered_text
    tags = parse_datavault_tags("Here [[vault:2|Doc]]", tag_prefix="vault")
    assert tags[0].item_id == 2
