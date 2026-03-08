from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.models import Channel, Video
from app.services.pipeline import run_pipeline


@patch("app.services.pipeline.extract_insights")
@patch("app.services.pipeline.rank_videos")
@patch("app.services.pipeline.sync_all_channels")
def test_pipeline_fetches_ranks_extracts(mock_sync, mock_rank, mock_extract, db_session):
    channel = Channel(name="Test", youtube_handle="@pipe", youtube_channel_id="UCP1")
    db_session.add(channel)
    db_session.commit()

    videos = []
    for i in range(5):
        v = Video(
            channel_id=channel.id,
            youtube_video_id=f"pipe{i}",
            title=f"Pipeline Video {i}",
            published_at=datetime.now(timezone.utc),
            views=(5 - i) * 10000,
            rank_score=float(5 - i),
        )
        db_session.add(v)
        videos.append(v)
    db_session.commit()

    mock_sync.return_value = videos
    mock_rank.return_value = videos[:3]  # rank returns top 3
    mock_extract.return_value = []

    result = run_pipeline(db_session, top_n=3)

    mock_sync.assert_called_once_with(db_session)
    mock_rank.assert_called_once_with(db_session, top_n=3)
    assert mock_extract.call_count == 3
    assert result["videos_fetched"] == 5
    assert result["videos_processed"] == 3


@patch("app.services.pipeline.extract_insights")
@patch("app.services.pipeline.rank_videos")
@patch("app.services.pipeline.sync_all_channels")
def test_pipeline_skips_already_processed(mock_sync, mock_rank, mock_extract, db_session):
    channel = Channel(name="Test", youtube_handle="@skip2", youtube_channel_id="UCP2")
    db_session.add(channel)
    db_session.commit()

    v1 = Video(
        channel_id=channel.id,
        youtube_video_id="already",
        title="Already Done",
        published_at=datetime.now(timezone.utc),
        rank_score=5.0,
        processed=True,
    )
    v2 = Video(
        channel_id=channel.id,
        youtube_video_id="new",
        title="New One",
        published_at=datetime.now(timezone.utc),
        rank_score=4.0,
        processed=False,
    )
    db_session.add_all([v1, v2])
    db_session.commit()

    mock_sync.return_value = []
    mock_rank.return_value = [v1, v2]
    mock_extract.return_value = []

    result = run_pipeline(db_session, top_n=5)

    # Should only extract for the unprocessed one
    mock_extract.assert_called_once()
    assert result["videos_processed"] == 1
    assert result["already_processed"] == 1


@patch("app.services.pipeline.extract_insights")
@patch("app.services.pipeline.rank_videos")
@patch("app.services.pipeline.sync_all_channels")
def test_pipeline_no_videos(mock_sync, mock_rank, mock_extract, db_session):
    mock_sync.return_value = []
    mock_rank.return_value = []

    result = run_pipeline(db_session, top_n=5)

    mock_extract.assert_not_called()
    assert result["videos_fetched"] == 0
    assert result["videos_processed"] == 0


def test_pipeline_api_endpoint(client, db_session):
    """Test the pipeline API endpoint returns correctly."""
    with patch("app.routers.pipeline.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {
            "videos_fetched": 10,
            "videos_processed": 3,
            "already_processed": 2,
        }
        response = client.post("/api/pipeline?top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert data["videos_fetched"] == 10
        assert data["videos_processed"] == 3
