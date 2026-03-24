import math
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Video
from app.schemas.schemas import FeedResponse, VideoSummary, WeekFeedResponse, WeekSummary

router = APIRouter()


def _to_summary(v: Video) -> VideoSummary:
    return VideoSummary(
        id=v.id,
        youtube_video_id=v.youtube_video_id,
        title=v.title,
        published_at=v.published_at,
        views=v.views,
        thumbnail_url=v.thumbnail_url,
        rank_score=v.rank_score,
        channel_name=v.channel.name,
        insight_count=len(v.insights),
        extracting=bool(v.extracting),
    )


def _get_monday(d: date) -> date:
    """Return Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


@router.get("/feed", response_model=WeekFeedResponse)
def get_feed(
    week_start: Optional[str] = Query(None, description="ISO date YYYY-MM-DD of the week's Monday"),
    db: Session = Depends(get_db),
):
    """Videos for a given week, ordered by rank_score descending."""
    today = date.today()
    current_monday = _get_monday(today)

    if week_start:
        try:
            monday = date.fromisoformat(week_start)
        except ValueError:
            monday = current_monday
        # Snap to Monday
        monday = _get_monday(monday)
    else:
        monday = current_monday

    sunday = monday + timedelta(days=6)
    is_current_week = monday == current_monday

    # Convert to datetime for DB query
    start_dt = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    end_dt = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, tzinfo=timezone.utc)

    videos = (
        db.query(Video)
        .filter(Video.published_at >= start_dt, Video.published_at <= end_dt)
        .order_by(Video.rank_score.desc())
        .all()
    )

    # Check if any videos exist before this week
    has_previous_week = (
        db.query(Video)
        .filter(Video.published_at < start_dt)
        .first()
    ) is not None

    videos_with_insights = sum(1 for v in videos if len(v.insights) > 0)

    # Build week label like "Mar 10-16" or "Mar 28 - Apr 3"
    if monday.month == sunday.month:
        week_label = f"{monday.strftime('%b')} {monday.day}-{sunday.day}"
    else:
        week_label = f"{monday.strftime('%b')} {monday.day} - {sunday.strftime('%b')} {sunday.day}"

    week = WeekSummary(
        week_start=monday.isoformat(),
        week_end=sunday.isoformat(),
        week_label=week_label,
        total_videos=len(videos),
        videos_with_insights=videos_with_insights,
        has_previous_week=has_previous_week,
        is_current_week=is_current_week,
    )

    return WeekFeedResponse(
        videos=[_to_summary(v) for v in videos],
        week=week,
    )


@router.get("/videos/unprocessed", response_model=FeedResponse)
def get_unprocessed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """All unprocessed videos, ranked by score, for user to explore."""
    total = db.query(Video).filter(Video.processed == False).count()
    total_pages = max(math.ceil(total / per_page), 1)

    videos = (
        db.query(Video)
        .filter(Video.processed == False)
        .order_by(Video.rank_score.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return FeedResponse(
        videos=[_to_summary(v) for v in videos],
        page=page,
        total_pages=total_pages,
    )


@router.get("/videos/all", response_model=FeedResponse)
def get_all_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """All videos (processed and unprocessed), most recent first."""
    total = db.query(Video).count()
    total_pages = max(math.ceil(total / per_page), 1)

    videos = (
        db.query(Video)
        .order_by(Video.published_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return FeedResponse(
        videos=[_to_summary(v) for v in videos],
        page=page,
        total_pages=total_pages,
    )
