import React from 'react';
import {View, Text, Image, StyleSheet, TouchableOpacity} from 'react-native';
import {VideoSummary} from '../types';

interface VideoCardProps {
  video: VideoSummary;
  onPress: (video: VideoSummary) => void;
}

const formatViews = (views: number): string => {
  if (views >= 1000000) return `${(views / 1000000).toFixed(1)}M views`;
  if (views >= 1000) return `${(views / 1000).toFixed(1)}K views`;
  return `${views} views`;
};

const VideoCard: React.FC<VideoCardProps> = ({video, onPress}) => {
  return (
    <TouchableOpacity style={styles.card} onPress={() => onPress(video)}>
      {video.thumbnail_url ? (
        <Image source={{uri: video.thumbnail_url}} style={styles.thumbnail} />
      ) : (
        <View style={[styles.thumbnail, styles.placeholderThumb]} />
      )}
      <View style={styles.info}>
        <Text style={styles.title} numberOfLines={2}>
          {video.title}
        </Text>
        <Text style={styles.channel}>{video.channel_name}</Text>
        <View style={styles.meta}>
          <Text style={styles.views}>{formatViews(video.views)}</Text>
          <Text style={styles.insights}>
            {video.insight_count} insights
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    marginHorizontal: 16,
    marginVertical: 8,
    overflow: 'hidden',
  },
  thumbnail: {
    width: '100%',
    height: 200,
    backgroundColor: '#2d2d44',
  },
  placeholderThumb: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: {
    padding: 14,
  },
  title: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 6,
  },
  channel: {
    color: '#888',
    fontSize: 13,
    marginBottom: 8,
  },
  meta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  views: {
    color: '#666',
    fontSize: 12,
  },
  insights: {
    color: '#4CAF50',
    fontSize: 12,
    fontWeight: '600',
  },
});

export default VideoCard;
