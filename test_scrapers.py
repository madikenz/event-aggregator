import asyncio
import logging
from scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper(name):
    scraper_class = SCRAPERS.get(name)
    if not scraper_class:
        logger.error(f"Scraper {name} not found")
        return

    scraper = scraper_class()
    logger.info(f"Testing {scraper.name} ({scraper.url})")
    
    try:
        if scraper.requires_js:
            print(f"Scraper {name} requires JS/Playwright. Ensure browsers are installed.")
            
        events = await scraper.run()
        print(f"Found {len(events)} events:")
        for event in events[:5]:  # Show first 5
            print(f"- {event.title} ({event.date}) - {event.url}")
            
    except Exception as e:
        logger.error(f"Failed to scrape {name}: {e}")

async def main():
    # Test specific scrapers
    # await test_scraper('luma')
    
    # Test all registered scrapers
    print(f"Available scrapers: {list(SCRAPERS.keys())}")
    for name in SCRAPERS.keys():
        await test_scraper(name)

if __name__ == "__main__":
    asyncio.run(main())
