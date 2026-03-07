import React from 'react';
import {render, fireEvent} from '@testing-library/react-native';
import VideoCard from '../src/components/VideoCard';
import {VideoSummary} from '../src/types';

const mockVideo: VideoSummary = {
  id: 1,
  youtube_video_id: 'abc123',
  title: 'How to Build Product-Market Fit',
  published_at: '2026-03-01T00:00:00Z',
  views: 150000,
  thumbnail_url: 'https://img.youtube.com/vi/abc123/0.jpg',
  rank_score: 0.95,
  channel_name: "Lenny's Podcast",
  insight_count: 7,
};

describe('VideoCard', () => {
  it('renders video title and channel name', () => {
    const onPress = jest.fn();
    const {getByText} = render(
      <VideoCard video={mockVideo} onPress={onPress} />,
    );

    expect(getByText('How to Build Product-Market Fit')).toBeTruthy();
    expect(getByText("Lenny's Podcast")).toBeTruthy();
    expect(getByText('7 insights')).toBeTruthy();
  });

  it('formats views correctly', () => {
    const onPress = jest.fn();
    const {getByText} = render(
      <VideoCard video={mockVideo} onPress={onPress} />,
    );

    expect(getByText('150.0K views')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    const {getByText} = render(
      <VideoCard video={mockVideo} onPress={onPress} />,
    );

    fireEvent.press(getByText('How to Build Product-Market Fit'));
    expect(onPress).toHaveBeenCalledWith(mockVideo);
  });
});
