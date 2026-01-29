import client from './client';
import type { Email, EmailDetail, EmailListParams, Entity } from '../types/email';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export async function getEmails(params: EmailListParams = {}): Promise<PaginatedResponse<Email>> {
  const response = await client.get('/emails', { params });
  return response.data;
}

export async function getEmailById(id: number): Promise<EmailDetail> {
  const response = await client.get(`/emails/${id}`);
  return response.data;
}

export async function getEmailEntities(id: number): Promise<{ items: Entity[] }> {
  const response = await client.get(`/emails/${id}/entities`);
  return response.data;
}
