import client from './client';
import type { ConfigValue } from '../types/config';

export async function getAllConfig(): Promise<{ items: Record<string, ConfigValue> }> {
  const response = await client.get('/config');
  return response.data;
}

export async function getConfig(key: string): Promise<{ key: string; value: ConfigValue }> {
  const response = await client.get(`/config/${key}`);
  return response.data;
}

export async function updateConfig(key: string, value: ConfigValue): Promise<void> {
  await client.put(`/config/${key}`, { value });
}
