import scrapy
from datetime import datetime
from crawler.items import EventItem

class MitHstSpider(scrapy.Spider):
    name = "mit_hst"
    start_urls = ["https://hst.mit.edu/news-events/events-academic-calendar"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                }
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()
        
        # Selectors for MIT HST Events (Drupal)
        # Based on debug HTML: article.node--event inside div.views-row
        events = response.css('article.node--event')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "MIT HST"
            item['tags'] = ['mit', 'hst', 'science']
            
            # Title
            item['title'] = event.css('h2.node__title--event-teaser span::text').get('').strip()
            
            # URL
            rel_url = event.css('h2.node__title--event-teaser a::attr(href)').get()
            if rel_url:
                if rel_url.startswith('/'):
                    item['url'] = "https://hst.mit.edu" + rel_url
                else:
                    item['url'] = rel_url
            else:
                # Fallback
                item['url'] = response.url
            
            # Date
            # <time datetime="2025-12-09T15:00:00-05:00">Dec 9</time>
            date_iso = event.css('time::attr(datetime)').get()
            if date_iso:
                try:
                    item['date'] = datetime.fromisoformat(date_iso)
                except:
                    item['date'] = datetime.now()
            else:
                 item['date'] = datetime.now()
            
            # Description
            desc = event.css('.field--node--field-short-teaser p::text').get()
            if desc:
                item['description'] = desc.strip()

            if item['title']:
                yield item
