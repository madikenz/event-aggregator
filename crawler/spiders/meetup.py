import scrapy
import json
from datetime import datetime
from crawler.items import EventItem
from scrapy_playwright.page import PageMethod

class MeetupSpider(scrapy.Spider):
    name = "meetup"
    start_urls = ["https://www.meetup.com/find/?location=us--ma--boston&source=EVENTS&categoryId=546"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                         PageMethod("wait_for_selector", "#__NEXT_DATA__")
                    ]
                }
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        next_data = response.css('script#__NEXT_DATA__::text').get()
        if not next_data:
            self.logger.warning("No __NEXT_DATA__ found")
            return

        try:
            data = json.loads(next_data)
            apollo_state = data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})
            
            for key, item in apollo_state.items():
                if item.get('__typename') == 'Event':
                    # Parse event
                    evt = EventItem()
                    evt['title'] = item.get('title')
                    evt['url'] = item.get('eventUrl')
                    if not evt['title'] or not evt['url']:
                        continue
                        
                    evt['source'] = "Meetup"
                    evt['tags'] = ['meetup', 'tech']
                    evt['location'] = "Boston, MA" # Future: resolve Venue ref
                    evt['description'] = item.get('description', '')
                    evt['image_url'] = None # Could extract from images list if needed

                    # Date
                    date_str = item.get('dateTime')
                    if date_str:
                        try:
                            # 2025-12-16T18:30:00-05:00
                            evt['date'] = datetime.fromisoformat(date_str)
                            yield evt
                        except Exception:
                            pass
                            
        except Exception as e:
            self.logger.error(f"Error parsing JSON: {e}")
