"""
GenericSpider — one spider that crawls any site based on a ProjectConfig.

Supports two modes set by crawler.response_type:

  html (default):
    - Uses item_selector (CSS) to find repeating nodes on the page
    - Extracts fields with CSS / XPath / Regex / JSON extractors
    - Follows pagination via CSS/XPath "next" link or url_increment

  json:
    - Parses the response body as JSON
    - Uses json_items_path (dot-path) to reach the items array
    - Field selectors are plain key names or dot-paths into each item dict
    - Pagination via url_increment, stopping automatically when the array is empty
    - Optionally reads total_pages from json_total_pages_path to stop earlier
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Generator

import scrapy
from scrapy.http import Response

from scraperkit.core.config import CrawlerConfig, FieldExtractorConfig, ProjectConfig

logger = logging.getLogger("scraperkit.spider")


def _json_path(data: Any, path: str, default: Any = None) -> Any:
    """Navigate a dot-path through nested dicts/lists. Returns default on any miss."""
    try:
        for key in path.split("."):
            if isinstance(data, list):
                data = data[int(key)]
            elif isinstance(data, dict):
                data = data[key]
            else:
                return default
        return data
    except (KeyError, IndexError, ValueError, TypeError):
        return default


class GenericSpider(scrapy.Spider):
    name = "generic"
    custom_settings: dict[str, Any] = {}

    def __init__(self, project_config: ProjectConfig, **kwargs: Any):
        super().__init__(**kwargs)
        self.project_config = project_config
        self.crawler_cfg: CrawlerConfig = project_config.crawler
        self.start_urls = project_config.start_urls

        self.custom_settings = dict(self.crawler_cfg.settings)
        if not self.crawler_cfg.autothrottle:
            self.custom_settings["AUTOTHROTTLE_ENABLED"] = False
        if not self.crawler_cfg.rotate_useragent:
            self.custom_settings.pop("DOWNLOADER_MIDDLEWARES", None)
        self.custom_settings["ROBOTSTXT_OBEY"] = self.crawler_cfg.respect_robots
        self.custom_settings["DOWNLOAD_DELAY"] = self.crawler_cfg.delay_min

        self.collected_items: list[dict] = []

    # ---------------------------------------------------------------- dispatch

    def parse(self, response: Response) -> Generator:
        if self.crawler_cfg.response_type == "json":
            yield from self._parse_json(response)
        else:
            yield from self._parse_html(response)

    # ---------------------------------------------------------------- HTML mode

    def _parse_html(self, response: Response) -> Generator:
        cfg = self.crawler_cfg

        nodes = response.css(cfg.item_selector) if cfg.item_selector else [response]

        for node in nodes:
            item = self._extract_fields_html(node, cfg.fields)
            item["_url"] = response.url
            item["_spider"] = self.name
            item["_crawled_at"] = datetime.now(timezone.utc).isoformat()
            yield item

        if cfg.pagination:
            next_url = self._resolve_html_pagination(response, cfg.pagination)
            if next_url:
                yield response.follow(next_url, callback=self.parse)

    # ---------------------------------------------------------------- JSON mode

    def _parse_json(self, response: Response) -> Generator:
        cfg = self.crawler_cfg
        crawled_at = datetime.now(timezone.utc).isoformat()

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as exc:
            logger.error("Could not decode JSON response from %s: %s", response.url, exc)
            return

        # Locate the items array
        if cfg.json_items_path:
            items = _json_path(data, cfg.json_items_path, default=[])
        else:
            items = data if isinstance(data, list) else [data]

        if not isinstance(items, list):
            logger.warning("json_items_path '%s' did not resolve to a list — got %s", cfg.json_items_path, type(items))
            return

        if not items:
            # Empty array → end of pagination
            logger.info("Empty items array at %s — stopping pagination", response.url)
            return

        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            item = self._extract_fields_json(raw_item, cfg.fields)
            item["_url"] = response.url
            item["_spider"] = self.name
            item["_crawled_at"] = crawled_at
            yield item

        # Pagination for JSON APIs — only url_increment is meaningful here
        if cfg.pagination and cfg.pagination.get("type") == "url_increment":
            # Read total_pages from the JSON response if a path is configured
            total_pages: int | None = None
            if cfg.json_total_pages_path:
                tp = _json_path(data, cfg.json_total_pages_path)
                if tp is not None:
                    try:
                        total_pages = int(tp)
                    except (ValueError, TypeError):
                        pass

            next_url = self._resolve_url_increment(response, cfg.pagination, total_pages)
            if next_url:
                yield response.follow(next_url, callback=self.parse, dont_filter=True)

    # ---------------------------------------------------------------- field extraction

    def _extract_fields_html(
        self,
        node: Any,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name, spec in fields.items():
            if isinstance(spec, str):
                value = node.css(spec).get(default=None)
                result[field_name] = value
            else:
                value = self._extract_one_html(node, spec)
                result[field_name] = self._transform(value, spec.transform)
        return result

    def _extract_one_html(self, node: Any, spec: FieldExtractorConfig) -> Any:
        t, sel, default = spec.type, spec.selector, spec.default
        if t == "css":
            return node.css(sel).get(default=default)
        if t == "xpath":
            return node.xpath(sel).get(default=default)
        if t == "regex":
            import re
            text = node.get() if hasattr(node, "get") else str(node)
            m = re.search(sel, text)
            return (m.group(1) if m.lastindex else m.group(0)) if m else default
        if t == "json":
            try:
                raw = json.loads(node.text if hasattr(node, "text") else str(node))
                return _json_path(raw, sel, default)
            except Exception:
                return default
        logger.warning("Unknown extractor type '%s'", t)
        return default

    def _extract_fields_json(
        self,
        raw_item: dict,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract fields from a plain dict (JSON API item).
        If no fields are defined, return the raw item as-is (all keys preserved).
        Selector is a dot-path key into the item dict.
        """
        if not fields:
            # No field mapping defined — pass through everything
            return dict(raw_item)

        result: dict[str, Any] = {}
        for field_name, spec in fields.items():
            if isinstance(spec, str):
                # Should have been normalized by config validator, but handle anyway
                value = raw_item.get(spec)
            else:
                selector = spec.selector
                value = _json_path(raw_item, selector, spec.default)
                value = self._transform(value, spec.transform)
            result[field_name] = value
        return result

    # ---------------------------------------------------------------- transforms

    def _transform(self, value: Any, transform: str | None) -> Any:
        if value is None or transform is None:
            return value
        if transform == "strip":
            return value.strip() if isinstance(value, str) else value
        if transform == "lower":
            return value.lower() if isinstance(value, str) else value
        if transform == "upper":
            return value.upper() if isinstance(value, str) else value
        if transform == "int":
            try:
                return int(str(value).replace(",", "").replace(".", "").strip())
            except (ValueError, TypeError):
                return value
        if transform == "float":
            try:
                return float(str(value).replace(",", "").strip())
            except (ValueError, TypeError):
                return value
        return value

    # ---------------------------------------------------------------- pagination

    def _resolve_html_pagination(self, response: Response, pagination: dict) -> str | None:
        method = pagination.get("type", "css")
        selector = pagination.get("selector", "")

        if method == "css":
            href = response.css(selector).get()
        elif method == "xpath":
            href = response.xpath(selector).get()
        elif method == "url_increment":
            return self._resolve_url_increment(response, pagination, None)
        else:
            return None

        return response.urljoin(href) if href else None

    def _resolve_url_increment(
        self,
        response: Response,
        pagination: dict,
        total_pages: int | None,
    ) -> str | None:
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        param_name = pagination.get("param", "page")
        current = int(params.get(param_name, ["1"])[0])

        # Stop if we hit a hard max_pages from config
        config_max = pagination.get("max_pages")
        if config_max and current >= int(config_max):
            return None

        # Stop if we know total_pages from the JSON response
        if total_pages is not None and current >= total_pages:
            return None

        params[param_name] = [str(current + 1)]
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
