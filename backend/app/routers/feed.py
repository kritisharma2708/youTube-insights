import math
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Video
from app.schemas.schemas import FeedResponse, VideoSummary

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
    )


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    db: Session = Depends(get_db),
):
    """Top 5 ranked videos regardless of processed status."""
    videos = (
        db.query(Video)
        .order_by(Video.rank_score.desc())
        .limit(5)
        .all()
    )

    return FeedResponse(
        videos=[_to_summary(v) for v in videos],
        page=1,
        total_pages=1,
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
