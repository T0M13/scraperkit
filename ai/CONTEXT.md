# ScraperKit — AI Assistant Context

This file is the single source of truth for AI assistants working on this codebase.
Read this before making any changes.

---

## What is ScraperKit?

A config-driven web scraping and automation platform built on Scrapy.
Users define everything in a YAML file — what to crawl, how to extract fields, and what
workflow steps to run after. No custom spider code needed.

Key qualities:
- **No boilerplate** — one generic spider handles all sites
- **Workflow steps** are composable and registered via decorator
- **Web dashboard** (FastAPI + plain HTML SPA) for monitoring, logs, file browser
- **Cross-platform** — Windows, macOS, Linux

---

## Repository layout

```
scraperkit/                     ← Python package
├── core/
│   ├── config.py               ← Pydantic v2 models for the YAML schema
│   ├── context.py              ← RunContext dataclass (shared state per run)
│   ├── base.py                 ← BaseStep and BaseExtractor abstract classes
│   ├── registry.py             ← WORKFLOW_STEPS dict + @register_step decorator
│   └── runner.py               ← WorkflowRunner — executes steps, fires hooks
├── spider/
│   ├── runner.py               ← run_spider() — launches Scrapy in-process
│   ├── middlewares.py          ← UA rotation, anti-detection headers
│   └── scrapyproject/
│       └── spiders/
│           └── generic_spider.py  ← One spider: HTML + JSON API modes
├── extractors/                 ← CSS, XPath, Regex, JSON extractors (registered)
├── steps/                      ← All built-in workflow steps (auto-registered)
│   ├── crawl.py                ← Runs Scrapy; falls back to subprocess if reactor reused
│   ├── clean.py                ← Strip whitespace, drop all-empty items
│   ├── deduplicate.py          ← Dedupe by compare.key_field
│   ├── export_json.py          ← Write timestamped JSON
│   ├── export_excel.py         ← Write timestamped Excel (openpyxl)
│   ├── compare_previous.py     ← Diff vs last run, fuzzy matching
│   ├── backup.py               ← Archive output files
│   ├── notify_slack.py         ← Slack via slack-sdk (skips if no token)
│   ├── notify_email.py         ← SMTP email
│   └── upload_sharepoint.py    ← Microsoft Graph API
├── hooks/
│   └── dispatcher.py           ← HookDispatcher — fires step/shell handlers
├── logging/
│   ├── db.py                   ← RunStore: SQLite run history (runs + run_steps tables)
│   └── setup.py                ← Console + JSON-lines file logging
├── api/
│   ├── app.py                  ← FastAPI app: all REST endpoints + SSE log streaming
│   ├── jobs.py                 ← JobManager: subprocess jobs, live log buffer, SSE
│   ├── configs.py              ← ConfigManager: CRUD for YAML files in configs/
│   └── static/
│       └── index.html          ← Single-file SPA dashboard (~1200 lines, no build step)
├── cli.py                      ← Typer CLI: run, serve, runs, show
└── _subprocess_spider.py       ← Spawned as child process when Twisted reactor reused

docs/                           ← Human-readable documentation
ai/                             ← AI assistant context files (this folder)
examples/                       ← Ready-to-run YAML example configs
configs/                        ← User's private configs (gitignored, .gitkeep only)
tests/                          ← pytest tests
```

---

## Core patterns

### Adding a workflow step

```python
from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

@register_step("my_step")
class MyStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict | None:
        # Modify ctx.items in-place
        # Return a dict; "output_files" key → saved to DB + shown in dashboard
        return {"output_files": [], "my_metric": 42}
```

Import it before running so the decorator fires. All built-in steps are imported in
`scraperkit/steps/__init__.py` which is loaded by the CLI and API on startup.

### RunContext fields

| Field | Type | Notes |
|-------|------|-------|
| `run_id` | str | 8-char hex ID — same in DB, job manager, and log buffer |
| `config` | ProjectConfig | Full parsed + validated YAML config |
| `items` | list[dict] | Flows between steps; modify in-place |
| `step_results` | list[StepResult] | Accumulated step outcomes |
| `output_dir` | Path | `output/<project_name>/` |
| `meta` | dict | Free-form between steps (e.g. `ctx.meta["compare"]`) |
| `started_at` | datetime | UTC |
| `run_ts` | property | `DDMMYYYY_HHMM` string for file naming |

### Config schema (Pydantic models in `core/config.py`)

Key models: `ProjectConfig`, `CrawlerConfig`, `OutputConfig`, `HookConfig`,
`NotifyConfig`, `CompareConfig`, `FieldExtractorConfig`.

`CrawlerConfig._normalize_fields` runs as a `model_validator(mode="before")` —
it converts shorthand field specs (`"css:.title::text"`) into full
`FieldExtractorConfig` dicts, and in `response_type: json` mode treats bare
strings as `type: json` selectors.

### Path handling

Always use `Path.as_posix()` before returning paths to the API or embedding them
in JavaScript. Windows backslashes break JS string literals inside HTML onclick attrs.

### SSE log streaming

`JobManager` stores log lines in a `deque(maxlen=2000)` per job.
SSE clients subscribe via `asyncio.Queue`. The run_id used by JobManager MUST match
the run_id in the DB (the CLI accepts `--run-id` for this purpose).

### Job cancellation (cross-platform)

`jobs.py` uses `ctypes.windll.kernel32.TerminateProcess` on win32 and
`os.kill(pid, SIGTERM)` elsewhere.

---

## Important conventions

- **Credentials always come from environment variables**, never from the YAML config.
  The notify steps check for env vars and skip silently if not set.
- **`output/` and `scraperkit.db` are gitignored** — never commit crawled data.
- **`configs/` is gitignored** (except `.gitkeep`) — user's private configs stay local.
- **No external calls are made** unless explicitly configured (Slack token set, etc.).
- All file paths returned by the API use forward slashes (`as_posix()`) for
  cross-platform JS compatibility.
- The dashboard is a single HTML file with no build step. Keep it that way.
- Python 3.10+ required (`str | None` union syntax without `from __future__` is used).

---

## Running locally

```bash
pip install -e ".[all]"

# Run a crawl
scraperkit run examples/simple_products.yaml

# Start dashboard
scraperkit serve   # http://localhost:8000

# Dry-run (validate only)
scraperkit run examples/simple_products.yaml --dry-run
```

---

## Tests

```bash
pip install -e ".[all,dev]"
pytest
```

Tests live in `tests/` — `test_config.py`, `test_steps.py`, `test_registry.py`, `test_db.py`.
