from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ChannelBase(BaseModel):
    name: str
    youtube_handle: str


class ChannelResponse(ChannelBase):
    id: int
    youtube_channel_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightResponse(BaseModel):
    id: int
    insight_text: str
    source_quote: Optional[str] = None
    category: str
    start_timestamp: float
    end_timestamp: float
    clip_url: Optional[str]
    order: int

    model_config = {"from_attributes": True}


class VideoResponse(BaseModel):
    id: int
    youtube_video_id: str
    title: str
    published_at: datetime
    views: int
    likes: int
    comments: int
    duration: Optional[str]
    thumbnail_url: Optional[str]
    rank_score: float
    processed: bool
    channel: ChannelResponse
    insights: List[InsightResponse] = []

    model_config = {"from_attributes": True}


class VideoSummary(BaseModel):
    id: int
    youtube_video_id: str
    title: str
    published_at: datetime
    views: int
    thumbnail_url: Optional[str]
    rank_score: float
    channel_name: str
    insight_count: int

    model_config = {"from_attributes": True}


class FeedResponse(BaseModel):
    videos: List[VideoSummary]
    page: int
    total_pages: int


class WeekSummary(BaseModel):
    week_start: str
    week_end: str
    week_label: str
    total_videos: int
    videos_with_insights: int
    has_previous_week: bool
    is_current_week: bool


class WeekFeedResponse(BaseModel):
    videos: List[VideoSummary]
    week: WeekSummary
