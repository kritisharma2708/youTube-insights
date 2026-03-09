"""Seed the database with initial channels. Safe to run multiple times."""
from app.database import SessionLocal, Base, engine
from app.models.models import Channel
from app.config import SEED_CHANNELS

Base.metadata.create_all(bind=engine)
db = SessionLocal()
for ch in SEED_CHANNELS:
    if not db.query(Channel).filter(Channel.youtube_handle == ch["youtube_handle"]).first():
        db.add(Channel(name=ch["name"], youtube_handle=ch["youtube_handle"]))
        print(f"Added channel: {ch['name']}")
db.commit()
db.close()
print("Seed complete.")
