import { useFailedResponses, useRetryResponse } from '../hooks/useResponses';
import { FailedResponseList } from '../components/responses/FailedResponseList';
import { PageLoader } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';

export function FailedResponsesPage() {
  const { data, isLoading, error, refetch } = useFailedResponses();
  const retryMutation = useRetryResponse();

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorAlert message="Failed to load failed responses" onRetry={refetch} />;

  return (
    <FailedResponseList
      responses={data?.items ?? []}
      onRetry={(id) => retryMutation.mutate(id)}
      isLoading={retryMutation.isPending}
    />
  );
}
