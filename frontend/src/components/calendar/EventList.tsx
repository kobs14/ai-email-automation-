import { EventCard } from './EventCard';
import { EmptyState } from '../common/EmptyState';
import type { CalendarEvent } from '../../types/calendar';
import { Calendar } from 'lucide-react';

interface EventListProps {
  events: CalendarEvent[];
}

export function EventList({ events }: EventListProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No events"
        description="No upcoming events scheduled."
        icon={<Calendar className="w-12 h-12" />}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </div>
  );
}
