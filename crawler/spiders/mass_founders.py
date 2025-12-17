import scrapy
from datetime import datetime
from crawler.items import EventItem

class MassFoundersSpider(scrapy.Spider):
    name = "mass_founders"
    start_urls = ["https://massfoundersnetwork.org/calendar-embed/v3gJc1MPW7e/embed/"]

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
        
        # Extract event links from the list
        # detailed view usually has links like https://massfoundersnetwork.org/event/...
        event_links = response.css('a[href*="/event/"]::attr(href)').getall()
        
        self.logger.info(f"Found {len(event_links)} event links")
        
        for link in set(event_links):
             yield scrapy.Request(link, callback=self.parse_event, meta=dict(
                 playwright=True,
                 playwright_include_page=True,
             ))

    async def parse_event(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        item = EventItem()
        item['source'] = "Mass Founders Network"
        item['tags'] = ['founders', 'massachusetts']
        item['url'] = response.url
        item['title'] = response.css('h1::text').get('').strip()
        
        # Use Outlook/Google Calendar links for reliable date/location extraction
        outlook_link = response.css('a[href*="outlook.office.com"]::attr(href)').get()
        google_link = response.css('a[href*="google.com/calendar"]::attr(href)').get()
        
        calendar_link = outlook_link or google_link
        
        if calendar_link:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(calendar_link)
            qs = parse_qs(parsed.query)
            
            # Extract dates
            # Outlook use startdt/enddt, Google uses dates=Start/End
            if 'startdt' in qs:
                 start_dt_str = qs['startdt'][0]
                 try:
                     item['date'] = datetime.fromisoformat(start_dt_str)
                 except ValueError:
                     pass # try other parsing
                     
                 if 'enddt' in qs:
                     try:
                        item['end_date'] = datetime.fromisoformat(qs['enddt'][0])
                     except:
                         pass

            elif 'dates' in qs:
                # Google format: 20251202T130000Z/20251202T150000Z
                dates_str = qs['dates'][0]
                parts = dates_str.split('/')
                if len(parts) >= 1:
                     try:
                         item['date'] = datetime.strptime(parts[0], "%Y%m%dT%H%M%SZ")
                     except:
                         pass
                if len(parts) >= 2:
                     try:
                         item['end_date'] = datetime.strptime(parts[1], "%Y%m%dT%H%M%SZ")
                     except:
                         pass

            # Extract location
            if 'location' in qs:
                item['location'] = qs['location'][0]
        
        # Fallback date parsing if calendar link failed
        if 'date' not in item:
             # Try generic time selector or meta tags
             date_text = response.css('.tribe-event-date-start::text, time::attr(datetime)').get()
             if date_text:
                 try:
                     item['date'] = datetime.fromisoformat(date_text)
                 except:
                     item['date'] = datetime.now() # Fail safe
             else:
                 item['date'] = datetime.now()
        
        # Description
        desc = response.css('.tribe-events-single-event-description, .event-description, .entry-content').get()
        # Simple cleanup
        if desc:
            item['description'] = desc
        
        yield item
