import React, { useState } from 'react';
import { Database, Download, Check, RefreshCw } from 'lucide-react';

interface DataDownloadPanelProps {
  onDownload: (params: { symbol: string; preset: string; timeframe: string }) => Promise<void>;
  isDownloading: boolean;
  downloadStatus: string | null;
}

export const DataDownloadPanel: React.FC<DataDownloadPanelProps> = ({
  onDownload,
  isDownloading,
  downloadStatus,
}) => {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [preset, setPreset] = useState('2025');
  const [timeframe, setTimeframe] = useState('5m');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onDownload({ symbol, preset, timeframe });
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-4 shadow-xl text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          <h3 className="font-semibold text-slate-100 text-sm">MARKET DATASET</h3>
        </div>
        <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          PARQUET CACHED
        </span>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
        <div>
          <label className="text-slate-400 block mb-1">Symbol</label>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-semibold focus:outline-none focus:border-sky-500"
          >
            <option value="RELIANCE">RELIANCE (NSE)</option>
            <option value="TCS">TCS (NSE)</option>
            <option value="INFY">INFY (NSE)</option>
            <option value="HDFCBANK">HDFCBANK (NSE)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1">Period</label>
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-sky-500"
          >
            <option value="2025">2025 Calendar Year</option>
            <option value="2024">2024 Calendar Year</option>
            <option value="90d">Last 90 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1">Timeframe</label>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-sky-500"
          >
            <option value="5m">5 Minute</option>
            <option value="1m">1 Minute</option>
            <option value="15m">15 Minute</option>
          </select>
        </div>

        <div className="flex items-end mt-4">
          <button
            type="submit"
            disabled={isDownloading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold transition disabled:opacity-50 cursor-pointer"
          >
            {isDownloading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                Load Dataset
              </>
            )}
          </button>
        </div>
      </form>

      {downloadStatus && (
        <div className="mt-2.5 text-[11px] text-slate-400 bg-slate-800/40 p-2 rounded border border-slate-800 flex items-center gap-1.5">
          <Check className="w-3.5 h-3.5 text-emerald-400" />
          <span>{downloadStatus}</span>
        </div>
      )}
    </div>
  );
};
