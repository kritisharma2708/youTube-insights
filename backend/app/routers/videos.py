from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Video
from app.schemas.schemas import VideoResponse
from app.services.extractor import extract_insights
from app.services.clip_generator import generate_clips_for_video

router = APIRouter()


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

    insights = extract_insights(db, video_id)
    return {"message": "Insights extracted", "insight_count": len(insights)}


@router.post("/videos/{video_id}/clips")
def generate_video_clips(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.processed:
        raise HTTPException(status_code=400, detail="Extract insights first")

    generate_clips_for_video(db, video_id)
    return {"message": "Clips generated", "video_id": video_id}
