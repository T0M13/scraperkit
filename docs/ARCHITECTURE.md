# Architecture

## Overview

```
scraperkit/
├── core/               Config models, shared state, base classes, registry, runner
├── spider/             Generic Scrapy spider + middlewares
├── extractors/         CSS, XPath, Regex, JSON extractors
├── steps/              All built-in workflow steps
├── hooks/              Hook dispatcher
├── logging/            Structured logging + SQLite run store
├── api/                FastAPI backend + admin dashboard
└── cli.py              Typer CLI
```

---

## Data flow

```
YAML config
    │
    ▼
load_config()          ← Pydantic validation, shorthand normalization
    │
    ▼
WorkflowRunner.run()
    │
    ├── HookDispatcher.fire("on_start")
    │
    ├── for step in workflow:
    │       step_cls = WORKFLOW_STEPS[step_name]   ← registry lookup
    │       result = step_cls().run(ctx)            ← BaseStep wraps with timing
    │           │
    │           ├── step.execute(ctx)               ← modifies ctx.items in-place
    │           └── returns StepResult
    │       HookDispatcher.fire("on_step_success" | "on_step_error")
    │
    ├── HookDispatcher.fire("on_workflow_success" | "on_workflow_failed")
    │
    └── write run_summary.json + save to SQLite
```

---

## RunContext

`RunContext` is the single object passed through every step. It holds:

| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | `ProjectConfig` | Full validated project config |
| `run_id` | `str` | Short UUID for this run |
| `started_at` | `datetime` | UTC start time |
| `items` | `list[dict]` | Current items (modified in-place by steps) |
| `step_results` | `list[StepResult]` | Accumulated results from all steps |
| `output_dir` | `Path` | Resolved output directory |
| `meta` | `dict` | Free-form data shared between steps |
| `run_ts` | `str` | Timestamp string `DDMMYYYY_HHMM` for file naming |

---

## Registry

Steps and extractors are registered with decorators at import time:

```python
# Registering a step
from scraperkit.core.registry import register_step
from scraperkit.core.base import BaseStep

@register_step("my_step")
class MyStep(BaseStep):
    def execute(self, ctx):
        # Do something with ctx.items
        return {"my_key": "my_value"}  # added to StepResult.meta
```

```python
# Registering an extractor
from scraperkit.core.registry import register_extractor
from scraperkit.core.base import BaseExtractor

@register_extractor("my_type")
class MyExtractor(BaseExtractor):
    def extract(self, response, selector, default=None):
        return response.my_method(selector) or default
```

The registries are just plain dicts:
```python
from scraperkit.core.registry import WORKFLOW_STEPS, EXTRACTORS
print(list(WORKFLOW_STEPS.keys()))
# ['crawl', 'clean', 'deduplicate', 'export_json', 'export_excel',
#  'compare_previous', 'backup', 'notify_slack', 'notify_email', 'upload_sharepoint']
```

---

## Generic Spider

`GenericSpider` is one Scrapy spider that reads `ProjectConfig` at runtime:

1. `start_urls` → `parse(response)`
2. For each `item_selector` node → extract all fields
3. Each field is extracted by type: CSS / XPath / Regex / JSON
4. Apply `transform` if specified
5. Yield item (collected by `CollectItemsPipeline`)
6. Follow `pagination` if configured

The spider runs via `CrawlerProcess` inside the `crawl` step. If the Twisted reactor was already used in the same process (e.g. running two crawls sequentially), the step automatically falls back to a subprocess.

---

## Hooks dispatcher

Hooks are resolved in this order:

1. Is it a key in `WORKFLOW_STEPS`? → run that step
2. Does it start with `shell:`? → run as a shell command
3. Does it contain a dot? → import as a Python dotted path and call

Hook errors are caught and logged — they never crash the main workflow.

---

## SQLite RunStore

Every run is persisted to `scraperkit.db`:

```
runs
  run_id, project, status, started_at, finished_at, duration_s, item_count, error

run_steps
  run_id, step, status, duration_s, items_in, items_out, output_files, error, meta
```

The FastAPI backend and CLI both read from this database.

---

## Admin panel

The admin panel is a single HTML file (`api/static/index.html`) — no build step, no npm.

It communicates with the FastAPI backend via:
- `GET /api/runs` — run history
- `GET /api/projects` — project list
- `POST /api/jobs` — start a crawl
- `GET /api/jobs/{id}/logs/stream` — **Server-Sent Events** for live console output
- `DELETE /api/jobs/{id}` — cancel a running job
- `GET/POST/PUT/DELETE /api/configs` — YAML config CRUD

Live log streaming uses SSE (`text/event-stream`). The browser opens a persistent HTTP connection and receives log lines as they are written to stdout by the subprocess.

---

## Job lifecycle

```
POST /api/jobs
    │
    └── JobManager.start(config_path, project)
            │
            └── threading.Thread → subprocess: python -m scraperkit.cli run <config>
                    │
                    ├── stdout lines → job.log_lines (circular buffer, 2000 lines)
                    │                → SSE subscribers (asyncio.Queue per client)
                    │
                    └── on exit → job.status = "success" | "failed"
                                → notify all SSE subscribers with __DONE__
```

