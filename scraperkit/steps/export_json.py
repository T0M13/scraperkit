"""
export_json step — writes ctx.items to a timestamped JSON file.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.export_json")


@register_step("export_json")
class ExportJsonStep(BaseStep):
    name = "export_json"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        out_dir = ctx.output_dir / "json"
        out_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{ctx.run_ts}_items.json"
        out_path = out_dir / filename

        payload = {
            "run_id": ctx.run_id,
            "project": ctx.config.name,
            "crawled_at": ctx.started_at.isoformat(),
            "item_count": len(ctx.items),
            "items": ctx.items,
        }

        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.meta["json_output"] = str(out_path)
        logger.info("export_json: wrote %d items to %s", len(ctx.items), out_path)
        return {"output_files": [str(out_path)]}
