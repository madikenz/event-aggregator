
import os
import time
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from tavily import TavilyClient
import google.generativeai as genai
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from database.models import Event, get_engine, get_session

# Load env vars
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load API Keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Initialize Clients
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
cerebras_client = Cerebras(api_key=CEREBRAS_API_KEY)

# Define Search Queries
def generate_dynamic_queries() -> List[str]:
    """Generate search queries dynamically based on current date."""
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year
    
    # Calculate next month
    if now.month == 12:
        next_month = "January"
        next_year_val = current_year + 1
    else:
        next_date = now + timedelta(days=32)
        next_month = next_date.strftime("%B")
        next_year_val = current_year

    queries = [
        f"upcoming startup events in Boston {current_month} {current_year}",
        f"upcoming startup events in Boston {next_month} {next_year_val}",
        f"upcoming tech conferences Boston {current_year}",
        f"Boston hackathons {current_year}",
        f"entrepreneur networking events Boston {current_month} {current_year}",
        f"MIT innovation events {current_year} open to public",
        f"Harvard biotech startup events {current_year}",
        f"Boston science entrepreneurship events {current_year}",
        f"TEDx events Boston {current_year}",
        f"Climate tech startup events Boston {current_year}",
        f"AI startup events Boston {current_month} {current_year}"
    ]
    return queries
    """
    Search for events using Tavily API.
    """
    try:
        logger.info(f"Searching Tavily for: {query}")
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            include_domains=["eventbrite.com", "luma.com", "meetup.com", "linkedin.com", "techcrunch.com", "boston.com", "mit.edu", "harvard.edu"],
            max_results=10,
            days=30  # Restrict to content published/updated in the last 30 days
        )
        return response.get("results", [])
    except Exception as e:
        logger.error(f"Tavily search failed for query '{query}': {e}")
        return []

def extract_events_with_cerebras(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use Cerebras (llama3.1-70b) to extract structured event data from search results.
    """
    events = []
    
    # Process small batch
    items_to_process = search_results[:5]
    
    prompt_items = []
    for i, res in enumerate(items_to_process):
        prompt_items.append({
            "id": i,
            "title": res.get("title", ""),
            "snippet": (res.get("content") or "")[:500],
            "date_hint": res.get("published_date", ""),
            "url": res.get("url", "")
        })
        
    prompt_json = json.dumps(prompt_items, indent=2)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = f"""
    You are an event scout for the "New England Science and Entrepreneurship Club" (NESEN).
    Today is: {today_str}.
    
    Analyze the search results and identify UPCOMING events (conferences, hackathons, meetups, pitch competitions).
    Focus on: Startups, Biotech, AI, Tech, Entrepreneurship in Boston.
    
    CRITICAL RULES:
    1. EXTRACT REAL DATES. Do not hallucinate. If the snippet says "Dec 10", assume it is the upcoming Dec 10 relative to {today_str}. If "Dec 10" of the current year has passed, assume next year.
    2. IGNORE events that have already passed (before {today_str}).
    3. Return a JSON ARRAY of valid upcoming events.
    4. Format per event: {{"title": "...", "description": "...", "date": "YYYY-MM-DD", "location": "...", "url": "...", "relevance_score": 8}}
    5. If no upcoming events are found, return [].
    """
    
    user_prompt = f"Input Data:\n{prompt_json}"
    
    try:
        response = cerebras_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3.1-8b",
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        extracted_list = []
        if isinstance(data, list):
            extracted_list = data
        elif isinstance(data, dict):
            # Look for a list value if wrapper object returned
            for k, v in data.items():
                if isinstance(v, list):
                    extracted_list = v
                    break
            # If no list found, maybe the dict itself is one item? rare but possible.
            if not extracted_list and data.get('title'):
                extracted_list = [data]
        
        for e in extracted_list:
            if e.get('title') and e.get('url') and e.get('date'):
                # Validate Date is in the future
                try:
                    evt_date = datetime.strptime(e['date'], "%Y-%m-%d")
                    now = datetime.now()
                    if evt_date >= now - timedelta(days=1): # Allow today/yesterday roughly
                         e['source'] = "Tavily Search"
                         events.append(e)
                    else:
                        logger.info(f"Skipping old event from AI: {e.get('title')} ({e.get('date')})")
                except ValueError:
                    # Date parsing failed, skip risk of bad data
                    continue
                
    except Exception as e:
        logger.error(f"Cerebras extraction failed: {e}")
        # Disable risky fallback that invents dates
        pass

    return events

def save_events_to_db(events: List[Dict[str, Any]]):
    """
    Save extracted events to the database, avoiding duplicates.
    """
    engine = get_engine()
    session = get_session(engine)
    
    count = 0
    for evt_data in events:
        try:
            if not evt_data.get('url'): continue
            
            existing = session.query(Event).filter(Event.url == evt_data['url']).first()
            if existing:
                continue
            
            # Parse date
            date_str = evt_data.get('date')
            event_date = None
            if date_str:
                try:
                    event_date = datetime.fromisoformat(date_str)
                except ValueError:
                    try:
                        event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    except:
                        pass
            
            if not event_date:
                 # Default to next week if unknown, or skip? better to have approximate date than none
                 event_date = datetime.now() + timedelta(days=7)
            
            new_event = Event(
                id=os.urandom(8).hex(),
                title=evt_data.get('title'),
                description=evt_data.get('description'),
                date=event_date,
                location=evt_data.get('location'),
                url=evt_data.get('url'),
                source="Tavily Search",
                image_url=None,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_event)
            count += 1
        except Exception as e:
            logger.error(f"Error saving event {evt_data.get('title')}: {e}")
    
    try:
        session.commit()
        logger.info(f"Saved {count} new events from search.")
    except Exception as e:
        session.rollback()
        logger.error(f"Database commit failed: {e}")
    finally:
        session.close()

def run_daily_search():
    logger.info("Starting Daily Search Job...")
    all_events = []
    
    selected_queries = generate_dynamic_queries() 
    
    for query in selected_queries:
        results = search_events_tavily(query)
        if results:
            logger.info(f"   --> Tavily found {len(results)} raw results.")
            extracted = extract_events_with_cerebras(results)
            logger.info(f"   --> AI Extracted {len(extracted)} valid events.")
            all_events.extend(extracted)
            time.sleep(2)
            
    unique_events = {}
    for e in all_events:
        if e.get('url'):
            unique_events[e['url']] = e
    
    save_events_to_db(list(unique_events.values()))
    logger.info("Daily Search Job Completed.")

if __name__ == "__main__":
    run_daily_search()
