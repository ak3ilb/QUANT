'use client';

import { useCallback, useEffect, useState } from 'react';
import { Activity, Brain, Globe, Layers, RefreshCw, TrendingUp } from 'lucide-react';
import type { StudyDashboard } from '../../types/study';
import styles from './page.module.css';

const MIN_STUDY_BARS = 400;

const INTERVAL_OPTIONS = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1d' },
] as const;

type FusedContext = {
  symbol: string;
  fused_at: string;
  timeline?: { active_session?: string; session_quality?: number; london_ny_overlap?: boolean };
  news?: { count?: number; avg_sentiment?: number; sentiment_label?: string; top_headline?: string };
  finrl?: { action?: string; model_reliable?: boolean; vault_bars?: number };
  matrix?: { current_price?: number; sde_divergence_pct?: number };
  broker?: { account_type?: string; max_leverage?: number };
  intelligence?: { trade_allowed?: boolean; data_quality?: string };
};

function statusClass(status: string) {
  if (status === 'ok') return styles.statusOk;
  if (status === 'weak') return styles.statusWeak;
  return styles.statusPoor;
}

function scorePct(score: number | null | undefined) {
  if (score == null) return '—';
  return `${(score * 100).toFixed(1)}%`;
}

function scoreKindLabel(kind: string | undefined) {
  if (kind === 'accuracy') return 'Accuracy';
  if (kind === 'readiness') return 'Readiness';
  if (kind === 'heuristic') return 'Heuristic';
  return 'Score';
}

function scoreKindClass(kind: string | undefined) {
  if (kind === 'accuracy') return styles.kindAccuracy;
  if (kind === 'readiness') return styles.kindReadiness;
  if (kind === 'heuristic') return styles.kindHeuristic;
  return styles.kindDefault;
}

function formatAlgoScore(algo: { historical_score: number; score_kind?: string; metric?: string }) {
  if (algo.score_kind === 'readiness') {
    return algo.historical_score >= 0.8 ? 'Ready' : 'Not ready';
  }
  return scorePct(algo.historical_score);
}

