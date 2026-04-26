"""
Job manager — starts scraperkit runs as subprocesses, streams stdout/stderr
back to the browser via Server-Sent Events, and tracks live status.

Each job is a subprocess running:
    python -m scraperkit.cli run <config_path>

We capture stdout+stderr line-by-line and:
  1. Append to an in-memory circular log buffer (last 2000 lines)
  2. Broadcast to any SSE listeners for that run_id
  3. Store final status in the SQLite RunStore
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator


@dataclass
class JobInfo:
    run_id: str
    project: str
    config_path: str
    status: str = "queued"          # queued | running | success | failed | cancelled
    started_at: str = ""
    finished_at: str = ""
    pid: int | None = None
    return_code: int | None = None
    log_lines: deque = field(default_factory=lambda: deque(maxlen=2000))
    _subscribers: list = field(default_factory=list)  # asyncio.Queue per SSE client

    def push_line(self, line: str) -> None:
        self.log_lines.append(line)
        for q in list(self._subscribers):
            try:
                q.put_nowait(line)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [self._job_to_dict(j) for j in reversed(list(self._jobs.values()))]

    def get_job(self, run_id: str) -> JobInfo | None:
        return self._jobs.get(run_id)

    def start(self, config_path: str, project: str, db_path: str = "scraperkit.db") -> str:
        run_id = str(uuid.uuid4())[:8]
        job = JobInfo(
            run_id=run_id,
            project=project,
            config_path=config_path,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[run_id] = job

        thread = threading.Thread(
            target=self._run_job,
            args=(job, db_path),
            daemon=True,
            name=f"job-{run_id}",
        )
        thread.start()
        return run_id

    def cancel(self, run_id: str) -> bool:
        job = self._jobs.get(run_id)
        if not job or job.status != "running" or job.pid is None:
            return False
        try:
            import os
            import signal
            import sys
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.kernel32.TerminateProcess(
                    ctypes.windll.kernel32.OpenProcess(1, False, job.pid), 1
                )
            else:
                os.kill(job.pid, signal.SIGTERM)
            job.status = "cancelled"
            job.push_line("[scraperkit] Job cancelled.")
            return True
        except Exception:
            return False

    def _run_job(self, job: JobInfo, db_path: str) -> None:
        job.status = "running"
        cmd = [
            sys.executable, "-m", "scraperkit.cli",
            "run", job.config_path,
            "--db", db_path,
            "--log-level", "INFO",
            "--run-id", job.run_id,
        ]
        job.push_line(f"[scraperkit] Starting: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            job.pid = proc.pid
            job.push_line(f"[scraperkit] PID {proc.pid}")

            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip("\n")
                if line:
                    job.push_line(line)

            proc.wait()
            job.return_code = proc.returncode
            job.status = "success" if proc.returncode == 0 else "failed"
            job.push_line(f"[scraperkit] Finished with exit code {proc.returncode}")

        except Exception as exc:
            job.status = "failed"
            job.push_line(f"[scraperkit] ERROR: {exc}")
        finally:
            job.finished_at = datetime.now(timezone.utc).isoformat()
            # Signal all SSE subscribers that the stream is done
            for q in list(job._subscribers):
                try:
                    q.put_nowait("__DONE__")
                except asyncio.QueueFull:
                    pass

    @staticmethod
    def _job_to_dict(job: JobInfo) -> dict:
        return {
            "run_id": job.run_id,
            "project": job.project,
            "config_path": job.config_path,
            "status": job.status,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "pid": job.pid,
            "return_code": job.return_code,
            "log_lines": list(job.log_lines),
        }


# Module-level singleton — shared across all API requests
_manager: JobManager | None = None


def get_manager() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
