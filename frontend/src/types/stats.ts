export interface OverviewStats {
  email_counts: Record<string, number>;
  response_counts: Record<string, number>;
  upcoming_events: number;
}

export interface IntentStat {
  intent: string;
  count: number;
}

export interface ProcessingDay {
  date: string;
  received: number;
  processed: number;
  responded: number;
}
