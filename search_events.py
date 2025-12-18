
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
        f"tech conferences Boston {current_month} {current_year}",
        f"Boston hackathons {current_month} {current_year}",
        f"entrepreneur networking events Boston {current_month} {current_year}",
        f"MIT innovation events {current_month} {current_year} open to public",
        f"Harvard biotech startup events {next_month} {next_year_val}",
        f"Boston science entrepreneurship events {current_month} {current_year}",
        f"upcoming TEDx events Boston {current_month} {current_year}",
        f"Climate tech startup events Boston {next_month} {next_year_val}",
        f"AI startup events Boston {current_month} {current_year}"
    ]
    return queries

def search_events_tavily(query: str) -> List[Dict[str, Any]]:
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
        results = response.get("results", [])
        
        # DEBUG: Save raw Tavily results to file
        try:
            dump_path = os.path.join("data", "tavily_raw_dump.json")
            existing_data = []
            if os.path.exists(dump_path):
                with open(dump_path, "r") as f:
                    try:
                        existing_data = json.load(f)
                    except: pass
            
            # Timestamp the dump for clarity
            dump_entry = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            existing_data.append(dump_entry)
            
            with open(dump_path, "w") as f:
                json.dump(existing_data, f, indent=2)
            logger.info(f"   💾 Saved raw search results to {dump_path}")
        except Exception as e:
            logger.warning(f"Failed to dump raw Tavily data: {e}")

        return results
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
    1. CHECK THE YEAR: Look for the year in the snippet, title, or date_hint. If you find a year older than the current year (e.g. 2014, 2023), DISCARD IT IMMEDIATELY.
    2. EXTRACT REAL DATES. Do not hallucinate. If the snippet says "Dec 10", assume it is the upcoming Dec 10 relative to {today_str}. If "Dec 10" of the current year has passed, assume next year.
    3. IGNORE events that have already passed (before {today_str}).
    4. Return a JSON ARRAY of valid upcoming events.
    5. Format per event: {{"title": "...", "description": "...", "date": "YYYY-MM-DD", "location": "...", "url": "...", "relevance_score": 8}}
    6. If no upcoming events are found, return [].
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
                    
                    # Hard check: If the event year is older than current year, skip it.
                    if evt_date.year < now.year:
                        logger.info(f"Skipping old year event: {e.get('title')} ({e.get('date')})")
                        continue

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

from playwright.sync_api import sync_playwright

def verify_with_playwright(event_candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Visit the URL using Playwright to extract full text and verify the date/relevance with AI.
    Returns the verified event dict (updated) or None if invalid.
    """
    url = event_candidate.get("url")
    if not url:
        return None
        
    logger.info(f"   🔎 Verifying URL with Playwright: {url}")
    page_text = ""
    
    try:
        with sync_playwright() as p:
            # Launch without user_data_dir to avoid locking issues, use headless
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Set timeout to 15s to be fast
            page.goto(url, timeout=15000, wait_until="domcontentloaded") 
            
            # Simple heuristic to get main content
            page_text = page.evaluate("document.body.innerText")
            browser.close()
            
    except Exception as e:
        logger.warning(f"   ⚠️ Playwright verification failed for {url}: {e}")
        # If site fails (timeout/block), we skip verification and rely on Stage 1 (or discard? Let's keep for now but log)
        return event_candidate

    # Clean text
    clean_text = " ".join(page_text.split())[:3000] # Limit tokens
    
    # AI Verification Prompt
    today_str = datetime.now().strftime("%Y-%m-%d")
    system_prompt = f"""
    You are a Fact-Checker for the NESEN EventAggregator.
    Today is {today_str}.
    
    Task: Verify if this event is REAL, UPCOMING, and RELEVANT based on the webpage text.
    
    Rules:
    1. EXTRACT the exact event date from the text.
    2. If the event date is in the PAST (before {today_str}), is from a PREVIOUS YEAR (e.g. copyright 2024 doesn't count, look for event date 2014, 2023...), or cannot be found -> INVALID.
    3. If the page is a generic "Calendar" or "List of events" and not a specific event page -> INVALID.
    4. Return JSON: {{"is_valid": true/false, "confirmed_date": "YYYY-MM-DD", "reason": "...", "updated_title": "..."}}
    """
    
    user_prompt = f"Candidate Event: {json.dumps(event_candidate)}\n\nWebpage Content Preview:\n{clean_text}"
    
    try:
        # Sleep to avoid Rate Limits (429)
        time.sleep(3)
        
        response = cerebras_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3.1-8b",
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        
        if data.get("is_valid"):
            # Update date if AI found a better one
            if data.get("confirmed_date"):
                 event_candidate["date"] = data["confirmed_date"]
            if data.get("updated_title"):
                 event_candidate["title"] = data["updated_title"]
            logger.info(f"   ✅ Verified: {event_candidate['title']} ({event_candidate['date']})")
            return event_candidate
        else:
            logger.info(f"   ❌ Rejected by Verification: {data.get('reason')} (Real content date: {data.get('confirmed_date')})")
            return None
            
    except Exception as e:
        logger.error(f"   AI Verification Logic Failed: {e}")
        # FAIL SAFE: Should we save unverified? User wants strictness.
        # If verification crashes (e.g. 429), better to discard than to save bad data.
        return None 

def run_daily_search():
    logger.info("Starting Daily Search Job...")
    
    selected_queries = generate_dynamic_queries() 
    
    final_verified_events = []
    
    for query in selected_queries:
        results = search_events_tavily(query)
        if results:
            logger.info(f"   --> Tavily found {len(results)} raw results.")
            
            # Stage 1: Fast Snippet Extraction
            # Sleep before AI extraction too
            time.sleep(2)
            candidates = extract_events_with_cerebras(results)
            logger.info(f"   --> Stage 1: {len(candidates)} candidates.")
            
            # Stage 2: Deep Verification
            for cand in candidates:
                verified = verify_with_playwright(cand)
                if verified:
                    try: 
                        # Final date safety check
                        evt_date = datetime.strptime(verified['date'], "%Y-%m-%d")
                        if evt_date.year < datetime.now().year:
                             logger.info(f"   ❌ Final Safety Check: Date {verified['date']} is too old.")
                             continue
                        final_verified_events.append(verified)
                    except:
                        # If date parsing fails, keep it (AI verification passed)
                        final_verified_events.append(verified)
                        
            time.sleep(5)
            
    # Remove duplicates by URL
    unique_events = {}
    for e in final_verified_events:
        if e.get('url'):
            unique_events[e['url']] = e
    
    if unique_events:
        save_events_to_db(list(unique_events.values()))
    else:
        logger.info("No events found after verification.")
        
    logger.info("Daily Search Job Completed.")

if __name__ == "__main__":
    run_daily_search()
