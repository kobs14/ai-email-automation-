import { MapPin, Clock, User, Wrench } from 'lucide-react';
import type { CalendarEvent } from '../../types/calendar';

interface EventCardProps {
  event: CalendarEvent;
}

export function EventCard({ event }: EventCardProps) {
  const startDate = new Date(event.start_time);
  const endDate = new Date(event.end_time);

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      <h4 className="text-sm font-semibold text-gray-900">{event.title}</h4>
      <div className="mt-2 space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <Clock className="w-3.5 h-3.5" />
          <span>
            {startDate.toLocaleDateString()} {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            {' - '}
            {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        {event.location && (
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <MapPin className="w-3.5 h-3.5" />
            <span>{event.location}</span>
          </div>
        )}
        {event.customer_name && (
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <User className="w-3.5 h-3.5" />
            <span>{event.customer_name}</span>
          </div>
        )}
        {event.service_type && (
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <Wrench className="w-3.5 h-3.5" />
            <span>{event.service_type}</span>
          </div>
        )}
      </div>
    </div>
  );
}
