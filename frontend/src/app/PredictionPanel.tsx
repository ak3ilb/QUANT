'use client';
import React from 'react';
import { Target, TrendingUp, TrendingDown } from 'lucide-react';

export default function PredictionPanel({ matrixData }: { matrixData: any }) {
  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"];
  
  if (!matrixData || Object.keys(matrixData).length === 0) {
    return <div style={{display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#718096'}}>Awaiting Predictions...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '0px 10px' }}>
      {timeframes.map(tf => {
        const data = matrixData[tf];
        if (!data || !data.current_price || !data.sde_forecast) return null;

        const current = data.current_price;
        const target = data.sde_forecast;
        const percentMove = ((target - current) / current) * 100;
        const isUp = percentMove > 0;
        const color = isUp ? '#16a34a' : '#dc2626'; // green-600 and red-600

        return (
          <div key={tf} style={{ 
            display: 'grid', 
            gridTemplateColumns: 'minmax(60px, 1fr) minmax(80px, 1fr) minmax(100px, 2fr) minmax(60px, 1fr)', 
            gap: '12px',
            alignItems: 'center',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            padding: '12px 16px',
            borderRadius: '8px',
            borderLeft: `3px solid ${color}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 'bold', color: '#111827' }}>{tf.toUpperCase()}</span>
              {isUp ? <TrendingUp size={16} color={color} style={{minWidth: '16px'}} /> : <TrendingDown size={16} color={color} style={{minWidth: '16px'}} />}
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#6b7280' }}>Target</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: '#111827' }}>
                ${target.toFixed(2)}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
              <span style={{ fontSize: '11px', color: '#6b7280' }}>Candlestick Pattern</span>
              <span style={{ fontSize: '11px', fontWeight: 'bold', color: data.active_patterns ? '#4f46e5' : '#9ca3af', display: 'block', wordBreak: 'break-word' }}>
                {data.active_patterns ? data.active_patterns.split(',').map((p: string) => p.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())).join(', ') : 'None'}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <span style={{ fontSize: '11px', color: '#6b7280' }}>Expected</span>
              <span style={{ fontWeight: 'bold', color: color }}>
                {isUp ? '+' : ''}{percentMove.toFixed(2)}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
