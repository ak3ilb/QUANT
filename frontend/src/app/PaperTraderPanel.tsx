"use client";

import React, { useEffect, useState } from "react";
import styles from "./page.module.css";

interface Trade {
  trade_id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_time: string;
  entry_price: number;
  size_usd: number;
  qty: number;
  status: "OPEN" | "CLOSED";
  exit_time?: string;
  exit_price?: number;
  pnl_usd?: number;
  pnl_pct?: number;
  kelly_pct: number;
  confidence: number;
  fees_paid: number;
  leveraged_size: number;
}

interface LedgerResponse {
  balance: number;
  open_positions: Trade[];
  history: Trade[];
  error?: string;
}

export default function PaperTraderPanel() {
  const [data, setData] = useState<LedgerResponse | null>(null);

  useEffect(() => {
    const fetchLedger = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/paper-ledger");
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to fetch paper ledger:", err);
      }
    };

    fetchLedger();
    const interval = setInterval(fetchLedger, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!data) {
    return (
      <div className={`${styles.panel} ${styles.glassPanel}`}>
        <h2 className={styles.panelTitle}>Medallion Paper Trader</h2>
        <div className={styles.loading}>Connecting to Execution Daemon...</div>
      </div>
    );
  }

  const balanceColor = data.balance >= 100 ? "#00ff88" : "#ff3366";

  return (
    <div className={`${styles.panel} ${styles.glassPanel}`}>
      <div className={styles.paperHeader}>
        <h2 className={styles.panelTitle}>Medallion Execution Engine</h2>
        <div className={styles.balanceDisplay}>
          <span className={styles.balanceLabel}>Account Equity</span>
          <span className={styles.balanceValue} style={{ color: balanceColor }}>
            ${data.balance.toFixed(2)}
          </span>
        </div>
      </div>

      <div className={styles.paperContent}>
        <div className={styles.positionsSection}>
          <h3 className={styles.subTitle}>Active Positions</h3>
          {data.open_positions && data.open_positions.length > 0 ? (
            <div className={styles.tradeList}>
              {data.open_positions.map((trade) => (
                <div key={trade.trade_id} className={styles.tradeCard}>
                  <div className={styles.tradeRow}>
                    <span className={trade.direction === "BUY" ? styles.textGreen : styles.textRed}>
                      {trade.direction} {trade.symbol}
                    </span>
                    <span>${trade.leveraged_size.toFixed(2)} (Lev: 100x)</span>
                  </div>
                  <div className={styles.tradeRow}>
                    <span className={styles.textMuted}>Margin: ${trade.size_usd.toFixed(2)}</span>
                    <span className={styles.textMuted}>Conf: {(trade.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className={styles.tradeRow}>
                    <span className={styles.textMuted}>Entry: ${trade.entry_price.toFixed(2)}</span>
                    <span className={styles.textRed}>Fees: -${trade.fees_paid.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>No open positions. Scanning market...</div>
          )}
        </div>

        <div className={styles.historySection}>
          <h3 className={styles.subTitle}>Ledger History</h3>
          <div className={styles.ledgerTable}>
            {data.history && data.history.length > 0 ? (
              data.history.map((trade) => {
                const isWin = (trade.pnl_usd || 0) > 0;
                return (
                  <div key={trade.trade_id} className={styles.ledgerRow}>
                    <div className={styles.ledgerInfo}>
                      <span className={trade.direction === "BUY" ? styles.textGreen : styles.textRed}>
                        {trade.direction}
                      </span>
                      <span> {trade.symbol}</span>
                      <span className={styles.textMuted}> • {new Date(trade.exit_time || "").toLocaleTimeString()}</span>
                    </div>
                    <div className={isWin ? styles.textGreen : styles.textRed}>
                      {isWin ? "+" : ""}${trade.pnl_usd?.toFixed(2)} ({(trade.pnl_pct! * 100).toFixed(2)}%)
                    </div>
                  </div>
                );
              })
            ) : (
              <div className={styles.emptyState}>Ledger is empty.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
