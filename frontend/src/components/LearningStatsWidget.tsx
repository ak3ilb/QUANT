'use client';

import Link from 'next/link';
import { Brain } from 'lucide-react';
import styles from '../app/page.module.css';

type Props = {
  learning: Record<string, unknown> | null;
  mlTrainableCount: number;
};

export default function LearningStatsWidget({ learning, mlTrainableCount }: Props) {
  const bandit = (learning?.bandit as Record<string, { expected_win_rate?: number; trades?: number }>) || {};
  const online = (learning?.online_model as { active?: boolean }) || {};
  const walk = (learning?.walk_forward as { trade_count?: number; production_sharpe?: number }) || {};

  const banditSummary = Object.entries(bandit)
    .map(([k, v]) => `${k}(${(v.trades ?? 0)}t, ${((v.expected_win_rate ?? 0.5) * 100).toFixed(0)}%)`)
    .join(' · ');

  return (
    <div>
      <div className={styles.intelligenceCardTitle}>
        <Brain size={16} className={styles.panelIcon} />
        <span>AI / ML Status</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>ML datasets ready</span>
        <span className={styles.statValue}>{mlTrainableCount}</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Online model</span>
        <span className={styles.statValue}>{online.active ? 'Active' : 'Idle'}</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Trades studied</span>
        <span className={styles.statValue}>{walk.trade_count ?? 0}</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Entry blocked</span>
        <span className={styles.statValue}>{learning?.entry_blocked ? 'Yes' : 'No'}</span>
      </div>
      {banditSummary && (
        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-secondary)' }}>
          Bandit: {banditSummary}
        </div>
      )}
      <Link href="/ai" style={{ display: 'inline-block', marginTop: 12, fontSize: 12, color: 'var(--accent-blue)' }}>
        Open AI Study Lab →
      </Link>
    </div>
  );
}
