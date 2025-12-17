"""Database models for Boston Events Aggregator."""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Event(Base):
    """Event model representing a single event from any source."""
    
    __tablename__ = 'events'
    
    id = Column(String(64), primary_key=True)  # SHA256 hash
    title = Column(String(500), nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime)
    location = Column(String(500))
    url = Column(String(1000), nullable=False)
    source = Column(String(100), nullable=False, index=True)
    image_url = Column(String(1000))
    tags_json = Column(Text, default='[]')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    @property
    def tags(self) -> list[str]:
        return json.loads(self.tags_json) if self.tags_json else []
    
    @tags.setter
    def tags(self, value: list[str]):
        self.tags_json = json.dumps(value)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'url': self.url,
            'source': self.source,
            'image_url': self.image_url,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Source(Base):
    """Source configuration and status tracking."""
    
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(String(1000), nullable=False)
    parser = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    last_scrape = Column(DateTime)
    last_success = Column(DateTime)
    last_error = Column(Text)
    event_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncLog(Base):
    """Log of scraping runs for debugging and monitoring."""
    
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    status = Column(String(20), nullable=False)  # success, error, partial
    events_found = Column(Integer, default=0)
    events_new = Column(Integer, default=0)
    events_updated = Column(Integer, default=0)
    error_message = Column(Text)


class Subscriber(Base):
    """Telegram subscribers for daily digest."""
    
    __tablename__ = 'subscribers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), nullable=False, unique=True)
    username = Column(String(100))
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    preferences_json = Column(Text, default='{}')
    
    @property
    def preferences(self) -> dict:
        return json.loads(self.preferences_json) if self.preferences_json else {}
    
    @preferences.setter
    def preferences(self, value: dict):
        self.preferences_json = json.dumps(value)


def get_engine(database_url: str = "sqlite:///data/events.db"):
    """Create database engine."""
    return create_engine(database_url, echo=False)


def get_session(engine):
    """Create database session."""
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(database_url: str = "sqlite:///data/events.db"):
    """Initialize database with all tables."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
