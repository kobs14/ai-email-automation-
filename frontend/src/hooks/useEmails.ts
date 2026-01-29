import { useQuery } from '@tanstack/react-query';
import { getEmails, getEmailById } from '../api/emails';
import type { EmailListParams } from '../types/email';

export function useEmails(params: EmailListParams = {}) {
  return useQuery({
    queryKey: ['emails', params],
    queryFn: () => getEmails(params),
  });
}

export function useEmail(id: number) {
  return useQuery({
    queryKey: ['emails', id],
    queryFn: () => getEmailById(id),
    enabled: id > 0,
  });
}
