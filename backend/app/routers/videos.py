import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.models import Video
from app.schemas.schemas import VideoResponse
from app.services.extractor import extract_insights
from app.services.clip_generator import generate_clips_for_video

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_in_background(video_id: int):
    """Run extraction in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video or video.processed:
            return
        video.extracting = True
        db.commit()

        extract_insights(db, video_id)
        logger.info(f"Background extraction complete for video {video_id}")
    except Exception as e:
        logger.error(f"Background extraction failed for video {video_id}: {e}")
        # Reset extracting flag so user can retry
        try:
            db.expire_all()
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.extracting = False
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/videos/{video_id}/extract")
def extract_video_insights(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.processed:
        return {"message": "Already processed", "insight_count": len(video.insights)}
    if video.extracting:
        return {"message": "Extraction in progress", "status": "extracting"}

    # Start extraction in background thread
    thread = threading.Thread(target=_extract_in_background, args=(video_id,), daemon=True)
    thread.start()

    return {"message": "Extraction started", "status": "extracting"}


@router.get("/videos/{video_id}/status")
def get_video_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.processed:
        return {"status": "done", "insight_count": len(video.insights)}
    if video.extracting:
        return {"status": "extracting"}
    return {"status": "pending"}


@router.post("/videos/{video_id}/clips")
def generate_video_clips(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.processed:
        raise HTTPException(status_code=400, detail="Extract insights first")

    generate_clips_for_video(db, video_id)
    return {"message": "Clips generated", "video_id": video_id}
