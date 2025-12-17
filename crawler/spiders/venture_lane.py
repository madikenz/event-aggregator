import scrapy
from datetime import datetime
from crawler.items import EventItem

class VentureLaneSpider(scrapy.Spider):
    name = "venture_lane"
    start_urls = ["https://theventurelane.com/programs-events/"]

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
        
        if True:
            self.logger.info("Dumping HTML to venturelane_debug.html")
            with open("venturelane_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)

        # Selectors for The Events Calendar (Tribe)
        # We target the specific event blocks in the month view
        events = response.css('article.tribe-events-calendar-month__calendar-event')
        
        for event in events:
            item = EventItem()
            item['source'] = "Venture Lane"
            item['tags'] = ['startup', 'venturelane']
            
            # Title
            item['title'] = event.css('.tribe-events-calendar-month__calendar-event-title-link::text').get('').strip()
            
            # URL
            item['url'] = event.css('.tribe-events-calendar-month__calendar-event-title-link::attr(href)').get()
            
            # Date
            # Use the tooltip datetime if available
            date_str = event.css('.tribe-events-calendar-month__calendar-event-tooltip-datetime time::attr(datetime)').get()
            if date_str:
                try:
                    item['date'] = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    item['date'] = datetime.now()
            else:
                 item['date'] = datetime.now()
            
            # Description from tooltip
            desc = event.css('.tribe-events-calendar-month__calendar-event-tooltip-description p::text').get()
            if desc:
                item['description'] = desc.strip()

            if item['title'] and item['url']:
                yield item
