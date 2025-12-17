# Boston Events Aggregator - Claude Code Prompt

## Project Overview

Create a Python project called "boston-events-aggregator" that scrapes events from multiple sources, stores them in a database, generates an RSS feed, displays them on a web page, and sends notifications via Telegram bot.

## Event Sources (15 total)

```
1.  https://luma.com/boston
2.  https://www.eventbrite.com/d/ma--boston/all-events/
3.  https://www.meetup.com/find/?location=us--ma--boston
4.  https://venturefizz.com/events/
5.  https://www.startupbos.org/directory/events
6.  https://www.hbsab.org/s/1738/cc/21/page.aspx?sid=1738&gid=8&pgid=13&cid=664
7.  https://entrepreneurship.mit.edu/events-calendar/
8.  https://sloangroups.mit.edu/events
9.  https://innovationlabs.harvard.edu/events/upcoming
10. https://hst.mit.edu/news-events/twihst/volume-27-number-12
11. https://massfoundersnetwork.org/events/
12. https://alumni.northeastern.edu/events/
13. https://bostonchamber.com/event/calendar/
14. https://www.labcentral.org/events-and-media/events
15. https://theventurelane.com/programs-events/
```

## Requirements

### 1. Event Data Model

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    id: str                      # unique hash (title + date + source)
    title: str
    description: str
    date: datetime
    end_date: datetime | None
    location: str
    url: str
    source: str                  # source name
    image_url: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
```

### 2. Scrapers

Create a base scraper class and individual scrapers for each source:

```python
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    name: str
    url: str
    
    @abstractmethod
    async def scrape(self) -> list[Event]:
        pass
    
    def parse_date(self, date_str: str) -> datetime:
        # Common date parsing logic
        pass
```

**Scraper types needed:**
- **Simple HTML** (BeautifulSoup): VentureFizz, MIT HST, Venture Lane, StartupBos
- **JavaScript-rendered** (Playwright): Luma, Eventbrite, Meetup, Harvard Innovation Labs
- **API-based** (if available): Check if sites have JSON APIs in network tab
- **Complex ASP.NET** (special handling): HBS Alumni

### 3. Database

- Use SQLite for development, PostgreSQL-ready for production
- SQLAlchemy ORM with Alembic migrations
- Tables: `events`, `sources`, `sync_logs`, `subscribers`
- Implement deduplication by hashing (title + date + location)

```python
# models.py
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class EventModel(Base):
    __tablename__ = 'events'
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime)
    location = Column(String)
    url = Column(String, nullable=False)
    source = Column(String, nullable=False, index=True)
    image_url = Column(String)
    tags = Column(String)  # JSON array as string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

### 4. RSS Feed Generation

- Endpoint: `GET /rss.xml`
- Standard RSS 2.0 format using `feedgen` library
- Query parameters for filtering:
  - `?source=mit` - filter by source
  - `?days=7` - events in next N days
  - `?tag=startup` - filter by tag

```python
from feedgen.feed import FeedGenerator

def generate_rss(events: list[Event]) -> str:
    fg = FeedGenerator()
    fg.title('Boston Events Aggregator')
    fg.link(href='https://your-domain.com')
    fg.description('Tech, startup, and networking events in Boston/MA')
    
    for event in events:
        fe = fg.add_entry()
        fe.id(event.id)
        fe.title(event.title)
        fe.link(href=event.url)
        fe.description(event.description)
        fe.pubDate(event.date)
    
    return fg.rss_str(pretty=True)
```

### 5. Web Interface

- FastAPI with Jinja2 templates
- Simple, clean HTML/CSS (no JavaScript frameworks)
- Pages:
  - `GET /` - Event listing with filters
  - `GET /event/{id}` - Single event details
  - `GET /sources` - List of sources with status

**Features:**
- Filter by source (dropdown)
- Filter by date range
- Search by keyword
- Pagination (20 events per page)
- Mobile-responsive design

### 6. Telegram Bot

Using `python-telegram-bot` library:

**Commands:**
- `/start` - Welcome message and subscribe
- `/today` - Events happening today
- `/tomorrow` - Events happening tomorrow  
- `/week` - Events in the next 7 days
- `/sources` - List all sources
- `/subscribe` - Subscribe to daily digest
- `/unsubscribe` - Unsubscribe from daily digest
- `/help` - Show available commands

**Features:**
- Daily digest at configurable time (default 9:00 AM EST)
- Inline keyboard for filtering by source
- Event cards with title, date, location, and link

### 7. Scheduler

Use APScheduler for task scheduling:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Scrape all sources every 6 hours
scheduler.add_job(scrape_all_sources, 'interval', hours=6)

