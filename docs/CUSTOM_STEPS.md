# Writing Custom Steps

Custom steps let you add any logic to the workflow without touching ScraperKit's core.

---

## Minimal example

```python
# my_project/steps/my_step.py

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

@register_step("my_step")
class MyStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        # ctx.items  — current list of items (modify in-place)
        # ctx.config — full ProjectConfig
        # ctx.meta   — shared dict (read/write freely)
        # ctx.output_dir — pathlib.Path to output folder

        for item in ctx.items:
            item["processed"] = True

        return {"processed_count": len(ctx.items)}
```

Then in your config:
```yaml
workflow:
  - crawl
  - clean
  - my_step
  - export_json
```

Make sure to import your step before running:
```python
# run.py
import my_project.steps.my_step   # registers it
from scraperkit.core.config import load_config
from scraperkit.core.runner import WorkflowRunner

config = load_config("project.yaml")
WorkflowRunner(config).run()
```

Or load it automatically by placing it in a package and importing it in a plugin entry point (see below).

---

## CRM / database matching example

Match scraped items against an existing database using exact + fuzzy lookup:

```python
from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step
from fuzzywuzzy import fuzz
import json
from pathlib import Path

@register_step("crm_match")
class CRMMatchStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        crm_path = ctx.config.extra.get("crm_file")
        if not crm_path:
            raise ValueError("crm_match step requires 'extra.crm_file' in config")

        crm_data = json.loads(Path(crm_path).read_text(encoding="utf-8"))
        crm_by_address = {
            (d["zip"], d["city"], d["address"]): d
            for d in crm_data["records"]
        }

        matched = 0
        for item in ctx.items:
            key = (item.get("zip"), item.get("city"), item.get("address"))
            if key in crm_by_address:
                crm = crm_by_address[key]
                item["crm_id"] = crm["id"]
                item["match_type"] = "exact"
                matched += 1
                continue

            # Fuzzy fallback on name
            best_score = 0
            best_match = None
            for record in crm_data["records"]:
                score = fuzz.token_set_ratio(
                    item.get("name", ""), record.get("name", "")
                )
                if score > best_score:
                    best_score = score
                    best_match = record

            if best_match and best_score >= 97:
                item["crm_id"] = best_match["id"]
                item["match_type"] = "fuzzy"
                item["match_score"] = best_score
                matched += 1
            else:
                item["crm_id"] = None
                item["match_type"] = "unmatched"

        return {"matched": matched, "unmatched": len(ctx.items) - matched}
```

Config:
```yaml
name: my_project
start_urls: [...]
workflow:
  - crawl
  - clean
  - deduplicate
  - crm_match
  - export_json
  - export_excel
  - compare_previous
  - notify_slack
extra:
  crm_file: "/path/to/crm_export.json"
```

---

## Accessing step results from a later step

```python
@register_step("send_report")
class SendReportStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        compare_result = ctx.meta.get("compare", {})
        new_items = compare_result.get("new", [])
        # Do something with new_items...
```

---

## Filtering items in a step

```python
@register_step("filter_active")
class FilterActiveStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        before = len(ctx.items)
        ctx.items = [i for i in ctx.items if i.get("status") == "active"]
        return {"filtered_out": before - len(ctx.items)}
```

---

## Writing output files from a step

```python
import json

@register_step("export_custom")
class ExportCustomStep(BaseStep):
    def execute(self, ctx: RunContext) -> dict:
        out_dir = ctx.output_dir / "custom"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{ctx.run_ts}_custom.json"
        out_path.write_text(json.dumps(ctx.items, ensure_ascii=False, indent=2))
        # Return file paths so they appear in the run summary + backup step
        return {"output_files": [str(out_path)]}
```

---

## Using ctx.meta to pass data between steps

```python
@register_step("step_a")
class StepA(BaseStep):
    def execute(self, ctx):
        ctx.meta["my_data"] = {"count": 42}
        return {}

@register_step("step_b")
class StepB(BaseStep):
    def execute(self, ctx):
        data = ctx.meta.get("my_data", {})
        print(data["count"])  # 42
        return {}
```
