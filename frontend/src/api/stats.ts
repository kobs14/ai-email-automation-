import client from './client';
import type { OverviewStats, IntentStat, ProcessingDay } from '../types/stats';

export async function getOverview(): Promise<OverviewStats> {
  const response = await client.get('/stats/overview');
  return response.data;
}

export async function getIntents(): Promise<{ items: IntentStat[] }> {
  const response = await client.get('/stats/intents');
  return response.data;
}

export async function getProcessingTimeline(days: number = 7): Promise<{ items: ProcessingDay[]; days: number }> {
  const response = await client.get('/stats/processing', { params: { days } });
  return response.data;
}
