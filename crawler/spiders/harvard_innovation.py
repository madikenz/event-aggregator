import scrapy
from datetime import datetime, timedelta
from crawler.items import EventItem

class HarvardInnovationSpider(scrapy.Spider):
    name = "harvard_innovation"
    start_urls = ["https://innovationlabs.harvard.edu/events/upcoming"]

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
        
        # Selectors for Harvard i-lab
        # Based on debug HTML: li.event-tease
        events = response.css('li.event-tease')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "Harvard i-lab"
            item['tags'] = ['harvard', 'innovation']
            
            # Title
            item['title'] = event.css('.event-tease__title::text').get('').strip()
            
            # URL
            item['url'] = event.css('a.event-tease__link::attr(href)').get()
            
            # Date
            # "Mon, Dec 08" -> Needs year.
            date_str = event.css('.event-tease__date::text').get()
            if date_str:
                try:
                    # Clean up
                    date_clean = date_str.split(',')[-1].strip() # "Dec 08"
                    # Add current year
                    now = datetime.now()
                    dt = datetime.strptime(f"{date_clean} {now.year}", "%b %d %Y")
                    # If date is in past (by more than a month?), maybe it's next year? 
                    # But usually "Upcoming" means future. 
                    # If scraped date is Dec 08 and today is Dec 06, it's this year.
                    # If scraped date is Jan 01 and today is Dec 06, it's next year.
                    if dt < now - timedelta(days=30):
                         dt = dt.replace(year=now.year + 1)
                    item['date'] = dt
                except:
                    item['date'] = datetime.now()
            else:
                 item['date'] = datetime.now()
            
            # Location
            loc = event.css('.event-tease__info-location::text').get()
            if loc:
                item['location'] = loc.strip()

            if item['title'] and item['url']:
                yield item
