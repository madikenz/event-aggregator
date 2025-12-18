
import os
import sys
import logging
import json
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras
from groq import Groq
from database.models import get_engine, get_session, Event

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def call_ai_with_fallback(client, system_prompt, user_prompt):
    """
    Try Cerebras first. If it fails, fallback to Groq.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Attempt 1: Cerebras
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3.1-8b",
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"⚠️ Cerebras curation failed: {e}. Switching to Groq fallback...")
        
        # Attempt 2: Groq Fallback
        if not GROQ_API_KEY:
            logger.error("❌ Groq API Key missing. Cannot fallback.")
            return None
            
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
            response = groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.6,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as groq_e:
            logger.error(f"❌ Groq fallback also failed: {groq_e}")
            return None

def send_telegram_message(token, chat_id, message, thread_id=None):
    """Send a message to a Telegram chat via the HTTP API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if thread_id:
        payload['message_thread_id'] = thread_id
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Message sent successfully!")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message: {e}")
        return False

def curate_events_with_cerebras(events):
    """
    Use Cerebras to select the top 10 events for NESEN.
    """
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if not cerebras_key:
        logger.warning("CEREBRAS_API_KEY not found. Returning standard sort.")
        return events[:10]

    client = Cerebras(api_key=cerebras_key)

    # Serialize events for prompt
    events_data = []
    for e in events:
        events_data.append({
            "id": e.id,
            "title": e.title,
            "description": e.description[:300] if e.description else "",
            "source": e.source,
            "location": e.location
        })
    
    events_json = json.dumps(events_data)
    
    system_prompt = """
    You are the Event Curator for the "New England Science and Entrepreneurship Club" (NESEN).
    
    Task: Select UP TO 10 events that are STRICTLY relevant to:
    - Science/Tech Startups & Entrepreneurship
    - DIY Biology / Biotech / Pharma
    - DeepTech / AI / Robotics
    - Hackathons & Technical Workshops
    - Academic Innovation (MIT/Harvard/Tufts)
    
    EXCLUDE:
    - Generic parties, holiday galas, concerts, and dance events (unless explicitly for startups).
    - General business networking (unless tech-focused).
    - Politics, arts, crafts, or unrelated social gatherings.
    
    Return a JSON ARRAY of IDs for the selected events.
    If fewer than 10 are relevant, return only the relevant ones. Do not fill with garbage.
    Example: ["id1", "id2", ...]
    """
    
    user_prompt = f"Events List:\n{events_json}"

    extracted = call_ai_with_fallback(client, system_prompt, user_prompt)
    
    if not extracted:
        return events[:10] # Fallback to top 10 recent if AI totally fails
        
    selected_ids = []
    if isinstance(extracted, list):
        selected_ids = extracted
    elif isinstance(extracted, dict):
            # Try to find a list value
            for v in extracted.values():
                if isinstance(v, list):
                    selected_ids = v
                    break
    
    # Normalize selected_ids to be a list of strings
    clean_ids = []
    if isinstance(selected_ids, list):
        for item in selected_ids:
            if isinstance(item, str):
                clean_ids.append(item)
            elif isinstance(item, dict) and 'id' in item:
                clean_ids.append(item['id'])
            elif isinstance(item, dict):
                    # Try finding any value that looks like an ID? or just skip
                    pass
    
    selected_ids = clean_ids

    # Filter original list
    top_events = [e for e in events if e.id in selected_ids]
    
    # Sort based on the selection order
    if selected_ids:
        id_map = {id: index for index, id in enumerate(selected_ids)}
        top_events.sort(key=lambda x: id_map.get(x.id, 999))
    
    # If list is empty (AI failed to return IDs), fallback to date sort
    if not top_events:
            return events[:10]
            
    return top_events


def generate_digest():
    engine = get_engine()
    session = get_session(engine)
    
    try:
        # Fetch upcoming events
        now_utc = datetime.now(timezone.utc)
        now_utc_naive = now_utc.replace(tzinfo=None)
        
        events = session.query(Event).filter(
            Event.is_active == True,
            Event.date >= now_utc_naive,
            Event.date <= now_utc_naive + timedelta(days=7)
        ).order_by(Event.date).limit(200).all()
        
        logger.info(f"Fetched {len(events)} events for the upcoming week (7 days).")
        
        if not events:
            return "No upcoming events found."

        # Curate with AI
        top_events = curate_events_with_cerebras(events)
        
        # Second Layer: Hard Filter for "Dance", "Party" (unless tech related)
        # Often "After-party" is tech related, but "Dance Party" is usually not.
        blacklist = ["dance party", "konpa", "reggae", "gala 2025", "nightclub", "concert"]
        final_events = []
        for e in top_events:
            title_lower = e.title.lower()
            if any(bad in title_lower for bad in blacklist):
                 # Skip unless it has safe words
                 if "startup" in title_lower or "tech" in title_lower or "founder" in title_lower:
                     final_events.append(e)
                 else:
                     continue
            else:
                final_events.append(e)

        if not final_events:
             return "No matching NESEN events found today."

        # Intro Message
        intro_prompts = [
            "Here is your daily dose of innovation for the NESEN Community! 🧬✨",
            "Fresh off the press: Top picks for Boston's science entrepreneurs today. 🚀",
            "Ready to connect? Check out these high-signal events for our community. 💡",
            "Your curated brief of what's happening in Boston Bio/DeepTech this week. 🧪"
        ]
        import random
        selected_intro = random.choice(intro_prompts)

        message = f"🧬 *NESEN Community Daily Digest*\n"
        message += f"_{selected_intro}_\n\n"
        
        for i, event in enumerate(final_events, 1):
            date_str = event.date.strftime('%a, %b %d @ %I%p').replace(" 0", " ")
            message += f"{i}. *{event.title}*\n"
            message += f"   📅 {date_str} | {event.source}\n"
            message += f"   🔗 [Link]({event.url})\n\n"
        
        # Add Scrape Stats
        try:
            stats_path = os.path.join("data", "scrape_stats.json")
            if os.path.exists(stats_path):
                with open(stats_path, "r") as f:
                    stats_data = json.load(f)
                    total_scraped = stats_data.get("total_new", 0)
                    message += f"📊 Total Items Scraped: {total_scraped}\n"
        except Exception:
            pass # Fail silently if stats missing due to manual run

        message += "[​​​​​​​​​​​](https://raw.githubusercontent.com/madikenz/event-aggregator/main/logo/NESEN-LOGO.png)👇 *See all events:* https://madikenz.github.io/event-aggregator/"
        
        return message
        
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    load_dotenv()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    topic_id = os.environ.get("TELEGRAM_TOPIC_ID")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
         print(generate_digest())
         sys.exit(0)

    if not token or not chat_id:
        logger.error(f"Error: Credentials missing. Token set: {bool(token)}, Chat ID set: {bool(chat_id)}")
        print(generate_digest())
        sys.exit(1)
        
    msg = generate_digest()
    if msg:
        send_telegram_message(token, chat_id, msg, thread_id=topic_id)
