export interface Candle {
  timestamp: string;
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  index?: number;
  total?: number;
}

export interface Indicators {
  timestamp: string;
  price: number;
  sma_20: number | null;
  sma_50: number | null;
  rsi: number | null;
  trend: string;
  strategy_signal: string;
  strategy_reason: string;
}

export interface AgentDecision {
  timestamp: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  symbol: string;
  quantity: number;
  confidence: number;
  decision_summary: string;
  risk_summary: string;
  conditions_to_reconsider?: string[];
}

export interface Trade {
  trade_id: string;
  timestamp: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  requested_price: number;
  fees: number;
  realized_pnl: number;
  decision_summary?: string;
}

export interface PortfolioState {
  initial_capital: number;
  cash: number;
  invested: number;
  portfolio_value: number;
  total_return_pct: number;
  realized_pnl: number;
  unrealized_pnl: number;
  holdings_quantity: number;
  average_entry_price: number;
}

export interface ActivityEvent {
  id: string;
  time: string;
  type: 'candle' | 'agent' | 'decision' | 'risk' | 'trade' | 'portfolio' | 'system';
  message: string;
  badge?: string;
  badgeColor?: string;
}

export interface ReplayState {
  status: 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'STOPPED' | 'ERROR';
  current_index: number;
  total_candles: number;
  progress_pct: number;
  simulation_timestamp: string;
  current_price: number;
  speed: number;
}
