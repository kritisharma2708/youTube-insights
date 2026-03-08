from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.post("/pipeline")
def trigger_pipeline(
    top_n: int = Query(5, ge=1, le=20),
    extract: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Trigger pipeline: fetch new videos and rank them. Set extract=true to also run insight extraction (slow)."""
    result = run_pipeline(db, top_n=top_n, extract=extract)
    return result
