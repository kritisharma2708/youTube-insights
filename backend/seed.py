"""Seed the database with initial channels. Safe to run multiple times."""
from app.database import SessionLocal, Base, engine
from app.models.models import Channel
from app.config import SEED_CHANNELS

Base.metadata.create_all(bind=engine)
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
