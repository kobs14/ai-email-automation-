import { useState } from 'react';
import { useEmails } from '../hooks/useEmails';
import { usePagination } from '../hooks/usePagination';
import { EmailTable } from '../components/emails/EmailTable';
import { EmailFilters } from '../components/emails/EmailFilters';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { EmptyState } from '../components/common/EmptyState';
import { Mail } from 'lucide-react';

export function EmailsPage() {
  const [status, setStatus] = useState('');
  const [intent, setIntent] = useState('');
  const [search, setSearch] = useState('');
  const { page, perPage, goToPage, resetPage } = usePagination();

  const { data, isLoading, error, refetch } = useEmails({
    page,
    per_page: perPage,
    status: (status || null) as import('../types/email').EmailStatus | null,
    intent: (intent || null) as import('../types/email').EmailIntent | null,
    search: search || undefined,
  });

  const handleStatusChange = (s: string) => {
    setStatus(s);
    resetPage();
  };
  const handleIntentChange = (i: string) => {
    setIntent(i);
    resetPage();
  };
  const handleSearchChange = (s: string) => {
    setSearch(s);
    resetPage();
  };

  return (
    <div>
      <EmailFilters
        status={status}
        intent={intent}
        search={search}
        onStatusChange={handleStatusChange}
        onIntentChange={handleIntentChange}
        onSearchChange={handleSearchChange}
      />

      {error && <ErrorAlert message="Failed to load emails" onRetry={refetch} />}

      {isLoading ? (
        <div className="card p-4">
          <TableSkeleton rows={8} />
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="card">
          <EmailTable emails={data.items} />
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            perPage={data.per_page}
            onPageChange={goToPage}
          />
        </div>
      ) : (
        <EmptyState
          title="No emails found"
          description="Adjust your filters or wait for new emails to arrive."
          icon={<Mail className="w-12 h-12" />}
        />
      )}
    </div>
  );
}
