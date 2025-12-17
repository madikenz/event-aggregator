import scrapy
from datetime import datetime
from crawler.items import EventItem

class SloanSpider(scrapy.Spider):
    name = "sloan"
    start_urls = ["https://sloangroups.mit.edu/events"]

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
        
        # CampusGroups structure (from previous HTML read)
        # It seems the list is loaded dynamically or in a standardized list
        # "### [[[eventName]](...)]" suggests structured rendering.
        
        # Selectors guess based on CampusGroups:
        # div.list-group-item or li.list-group-item
        
        events = response.css('div.list-group-item, li.list-group-item-action, div.club-small-box')
        
        # From the text dump: "### [[[eventName]]" implies h3 > a
        if not events:
            events = response.css('h3')

        for event in events:
            item = EventItem()
            item['source'] = "MIT Sloan"
            item['tags'] = ['mit', 'sloan', 'business']
            
            # If grabbing h3 directly
            if event.root.tag == 'h3':
                item['title'] = event.css('a::text').get('').strip()
                rel_url = event.css('a::attr(href)').get()
            else:
                item['title'] = event.css('h3 a::text, h4 a::text').get('').strip()
                rel_url = event.css('h3 a::attr(href), h4 a::attr(href)').get()
            
            if not item['title']:
                continue
                
            if rel_url and not rel_url.startswith('http'):
                item['url'] = f"https://sloangroups.mit.edu{rel_url}"
            else:
                item['url'] = rel_url

            # Date is likely in a nearby element or sibling header
            # For now default to now() or try to find date in parent
            # From text dump: "## [date_text]" -> "### [eventName]"
            # This suggests H2 is date, H3 is event.
            # We need to iterate the list and keep track of current date.
            
            item['date'] = datetime.now() # Refine later with logic matching date headers
            item['location'] = "MIT Sloan, Cambridge, MA"
            
            yield item
