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
        
        # Scroll to load more events
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
        content = await page.content()
        await page.close()
        
        # Re-parse with updated content
        selector = scrapy.Selector(text=content)
        
        # Find all event cards (Meetup changes classes often, looking for generic structure or data-testid)
        # 2024/2025 Layout: usually cards inside a list
        events = selector.css('div[data-testid="category-search-results"] > div')
        
        if not events:
            # Fallback for alternative layout
            events = selector.css('ul li div[data-testid="event-card-in-search"]')
            
        self.logger.info(f"Found {len(events)} visible events on Meetup page.")

        for event in events:
            item = EventItem()
            item['source'] = "Meetup"
            item['tags'] = ['meetup', 'tech']
            
            # Title & URL
            # Usually h2 > a or just a[data-event-label]
            title_el = event.css('h3::text, h2::text').get()
            url_el = event.css('a::attr(href)').get()
            
            if not title_el or not url_el:
                continue
                
            item['title'] = title_el.strip()
            item['url'] = response.urljoin(url_el)
            
            # Description (Meetup search doesn't show full desc, use title as fallback or scrape detail page)
            # For efficiency we stick to list view for now.
            item['description'] = item['title']
            
            # Date (Crucial)
            # usually <time> tag or specific class
            date_text = event.css('time::text').get() 
            # Format: "Fri, Dec 19 · 6:00 PM EST"
            if date_text:
                try:
                    # Clean up: "Fri, Dec 19 · 6:00 PM EST" -> "Dec 19 2025 6:00 PM"
                    # We need to guess year.
                    dt_str = date_text.split('·')[0].strip() # "Fri, Dec 19"
                    
                    # If time exists
                    time_part = date_text.split('·')[1].strip() if '·' in date_text else ""
                    # Remove timezone " EST"
                    time_part = time_part.replace(" EST", "").replace(" EDT", "").strip()
                    
                    # Parse "Fri, Dec 19"
                    current_year = datetime.now().year
                    parse_str = f"{dt_str} {current_year} {time_part}"
                    
                    # Try parsing
                    # Example pattern: "%a, %b %d %Y %I:%M %p"
                    try:
                        dt = datetime.strptime(parse_str, "%a, %b %d %Y %I:%M %p")
                        # Handle year rollover? If parsed date is in past (e.g. Dec 2024 when now is Jan 2025), add year
                        if dt < datetime.now():
                             dt = dt.replace(year=current_year + 1)
                        item['date'] = dt
                    except:
                        # Fallback try without day name
                        # "Dec 19"
                        clean_d = dt_str.split(', ')[-1] # "Dec 19"
                        dt = datetime.strptime(f"{clean_d} {current_year} {time_part}", "%b %d %Y %I:%M %p")
                        if dt < datetime.now():
                             dt = dt.replace(year=current_year + 1)
                        item['date'] = dt
                        
                except Exception as e:
                    self.logger.warning(f"Date parse error '{date_text}': {e}")
                    continue
            else:
                continue
            
            # Location
            # Usually strict text like "Cambridge, MA"
            # It's hard to find generic selector, leaving generic for now
            item['location'] = "Boston, MA"

            yield item
