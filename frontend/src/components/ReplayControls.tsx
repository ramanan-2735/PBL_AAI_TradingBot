import React from 'react';
import { Play, Pause, StepForward, Square, RotateCcw, FastForward, Clock } from 'lucide-react';
import type { ReplayState } from '../types/trading';

interface ReplayControlsProps {
  replayState: ReplayState;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStep: () => void;
  onStop: () => void;
  onRestart: () => void;
  onSpeedChange: (speed: number) => void;
}

const SPEEDS = [0.5, 1, 2, 5, 10, 25, 50, 100];

export const ReplayControls: React.FC<ReplayControlsProps> = ({
  replayState,
  onStart,
  onPause,
  onResume,
  onStep,
  onStop,
  onRestart,
  onSpeedChange,
}) => {
  const isRunning = replayState.status === 'RUNNING';
  const isPaused = replayState.status === 'PAUSED';

  // Format historical simulation time nicely
  const formatSimulationTime = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const dt = new Date(isoString);
      return dt.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-3.5 shadow-xl flex flex-wrap items-center justify-between gap-4 text-xs">
      {/* Simulation Clock & Progress */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <Clock className="w-4 h-4 text-sky-400" />
          <div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Simulation Time</span>
            <span className="font-mono font-semibold text-slate-200">
              {formatSimulationTime(replayState.simulation_timestamp)}
            </span>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 text-slate-400 text-[11px] mb-1">
            <span>Candle {replayState.current_index} / {replayState.total_candles}</span>
            <span className="font-mono text-slate-200">({replayState.progress_pct}%)</span>
          </div>
          <div className="w-36 h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-emerald-500 transition-all duration-200"
              style={{ width: `${replayState.progress_pct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Primary Action Buttons */}
      <div className="flex items-center gap-2">
        {replayState.status === 'IDLE' || replayState.status === 'STOPPED' || replayState.status === 'COMPLETED' ? (
          <button
            onClick={onStart}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-lg shadow-emerald-600/20 transition cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            START SIMULATION
          </button>
        ) : isRunning ? (
          <button
            onClick={onPause}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold transition cursor-pointer"
          >
            <Pause className="w-3.5 h-3.5 fill-current" />
            PAUSE
          </button>
        ) : (
          <button
            onClick={onResume}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            RESUME
          </button>
        )}

        <button
          onClick={onStep}
          disabled={!isPaused}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 border border-slate-700 transition cursor-pointer"
          title="Step 1 Candle"
        >
          <StepForward className="w-4 h-4" />
        </button>

        <button
          onClick={onStop}
          disabled={replayState.status === 'IDLE'}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 border border-slate-700 transition cursor-pointer"
          title="Stop Replay"
        >
          <Square className="w-4 h-4" />
        </button>

        <button
          onClick={onRestart}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer"
          title="Restart Replay"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Speed Selector */}
      <div className="flex items-center gap-1.5 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
        <FastForward className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-0.5" />
        {SPEEDS.map(spd => (
          <button
            key={spd}
            onClick={() => onSpeedChange(spd)}
            className={`px-2 py-1 rounded text-[11px] font-mono font-semibold transition cursor-pointer ${
              replayState.speed === spd
                ? 'bg-sky-500 text-slate-900 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {spd}x
          </button>
        ))}
      </div>
    </div>
  );
};
