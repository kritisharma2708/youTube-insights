import React, {useEffect, useState, useCallback} from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  Text,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {getFeed} from '../services/api';
import {VideoSummary} from '../types';
import VideoCard from '../components/VideoCard';

type RootStackParamList = {
  Feed: undefined;
  InsightThread: {videoId: number; title: string};
  Channels: undefined;
};

type FeedScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Feed'>;
};

const FeedScreen: React.FC<FeedScreenProps> = ({navigation}) => {
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const loadFeed = useCallback(async (pageNum: number, refresh = false) => {
    try {
      const data = await getFeed(pageNum);
      if (refresh) {
        setVideos(data.videos);
      } else {
        setVideos(prev => [...prev, ...data.videos]);
      }
      setTotalPages(data.total_pages);
    } catch (error) {
      console.error('Failed to load feed:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFeed(1, true);
  }, [loadFeed]);

  const onRefresh = () => {
    setRefreshing(true);
    setPage(1);
    loadFeed(1, true);
  };

  const onEndReached = () => {
    if (page < totalPages) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadFeed(nextPage);
    }
  };

  const onVideoPress = (video: VideoSummary) => {
    navigation.navigate('InsightThread', {
      videoId: video.id,
      title: video.title,
    });
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Loading insights...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={videos}
        keyExtractor={item => item.id.toString()}
        renderItem={({item}) => (
          <VideoCard video={item} onPress={onVideoPress} />
        )}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#4CAF50"
          />
        }
        onEndReached={onEndReached}
        onEndReachedThreshold={0.5}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.center}>
            <Text style={styles.emptyText}>No videos yet</Text>
            <Text style={styles.emptySubtext}>
              Pull to refresh or check back later
            </Text>
          </View>
        }
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
  loadingText: {
    color: '#888',
    marginTop: 12,
    fontSize: 14,
  },
  list: {
    paddingVertical: 8,
  },
  emptyText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  emptySubtext: {
    color: '#666',
    fontSize: 14,
    marginTop: 8,
  },
});

export default FeedScreen;
