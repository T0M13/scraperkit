"""
crawl step — runs the generic Scrapy spider and loads items into ctx.items.

Scrapy/Twisted can only run once per process. If the reactor is already stopped
(e.g. a second crawl in the same process), this step spawns a subprocess instead.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.crawl")


@register_step("crawl")
class CrawlStep(BaseStep):
    name = "crawl"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        items = self._run(ctx)
        ctx.items = items
        ctx.meta["crawl_count"] = len(items)

        if len(items) > 0:
            from scraperkit.hooks import HookDispatcher
            HookDispatcher(ctx.config.hooks).fire("on_new_items_found", ctx)

        return {"items_found": len(items)}

    def _run(self, ctx: RunContext) -> list[dict]:
        # Try in-process first; fall back to subprocess if reactor already ran
        try:
            from scraperkit.spider.runner import run_spider
            return run_spider(ctx.config)
        except Exception as exc:
            if "ReactorNotRestartable" in str(type(exc).__name__) or "reactor" in str(exc).lower():
                logger.info("Reactor already stopped — running spider in subprocess")
                return self._subprocess_crawl(ctx)
            raise

    def _subprocess_crawl(self, ctx: RunContext) -> list[dict]:
        """Serialize config, run spider in a child process, read back JSON results."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as cfg_file:
            cfg_path = cfg_file.name
            cfg_file.write(ctx.config.model_dump_json())

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, encoding="utf-8"
        ) as out_file:
            out_path = out_file.name

        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scraperkit._subprocess_spider",
                    cfg_path,
                    out_path,
                ],
                check=True,
                timeout=3600,
            )
            return json.loads(Path(out_path).read_text(encoding="utf-8"))
        finally:
            Path(cfg_path).unlink(missing_ok=True)
            Path(out_path).unlink(missing_ok=True)
