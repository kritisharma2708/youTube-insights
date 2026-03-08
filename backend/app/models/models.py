from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    youtube_handle = Column(String, unique=True, nullable=False)
    youtube_channel_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    videos = relationship("Video", back_populates="channel")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    youtube_video_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    duration = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    rank_score = Column(Float, default=0.0)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    channel = relationship("Channel", back_populates="videos")
    insights = relationship("Insight", back_populates="video")


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    insight_text = Column(Text, nullable=False)
    source_quote = Column(Text, nullable=True)  # verbatim transcript text
    category = Column(String, nullable=False)  # takeaway, action, quote
    start_timestamp = Column(Float, nullable=False)  # seconds
    end_timestamp = Column(Float, nullable=False)  # seconds
    clip_url = Column(String, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    video = relationship("Video", back_populates="insights")
