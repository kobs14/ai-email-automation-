export interface CalendarEvent {
  id: number;
  google_event_id?: string;
  response_id?: number;
  title: string;
  description?: string;
  location?: string;
  start_time: string;
  end_time: string;
  customer_name?: string;
  customer_phone?: string;
  service_type?: string;
  source: 'system' | 'manual';
  created_at?: string;
  updated_at?: string;
}
