import React from 'react';
import {View, Text, StyleSheet, FlatList} from 'react-native';

const CHANNELS = [
  {
    id: 1,
    name: "Lenny's Podcast",
    handle: '@LennysPodcast',
    description: 'Product, growth, startups',
  },
  {
    id: 2,
    name: 'Think School',
    handle: '@ThinkSchool',
    description: 'Business case studies, Indian market',
  },
  {
    id: 3,
    name: 'Dwarkesh Patel',
    handle: '@DwarkeshPatel',
    description: 'Deep intellectual interviews, AI, history',
  },
];

const ChannelsScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.header}>Following</Text>
      <FlatList
        data={CHANNELS}
        keyExtractor={item => item.id.toString()}
        renderItem={({item}) => (
          <View style={styles.channelCard}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{item.name[0]}</Text>
            </View>
            <View style={styles.info}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.handle}>{item.handle}</Text>
              <Text style={styles.description}>{item.description}</Text>
            </View>
          </View>
        )}
        contentContainerStyle={styles.list}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f23',
  },
  header: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '700',
    padding: 20,
    paddingBottom: 10,
  },
  list: {
    paddingHorizontal: 16,
  },
  channelCard: {
    flexDirection: 'row',
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    padding: 16,
    marginVertical: 6,
    alignItems: 'center',
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#4CAF50',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  avatarText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
  },
  info: {
    flex: 1,
  },
  name: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  handle: {
    color: '#888',
    fontSize: 13,
    marginTop: 2,
  },
  description: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
});

export default ChannelsScreen;
