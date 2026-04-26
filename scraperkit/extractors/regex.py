from __future__ import annotations
import re
from typing import Any

from scraperkit.core.base import BaseExtractor


class RegexExtractor(BaseExtractor):
    """
    Extracts values from text using regular expressions.
    The selector is the regex pattern; group 1 is returned if present.
    Works on plain strings, Scrapy Selectors, and response objects.
    """

    def extract(self, response: Any, selector: str, default: Any = None) -> Any:
        text = self._to_text(response)
        match = re.search(selector, text, re.DOTALL)
        if not match:
            return default
        return match.group(1) if match.lastindex else match.group(0)

    def extract_all(self, response: Any, selector: str) -> list[str]:
        text = self._to_text(response)
        matches = re.findall(selector, text, re.DOTALL)
        return matches

    @staticmethod
    def _to_text(response: Any) -> str:
        if isinstance(response, str):
            return response
        if hasattr(response, "text"):
            return response.text or ""
        if hasattr(response, "get"):
            return response.get() or ""
        return str(response)
