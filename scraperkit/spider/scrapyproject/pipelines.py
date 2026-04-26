"""Collects scraped items into a shared list so the crawl step can return them."""
from __future__ import annotations

from typing import Any


class CollectItemsPipeline:
    """Accumulates all items in spider.collected_items for the workflow runner."""

    def open_spider(self, spider: Any) -> None:
        spider.collected_items = []

    def process_item(self, item: Any, spider: Any) -> Any:
        spider.collected_items.append(dict(item))
        return item
