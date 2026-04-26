"""
export_excel step — writes ctx.items to a timestamped .xlsx file.
"""
from __future__ import annotations

import logging
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.export_excel")


@register_step("export_excel")
class ExportExcelStep(BaseStep):
    name = "export_excel"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        try:
            import openpyxl
        except ImportError:
            raise RuntimeError("openpyxl is required for export_excel. Run: pip install openpyxl")

        if not ctx.items:
            logger.warning("export_excel: no items to write")
            return {}

        out_dir = ctx.output_dir / "excel"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{ctx.run_ts}_items.xlsx"
        out_path = out_dir / filename

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Items"

        # Header row: collect all keys from all items (preserves insertion order)
        all_keys: list[str] = []
        seen: set[str] = set()
        for item in ctx.items:
            for key in item:
                if key not in seen:
                    all_keys.append(key)
                    seen.add(key)

        ws.append(all_keys)

        for item in ctx.items:
            row = [item.get(k) for k in all_keys]
            ws.append(row)

        # Meta sheet: run summary
        meta_ws = wb.create_sheet("Run Info")
        meta_ws.append(["Field", "Value"])
        meta_ws.append(["run_id", ctx.run_id])
        meta_ws.append(["project", ctx.config.name])
        meta_ws.append(["crawled_at", ctx.started_at.isoformat()])
        meta_ws.append(["item_count", len(ctx.items)])

        wb.save(str(out_path))
        ctx.meta["excel_output"] = str(out_path)
        logger.info("export_excel: wrote %d items to %s", len(ctx.items), out_path)
        return {"output_files": [str(out_path)]}
