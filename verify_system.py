import requests
import xml.etree.ElementTree as ET
import sys

def check_endpoint(url, description):
    print(f"Checking {description} at {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"✅ {description} is UP (Status: {response.status_code})")
        return response
    except Exception as e:
        print(f"❌ {description} FAILED: {e}")
        return None

def verify_system():
    base_url = "http://127.0.0.1:8000"
    
    # 1. Check Health
    check_endpoint(f"{base_url}/health", "Health Check")
    
    # 2. Check API Events
    resp = check_endpoint(f"{base_url}/api/events", "Events API")
    if resp:
        data = resp.json()
        events = data.get('events', [])
        print(f"   Found {len(events)} events in API response.")
        if len(events) > 0:
            print(f"   Sample: {events[0]['title']}")
            
            # Count by source
            sources = {}
            for e in events:
                src = e['source']
                sources[src] = sources.get(src, 0) + 1
            
            print("   📊 Events by Source:")
            for src, count in sources.items():
                print(f"      - {src}: {count}")
        else:
            print("   ⚠️ No events found in API. Did scrape.py run successfully?")

    # 3. Check RSS Feed
    resp = check_endpoint(f"{base_url}/rss.xml", "RSS Feed")
    if resp:
        try:
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            items = channel.findall('item')
            print(f"   ✅ RSS Valid. Found {len(items)} items in feed.")
        except ET.ParseError as e:
            print(f"   ❌ RSS XML Parsing Failed: {e}")

if __name__ == "__main__":
    verify_system()
