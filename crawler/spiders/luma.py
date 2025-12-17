import scrapy
from datetime import datetime, timedelta
from crawler.items import EventItem
from scrapy_playwright.page import PageMethod

class LumaSpider(scrapy.Spider):
    name = "luma"
    start_urls = ["https://luma.com/boston"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                         # Wait for the timeline to load
                        PageMethod("wait_for_selector", ".timeline-section"),
                        # Scroll down a bit to trigger lazy loading if needed (optional)
                        PageMethod("evaluate", "window.scrollBy(0, 1000)"),
                        PageMethod("wait_for_timeout", 2000), 
                    ],
                ),
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        # Iterate over timeline sections
        for section in response.css('.timeline-section'):
            # Extract date header "Dec 10", "Today"
            date_text = section.css('.date-title .date::text').get()
            if not date_text:
                continue
                
            base_date = self._parse_section_date(date_text)
            if not base_date:
                continue

            # Iterate over cards in this section
            for card in section.css('.content-card'):
                item = EventItem()
                item['source'] = "Luma"
                item['tags'] = ['luma', 'tech']
                item['location'] = "Boston, MA" # Default

                item['title'] = card.css('h3::text').get('').strip()
                rel_url = card.css('a.event-link::attr(href)').get()
                if rel_url:
                    item['url'] = f"https://luma.com{rel_url}" if rel_url.startswith('/') else rel_url
                
                if not item.get('url'):
                    continue

                # Time parsing
                time_text = card.css('.event-time span::text').get() 
                start_time = base_date
                if time_text:
                    try:
                        t = datetime.strptime(time_text.strip(), "%I:%M %p").time()
                        start_time = base_date.replace(hour=t.hour, minute=t.minute)
                    except:
                        pass
                item['date'] = start_time

                # Location heuristic (same as before)
                # Attributes: often "By Host" is first, Location second
                # Scrapy CSS doesn't handle "not starts-with" easily, so iterate
                attr_texts = card.css('.attribute ::text').getall()
                for t in attr_texts:
                    t = t.strip()
                    if t and not t.startswith("By ") and len(t) > 2:
                        item['location'] = t
                        break
                
                item['image_url'] = card.css('img::attr(src)').get()
                
                yield item

    def _parse_section_date(self, text: str):
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        text = text.lower().strip()
        
        if 'today' in text:
            return today
        if 'tomorrow' in text:
            return today + timedelta(days=1)
            
        try:
            # "Dec 10"
            dt = datetime.strptime(text, "%b %d")
            dt = dt.replace(year=today.year)
            if dt < today - timedelta(days=90): 
                dt = dt.replace(year=today.year + 1)
            return dt
        except ValueError:
            return None
