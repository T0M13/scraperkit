import scrapy


class ScraperKitItem(scrapy.Item):
    """Generic item — fields added dynamically per project config."""
    # _meta is used internally to pass source URL and spider metadata
    _url = scrapy.Field()
    _spider = scrapy.Field()
    _crawled_at = scrapy.Field()

    # Dynamic fields are added at runtime by the spider
    def __class_getitem__(cls, item):
        return cls
