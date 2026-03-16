import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from sqlalchemy import inspect, text

from app.config import APP_API_KEY
from app.database import Base, engine
from app.routers import feed, pipeline, videos
from app.services.scheduler import start_scheduler, stop_scheduler

Base.metadata.create_all(bind=engine)

# Add missing columns to existing tables (lightweight migration)
with engine.connect() as conn:
    inspector = inspect(engine)
    channels_cols = {c["name"] for c in inspector.get_columns("channels")}
    if "podcast_rss_url" not in channels_cols:
        conn.execute(text("ALTER TABLE channels ADD COLUMN podcast_rss_url VARCHAR"))
        conn.commit()
        print("[MIGRATION] Added podcast_rss_url column to channels")


@asynccontextmanager
async def lifespan(app):
    start_scheduler(interval_hours=6)
    yield
    stop_scheduler()


app = FastAPI(title="InsightClips", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    if not APP_API_KEY:
        return  # No key configured = dev mode
    # Allow same-origin requests from the served frontend (no API key needed)
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    if host and (referer.startswith(f"http://{host}") or referer.startswith(f"https://{host}") or origin == f"http://{host}" or origin == f"https://{host}"):
        return
    if api_key != APP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


app.include_router(
    feed.router, prefix="/api", tags=["feed"], dependencies=[Depends(verify_api_key)]
)
app.include_router(
    videos.router, prefix="/api", tags=["videos"], dependencies=[Depends(verify_api_key)]
)
app.include_router(
    pipeline.router, prefix="/api", tags=["pipeline"], dependencies=[Depends(verify_api_key)]
)


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(static_dir, "index.html"))
