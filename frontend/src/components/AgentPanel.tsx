import React from 'react';
import { Bot, ShieldCheck, ShieldAlert } from 'lucide-react';
import type { Indicators, AgentDecision } from '../types/trading';

interface AgentPanelProps {
  status: string;
  indicators: Indicators | null;
  decision: AgentDecision | null;
  riskStatus: string;
  riskReason: string;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({
  status,
  indicators,
  decision,
  riskStatus,
  riskReason,
}) => {
  const getActionBadge = (action?: string) => {
    switch (action) {
      case 'BUY':
        return <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">BUY</span>;
      case 'SELL':
        return <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">SELL</span>;
      default:
        return <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-slate-700/50 text-slate-300 border border-slate-600/30">HOLD</span>;
    }
  };

  const getStatusBadge = (s: string) => {
    const colors: Record<string, string> = {
      OBSERVING: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
      ANALYZING: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
      DECIDING: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
      EXECUTING: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      WAITING: 'text-slate-400 bg-slate-800 border-slate-700',
    };
    return (
      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${colors[s] || 'text-slate-400 bg-slate-800'}`}>
        {s}
      </span>
    );
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-4 shadow-xl flex flex-col gap-4 text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">🤖 AUTONOMOUS AGENT</h3>
            <p className="text-[11px] text-slate-400">LangGraph Orchestrated Reasoning</p>
          </div>
        </div>
        {getStatusBadge(status || 'WAITING')}
      </div>

      {/* Grid of Key Variables */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-1">Market Trend</span>
          <span className={`font-semibold ${indicators?.trend === 'BULLISH' ? 'text-emerald-400' : indicators?.trend === 'BEARISH' ? 'text-rose-400' : 'text-slate-300'}`}>
            {indicators?.trend || 'NEUTRAL'}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <span className="text-slate-400 block mb-1">Strategy Signal</span>
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-200">{indicators?.strategy_signal || 'HOLD'}</span>
            {indicators?.strategy_signal === 'BUY' && <span className="w-2 h-2 rounded-full bg-emerald-400"></span>}
          </div>
        </div>
      </div>

      {/* Latest Decision Card */}
      <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-800/80 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 font-medium">Agent Decision</span>
          {getActionBadge(decision?.action)}
        </div>

        {decision && (
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Confidence:</span>
              <span className="font-mono text-emerald-400">{(decision.confidence * 100).toFixed(0)}%</span>
            </div>
            {decision.quantity > 0 && (
              <div className="flex justify-between text-slate-300">
                <span className="text-slate-400">Target Quantity:</span>
                <span className="font-mono">{decision.quantity} shares</span>
              </div>
            )}
            <div className="text-[11px] text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800/60 mt-1">
              <p className="text-slate-400 font-medium mb-0.5">Audit Summary:</p>
              {decision.decision_summary}
            </div>
          </div>
        )}
      </div>

      {/* Deterministic Risk Gatekeeper Status */}
      <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-800/80 flex items-start gap-2.5">
        {riskStatus === 'APPROVED' ? (
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        ) : (
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        )}
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-200">Risk Gatekeeper:</span>
            <span className={`text-[11px] font-bold ${riskStatus === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {riskStatus || 'OPERATIONAL'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">{riskReason || 'Concentration and drawdown limits verified.'}</p>
        </div>
      </div>
    </div>
  );
};
