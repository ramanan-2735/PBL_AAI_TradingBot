import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import config
from app.data.market_data_manager import MarketDataManager
from app.data.instrument_resolver import InstrumentResolver
from app.data.providers.dhan_provider import DhanMarketDataProvider
from app.simulation.async_replay_engine import AsyncReplayEngine
from app.api.websocket_manager import manager
from app.memory.database import SimulationDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("autonomous_trader_api")

app = FastAPI(
    title="Autonomous Trading Bot API",
    description="High-performance simulation backend powered by LangGraph, FastAPI, and WebSocket events.",
    version="2.0.0"
)

# Enable CORS for React frontend (Vite default ports 5173, 3000, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Singletons
market_manager = MarketDataManager()
resolver = InstrumentResolver()
db = SimulationDatabase()
current_replay_engine: Optional[AsyncReplayEngine] = None


# Request / Response Schemas
class ReplayInitRequest(BaseModel):
    symbol: str = "RELIANCE"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period_preset: Optional[str] = "2025"  # 2024, 2025, 2026, 30d, 90d, 6m
    timeframe: str = "5m"
    initial_capital: float = 100000.0
    warmup_period: int = 30
    decision_frequency: int = 5
    speed_multiplier: float = 25.0
    force_download: bool = False

class SpeedUpdateRequest(BaseModel):
    speed: float = Field(..., ge=0.5, le=100.0)

# Endpoints
@app.get("/api/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "simulation_only": config.SIMULATION_MODE_ONLY,
        "banner": config.SAFETY_BANNER,
        "dhan_configured": DhanMarketDataProvider().is_configured(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/symbols")
async def get_supported_symbols():
    return {
        "default": config.DEFAULT_SYMBOL,
        "symbols": resolver.get_supported_symbols()
    }

@app.post("/api/market/download")
async def download_market_data(req: ReplayInitRequest):
    """Downloads and caches market data for the selected symbol and timeframe."""
    sym = req.symbol.upper()
    
    # Resolve dates from preset
    start_dt, end_dt = _resolve_dates(req.period_preset, req.start_date, req.end_date)
    
    candles, source = market_manager.get_market_data(
        symbol=sym,
        start_date=start_dt,
        end_date=end_dt,
        timeframe=req.timeframe,
        force_download=req.force_download
    )

    if not candles:
        raise HTTPException(status_code=400, detail=f"No market data could be retrieved for {sym}.")

    return {
        "symbol": sym,
        "candle_count": len(candles),
        "source": source,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "timeframe": req.timeframe,
        "cached": True
    }

@app.post("/api/replay/init")
async def initialize_replay(req: ReplayInitRequest):
    """Initializes a new replay engine session and loads warm-up candles."""
    global current_replay_engine
    
    if current_replay_engine and current_replay_engine.status == "RUNNING":
        await current_replay_engine.stop()

    start_dt, end_dt = _resolve_dates(req.period_preset, req.start_date, req.end_date)
    candles, source = market_manager.get_market_data(
        symbol=req.symbol,
        start_date=start_dt,
        end_date=end_dt,
        timeframe=req.timeframe,
        force_download=req.force_download
    )

    if not candles or len(candles) < 20:
        raise HTTPException(status_code=400, detail="Insufficient candles retrieved to initialize replay.")

    current_replay_engine = AsyncReplayEngine(
        candles=candles,
        symbol=req.symbol,
        initial_capital=req.initial_capital,
        warmup_period=req.warmup_period,
        decision_frequency=req.decision_frequency,
        speed_multiplier=req.speed_multiplier,
        slippage_bps=config.SIMULATION_SLIPPAGE_BPS,
        transaction_cost_pct=config.TRANSACTION_COST_PCT,
        db=db,
        event_broadcaster=manager.broadcast
    )

    return {
        "status": "INITIALIZED",
        "session_id": current_replay_engine.session_id,
        "symbol": current_replay_engine.symbol,
        "total_candles": len(candles),
        "warmup_candles": current_replay_engine.get_warmup_candles(),
        "data_source": source,
        "initial_capital": req.initial_capital,
        "speed": req.speed_multiplier
    }

@app.post("/api/replay/control/{action}")
async def control_replay(action: str):
    """Controls replay: start, pause, resume, step, stop, restart."""
    global current_replay_engine
    if not current_replay_engine:
        raise HTTPException(status_code=400, detail="No active replay session. Call /api/replay/init first.")

    act = action.lower()
    if act == "start":
        await current_replay_engine.start()
    elif act == "pause":
        await current_replay_engine.pause()
    elif act == "resume":
        await current_replay_engine.resume()
    elif act == "step":
        await current_replay_engine.step()
    elif act == "stop":
        await current_replay_engine.stop()
    elif act == "restart":
        await current_replay_engine.restart()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'. Use start/pause/resume/step/stop/restart.")

    return {"status": current_replay_engine.status, "action": act}

@app.post("/api/replay/speed")
async def update_speed(req: SpeedUpdateRequest):
    global current_replay_engine
    if not current_replay_engine:
        raise HTTPException(status_code=400, detail="No active replay session.")
    current_replay_engine.set_speed(req.speed)
    return {"speed": req.speed}

@app.get("/api/replay/state")
async def get_replay_state():
    global current_replay_engine
    if not current_replay_engine:
        return {"status": "NO_SESSION"}
    return current_replay_engine.get_current_snapshot()

@app.get("/api/replay/history")
async def get_session_history(session_id: Optional[str] = None):
    sid = session_id or (current_replay_engine.session_id if current_replay_engine else "")
    if not sid:
        return {"trades": [], "decisions": []}
    trades = db.get_session_trades(sid)
    decisions = db.get_recent_decisions(sid, limit=50)
    return {"session_id": sid, "trades": trades, "decisions": decisions}

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send immediate state on connect
    if current_replay_engine:
        await websocket.send_json({
            "type": "initial_state",
            "snapshot": current_replay_engine.get_current_snapshot()
        })
    try:
        while True:
            data = await websocket.receive_text()
            # Handle possible incoming client commands via WS
            try:
                msg = eval(data) if data.startswith("{") else {}
                if isinstance(msg, dict) and "action" in msg:
                    act = msg["action"].lower()
                    if current_replay_engine:
                        if act == "start":
                            await current_replay_engine.start()
                        elif act == "pause":
                            await current_replay_engine.pause()
                        elif act == "resume":
                            await current_replay_engine.resume()
            except Exception:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

def _resolve_dates(preset: Optional[str], custom_start: Optional[str], custom_end: Optional[str]):
    today = date.today()
    if preset == "2024":
        return date(2024, 1, 1), date(2024, 12, 31)
    elif preset == "2025":
        return date(2025, 1, 1), date(2025, 12, 31)
    elif preset == "2026":
        return date(2026, 1, 1), min(today, date(2026, 12, 31))
    elif preset == "30d":
        return today - timedelta(days=30), today
    elif preset == "90d":
        return today - timedelta(days=90), today
    elif preset == "6m":
        return today - timedelta(days=180), today
    
    # Custom dates
    if custom_start and custom_end:
        return date.fromisoformat(custom_start), date.fromisoformat(custom_end)
    return date(2025, 1, 1), date(2025, 12, 31)
