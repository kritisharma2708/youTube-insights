import axios from 'axios';
import {FeedResponse, VideoDetail} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const getFeed = async (
  page: number = 1,
  perPage: number = 10,
): Promise<FeedResponse> => {
  const response = await api.get('/feed', {
    params: {page, per_page: perPage},
  });
  return response.data;
};

export const getVideo = async (videoId: number): Promise<VideoDetail> => {
  const response = await api.get(`/videos/${videoId}`);
  return response.data;
};

export const extractInsights = async (
  videoId: number,
): Promise<{message: string; insight_count: number}> => {
  const response = await api.post(`/videos/${videoId}/extract`);
  return response.data;
};

export const generateClips = async (
  videoId: number,
): Promise<{message: string; video_id: number}> => {
  const response = await api.post(`/videos/${videoId}/clips`);
  return response.data;
};
