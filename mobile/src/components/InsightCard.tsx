import React from 'react';
import {View, Text, StyleSheet, Dimensions, TouchableOpacity} from 'react-native';
import Video from 'react-native-video';
import {Insight} from '../types';

const {width, height} = Dimensions.get('window');

interface InsightCardProps {
  insight: Insight;
  onShare?: (insight: Insight) => void;
}

const categoryColors: Record<string, string> = {
  takeaway: '#4CAF50',
  action: '#2196F3',
  quote: '#FF9800',
};

const categoryLabels: Record<string, string> = {
  takeaway: 'Key Takeaway',
  action: 'Action Item',
  quote: 'Notable Quote',
};

const formatTimestamp = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const InsightCard: React.FC<InsightCardProps> = ({insight, onShare}) => {
  const categoryColor = categoryColors[insight.category] || '#666';

  return (
    <View style={styles.card}>
      {insight.clip_url ? (
        <View style={styles.videoContainer}>
          <Video
            source={{uri: insight.clip_url}}
            style={styles.video}
            resizeMode="cover"
            repeat
            muted
            controls
          />
        </View>
      ) : (
        <View style={[styles.videoPlaceholder, {backgroundColor: '#1a1a2e'}]}>
          <Text style={styles.placeholderText}>Clip generating...</Text>
        </View>
      )}

      <View style={styles.content}>
        <View style={styles.header}>
          <View
            style={[styles.categoryBadge, {backgroundColor: categoryColor}]}>
            <Text style={styles.categoryText}>
              {categoryLabels[insight.category] || insight.category}
            </Text>
          </View>
          <Text style={styles.timestamp}>
            {formatTimestamp(insight.start_timestamp)} -{' '}
            {formatTimestamp(insight.end_timestamp)}
          </Text>
        </View>

        <Text style={styles.insightText}>{insight.insight_text}</Text>

        {onShare && (
          <TouchableOpacity
            style={styles.shareButton}
            onPress={() => onShare(insight)}>
            <Text style={styles.shareText}>Share</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    width: width,
    height: height - 100,
    backgroundColor: '#0f0f23',
  },
  videoContainer: {
    flex: 0.6,
    backgroundColor: '#000',
  },
  video: {
    flex: 1,
  },
  videoPlaceholder: {
    flex: 0.6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    color: '#666',
    fontSize: 16,
  },
  content: {
    flex: 0.4,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  categoryBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  categoryText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  timestamp: {
    color: '#888',
    fontSize: 13,
  },
  insightText: {
    color: '#fff',
    fontSize: 18,
    lineHeight: 28,
    fontWeight: '500',
  },
  shareButton: {
    marginTop: 20,
    alignSelf: 'flex-end',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#444',
  },
  shareText: {
    color: '#fff',
    fontSize: 14,
  },
});

export default InsightCard;
