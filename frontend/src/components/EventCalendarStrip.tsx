'use client';

import { Calendar } from 'lucide-react';
import styles from '../app/page.module.css';

type Event = {
  name?: string;
  event_time?: string;
  impact?: string;
  country?: string;
};

type Props = {
  events: Event[];
};

export default function EventCalendarStrip({ events }: Props) {
  const upcoming = events.slice(0, 3);

  return (
    <div>
      <div className={styles.intelligenceCardTitle}>
        <Calendar size={16} className={styles.panelIcon} />
        <span>Upcoming Events</span>
      </div>
      {upcoming.length === 0 ? (
        <div className={styles.textMuted} style={{ fontSize: 12 }}>No events in window.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {upcoming.map((e, i) => (
            <div key={i} className={styles.statRow} style={{ fontSize: 12, flexWrap: 'wrap', gap: 4 }}>
              <span style={{ flex: '1 1 120px' }}>{e.name}</span>
              <span style={{ color: 'var(--text-tertiary)', flex: '0 0 auto' }}>
                {e.impact} · {e.event_time?.slice(0, 16)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
