"""WorkflowRunner: resolves steps from registry, fires hooks, executes in order."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ProjectConfig
from .context import RunContext
from .registry import get_step

logger = logging.getLogger("scraperkit.runner")


class WorkflowRunner:
    def __init__(
        self,
        config: ProjectConfig,
        output_dir: str | Path | None = None,
        run_id: str | None = None,
        task: str | None = None,
    ):
        self.config = config
        self.output_dir = Path(output_dir or config.output.directory) / config.name
        self._run_id = run_id
        self._task = task

    def _resolve_workflow(self) -> list[str]:
        """Return the workflow list to execute, respecting --task and default_task."""
        if self._task:
            if self._task not in self.config.tasks:
                available = list(self.config.tasks.keys())
                raise ValueError(
                    f"Task '{self._task}' not found in config '{self.config.name}'. "
                    f"Available tasks: {available}"
                )
            return self.config.tasks[self._task].workflow
        if self.config.default_task and self.config.default_task in self.config.tasks:
            return self.config.tasks[self.config.default_task].workflow
        return self.config.workflow

    def run(self) -> RunContext:
        kwargs: dict = {"config": self.config, "output_dir": self.output_dir}
        if self._run_id:
            kwargs["run_id"] = self._run_id
        ctx = RunContext(**kwargs)
        ctx.output_dir.mkdir(parents=True, exist_ok=True)

        # Import hooks dispatcher here to avoid circular imports at module level
        from scraperkit.hooks import HookDispatcher
        hooks = HookDispatcher(self.config.hooks)

        workflow = self._resolve_workflow()
        task_label = f" [task={self._task}]" if self._task else ""
        logger.info(
            "Starting workflow '%s'%s [run_id=%s] steps=%s",
            self.config.name,
            task_label,
            ctx.run_id,
            workflow,
        )

        hooks.fire("on_start", ctx)

        failed = False
        for step_name in workflow:
            try:
                step_cls = get_step(step_name)
            except KeyError as exc:
                logger.error("Step lookup failed: %s", exc)
                failed = True
                hooks.fire("on_step_error", ctx, step=step_name, error=str(exc))
                break

            logger.info("[%s] Starting step '%s'", ctx.run_id, step_name)
            step_instance = step_cls()
            result = step_instance.run(ctx)

            if result.status == "success":
                logger.info(
                    "[%s] Step '%s' done in %.2fs — %d items out",
                    ctx.run_id, step_name, result.duration_s, result.items_out,
                )
                hooks.fire("on_step_success", ctx, result=result)
            else:
                logger.error(
                    "[%s] Step '%s' FAILED in %.2fs — %s",
                    ctx.run_id, step_name, result.duration_s, result.error,
                )
                hooks.fire("on_step_error", ctx, result=result)
                failed = True
                break

        if failed:
            hooks.fire("on_workflow_failed", ctx)
            logger.error("[%s] Workflow '%s' FAILED", ctx.run_id, self.config.name)
        else:
            hooks.fire("on_workflow_success", ctx)
            logger.info("[%s] Workflow '%s' completed successfully", ctx.run_id, self.config.name)

        self._write_run_summary(ctx)
        return ctx

    def _write_run_summary(self, ctx: RunContext) -> None:
        """Write a JSON summary of the run to the output directory."""
        import json

        finished_at = datetime.now(timezone.utc)
        total_s = (finished_at - ctx.started_at).total_seconds()

        summary: dict[str, Any] = {
            "run_id": ctx.run_id,
            "project": self.config.name,
            "task": self._task,
            "started_at": ctx.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "total_duration_s": round(total_s, 3),
            "steps": [
                {
                    "step": r.step,
                    "status": r.status,
                    "duration_s": r.duration_s,
                    "items_in": r.items_in,
                    "items_out": r.items_out,
                    "output_files": r.output_files,
                    "error": r.error,
                }
                for r in ctx.step_results
            ],
        }

        out_path = ctx.output_dir / f"{ctx.run_ts}_run_summary.json"
        out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[%s] Run summary written to %s", ctx.run_id, out_path)
