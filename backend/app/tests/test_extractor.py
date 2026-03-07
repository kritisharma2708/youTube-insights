import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.models.models import Channel, Video
from app.services.extractor import extract_insights, parse_claude_response


SAMPLE_CLAUDE_RESPONSE = json.dumps({
    "video_type": "podcast_interview",
    "summary_style": "key_takeaways",
    "insights": [
        {
            "insight_text": "Product-market fit is not a moment, it's a spectrum",
            "category": "takeaway",
            "start_timestamp": 120.0,
            "end_timestamp": 155.0,
        },
        {
            "insight_text": "Talk to 5 customers every week without exception",
            "category": "action",
            "start_timestamp": 340.0,
            "end_timestamp": 380.0,
        },
        {
            "insight_text": "The best founders I know are the ones who can hold two contradictory ideas at once",
            "category": "quote",
            "start_timestamp": 600.0,
            "end_timestamp": 625.0,
        },
    ],
})


def test_parse_claude_response():
    insights = parse_claude_response(SAMPLE_CLAUDE_RESPONSE)
    assert len(insights) == 3
    assert insights[0]["category"] == "takeaway"
    assert insights[1]["category"] == "action"
    assert insights[2]["category"] == "quote"
    assert insights[0]["start_timestamp"] == 120.0


def test_parse_claude_response_invalid_json():
    insights = parse_claude_response("not json")
    assert insights == []


def test_parse_claude_response_missing_insights():
    insights = parse_claude_response(json.dumps({"video_type": "podcast"}))
    assert insights == []


@patch("app.services.extractor.get_transcript")
@patch("app.services.extractor.call_claude")
def test_extract_insights(mock_claude, mock_transcript, db_session):
    channel = Channel(name="Test", youtube_handle="@ext", youtube_channel_id="UCE1")
    db_session.add(channel)
    db_session.commit()

    video = Video(
        channel_id=channel.id,
        youtube_video_id="extract1",
        title="Extract Test",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video)
    db_session.commit()

    mock_transcript.return_value = "This is the transcript text..."
    mock_claude.return_value = SAMPLE_CLAUDE_RESPONSE

    insights = extract_insights(db_session, video.id)
    assert len(insights) == 3
    assert insights[0].order == 0
    assert insights[1].order == 1
    assert insights[2].order == 2

    db_session.refresh(video)
    assert video.processed is True
