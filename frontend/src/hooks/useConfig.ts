import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAllConfig, getConfig, updateConfig } from '../api/config';
import type { ConfigValue } from '../types/config';
import toast from 'react-hot-toast';

export function useAllConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: getAllConfig,
  });
}

export function useConfigKey(key: string) {
  return useQuery({
    queryKey: ['config', key],
    queryFn: () => getConfig(key),
    enabled: !!key,
  });
}

export function useUpdateConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: ConfigValue }) =>
      updateConfig(key, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
      toast.success('Configuration updated');
    },
    onError: () => toast.error('Failed to update configuration'),
  });
}
