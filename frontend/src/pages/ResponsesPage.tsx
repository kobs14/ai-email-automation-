import { useState } from 'react';
import {
  useResponses,
  useApproveResponse,
  useRejectResponse,
  useUpdateContent,
} from '../hooks/useResponses';
import { usePagination } from '../hooks/usePagination';
import { ResponseList } from '../components/responses/ResponseList';
import { ResponseEditor } from '../components/responses/ResponseEditor';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import type { ResponseStatus } from '../types/response';

const TABS: { label: string; value: ResponseStatus | '' }[] = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'draft' },
  { label: 'Approved', value: 'approved' },
  { label: 'Sent', value: 'sent' },
  { label: 'Rejected', value: 'rejected' },
];

export function ResponsesPage() {
  const [activeTab, setActiveTab] = useState<ResponseStatus | ''>('draft');
  const [editingId, setEditingId] = useState<number | null>(null);
  const { page, perPage, goToPage, resetPage } = usePagination();

  const { data, isLoading, error, refetch } = useResponses({
    page,
    per_page: perPage,
    status: activeTab || null,
  });

  const approveMutation = useApproveResponse();
  const rejectMutation = useRejectResponse();
  const updateContentMutation = useUpdateContent();

  const handleTabChange = (tab: ResponseStatus | '') => {
    setActiveTab(tab);
    setEditingId(null);
    resetPage();
  };

  const editingResponse = editingId && data
    ? data.items.find((r) => r.id === editingId)
    : null;

  if (editingResponse) {
    return (
      <div>
        <ResponseEditor
          initialContent={editingResponse.draft_content}
          onSave={(content) => {
            updateContentMutation.mutate(
              { id: editingResponse.id, content },
              { onSuccess: () => setEditingId(null) }
            );
          }}
          onCancel={() => setEditingId(null)}
          isSaving={updateContentMutation.isPending}
        />
      </div>
    );
  }

  return (
    <div>
      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200 overflow-x-auto" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={activeTab === tab.value}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab.value
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => handleTabChange(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <ErrorAlert message="Failed to load responses" onRetry={refetch} />}

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : data ? (
        <>
          <ResponseList
            responses={data.items}
            onApprove={(id) => approveMutation.mutate(id)}
            onReject={(id) => rejectMutation.mutate(id)}
            onEdit={(id) => setEditingId(id)}
            isLoading={approveMutation.isPending || rejectMutation.isPending}
          />
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            perPage={data.per_page}
            onPageChange={goToPage}
          />
        </>
      ) : null}
    </div>
  );
}
