import React, {useEffect, useState} from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  Text,
  ActivityIndicator,
  Dimensions,
  Share,
} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {getVideo} from '../services/api';
import {Insight, VideoDetail} from '../types';
import InsightCard from '../components/InsightCard';

const {height} = Dimensions.get('window');

type RootStackParamList = {
  Feed: undefined;
  InsightThread: {videoId: number; title: string};
  Channels: undefined;
};

type Props = NativeStackScreenProps<RootStackParamList, 'InsightThread'>;

const InsightThreadScreen: React.FC<Props> = ({route}) => {
  const {videoId} = route.params;
  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadVideo = async () => {
      try {
        const data = await getVideo(videoId);
        setVideo(data);
      } catch (error) {
        console.error('Failed to load video:', error);
      } finally {
        setLoading(false);
      }
    };
    loadVideo();
  }, [videoId]);

  const onShare = async (insight: Insight) => {
    try {
      await Share.share({
        message: `${insight.insight_text}\n\nFrom: ${video?.title}`,
      });
    } catch (error) {
      console.error('Share failed:', error);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  if (!video || video.insights.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>No insights available</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={video.insights}
        keyExtractor={item => item.id.toString()}
        renderItem={({item}) => (
          <InsightCard insight={item} onShare={onShare} />
        )}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        snapToInterval={height - 100}
        decelerationRate="fast"
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f23',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f0f23',
  },
  emptyText: {
    color: '#888',
    fontSize: 16,
  },
});

export default InsightThreadScreen;
