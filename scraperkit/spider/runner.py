"""
Runs the Scrapy GenericSpider in-process and returns the collected items.
Uses CrawlerProcess so it can be called from within the workflow step.
"""
from __future__ import annotations

import logging
from typing import Any

from scraperkit.core.config import ProjectConfig

logger = logging.getLogger("scraperkit.spider.runner")


def run_spider(project_config: ProjectConfig) -> list[dict[str, Any]]:
    """
    Spin up a CrawlerProcess, run GenericSpider, and return collected items.

    Uses a fresh Twisted reactor via CrawlerProcess. Must not be called a second
    time in the same process (Scrapy/Twisted limitation) — the crawl workflow step
    handles this by running in a subprocess when needed.
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    from scraperkit.spider.scrapyproject.spiders.generic_spider import GenericSpider

    settings = get_project_settings()
    settings.setmodule(
        "scraperkit.spider.scrapyproject.settings",
        priority="project",
    )

    # Project-level overrides
    crawler_cfg = project_config.crawler
    settings.set("DOWNLOAD_DELAY", crawler_cfg.delay_min, priority="cmdline")
    settings.set("ROBOTSTXT_OBEY", crawler_cfg.respect_robots, priority="cmdline")
    settings.set("AUTOTHROTTLE_ENABLED", crawler_cfg.autothrottle, priority="cmdline")
    for key, val in crawler_cfg.settings.items():
        settings.set(key, val, priority="cmdline")

    process = CrawlerProcess(settings)
    crawler = process.create_crawler(GenericSpider)
    process.crawl(crawler, project_config=project_config)
    process.start()

    spider_instance = crawler.spider
    if spider_instance is None:
        logger.warning("Spider did not run — no items collected")
        return []

    items: list[dict[str, Any]] = getattr(spider_instance, "collected_items", [])
    logger.info("Spider finished. Collected %d items.", len(items))
    return items
