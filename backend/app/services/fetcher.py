from __future__ import annotations

from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import YOUTUBE_API_KEY
from app.models.models import Channel, Video

import re

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Minimum video duration in seconds to include (filters out Shorts/Reels)
MIN_DURATION_SECONDS = 180  # 3 minutes


def parse_iso8601_duration(duration: str) -> int:
    """Parse ISO 8601 duration (e.g. PT1H30M15S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def resolve_channel_id(handle: str) -> str | None:
    """Resolve a YouTube handle (e.g. @LennysPodcast) to a channel ID."""
    url = f"{YOUTUBE_API_BASE}/search"
    params = {
        "part": "snippet",
        "q": handle,
        "type": "channel",
        "maxResults": 1,
        "key": YOUTUBE_API_KEY,
    }
    response = httpx.get(url, params=params)
    response.raise_for_status()
    items = response.json().get("items", [])
    if items:
        return items[0]["snippet"]["channelId"]
    return None


def fetch_recent_videos(channel_id: str, days: int = 7) -> list[dict]:
    """Fetch videos from a channel published in the last N days."""
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"{YOUTUBE_API_BASE}/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "publishedAfter": published_after,
        "type": "video",
        "order": "date",
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }
    response = httpx.get(url, params=params)
    response.raise_for_status()
    return response.json().get("items", [])


def get_video_stats(video_ids: list[str]) -> dict:
    """Get statistics for a list of video IDs."""
    if not video_ids:
        return {}
    url = f"{YOUTUBE_API_BASE}/videos"
    params = {
        "part": "statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }
    response = httpx.get(url, params=params)
    response.raise_for_status()
    stats = {}
    for item in response.json().get("items", []):
        s = item["statistics"]
        stats[item["id"]] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "duration": item["contentDetails"].get("duration", ""),
        }
    return stats


def sync_channel_videos(db: Session, channel: Channel) -> list[Video]:
    """Fetch and store recent videos for a channel."""
    if not channel.youtube_channel_id:
        channel_id = resolve_channel_id(channel.youtube_handle)
        if not channel_id:
            return []
        channel.youtube_channel_id = channel_id
        db.commit()

    items = fetch_recent_videos(channel.youtube_channel_id)
    video_ids = [item["id"]["videoId"] for item in items]
    stats = get_video_stats(video_ids)

    new_videos = []
    for item in items:
        vid = item["id"]["videoId"]
        existing = db.query(Video).filter(Video.youtube_video_id == vid).first()
        if existing:
            continue

        video_stats = stats.get(vid, {})
        duration_str = video_stats.get("duration", "")
        duration_secs = parse_iso8601_duration(duration_str)

        # Skip Shorts/Reels (videos under 3 minutes)
        if duration_secs < MIN_DURATION_SECONDS:
            continue

        video = Video(
            channel_id=channel.id,
            youtube_video_id=vid,
            title=item["snippet"]["title"],
            published_at=datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            ),
            views=video_stats.get("views", 0),
            likes=video_stats.get("likes", 0),
            comments=video_stats.get("comments", 0),
            duration=duration_str,
            thumbnail_url=item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        )
        db.add(video)
        new_videos.append(video)

    db.commit()
    return new_videos


def sync_all_channels(db: Session) -> list[Video]:
    """Sync videos for all channels in the database."""
    channels = db.query(Channel).all()
    all_videos = []
    for channel in channels:
        videos = sync_channel_videos(db, channel)
        all_videos.extend(videos)
    return all_videos
