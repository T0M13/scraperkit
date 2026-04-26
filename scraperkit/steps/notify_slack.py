"""
notify_slack step — posts a run summary to a Slack channel.

Reads credentials from environment variables (never from hardcoded config).
Set SLACK_TOKEN (or the env var named in notify.slack.token_env) before running.

NOTE: This step does nothing unless explicitly included in the workflow list.
      It will never fire automatically or during development.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.notify_slack")


@register_step("notify_slack")
class NotifySlackStep(BaseStep):
    name = "notify_slack"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        cfg = ctx.config.notify.slack
        if cfg is None:
            logger.warning("notify_slack: no slack config defined — skipping")
            return {"skipped": True, "reason": "no_config"}

        token = os.environ.get(cfg.token_env)
        if not token:
            logger.warning(
                "notify_slack: env var '%s' not set — skipping", cfg.token_env
            )
            return {"skipped": True, "reason": f"missing_env_{cfg.token_env}"}

        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
        except ImportError:
            raise RuntimeError("slack_sdk is required. Run: pip install slack-sdk")

        channel = cfg.channel
        text = self._build_message(ctx)

        # Slack messages have a 40 000 char limit — split if needed
        chunks = [text[i : i + 39_000] for i in range(0, len(text), 39_000)]

        client = WebClient(token=token)
        ts = None
        for i, chunk in enumerate(chunks):
            try:
                resp = client.chat_postMessage(
                    channel=channel,
                    text=chunk,
                    thread_ts=ts if i > 0 else None,
                )
                if i == 0:
                    ts = resp["ts"]
            except SlackApiError as exc:
                raise RuntimeError(f"Slack API error: {exc.response['error']}") from exc

        logger.info("notify_slack: posted %d chunk(s) to %s", len(chunks), channel)
        return {"channel": channel, "chunks": len(chunks), "ts": ts}

    def _build_message(self, ctx: RunContext) -> str:
        compare = ctx.meta.get("compare", {})
        counts = compare.get("counts", {})
        lines = [
            f"*ScraperKit run: {ctx.config.name}*",
            f"Run ID: `{ctx.run_id}` | Started: {ctx.started_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Items collected: *{len(ctx.items)}*",
        ]
        if counts:
            lines += [
                "",
                f"New: *{counts.get('new', 0)}* | "
                f"Removed: *{counts.get('removed', 0)}* | "
                f"Changed: *{counts.get('changed', 0)}*",
            ]
        failed = [r for r in ctx.step_results if r.status == "error"]
        if failed:
            lines.append(f":warning: Failed steps: {', '.join(r.step for r in failed)}")
        return "\n".join(lines)
