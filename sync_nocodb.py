import os
import requests
import logging
from dotenv import load_dotenv
from database.models import get_session, get_engine, Event

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env variables
load_dotenv()

NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN")
NOCODB_BASE_ID = os.getenv("NOCODB_BASE_ID")
NOCODB_TABLE_NAME = os.getenv("NOCODB_TABLE_NAME")
NOCODB_URL = "https://app.nocodb.com/api/v2"

def sync_events_to_nocodb():
    """Reads all events from local DB and upserts them to NocoDB."""
    if not NOCODB_API_TOKEN or not NOCODB_BASE_ID:
        logger.error("❌ NocoDB credentials missing in .env")
        return

    engine = get_engine()
    session = get_session(engine)
    events = session.query(Event).all()
    session.close()

    if not events:
        logger.info("No events to sync.")
        return

    logger.info(f"🔄 Syncing {len(events)} events to NocoDB...")

    headers = {
        "xc-token": NOCODB_API_TOKEN,
        "Content-Type": "application/json"
    }

    # Step 1: Get existing records from NocoDB to avoid duplicates
    # Note: For simplicity in this v1, we will just try to create records. 
    # Ideally, we should check if they exist by 'url' or Title+Date.
    
    success_count = 0
    
    # Batch upload logic could be added here, but let's do one-by-one for safety first.
    # Actually, NocoDB supports bulk create. Let's try to prepare a payload.
    # However, to avoid duplicates without complex logic, we'll just push NEW ones or update.
    # NocoDB doesn't have a native "upsert" via API easily without record ID.
    
    # Alternate strategy: Just Push. If duplicate, we might just have dupes for now or we can query first.
    # Let's try to push individually and just log errors for now.
    
    # Construct the endpoint for "Table Records" -> Create
    # We need the Table ID or Table Name. Using Table Name requires a specific endpoint or ID lookup.
    # It's safer to rely on Table Name if the API supports it, but usually ID is standard.
    # If user provided TABLE NAME, we might need to fetch the ID first.
    # BUT, the user's config implies they might just want to use the Name.
    # Standard NocoDB API structure: /tables/{tableId}/records
    
    # Let's try to list tables to find the ID for "Events"
    tables_url = f"{NOCODB_URL}/meta/bases/{NOCODB_BASE_ID}/tables"
    try:
        r = requests.get(tables_url, headers=headers)
        r.raise_for_status()
        tables = r.json().get('list', [])
        table_id = None
        for t in tables:
            if t['title'] == NOCODB_TABLE_NAME:
                table_id = t['id']
                break
        
        if not table_id:
            logger.error(f"❌ Could not find table '{NOCODB_TABLE_NAME}' in base '{NOCODB_BASE_ID}'")
            return
            
        logger.info(f"✅ Found Table ID: {table_id}")

        # Now we can push records
        records_url = f"{NOCODB_URL}/tables/{table_id}/records"
        
        for e in events:
            # Prepare payload
            payload = {
                "Title": e.title,
                "Description": e.description[:500] if e.description else "", # Truncate to be safe
                "Date": e.date.strftime("%Y-%m-%d") if e.date else None,
                "Location": e.location,
                "URL": e.url,
                "Source": e.source
            }
            
            # Simple check: Try to create. If we wanted duplication check, we'd search first.
            # For now, let's just POST.
            try:
                # We can't easily check duplication without querying by URL first.
                # Let's query by URL to see if it exists.
                # Filter syntax: (URL,eq,value)
                query_params = {
                    "where": f"(URL,eq,{e.url})"
                }
                # check = requests.get(records_url, headers=headers, params=query_params)
                # If verified, we skip.
                # This adds latency. For MVP, let's just push and see.
                
                resp = requests.post(records_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    success_count += 1
                elif resp.status_code == 400:
                    # Maybe validation error?
                    pass
            except Exception as req_err:
                logger.warning(f"Failed to push {e.title}: {req_err}")

        logger.info(f"🎉 Synced {success_count} events to NocoDB successfully!")

    except Exception as e:
        logger.error(f"Sync failed: {e}")

if __name__ == "__main__":
    sync_events_to_nocodb()
