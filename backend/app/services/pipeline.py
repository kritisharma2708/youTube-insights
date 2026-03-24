import logging

from sqlalchemy.orm import Session

from app.services.fetcher import sync_all_channels
from app.services.ranker import rank_videos
from app.services.extractor import extract_insights, get_transcript, _parse_duration_minutes, MAX_VIDEO_DURATION_MINUTES

logger = logging.getLogger(__name__)


def run_pipeline(db: Session, top_n: int = 5, extract: bool = False) -> dict:
    """Pipeline: fetch new videos, rank them, pre-fetch transcripts, optionally extract insights."""
    # Step 1: Fetch new videos from all channels
    new_videos = sync_all_channels(db)
    logger.info(f"Fetched {len(new_videos)} new videos")

    # Step 2: Rank ALL videos (ranking is cheap — just a DB query)
    ranked = rank_videos(db, top_n=None)
    logger.info(f"Ranked {len(ranked)} total videos")

    # Step 3: Pre-fetch transcripts for unprocessed videos (slow but runs in background)
    transcripts_cached = 0
    extract_limit = top_n or 10
    unprocessed = [
        v for v in ranked
        if not v.processed and _parse_duration_minutes(v.duration) <= MAX_VIDEO_DURATION_MINUTES
    ][:extract_limit]

    for video in unprocessed:
        if video.transcript:
            continue
        try:
            transcript = get_transcript(video)
            # Refresh connection in case it went stale during long transcription
            db.expire_all()
            from app.models.models import Video
            video = db.query(Video).filter(Video.id == video.id).first()
            video.transcript = transcript
            db.commit()
            transcripts_cached += 1
            logger.info(f"Cached transcript for: {video.title}")
        except Exception as e:
            logger.error(f"Failed to fetch transcript for {video.title}: {e}")

    # Step 4: Extract insights (fast now — transcripts are cached)
    processed = 0
    already = 0
    if extract:
        for video in ranked:
            if video.processed:
                already += 1
                continue

            if processed >= extract_limit:
                break

            try:
                insights = extract_insights(video.id)
                processed += 1
                logger.info(f"Extracted {len(insights)} insights from: {video.title}")
            except Exception as e:
                logger.error(f"Failed to extract from {video.title}: {e}")

    result = {
        "videos_fetched": len(new_videos),
        "transcripts_cached": transcripts_cached,
        "videos_processed": processed,
        "already_processed": already,
    }
    logger.info(f"Pipeline complete: {result}")
    return result
