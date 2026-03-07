import os
import subprocess

from sqlalchemy.orm import Session

from app.config import CLIPS_STORAGE_PATH
from app.models.models import Video, Insight


def download_segment(youtube_video_id: str, start: float, end: float, output_path: str) -> str:
    """Download a segment of a YouTube video using yt-dlp."""
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{start}-{end}",
        "--force-keyframes-at-cuts",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def run_ffmpeg(input_path: str, output_path: str) -> str:
    """Convert clip to vertical 9:16 format using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "crop=ih*9/16:ih,scale=1080:1920",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def generate_clip(
    youtube_video_id: str,
    start_timestamp: float,
    end_timestamp: float,
    insight_id: int,
) -> str:
    """Generate a vertical clip for an insight."""
    os.makedirs(CLIPS_STORAGE_PATH, exist_ok=True)

    raw_path = os.path.join(CLIPS_STORAGE_PATH, f"raw_{insight_id}.mp4")
    final_path = os.path.join(CLIPS_STORAGE_PATH, f"clip_{insight_id}.mp4")

    download_segment(youtube_video_id, start_timestamp, end_timestamp, raw_path)
    run_ffmpeg(raw_path, final_path)

    # Clean up raw file
    if os.path.exists(raw_path):
        os.remove(raw_path)

    return final_path


def generate_clips_for_video(db: Session, video_id: int) -> None:
    """Generate clips for all insights of a video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return

    for insight in video.insights:
        if insight.clip_url:
            continue

        clip_path = generate_clip(
            youtube_video_id=video.youtube_video_id,
            start_timestamp=insight.start_timestamp,
            end_timestamp=insight.end_timestamp,
            insight_id=insight.id,
        )
        insight.clip_url = clip_path

    db.commit()
