import { Link } from 'react-router-dom';
import { StatusBadge } from '../common/Badge';
import type { Email } from '../../types/email';

interface EmailTableProps {
  emails: Email[];
}

export function EmailTable({ emails }: EmailTableProps) {
  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="min-w-full">
          <caption className="sr-only">Email list</caption>
          <thead>
            <tr className="border-b border-gray-200">
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">From</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Subject</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Intent</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Received</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {emails.map((email) => (
              <tr key={email.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-sm">
                  <Link to={`/emails/${email.id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                    {email.from_address}
                  </Link>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate">{email.subject}</td>
                <td className="px-4 py-3"><StatusBadge status={email.status} /></td>
                <td className="px-4 py-3 text-sm text-gray-600">{email.intent?.replace(/_/g, ' ') || '-'}</td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {new Date(email.received_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {emails.map((email) => (
          <Link key={email.id} to={`/emails/${email.id}`} className="card block p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-blue-600 truncate">{email.from_address}</p>
                <p className="text-sm text-gray-700 truncate mt-1">{email.subject}</p>
              </div>
              <StatusBadge status={email.status} />
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
              <span>{email.intent?.replace(/_/g, ' ') || 'Unclassified'}</span>
              <span>{new Date(email.received_at).toLocaleDateString()}</span>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
