"use client";

import React, { useEffect, useState } from "react";
import styles from "./page.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001/api";

interface Trade {
  trade_id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_time: string;
  entry_price: number;
  size_usd: number;
  qty: number;
  lots?: number;
  leverage?: number;
  notional_usd?: number;
  spread_width?: number;
  swap_usd?: number;
  status: "OPEN" | "CLOSED";
  exit_time?: string;
  exit_price?: number;
  pnl_usd?: number;
  pnl_pct?: number;
  kelly_pct: number;
  confidence: number;
  fees_paid: number;
  leveraged_size: number;
  stop_price?: number;
  sde_target?: number;
  current_price?: number;
  unrealized_pnl?: number;
  live_confidence?: number;
  close_reason?: string;
}

interface AccountInfo {
  type: string;
  initial_deposit: number;
  max_leverage: number;
  commission: string;
  min_spread: string;
}

interface LedgerStats {
  win_rate: number;
  total_spread_cost?: number;
  total_fees: number;
  total_trades: number;
  wins: number;
  losses: number;
}

interface LedgerResponse {
  balance: number;
  equity: number;
  locked_margin: number;
  unrealized_pnl: number;
  account?: AccountInfo;
  stats: LedgerStats;
  open_positions: Trade[];
  history: Trade[];
  error?: string;
}

