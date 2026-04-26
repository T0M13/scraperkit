"""
HookDispatcher — resolves hook names and fires them with RunContext.

Hook names in the config map to either:
  1. A registered workflow step name (e.g. "notify_slack") — runs that step
  2. A shell command string starting with "shell:" (e.g. "shell:echo done")
  3. A Python dotted path (e.g. "mypackage.hooks.my_hook")
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger("scraperkit.hooks")


class HookDispatcher:
    def __init__(self, hook_config: Any):
        self._config = hook_config

    def fire(self, event: str, ctx: Any, **kwargs: Any) -> None:
        handlers: list[str] = getattr(self._config, event, [])
        if not handlers:
            return
        logger.debug("Firing hook '%s' (%d handlers)", event, len(handlers))
        for handler in handlers:
            try:
                self._dispatch(handler, ctx, event=event, **kwargs)
            except Exception as exc:
                logger.error("Hook '%s' raised on event '%s': %s", handler, event, exc)

    def _dispatch(self, handler: str, ctx: Any, **kwargs: Any) -> None:
        if handler.startswith("shell:"):
            self._run_shell(handler[6:].strip(), ctx)
        elif "." in handler and not handler.startswith("notify") and not handler.startswith("upload"):
            self._run_python(handler, ctx, **kwargs)
        else:
            self._run_step(handler, ctx)

    def _run_step(self, step_name: str, ctx: Any) -> None:
        from scraperkit.core.registry import WORKFLOW_STEPS
        step_cls = WORKFLOW_STEPS.get(step_name)
        if step_cls is None:
            logger.warning("Hook step '%s' not found in registry — skipping", step_name)
            return
        logger.info("Hook running step '%s'", step_name)
        step_cls().run(ctx)

    def _run_shell(self, command: str, ctx: Any) -> None:
        import os
        env = {**os.environ, "SCRAPERKIT_RUN_ID": ctx.run_id, "SCRAPERKIT_PROJECT": ctx.config.name}
        logger.info("Hook running shell: %s", command)
        result = subprocess.run(command, shell=True, env=env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("Shell hook failed (exit %d): %s", result.returncode, result.stderr)
        else:
            logger.debug("Shell hook output: %s", result.stdout)

    def _run_python(self, dotted_path: str, ctx: Any, **kwargs: Any) -> None:
        import importlib
        parts = dotted_path.rsplit(".", 1)
        if len(parts) != 2:
            logger.warning("Invalid Python hook path '%s' — skipping", dotted_path)
            return
        module_path, func_name = parts
        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            func(ctx, **kwargs)
        except (ImportError, AttributeError) as exc:
            logger.error("Could not load Python hook '%s': %s", dotted_path, exc)
