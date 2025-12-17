import scrapy
from datetime import datetime
from crawler.items import EventItem
from scrapy_playwright.page import PageMethod

class HbsAbSpider(scrapy.Spider):
    name = "hbsab"
    start_urls = ["https://www.hbsab.org/s/1738/cc/21/page.aspx?sid=1738&gid=8&pgid=13&cid=664"]

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "viewport": {"width": 1920, "height": 1080},
                        "java_script_enabled": True,
                    }
                }
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()
        
        if True:
            self.logger.info("Dumping HTML to hbsab_debug.html")
            with open("hbsab_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
        
        # Encompass / iModules platform
        # Based on debug HTML: article.eventItem
        
        events = response.css('article.eventItem')
        self.logger.info(f"Found {len(events)} events")
        
        for event in events:
            item = EventItem()
            item['source'] = "HBS Alumni Boston"
            item['tags'] = ['hbs', 'business']
            
            # Title: The <a> tag has a span.sr-only then the text.
            # We want the text node that is NOT the span.
            # h3.title a::text might return the text after the span.
            title_parts = event.css('h3.title a::text').getall()
            item['title'] = "".join(title_parts).strip()
            
            item['url'] = event.css('h3.title a::attr(href)').get()
            
            if item['url'] and not item['url'].startswith('http'):
                item['url'] = f"https://www.hbsab.org{item['url']}"
                
            # Date
            # <span class="sr-only">December 9, 2025: </span>
            date_str = event.css('h3.title a span.sr-only::text').get()
            if date_str:
                date_str = date_str.replace(':', '').strip()
                try:
                    item['date'] = datetime.strptime(date_str, "%B %d, %Y")
                except:
                    # Fallback to dateBox if needed, but year might be missing
                    item['date'] = datetime.now()
            else:
                item['date'] = datetime.now()

            if item['title']:
                yield item

            if item['title']:
                yield item
