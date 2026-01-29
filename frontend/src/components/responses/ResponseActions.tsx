import { useState } from 'react';
import { Check, X, RotateCcw, Pencil } from 'lucide-react';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { useAuth } from '../../auth/useAuth';

interface ResponseActionsProps {
  status: string;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
  onEdit?: () => void;
  isLoading?: boolean;
}

export function ResponseActions({
  status,
  onApprove,
  onReject,
  onRetry,
  onEdit,
  isLoading,
}: ResponseActionsProps) {
  const { isOperator } = useAuth();
  const [confirmAction, setConfirmAction] = useState<'approve' | 'reject' | null>(null);

  if (!isOperator) return null;

  return (
    <>
      <div className="flex items-center gap-2">
        {(status === 'draft' || status === 'rejected') && onEdit && (
          <button
            onClick={onEdit}
            disabled={isLoading}
            className="btn-secondary text-xs py-1 px-2 flex items-center gap-1"
            aria-label="Edit response"
          >
            <Pencil className="w-3.5 h-3.5" />
            Edit
          </button>
        )}
        {status === 'draft' && (
          <>
            <button
              onClick={() => setConfirmAction('approve')}
              disabled={isLoading}
              className="btn-success text-xs py-1 px-2 flex items-center gap-1"
              aria-label="Approve response"
            >
              <Check className="w-3.5 h-3.5" />
              Approve
            </button>
            <button
              onClick={() => setConfirmAction('reject')}
              disabled={isLoading}
              className="btn-secondary text-xs py-1 px-2 flex items-center gap-1"
              aria-label="Reject response"
            >
              <X className="w-3.5 h-3.5" />
              Reject
            </button>
          </>
        )}
        {status === 'failed' && onRetry && (
          <button
            onClick={onRetry}
            disabled={isLoading}
            className="btn-primary text-xs py-1 px-2 flex items-center gap-1"
            aria-label="Retry sending"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
      </div>

      <ConfirmDialog
        open={confirmAction === 'approve'}
        title="Approve Response"
        message="Are you sure you want to approve this response? It will be queued for sending."
        confirmLabel="Approve"
        onConfirm={() => {
          setConfirmAction(null);
          onApprove?.();
        }}
        onCancel={() => setConfirmAction(null)}
      />

      <ConfirmDialog
        open={confirmAction === 'reject'}
        title="Reject Response"
        message="Are you sure you want to reject this response?"
        confirmLabel="Reject"
        variant="danger"
        onConfirm={() => {
          setConfirmAction(null);
          onReject?.();
        }}
        onCancel={() => setConfirmAction(null)}
      />
    </>
  );
}
