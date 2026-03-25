import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insightclips.db")
CLIPS_STORAGE_PATH = os.getenv("CLIPS_STORAGE_PATH", "./clips")
APP_API_KEY = os.getenv("APP_API_KEY", "")
TRANSCRIPT_PROXY_URL = os.getenv("TRANSCRIPT_PROXY_URL", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")

SEED_CHANNELS = [
    {
        "name": "Lenny's Podcast",
        "youtube_handle": "@LennysPodcast",
        "podcast_rss_url": "https://api.substack.com/feed/podcast/10845.rss",
    },
    {
        "name": "Raj Shamani",
        "youtube_handle": "@rajshamani",
        "podcast_rss_url": "https://anchor.fm/s/f5347ab0/podcast/rss",
    },
    {
        "name": "Dwarkesh Patel",
        "youtube_handle": "@DwarkeshPatel",
        "podcast_rss_url": "https://api.substack.com/feed/podcast/69345.rss",
    },
]
