export type StudyAlgorithm = {
  algorithm_id: string;
  layer: string;
  historical_score: number;
  metric: string;
  score_kind: 'accuracy' | 'readiness' | 'heuristic';
  bars_used: number;
  status: 'ok' | 'weak' | 'poor' | 'not_evaluated';
  model_reliable?: boolean;
};

export type StudyLayer = {
  layer_id: string;
  name: string;
  description: string;
  avg_historical_score: number | null;
  avg_accuracy_score: number | null;
  avg_readiness_score: number | null;
  best_algorithm: string | null;
  best_accuracy_algorithm: string | null;
  registry_algorithms: {
    id: string;
    name: string;
    category: string;
    implementation_status: string;
    historical_score: number | null;
    score_kind?: string | null;
    status: string;
  }[];
  evaluated_algorithms: StudyAlgorithm[];
};

export type StudyStrategy = {
  strategy: string;
  layer: string;
  bandit_alpha: number;
  bandit_beta: number;
  expected_win_rate: number;
  live_trades: number;
  live_wins: number;
  live_losses: number;
  live_pnl_pct_sum: number;
  working: boolean;
};

export type StudyDashboard = {
  status: string;
  symbol: string;
  interval: string;
  updated_at: string;
  layers: StudyLayer[];
  live_learning: {
    strategies: StudyStrategy[];
    online_model: { active: boolean; n_samples: number; candidate_samples: number };
    walk_forward: { production_sharpe: number; candidate_sharpe: number; trade_count: number };
    drift: Record<string, unknown>;
    entry_blocked: boolean;
    size_multiplier: number;
  };
  historical: {
    bars: number;
    evaluated_at: number;
    cached_at?: string;
    status?: string;
    min_recommended_bars?: number;
    low_data?: boolean;
  };
  recent_events: { id: string; event_type: string; symbol: string; payload: Record<string, unknown>; created_at: string }[];
  recommendations: string[];
  study_active: boolean;
};
