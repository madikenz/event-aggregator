import scrapy
from datetime import datetime
from crawler.items import EventItem

class BostonChamberSpider(scrapy.Spider):
    name = "boston_chamber"
    start_urls = ["https://bostonchamber.com/event/calendar/"]

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
        
        # Use verified selector from debug HTML
        events = response.css('.fwpl-result')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "Boston Chamber"
            item['tags'] = ['business', 'chamber']
            
            item['title'] = event.css('.event_title h6::text').get('').strip()
            item['url'] = event.css('a.stretched-link::attr(href)').get()
            
            # Categories
            categories = event.css('.taxonomy-term-list span::text').getall()
            for cat in categories:
                cat = cat.strip()
                if cat:
                    item['tags'].append(cat.lower())
            
            # Date Parsing logic
            date_str = event.css('.event-date::text').get('').strip()
            
            # Collect all text from event_data chunks
            data_texts = [t.strip() for t in event.css('.event_data::text').getall() if t.strip()]
            
            time_str = ""
            location_str = ""
            
            # Simple heuristic: Date is usually first, Time second, Location third
            if len(data_texts) >= 1:
                # verify if first looks like date
                pass
            
            if len(data_texts) >= 2:
                 # Check for time chars
                 if any(c in data_texts[1] for c in ['AM', 'PM', 'am', 'pm', ':']):
                     time_str = data_texts[1]
                 else:
                     location_str = data_texts[1]

            if len(data_texts) >= 3 and time_str:
                location_str = data_texts[2]
            
            item['location'] = location_str

            # Parse Date
            if date_str:
                try:
                    # Example: Thursday 1/22/26 or similar
                    clean_date = date_str.split(' ')[-1] if ' ' in date_str else date_str
                    
                    if time_str:
                        # "9:30AM-11:30AM"
                        start_time = time_str.split('-')[0].strip()
                        full_str = f"{clean_date} {start_time}"
                        try:
                            item['date'] = datetime.strptime(full_str, "%m/%d/%y %I:%M%p")
                        except:
                            # Try without time
                            item['date'] = datetime.strptime(clean_date, "%m/%d/%y")
                    else:
                        item['date'] = datetime.strptime(clean_date, "%m/%d/%y")
                except Exception as e:
                    self.logger.warning(f"Error parsing date '{date_str}': {e}")
                    item['date'] = datetime.now()
            else:
                 item['date'] = datetime.now()

            # Image
            style = event.css('.image-div-events-calendar::attr(style)').get()
            if style:
                import re
                match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
                if match:
                    item['image_url'] = match.group(1).strip()

            yield item
