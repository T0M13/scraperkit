from .css import CssExtractor
from .xpath import XPathExtractor
from .regex import RegexExtractor
from .json import JsonExtractor

from scraperkit.core.registry import register_extractor

register_extractor("css")(CssExtractor)
register_extractor("xpath")(XPathExtractor)
register_extractor("regex")(RegexExtractor)
register_extractor("json")(JsonExtractor)

__all__ = ["CssExtractor", "XPathExtractor", "RegexExtractor", "JsonExtractor"]
