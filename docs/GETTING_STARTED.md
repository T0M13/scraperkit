# Getting Started

## 1. Install

```bash
cd scraperkit
pip install -e ".[all]"
```

This installs ScraperKit with all optional extras (fuzzy matching, Slack, Excel).

For a minimal install (just crawling + JSON export):
```bash
pip install -e .
```

---

## 2. Your first config

Create a file called `my_project.yaml`:

```yaml
name: my_project

start_urls:
  - https://books.toscrape.com/catalogue/page-1.html

crawler:
  item_selector: "article.product_pod"
  fields:
    title: "h3 a::attr(title)"
    price: "p.price_color::text"
    url:   "h3 a::attr(href)"
  pagination:
    type: css
    selector: "li.next a::attr(href)"

compare:
  key_field: url

workflow:
  - crawl
  - clean
  - deduplicate
  - export_json
  - export_excel
  - compare_previous
```

---

## 3. Run it

```bash
scraperkit run my_project.yaml
```

Output appears in `output/my_project/`:
```
output/
└── my_project/
    ├── json/
    │   └── 04042026_1430_items.json
    ├── excel/
    │   └── 04042026_1430_items.xlsx
    ├── compare/
    │   └── 04042026_1430_comparison.json
    └── 04042026_1430_run_summary.json
```

---

## 4. Open the admin panel

```bash
scraperkit serve
```

Open `http://localhost:8000` in your browser.

You'll see:
- **Overview** — project list, recent runs, quick "Run" buttons
- **Live Jobs** — active crawls with a live console output
- **Run History** — all past runs with step-by-step breakdown
- **Configs** — YAML editor, create/edit/delete configs
- **New Crawl** — start a crawl from a saved config or paste raw YAML

---

## 5. Dry run (validate config without crawling)

```bash
scraperkit run my_project.yaml --dry-run
```

Prints the project name, URLs, and workflow steps without executing anything.

---

## 6. CLI reference

```bash
scraperkit run <config.yaml>          # run a workflow
scraperkit run <config.yaml> --dry-run       # validate only
scraperkit run <config.yaml> -o ./myoutput   # custom output dir
scraperkit run <config.yaml> -l DEBUG        # verbose logging

scraperkit serve                      # start admin panel (port 8000)
scraperkit serve --port 9000          # custom port
scraperkit serve --host 0.0.0.0       # bind to all interfaces

scraperkit runs                       # list recent runs (table)
scraperkit runs --project my_project  # filter by project
scraperkit runs --limit 50

scraperkit show <run_id>              # step-by-step run detail
```
