interface EmailFiltersProps {
  status: string;
  intent: string;
  search: string;
  onStatusChange: (status: string) => void;
  onIntentChange: (intent: string) => void;
  onSearchChange: (search: string) => void;
}

const STATUS_OPTIONS = ['', 'pending', 'classified', 'responded', 'failed'];
const INTENT_OPTIONS = ['', 'quote_request', 'booking_request', 'rescheduling', 'complaint', 'general_inquiry'];

export function EmailFilters({
  status,
  intent,
  search,
  onStatusChange,
  onIntentChange,
  onSearchChange,
}: EmailFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-4">
      <div className="flex-1">
        <label htmlFor="email-search" className="sr-only">Search emails</label>
        <input
          id="email-search"
          type="text"
          placeholder="Search by sender or subject..."
          className="input-field"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="email-status" className="sr-only">Filter by status</label>
        <select
          id="email-status"
          className="input-field"
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="email-intent" className="sr-only">Filter by intent</label>
        <select
          id="email-intent"
          className="input-field"
          value={intent}
          onChange={(e) => onIntentChange(e.target.value)}
        >
          <option value="">All intents</option>
          {INTENT_OPTIONS.filter(Boolean).map((i) => (
            <option key={i} value={i}>{i.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
