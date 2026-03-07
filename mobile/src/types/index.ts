export interface Channel {
  id: number;
  name: string;
  youtube_handle: string;
  youtube_channel_id: string | null;
  created_at: string;
}

export interface Insight {
  id: number;
  insight_text: string;
  category: 'takeaway' | 'action' | 'quote';
  start_timestamp: number;
  end_timestamp: number;
  clip_url: string | null;
  order: number;
}

export interface VideoSummary {
  id: number;
  youtube_video_id: string;
  title: string;
  published_at: string;
  views: number;
  thumbnail_url: string | null;
  rank_score: number;
  channel_name: string;
  insight_count: number;
}

export interface VideoDetail {
  id: number;
  youtube_video_id: string;
  title: string;
  published_at: string;
  views: number;
  likes: number;
  comments: number;
  duration: string | null;
  thumbnail_url: string | null;
  rank_score: number;
  processed: boolean;
  channel: Channel;
  insights: Insight[];
}

export interface FeedResponse {
  videos: VideoSummary[];
  page: number;
  total_pages: number;
}
