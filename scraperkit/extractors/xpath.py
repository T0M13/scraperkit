from __future__ import annotations
from typing import Any

from scraperkit.core.base import BaseExtractor


class XPathExtractor(BaseExtractor):
    """Extracts values using XPath expressions on a Scrapy Selector or response."""

    def extract(self, response: Any, selector: str, default: Any = None) -> Any:
        return response.xpath(selector).get(default=default)

    def extract_all(self, response: Any, selector: str) -> list[Any]:
        return response.xpath(selector).getall()
