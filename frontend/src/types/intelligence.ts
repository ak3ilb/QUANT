export type NewsImpact = {
  impact_direction: string;
  prob_bull_delta: number;
  impact_strength: string;
  trade_gate: string;
  affected_symbols: string[];
};

export type Headline = {
  id: string;
  published_at: string;
  source: string;
  headline: string;
  url: string;
  symbols: string[];
  ensemble_score: number | null;
  label: string | null;
  vader_score?: number | null;
  finbert_score?: number | null;
  impact: NewsImpact | null;
};

export type IntelligenceContext = {
  session?: string;
  session_quality?: number;
  event_risk?: number;
  in_pre_event_window?: boolean;
  sentiment_1h?: number;
  sentiment_label?: string;
  fear_greed_norm?: number;
  data_quality?: string;
  trade_allowed?: boolean;
  utc_hour?: number;
  is_weekend?: boolean;
};

export type ServiceStatus = {
  status: string;
  [key: string]: unknown;
};

export type ServicesResponse = {
  fastapi: ServiceStatus;
  matrix_worker: ServiceStatus;
  intelligence_worker: ServiceStatus;
  historical_sync: ServiceStatus;
  paper_trader: ServiceStatus;
  checked_at: string;
};
