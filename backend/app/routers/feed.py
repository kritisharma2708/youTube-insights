import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Video
from app.schemas.schemas import FeedResponse, VideoSummary

router = APIRouter()


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    total = db.query(Video).filter(Video.processed == True).count()
    total_pages = max(math.ceil(total / per_page), 1)

    videos = (
        db.query(Video)
        .filter(Video.processed == True)
        .order_by(Video.rank_score.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    summaries = [
        VideoSummary(
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
        for v in videos
    ]

    return FeedResponse(videos=summaries, page=page, total_pages=total_pages)
