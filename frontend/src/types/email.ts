export type EmailStatus = 'pending' | 'classified' | 'responded' | 'failed';

export type EmailIntent =
  | 'quote_request'
  | 'booking_request'
  | 'rescheduling'
  | 'complaint'
  | 'general_inquiry';

export interface Email {
  id: number;
  message_id: string;
  from_address: string;
  subject: string;
  body?: string;
  received_at: string;
  processed_at?: string;
  status: EmailStatus;
  intent?: EmailIntent;
  priority?: number;
  raw_headers?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface Entity {
  id: number;
  email_id: number;
  entity_type: string;
  entity_value: string;
  confidence: number;
  extracted_at: string;
}

export interface EmailDetail extends Email {
  entities: Entity[];
  response: ResponseRecord | null;
}

export interface EmailListParams {
  page?: number;
  per_page?: number;
  status?: EmailStatus | null;
  intent?: EmailIntent | null;
  search?: string;
}

import type { ResponseRecord } from './response';
