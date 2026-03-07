from datetime import datetime, timezone

from app.models.models import Channel, Video, Insight


def test_create_channel(db_session):
    channel = Channel(
        name="Lenny's Podcast",
        youtube_handle="@LennysPodcast",
        youtube_channel_id="UCtest123",
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    assert channel.id is not None
    assert channel.name == "Lenny's Podcast"
    assert channel.youtube_handle == "@LennysPodcast"
    assert channel.created_at is not None


def test_create_video(db_session):
    channel = Channel(name="Test Channel", youtube_handle="@test", youtube_channel_id="UC1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="abc123",
        title="Test Video",
        published_at=datetime.now(timezone.utc),
        views=1000,
        likes=100,
        comments=50,
        duration="PT1H30M",
        thumbnail_url="https://img.youtube.com/vi/abc123/0.jpg",
        rank_score=0.85,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    assert video.id is not None
    assert video.channel_id == channel.id
    assert video.processed is False
    assert video.channel.name == "Test Channel"


def test_create_insight(db_session):
    channel = Channel(name="Test", youtube_handle="@t", youtube_channel_id="UC2")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="xyz789",
        title="Test",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video)
    db_session.commit()

    insight = Insight(
        video_id=video.id,
        insight_text="Key insight about product management",
        category="takeaway",
        start_timestamp=120.5,
        end_timestamp=145.0,
        order=1,
    )
    db_session.add(insight)
    db_session.commit()
    db_session.refresh(insight)

    assert insight.id is not None
    assert insight.video.title == "Test"
    assert insight.clip_url is None
    assert insight.category == "takeaway"


def test_video_insights_relationship(db_session):
    channel = Channel(name="Test", youtube_handle="@r", youtube_channel_id="UC3")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="rel123",
        title="Relationships",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video)
    db_session.commit()

    for i in range(3):
        insight = Insight(
            video_id=video.id,
            insight_text=f"Insight {i}",
            category="action",
            start_timestamp=float(i * 60),
            end_timestamp=float(i * 60 + 30),
            order=i,
        )
        db_session.add(insight)
    db_session.commit()
    db_session.refresh(video)

    assert len(video.insights) == 3
