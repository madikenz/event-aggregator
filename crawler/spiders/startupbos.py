
import scrapy
from datetime import datetime
import re
from crawler.items import EventItem
from scrapy.utils.project import get_project_settings

class StartupBosSpider(scrapy.Spider):
    name = "startupbos"
    start_urls = ["https://www.startupbos.org/directory/events"]
    
    custom_settings = {
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "timeout": 60000,
        },
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "viewport": {"width": 1920, "height": 1080},
                        "ignore_https_errors": True,
                        "java_script_enabled": True
                    }
                }
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        try:
            self.logger.info("Navigated to Startup Boston. Waiting for load...")
            
            # Wait for content to ensure page is loaded
            try:
                await page.wait_for_selector("text=STARTUP EVENTS", timeout=20000)
                self.logger.info("Found 'STARTUP EVENTS' header.")
            except:
                self.logger.warning("Could not find 'STARTUP EVENTS' header. Continuing anyway.")

            # Scroll to trigger lazy loading (which might reveal more links)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            # Strategy 1: Extract External Event Links (Luma / Eventbrite)
            # This is the most robust method as it bypasses the iframe widget issues
            
            # Get all links on the page
            links = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors.map(a => ({
                    href: a.href,
                    text: a.innerText
                }));
            }""")
            
            unique_urls = set()
            found_count = 0
            
            for link in links:
                url = link['href']
                
                # Filter for Event Platforms
                if any(domain in url for domain in ["luma.com", "lu.ma", "eventbrite.com"]):
                    # Normalize URL (remove query params for deduplication if needed, but sometimes they allow tracking)
                    # For Luma/Eventbrite, usually keeping query params is noisy, but safe.
                    
                    if url not in unique_urls:
                        unique_urls.add(url)
                        self.logger.info(f"Found External Event Link: {url}")
                        
                        yield scrapy.Request(
                            url,
                            callback=self.parse_external_event,
                            meta={
                                "playwright": True,
                                "playwright_include_page": True, # Needed for LD+JSON extraction via Playwright
                                "playwright_context_kwargs": {
                                    "viewport": {"width": 1920, "height": 1080},
                                }
                            }
                        )
                        found_count += 1

            self.logger.info(f"Dispatched {found_count} external event scraping requests.")
                 
        except Exception as e:
            self.logger.error(f"Top level error: {e}")
        finally:
            await page.close()

    async def parse_external_event(self, response):
        """
        Parses an event page (Luma or Eventbrite) to extract details via LD+JSON.
        """
        page = response.meta["playwright_page"]
        
        try:
            url = response.url
            self.logger.info(f"Scraping External Event: {url}")
            
            # Luma / Eventbrite specific wait
            try:
                # Wait for JSON-LD script or title using a state check
                # Note: 'attached' state is default for wait_for_selector
                await page.wait_for_selector('script[type="application/ld+json"]', timeout=10000)
            except:
                self.logger.warning("Wait for LD+JSON timed out, trying to extract anyway.")
            
            # Extract LD+JSON
            ld_json_list = await page.evaluate("""() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try {
                        return JSON.parse(s.innerText);
                    } catch (e) {
                        return null;
                    }
                }).filter(i => i);
            }""")
            
            event_data = None
            
            # Find the 'Event' object in LD+JSON
            for data in ld_json_list:
                if isinstance(data, dict):
                    if data.get('@type') == 'Event':
                        event_data = data
                        break
                elif isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Event':
                            event_data = item
                            break
            
            if event_data:
                self.logger.info(f"Found LD+JSON Event Data for {url}")
                
                item = EventItem()
                item['source'] = "Startup Boston" 
                item['title'] = event_data.get('name')
                item['url'] = url
                item['description'] = event_data.get('description', '') or ""
                
                # Parse Date
                start_str = event_data.get('startDate')
                if start_str:
                    try:
                        dt = datetime.fromisoformat(start_str)
                        item['date'] = dt.replace(tzinfo=None) # Naive
                    except:
                        self.logger.warning(f"Could not parse date: {start_str}")
                        item['date'] = datetime.now()
                else:
                    item['date'] = datetime.now()

                # Location
                location = event_data.get('location')
                if isinstance(location, dict):
                    item['location'] = location.get('name') or location.get('address', {}).get('addressLocality') or ""
                elif isinstance(location, str):
                    item['location'] = location
                else:
                    item['location'] = "Boston" # Default
                
                # Image
                images = event_data.get('image')
                if isinstance(images, list) and images:
                    item['image_url'] = images[0]
                elif isinstance(images, str):
                    item['image_url'] = images
                
                yield item
            else:
                self.logger.warning(f"No LD+JSON Event found for {url}")
                    
        except Exception as e:
            self.logger.error(f"Error parsing external event {response.url}: {e}")
        finally:
            await page.close()
