"""
RunStore — SQLite-backed run history.

Stores every workflow run and its step results so the API and dashboard
can query past runs, durations, item counts, errors, and output files.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL UNIQUE,
    project     TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'running',
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    duration_s  REAL,
    item_count  INTEGER DEFAULT 0,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS run_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL REFERENCES runs(run_id),
    step        TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    duration_s  REAL,
    items_in    INTEGER DEFAULT 0,
    items_out   INTEGER DEFAULT 0,
    output_files TEXT,
    error       TEXT,
    meta        TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_run_steps_run_id ON run_steps(run_id);
"""


class RunStore:
    def __init__(self, db_path: str | Path = "scraperkit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_DDL)

    # ------------------------------------------------------------------ writes

    def start_run(self, run_id: str, project: str, started_at: datetime) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO runs (run_id, project, status, started_at) VALUES (?,?,?,?)",
                (run_id, project, "running", started_at.isoformat()),
            )

    def finish_run(self, run_id: str, status: str, item_count: int, error: str | None = None) -> None:
        now = datetime.now(timezone.utc)
        with self._conn() as conn:
            row = conn.execute("SELECT started_at FROM runs WHERE run_id=?", (run_id,)).fetchone()
            duration_s: float | None = None
            if row:
                started = datetime.fromisoformat(row["started_at"])
                duration_s = round((now - started).total_seconds(), 3)
            conn.execute(
                """UPDATE runs
                   SET status=?, finished_at=?, duration_s=?, item_count=?, error=?
                   WHERE run_id=?""",
                (status, now.isoformat(), duration_s, item_count, error, run_id),
            )

    def save_step(
        self,
        run_id: str,
        step: str,
        status: str,
        duration_s: float,
        items_in: int,
        items_out: int,
        output_files: list[str],
        error: str | None,
        meta: dict[str, Any],
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO run_steps
                   (run_id, step, status, duration_s, items_in, items_out, output_files, error, meta)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    run_id, step, status, duration_s, items_in, items_out,
                    json.dumps(output_files),
                    error,
                    json.dumps(meta),
                ),
            )

    # ------------------------------------------------------------------ reads

    def list_runs(self, project: str | None = None, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            if project:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE project=? ORDER BY started_at DESC LIMIT ?",
                    (project, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            steps = conn.execute(
                "SELECT * FROM run_steps WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
            result["steps"] = [dict(s) for s in steps]
        return result

    def get_latest_run(self, project: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT run_id FROM runs WHERE project=? ORDER BY started_at DESC LIMIT 1",
                (project,),
            ).fetchone()
        if not row:
            return None
        return self.get_run(row["run_id"])

    def project_stats(self, project: str) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*) as total_runs,
                       SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                       SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)  as failed_count,
                       AVG(duration_s) as avg_duration_s,
                       MAX(item_count) as max_items,
                       AVG(item_count) as avg_items
                   FROM runs WHERE project=?""",
                (project,),
            ).fetchone()
        return dict(row) if row else {}
