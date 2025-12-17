import scrapy
import re
from datetime import datetime
from scrapy_playwright.page import PageMethod
from crawler.items import EventItem

class VentureFizzSpider(scrapy.Spider):
    name = "venturefizz"
    start_urls = ["https://venturefizz.com/events/"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "article.tribe-events-calendar-list__event"),
                    ],
                ),
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        for card in response.css('article.tribe-events-calendar-list__event'):
            item = EventItem()
            item['source'] = "VentureFizz"
            item['tags'] = ['tech', 'boston']

            # Title & URL
            title_el = card.css('.tribe-events-calendar-list__event-title-link, .tribe-events-list-event-title a')
            item['title'] = title_el.css('::text').get('').strip()
            item['url'] = title_el.css('::attr(href)').get()
            
            if not item['title'] or not item['url']:
                continue

            # Date
            date_ok = False
            time_el = card.css('time.tribe-events-calendar-list__event-datetime')
            date_str = time_el.css('::attr(datetime)').get()
            
            if date_str:
                # Try to extract time "December 11 @ 6:00 pm"
                date_text = time_el.css('::text').get('').strip()
                time_match = re.search(r'@\s*(\d{1,2}:\d{2}\s*[ap]m)', date_text, re.IGNORECASE)
                
                if time_match:
                    try:
                        time_str = time_match.group(1)
                         # Standardize am/pm
                        full_str = f"{date_str} {time_str}"
                         # Fix malformed "6:00pm" -> "6:00 pm" if needed
                        if full_str[-2:].lower() in ['am', 'pm'] and full_str[-3] != ' ':
                            full_str = full_str[:-2] + ' ' + full_str[-2:]
                        
                        item['date'] = datetime.strptime(full_str, "%Y-%m-%d %I:%M %p")
                        date_ok = True
                    except Exception:
                        pass
                
                if not date_ok:
                    # Just the date part
                    try:
                        item['date'] = datetime.fromisoformat(date_str)
                        date_ok = True
                    except:
                        pass

            if not date_ok:
                continue

            # Description
            desc = card.css('.tribe-events-calendar-list__event-description p::text').get()
            item['description'] = desc.strip() if desc else ""

            # Location
            loc_list = card.css('address.tribe-events-calendar-list__event-venue-address span::text').getall()
            item['location'] = ", ".join([l.strip() for l in loc_list if l.strip()]) or "Boston, MA"

            # Image
            item['image_url'] = card.css('img::attr(src)').get()

            yield item
