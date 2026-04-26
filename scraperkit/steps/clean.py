"""
clean step — strips whitespace, removes empty/null items, normalises field types.
"""
from __future__ import annotations

import logging
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.clean")

# Fields added internally by the spider — skip cleaning them
_INTERNAL_FIELDS = {"_url", "_spider", "_crawled_at"}


@register_step("clean")
class CleanStep(BaseStep):
    name = "clean"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        before = len(ctx.items)
        cleaned = []
        for item in ctx.items:
            cleaned_item = self._clean_item(item)
            if cleaned_item:
                cleaned.append(cleaned_item)
        removed = before - len(cleaned)
        logger.info("clean: %d items before, %d removed, %d remaining", before, removed, len(cleaned))
        ctx.items = cleaned
        return {"removed": removed}

    def _clean_item(self, item: dict) -> dict | None:
        result: dict[str, Any] = {}
        for key, value in item.items():
            if key in _INTERNAL_FIELDS:
                result[key] = value
                continue
            cleaned = self._clean_value(value)
            result[key] = cleaned

        # Drop items where all user-facing fields are empty
        user_fields = {k: v for k, v in result.items() if k not in _INTERNAL_FIELDS}
        if all(v is None or v == "" for v in user_fields.values()):
            return None
        return result

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        if isinstance(value, list):
            return [self._clean_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._clean_value(v) for k, v in value.items()}
        return value
