from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Video, Channel


def compute_rank_score(video: Video, channel_avg_views: float) -> float:
    """Compute a rank score for a video based on engagement signals."""
    if video.views == 0:
        return 0.0

    # Breakout factor: how much this video exceeded the channel average
    breakout = video.views / max(channel_avg_views, 1)

    # Engagement ratios
    like_ratio = video.likes / video.views if video.views > 0 else 0
    comment_ratio = video.comments / video.views if video.views > 0 else 0

    # Weighted score
    score = (breakout * 0.4) + (like_ratio * 100 * 0.35) + (comment_ratio * 1000 * 0.25)
    return round(score, 4)


def rank_videos(db: Session, top_n: int | None = None) -> list[Video]:
    """Rank all unprocessed or all videos and return sorted list."""
    videos = db.query(Video).all()
    if not videos:
        return []

    # Compute channel average views
    channel_avgs: dict[int, float] = {}
    for video in videos:
        if video.channel_id not in channel_avgs:
            avg = (
                db.query(func.avg(Video.views))
                .filter(Video.channel_id == video.channel_id)
                .scalar()
            )
            channel_avgs[video.channel_id] = float(avg or 1)

    # Score and sort
    for video in videos:
        video.rank_score = compute_rank_score(video, channel_avgs[video.channel_id])
    db.commit()

    videos.sort(key=lambda v: v.rank_score, reverse=True)

    if top_n:
        return videos[:top_n]
    return videos
