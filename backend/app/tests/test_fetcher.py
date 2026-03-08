from app.services.fetcher import parse_iso8601_duration


def test_parse_duration_full():
    assert parse_iso8601_duration("PT1H30M15S") == 5415


def test_parse_duration_minutes_seconds():
    assert parse_iso8601_duration("PT10M30S") == 630


def test_parse_duration_minutes_only():
    assert parse_iso8601_duration("PT45M") == 2700


def test_parse_duration_seconds_only():
    """A YouTube Short - e.g. 45 seconds."""
    assert parse_iso8601_duration("PT45S") == 45


def test_parse_duration_hours_only():
    assert parse_iso8601_duration("PT2H") == 7200


def test_parse_duration_empty():
    assert parse_iso8601_duration("") == 0


def test_parse_duration_invalid():
    assert parse_iso8601_duration("invalid") == 0


def test_short_video_is_under_threshold():
    """Shorts (under 3 min) should be filtered out."""
    from app.services.fetcher import MIN_DURATION_SECONDS
    assert parse_iso8601_duration("PT58S") < MIN_DURATION_SECONDS
    assert parse_iso8601_duration("PT2M30S") < MIN_DURATION_SECONDS


def test_long_video_is_above_threshold():
    """Regular videos (over 3 min) should pass the filter."""
    from app.services.fetcher import MIN_DURATION_SECONDS
    assert parse_iso8601_duration("PT10M30S") >= MIN_DURATION_SECONDS
    assert parse_iso8601_duration("PT1H17M25S") >= MIN_DURATION_SECONDS
