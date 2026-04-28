"""Config loader: reads YAML/JSON project files and validates them with Pydantic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class FieldExtractorConfig(BaseModel):
    """How to extract a single field. Shorthand: 'css:.title::text' or full form."""
    type: str = "css"          # css | xpath | regex | json
    selector: str
    default: Any = None
    transform: str | None = None  # strip | lower | upper | int | float


class CrawlerConfig(BaseModel):
    item_selector: str | None = None
    fields: dict[str, str | FieldExtractorConfig] = Field(default_factory=dict)
    pagination: dict[str, Any] | None = None
    # Scrapy-level settings override
    settings: dict[str, Any] = Field(default_factory=dict)
    # Anti-detection
    delay_min: float = 2.0
    delay_max: float = 5.0
    autothrottle: bool = True
    rotate_useragent: bool = True
    respect_robots: bool = True
    # JSON API mode
    # Set response_type: json when the start_url returns a JSON response instead of HTML.
    # json_items_path: dot-path to the array of items inside the JSON (e.g. "items" or "data.results")
    # json_total_pages_path: dot-path to the total page count field (used to stop pagination)
    # Fields use plain key names (or dot-paths) as their selector when in JSON mode.
    response_type: str = "html"          # "html" | "json"
    json_items_path: str | None = None   # e.g. "items"  or  "data.dealers"
    json_total_pages_path: str | None = None  # e.g. "total_pages"

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, values: dict) -> dict:
        """Allow shorthand field selectors like 'title: .title::text'."""
        raw_fields = values.get("fields", {})
        response_type = values.get("response_type", "html")
        normalized: dict[str, FieldExtractorConfig | str] = {}
        for name, spec in raw_fields.items():
            if isinstance(spec, str):
                if spec.startswith("xpath="):
                    normalized[name] = {"type": "xpath", "selector": spec[6:]}
                elif spec.startswith("regex="):
                    normalized[name] = {"type": "regex", "selector": spec[6:]}
                elif spec.startswith("json="):
                    normalized[name] = {"type": "json", "selector": spec[5:]}
                elif response_type == "json":
                    # In JSON mode, bare strings are key/dot-path selectors, not CSS
                    normalized[name] = {"type": "json", "selector": spec}
                else:
                    normalized[name] = {"type": "css", "selector": spec}
            else:
                normalized[name] = spec
        values["fields"] = normalized
        return values


class HookConfig(BaseModel):
    on_start: list[str] = Field(default_factory=list)
    on_step_success: list[str] = Field(default_factory=list)
    on_step_error: list[str] = Field(default_factory=list)
    on_crawl_finished: list[str] = Field(default_factory=list)
    on_new_items_found: list[str] = Field(default_factory=list)
    on_workflow_failed: list[str] = Field(default_factory=list)
    on_workflow_success: list[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    model_config = {"populate_by_name": True}
    directory: str = "output"
    # Per-step output overrides (use alias so YAML key "json" still works)
    json_opts: dict[str, Any] = Field(default_factory=dict, alias="json")
    excel: dict[str, Any] = Field(default_factory=dict)
    backup: dict[str, Any] = Field(default_factory=dict)


class NotifySlackConfig(BaseModel):
    token_env: str = "SLACK_TOKEN"         # env var name holding the token
    channel: str                            # channel name or ID
    test_channel: str | None = None


class NotifyEmailConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    from_addr: str
    to_addrs: list[str]
    subject: str = "ScraperKit notification"
    username_env: str = "SMTP_USER"
    password_env: str = "SMTP_PASS"


class SharePointConfig(BaseModel):
    tenant_id_env: str = "SP_TENANT_ID"
    client_id_env: str = "SP_CLIENT_ID"
    client_secret_env: str = "SP_CLIENT_SECRET"
    site_url: str
    drive_id: str
    remote_folder: str
    keep_only_latest: bool = False


class NotifyConfig(BaseModel):
    slack: NotifySlackConfig | None = None
    email: NotifyEmailConfig | None = None
    sharepoint: SharePointConfig | None = None


class CompareConfig(BaseModel):
    """Settings for the compare_previous workflow step."""
    key_field: str = "id"           # field that uniquely identifies an item
    fuzzy_fields: list[str] = Field(default_factory=list)
    fuzzy_threshold: int = 97       # token_set_ratio threshold
    track_file: str | None = None   # explicit path to previous data file


class TaskConfig(BaseModel):
    """A named sub-workflow inside a project config."""
    workflow: list[str]
    description: str | None = None


class ProjectConfig(BaseModel):
    name: str
    start_urls: list[str]
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    workflow: list[str] = Field(default_factory=lambda: ["crawl", "export_json"])
    # Named sub-workflows — run with: scraperkit run config.yaml --task crawl
    tasks: dict[str, TaskConfig] = Field(default_factory=dict)
    default_task: str | None = None   # task to use when no --task flag is given
    hooks: HookConfig = Field(default_factory=HookConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    compare: CompareConfig = Field(default_factory=CompareConfig)
    # Arbitrary extra data available to custom steps
    extra: dict[str, Any] = Field(default_factory=dict)


def load_config(path: str | Path) -> ProjectConfig:
    """Load a YAML or JSON project config file and return a validated ProjectConfig."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(raw)
    elif path.suffix == ".json":
        data = json.loads(raw)
    else:
        raise ValueError(f"Unsupported config format: {path.suffix} (use .yaml/.yml or .json)")

    if "name" not in data:
        data["name"] = path.stem

    return ProjectConfig.model_validate(data)
