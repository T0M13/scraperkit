"""
deduplicate step — removes duplicate items based on a configurable key.

Uses compare.key_field from project config. If the key field is missing on an
item, the item is kept (no false-positive deduplication).
"""
from __future__ import annotations

import logging
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.deduplicate")


@register_step("deduplicate")
class DeduplicateStep(BaseStep):
    name = "deduplicate"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        key_field = ctx.config.compare.key_field
        before = len(ctx.items)
        seen: set = set()
        unique: list[dict] = []

        for item in ctx.items:
            key = item.get(key_field)
            if key is None:
                # No key → always keep
                unique.append(item)
                continue
            if key not in seen:
                seen.add(key)
                unique.append(item)

        removed = before - len(unique)
        logger.info(
            "deduplicate: key_field='%s', %d dupes removed, %d remaining",
            key_field, removed, len(unique),
        )
        ctx.items = unique
        ctx.meta["dupes_removed"] = removed
        return {"dupes_removed": removed}
