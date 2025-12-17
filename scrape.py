import logging
import subprocess
import sys
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPIDERS = [
    'venturefizz', 'luma', 'mit', 'eventbrite', 'meetup',
    'startupbos', 'hbsab', 'sloan', 'harvard_innovation', 'mit_hst',
    'mass_founders', 'northeastern_alumni', 'boston_chamber', 
    'lab_central', 'venture_lane'
]

def main():
    logger.info("Starting Scrapy Crawl Cycle...")
    
    # Ensure database is initialized
    from database import init_db
    init_db()

    stats = {
        "success": [],
        "empty": [],
        "failed": [],
        "total_new": 0
    }

    # regex to extract item count from scrapy log
    # Log line example: 'item_scraped_count': 20,
    item_count_pattern = re.compile(r"'item_scraped_count': (\d+)")

    for spider in SPIDERS:
        logger.info(f"🕸️ Starting spider: {spider}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scrapy", "crawl", spider],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                # Parse item count from logs (stderr)
                match = item_count_pattern.search(result.stderr)
                count = int(match.group(1)) if match else 0
                
                logger.info(f"✅ Spider {spider} finished. Items: {count}")
                stats["total_new"] += count
                
                if count > 0:
                    stats["success"].append((spider, count))
                else:
                    stats["empty"].append(spider)
            else:
                logger.error(f"❌ Spider {spider} failed with code {result.returncode}")
                # Try to capture last few lines of error
                error_snippet = "\n".join(result.stderr.splitlines()[-3:])
                stats["failed"].append((spider, error_snippet))

        except Exception as e:
            logger.error(f"Failed to run spider {spider}: {e}")
            stats["failed"].append((spider, str(e)))

    logger.info("All spiders completed.")

    # Notify Telegram
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
        
        if token and chat_id:
            import requests
            
            message = f"📊 *Daily Scrape Report*\n"
            message += f"Total Items Scraped: {stats['total_new']}\n\n"
            
            if stats["success"]:
                message += "✅ *Active Sources:*\n"
                for name, count in stats["success"]:
                    message += f"• {name.replace('_', ' ').title()}: {count}\n"
                message += "\n"
                
            if stats["empty"]:
                message += "⚠️ *No Events Found (Check if Site Changed):*\n"
                for name in stats["empty"]:
                    message += f"• {name.replace('_', ' ').title()}\n"
                message += "\n"
                
            if stats["failed"]:
                message += "❌ *Failures:*\n"
                for name, err in stats["failed"]:
                    # Escape markdown characters in error
                    err_clean = err.replace('*', '').replace('_', '').replace('`', '')
                    message += f"• {name}: `{err_clean}`\n"
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            })
            logger.info("Telegram notification sent.")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

if __name__ == "__main__":
    main()
