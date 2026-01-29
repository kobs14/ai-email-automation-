import { useQuery } from '@tanstack/react-query';
import { getOverview, getIntents, getProcessingTimeline } from '../api/stats';

export function useOverview() {
  return useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: getOverview,
    refetchInterval: 60000,
  });
}

export function useIntents() {
  return useQuery({
    queryKey: ['stats', 'intents'],
    queryFn: getIntents,
  });
}

export function useProcessingTimeline(days: number = 7) {
  return useQuery({
    queryKey: ['stats', 'processing', days],
    queryFn: () => getProcessingTimeline(days),
  });
}
