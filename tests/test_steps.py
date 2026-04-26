"""Tests for workflow steps — no network calls, no file I/O side effects."""
import pytest
from pathlib import Path

from scraperkit.core.config import ProjectConfig
from scraperkit.core.context import RunContext
from scraperkit.steps.clean import CleanStep
from scraperkit.steps.deduplicate import DeduplicateStep
from scraperkit.steps.export_json import ExportJsonStep


def make_ctx(tmp_path: Path, items=None) -> RunContext:
    config = ProjectConfig(name="test", start_urls=["https://example.com"])
    ctx = RunContext(config=config, output_dir=tmp_path)
    ctx.items = items or []
    return ctx


def test_clean_strips_whitespace(tmp_path):
    ctx = make_ctx(tmp_path, [{"title": "  Hello  ", "price": " 9.99 "}])
    result = CleanStep().run(ctx)
    assert result.status == "success"
    assert ctx.items[0]["title"] == "Hello"
    assert ctx.items[0]["price"] == "9.99"


def test_clean_removes_all_empty_item(tmp_path):
    ctx = make_ctx(tmp_path, [{"title": "  ", "price": None}])
    CleanStep().run(ctx)
    assert ctx.items == []


def test_deduplicate_by_key(tmp_path):
    items = [
        {"id": "1", "name": "A"},
        {"id": "2", "name": "B"},
        {"id": "1", "name": "A duplicate"},
    ]
    ctx = make_ctx(tmp_path, items)
    ctx.config.compare.key_field = "id"
    DeduplicateStep().run(ctx)
    assert len(ctx.items) == 2
    assert ctx.meta["dupes_removed"] == 1


def test_deduplicate_keeps_items_without_key(tmp_path):
    items = [{"name": "A"}, {"name": "B"}]
    ctx = make_ctx(tmp_path, items)
    ctx.config.compare.key_field = "id"
    DeduplicateStep().run(ctx)
    assert len(ctx.items) == 2


def test_export_json_writes_file(tmp_path):
    import json
    ctx = make_ctx(tmp_path, [{"id": "1", "name": "Test"}])
    ExportJsonStep().run(ctx)
    json_dir = tmp_path / "json"
    files = list(json_dir.glob("*_items.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["item_count"] == 1
    assert data["items"][0]["name"] == "Test"


def test_step_error_captured(tmp_path):
    from scraperkit.core.base import BaseStep

    class BrokenStep(BaseStep):
        name = "broken"
        def execute(self, ctx):
            raise ValueError("intentional error")

    ctx = make_ctx(tmp_path)
    result = BrokenStep().run(ctx)
    assert result.status == "error"
    assert "intentional error" in result.error
