'use client';

import type { Headline } from '../types/intelligence';
import styles from '../app/page.module.css';

type Props = {
  headline: Headline;
  onClose?: () => void;
};

export default function NewsImpactCard({ headline, onClose }: Props) {
  const impact = headline.impact;

  return (
    <div style={{ border: '1px solid var(--panel-border)', borderRadius: 8, padding: 12, background: 'rgba(0,0,0,0.02)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong style={{ fontSize: 13 }}>AI Impact Analysis</strong>
        {onClose && (
          <button type="button" onClick={onClose} style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer' }}>
            Close
          </button>
        )}
      </div>
      <p style={{ fontSize: 12, marginBottom: 10, color: 'var(--text-secondary)' }}>{headline.headline}</p>
      {!impact ? (
        <div className={styles.textMuted}>Impact not scored yet.</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
          <div><span className={styles.statLabel}>Direction</span><br />{impact.impact_direction}</div>
          <div><span className={styles.statLabel}>Strength</span><br />{impact.impact_strength}</div>
          <div><span className={styles.statLabel}>ΔP(bull)</span><br />{(impact.prob_bull_delta * 100).toFixed(2)}%</div>
          <div><span className={styles.statLabel}>Trade gate</span><br />{impact.trade_gate}</div>
          <div style={{ gridColumn: '1 / -1' }}>
            <span className={styles.statLabel}>Symbols</span><br />
            {(impact.affected_symbols || headline.symbols || []).join(', ') || '—'}
          </div>
          <div><span className={styles.statLabel}>VADER</span><br />{headline.vader_score?.toFixed(3) ?? '—'}</div>
          <div><span className={styles.statLabel}>FinBERT</span><br />{headline.finbert_score?.toFixed(3) ?? '—'}</div>
        </div>
      )}
    </div>
  );
}
