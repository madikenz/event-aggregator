import logging
import hashlib
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from database.models import get_engine, Event

class DatabasePipeline:
    def __init__(self):
        engine = get_engine()
        self.Session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        session = self.Session()
        try:
            # Generate ID
            unique_string = f"{item['title']}|{item['date'].isoformat()}|{item['source']}"
            item_id = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
            
            # Prepare data
            event_dict = {
                'id': item_id,
                'title': item['title'],
                'description': item.get('description', ''),
                'date': item['date'],
                'end_date': item.get('end_date'),
                'location': item.get('location', ''),
                'url': item['url'],
                'source': item['source'],
                'image_url': item.get('image_url'),
                'tags_json': json.dumps(item.get('tags', [])),
                'updated_at': datetime.utcnow()
            }
            
            # Upsert
            existing = session.query(Event).filter_by(id=item_id).first()
            if existing:
                for key, value in event_dict.items():
                    if key != 'id':
                        setattr(existing, key, value)
                logging.info(f"Updated event: {item['title']}")
            else:
                new_event = Event(**event_dict)
                session.add(new_event)
                logging.info(f"New event: {item['title']}")
            
            session.commit()
            return item
            
        except Exception as e:
            logging.error(f"Error saving item: {e}")
            session.rollback()
            return item
        finally:
            session.close()
