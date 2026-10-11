import React, { useEffect, useRef } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  createSeriesMarkers,
} from 'lightweight-charts';
import type {
  IChartApi,
  ISeriesApi,
  CandlestickData,
  UTCTimestamp,
  SeriesMarker,
  Time,
} from 'lightweight-charts';
import type { Candle, Indicators, Trade } from '../types/trading';

interface TradingChartProps {
  candles: Candle[];
  indicators: Indicators | null;
  trades: Trade[];
}

export const TradingChart: React.FC<TradingChartProps> = ({ candles, indicators, trades }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const sma20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const sma50SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markersRef = useRef<any>(null);

  // Initialize TradingView Lightweight Chart (v5 API)
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 480,
      layout: {
        background: { color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.4)' },
        horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
      },
      crosshair: {
        mode: 1,
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
    });

    // In Lightweight Charts v5: chart.addSeries(CandlestickSeries, options)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    const sma20Series = chart.addSeries(LineSeries, {
      color: '#38bdf8', // Light sky blue
      lineWidth: 2,
      title: 'SMA 20',
    });

    const sma50Series = chart.addSeries(LineSeries, {
      color: '#f59e0b', // Amber
      lineWidth: 2,
      title: 'SMA 50',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candleSeries;
    sma20SeriesRef.current = sma20Series;
    sma50SeriesRef.current = sma50Series;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  const parseTime = (ts: string): Time => {
    return Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp;
  };

  // Update data when candles change
  useEffect(() => {
    if (!candlestickSeriesRef.current || candles.length === 0) return;

    const formattedCandles: CandlestickData[] = candles.map((c) => ({
      time: parseTime(c.timestamp),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candlestickSeriesRef.current.setData(formattedCandles);

    // Apply BUY / SELL markers in v5 using createSeriesMarkers
    if (trades.length > 0) {
      const markers: SeriesMarker<Time>[] = trades.map((t) => ({
        time: parseTime(t.timestamp),
        position: t.action === 'BUY' ? 'belowBar' : 'aboveBar',
        color: t.action === 'BUY' ? '#10b981' : '#ef4444',
        shape: t.action === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: `${t.action} ${t.quantity} @ ₹${t.price.toFixed(2)}`,
        size: 2,
      }));

      if (markersRef.current) {
        markersRef.current.setMarkers(markers);
      } else {
        markersRef.current = createSeriesMarkers(candlestickSeriesRef.current, markers);
      }
    }
  }, [candles, trades]);

  // Update SMA Lines
  useEffect(() => {
    if (!indicators || !candles.length) return;

    try {
      if (sma20SeriesRef.current && indicators.sma_20 !== null) {
        sma20SeriesRef.current.update({
          time: parseTime(indicators.timestamp),
          value: indicators.sma_20,
        });
      }

      if (sma50SeriesRef.current && indicators.sma_50 !== null) {
        sma50SeriesRef.current.update({
          time: parseTime(indicators.timestamp),
          value: indicators.sma_50,
        });
      }
    } catch {
      // Ignore timestamp duplicate or out-of-order updates safely
    }
  }, [indicators]);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 bg-slate-900 shadow-2xl">
      {/* Chart Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-slate-200">RELIANCE 5M</span>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
            <span className="text-slate-400">SMA 20:</span>
            <span className="font-mono text-sky-400">{indicators?.sma_20 ? `₹${indicators.sma_20.toFixed(2)}` : '—'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span className="text-slate-400">SMA 50:</span>
            <span className="font-mono text-amber-400">{indicators?.sma_50 ? `₹${indicators.sma_50.toFixed(2)}` : '—'}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-slate-400">RSI (14):</span>
          <span className={`font-mono font-bold ${
            (indicators?.rsi ?? 50) > 70 ? 'text-rose-400' : (indicators?.rsi ?? 50) < 35 ? 'text-emerald-400' : 'text-slate-200'
          }`}>
            {indicators?.rsi ? indicators.rsi.toFixed(1) : '—'}
          </span>
        </div>
      </div>

      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
};
