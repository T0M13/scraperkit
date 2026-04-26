"""RunContext holds all shared state for a single workflow execution."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ProjectConfig


@dataclass
class StepResult:
    step: str
    status: str        # "success" | "error" | "skipped"
    duration_s: float
    items_in: int = 0
    items_out: int = 0
    output_files: list[str] = field(default_factory=list)
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext:
    """Shared mutable state passed through every workflow step."""
    config: ProjectConfig
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Items flow between steps via this list
    items: list[dict[str, Any]] = field(default_factory=list)

    # Accumulated step results (used for logging + API)
    step_results: list[StepResult] = field(default_factory=list)

    # Output directory resolved at runtime
    output_dir: Path = field(default=Path("output"))

    # Arbitrary metadata any step can write and any subsequent step can read
    meta: dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: StepResult) -> None:
        self.step_results.append(result)

    def last_result(self, step: str) -> StepResult | None:
        for r in reversed(self.step_results):
            if r.step == step:
                return r
        return None

    @property
    def run_ts(self) -> str:
        """Timestamp string for file naming: DDMMYYYY_HHMM."""
        return self.started_at.strftime("%d%m%Y_%H%M")
