
import os
import sys
from datetime import datetime, timezone
from sqlalchemy.sql import func
from jinja2 import Environment, FileSystemLoader
from database.models import Event, get_engine, get_session

def generate_static_html():
    engine = get_engine()
    session = get_session(engine)
    
    # Get all active future events
    now = datetime.now(timezone.utc).replace(tzinfo=None) # naive DB match
    events = session.query(Event).filter(
        Event.is_active == True,
        Event.date >= now
    ).order_by(Event.date).all()
    
    # Get source stats
    source_counts = session.query(
        Event.source, func.count(Event.source)
    ).filter(
        Event.is_active == True,
        Event.date >= now
    ).group_by(Event.source).all()
    
    session.close()
    
    # Render Layout
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.html")
    
    output_html = template.render(
        events=events,
        sources=source_counts
    )
    
    # Ensure public dir exists
    if not os.path.exists("public"):
        os.makedirs("public")
        
    # Copy logo
    if not os.path.exists("public/logo"):
        os.makedirs("public/logo")
        
    import shutil
    if os.path.exists("logo/NESEN-LOGO.png"):
        shutil.copy("logo/NESEN-LOGO.png", "public/logo/NESEN-LOGO.png")
    
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print(f"Generated static site in /public with {len(events)} events.")

if __name__ == "__main__":
    generate_static_html()
