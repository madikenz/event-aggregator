# Boston Events Aggregator

Aggregates tech, startup, and networking events from multiple sources in Boston/Massachusetts area. Provides RSS feed, web interface, and Telegram bot notifications.

## Features

- 📡 **RSS Feed** - Subscribe in any RSS reader
- 🌐 **Web Interface** - Browse events with filters
- 🤖 **Telegram Bot** - Daily digest and on-demand queries
- ⚡ **15 Event Sources** - MIT, Harvard, Eventbrite, Meetup, and more

## Event Sources

| Source | URL | Status |
|--------|-----|--------|
| Luma Boston | https://luma.com/boston | 🔄 Pending |
| Eventbrite | https://eventbrite.com/d/ma--boston/all-events/ | 🔄 Pending |
| Meetup | https://meetup.com/find/?location=us--ma--boston | 🔄 Pending |
| VentureFizz | https://venturefizz.com/events/ | ✅ Ready |
| StartupBos | https://startupbos.org/directory/events | 🔄 Pending |
| HBS Alumni Boston | https://hbsab.org/... | 🔄 Pending |
| MIT Entrepreneurship | https://entrepreneurship.mit.edu/events-calendar/ | 🔄 Pending |
| MIT Sloan Groups | https://sloangroups.mit.edu/events | 🔄 Pending |
| Harvard Innovation Labs | https://innovationlabs.harvard.edu/events/upcoming | 🔄 Pending |
| MIT HST | https://hst.mit.edu/news-events/twihst/... | 🔄 Pending |
| Mass Founders Network | https://massfoundersnetwork.org/events/ | 🔄 Pending |
| Northeastern Alumni | https://alumni.northeastern.edu/events/ | 🔄 Pending |
| Boston Chamber | https://bostonchamber.com/event/calendar/ | 🔄 Pending |
| LabCentral | https://labcentral.org/events-and-media/events | 🔄 Pending |
| The Venture Lane | https://theventurelane.com/programs-events/ | 🔄 Pending |

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/your-username/boston-events-aggregator.git
cd boston-events-aggregator
cp .env.example .env
# Edit .env with your Telegram bot token
```

### 2. Run with Docker

```bash
docker-compose up -d
```

### 3. Access

- Web: http://localhost:8000
- RSS: http://localhost:8000/rss.xml
- API: http://localhost:8000/api/events

## Development

### Local setup

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run
python -m uvicorn api.main:app --reload
```

### Project Structure

```
boston-events-aggregator/
├── api/                 # FastAPI application
│   └── main.py
├── bot/                 # Telegram bot
├── database/            # SQLAlchemy models
│   └── models.py
├── scrapers/            # Event scrapers
│   ├── base.py          # Base scraper class
│   └── venturefizz.py   # Example scraper
├── templates/           # Jinja2 templates
├── static/              # CSS, JS, images
├── config.yaml          # Source configuration
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web interface |
| `GET /rss.xml` | RSS feed |
| `GET /api/events` | Events JSON |
| `GET /api/sources` | List sources |
| `GET /health` | Health check |

### Query Parameters

- `source` - Filter by source name
- `days` - Events in next N days (default: 30)
- `limit` - Number of results (default: 50)
- `offset` - Pagination offset

## Telegram Bot Commands

- `/start` - Subscribe to updates
- `/today` - Today's events
- `/week` - This week's events
- `/sources` - List all sources
- `/help` - Show commands

## Huginn Integration

This application acts as a "Satellite" scraper that feeds clean data into your Huginn instance via RSS.

### 1. Create an RSS Agent
Create a new **RSS Agent** in Huginn with the following configuration:

```json
{
  "expected_update_period_in_days": "1",
  "clean": "true",
  "url": "http://host.docker.internal:8000/rss.xml"
}
```

*Note: If Huginn is running in Docker, use `http://host.docker.internal:8000/rss.xml` to access this app running on your host machine. If running natively, use `http://localhost:8000/rss.xml`.*

### 2. Connect to Downstream Agents
You can now connect this RSS Agent to other Huginn agents, such as:
- **Trigger Agent**: To filter for specific keywords (e.g., "AI", "Startup").
- **Email Digest Agent**: To send you a weekly summary.
- **Slack/Telegram Agent**: To send real-time notifications.

## Contributing

1. Fork the repo
2. Create a scraper in `scrapers/`
3. Register it in `scrapers/__init__.py`
4. Submit a PR

## Operations Manual

### Core Commands

| Command | Description |
|---------|-------------|
| `python scheduler.py` | **Main Automation**: Runs Scrape -> AI Search -> Static Site -> Diges -> NocoDB Sync in a loop. |
| `python scrape.py` | Runs all Scrapy spiders to collect events from configured sources. |
| `python search_events.py` | Runs AI-powered search (Tavily + LLM) to find and verify events from the web. |
| `python sync_nocodb.py` | Syncs local SQLite database events to NocoDB (De-duplicates by URL). |
| `python send_digest.py` | Generates and sends the daily event digest to Telegram. |
| `python generate_static.py` | Rebuilds the static HTML website (`docs/index.html`) from the database. |

### Debugging & Specific Tasks

- **Run Single Spider**:
  ```bash
  python -m scrapy crawl meetups
  python -m scrapy crawl boston_chamber
  ```

- **Reset Database**:
  Delete `data/events.db` to start fresh. The system will recreate it on next run.

- **Check Logs**:
  Logs are printed to console. `ansible.log` or `scheduler.log` may contain details if configured.

## License

MIT
