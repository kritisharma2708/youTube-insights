from datetime import datetime, timezone

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
    assert data["page"] == 1


def test_feed_with_videos(client, db_session):
    channel = Channel(name="Test", youtube_handle="@feed", youtube_channel_id="UCF1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="feed1",
        title="Feed Video",
        published_at=datetime.now(timezone.utc),
        views=5000,
        likes=500,
        comments=100,
        thumbnail_url="https://img.youtube.com/vi/feed1/0.jpg",
        rank_score=0.9,
        processed=True,
    )
    db_session.add(video)
    db_session.commit()

    insight = Insight(
        video_id=video.id,
        insight_text="Test insight",
        category="takeaway",
        start_timestamp=10.0,
        end_timestamp=30.0,
        order=0,
    )
    db_session.add(insight)
    db_session.commit()

    response = client.get("/api/feed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["title"] == "Feed Video"
    assert data["videos"][0]["insight_count"] == 1
    assert data["videos"][0]["channel_name"] == "Test"


def test_feed_pagination(client, db_session):
    channel = Channel(name="Test", youtube_handle="@page", youtube_channel_id="UCF2")
    db_session.add(channel)
    db_session.commit()

    for i in range(15):
        video = Video(
            channel_id=channel.id,
            youtube_video_id=f"page{i}",
            title=f"Video {i}",
            published_at=datetime.now(timezone.utc),
            rank_score=float(15 - i),
            processed=True,
        )
        db_session.add(video)
    db_session.commit()

    response = client.get("/api/feed?page=1&per_page=10")
    data = response.json()
    assert len(data["videos"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] == 2

    response = client.get("/api/feed?page=2&per_page=10")
    data = response.json()
    assert len(data["videos"]) == 5


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
