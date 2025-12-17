import scrapy
from datetime import datetime
from crawler.items import EventItem

class NortheasternAlumniSpider(scrapy.Spider):
    name = "northeastern_alumni"
    start_urls = ["https://alumni.northeastern.edu/events/"]

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
        
        events = response.css('.event-item')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "Northeastern Alumni"
            item['tags'] = ['northeastern', 'alumni']
            
            # Title & URL
            item['title'] = event.css('h3.event-title::text').get('').strip()
            item['url'] = event.css('a::attr(href)').get()
            
            # Timestamp (Unix)
            ts = event.css('.event-date::attr(data-timestamp)').get()
            if ts:
                try:
                    item['date'] = datetime.fromtimestamp(int(ts))
                except:
                    pass
            
            # Fallback Date Parsing (visual elements)
            if 'date' not in item:
                month = event.css('.event-date__month::text').get('').strip()
                day = event.css('.event-date__day::text').get('').strip()
                time_str = event.css('.event-date__time::text').get('').strip() # e.g., 5:30 PM EST
                
                # Construct date string and parse? 
                # Without year, it's risky. But data-timestamp handles most cases.
                pass

            # Location
            item['location'] = event.css('.event-location::text').get('').strip()
            
            # Image
            style = event.css('.event-image::attr(style)').get()
            if style and 'url(' in style:
                import re
                match = re.search(r'url\((.*?)\)', style)
                if match:
                    item['image_url'] = match.group(1).strip("'\"")

            yield item
