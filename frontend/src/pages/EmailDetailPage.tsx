import { useParams } from 'react-router-dom';
import { useEmail } from '../hooks/useEmails';
import { EmailDetailView } from '../components/emails/EmailDetail';
import { Breadcrumb } from '../components/layout/Breadcrumb';
import { PageLoader } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';

export function EmailDetailPage() {
  const { id } = useParams<{ id: string }>();
  const emailId = parseInt(id || '0', 10);
  const { data, isLoading, error, refetch } = useEmail(emailId);

  if (isLoading) return <PageLoader />;
  if (error || !data) return <ErrorAlert message="Failed to load email" onRetry={refetch} />;

  return (
    <div>
      <Breadcrumb items={[
        { label: 'Emails', to: '/emails' },
        { label: data.subject || `Email #${emailId}` },
      ]} />
      <EmailDetailView email={data} />
    </div>
  );
}
