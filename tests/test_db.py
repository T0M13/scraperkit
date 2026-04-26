"""Tests for the SQLite RunStore."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scraperkit.logging.db import RunStore


@pytest.fixture
def store(tmp_path: Path) -> RunStore:
    return RunStore(tmp_path / "test.db")


def test_start_and_finish_run(store):
    now = datetime.now(timezone.utc)
    store.start_run("abc123", "my_project", now)
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "abc123"
    assert runs[0]["status"] == "running"

    store.finish_run("abc123", "success", item_count=42)
    run = store.get_run("abc123")
    assert run["status"] == "success"
    assert run["item_count"] == 42
    assert run["duration_s"] is not None


def test_save_step(store):
    now = datetime.now(timezone.utc)
    store.start_run("run1", "proj", now)
    store.save_step("run1", "crawl", "success", 1.23, 0, 10, ["out.json"], None, {})
    run = store.get_run("run1")
    assert len(run["steps"]) == 1
    assert run["steps"][0]["step"] == "crawl"
    assert run["steps"][0]["items_out"] == 10


def test_list_runs_filter_by_project(store):
    now = datetime.now(timezone.utc)
    store.start_run("r1", "proj_a", now)
    store.start_run("r2", "proj_b", now)
    runs = store.list_runs(project="proj_a")
    assert len(runs) == 1
    assert runs[0]["project"] == "proj_a"


def test_get_latest_run(store):
    now = datetime.now(timezone.utc)
    store.start_run("old", "proj", now)
    store.start_run("new", "proj", now)
    latest = store.get_latest_run("proj")
    assert latest["run_id"] == "new"


def test_project_stats(store):
    now = datetime.now(timezone.utc)
    store.start_run("r1", "proj", now)
    store.finish_run("r1", "success", 50)
    store.start_run("r2", "proj", now)
    store.finish_run("r2", "failed", 0)
    stats = store.project_stats("proj")
    assert stats["total_runs"] == 2
    assert stats["success_count"] == 1
    assert stats["failed_count"] == 1
