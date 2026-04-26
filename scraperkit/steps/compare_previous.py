"""
compare_previous step — detects new, removed, and changed items vs the last run.

Uses CompareConfig from project config:
  - key_field: unique identifier per item
  - fuzzy_fields: fields to fuzzy-match when key_field doesn't match exactly
  - fuzzy_threshold: token_set_ratio threshold (default 97)
  - track_file: explicit path to previous JSON file (auto-detected if omitted)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.compare_previous")


@register_step("compare_previous")
class ComparePreviousStep(BaseStep):
    name = "compare_previous"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        cfg = ctx.config.compare
        previous = self._load_previous(ctx)

        if previous is None:
            logger.info("compare_previous: no previous run found — skipping comparison")
            ctx.meta["compare"] = {"status": "no_previous_data"}
            return {"status": "no_previous_data"}

        current_by_key = {item[cfg.key_field]: item for item in ctx.items if cfg.key_field in item}
        previous_by_key = {item[cfg.key_field]: item for item in previous if cfg.key_field in item}

        new_keys = set(current_by_key) - set(previous_by_key)
        removed_keys = set(previous_by_key) - set(current_by_key)
        shared_keys = set(current_by_key) & set(previous_by_key)

        changed = []
        for key in shared_keys:
            curr = current_by_key[key]
            prev = previous_by_key[key]
            diffs = {
                field: {"before": prev.get(field), "after": curr.get(field)}
                for field in set(curr) | set(prev)
                if curr.get(field) != prev.get(field) and not field.startswith("_")
            }
            if diffs:
                changed.append({"key": key, "changes": diffs})

        # Fuzzy matching for items without a key match
        fuzzy_matches = []
        if cfg.fuzzy_fields:
            fuzzy_matches = self._fuzzy_match(
                [current_by_key[k] for k in new_keys],
                [previous_by_key[k] for k in removed_keys],
                cfg.fuzzy_fields,
                cfg.fuzzy_threshold,
            )

        comparison = {
            "new": [current_by_key[k] for k in new_keys],
            "removed": [previous_by_key[k] for k in removed_keys],
            "changed": changed,
            "fuzzy_matches": fuzzy_matches,
            "counts": {
                "current": len(current_by_key),
                "previous": len(previous_by_key),
                "new": len(new_keys),
                "removed": len(removed_keys),
                "changed": len(changed),
            },
        }

        ctx.meta["compare"] = comparison
        self._write_comparison_file(ctx, comparison)

        logger.info(
            "compare_previous: %d new, %d removed, %d changed",
            len(new_keys), len(removed_keys), len(changed),
        )
        return comparison["counts"]

    def _load_previous(self, ctx: RunContext) -> list[dict] | None:
        cfg = ctx.config.compare
        if cfg.track_file:
            p = Path(cfg.track_file)
            if p.exists():
                return self._read_json_items(p)
            return None

        json_dir = ctx.output_dir / "json"
        if not json_dir.exists():
            return None

        files = sorted(json_dir.glob("*_items.json"))
        # Exclude the file that was just written in this run
        current_ts = ctx.run_ts
        candidates = [f for f in files if current_ts not in f.name]
        if not candidates:
            return None
        return self._read_json_items(candidates[-1])

    @staticmethod
    def _read_json_items(path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("items", data) if isinstance(data, dict) else data

    @staticmethod
    def _fuzzy_match(
        new_items: list[dict],
        removed_items: list[dict],
        fuzzy_fields: list[str],
        threshold: int,
    ) -> list[dict]:
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            logger.warning("fuzzywuzzy not installed — skipping fuzzy matching")
            return []

        def score(a: dict, b: dict) -> int:
            scores = [
                fuzz.token_set_ratio(str(a.get(f, "")), str(b.get(f, "")))
                for f in fuzzy_fields
            ]
            return max(scores) if scores else 0

        matches = []
        for new_item in new_items:
            for rem_item in removed_items:
                s = score(new_item, rem_item)
                if s >= threshold:
                    matches.append({"new": new_item, "previous": rem_item, "score": s})
        return matches

    def _write_comparison_file(self, ctx: RunContext, comparison: dict) -> None:
        out_dir = ctx.output_dir / "compare"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{ctx.run_ts}_comparison.json"
        out_path.write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("compare_previous: comparison written to %s", out_path)
