import { StatusBadge } from '../common/Badge';
import type { EmailDetail as EmailDetailType } from '../../types/email';

interface EmailDetailProps {
  email: EmailDetailType;
}

export function EmailDetailView({ email }: EmailDetailProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{email.subject}</h2>
            <p className="text-sm text-gray-600 mt-1">From: {email.from_address}</p>
            <p className="text-sm text-gray-500 mt-1">
              Received: {new Date(email.received_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={email.status} />
            {email.intent && <StatusBadge status={email.intent.replace(/_/g, ' ')} />}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="card p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Email Body</h3>
        <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-4">
          {email.body || 'No content'}
        </div>
      </div>

      {/* Entities */}
      {email.entities.length > 0 && (
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Extracted Entities</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {email.entities.map((entity) => (
              <div key={entity.id} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs font-medium text-gray-500 uppercase">{entity.entity_type.replace(/_/g, ' ')}</p>
                <p className="text-sm font-medium text-gray-900 mt-1">{entity.entity_value}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Confidence: {(entity.confidence * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Response */}
      {email.response && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Response Draft</h3>
            <StatusBadge status={email.response.status} />
          </div>
          <div className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded-lg p-4">
            {email.response.draft_content}
          </div>
          {email.response.approved_by && (
            <p className="text-xs text-gray-500 mt-2">
              Approved by: {email.response.approved_by}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
