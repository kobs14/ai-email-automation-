import { StatusBadge } from '../common/Badge';
import type { ResponseRecord } from '../../types/response';

interface ResponseCardProps {
  response: ResponseRecord;
  actions?: React.ReactNode;
}

export function ResponseCard({ response, actions }: ResponseCardProps) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={response.status} />
            {response.intent && (
              <span className="text-xs text-gray-500">{response.intent.replace(/_/g, ' ')}</span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900 truncate">
            {response.subject || `Response #${response.id}`}
          </p>
          <p className="text-sm text-gray-600 truncate">
            To: {response.from_address || 'Unknown'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Created: {new Date(response.created_at).toLocaleString()}
          </p>
        </div>
        {actions && <div className="flex-shrink-0">{actions}</div>}
      </div>

      <div className="mt-3 text-sm text-gray-700 bg-gray-50 rounded-lg p-3 line-clamp-3 whitespace-pre-wrap">
        {response.draft_content}
      </div>

      {response.send_error && (
        <p className="mt-2 text-xs text-red-600">
          Error: {response.send_error} (Attempts: {response.send_attempts})
        </p>
      )}
    </div>
  );
}
