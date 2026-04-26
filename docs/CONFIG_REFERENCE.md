# Config Reference

Every ScraperKit project is defined by a single YAML (or JSON) file.

---

## Full example

```yaml
name: my_project                     # required — used for output folder naming

start_urls:
  - https://example.com/listings
  - https://example.com/listings?page=2

crawler:
  item_selector: ".listing-card"    # CSS selector: one match = one item
  fields:
    title:   ".card-title::text"    # shorthand CSS
    price:   ".price::text"
    address: "xpath=//span[@class='addr']/text()"   # XPath shorthand
    id:      "regex=data-id=\"(\\d+)\""              # Regex shorthand
    data:                           # full form
      type: json
      selector: "meta.price"        # dot-path into JSON response
      default: null
      transform: float              # strip | lower | upper | int | float
  pagination:
    type: css                       # css | xpath | url_increment
    selector: "a.next-page::attr(href)"
    # url_increment example:
    # type: url_increment
    # param: page
    # max_pages: 10
  delay_min: 2.0                    # seconds between requests
  delay_max: 5.0
  autothrottle: true                # Scrapy adaptive throttling
  rotate_useragent: true            # random User-Agent on every request
  respect_robots: true              # obey robots.txt
  settings:                         # raw Scrapy settings override
    CONCURRENT_REQUESTS: 2
    DOWNLOAD_TIMEOUT: 30

compare:
  key_field: id                     # unique field that identifies an item
  fuzzy_fields:                     # fields to fuzzy-match when key doesn't match
    - title
    - address
  fuzzy_threshold: 97               # fuzzywuzzy token_set_ratio (0-100)
  track_file: null                  # explicit path to previous data (auto-detected if null)

workflow:
  - crawl
  - clean
  - deduplicate
  - export_json
  - export_excel
  - compare_previous
  - backup
  # - notify_slack        (uncomment + set env var SLACK_TOKEN)
  # - notify_email
  # - upload_sharepoint

hooks:
  on_start:           []
  on_step_success:    []
  on_step_error:      []
  on_crawl_finished:  []
  on_new_items_found: []
  on_workflow_failed:
    - notify_slack
    - shell: echo "workflow failed for ${SCRAPERKIT_PROJECT}"
  on_workflow_success:
    - upload_sharepoint

output:
  directory: output                 # root output folder
  backup:
    directory: output/backup        # backup archive location

notify:
  slack:
    token_env: SLACK_TOKEN          # name of env var holding the token
    channel: "#my-channel"
    test_channel: "#my-dev-channel"
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_addr: me@example.com
    to_addrs:
      - team@example.com
    subject: "ScraperKit run complete"
    username_env: SMTP_USER
    password_env: SMTP_PASS
  sharepoint:
    tenant_id_env:     SP_TENANT_ID
    client_id_env:     SP_CLIENT_ID
    client_secret_env: SP_CLIENT_SECRET
    site_url: "https://mytenant.sharepoint.com/sites/MySite"
    drive_id: "YOUR_DRIVE_ID"
    remote_folder: "General/reports"
    keep_only_latest: false

extra:                              # free-form data for custom steps
  my_custom_param: hello
```

---

## Crawler fields

### Shorthand field format

| Syntax | Type | Example |
|--------|------|---------|
| `.selector::text` | CSS | `.title::text` |
| `xpath=...` | XPath | `xpath=//h1/text()` |
| `regex=...` | Regex | `regex=price\s*:\s*(\d+)` |
| `json=...` | JSON path | `json=data.price` |

### Full field format

```yaml
fields:
  my_field:
    type: css | xpath | regex | json
    selector: "..."
    default: null          # returned when nothing matches
    transform: strip       # strip | lower | upper | int | float
```

### Transforms

| Value | Effect |
|-------|--------|
| `strip` | `"  hello  "` → `"hello"` |
| `lower` | `"HELLO"` → `"hello"` |
| `upper` | `"hello"` → `"HELLO"` |
| `int` | `"1,234"` → `1234` |
| `float` | `"9.99"` → `9.99` |

---

## Pagination

### CSS / XPath (follow a "next page" link)
```yaml
pagination:
  type: css
  selector: "a.next::attr(href)"
```

### URL increment (bump `?page=N`)
```yaml
pagination:
  type: url_increment
  param: page
  max_pages: 20
```

---

## Workflow steps

| Step | Description |
|------|-------------|
| `crawl` | Run the Scrapy spider, load items into the pipeline |
| `clean` | Strip whitespace, remove items where all fields are empty |
| `deduplicate` | Remove duplicates by `compare.key_field` |
| `export_json` | Write `output/<project>/json/<ts>_items.json` |
| `export_excel` | Write `output/<project>/excel/<ts>_items.xlsx` |
| `compare_previous` | Detect new / removed / changed items vs previous run |
| `backup` | Archive all output files to `output/backup/<ts>_<run_id>/` |
| `notify_slack` | Post summary to Slack (requires `SLACK_TOKEN` env var) |
| `notify_email` | Send summary email via SMTP |
| `upload_sharepoint` | Upload files to SharePoint via Microsoft Graph |

---

## Hooks

Hooks fire on lifecycle events. Each handler can be:

| Handler format | What it does |
|----------------|-------------|
| `notify_slack` | Runs the registered workflow step |
| `upload_sharepoint` | Runs the registered workflow step |
| `shell:echo done` | Runs a shell command (env vars `SCRAPERKIT_RUN_ID`, `SCRAPERKIT_PROJECT` are set) |
| `mypackage.hooks.my_func` | Calls a Python function `my_func(ctx)` |

Available events:

| Event | When it fires |
|-------|--------------|
| `on_start` | Before any step runs |
| `on_step_success` | After each successful step |
| `on_step_error` | After a step fails |
| `on_crawl_finished` | After the crawl step completes (regardless of item count) |
| `on_new_items_found` | After crawl, if items > 0 |
| `on_workflow_failed` | If any step errors out |
| `on_workflow_success` | After all steps complete successfully |

---

## Environment variables for secrets

Never put credentials in your YAML config. Use environment variables:

```bash
export SLACK_TOKEN=xoxb-your-token
export SMTP_USER=me@example.com
export SMTP_PASS=mypassword
export SP_TENANT_ID=your-tenant-id
export SP_CLIENT_ID=your-client-id
export SP_CLIENT_SECRET=your-secret
```

Or create a `.env` file and load it before running:
```bash
set -a && source .env && set +a
scraperkit run project.yaml
```
