import { ResponseCard } from './ResponseCard';
import { ResponseActions } from './ResponseActions';
import { EmptyState } from '../common/EmptyState';
import type { ResponseRecord } from '../../types/response';
import { AlertCircle } from 'lucide-react';

interface FailedResponseListProps {
  responses: ResponseRecord[];
  onRetry: (id: number) => void;
  isLoading?: boolean;
}

export function FailedResponseList({ responses, onRetry, isLoading }: FailedResponseListProps) {
  if (responses.length === 0) {
    return (
      <EmptyState
        title="No failed responses"
        description="All responses have been sent successfully."
        icon={<AlertCircle className="w-12 h-12" />}
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
              status="failed"
              onRetry={() => onRetry(response.id)}
              isLoading={isLoading}
            />
          }
        />
      ))}
    </div>
  );
}
