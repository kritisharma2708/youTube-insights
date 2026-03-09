import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insightclips.db")
CLIPS_STORAGE_PATH = os.getenv("CLIPS_STORAGE_PATH", "./clips")
APP_API_KEY = os.getenv("APP_API_KEY", "")
TRANSCRIPT_PROXY_URL = os.getenv("TRANSCRIPT_PROXY_URL", "")

SEED_CHANNELS = [
    {"name": "Lenny's Podcast", "youtube_handle": "@LennysPodcast"},
    {"name": "Think School", "youtube_handle": "@ThinkSchool"},
    {"name": "Dwarkesh Patel", "youtube_handle": "@DwarkeshPatel"},
]
