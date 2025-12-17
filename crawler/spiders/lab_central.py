import scrapy
from datetime import datetime
from crawler.items import EventItem

class LabCentralSpider(scrapy.Spider):
    name = "lab_central"
    start_urls = ["https://www.labcentral.org/events-and-media/events"]

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
        
        # Selectors for LabCentral
        # Events are <a> tags in a grid
        events = response.css('div.grid a[href*="/events/"]')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "LabCentral"
            item['tags'] = ['biotech', 'labcentral']
            
            # Title: It seems the title is in a <p> tag directly inside the <a> or in an h3
            # In the debug HTML, it looks like <p>The Dish...</p> inside the <a>
            item['title'] = event.css('p::text, h3::text').get('').strip()
            
            # URL
            item['url'] = event.css('::attr(href)').get()
            if item['url'] and not item['url'].startswith('http'):
                 item['url'] = f"https://www.labcentral.org{item['url']}"
            
            # Date
            # <h5 class="font-bold ...">12.11.25</h5>
            date_str = event.css('h5::text').get()
            if date_str:
                try:
                    item['date'] = datetime.strptime(date_str.strip(), "%m.%d.%y")
                except:
                    item['date'] = datetime.now()
            else:
                 item['date'] = datetime.now()
            
            # Location
            loc = event.css('h4 span::text').get()
            if loc:
                item['location'] = loc.strip()

            if item['title'] and item['url']:
                yield item
