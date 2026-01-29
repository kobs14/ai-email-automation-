import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getResponses,
  getPendingResponses,
  getFailedResponses,
  getResponseById,
  updateResponseContent,
  approveResponse,
  rejectResponse,
  retryResponse,
} from '../api/responses';
import type { ResponseListParams } from '../types/response';
import toast from 'react-hot-toast';

export function useResponses(params: ResponseListParams = {}) {
  return useQuery({
    queryKey: ['responses', params],
    queryFn: () => getResponses(params),
  });
}

export function usePendingResponses() {
  return useQuery({
    queryKey: ['responses', 'pending'],
    queryFn: getPendingResponses,
    refetchInterval: 30000,
  });
}

export function useFailedResponses() {
  return useQuery({
    queryKey: ['responses', 'failed'],
    queryFn: getFailedResponses,
  });
}

export function useResponse(id: number) {
  return useQuery({
    queryKey: ['responses', id],
    queryFn: () => getResponseById(id),
    enabled: id > 0,
  });
}

export function useUpdateContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: number; content: string }) =>
      updateResponseContent(id, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['responses'] });
      toast.success('Response content updated');
    },
    onError: () => toast.error('Failed to update response'),
  });
}

export function useApproveResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => approveResponse(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['responses'] });
      toast.success('Response approved');
    },
    onError: () => toast.error('Failed to approve response'),
  });
}

export function useRejectResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => rejectResponse(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['responses'] });
      toast.success('Response rejected');
    },
    onError: () => toast.error('Failed to reject response'),
  });
}

export function useRetryResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => retryResponse(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['responses'] });
      toast.success('Response reset for retry');
    },
    onError: () => toast.error('Failed to retry response'),
  });
}
