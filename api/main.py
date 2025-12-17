"""Boston Events Aggregator - FastAPI Application."""

import pytz
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from feedgen.feed import FeedGenerator

from database import init_db, get_engine, get_session, Event

app = FastAPI(
    title="Boston Events Aggregator",
    description="Tech, startup, and networking events in Boston/MA",
    version="1.0.0"
)

app.mount("/logo", StaticFiles(directory="logo"), name="logo")

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# RSS Feed
@app.get("/rss.xml", response_class=Response)
async def rss_feed(
    source: Optional[str] = Query(None, description="Filter by source"),
    days: int = Query(30, description="Events in next N days"),
):
    """Generate RSS feed of events."""
    
    engine = get_engine()
    session = get_session(engine)
    
    try:
        # Relax start date filters to include today's events that might appear "past" in UTC vs Local
        start_date = datetime.utcnow() - timedelta(hours=24)
        end_date = datetime.utcnow() + timedelta(days=days)
        
        query = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= start_date,
            Event.date <= end_date
        )
        
        if source:
            query = query.filter(Event.source.ilike(f"%{source}%"))
        
        events = query.order_by(Event.date).limit(100).all()
        
        # Generate RSS
        fg = FeedGenerator()
        fg.title("Boston Events Aggregator")
        fg.link(href="http://localhost:8000", rel="alternate")
        fg.description("Tech, startup, and networking events in Boston/MA")
        fg.language("en")
        
        # Ensure lastBuildDate is timezone aware
        fg.lastBuildDate(datetime.utcnow().replace(tzinfo=pytz.UTC))
        
        for event in events:
            fe = fg.add_entry()
            fe.id(event.id)
            fe.title(event.title)
            fe.link(href=event.url)
            fe.description(event.description or "")
            
            # Ensure published date is timezone aware
            evt_date = event.date
            if not evt_date.tzinfo:
                evt_date = evt_date.replace(tzinfo=pytz.UTC)
                
            fe.published(evt_date)
            
            content = ""
            if event.location:
                content += f"📍 {event.location}<br/>"
            if event.source:
                content += f"🏷️ {event.source}<br/>"
            if event.date:
                content += f"📅 {event.date.strftime('%Y-%m-%d %H:%M')}<br/><br/>"
            content += event.description or ""
            
            fe.content(content)
        
        rss_xml = fg.rss_str(pretty=True)
        
        return Response(
            content=rss_xml,
            media_type="application/rss+xml"
        )
    finally:
        session.close()

@app.get("/api/events")
async def get_events(
    source: Optional[str] = None,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
):
    """Get events as JSON."""
    
    engine = get_engine()
    session = get_session(engine)
    
    try:
        query = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= datetime.utcnow(),
            Event.date <= datetime.utcnow() + timedelta(days=days)
        )
        
        if source:
            query = query.filter(Event.source.ilike(f"%{source}%"))
        
        total = query.count()
        events = query.order_by(Event.date).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "events": [e.to_dict() for e in events]
        }
    finally:
        session.close()


@app.get("/api/sources")
async def get_sources():
    """Get list of event sources."""
    
    engine = get_engine()
    session = get_session(engine)
    
    try:
        sources = session.query(
            Event.source,
        ).distinct().all()
        
        return {
            "sources": [s[0] for s in sources]
        }
    finally:
        session.close()


# Initialize templates
templates = Jinja2Templates(directory="templates")

# Web Interface
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with event listing."""
    
    engine = get_engine()
    session = get_session(engine)
    
    try:
        # Get start of today (UTC) to ensure we show all events for today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        events = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= today
        ).order_by(Event.date).limit(300).all()

        # Calculate counts per source
        source_counts = {}
        for event in events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
            
        # Sort sources by count (descending)
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "events": events,
            "sources": sorted_sources  # Pass list of (name, count) tuples
        })
    finally:
        session.close()
