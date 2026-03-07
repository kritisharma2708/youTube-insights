from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.models import Channel, Video, Insight
from app.services.clip_generator import generate_clip, generate_clips_for_video


@patch("app.services.clip_generator.run_ffmpeg")
@patch("app.services.clip_generator.download_segment")
def test_generate_clip(mock_download, mock_ffmpeg):
    mock_download.return_value = "/tmp/raw_clip.mp4"
    mock_ffmpeg.return_value = "/tmp/clips/clip_1.mp4"

    result = generate_clip(
        youtube_video_id="abc123",
        start_timestamp=120.0,
        end_timestamp=150.0,
        insight_id=1,
    )
    assert result.endswith(".mp4")
    mock_download.assert_called_once()
    mock_ffmpeg.assert_called_once()


@patch("app.services.clip_generator.generate_clip")
def test_generate_clips_for_video(mock_gen_clip, db_session):
    channel = Channel(name="Test", youtube_handle="@clip", youtube_channel_id="UCC1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="clipvid",
        title="Clip Test",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video)
    db_session.commit()

    for i in range(3):
        insight = Insight(
            video_id=video.id,
            insight_text=f"Insight {i}",
            category="takeaway",
            start_timestamp=float(i * 60),
            end_timestamp=float(i * 60 + 30),
            order=i,
        )
        db_session.add(insight)
    db_session.commit()

    mock_gen_clip.return_value = "/tmp/clips/clip.mp4"

    generate_clips_for_video(db_session, video.id)

    assert mock_gen_clip.call_count == 3
    db_session.refresh(video)
    for insight in video.insights:
        assert insight.clip_url is not None


@patch("app.services.clip_generator.generate_clip")
def test_generate_clips_skips_existing(mock_gen_clip, db_session):
    channel = Channel(name="Test", youtube_handle="@skip", youtube_channel_id="UCC2")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="skipvid",
        title="Skip Test",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video)
    db_session.commit()

    insight = Insight(
        video_id=video.id,
        insight_text="Already clipped",
        category="takeaway",
        start_timestamp=0.0,
        end_timestamp=30.0,
        order=0,
        clip_url="/existing/clip.mp4",
    )
    db_session.add(insight)
    db_session.commit()

    generate_clips_for_video(db_session, video.id)
    mock_gen_clip.assert_not_called()
