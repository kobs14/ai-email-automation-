import { ResponseCard } from './ResponseCard';
import { ResponseActions } from './ResponseActions';
import { EmptyState } from '../common/EmptyState';
import type { ResponseRecord } from '../../types/response';
import { MessageSquare } from 'lucide-react';

interface ResponseListProps {
  responses: ResponseRecord[];
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
  onRetry?: (id: number) => void;
  onEdit?: (id: number) => void;
  isLoading?: boolean;
}

export function ResponseList({
  responses,
  onApprove,
  onReject,
  onRetry,
  onEdit,
  isLoading,
}: ResponseListProps) {
  if (responses.length === 0) {
    return (
      <EmptyState
        title="No responses"
        description="No responses match the current filter."
        icon={<MessageSquare className="w-12 h-12" />}
      />
    );
  }

  return (
    <div className="space-y-3">
      {responses.map((response) => (
        <ResponseCard
          key={response.id}
          response={response}
          actions={
            <ResponseActions
              status={response.status}
              onApprove={() => onApprove?.(response.id)}
              onReject={() => onReject?.(response.id)}
              onRetry={() => onRetry?.(response.id)}
              onEdit={() => onEdit?.(response.id)}
              isLoading={isLoading}
            />
          }
        />
      ))}
    </div>
  );
}
