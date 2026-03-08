from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.post("/pipeline")
def trigger_pipeline(
    top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Trigger the full pipeline: fetch, rank, and extract insights."""
    result = run_pipeline(db, top_n=top_n)
    return result
