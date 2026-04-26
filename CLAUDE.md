# ScraperKit — Claude Code Context

**Full project context:** see [`ai/CONTEXT.md`](ai/CONTEXT.md)

## Quick orientation

- Config-driven Scrapy platform. Users write YAML, not spiders.
- Workflow steps registered via `@register_step("name")` in `scraperkit/steps/`.
- FastAPI dashboard at `scraperkit/api/app.py` + single-file SPA `api/static/index.html`.
- SQLite run history via `scraperkit/logging/db.py` (`RunStore`).
- CLI entry: `scraperkit/cli.py` (Typer).

## Critical rules

1. **Never commit** `output/`, `scraperkit.db`, `configs/*.yaml`, `.env*`, `*_creds.json`.
2. **Credentials via env vars only** — not in code, not in YAML.
3. **Paths to frontend** → always `Path.as_posix()`. Windows backslashes break JS.
4. **`run_id` must be consistent** — JobManager passes `--run-id` to subprocess so DB and SSE use the same ID.
5. **Dashboard is one HTML file** — no build step, keep it that way.
6. When adding a step: create file in `scraperkit/steps/`, decorate with `@register_step`, import in `scraperkit/steps/__init__.py`.

## Running

```bash
pip install -e ".[all]"
scraperkit run examples/simple_products.yaml   # test crawl
scraperkit serve                                # dashboard at :8000
pytest                                          # tests
```
