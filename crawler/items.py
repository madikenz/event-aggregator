import scrapy

class EventItem(scrapy.Item):
    title = scrapy.Field()
    date = scrapy.Field()
    end_date = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    image_url = scrapy.Field()
    tags = scrapy.Field()
