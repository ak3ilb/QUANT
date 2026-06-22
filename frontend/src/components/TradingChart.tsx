'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';

export interface TradeOverlay {
  entry_price: number;
  stop_price?: number;
  sde_target?: number;
  exit_price?: number;
  direction: 'BUY' | 'SELL';
  status: 'OPEN' | 'CLOSED';
}

interface ChartProps {
  data: Array<{
    time: string | number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  regime?: string;
  signal?: string;
  magneticLevels?: number[];
  tradeOverlays?: TradeOverlay[];
}

export default function TradingChart({
  data,
  regime,
  signal,
  magneticLevels = [],
  tradeOverlays = [],
}: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    let bgColor = '#0b0e14';
    if (regime === 'Bull') bgColor = '#0b1410';
    else if (regime === 'Bear') bgColor = '#1a0b0f';
    else if (regime === 'Sideways') bgColor = '#17140b';

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: bgColor },
        textColor: '#a0aec0',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    if (data && data.length > 0) {
      const sorted = [...data].sort((a, b) => {
        const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : a.time;
        const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : b.time;
        return timeA - timeB;
      });

      const formattedData = sorted.map((d) => {
        let t = d.time;
        if (typeof t === 'string' && t.includes('T')) {
          t = t.split('T')[0];
        }
        return { ...d, time: t as string | number };
      });

      const uniqueData = [];
      const seen = new Set<string | number>();
      for (const d of formattedData) {
        if (!seen.has(d.time)) {
          seen.add(d.time);
          uniqueData.push(d);
        }
      }

      try {
        candlestickSeries.setData(uniqueData as Parameters<typeof candlestickSeries.setData>[0]);
      } catch (e) {
        console.error('Error setting chart data', e);
      }
    }

    if (signal && data && data.length > 0) {
      const lastItem = data[data.length - 1];
      let t = lastItem.time;
      if (typeof t === 'string' && t.includes('T')) t = t.split('T')[0];

      try {
        if (signal === 'BUY') {
          candlestickSeries.setMarkers([
            { time: t as never, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'BUY' },
          ]);
        } else if (signal === 'SELL') {
          candlestickSeries.setMarkers([
            { time: t as never, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'SELL' },
          ]);
        }
      } catch (e) {
        console.error('Marker error:', e);
      }
    }

    magneticLevels.forEach((level) => {
      candlestickSeries.createPriceLine({
        price: level,
        color: 'rgba(59, 130, 246, 0.5)',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'KDE Node',
      });
    });

    tradeOverlays.forEach((trade) => {
      candlestickSeries.createPriceLine({
        price: trade.entry_price,
        color: trade.direction === 'BUY' ? '#10b981' : '#ef4444',
        lineWidth: +2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `Entry ${trade.direction}`,
      });
      if (trade.stop_price) {
        candlestickSeries.createPriceLine({
          price: trade.stop_price,
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'Stop -2%',
        });
      }
      if (trade.sde_target) {
        candlestickSeries.createPriceLine({
          price: trade.sde_target,
          color: '#3b82f6',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'SDE Target',
        });
      }
      if (trade.status === 'CLOSED' && trade.exit_price) {
        candlestickSeries.createPriceLine({
          price: trade.exit_price,
          color: '#a855f7',
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: true,
          title: 'Exit',
        });
      }
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, regime, signal, magneticLevels, tradeOverlays]);

  return (
    <div
      ref={chartContainerRef}
      style={{ width: '100%', height: '100%', minHeight: '400px' }}
    />
  );
}
