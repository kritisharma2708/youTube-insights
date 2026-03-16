"""Seed the database with initial channels. Safe to run multiple times."""
from sqlalchemy import inspect, text

from app.database import SessionLocal, Base, engine
from app.models.models import Channel
from app.config import SEED_CHANNELS

Base.metadata.create_all(bind=engine)

# Add missing columns to existing tables (lightweight migration)
with engine.connect() as conn:
    inspector = inspect(engine)
    channels_cols = {c["name"] for c in inspector.get_columns("channels")}
    if "podcast_rss_url" not in channels_cols:
        conn.execute(text("ALTER TABLE channels ADD COLUMN podcast_rss_url VARCHAR"))
        conn.commit()
        print("[MIGRATION] Added podcast_rss_url column to channels")
db = SessionLocal()
for ch in SEED_CHANNELS:
    existing = db.query(Channel).filter(Channel.youtube_handle == ch["youtube_handle"]).first()
    if not existing:
        db.add(Channel(
            name=ch["name"],
            youtube_handle=ch["youtube_handle"],
            podcast_rss_url=ch.get("podcast_rss_url"),
        ))
        print(f"Added channel: {ch['name']}")
    elif ch.get("podcast_rss_url") and not existing.podcast_rss_url:
        existing.podcast_rss_url = ch["podcast_rss_url"]
        print(f"Updated RSS URL for: {ch['name']}")
db.commit()
db.close()
print("Seed complete.")
