from __future__ import annotations
import json
from typing import Any

from scraperkit.core.base import BaseExtractor


class JsonExtractor(BaseExtractor):
    """
    Extracts values from JSON API responses using dot-notation paths.

    Example:
        selector = "data.items.0.name"
        Navigates response["data"]["items"][0]["name"]

    Works on Scrapy responses (parsed via .text), dicts, or plain strings.
    """

    def extract(self, response: Any, selector: str, default: Any = None) -> Any:
        data = self._to_dict(response)
        if data is None:
            return default
        try:
            for key in selector.split("."):
                if isinstance(data, list):
                    data = data[int(key)]
                else:
                    data = data[key]
            return data
        except (KeyError, IndexError, ValueError, TypeError):
            return default

    def extract_all(self, response: Any, selector: str) -> list[Any]:
        """Return a list at the given path, or [] if not found/not a list."""
        result = self.extract(response, selector, default=[])
        return result if isinstance(result, list) else [result]

    @staticmethod
    def _to_dict(response: Any) -> dict | list | None:
        if isinstance(response, (dict, list)):
            return response
        text = getattr(response, "text", None) or str(response)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
