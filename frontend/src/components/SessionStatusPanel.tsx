'use client';

import { Clock, Globe } from 'lucide-react';
import type { IntelligenceContext, ServicesResponse } from '../types/intelligence';
import styles from '../app/page.module.css';

type Props = {
  context: IntelligenceContext | null;
  services: ServicesResponse | null;
};

function pillColor(status: string) {
  if (status === 'ok' || status === 'running') return 'var(--success)';
  if (status === 'stale' || status === 'idle' || status === 'warn') return 'var(--warning)';
  return 'var(--danger)';
}

export default function SessionStatusPanel({ context, services }: Props) {
  const session = context?.session?.replace(/_/g, ' ') || 'Unknown';
  const quality = context?.session_quality ?? 0;
  const utcHour = context?.utc_hour ?? new Date().getUTCHours();

  const servicePills = services
    ? [
        { label: 'Matrix', status: String(services.matrix_worker?.status || 'unknown') },
        { label: 'AI', status: String(services.intelligence_worker?.status || 'unknown') },
        { label: 'Sync', status: String(services.historical_sync?.status || 'unknown') },
      ]
    : [];

  return (
    <div>
      <div className={styles.intelligenceCardTitle}>
        <Globe size={16} className={styles.panelIcon} />
        <span>Session & Services</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}><Globe size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />Session</span>
        <span className={styles.statValue} style={{ textTransform: 'capitalize' }}>{session}</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Session quality</span>
        <span className={styles.statValue}>{(quality * 100).toFixed(0)}%</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}><Clock size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />UTC</span>
        <span className={styles.statValue}>{utcHour}:00 {context?.is_weekend ? '(weekend)' : ''}</span>
      </div>
      {context?.sentiment_label && (
        <div className={styles.statRow}>
          <span className={styles.statLabel}>Sentiment 1h</span>
          <span className={styles.statValue}>{context.sentiment_label} ({((context.sentiment_1h || 0) * 100).toFixed(0)}%)</span>
        </div>
      )}
      <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {servicePills.map((s) => (
          <span
            key={s.label}
            style={{
              fontSize: 11,
              padding: '4px 10px',
              borderRadius: 12,
              border: `1px solid ${pillColor(s.status)}`,
              color: pillColor(s.status),
            }}
          >
            {s.label}: {s.status}
          </span>
        ))}
      </div>
    </div>
  );
}
