'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';
import { Activity, Cpu, Crosshair, Target, Newspaper } from 'lucide-react';
import SpeedometerGrid from './SpeedometerGrid';
import PredictionPanel from './PredictionPanel';
import PaperTraderPanel from './PaperTraderPanel';
import SessionStatusPanel from '../components/SessionStatusPanel';
import NewsFeedPanel from '../components/NewsFeedPanel';
import EventCalendarStrip from '../components/EventCalendarStrip';
import LearningStatsWidget from '../components/LearningStatsWidget';
import type { Headline, IntelligenceContext, ServicesResponse } from '../types/intelligence';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001/api';
const CDP_HEALTH = 'http://localhost:3001/health';

type SystemStatus = {
  api: 'ok' | 'error' | 'unknown';
  cdp: 'ok' | 'error' | 'unknown';
  matrix: 'ok' | 'stale' | 'unknown';
};

export default function Dashboard() {
  const [symbol, setSymbol] = useState('BTCUSD');
  const [matrixData, setMatrixData] = useState<any>(null);
  const [magneticLevels, setMagneticLevels] = useState<number[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    api: 'unknown',
    cdp: 'unknown',
    matrix: 'unknown',
  });
  const [context, setContext] = useState<IntelligenceContext | null>(null);
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [services, setServices] = useState<ServicesResponse | null>(null);
  const [learning, setLearning] = useState<Record<string, unknown> | null>(null);
  const [mlTrainable, setMlTrainable] = useState(0);

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
  const strategies = [
    { id: 'nova', name: '🚀 Nova', type: 'Momentum' },
    { id: 'piggy', name: '🐷 Piggy', type: 'Mean Reversion' },
    { id: 'limroy', name: '📊 Limroy', type: 'Stat Arb' },
    { id: 'dejavu', name: '🔮 Déjà Vu', type: 'HMM Pattern' },
    { id: 'medallion', name: '🥇 Medallion', type: 'Ensemble' },
  ];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [matrixRes, healthRes, cdpRes] = await Promise.all([
          fetch(`${API_BASE}/medallion-matrix?symbol=${symbol}`),
          fetch(`${API_BASE.replace('/api', '')}/health`).catch(() => null),
          fetch(CDP_HEALTH).catch(() => null),
        ]);

        const matrix = await matrixRes.json();
        setMatrixData(matrix.matrix);
        setMagneticLevels(matrix.magnetic_levels || matrix.magneticLevels || []);
        if (matrix.context) {
          setContext(matrix.context as IntelligenceContext);
        }

        const apiOk = healthRes?.ok ?? false;
        const cdpOk = cdpRes?.ok ?? false;
        let matrixOk: SystemStatus['matrix'] = 'unknown';
        if (matrix.last_updated) {
          const age = Date.now() - new Date(matrix.last_updated).getTime();
          matrixOk = age < 60000 ? 'ok' : 'stale';
        } else if (matrix.matrix) {
          matrixOk = 'ok';
        }

        setSystemStatus({
          api: apiOk ? 'ok' : 'error',
          cdp: cdpOk ? 'ok' : 'error',
          matrix: matrixOk,
        });
      } catch (err) {
        console.error('Error fetching data:', err);
        setSystemStatus({ api: 'error', cdp: 'error', matrix: 'unknown' });
      }
    };

    fetchData();
    const intervalId = setInterval(fetchData, 5000);
    return () => clearInterval(intervalId);
  }, [symbol]);

  useEffect(() => {
    const loadIntel = async () => {
      try {
        const [aiRes, headRes, calRes, svcRes] = await Promise.all([
          fetch(`${API_BASE}/ai/status?symbol=${symbol}`).catch(() => null),
          fetch(`${API_BASE}/intelligence/headlines?symbol=${symbol}&hours=24`).catch(() => null),
          fetch(`${API_BASE}/intelligence/calendar?hours=48`).catch(() => null),
          fetch(`${API_BASE}/system/services`).catch(() => null),
        ]);
        if (aiRes?.ok) {
          const ai = await aiRes.json();
          setContext(ai.context || null);
          setLearning(ai.learning || null);
          setMlTrainable(ai.ml_readiness?.trainable_count ?? 0);
        }
        if (headRes?.ok) {
          const h = await headRes.json();
          setHeadlines(h.headlines || []);
        }
        if (calRes?.ok) {
          const c = await calRes.json();
          setEvents(c.events || []);
        }
        if (svcRes?.ok) {
          setServices(await svcRes.json());
        }
      } catch (e) {
        console.error('Intelligence fetch error', e);
      }
    };
    loadIntel();
    const id = setInterval(loadIntel, 15000);
    return () => clearInterval(id);
  }, [symbol]);

  const statusColor = (s: string) =>
    s === 'ok' ? 'var(--success)' : s === 'stale' ? 'var(--warning)' : 'var(--danger)';

  const tf1h = matrixData?.['1h'];

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h1>QUANT Command Center</h1>
          <p>Medallion Matrix & Advanced Topology Engine</p>
        </div>

        <div className={styles.controls}>
          <select
            className={styles.input}
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          >
            <option value="BTCUSD">BTCUSD</option>
            <option value="XAUUSD">XAUUSD</option>
          </select>
        </div>
      </header>

      <main className={styles.dashboard}>
        <div className={styles.topRow}>
          <section className={styles.glassPanel}>
            <div className={styles.panelHeader}>
              <Activity className={styles.panelIcon} size={20} />
              <span className={styles.panelTitle}>{symbol} — Live Momentum Speedometers</span>
            </div>
            <div className={styles.chartContainer}>
              <SpeedometerGrid matrixData={matrixData} />
            </div>
          </section>

          <section className={styles.glassPanel}>
            <div className={styles.panelHeader}>
              <Target className={styles.panelIcon} size={20} />
              <span className={styles.panelTitle}>SDE Target Predictor</span>
            </div>
            <div className={styles.chartContainer} style={{ overflowY: 'auto' }}>
              <PredictionPanel matrixData={matrixData} />
            </div>
          </section>

          <section className={styles.glassPanel}>
            <div className={styles.panelHeader}>
              <Cpu className={styles.panelIcon} size={20} />
              <span className={styles.panelTitle}>Engine Telemetry</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', minWidth: 0 }}>
              <div>
                <h4 style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>System Status</h4>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>FastAPI</span>
                  <span className={styles.statValue} style={{ color: statusColor(systemStatus.api) }}>
                    {systemStatus.api === 'ok' ? 'Active' : 'Offline'}
                  </span>
                </div>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>CDP Bridge</span>
                  <span className={styles.statValue} style={{ color: statusColor(systemStatus.cdp) }}>
                    {systemStatus.cdp === 'ok' ? 'Connected' : 'Offline'}
                  </span>
                </div>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>Matrix Daemon</span>
                  <span className={styles.statValue} style={{ color: statusColor(systemStatus.matrix) }}>
                    {systemStatus.matrix === 'ok' ? 'Live' : systemStatus.matrix === 'stale' ? 'Stale' : 'Unknown'}
                  </span>
                </div>
                {tf1h && (
                  <>
                    <div className={styles.statRow}>
                      <span className={styles.statLabel}>Price (1h)</span>
                      <span className={styles.statValue}>{tf1h.current_price?.toFixed(2)}</span>
                    </div>
                    <div className={styles.statRow}>
                      <span className={styles.statLabel}>SDE Target</span>
                      <span className={styles.statValue}>{tf1h.sde_forecast?.toFixed(2)}</span>
                    </div>
                  </>
                )}
              </div>

              <div>
                <h4 style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>Magnetic Levels (KDE)</h4>
                {magneticLevels.length > 0 ? (
                  magneticLevels.map((lvl, i) => (
                    <div key={i} className={styles.statRow}>
                      <span className={styles.statLabel}>Node {i + 1}</span>
                      <span className={styles.statValue}>{lvl.toFixed(2)}</span>
                    </div>
                  ))
                ) : (
                  <div className={styles.textMuted}>No levels computed yet</div>
                )}
              </div>
            </div>
          </section>
        </div>

        <section className={styles.glassPanel}>
          <div className={styles.panelHeader}>
            <Newspaper className={styles.panelIcon} size={20} />
            <span className={styles.panelTitle}>Intelligence Layer — News & AI Impact</span>
          </div>

          <div className={styles.intelligenceTop}>
            <div className={styles.intelligenceCard}>
              <SessionStatusPanel context={context} services={services} />
            </div>
            <div className={styles.intelligenceCard}>
              <EventCalendarStrip events={events} />
            </div>
            <div className={styles.intelligenceCard}>
              <LearningStatsWidget learning={learning} mlTrainableCount={mlTrainable} />
            </div>
          </div>

          <div className={`${styles.intelligenceCard} ${styles.intelligenceNewsWrap}`}>
            <NewsFeedPanel headlines={headlines} symbol={symbol} embedded />
          </div>
        </section>

        <section className={styles.glassPanel}>
          <div className={styles.panelHeader}>
            <Crosshair className={styles.panelIcon} size={20} />
            <span className={styles.panelTitle}>Multi-Dimensional Signal Matrix</span>
          </div>

          {!matrixData ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              Computing Tensor Matrices...
            </div>
          ) : (
            <div className={styles.matrixGrid}>
              <div className={styles.gridHeader}>Strategy \ TF</div>
              {timeframes.map((tf) => (
                <div key={tf} className={styles.gridHeader}>
                  {tf.toUpperCase()}
                  {matrixData[tf] && matrixData[tf].regime && (
                    <div style={{ marginTop: '4px' }}>
                      <span className={`${styles.regimeTag} ${styles['regime' + matrixData[tf].regime]}`}>
                        {matrixData[tf].regime}
                      </span>
                    </div>
                  )}
                </div>
              ))}

              {strategies.map((strat) => (
                <div
                  key={strat.id}
                  style={{ display: 'contents' }}
                  className={strat.id === 'medallion' ? styles.medallionRow : ''}
                >
                  <div className={styles.strategyLabel}>
                    <div>
                      <div>{strat.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 'normal' }}>
                        {strat.type}
                      </div>
                    </div>
                  </div>

                  {timeframes.map((tf) => {
                    const cellData = matrixData[tf]?.signals?.[strat.id];
                    if (!cellData) return <div key={tf} className={styles.gridCell}>-</div>;

                    return (
                      <div key={tf} className={styles.gridCell}>
                        <span className={styles[`signal${cellData.action}`]}>{cellData.action}</span>
                        <span className={styles.confText}>{(cellData.confidence * 100).toFixed(1)}%</span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={styles.lowerRow}>
          <PaperTraderPanel symbol={symbol} />
        </section>
      </main>
    </div>
  );
}
