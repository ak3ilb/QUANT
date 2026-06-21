'use client';
import React from 'react';

// Semicircular gauge using SVG
const SemicircleGauge = ({ value, label, tf }: { value: number, label: string, tf: string }) => {
  // value is expected to be between 0 and 1
  const radius = 40;
  const strokeWidth = 8;
  const circumference = Math.PI * radius;
  // Map value to stroke-dashoffset: 0 means full, circumference means empty
  const strokeDashoffset = circumference - value * circumference;
  
  // Interpolate color from Red (0) to Green (1) through Yellow/Orange
  const hue = value * 120; // 0 = red, 120 = green
  const color = `hsl(${hue}, 80%, 45%)`; // Darkened slightly for white bg

  // Calculate needle angle
  // 0 -> -90 deg (left), 1 -> +90 deg (right)
  const angle = (value * 180) - 90;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '10px' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#111827', letterSpacing: '1px' }}>{tf.toUpperCase()}</div>
      
      <div style={{ position: 'relative', width: '100px', height: '55px', display: 'flex', justifyContent: 'center' }}>
        {/* Background Arc */}
        <svg width="100" height="50" style={{ position: 'absolute', top: 0, overflow: 'visible' }}>
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Active Arc */}
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease' }}
          />
        </svg>
        
        {/* Needle pivot */}
        <div style={{
          position: 'absolute',
          bottom: '0px',
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          backgroundColor: '#111827',
          zIndex: 10
        }} />
        
        {/* Needle */}
        <div style={{
          position: 'absolute',
          bottom: '5px',
          width: '4px',
          height: '40px',
          backgroundColor: '#111827',
          transformOrigin: 'bottom center',
          transform: `rotate(${angle}deg)`,
          transition: 'transform 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)',
          zIndex: 5,
          borderRadius: '2px'
        }} />
      </div>

      <div style={{ marginTop: '15px', color: color, fontWeight: 'bold', fontSize: '14px' }}>
        {label}
      </div>
      <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
        {(value * 100).toFixed(1)}% Bull
      </div>
    </div>
  );
};

export default function SpeedometerGrid({ matrixData }: { matrixData: any }) {
  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"];
  
  if (!matrixData || Object.keys(matrixData).length === 0) {
    return <div style={{display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#718096'}}>Loading Matrix Data...</div>;
  }

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(3, 1fr)', 
      gap: '20px',
      padding: '20px',
      height: '100%',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: '12px'
    }}>
      {timeframes.map(tf => {
        // Use Medallion bayesian_prob_bull for the gauge
        const prob = matrixData[tf]?.signals?.medallion?.bayesian_prob_bull ?? 0.5;
        const medallionAction = matrixData[tf]?.signals?.medallion?.action || "HOLD";
        return (
          <SemicircleGauge 
            key={tf} 
            tf={tf} 
            value={prob} 
            label={medallionAction} 
          />
        );
      })}
    </div>
  );
}
