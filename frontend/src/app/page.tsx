'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';
import { Activity, Shield, BarChart2, Cpu, Crosshair, Zap, Target } from 'lucide-react';
import dynamic from 'next/dynamic';
import SpeedometerGrid from './SpeedometerGrid';
import PredictionPanel from './PredictionPanel';
import PaperTraderPanel from './PaperTraderPanel';

const TradingChart = dynamic(() => import('../components/TradingChart'), { ssr: false });

const API_BASE = 'http://localhost:8000/api';

export default function Dashboard() {
  const [symbol, setSymbol] = useState('BTCUSD');
  const [chartData, setChartData] = useState<any[]>([]);
  const [matrixData, setMatrixData] = useState<any>(null);
  const [magneticLevels, setMagneticLevels] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"];
  const strategies = [
    { id: "nova", name: "🚀 Nova", type: "Momentum" },
    { id: "piggy", name: "🐷 Piggy", type: "Mean Reversion" },
    { id: "limroy", name: "📊 Limroy", type: "Stat Arb" },
    { id: "dejavu", name: "🔮 Déjà Vu", type: "HMM Pattern" },
    { id: "medallion", name: "🥇 Medallion", type: "Ensemble" }
  ];

  useEffect(() => {
    const fetchData = async () => {
      // Removed setLoading(true) to avoid React closure bug inside setInterval
      try {
        // 1. Fetch High-Res Chart Data (1h default for main view)
        const dataRes = await fetch(`${API_BASE}/data?symbol=${symbol}&interval=1h&bars=500`);
        const data = await dataRes.json();
        if (data.data) {
          const formatted = data.data.map((d: any) => ({
            time: d.time || d.index || d.Date,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
            volume: d.volume
          }));
          setChartData(formatted);
        }

        // 2. Fetch the entire Medallion Matrix (all timeframes, all strategies)
        const matrixRes = await fetch(`${API_BASE}/medallion-matrix?symbol=${symbol}`);
        const matrix = await matrixRes.json();
        setMatrixData(matrix.matrix);
        setMagneticLevels(matrix.magnetic_levels || []);

      } catch (err) {
        console.error("Error fetching data:", err);
      }
      setLoading(false);
    };

    fetchData();
    // Refresh every 5s — fast enough to feel live, not hammering the API
    const intervalId = setInterval(fetchData, 5000);
    return () => clearInterval(intervalId);
  }, [symbol]);

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
        {/* TOP ROW: Chart & Topology Stats */}
        <div className={styles.topRow}>
          <section className={styles.glassPanel}>
            <div className={styles.panelHeader}>
              <BarChart2 className={styles.panelIcon} size={20} />
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
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px'}}>
              <div>
                <h4 style={{marginBottom: '12px', color: 'var(--text-secondary)'}}>System Status</h4>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>DuckDB Vault</span>
                  <span className={styles.statValue} style={{color: 'var(--success)'}}>Connected</span>
                </div>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>FastAPI</span>
                  <span className={styles.statValue} style={{color: 'var(--success)'}}>Active</span>
                </div>
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>CDP Bridge</span>
                  <span className={styles.statValue} style={{color: 'var(--success)'}}>Streaming</span>
                </div>
              </div>

              <div>
                <h4 style={{marginBottom: '12px', color: 'var(--text-secondary)'}}>Magnetic Levels (KDE)</h4>
                {magneticLevels.map((lvl, i) => (
                  <div key={i} className={styles.statRow}>
                    <span className={styles.statLabel}>Node {i+1}</span>
                    <span className={styles.statValue}>{lvl.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* BOTTOM ROW: The Matrix */}
        <section className={styles.glassPanel}>
          <div className={styles.panelHeader}>
            <Crosshair className={styles.panelIcon} size={20} />
            <span className={styles.panelTitle}>Multi-Dimensional Signal Matrix</span>
          </div>

          {!matrixData ? (
            <div style={{padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)'}}>
              Computing Tensor Matrices...
            </div>
          ) : (
            <div className={styles.matrixGrid}>
              {/* Header Row */}
              <div className={styles.gridHeader}>Strategy \ TF</div>
              {timeframes.map(tf => (
                <div key={tf} className={styles.gridHeader}>
                  {tf.toUpperCase()}
                  {matrixData[tf] && matrixData[tf].regime && (
                    <div style={{marginTop: '4px'}}>
                      <span className={`${styles.regimeTag} ${styles['regime' + matrixData[tf].regime]}`}>
                        {matrixData[tf].regime}
                      </span>
                      {matrixData[tf].cs_5d !== undefined && (
                        <div style={{marginTop: '6px', fontSize: '10px', color: 'var(--text-secondary)', textAlign: 'left', background: '#f3f4f6', padding: '6px', borderRadius: '4px', border: '1px solid #e5e7eb', borderLeft: matrixData[tf].kernel_p_value < 0.01 ? '3px solid #16a34a' : '3px solid #dc2626'}}>
                          <div style={{fontWeight: 'bold', marginBottom: '4px', color: '#000'}}>Unified Risk Engine</div>
                          <div>p-value: <span style={{color: matrixData[tf].kernel_p_value < 0.01 ? '#16a34a' : '#dc2626', fontWeight: 'bold'}}>{matrixData[tf].kernel_p_value?.toFixed(3)}</span></div>
                          <div>Kelly Target: <span style={{fontWeight: 'bold', color: '#2563eb'}}>{matrixData[tf].kelly_recommended_pct?.toFixed(2)}%</span></div>
                          <div style={{marginTop: '4px', paddingTop: '4px', borderTop: '1px dashed #d1d5db'}}>CS 5D: <span style={{color: matrixData[tf].cs_5d > 0 ? '#16a34a' : '#dc2626'}}>{matrixData[tf].cs_5d?.toFixed(4)}</span></div>
                          <div>Δ|A|: <span style={{color: matrixData[tf].hyper_instability ? '#dc2626' : '#16a34a'}}>{matrixData[tf].hyper_instability ? 'CRITICAL' : 'Stable'}</span></div>
                          <div>SDE μ: <span>{matrixData[tf].sde_forecast?.toFixed(1)}</span></div>
                          <div>Cheeger: <span>{matrixData[tf].cheeger_invariant?.toFixed(3)}</span></div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Strategy Rows */}
              {strategies.map(strat => (
                <div key={strat.id} style={{ display: 'contents' }} className={strat.id === 'medallion' ? styles.medallionRow : ''}>
                  <div className={styles.strategyLabel}>
                    <div>
                      <div>{strat.name}</div>
                      <div style={{fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 'normal'}}>{strat.type}</div>
                    </div>
                  </div>
                  
                  {timeframes.map(tf => {
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
          <PaperTraderPanel />
        </section>
      </main>
    </div>
  );
}
