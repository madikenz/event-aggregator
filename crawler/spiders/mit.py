import scrapy
from datetime import datetime
from crawler.items import EventItem
from scrapy_playwright.page import PageMethod

class MitSpider(scrapy.Spider):
    name = "mit"
    start_urls = ["https://entrepreneurship.mit.edu/events-calendar/"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "#orbit-events .card"),
                    ],
                )
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        cards = response.css('#orbit-events .card')
        if not cards:
            self.logger.warning("No cards found with primary selector")
            # Fallback
            cards = response.css('article, .event-card')
        
        for card in cards:
            item = EventItem()
            item['source'] = "MIT Entrepreneurship"
            item['tags'] = ['mit', 'entrepreneurship']
            
            # Title
            item['title'] = card.css('h2::text').get('').strip()
            # Link is parent of h2
            # Use xpath to go up
            link = card.xpath('.//h2/parent::a/@href').get()
            if not link:
                link = card.css('a::attr(href)').get()
                
            item['url'] = link
            if not item['title']:
                # fallback
                item['title'] = card.css('h3::text, .title::text').get('').strip()

            if not item['title']:
                continue

            # Date: <h3>December 5...
            date_text = card.css('h3::text').get('').strip()
            # Clean TZ
            date_text = date_text.replace(" EST", "").replace(" EDT", "")
            
            try:
                # "December 5, 2025 at 4:00 PM"
                # Flexible parsing needed?
                # Direct format match first
                item['date'] = datetime.strptime(date_text, "%B %d, %Y at %I:%M %p")
            except ValueError:
                item['date'] = datetime.now() # fail safe for specific run

            description = card.css('p[id^="event-description"]::text, .description::text').get()
            item['description'] = description.strip() if description else ""

            # Location (italic p)
            # CSS can't select by style easily, verify with xpath or just grab all p
            # Logic: <p style="...">Building 32...
            # Just grabbing all p text and checking for building keywords might be safer
            ps = card.css('p::text').getall()
            loc = "MIT, Cambridge, MA"
            for p in ps:
                if "Building" in p or "Room" in p:
                    loc = p.strip()
                    break
            item['location'] = loc

            yield item
