import React from 'react';
import { Activity, Bot, Shield, CheckCircle } from 'lucide-react';
import type { ActivityEvent } from '../types/trading';

interface ActivityFeedProps {
  events: ActivityEvent[];
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ events }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'trade':
        return <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      case 'decision':
        return <Bot className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
      case 'risk':
        return <Shield className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-slate-500 shrink-0" />;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-4 shadow-xl text-xs space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h3 className="font-semibold text-slate-100 text-sm">ACTIVITY & AUDIT FEED</h3>
        </div>
        <span className="text-[11px] text-slate-400 font-mono">{events.length} events</span>
      </div>

      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <p className="text-slate-500 italic py-4 text-center">No simulation events yet. Press START to begin replay.</p>
        ) : (
          events.slice(0, 40).map((ev) => (
            <div
              key={ev.id}
              className="flex items-start justify-between gap-2 p-2 rounded bg-slate-800/30 hover:bg-slate-800/60 border border-slate-800/60 transition"
            >
              <div className="flex items-start gap-2">
                <span className="mt-0.5">{getIcon(ev.type)}</span>
                <div>
                  <span className="text-slate-300 block">{ev.message}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {ev.badge && (
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${ev.badgeColor || 'bg-slate-700 text-slate-300'}`}>
                    {ev.badge}
                  </span>
                )}
                <span className="text-[10px] font-mono text-slate-500">{ev.time}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
