from __future__ import annotations
from typing import Any

from scraperkit.core.base import BaseExtractor


class CssExtractor(BaseExtractor):
    """
    Extracts values using CSS selectors on a Scrapy Selector or response.
    Selector supports Scrapy's ::text and ::attr(x) pseudo-elements.
    """

    def extract(self, response: Any, selector: str, default: Any = None) -> Any:
        return response.css(selector).get(default=default)

    def extract_all(self, response: Any, selector: str) -> list[Any]:
        return response.css(selector).getall()
