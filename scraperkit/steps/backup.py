"""
backup step — copies all output files from this run into a timestamped archive folder.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.backup")


@register_step("backup")
class BackupStep(BaseStep):
    name = "backup"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        backup_cfg = ctx.config.output.backup
        backup_root = Path(backup_cfg.get("directory", str(ctx.output_dir / "backup")))
        run_archive = backup_root / f"{ctx.run_ts}_{ctx.run_id}"
        run_archive.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for result in ctx.step_results:
            for file_path in result.output_files:
                src = Path(file_path)
                if src.exists():
                    dest = run_archive / src.name
                    shutil.copy2(src, dest)
                    copied.append(str(dest))

        logger.info("backup: archived %d files to %s", len(copied), run_archive)
        return {"output_files": copied, "archive_dir": str(run_archive)}
