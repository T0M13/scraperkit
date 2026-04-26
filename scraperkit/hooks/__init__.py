"""
Hooks system — fires shell commands or Python callables on workflow lifecycle events.

Hook commands are configured in the project YAML under the `hooks:` key.
Each event maps to a list of shell command strings that are executed in order.

Available events:
  on_start, on_step_success, on_step_error, on_crawl_finished,
  on_new_items_found, on_workflow_failed, on_workflow_success
"""
from .dispatcher import HookDispatcher

__all__ = ["HookDispatcher"]
