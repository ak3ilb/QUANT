'use client';

import { useState } from 'react';
import { Newspaper } from 'lucide-react';
import type { Headline } from '../types/intelligence';
import NewsImpactCard from './NewsImpactCard';
import styles from '../app/page.module.css';

type Props = {
  headlines: Headline[];
  symbol: string;
  embedded?: boolean;
};

function isNew(publishedAt: string) {
  const age = Date.now() - new Date(publishedAt).getTime();
  return age < 5 * 60 * 1000;
}

function labelClass(label: string | null) {
  if (label === 'bullish') return styles.signalBUY;
  if (label === 'bearish') return styles.signalSELL;
  return styles.signalHOLD;
}

export default function NewsFeedPanel({ headlines, symbol, embedded }: Props) {
  const [selected, setSelected] = useState<Headline | null>(null);

  return (
    <div style={{ minWidth: 0 }}>
      {!embedded && (
        <div className={styles.panelHeader} style={{ marginBottom: 12 }}>
          <Newspaper className={styles.panelIcon} size={20} />
          <span className={styles.panelTitle}>News — {symbol}</span>
        </div>
      )}
      {embedded && (
        <div className={styles.intelligenceCardTitle}>
          <Newspaper size={16} className={styles.panelIcon} />
          <span>News — {symbol}</span>
        </div>
      )}
      <div className={`${styles.newsSplit} ${selected ? styles.newsSplitWithDetail : ''}`}>
        <div className={styles.newsList}>
        {headlines.length === 0 ? (
          <div className={styles.textMuted}>No headlines yet. Start intelligence worker.</div>
        ) : (
          headlines.map((h) => (
            <button
              key={h.id}
              type="button"
              onClick={() => setSelected(h)}
              style={{
                textAlign: 'left',
                background: selected?.id === h.id ? 'rgba(37,99,235,0.08)' : 'transparent',
                border: '1px solid var(--panel-border)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{h.source}</span>
                <span className={labelClass(h.label)} style={{ fontSize: 11, padding: '2px 6px' }}>
                  {h.label || 'neutral'}
                  {isNew(h.published_at) ? ' • NEW' : ''}
                </span>
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.4 }}>{h.headline}</div>
              {h.impact && (
                <div style={{ fontSize: 11, marginTop: 4, color: 'var(--text-secondary)' }}>
                  Impact: {h.impact.impact_direction} ΔP {(h.impact.prob_bull_delta * 100).toFixed(1)}% · {h.impact.trade_gate}
                </div>
              )}
            </button>
          ))
        )}
        </div>
        {selected && (
          <div className={styles.newsDetail}>
            <NewsImpactCard headline={selected} onClose={() => setSelected(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
