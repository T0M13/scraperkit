# ⚡ ScraperKit

**Config-driven web scraping and automation — define what to crawl, extract, and do after, all in one YAML file.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built on Scrapy](https://img.shields.io/badge/built%20on-Scrapy-brightgreen.svg)](https://scrapy.org/)

No custom spiders. No boilerplate. Write a config, run a command.

```yaml
name: books

start_urls:
  - https://books.toscrape.com/catalogue/page-1.html

crawler:
  item_selector: "article.product_pod"
  fields:
    title: "h3 a::attr(title)"
    price: "p.price_color::text"
  pagination:
    type: css
    selector: "li.next a::attr(href)"

workflow:
  - crawl
  - clean
  - deduplicate
  - export_json
  - export_excel
  - compare_previous
```

```bash
scraperkit run books.yaml
# → output/books/json/26042025_1430_items.json
# → output/books/excel/26042025_1430_items.xlsx
```

---

## Features

- **One generic spider** — CSS, XPath, regex, and JSON path extraction with no code
- **JSON API mode** — point it at a REST API and it pages through automatically
- **Workflow steps** — reorder, skip, or chain steps in config
- **Change detection** — diff current crawl against previous run, with fuzzy matching
- **Export** — JSON and Excel out of the box
- **Notifications** — Slack, email, SharePoint (credentials via env vars only)
- **Hooks** — trigger steps or shell commands on lifecycle events
- **Web dashboard** — browser UI to start crawls, monitor live logs, browse output files
- **CLI** — `run`, `serve`, `runs`, `show`
- **Extensible** — register custom steps and extractors with a single decorator
- **Cross-platform** — Windows, macOS, Linux

---

## Installation

```bash
pip install scraperkit

# Optional extras:
pip install "scraperkit[fuzzy]"   # fuzzy change detection (fuzzywuzzy)
pip install "scraperkit[slack]"   # Slack notifications
pip install "scraperkit[all]"     # everything
```

From source:

```bash
git clone https://github.com/herceg133/scraperkit
cd scraperkit
pip install -e ".[all]"
```

---

## Quick Start

```bash
# Run an example
scraperkit run examples/simple_products.yaml

# Start the dashboard at http://localhost:8000
scraperkit serve

# List recent runs
scraperkit runs

# Step-by-step detail for a specific run
scraperkit show <run_id>
```

---

## Config Reference

### Top-level

| Key | Type | Description |
|-----|------|-------------|
| `name` | string | Project name — used for output folder |
| `start_urls` | list | One or more URLs to start from |
| `crawler` | object | Spider and extraction settings |
| `workflow` | list | Ordered steps to run (default: `[crawl, export_json]`) |
| `hooks` | object | Lifecycle event handlers |
| `output` | object | Output directory settings |
| `notify` | object | Slack / email / SharePoint |
| `compare` | object | Change detection settings |
| `extra` | object | Free-form data for custom steps |

### HTML crawling

```yaml
crawler:
  item_selector: ".product-card"

  fields:
    title:  ".title::text"              # CSS (default)
    link:   "a::attr(href)"
    name:   "xpath=//h1/text()"         # XPath prefix
    sku:    "regex=SKU-(\d+)"           # Regex prefix — returns group 1
    price:                              # Full form
      type: css
      selector: ".price::text"
      transform: strip                  # strip | lower | upper | int | float
      default: "N/A"

  pagination:
    type: css                           # css | xpath | url_increment
    selector: "a.next::attr(href)"

  delay_min: 2.0
  delay_max: 5.0
  autothrottle: true
  rotate_useragent: true
  respect_robots: true
```

### JSON API crawling

```yaml
crawler:
  response_type: json
  json_items_path: "data.results"       # dot-path to items array
  json_total_pages_path: "total_pages"  # optional — stops pagination early

  fields:                               # omit to pass through all API fields
    id:   "id"
    name: "name"
    city: "address.city"               # nested dot-path

  pagination:
    type: url_increment
    param: page                        # query param to increment
  
  respect_robots: false
```

### Workflow steps

| Step | Description |
|------|-------------|
| `crawl` | Run the Scrapy spider |
| `clean` | Strip whitespace, remove all-empty items |
| `deduplicate` | Remove duplicates by `compare.key_field` |
| `export_json` | Write timestamped JSON file |
| `export_excel` | Write timestamped Excel file |
| `compare_previous` | Diff against last run — new / removed / changed |
| `backup` | Archive output files to timestamped folder |
| `notify_slack` | Post summary to Slack |
| `notify_email` | Send summary email via SMTP |
| `upload_sharepoint` | Upload files to SharePoint via Microsoft Graph |

### Change detection

```yaml
compare:
  key_field: id             # unique field per item
  fuzzy_fields:             # fields to fuzzy-match for renamed items
    - name
    - address
  fuzzy_threshold: 97       # fuzzywuzzy token_set_ratio (0-100)
```

Results saved to `output/<project>/compare/<ts>_comparison.json`:

```json
{
  "new":     [...],
  "removed": [...],
  "changed": [...],
  "counts":  { "new": 3, "removed": 1, "changed": 5 }
}
```

### Hooks

```yaml
hooks:
  on_start:            []
  on_step_success:     []
  on_step_error:       []
  on_crawl_finished:   []
  on_new_items_found:  []
  on_workflow_failed:
    - notify_slack              # run a registered step
    - shell:echo "failed!"      # shell command
  on_workflow_success:
    - upload_sharepoint
```

### Notifications

All credentials are read from **environment variables** — never put secrets in the config file.

```yaml
notify:
  slack:
    token_env: SLACK_TOKEN
    channel: "#alerts"

  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_addr: me@example.com
    to_addrs: [you@example.com]
    username_env: SMTP_USER
    password_env: SMTP_PASS

  sharepoint:
    tenant_id_env:     SP_TENANT_ID
    client_id_env:     SP_CLIENT_ID
    client_secret_env: SP_CLIENT_SECRET
    site_url: "https://tenant.sharepoint.com/sites/MySite"
    drive_id: "YOUR_DRIVE_ID"
    remote_folder: "General/reports"
    keep_only_latest: false
```

---

## Web Dashboard

```bash
scraperkit serve              # http://localhost:8000
scraperkit serve --host 0.0.0.0 --port 9000
```

The dashboard lets you:
- Browse all projects and run history
- Start a crawl from a saved config or paste YAML inline
- Stream live logs from running jobs
- Inspect step-by-step results and timing
- Browse, preview, and download output files (JSON table view, Excel with sheet tabs)
- Manage saved configs in the browser editor

---

## Writing a Custom Step

```python
from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

@register_step("enrich")
class EnrichStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        # ctx.items  — current items (modify in-place)
        # ctx.config — full ProjectConfig
        # ctx.meta   — shared dict between steps
        # ctx.output_dir — pathlib.Path to output folder

        for item in ctx.items:
            item["source"] = ctx.config.name

        return {"enriched": len(ctx.items)}
```

Register it before running and use it in your YAML:

```yaml
workflow:
  - crawl
  - enrich
  - export_json
```

---

## Project Structure

```
scraperkit/
├── core/
│   ├── config.py        # Pydantic config models + YAML/JSON loader
│   ├── context.py       # RunContext — shared state for a workflow run
│   ├── base.py          # BaseStep, BaseExtractor abstract classes
│   ├── registry.py      # WORKFLOW_STEPS dict + @register_step decorator
│   └── runner.py        # WorkflowRunner — executes steps, fires hooks
├── spider/
│   ├── middlewares.py   # User-agent rotation, anti-detection headers
│   └── scrapyproject/
│       └── spiders/
│           └── generic_spider.py  # One spider for HTML + JSON APIs
├── extractors/          # CSS, XPath, Regex, JSON extractors
├── steps/               # All built-in workflow steps
├── hooks/               # HookDispatcher
├── logging/
│   ├── setup.py         # Console + file logging
│   └── db.py            # SQLite run history (RunStore)
├── api/
│   ├── app.py           # FastAPI application + SSE log streaming
│   ├── jobs.py          # Job manager (subprocess + live log buffer)
│   ├── configs.py       # Config CRUD
│   └── static/
│       └── index.html   # Single-file dashboard SPA
└── cli.py               # Typer CLI entry point
```

---

## Contributing

Pull requests are welcome. For large changes, open an issue first.

```bash
git clone https://github.com/herceg133/scraperkit
cd scraperkit
pip install -e ".[all,dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).
