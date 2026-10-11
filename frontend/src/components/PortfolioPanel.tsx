import React from 'react';
import { Wallet } from 'lucide-react';
import type { PortfolioState } from '../types/trading';

interface PortfolioPanelProps {
  portfolio: PortfolioState;
  currentPrice: number;
}

export const PortfolioPanel: React.FC<PortfolioPanelProps> = ({ portfolio, currentPrice }) => {
  const isPositive = portfolio.total_return_pct >= 0;
  const totalPnl = portfolio.realized_pnl + portfolio.unrealized_pnl;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-4 shadow-xl text-xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Wallet className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">VIRTUAL PORTFOLIO</h3>
            <p className="text-[11px] text-slate-400">Simulation Account (Long-Only)</p>
          </div>
        </div>
        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[11px] border border-emerald-500/20">
          ₹1,00,000 BASE
        </span>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-0.5">Portfolio Value</span>
          <span className="text-xs font-bold font-mono text-slate-100">
            ₹{portfolio.portfolio_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Base: ₹1,00,000</span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-0.5">Virtual Cash</span>
          <span className="text-xs font-bold font-mono text-slate-100">
            ₹{portfolio.cash.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            {((portfolio.cash / Math.max(portfolio.portfolio_value, 1)) * 100).toFixed(1)}% liquid
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-0.5">Invested Stock</span>
          <span className="text-xs font-bold font-mono text-slate-100">
            ₹{portfolio.invested.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            {portfolio.holdings_quantity > 0 ? `${portfolio.holdings_quantity} × ₹${currentPrice.toFixed(1)}` : '0 allocated'}
          </span>
        </div>

        <div className={`p-2.5 rounded-lg border ${portfolio.holdings_quantity > 0 ? 'bg-sky-950/20 border-sky-800/60' : 'bg-slate-800/40 border-slate-800'}`}>
          <span className="text-slate-400 block mb-0.5">Shares Held</span>
          <span className={`text-xs font-bold font-mono ${portfolio.holdings_quantity > 0 ? 'text-sky-400' : 'text-slate-400'}`}>
            {portfolio.holdings_quantity} Shares
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            {portfolio.holdings_quantity > 0 ? 'RELIANCE Long' : 'No open shares'}
          </span>
        </div>

        <div className={`p-2.5 rounded-lg border ${totalPnl >= 0 ? 'bg-emerald-950/20 border-emerald-900/50' : 'bg-rose-950/20 border-rose-900/50'}`}>
          <span className="text-slate-400 block mb-0.5">Total Profit / P&L</span>
          <span className={`text-xs font-bold font-mono ${totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toFixed(2)}
          </span>
          <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">
            R: {portfolio.realized_pnl >= 0 ? '+' : ''}₹{portfolio.realized_pnl.toFixed(1)} | U: {portfolio.unrealized_pnl >= 0 ? '+' : ''}₹{portfolio.unrealized_pnl.toFixed(1)}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-0.5">Total Return</span>
          <span className={`text-xs font-bold font-mono ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isPositive ? '+' : ''}{portfolio.total_return_pct.toFixed(2)}%
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Net simulation return</span>
        </div>
      </div>

      {/* Current Position Details */}
      <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">RELIANCE Position Status</span>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${portfolio.holdings_quantity > 0 ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' : 'bg-slate-700/40 text-slate-400'}`}>
              {portfolio.holdings_quantity > 0 ? `HOLDING ${portfolio.holdings_quantity} SHARES` : 'FLAT / NO POSITION'}
            </span>
          </div>
          <span className="font-mono text-slate-300 text-[11px]">
            {portfolio.holdings_quantity > 0 ? `Current Value: ₹${(portfolio.holdings_quantity * currentPrice).toFixed(2)}` : '100% Cash'}
          </span>
        </div>

        {portfolio.holdings_quantity > 0 && (
          <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
            <div>
              <span className="text-slate-400 block text-[10px]">Avg Entry Price</span>
              <span className="font-mono text-slate-200 font-semibold">₹{portfolio.average_entry_price.toFixed(2)}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Current LTP</span>
              <span className="font-mono text-slate-200 font-semibold">₹{currentPrice.toFixed(2)}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Invested Value</span>
              <span className="font-mono text-slate-200 font-semibold">₹{(portfolio.holdings_quantity * portfolio.average_entry_price).toFixed(2)}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Unrealized P&L</span>
              <span className={`font-mono font-bold ${portfolio.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {portfolio.unrealized_pnl >= 0 ? '+' : ''}₹{portfolio.unrealized_pnl.toFixed(2)}
                {portfolio.average_entry_price > 0 && (
                  <span className="text-[10px] ml-1">
                    ({((portfolio.unrealized_pnl / (portfolio.holdings_quantity * portfolio.average_entry_price)) * 100).toFixed(2)}%)
                  </span>
                )}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
