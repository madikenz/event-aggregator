
# Scraping Resources & Architecture

This document outlines the resources, technologies, and data sources used in the **Boston Events Aggregator**.

## Core Technologies

*   **[Scrapy](https://scrapy.org/)**: The primary high-level web crawling framework directly used for orchestrating spiders, handling requests, and processing item pipelines.
*   **[Scrapy-Playwright](https://github.com/scrapy-plugins/scrapy-playwright)**: An integration layer that allows Scrapy spiders to use Microsoft's **Playwright** browser automation. This is critical for:
    *   Rendering JavaScript-heavy Single Page Applications (SPAs) like Luma and Startup Boston.
    *   Handling dynamic content loading (infinite scroll).
    *   Bypassing basic anti-bot protections by simulating real browser behavior (headers, user agents).
*   **[SQLAlchemy](https://www.sqlalchemy.org/)**: Object Relational Mapper (ORM) used to model event data and persist it to the SQLite database.
*   **[FeedGen](https://feedgen.kiesow.be/)**: Used to generate standard RSS 2.0 feeds from the scraped database content.

## Data Sources & Spiders

The application scrapes the following sources. Each source has a dedicated "Spider" defined in `crawler/spiders/`.

| Source Name | Target URL | Spider File | Scraping Strategy | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Boston Chamber of Commerce** | `bostonchamber.com/events` | `boston_chamber.py` | Direct HTML (CSS) | Standard static HTML parsing. |
| **Eventbrite** | `eventbrite.com` | `eventbrite.py` | Playwright + LD+JSON | Uses Playwright to render; extracts structured `LD+JSON` data for high fidelity. |
| **Harvard Innovation Labs** | `innovationlabs.harvard.edu` | `harvard_innovation.py` | Direct HTML (CSS) | Parses calendar list views. |
| **HBS Alumni Boston** | `hbsab.org/events` | `hbsab.py` | Direct HTML (CSS) |  |
| **LabCentral** | `labcentral.org/events` | `lab_central.py` | Direct HTML (CSS) |  |
| **Luma (Boston)** | `luma.com/boston` | `luma.py` | Playwright + CSS | Requires Playwright to render the timeline; uses CSS selectors on the dynamic content. |
| **Mass Founders** | `massfounders.com` | `mass_founders.py` | Direct HTML (CSS) |  |
| **Meetup** | `meetup.com` | `meetup.py` | Playwright + API/JSON | Often requires Playwright to handle Meetup's dynamic hydration or internal API JSON structures. |
| **MIT Entrepreneurship** | `orbit.mit.edu` | `mit.py` | Direct HTML (CSS) |  |
| **MIT HST** | `hst.mit.edu` | `mit_hst.py` | Direct HTML (CSS) |  |
| **MIT Sloan** | `sloanclubs.mit.edu` | `sloan.py` | Direct HTML (CSS) |  |
| **Northeastern Alumni** | `alumni.northeastern.edu` | `northeastern.py` | Direct HTML (CSS) |  |
| **Startup Boston** | `startupbos.org` | `startupbos.py` | **Hybrid / Deep Link** | **Complex**: The main calendar widget is blocked. The spider instead scans the page for "Featured" links to Luma/Eventbrite, visits those external pages using Playwright, and extracts `LD+JSON` data. |
| **Venture Lane** | `venturelane.com` | `venture_lane.py` | Direct HTML (CSS) |  |
| **VentureFizz** | `venturefizz.com` | `venturefizz.py` | Direct HTML (CSS) |  |

## Scraping Strategies Explained

### 1. Direct HTML Parsing (Static)
**Used by:** Boston Chamber, MIT, etc.
*   **Method:** Scrapy fetches the raw HTML. CSS selectors (e.g., `div.event-title::text`) are used to extract text.
*   **Pros:** Fast, low resource usage.
*   **Cons:** Breaks easily if site layout changes.

### 2. Playwright Rendering (Dynamic)
**Used by:** Luma, Meetup.
*   **Method:** Scrapy launches a headless Chromium browser via Playwright. It waits for specific JavaScript events (like `wait_for_selector`) before passing the DOM to Scrapy.
*   **Pros:** Can scrape modern React/Vue/Angular apps that don't server-side render.
*   **Cons:** Slower, higher CPU/Memory usage.

### 3. Deep Linking & JSON-LD (Hybrid)
**Used by:** Startup Boston, Eventbrite.
*   **Method:** The spider does not scrape the "List View" directly because it might be incomplete or blocked. Instead, it finds links to individual event pages. On those pages, it looks for the invisible `<script type="application/ld+json">` tag which contains perfectly structured event data (Date, Location, Description) intended for Google Search indexing.
*   **Pros:** Extremely high data quality and reliability. Harder to break.
*   **Cons:** Requires making more requests (1 request per event found).
