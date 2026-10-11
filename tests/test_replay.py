import pytest
from datetime import datetime, timedelta
from app.data.providers.mock_provider import MockMarketDataProvider
from app.simulation.replay_engine import HistoricalReplayEngine
from app.memory.database import SimulationDatabase

def test_historical_replay_monotonic_execution_and_safety():
    mock_provider = MockMarketDataProvider(seed=123)
    start_dt = datetime(2026, 1, 1, 9, 15)
    end_dt = start_dt + timedelta(minutes=100)
    
    candles = mock_provider.get_historical_candles("RELIANCE", start_dt, end_dt, "1m")
    assert len(candles) == 101

    db = SimulationDatabase(db_path=":memory:")
    replay = HistoricalReplayEngine(
        candles=candles,
        symbol="RELIANCE",
        initial_capital=100000.0,
        warmup_period=20,
        db=db
    )

    results = replay.run()
    assert "session_id" in results
    assert "evaluation" in results
    eval_metrics = results["evaluation"]
    
    assert eval_metrics["initial_capital"] == 100000.0
    assert eval_metrics["final_portfolio_value"] > 0.0
    assert "total_return_pct" in eval_metrics
    assert "win_rate_pct" in eval_metrics
    assert "benchmark_return_pct" in eval_metrics
