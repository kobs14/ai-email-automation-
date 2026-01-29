import { useQuery } from '@tanstack/react-query';
import { getEvents, getUpcomingEvents } from '../api/calendar';

export function useCalendarEvents(start?: string, end?: string) {
  return useQuery({
    queryKey: ['calendar', 'events', start, end],
    queryFn: () => getEvents(start, end),
  });
}

export function useUpcomingEvents(limit: number = 10) {
  return useQuery({
    queryKey: ['calendar', 'upcoming', limit],
    queryFn: () => getUpcomingEvents(limit),
  });
}
