"""Base classes for workflow steps and extractors."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from .context import RunContext, StepResult


class BaseStep(ABC):
    """All workflow steps inherit from this. Wraps execute() with timing + error capture."""

    name: str = "unnamed_step"

    def run(self, ctx: RunContext) -> StepResult:
        start = time.perf_counter()
        items_in = len(ctx.items)
        try:
            meta = self.execute(ctx) or {}
            duration = time.perf_counter() - start
            result = StepResult(
                step=self.name,
                status="success",
                duration_s=round(duration, 3),
                items_in=items_in,
                items_out=len(ctx.items),
                output_files=meta.pop("output_files", []),
                meta=meta,
            )
        except Exception as exc:
            duration = time.perf_counter() - start
            result = StepResult(
                step=self.name,
                status="error",
                duration_s=round(duration, 3),
                items_in=items_in,
                items_out=len(ctx.items),
                error=str(exc),
            )
        ctx.add_result(result)
        return result

    @abstractmethod
    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        """Implement step logic here. Modify ctx.items in-place. Return optional meta dict."""


class BaseExtractor(ABC):
    """All field extractors inherit from this."""

    @abstractmethod
    def extract(self, response: Any, selector: str, default: Any = None) -> Any:
        """Extract a value from a response/node using the given selector."""
