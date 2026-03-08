import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def scheduled_pipeline_job():
    """Background job that runs the full pipeline."""
    logger.info("Scheduler: starting pipeline run")
    db = SessionLocal()
    try:
        result = run_pipeline(db, top_n=5)
        logger.info(f"Scheduler: pipeline complete - {result}")
    except Exception as e:
        logger.error(f"Scheduler: pipeline failed - {e}")
    finally:
        db.close()


def start_scheduler(interval_hours: int = 6):
    """Start the background scheduler."""
    scheduler.add_job(
        scheduled_pipeline_job,
        trigger="interval",
        hours=interval_hours,
        id="pipeline_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started: pipeline runs every {interval_hours} hours")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
