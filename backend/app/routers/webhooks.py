import logging
import threading

import requests as req
from fastapi import APIRouter, Request, HTTPException

from app.config import ASSEMBLYAI_API_KEY
from app.database import SessionLocal
from app.models.models import Video
from app.services.extractor import format_assemblyai_transcript, resume_extraction_after_webhook

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/assemblyai")
async def assemblyai_webhook(request: Request):
    """Receive transcript completion callback from AssemblyAI."""
    data = await request.json()
    transcript_id = data.get("transcript_id")
    status = data.get("status")

    if not transcript_id:
        raise HTTPException(status_code=400, detail="Missing transcript_id")

    logger.info(f"[WEBHOOK] Received AssemblyAI callback: {transcript_id}, status={status}")

    # Look up the video by assemblyai_transcript_id
    db = SessionLocal()
    try:
        video = db.query(Video).filter(
            Video.assemblyai_transcript_id == transcript_id
        ).first()
        if not video:
            logger.warning(f"[WEBHOOK] No video found for transcript_id={transcript_id}")
            return {"status": "ignored"}
        video_id = video.id
    finally:
        db.close()

    if status != "completed":
        # Transcription failed — reset so user can retry
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.extracting = False
                video.assemblyai_transcript_id = None
                db.commit()
                logger.error(f"[WEBHOOK] Transcription failed for video {video_id}: {data.get('error')}")
        finally:
            db.close()
        return {"status": "error_handled"}

    # Fetch full transcript from AssemblyAI (webhook POST only has transcript_id + status)
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    resp = req.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    full_data = resp.json()

    # Format transcript
    transcript = format_assemblyai_transcript(full_data)

    # Resume extraction in background thread (don't block the webhook response)
    thread = threading.Thread(
        target=resume_extraction_after_webhook,
        args=(video_id, transcript),
        daemon=True,
    )
    thread.start()

    return {"status": "processing", "video_id": video_id}
