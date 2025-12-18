import logging
import schedule
import time
import subprocess
import asyncio
from datetime import datetime
from scrape import main as run_scrapes_internal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_sync_job():
    """Syncs data to NocoDB."""
    logger.info("Starting NocoDB sync...")
    try:
        subprocess.run(["python", "sync_nocodb.py"], check=True)
        logger.info("NocoDB sync finished.")
    except Exception as e:
        logger.error(f"NocoDB sync failed: {e}")

def run_scrape_job():
    """Runs the main scraper."""
    logger.info("Starting scheduled scraper...")
    try:
        # We can call the internal function, or run as subprocess. 
        # Using subprocess is safer for long running processes.
        subprocess.run(["python", "scrape.py"], check=True)
        logger.info("Scraper finished.")
        run_sync_job() # Sync after scraping
    except Exception as e:
        logger.error(f"Scraper job failed: {e}")

def run_search_job():
    """Runs the Tavily search."""
    logger.info("Starting scheduled search job...")
    try:
        subprocess.run(["python", "search_events.py"], check=True)
        logger.info("Search job finished.")
        run_sync_job() # Sync after search
    except Exception as e:
        logger.error(f"Search job failed: {e}")

def run_digest_job():
    """Runs the Telegram digest sender."""
    logger.info("Starting digest job...")
    try:
        subprocess.run(["python", "send_digest.py"], check=True)
        logger.info("Digest sent.")
    except Exception as e:
        logger.error(f"Digest job failed: {e}")

def start_scheduler():
    logger.info("Scheduler started.")
    
    # Schedule Scraper (Morning and Afternoon)
    schedule.every().day.at("07:00").do(run_scrape_job)
    schedule.every().day.at("15:00").do(run_scrape_job)
    
    # Schedule Search (Once a day, mid-morning)
    schedule.every().day.at("09:00").do(run_search_job)
    
    # Schedule Digest (9 PM)
    schedule.every().day.at("21:00").do(run_digest_job)
    
    # Run scrape and search immediately on startup to populate DB
    run_scrape_job()
    run_search_job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_scheduler()

