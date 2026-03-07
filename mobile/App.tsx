import React from 'react';
import {StatusBar} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';

import FeedScreen from './src/screens/FeedScreen';
import InsightThreadScreen from './src/screens/InsightThreadScreen';
import ChannelsScreen from './src/screens/ChannelsScreen';

type RootStackParamList = {
  Feed: undefined;
  InsightThread: {videoId: number; title: string};
  Channels: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" />
      <NavigationContainer>
        <Stack.Navigator
          screenOptions={{
            headerStyle: {backgroundColor: '#0f0f23'},
            headerTintColor: '#fff',
            headerTitleStyle: {fontWeight: '600'},
          }}>
          <Stack.Screen
            name="Feed"
            component={FeedScreen}
            options={{title: 'InsightClips'}}
          />
          <Stack.Screen
            name="InsightThread"
            component={InsightThreadScreen}
            options={({route}) => ({
              title: route.params.title,
              headerBackTitle: 'Feed',
            })}
          />
          <Stack.Screen
            name="Channels"
            component={ChannelsScreen}
            options={{title: 'Channels'}}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

export default App;
