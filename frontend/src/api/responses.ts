import client from './client';
import type { ResponseRecord, ResponseWithEmail, ResponseListParams } from '../types/response';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export async function getResponses(params: ResponseListParams = {}): Promise<PaginatedResponse<ResponseRecord>> {
  const response = await client.get('/responses', { params });
  return response.data;
}

export async function getPendingResponses(): Promise<{ items: ResponseRecord[] }> {
  const response = await client.get('/responses/pending');
  return response.data;
}

export async function getFailedResponses(): Promise<{ items: ResponseRecord[] }> {
  const response = await client.get('/responses/failed');
  return response.data;
}

export async function getResponseById(id: number): Promise<ResponseWithEmail> {
  const response = await client.get(`/responses/${id}`);
  return response.data;
}

export async function updateResponseContent(id: number, content: string): Promise<void> {
  await client.put(`/responses/${id}/content`, { content });
}

export async function approveResponse(id: number): Promise<void> {
  await client.post(`/responses/${id}/approve`);
}

export async function rejectResponse(id: number): Promise<void> {
  await client.post(`/responses/${id}/reject`);
}

export async function retryResponse(id: number): Promise<void> {
  await client.post(`/responses/${id}/retry`);
}