function fmtTime(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  // Stable format avoids SSR/client locale hydration mismatch
  return d.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

function fmtDuration(start?: string, end?: string) {
  if (!start || !end) return "";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

function pnlClass(value: number) {
  if (value > 0) return styles.textGreen;
  if (value < 0) return styles.textRed;
  return styles.textMuted;
}

interface Props {
  symbol?: string;
}

export default function PaperTraderPanel({ symbol }: Props) {
  const [data, setData] = useState<LedgerResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLedger = async () => {
      try {
        const res = await fetch(`${API_BASE}/paper-ledger`);
        const json = await res.json();
        if (json.error) {
          setFetchError(json.error);
        } else {
          setFetchError(null);
        }
        setData(json);
      } catch (err) {
        setFetchError("Cannot reach backend API");
        console.error("Failed to fetch paper ledger:", err);
      }
    };

    fetchLedger();
    const interval = setInterval(fetchLedger, 2000);
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

  const filterSymbol = symbol?.toUpperCase();
  const openPositions = (data.open_positions || []).filter(
    (t) => !filterSymbol || t.symbol === filterSymbol
  );
  const history = (data.history || []).filter(
    (t) => !filterSymbol || t.symbol === filterSymbol
  );

  const equity = data.equity ?? data.balance;
  const equityColor = equity >= 100 ? "var(--success)" : "var(--danger)";

  return (
    <div className={`${styles.panel} ${styles.glassPanel}`}>
      <div className={styles.paperHeader}>
        <h2 className={styles.panelTitle}>
          Standard Paper Account
          {data.account ? ` (${data.account.type})` : ""}
        </h2>
        <div className={styles.balanceDisplay}>
          <span className={styles.balanceLabel}>Equity</span>
          <span className={styles.balanceValue} style={{ color: equityColor }}>
            ${equity.toFixed(2)}
          </span>
        </div>
      </div>

      {data.account && (
        <div className={styles.summaryBar}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Deposit</span>
            <span className={styles.summaryValue}>${data.account.initial_deposit.toFixed(0)}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Max leverage</span>
            <span className={styles.summaryValue}>1:{data.account.max_leverage}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Spread (min)</span>
            <span className={styles.summaryValue}>{data.account.min_spread}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Commission</span>
            <span className={styles.summaryValue}>{data.account.commission}</span>
          </div>
        </div>
      )}

      {fetchError && (
        <div className={styles.errorBanner}>{fetchError}</div>
      )}

      <div className={styles.summaryBar}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Cash</span>
          <span className={styles.summaryValue}>${(data.balance ?? 0).toFixed(2)}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Locked Margin</span>
          <span className={styles.summaryValue}>${(data.locked_margin ?? 0).toFixed(2)}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Unrealized P&L</span>
          <span className={`${styles.summaryValue} ${pnlClass(data.unrealized_pnl ?? 0)}`}>
            {(data.unrealized_pnl ?? 0) >= 0 ? "+" : ""}${(data.unrealized_pnl ?? 0).toFixed(2)}
          </span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Win Rate</span>
          <span className={styles.summaryValue}>
            {((data.stats?.win_rate ?? 0) * 100).toFixed(0)}% ({data.stats?.wins ?? 0}W / {data.stats?.losses ?? 0}L)
          </span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Spread (round-trip est.)</span>
          <span className={styles.summaryValue}>
            ${(data.stats?.total_spread_cost ?? data.stats?.total_fees ?? 0).toFixed(2)}
          </span>
        </div>
      </div>

      <div className={styles.paperContent}>
        <div className={styles.positionsSection}>
          <h3 className={styles.subTitle}>Active Positions {filterSymbol ? `(${filterSymbol})` : ""}</h3>
          {openPositions.length > 0 ? (
            <div className={styles.tradeList}>
              {openPositions.map((trade) => {
                const mark = trade.current_price ?? trade.entry_price;
                const unrealized = trade.unrealized_pnl ?? 0;
                const lots = trade.lots ?? trade.qty;
                const leverage = trade.leverage ?? 2000;
                const notional = trade.notional_usd ?? trade.leveraged_size;
                const stopDist = trade.stop_price
                  ? trade.direction === "BUY"
                    ? ((trade.stop_price - mark) / mark * 100).toFixed(2)
                    : ((mark - trade.stop_price) / mark * 100).toFixed(2)
                  : null;
                const sdeDist = trade.sde_target
                  ? trade.direction === "BUY"
                    ? ((trade.sde_target - mark) / mark * 100).toFixed(2)
                    : ((mark - trade.sde_target) / mark * 100).toFixed(2)
                  : null;
                return (
                  <div key={trade.trade_id} className={styles.tradeCard}>
                    <div className={styles.tradeRow}>
                      <span className={trade.direction === "BUY" ? styles.textGreen : styles.textRed}>
                        {trade.direction} {trade.symbol.replace("USD", "")}
                      </span>
                      <span className={styles.textMuted}>{trade.trade_id}</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Volume (lots)</span>
                      <span>{lots.toFixed(2)}</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Open time</span>
                      <span>{fmtTime(trade.entry_time)}</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Open / Current</span>
                      <span>${trade.entry_price.toFixed(2)} → ${mark.toFixed(2)}</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>P/L, USD</span>
                      <span className={pnlClass(unrealized)}>
                        {unrealized >= 0 ? "+" : ""}${unrealized.toFixed(2)}
                      </span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Swap, USD</span>
                      <span>${(trade.swap_usd ?? 0).toFixed(2)}</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>S/L (20% margin)</span>
                      <span className={styles.textRed}>
                        ${trade.stop_price?.toFixed(2) ?? "—"}
                        {stopDist ? ` (${stopDist}%)` : ""}
                      </span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>T/P (SDE)</span>
                      <span className={styles.textGreen}>
                        ${trade.sde_target?.toFixed(2) ?? "—"}
                        {sdeDist ? ` (${sdeDist}%)` : ""}
                      </span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Margin / Lev</span>
                      <span>
                        ${trade.size_usd.toFixed(2)} / 1:{leverage.toFixed(0)} (${notional.toFixed(2)})
                      </span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Spread</span>
                      <span>{(trade.spread_width ?? 0.2).toFixed(2)} (in price)</span>
                    </div>
                    <div className={styles.tradeRow}>
                      <span className={styles.textMuted}>Conf (entry → live)</span>
                      <span>
                        {(trade.confidence * 100).toFixed(1)}%
                        {trade.live_confidence != null
                          ? ` → ${(trade.live_confidence * 100).toFixed(1)}%`
                          : ""}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.emptyState}>No open positions. Scanning market...</div>
          )}
        </div>

        <div className={styles.historySection}>
          <h3 className={styles.subTitle}>Trade History</h3>
          <div className={styles.ledgerTable}>
            {history.length > 0 ? (
              history.map((trade) => {
                const pnl = trade.pnl_usd ?? 0;
                return (
                  <div key={trade.trade_id} className={styles.ledgerRow}>
                    <div className={styles.ledgerDetail}>
                      <div className={styles.ledgerInfo}>
                        <span className={trade.direction === "BUY" ? styles.textGreen : styles.textRed}>
                          {trade.direction}
                        </span>
                        <span>{trade.symbol}</span>
                        {trade.close_reason && (
                          <span className={styles.reasonBadge}>{trade.close_reason}</span>
                        )}
                      </div>
                      <div className={styles.ledgerMeta}>
                        <span>{fmtTime(trade.entry_time)} → {fmtTime(trade.exit_time)}</span>
                        <span className={styles.textMuted}>
                          {fmtDuration(trade.entry_time, trade.exit_time)}
                        </span>
                      </div>
                      <div className={styles.ledgerMeta}>
                        <span>
                          ${trade.entry_price?.toFixed(2)} → ${trade.exit_price?.toFixed(2)}
                        </span>
                        <span className={styles.textMuted}>
                          {(trade.lots ?? trade.qty)?.toFixed?.(2) ?? trade.qty} lots
                        </span>
                      </div>
                    </div>
                    <div className={`${styles.ledgerPnl} ${pnlClass(pnl)}`}>
                      {pnl > 0 ? "+" : ""}${pnl.toFixed(2)}
                      <div className={styles.textMuted} style={{ fontSize: "0.75rem" }}>
                        {((trade.pnl_pct ?? 0) * 100).toFixed(2)}% on margin
                      </div>
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
