import client from './client';
import type { CalendarEvent } from '../types/calendar';

export async function getEvents(start?: string, end?: string): Promise<{ items: CalendarEvent[] }> {
  const params: Record<string, string> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  const response = await client.get('/calendar/events', { params });
  return response.data;
}

export async function getUpcomingEvents(limit: number = 10): Promise<{ items: CalendarEvent[] }> {
  const response = await client.get('/calendar/events/upcoming', { params: { limit } });
  return response.data;
}

export async function getEventById(id: number): Promise<CalendarEvent> {
  const response = await client.get(`/calendar/events/${id}`);
  return response.data;
}