export default function AIStudyPage() {
  const [symbol, setSymbol] = useState('BTCUSD');
  const [barInterval, setBarInterval] = useState('1h');
  const [data, setData] = useState<StudyDashboard | null>(null);
  const [context, setContext] = useState<FusedContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (force = false) => {
    try {
      const url = `${API_BASE}/ai/study?symbol=${symbol}&interval=${barInterval}${force ? '&refresh=true' : ''}`;
      const [res, ctxRes] = await Promise.all([
        fetch(url),
        fetch(`${API_BASE}/ai/context?symbol=${symbol}&interval=${barInterval}`),
      ]);
      if (res.ok) {
        setData(await res.json());
      }
      if (ctxRes.ok) {
        setContext(await ctxRes.json());
      }
    } catch (e) {
      console.error('Study fetch error', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [symbol, barInterval]);

  useEffect(() => {
    setLoading(true);
    load();
    const id = setInterval(() => load(), 5000);
    return () => clearInterval(id);
  }, [load]);

  const onRefresh = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/ai/study/tick?symbol=${symbol}&interval=${barInterval}`, { method: 'POST' }).finally(() => {
      setTimeout(() => load(true), 2000);
    });
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1><Brain size={28} className={styles.headerIcon} /> AI Study Lab</h1>
          <p>Multi-layer algorithm learning · live trades · historical walk-forward</p>
        </div>
        <div className={styles.controls}>
          <select className={styles.select} value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            <option value="BTCUSD">BTCUSD</option>
            <option value="XAUUSD">XAUUSD</option>
          </select>
          <select className={styles.select} value={barInterval} onChange={(e) => setBarInterval(e.target.value)}>
            {INTERVAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button type="button" className={styles.refreshBtn} onClick={onRefresh} disabled={refreshing}>
            <RefreshCw size={16} className={refreshing ? styles.spin : ''} />
            Re-study
          </button>
        </div>
      </header>

      {loading && !data ? (
        <div className={styles.loading}>Loading study data…</div>
      ) : data ? (
        <>
          {(data.historical.bars ?? 0) < MIN_STUDY_BARS && (
            <section className={styles.dataWarn}>
              <strong>Low data warning</strong>
              <p>
                Only <strong>{data.historical.bars ?? 0}</strong> bars available for{' '}
                <strong>{data.symbol}</strong> @ <strong>{data.interval}</strong>.
                Walk-forward scores are unreliable below {MIN_STUDY_BARS} bars — backfill history
                or use 1h / 4h / 1d for stable study results.
              </p>
            </section>
          )}

          <section className={styles.summaryRow}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Live trades studied</span>
              <span className={styles.summaryValue}>{data.live_learning.walk_forward.trade_count}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Online model</span>
              <span className={styles.summaryValue}>
                {data.live_learning.online_model.active ? 'Active' : 'Idle'}
                <small> ({data.live_learning.online_model.n_samples} samples)</small>
              </span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Production Sharpe</span>
              <span className={styles.summaryValue}>{data.live_learning.walk_forward.production_sharpe.toFixed(3)}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Historical bars</span>
              <span className={styles.summaryValue}>{data.historical.bars ?? '—'}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Drift / sizing</span>
              <span className={styles.summaryValue}>
                {data.live_learning.entry_blocked ? 'BLOCKED' : `×${data.live_learning.size_multiplier.toFixed(2)}`}
              </span>
            </div>
          </section>

          {context && (
            <section className={styles.panel}>
              <div className={styles.panelTitle}>
                <Globe size={18} /> Live context fusion
              </div>
              <div className={styles.contextGrid}>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>Session</span>
                  <span>{context.timeline?.active_session ?? '—'}</span>
                  <small>quality {(context.timeline?.session_quality ?? 0).toFixed(2)}</small>
                </div>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>News</span>
                  <span>{context.news?.count ?? 0} headlines</span>
                  <small>{context.news?.sentiment_label ?? 'neutral'} ({(context.news?.avg_sentiment ?? 0).toFixed(2)})</small>
                </div>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>FinRL</span>
                  <span>{context.finrl?.action ?? 'HOLD'}</span>
                  <small>{context.finrl?.model_reliable ? 'verified' : 'gated'} · {context.finrl?.vault_bars ?? 0} bars</small>
                </div>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>Matrix / SDE</span>
                  <span>{context.matrix?.current_price?.toLocaleString() ?? '—'}</span>
                  <small>divergence {(context.matrix?.sde_divergence_pct ?? 0).toFixed(4)}%</small>
                </div>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>Broker</span>
                  <span>{context.broker?.account_type ?? 'Standard'}</span>
                  <small>1:{context.broker?.max_leverage ?? 2000}</small>
                </div>
                <div className={styles.contextCard}>
                  <span className={styles.contextLabel}>Trade gate</span>
                  <span>{context.intelligence?.trade_allowed === false ? 'BLOCKED' : 'OK'}</span>
                  <small>data {context.intelligence?.data_quality ?? '—'}</small>
                </div>
              </div>
              {context.news?.top_headline && (
                <p className={styles.muted}>Latest: {context.news.top_headline}</p>
              )}
              <div className={styles.footerMeta}>Fused {new Date(context.fused_at).toLocaleTimeString()}</div>
            </section>
          )}

          {data.recommendations.length > 0 && (
            <section className={styles.recBox}>
              <strong>Recommendations</strong>
              <ul>
                {data.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </section>
          )}

          <section className={styles.panel}>
            <div className={styles.panelTitle}>
              <TrendingUp size={18} /> Strategy bandit — live learning from paper trades
            </div>
            <div className={styles.strategyGrid}>
              {data.live_learning.strategies.map((s) => (
                <div key={s.strategy} className={`${styles.strategyCard} ${s.working ? styles.working : styles.weak}`}>
                  <div className={styles.strategyName}>{s.strategy}</div>
                  <div className={styles.strategyMeta}>
                    Win rate (bandit): {(s.expected_win_rate * 100).toFixed(1)}%
                  </div>
                  <div className={styles.strategyMeta}>
                    Live: {s.live_wins}W / {s.live_losses}L · PnL% sum {s.live_pnl_pct_sum.toFixed(2)}
                  </div>
                  <div className={styles.banditBar}>
                    <div className={styles.banditFill} style={{ width: `${s.expected_win_rate * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelTitle}>
              <Layers size={18} /> Algorithm layers — decoded from registry + historical eval
            </div>
            <p className={styles.scoreLegend}>
              <span className={styles.kindAccuracy}>Accuracy</span> = walk-forward direction/calibration ·{' '}
              <span className={styles.kindReadiness}>Readiness</span> = data/model pipeline status ·{' '}
              <span className={styles.kindHeuristic}>Heuristic</span> = rule-based proxy
            </p>
            <div className={styles.layerStack}>
              {data.layers.map((layer) => (
                <div key={layer.layer_id} className={styles.layerCard}>
                  <div className={styles.layerHeader}>
                    <div>
                      <div className={styles.layerId}>{layer.layer_id}</div>
                      <div className={styles.layerName}>{layer.name}</div>
                      <div className={styles.layerDesc}>{layer.description}</div>
                    </div>
                    <div className={styles.layerScore}>
                      {layer.avg_accuracy_score != null ? (
                        <>
                          <span className={styles.kindAccuracy}>{scorePct(layer.avg_accuracy_score)}</span>
                          <small>avg accuracy</small>
                        </>
                      ) : layer.avg_readiness_score != null ? (
                        <>
                          <span className={styles.kindReadiness}>{scorePct(layer.avg_readiness_score)}</span>
                          <small>avg readiness</small>
                        </>
                      ) : (
                        scorePct(layer.avg_historical_score)
                      )}
                      {layer.best_accuracy_algorithm && (
                        <small>best accuracy: {layer.best_accuracy_algorithm}</small>
                      )}
                    </div>
                  </div>
                  <div className={styles.algoTable}>
                    <div className={styles.algoHeader}>
                      <span>Algorithm</span>
                      <span>Status</span>
                      <span>Score</span>
                      <span>Metric</span>
                    </div>
                    {(layer.evaluated_algorithms.length ? layer.evaluated_algorithms : layer.registry_algorithms.map((r) => ({
                      algorithm_id: r.id,
                      historical_score: r.historical_score ?? 0,
                      status: r.status,
                      metric: 'registry',
                      score_kind: r.score_kind ?? undefined,
                      bars_used: 0,
                      layer: layer.layer_id,
                    }))).map((algo) => (
                      <div key={algo.algorithm_id} className={styles.algoRow}>
                        <span className={styles.algoId}>{algo.algorithm_id}</span>
                        <span className={statusClass(algo.status)}>{algo.status}</span>
                        <span className={styles.algoScore}>
                          {formatAlgoScore(algo)}
                          {algo.algorithm_id === 'finrl_ppo' && 'model_reliable' in algo && (
                            <small className={algo.model_reliable ? styles.reliableOk : styles.reliableWarn}>
                              {algo.model_reliable ? ' verified' : ' unverified'}
                            </small>
                          )}
                        </span>
                        <span className={styles.algoMetric}>
                          <span className={scoreKindClass('score_kind' in algo ? algo.score_kind : undefined)}>
                            {scoreKindLabel('score_kind' in algo ? algo.score_kind : undefined)}
                          </span>
                          {' · '}
                          {'metric' in algo ? algo.metric : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelTitle}>
              <Activity size={18} /> Realtime study event stream
            </div>
            <div className={styles.eventStream}>
              {data.recent_events.length === 0 ? (
                <div className={styles.muted}>No study events yet — close paper trades or run Re-study.</div>
              ) : (
                data.recent_events.map((ev) => (
                  <div key={ev.id} className={styles.eventRow}>
                    <span className={styles.eventTime}>{ev.created_at.slice(0, 19)}</span>
                    <span className={styles.eventType}>{ev.event_type}</span>
                    <span className={styles.eventPayload}>
                      {ev.event_type === 'trade_closed'
                        ? `${ev.payload.strategy} ${ev.payload.won ? 'WIN' : 'LOSS'} ${((ev.payload.pnl_pct as number) * 100)?.toFixed?.(2) ?? ev.payload.pnl_pct}%`
                        : JSON.stringify(ev.payload).slice(0, 80)}
                    </span>
                  </div>
                ))
              )}
            </div>
            <div className={styles.footerMeta}>
              Updated {new Date(data.updated_at).toLocaleTimeString()} · polling every 5s
            </div>
          </section>
        </>
      ) : (
        <div className={styles.loading}>Could not load study API. Is backend running on port 8001?</div>
      )}
    </div>
  );
}
