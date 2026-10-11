import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';
import { TradingChart } from './components/TradingChart';
import { AgentPanel } from './components/AgentPanel';
import { PortfolioPanel } from './components/PortfolioPanel';
import { ReplayControls } from './components/ReplayControls';
import { ActivityFeed } from './components/ActivityFeed';
import { DataDownloadPanel } from './components/DataDownloadPanel';
import type {
  Candle,
  Indicators,
  AgentDecision,
  Trade,
  PortfolioState,
  ActivityEvent,
  ReplayState,
} from './types/trading';

const INITIAL_PORTFOLIO: PortfolioState = {
  initial_capital: 100000,
  cash: 100000,
  invested: 0,
  portfolio_value: 100000,
  total_return_pct: 0,
  realized_pnl: 0,
  unrealized_pnl: 0,
  holdings_quantity: 0,
  average_entry_price: 0,
};

const INITIAL_REPLAY: ReplayState = {
  status: 'IDLE',
  current_index: 0,
  total_candles: 0,
  progress_pct: 0,
  simulation_timestamp: '',
  current_price: 1450.0,
  speed: 25,
};

export const App: React.FC = () => {
  // Application State
  const [candles, setCandles] = useState<Candle[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [decision, setDecision] = useState<AgentDecision | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioState>(INITIAL_PORTFOLIO);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [replayState, setReplayState] = useState<ReplayState>(INITIAL_REPLAY);
  const [agentStatus, setAgentStatus] = useState<string>('WAITING');
  const [riskStatus, setRiskStatus] = useState<string>('OPERATIONAL');
  const [riskReason, setRiskReason] = useState<string>('Limits enforced');
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  // Helper to add events
  const addEvent = (
    type: ActivityEvent['type'],
    message: string,
    badge?: string,
    badgeColor?: string
  ) => {
    const newEvent: ActivityEvent = {
      id: Math.random().toString(36).substring(7),
      time: new Date().toLocaleTimeString('en-IN', { hour12: false }),
      type,
      message,
      badge,
      badgeColor,
    };
    setEvents((prev) => [newEvent, ...prev.slice(0, 100)]);
  };

  // Connect WebSocket with robust reconnection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isUnmounted = false;

    const connect = () => {
      if (isUnmounted) return;
      // Connect directly to FastAPI port 8000 or via proxy
      const wsUrl = `ws://${window.location.hostname}:8000/ws`;
      ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        addEvent('system', 'Connected to FastAPI simulation feed', 'ONLINE', 'bg-emerald-500/20 text-emerald-400');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketEvent(data);
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onclose = () => {
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        if (ws) ws.close();
      };
    };

    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  // Handle stream events
  const handleWebSocketEvent = (event: any) => {
    switch (event.type) {
      case 'candle':
        setCandles((prev) => [...prev, event]);
        setReplayState((prev) => ({
          ...prev,
          current_index: event.index,
          total_candles: event.total,
          progress_pct: Math.round((event.index / Math.max(event.total, 1)) * 100),
          simulation_timestamp: event.timestamp,
          current_price: event.close,
        }));
        break;

      case 'indicators_update':
        setIndicators(event);
        break;

      case 'agent_status':
        setAgentStatus(event.status);
        break;

      case 'agent_decision':
        setDecision(event);
        setAgentStatus('DECIDED');
        addEvent(
          'decision',
          `Agent reasoned: ${event.action} (${(event.confidence * 100).toFixed(0)}% conf) - ${event.decision_summary}`,
          event.action,
          event.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : event.action === 'SELL' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-700 text-slate-300'
        );
        break;

      case 'risk':
        setRiskStatus(event.status);
        setRiskReason(event.reason);
        if (event.status !== 'APPROVED') {
          addEvent('risk', `Risk Rejected: ${event.reason}`, 'REJECTED', 'bg-rose-500/20 text-rose-400');
        }
        break;

      case 'trade':
        setTrades((prev) => [...prev, event]);
        addEvent(
          'trade',
          `Simulated execution: ${event.action} ${event.quantity} shares @ ₹${event.price.toFixed(2)}`,
          event.action,
          event.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
        );
        break;

      case 'portfolio_update':
        setPortfolio(event);
        break;

      case 'simulation_status':
        setReplayState((prev) => ({
          ...prev,
          status: event.status,
        }));
        if (event.status === 'RUNNING') setAgentStatus('OBSERVING');
        break;

      case 'simulation_completed':
        setReplayState((prev) => ({ ...prev, status: 'COMPLETED' }));
        setAgentStatus('WAITING');
        addEvent('system', `Simulation completed! Final Return: ${event.evaluation?.total_return_pct}%`, 'COMPLETE', 'bg-sky-500/20 text-sky-400');
        break;
    }
  };

  // Load dataset and initialize
  const handleLoadDataset = async (params: { symbol: string; preset: string; timeframe: string }) => {
    setIsDownloading(true);
    setDownloadStatus('Downloading & validating historical data...');
    try {
      const res = await fetch('/api/replay/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: params.symbol,
          period_preset: params.preset,
          timeframe: params.timeframe,
          initial_capital: 100000,
          speed_multiplier: replayState.speed,
        }),
      });

      if (!res.ok) throw new Error('Failed to load dataset');
      const data = await res.json();

      setCandles(data.warmup_candles || []);
      setReplayState((prev) => ({
        ...prev,
        status: 'IDLE',
        current_index: data.warmup_candles?.length || 0,
        total_candles: data.total_candles,
        progress_pct: Math.round(((data.warmup_candles?.length || 0) / data.total_candles) * 100),
        simulation_timestamp: data.warmup_candles?.[data.warmup_candles.length - 1]?.timestamp || '',
      }));
      setTrades([]);
      setPortfolio(INITIAL_PORTFOLIO);
      setDownloadStatus(`✓ ${data.total_candles} candles cached & ready for simulation`);
      addEvent('system', `Loaded ${data.symbol} (${data.total_candles} candles). Press START to begin replay.`);
    } catch (err: any) {
      setDownloadStatus(`Error loading dataset: ${err.message}`);
    } finally {
      setIsDownloading(false);
    }
  };

  // Initial auto-load of RELIANCE 2025 on mount
  useEffect(() => {
    handleLoadDataset({ symbol: 'RELIANCE', preset: '2025', timeframe: '5m' });
  }, []);

  // Replay Control Handlers
  const handleStart = async () => {
    await fetch('/api/replay/control/start', { method: 'POST' });
  };

  const handlePause = async () => {
    await fetch('/api/replay/control/pause', { method: 'POST' });
  };

  const handleResume = async () => {
    await fetch('/api/replay/control/resume', { method: 'POST' });
  };

  const handleStep = async () => {
    await fetch('/api/replay/control/step', { method: 'POST' });
  };

  const handleStop = async () => {
    await fetch('/api/replay/control/stop', { method: 'POST' });
  };

  const handleRestart = async () => {
    await fetch('/api/replay/control/restart', { method: 'POST' });
    setTrades([]);
    setPortfolio(INITIAL_PORTFOLIO);
    setDecision(null);
    setIndicators(null);
  };

  const handleSpeedChange = async (spd: number) => {
    setReplayState((prev) => ({ ...prev, speed: spd }));
    await fetch('/api/replay/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed: spd }),
    });
  };

  return (
    <div className="min-h-screen bg-[#0b0e14] text-slate-100 flex flex-col">
      {/* 1. Header Bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/90 sticky top-0 z-50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <h1 className="font-bold text-base tracking-wide text-slate-100">AUTONOMOUS TRADING TERMINAL</h1>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-slate-200">RELIANCE</span>
            <span className="text-slate-400">NSE</span>
            <span className="font-mono text-emerald-400 font-semibold">
              ₹{replayState.current_price.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Safety Badge */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold tracking-wider">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>SIMULATION ONLY — NO REAL ORDERS</span>
        </div>
      </header>

      {/* 2. Main Content Grid */}
      <main className="flex-1 p-5 max-w-7xl mx-auto w-full space-y-4">
        {/* Replay Controls & Timeline Bar */}
        <ReplayControls
          replayState={replayState}
          onStart={handleStart}
          onPause={handlePause}
          onResume={handleResume}
          onStep={handleStep}
          onStop={handleStop}
          onRestart={handleRestart}
          onSpeedChange={handleSpeedChange}
        />


        {/* Primary View: Chart (Left) + Agent Panel (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <TradingChart
              candles={candles}
              indicators={indicators}
              trades={trades}
            />
            {/* Portfolio Summary Card */}
            <PortfolioPanel
              portfolio={portfolio}
              currentPrice={replayState.current_price}
            />
          </div>

          {/* Right Column: AI Agent + Market Data Downloader */}
          <div className="space-y-4">
            <AgentPanel
              status={agentStatus}
              indicators={indicators}
              decision={decision}
              riskStatus={riskStatus}
              riskReason={riskReason}
            />
            <DataDownloadPanel
              onDownload={handleLoadDataset}
              isDownloading={isDownloading}
              downloadStatus={downloadStatus}
            />
          </div>
        </div>

        {/* Activity & Event Log */}
        <ActivityFeed events={events} />
      </main>

      {/* Footer */}
      <footer className="px-6 py-2 border-t border-slate-900 bg-slate-950 text-[11px] text-slate-500 flex justify-between items-center">
        <span>College Mini Project: Agentic AI Autonomous Trading Bot (LangGraph + FastAPI + React)</span>
        <span>Guaranteed Zero Look-Ahead Bias | 100% Virtual Portfolio Accounting</span>
      </footer>
    </div>
  );
};

export default App;
