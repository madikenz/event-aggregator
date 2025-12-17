# Boston Events Aggregator - Scrapy Edition

This project aggregates events from multiple sources (VentureFizz, Luma, MIT, Eventbrite, Meetup) into a unified database, API, and RSS feed using **Scrapy** and **Playwright**.

## Components

1.  **`crawler/`**: Scrapy project directory.
    *   **`spiders/`**: Contains spiders for `luma`, `meetup`, `eventbrite`, `mit`, `venturefizz`.
    *   **`pipelines.py`**: Saves scraped items to SQLite.
2.  **`api/main.py`**: FastAPI application exposing:
    *   `/api/events`: JSON endpoint.
    *   `/rss.xml`: RSS 2.0 feed (Huginn-compatible).
    *   `/`: Simple HTML dashboard.
3.  **`scrape.py`**: Master script that runs all Scrapy spiders in sequence.
4.  **`scheduler.py`**: Daemon script to run `scrape.py` every 12 hours.
5.  **`data/events.db`**: SQLite database.

## How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the Web Server (API & RSS)
Start the web server to serve the feed.
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```
- RSS Feed: http://localhost:8000/rss.xml
- API: http://localhost:8000/api/events

### 3. Run the Scheduler
In a separate terminal, run the scheduler.
```bash
python scheduler.py
```

### 4. Manual Scrape
To force an update immediately:
```bash
python scrape.py
```
Or run a specific spider:
```bash
python -m scrapy crawl luma
```

## Huginn Integration

1.  Create an **RssAgent** in Huginn.
2.  Set `url` to `http://<your-server-ip>:8000/rss.xml`.
