"""
notify_email step — sends a run summary via SMTP.

Credentials read from environment variables named in notify.email config.
NOTE: Does nothing unless explicitly in the workflow list.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.notify_email")


@register_step("notify_email")
class NotifyEmailStep(BaseStep):
    name = "notify_email"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        cfg = ctx.config.notify.email
        if cfg is None:
            logger.warning("notify_email: no email config — skipping")
            return {"skipped": True, "reason": "no_config"}

        username = os.environ.get(cfg.username_env, "")
        password = os.environ.get(cfg.password_env, "")

        body = self._build_body(ctx)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"{cfg.subject} [{ctx.config.name}]"
        msg["From"] = cfg.from_addr
        msg["To"] = ", ".join(cfg.to_addrs)

        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
            server.ehlo()
            server.starttls()
            if username:
                server.login(username, password)
            server.sendmail(cfg.from_addr, cfg.to_addrs, msg.as_string())

        logger.info("notify_email: sent to %s", cfg.to_addrs)
        return {"recipients": cfg.to_addrs}

    def _build_body(self, ctx: RunContext) -> str:
        compare = ctx.meta.get("compare", {})
        counts = compare.get("counts", {})
        lines = [
            f"ScraperKit run: {ctx.config.name}",
            f"Run ID: {ctx.run_id}",
            f"Started: {ctx.started_at.isoformat()}",
            f"Items collected: {len(ctx.items)}",
        ]
        if counts:
            lines += [
                f"New: {counts.get('new', 0)}",
                f"Removed: {counts.get('removed', 0)}",
                f"Changed: {counts.get('changed', 0)}",
            ]
        failed = [r for r in ctx.step_results if r.status == "error"]
        if failed:
            lines.append(f"FAILED steps: {', '.join(r.step for r in failed)}")
        return "\n".join(lines)
