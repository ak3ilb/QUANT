'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';

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
}

export default function TradingChart({ data, regime, signal, magneticLevels = [] }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };

    // Determine background color based on regime
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
      crosshair: {
        mode: 1, // Normal
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
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
      // Sort data by time
      const sorted = [...data].sort((a, b) => {
        const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : a.time;
        const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : b.time;
        return timeA - timeB;
      });
      
      // Ensure time is in the format lightweight-charts expects (YYYY-MM-DD or unix timestamp in seconds)
      const formattedData = sorted.map(d => {
        let t = d.time;
        if (typeof t === 'string' && t.includes('T')) {
          t = t.split('T')[0]; // Extract YYYY-MM-DD
        }
        return { ...d, time: t as any };
      });

      // Deduplicate by time
      const uniqueData = [];
      const seen = new Set();
      for (const d of formattedData) {
        if (!seen.has(d.time)) {
          seen.add(d.time);
          uniqueData.push(d);
        }
      }

      try {
        candlestickSeries.setData(uniqueData);
      } catch (e) {
        console.error("Error setting chart data", e);
      }
    }

    // Add markers for current signal if provided
    if (signal && data && data.length > 0) {
      const lastItem = data[data.length - 1];
      let t = lastItem.time;
      if (typeof t === 'string' && t.includes('T')) t = t.split('T')[0];
      
      try {
        if (signal === 'BUY') {
          candlestickSeries.setMarkers([
            { time: t as any, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'BUY' }
          ]);
        } else if (signal === 'SELL') {
          candlestickSeries.setMarkers([
            { time: t as any, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'SELL' }
          ]);
        }
      } catch (e) {
        console.error("Marker error:", e);
      }
    }

    // Add horizontal price lines for magnetic levels
    if (magneticLevels && magneticLevels.length > 0) {
      magneticLevels.forEach(level => {
        candlestickSeries.createPriceLine({
          price: level,
          color: 'rgba(59, 130, 246, 0.5)',
          lineWidth: 2,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'KDE Node',
        });
      });
    }

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, regime, signal, magneticLevels]);

  return (
    <div 
      ref={chartContainerRef} 
      style={{ width: '100%', height: '100%', minHeight: '400px' }} 
    />
  );
}
