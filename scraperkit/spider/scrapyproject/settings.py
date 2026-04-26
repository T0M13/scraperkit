"""
Scrapy settings for the ScraperKit generic spider.
These are baseline defaults — CrawlerConfig.settings overrides them at runtime.
"""

BOT_NAME = "scraperkit"

SPIDER_MODULES = ["scraperkit.spider.scrapyproject.spiders"]
NEWSPIDER_MODULE = "scraperkit.spider.scrapyproject.spiders"

# Polite defaults — overridden per project config
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 20
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

DOWNLOADER_MIDDLEWARES = {
    "scraperkit.spider.middlewares.RandomUserAgentMiddleware": 400,
    "scraperkit.spider.middlewares.RandomHeadersMiddleware": 410,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# Disable cookies by default (many anti-bot systems track them)
COOKIES_ENABLED = False

# Don't throttle based on Scrapy's default memory queue size
DEPTH_LIMIT = 0

LOG_LEVEL = "WARNING"

# JSON pipeline enabled by default; steps write files themselves
ITEM_PIPELINES = {
    "scraperkit.spider.scrapyproject.pipelines.CollectItemsPipeline": 100,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
