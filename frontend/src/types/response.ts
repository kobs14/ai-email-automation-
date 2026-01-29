export type ResponseStatus = 'draft' | 'approved' | 'sent' | 'rejected' | 'failed';

export interface ResponseRecord {
  id: number;
  email_id: number;
  draft_content: string;
  status: ResponseStatus;
  generated_at: string;
  sent_at?: string;
  approved_by?: string;
  send_attempts?: number;
  send_error?: string;
  created_at: string;
  updated_at: string;
  // Joined fields
  from_address?: string;
  subject?: string;
  intent?: string;
}

export interface ResponseWithEmail extends ResponseRecord {
  message_id?: string;
  original_body?: string;
  raw_headers?: Record<string, unknown>;
  entities?: Array<{
    id: number;
    entity_type: string;
    entity_value: string;
    confidence: number;
  }>;
}

export interface ResponseListParams {
  page?: number;
  per_page?: number;
  status?: ResponseStatus | null;
}
