import scrapy
import json
from datetime import datetime
from crawler.items import EventItem

class EventbriteSpider(scrapy.Spider):
    name = "eventbrite"
    start_urls = ["https://www.eventbrite.com/d/ma--boston/all-events/"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                )
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.close()

        # Strategy 1: JSON-LD
        found_json = False
        scripts = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        for script_content in scripts:
            try:
                data = json.loads(script_content)
                if isinstance(data, dict):
                    if data.get('@type') == 'Event':
                        yield self._parse_json_event(data)
                        found_json = True
                    elif 'itemListElement' in data:
                         for item in data['itemListElement']:
                             if isinstance(item, dict) and item.get('item', {}).get('@type') == 'Event':
                                 yield self._parse_json_event(item['item'])
                                 found_json = True
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Event':
                            yield self._parse_json_event(item)
                            found_json = True
            except:
                pass

    def _parse_json_event(self, data):
        item = EventItem()
        item['source'] = "Eventbrite"
        item['tags'] = ['eventbrite']
        
        item['title'] = data.get('name')
        item['url'] = data.get('url')
        item['description'] = data.get('description', '')
        
        img = data.get('image')
        if isinstance(img, list) and img:
            item['image_url'] = img[0]
        elif isinstance(img, str):
            item['image_url'] = img

        loc = data.get('location', {})
        if isinstance(loc, dict):
             item['location'] = loc.get('name') or loc.get('address', {}).get('addressLocality', "Boston, MA")
        else:
             item['location'] = "Boston, MA"

        try:
            item['date'] = datetime.fromisoformat(data.get('startDate'))
            if data.get('endDate'):
                item['end_date'] = datetime.fromisoformat(data.get('endDate'))
        except:
            if not item.get('date'):
                item['date'] = datetime.now() # Fallback

        return item
