# Cursor Rules — ScraperKit

See `ai/CONTEXT.md` for the full project context.

## Key rules

- Python 3.10+. Use `str | None` union syntax (not `Optional`).
- Pydantic v2. Use `model_validator(mode="before")`, not v1 validators.
- No new dependencies without updating `pyproject.toml`.
- All new workflow steps go in `scraperkit/steps/` and must be imported in `scraperkit/steps/__init__.py`.
- File paths returned to the frontend must use `.as_posix()` (forward slashes only).
- The dashboard is one HTML file (`api/static/index.html`). No build tools, no npm.
- Never commit: `output/`, `scraperkit.db`, `configs/*.yaml`, `.env*`, `*_creds.json`.
- Credentials via env vars only — never hardcoded or in YAML files.
- `configs/` is gitignored. Drop example configs in `examples/` instead.
