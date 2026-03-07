from datetime import datetime, timezone

from app.models.models import Channel, Video
from app.services.ranker import rank_videos


def test_rank_videos_by_engagement(db_session):
    channel = Channel(name="Test", youtube_handle="@rank", youtube_channel_id="UCR1")
    db_session.add(channel)
    db_session.commit()

    # High engagement video
    v1 = Video(
        channel_id=channel.id,
        youtube_video_id="high",
        title="High Engagement",
        published_at=datetime.now(timezone.utc),
        views=100000,
        likes=10000,
        comments=5000,
    )
    # Low engagement video
    v2 = Video(
        channel_id=channel.id,
        youtube_video_id="low",
        title="Low Engagement",
        published_at=datetime.now(timezone.utc),
        views=1000,
        likes=10,
        comments=2,
    )
    # Medium engagement video
    v3 = Video(
        channel_id=channel.id,
        youtube_video_id="med",
        title="Medium Engagement",
        published_at=datetime.now(timezone.utc),
        views=50000,
        likes=5000,
        comments=1000,
    )
    db_session.add_all([v1, v2, v3])
    db_session.commit()

    ranked = rank_videos(db_session)
    assert len(ranked) == 3
    # High engagement should rank first
    assert ranked[0].youtube_video_id == "high"
    # Low engagement should rank last
    assert ranked[2].youtube_video_id == "low"


def test_rank_videos_empty(db_session):
    ranked = rank_videos(db_session)
    assert ranked == []


def test_rank_videos_top_n(db_session):
    channel = Channel(name="Test", youtube_handle="@topn", youtube_channel_id="UCR2")
    db_session.add(channel)
    db_session.commit()

    for i in range(10):
        v = Video(
            channel_id=channel.id,
            youtube_video_id=f"v{i}",
            title=f"Video {i}",
            published_at=datetime.now(timezone.utc),
            views=(i + 1) * 1000,
            likes=(i + 1) * 100,
            comments=(i + 1) * 10,
        )
        db_session.add(v)
    db_session.commit()

    ranked = rank_videos(db_session, top_n=5)
    assert len(ranked) == 5
