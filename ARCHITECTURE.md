# Architectural Specification — React + FastAPI + LangGraph

## 1. System Topology
The platform separates presentation and quant computation cleanly:

```
[React + Vite + TypeScript (Port 5173)]
   │
   ├── REST (/api/replay/*, /api/market/*) ──────────┐
   └── WebSocket (/ws event stream) ──────────────┐   │
                                                  │   │
                                                  ▼   ▼
                                       [FastAPI + Uvicorn (Port 8000)]
                                                  │
                                       ┌──────────┴──────────┐
                                       ▼                     ▼
                               [AsyncReplayEngine]    [MarketDataManager]
                                       │                     │
                                       ▼                     ▼
                               [TradingAgentGraph]     [Parquet Cache / DhanHQ v2]
                                       │
                                       ▼
                               [RiskManager Gatekeeper]
                                       │
                                       ▼
                               [SimulationEngine + SQLite Memory]
```

## 2. Event Stream Contract (WebSocket `/ws`)
The FastAPI server streams incremental, strongly-typed JSON events:
- `candle`: Pushes newly arrived OHLCV bar with progressive index.
- `indicators_update`: Pushes updated SMA20, SMA50, RSI14, and Trend.
- `agent_status`: Transitions status (`OBSERVING`, `ANALYZING`, `DECIDING`, `EXECUTING`).
- `agent_decision`: Carries `action` (BUY/SELL/HOLD), `confidence`, and auditable summary.
- `risk`: Gatekeeper decision (`APPROVED`/`REJECTED`) with explicit reason.
- `trade`: Executed virtual trade with execution price, fees, and realized P&L.
- `portfolio_update`: Real-time virtual cash, invested balance, and return percentage.
- `simulation_status`: Current lifecycle state (`IDLE`, `RUNNING`, `PAUSED`, `COMPLETED`).

## 3. Strict No Look-Ahead Verification
At any replay step index $k$, the data visible to indicator calculations and agent context is strictly bounded to $C_{0:k}$. In `AsyncReplayEngine._process_step`, the slice `self.candles[:idx + 1]` is passed to `MarketAnalyzer.analyze_window()`. Future candles are never exposed to any analytical or decision-making routine before their simulated timestamp occurs.

## 4. Voice AI Architecture (Control Layer Separation)
Voice interaction operates purely as an out-of-band **control and announcement layer** with zero impact on quantitative reasoning or deterministic risk limits:

```
[React Browser Microphone]
        │ (Push-to-Talk WebM audio blob)
        ▼
[FastAPI /api/voice/command]
        │
        ▼
[faster-whisper (tiny.en on CPU INT8)]
        │ (Transcript)
        ▼
[Deterministic Command Parser] ──(Rejects arbitrary chat / direct trades)──► UNKNOWN
        │ (START / PAUSE / RESUME / STEP / SET_SPEED)
        ▼
[AsyncReplayEngine] ──(Reuses identical button controllers)──► Chart & State Replay
        │
        ▼
[Supertonic-3 Local TTS] (Cached WAV Responses)
        │
        ▼
[React Audio Playback Queue] (Sequential HTMLAudioElement, zero overlap)
```
