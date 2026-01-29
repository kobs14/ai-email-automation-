import { useMemo } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale/en-US';
import type { CalendarEvent } from '../../types/calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const locales = { 'en-US': enUS };

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

interface CalendarViewProps {
  events: CalendarEvent[];
  onRangeChange?: (start: Date, end: Date) => void;
}

export function CalendarViewComponent({ events, onRangeChange }: CalendarViewProps) {
  const calendarEvents = useMemo(
    () =>
      events.map((e) => ({
        id: e.id,
        title: e.title,
        start: new Date(e.start_time),
        end: new Date(e.end_time),
        resource: e,
      })),
    [events]
  );

  return (
    <div className="card p-4" style={{ height: 600 }}>
      <Calendar
        localizer={localizer}
        events={calendarEvents}
        startAccessor="start"
        endAccessor="end"
        views={['month', 'week', 'day']}
        defaultView="month"
        onRangeChange={(range) => {
          if (onRangeChange) {
            if (Array.isArray(range)) {
              onRangeChange(range[0], range[range.length - 1]);
            } else if ('start' in range && 'end' in range) {
              onRangeChange(range.start, range.end);
            }
          }
        }}
        style={{ height: '100%' }}
        eventPropGetter={() => ({
          style: {
            backgroundColor: '#3b82f6',
            borderRadius: '4px',
            border: 'none',
            fontSize: '12px',
          },
        })}
      />
    </div>
  );
}
