from datetime import datetime, timedelta, timezone

from app.models.models import Channel, Video, Insight


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_feed_empty(client):
    response = client.get("/api/feed")
    assert response.status_code == 200
    data = response.json()
    assert data["videos"] == []
    assert "week" in data
    assert data["week"]["is_current_week"] is True


def test_feed_returns_current_week_videos(client, db_session):
    channel = Channel(name="Test", youtube_handle="@top5", youtube_channel_id="UCT5")
    db_session.add(channel)
    db_session.commit()

    now = datetime.now(timezone.utc)
    for i in range(10):
        video = Video(
            channel_id=channel.id,
            youtube_video_id=f"top{i}",
            title=f"Video {i}",
            published_at=now - timedelta(hours=i),
            views=(i + 1) * 1000,
            rank_score=float(i),
            processed=(i % 2 == 0),
        )
        db_session.add(video)
    db_session.commit()

    response = client.get("/api/feed")
    assert response.status_code == 200
    data = response.json()
    # All 10 videos are from this week (created just now)
    assert len(data["videos"]) == 10
    # Should be sorted by rank_score desc
    scores = [v["rank_score"] for v in data["videos"]]
    assert scores == sorted(scores, reverse=True)
    # Week metadata
    assert data["week"]["is_current_week"] is True
    assert data["week"]["total_videos"] == 10


def test_feed_week_start_param(client, db_session):
    channel = Channel(name="Test", youtube_handle="@wk", youtube_channel_id="UCW1")
    db_session.add(channel)
    db_session.commit()

    # Create a video last week
    last_monday = datetime.now(timezone.utc) - timedelta(days=7)
    # Snap to Monday
    last_monday = last_monday - timedelta(days=last_monday.weekday())
    last_monday = last_monday.replace(hour=12, minute=0, second=0, microsecond=0)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="lastweek1",
        title="Last Week Video",
        published_at=last_monday,
        rank_score=5.0,
        processed=False,
    )
    db_session.add(video)
    db_session.commit()

    # Query with last week's Monday
    week_start = last_monday.strftime("%Y-%m-%d")
    response = client.get(f"/api/feed?week_start={week_start}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["title"] == "Last Week Video"
    assert data["week"]["is_current_week"] is False


def test_feed_has_previous_week(client, db_session):
    channel = Channel(name="Test", youtube_handle="@prev", youtube_channel_id="UCP1")
    db_session.add(channel)
    db_session.commit()

    # A video from two weeks ago
    old_date = datetime.now(timezone.utc) - timedelta(days=14)
    video = Video(
        channel_id=channel.id,
        youtube_video_id="old1",
        title="Old Video",
        published_at=old_date,
        rank_score=3.0,
    )
    db_session.add(video)
    db_session.commit()

    # Current week feed should show has_previous_week=True
    response = client.get("/api/feed")
    data = response.json()
    assert data["week"]["has_previous_week"] is True


def test_feed_includes_unprocessed(client, db_session):
    channel = Channel(name="Test", youtube_handle="@unp", youtube_channel_id="UCU1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="unprocessed1",
        title="Unprocessed Video",
        published_at=datetime.now(timezone.utc),
        rank_score=5.0,
        processed=False,
    )
    db_session.add(video)
    db_session.commit()

    response = client.get("/api/feed")
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["title"] == "Unprocessed Video"
    assert data["videos"][0]["insight_count"] == 0


def test_unprocessed_endpoint(client, db_session):
    channel = Channel(name="Test", youtube_handle="@disc", youtube_channel_id="UCD1")
    db_session.add(channel)
    db_session.commit()

    processed = Video(
        channel_id=channel.id,
        youtube_video_id="proc1",
        title="Processed",
        published_at=datetime.now(timezone.utc),
        rank_score=3.0,
        processed=True,
    )
    unprocessed = Video(
        channel_id=channel.id,
        youtube_video_id="unproc1",
        title="Unprocessed",
        published_at=datetime.now(timezone.utc),
        rank_score=2.0,
        processed=False,
    )
    db_session.add_all([processed, unprocessed])
    db_session.commit()

    response = client.get("/api/videos/unprocessed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["title"] == "Unprocessed"


def test_unprocessed_empty_when_all_processed(client, db_session):
    channel = Channel(name="Test", youtube_handle="@all", youtube_channel_id="UCA1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="allproc",
        title="All Processed",
        published_at=datetime.now(timezone.utc),
        processed=True,
    )
    db_session.add(video)
    db_session.commit()

    response = client.get("/api/videos/unprocessed")
    data = response.json()
    assert data["videos"] == []


def test_all_videos_endpoint(client, db_session):
    channel = Channel(name="Test", youtube_handle="@allv", youtube_channel_id="UCAV")
    db_session.add(channel)
    db_session.commit()

    processed = Video(
        channel_id=channel.id,
        youtube_video_id="allv_proc",
        title="Processed Video",
        published_at=datetime.now(timezone.utc),
        rank_score=3.0,
        processed=True,
    )
    unprocessed = Video(
        channel_id=channel.id,
        youtube_video_id="allv_unproc",
        title="Unprocessed Video",
        published_at=datetime.now(timezone.utc),
        rank_score=2.0,
        processed=False,
    )
    db_session.add_all([processed, unprocessed])
    db_session.commit()

    response = client.get("/api/videos/all")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 2
    titles = {v["title"] for v in data["videos"]}
    assert "Processed Video" in titles
    assert "Unprocessed Video" in titles


def test_get_video_with_insights(client, db_session):
    channel = Channel(name="Test", youtube_handle="@detail", youtube_channel_id="UCF3")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="detail1",
        title="Detail Video",
        published_at=datetime.now(timezone.utc),
        processed=True,
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
            clip_url=f"/clips/clip_{i}.mp4",
            order=i,
        )
        db_session.add(insight)
    db_session.commit()

    response = client.get(f"/api/videos/{video.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Detail Video"
    assert len(data["insights"]) == 3
    assert data["insights"][0]["clip_url"] == "/clips/clip_0.mp4"
