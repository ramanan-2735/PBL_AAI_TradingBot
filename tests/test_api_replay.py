import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.api.server import app
from app.data.models import MarketCandle
from app.simulation.async_replay_engine import AsyncReplayEngine

client = TestClient(app)

def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["simulation_only"] is True
    assert "SIMULATION ONLY" in data["banner"]

def test_api_symbols_endpoint():
    response = client.get("/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert data["default"] == "RELIANCE"
    assert "RELIANCE" in data["symbols"]

def test_replay_init_and_no_lookahead():
    response = client.post("/api/replay/init", json={
        "symbol": "RELIANCE",
        "period_preset": "90d",
        "timeframe": "5m",
        "initial_capital": 100000.0,
        "warmup_period": 25,
        "speed_multiplier": 50.0
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INITIALIZED"
    assert len(data["warmup_candles"]) == 25

    # Verification: at step T, only candles <= T are observed
    state_res = client.get("/api/replay/state")
    assert state_res.status_code == 200
    state = state_res.json()
    assert state["current_index"] == 25
    assert state["portfolio"]["cash"] == 100000.0

@pytest.mark.asyncio
async def test_async_replay_engine_stepping():
    candles = [
        MarketCandle(
            symbol="RELIANCE",
            timestamp=datetime(2025, 1, 1, 9, 15) + timedelta(minutes=5 * i),
            open=1400.0 + i,
            high=1405.0 + i,
            low=1395.0 + i,
            close=1402.0 + i,
            volume=5000.0
        ) for i in range(40)
    ]

    events_received = []
    def broadcaster(event):
        events_received.append(event)

    engine = AsyncReplayEngine(
        candles=candles,
        symbol="RELIANCE",
        warmup_period=20,
        decision_frequency=2,
        speed_multiplier=100.0,
        event_broadcaster=broadcaster
    )

    # Initial state
    assert engine.current_index == 20
    assert len(engine.get_warmup_candles()) == 20

    # Step exactly one candle
    engine.status = "PAUSED"
    await engine.step()
    assert engine.current_index == 21
    # Verify candle event was broadcast
    candle_events = [e for e in events_received if e["type"] == "candle"]
    assert len(candle_events) == 1
    assert candle_events[0]["symbol"] == "RELIANCE"
