import logging

from sqlalchemy.orm import Session

from app.services.fetcher import sync_all_channels
from app.services.ranker import rank_videos
from app.services.extractor import extract_insights

logger = logging.getLogger(__name__)


def run_pipeline(db: Session, top_n: int = 5, extract: bool = False) -> dict:
    """Pipeline: fetch new videos, rank them, optionally extract insights."""
    # Step 1: Fetch new videos from all channels
    new_videos = sync_all_channels(db)
    logger.info(f"Fetched {len(new_videos)} new videos")

    # Step 2: Rank all videos
    ranked = rank_videos(db, top_n=top_n)
    logger.info(f"Top {len(ranked)} ranked videos selected")

    # Step 3: Extract insights only if requested (slow — calls Claude per video)
    processed = 0
    already = 0
    if extract:
        for video in ranked:
            if video.processed:
                already += 1
                logger.info(f"Skipping already processed: {video.title}")
                continue

            try:
                insights = extract_insights(db, video.id)
                processed += 1
                logger.info(f"Extracted {len(insights)} insights from: {video.title}")
            except Exception as e:
                logger.error(f"Failed to extract from {video.title}: {e}")

    result = {
        "videos_fetched": len(new_videos),
        "videos_processed": processed,
        "already_processed": already,
    }
    logger.info(f"Pipeline complete: {result}")
    return result