# Send daily digest at 9 AM
scheduler.add_job(send_daily_digest, 'cron', hour=9, minute=0)

# Clean old events weekly
scheduler.add_job(cleanup_old_events, 'cron', day_of_week='sun', hour=3)
```

### 8. Configuration

```yaml
# config.yaml
app:
  name: "Boston Events Aggregator"
  debug: false
  timezone: "America/New_York"

database:
  url: "${DATABASE_URL:-sqlite:///events.db}"

sources:
  - name: "Luma Boston"
    url: "https://luma.com/boston"
    parser: "luma"
    enabled: true
    
  - name: "Eventbrite Boston"
    url: "https://www.eventbrite.com/d/ma--boston/all-events/"
    parser: "eventbrite"
    enabled: true
    
  - name: "Meetup Boston"
    url: "https://www.meetup.com/find/?location=us--ma--boston"
    parser: "meetup"
    enabled: true
    
  - name: "VentureFizz"
    url: "https://venturefizz.com/events/"
    parser: "venturefizz"
    enabled: true
    
  - name: "StartupBos"
    url: "https://www.startupbos.org/directory/events"
    parser: "startupbos"
    enabled: true
    
  - name: "HBS Alumni Boston"
    url: "https://www.hbsab.org/s/1738/cc/21/page.aspx?sid=1738&gid=8&pgid=13&cid=664"
    parser: "hbsab"
    enabled: true
    
  - name: "MIT Entrepreneurship"
    url: "https://entrepreneurship.mit.edu/events-calendar/"
    parser: "mit_entrepreneurship"
    enabled: true
    
  - name: "MIT Sloan Groups"
    url: "https://sloangroups.mit.edu/events"
    parser: "mit_sloan"
    enabled: true
    
  - name: "Harvard Innovation Labs"
    url: "https://innovationlabs.harvard.edu/events/upcoming"
    parser: "harvard_ilab"
    enabled: true
    
  - name: "MIT HST"
    url: "https://hst.mit.edu/news-events/twihst/volume-27-number-12"
    parser: "mit_hst"
    enabled: true
    
  - name: "Mass Founders Network"
    url: "https://massfoundersnetwork.org/events/"
    parser: "massfounders"
    enabled: true
    
  - name: "Northeastern Alumni"
    url: "https://alumni.northeastern.edu/events/"
    parser: "northeastern"
    enabled: true
    
  - name: "Boston Chamber"
    url: "https://bostonchamber.com/event/calendar/"
    parser: "boston_chamber"
    enabled: true
    
  - name: "LabCentral"
    url: "https://www.labcentral.org/events-and-media/events"
    parser: "labcentral"
    enabled: true
    
  - name: "The Venture Lane"
    url: "https://theventurelane.com/programs-events/"
    parser: "venturelane"
    enabled: true

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  daily_digest_time: "09:00"
  admin_chat_id: "${TELEGRAM_ADMIN_CHAT_ID}"

rss:
  title: "Boston Events Aggregator"
  description: "Tech, startup, and networking events in Boston/MA"
  max_items: 100
```

### 9. Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/events.db
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ADMIN_CHAT_ID=${TELEGRAM_ADMIN_CHAT_ID}
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Optional: Use PostgreSQL for production
  # db:
  #   image: postgres:15
  #   environment:
  #     - POSTGRES_DB=events
  #     - POSTGRES_USER=events
  #     - POSTGRES_PASSWORD=${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 10. Dependencies

```txt
# requirements.txt
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
alembic>=1.12.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
python-telegram-bot>=20.6
feedgen>=1.0.0
apscheduler>=3.10.0
pyyaml>=6.0.0
python-dotenv>=1.0.0
jinja2>=3.1.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
```

## Implementation Order

1. **Project structure** - Set up folders, configs, dependencies
2. **Database models** - SQLAlchemy models and Alembic migrations
3. **Base scraper class** - Abstract base with common functionality
4. **3 initial scrapers** - Start with VentureFizz (simple), Luma (JS), MIT (medium)
5. **RSS generation** - FastAPI endpoint for RSS feed
6. **Web interface** - Event listing page with filters
7. **Remaining scrapers** - Implement all 15 sources
8. **Telegram bot** - Commands and daily digest
9. **Scheduler** - Automated scraping and notifications
10. **Docker** - Containerization and deployment
11. **Documentation** - README with setup instructions

## Commands to Start

```bash
# Start implementing the project
# Begin with project structure and first 3 scrapers (VentureFizz, Luma, MIT Entrepreneurship)
```
