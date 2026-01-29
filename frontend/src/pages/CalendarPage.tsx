import { useState } from 'react';
import { useCalendarEvents, useUpcomingEvents } from '../hooks/useCalendar';
import { CalendarViewComponent } from '../components/calendar/CalendarView';
import { EventList } from '../components/calendar/EventList';
import { PageLoader } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { CalendarDays, List } from 'lucide-react';

export function CalendarPage() {
  const [view, setView] = useState<'calendar' | 'list'>('calendar');
  const [dateRange, setDateRange] = useState<{ start?: string; end?: string }>({});

  const { data: eventsData, isLoading: loadingEvents, error, refetch } = useCalendarEvents(
    dateRange.start,
    dateRange.end
  );

  const { data: upcomingData, isLoading: loadingUpcoming } = useUpcomingEvents(20);

  const handleRangeChange = (start: Date, end: Date) => {
    setDateRange({
      start: start.toISOString(),
      end: end.toISOString(),
    });
  };

  if (loadingEvents && loadingUpcoming) return <PageLoader />;
  if (error) return <ErrorAlert message="Failed to load calendar events" onRetry={refetch} />;

  const events = eventsData?.items ?? upcomingData?.items ?? [];

  return (
    <div>
      {/* View toggle */}
      <div className="flex items-center justify-end gap-2 mb-4">
        <button
          onClick={() => setView('calendar')}
          className={`p-2 rounded-lg ${view === 'calendar' ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'}`}
          aria-label="Calendar view"
          aria-pressed={view === 'calendar'}
        >
          <CalendarDays className="w-5 h-5" />
        </button>
        <button
          onClick={() => setView('list')}
          className={`p-2 rounded-lg ${view === 'list' ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'}`}
          aria-label="List view"
          aria-pressed={view === 'list'}
        >
          <List className="w-5 h-5" />
        </button>
      </div>

      {view === 'calendar' ? (
        <CalendarViewComponent events={events} onRangeChange={handleRangeChange} />
      ) : (
        <EventList events={events} />
      )}
    </div>
  );
}
