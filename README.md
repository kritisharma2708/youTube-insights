# InsightClips

AI-powered tool that monitors your favorite YouTube channels, picks the best recent videos, and delivers bite-sized insight cards with video clips.

## What it does

1. **Fetches** new videos from YouTube channels you follow (last 7 days)
2. **Ranks** them by engagement (views, likes, comments relative to channel average)
3. **Extracts** 5-10 key insights per video using Claude AI — auto-detecting the best summary style (takeaways, actionable advice, or quotable moments)
4. **Generates** short video clips for each insight (vertical 9:16 format)
5. **Runs automatically** every 6 hours via background scheduler

## Channels (seed list)

- [Lenny's Podcast](https://www.youtube.com/@LennysPodcast) — Product, growth, startups
- [Think School](https://www.youtube.com/@ThinkSchool) — Business case studies
- [Dwarkesh Patel](https://www.youtube.com/@DwarkeshPatel) — Deep intellectual interviews, AI, history

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| AI | Claude API (Anthropic) |
| Transcript | youtube-transcript-api |
| Video Clipping | yt-dlp + ffmpeg |
| Database | SQLite (MVP) |
| Frontend | Web UI (served by FastAPI) + React Native mobile app |
| YouTube Data | YouTube Data API v3 |
| Scheduler | APScheduler |

## Quick Start

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```
YOUTUBE_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
APP_API_KEY=any_random_string
```

Seed the channels and start the server:

```bash
python3 -c "
from app.database import SessionLocal, Base, engine
from app.models.models import Channel
from app.config import SEED_CHANNELS
Base.metadata.create_all(bind=engine)
db = SessionLocal()
for ch in SEED_CHANNELS:
    if not db.query(Channel).filter(Channel.youtube_handle == ch['youtube_handle']).first():
        db.add(Channel(name=ch['name'], youtube_handle=ch['youtube_handle']))
db.commit()
db.close()
"

uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser.

### 2. Run the Pipeline

Click the **"Run Pipeline"** button in the web UI, or call:

```bash
curl -X POST -H "X-API-Key: YOUR_APP_API_KEY" http://localhost:8000/api/pipeline?top_n=5
```

This fetches new videos, ranks them, and extracts insights from the top 5.

### 3. Mobile App (optional)

```bash
cd mobile
npm install
npx react-native run-ios   # requires Xcode + CocoaPods
npx react-native run-android  # requires Android SDK
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/feed` | Top 5 ranked videos with insight counts |
| GET | `/api/videos/unprocessed` | Unprocessed videos for discovery |
| GET | `/api/videos/{id}` | Video detail with all insights |
| POST | `/api/videos/{id}/extract` | Extract insights for a video |
| POST | `/api/videos/{id}/clips` | Generate video clips for insights |
| POST | `/api/pipeline?top_n=5` | Run full pipeline (fetch + rank + extract) |

All `/api` endpoints require `X-API-Key` header.

## How It Works

- **Ranking**: Videos are scored by breakout factor (views vs channel average), like-to-view ratio, and comment-to-view ratio
- **Insight Extraction**: Claude analyzes the transcript, identifies the video type (interview, case study, lecture), and auto-selects the best extraction style
- **Shorts Filter**: Videos under 3 minutes are automatically excluded
- **Scheduler**: Background job runs the pipeline every 6 hours

## Tests

```bash
cd backend
source venv/bin/activate
python -m pytest app/tests/ -v          # 34 tests
python -m pytest app/tests/ --cov=app   # with coverage
```

## Project Structure

```
insight-clips/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, auth, lifespan
│   │   ├── config.py            # Environment config
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/models.py     # Channel, Video, Insight models
│   │   ├── schemas/schemas.py   # Pydantic response schemas
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── fetcher.py       # YouTube API integration
│   │   │   ├── ranker.py        # Video ranking algorithm
│   │   │   ├── extractor.py     # Claude AI insight extraction
│   │   │   ├── clip_generator.py# yt-dlp + ffmpeg clips
│   │   │   ├── pipeline.py      # Full pipeline orchestration
│   │   │   └── scheduler.py     # APScheduler background jobs
│   │   ├── static/index.html    # Web frontend
│   │   └── tests/               # 34 tests
│   └── requirements.txt
└── mobile/                      # React Native app
    ├── src/
    │   ├── screens/             # Feed, InsightThread, Channels
    │   ├── components/          # VideoCard, InsightCard
    │   └── services/api.ts      # API client
    └── __tests__/               # 9 component tests
```
