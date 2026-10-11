import sys
import os
import argparse
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data.providers.mock_provider import MockMarketDataProvider
from app.simulation.replay_engine import HistoricalReplayEngine

def main():
    parser = argparse.ArgumentParser(description="Run autonomous trading replay simulation.")
    parser.add_argument("--symbol", default="RELIANCE", help="Stock symbol to simulate")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial virtual capital")
    parser.add_argument("--candles", type=int, default=120, help="Number of candles to simulate")
    args = parser.parse_args()

    print(f"=================================================================")
    print(f"  AUTONOMOUS TRADING BOT - REPLAY SIMULATION (CLI)")
    print(f"  SIMULATION ONLY — NO REAL ORDERS WILL EVER BE PLACED")
    print(f"=================================================================")

    start_dt = datetime.now() - timedelta(minutes=args.candles * 5)
    end_dt = datetime.now()

    provider = MockMarketDataProvider(seed=42)
    candles = provider.get_historical_candles(args.symbol, start_dt, end_dt, "5m")
    print(f"Loaded {len(candles)} historical candles for {args.symbol}.")

    replay = HistoricalReplayEngine(
        candles=candles,
        symbol=args.symbol,
        initial_capital=args.capital,
        warmup_period=20
    )

    print("Running autonomous LangGraph agent cycles...")
    results = replay.run()
    eval_m = results["evaluation"]

    print("\n--- SIMULATION RESULTS ---")
    print(f"Initial Capital:         INR {eval_m['initial_capital']:,.2f}")
    print(f"Final Portfolio Value:   INR {eval_m['final_portfolio_value']:,.2f}")
    print(f"Total Return:            {eval_m['total_return_pct']}%")
    print(f"Total Trades:            {eval_m['total_trades']}")
    print(f"Win Rate:                {eval_m['win_rate_pct']}%")
    print(f"Max Drawdown:            {eval_m['max_drawdown_pct']}%")
    print(f"Buy & Hold Return:       {eval_m['benchmark_return_pct']}%")
    print(f"Alpha:                   {eval_m['alpha_pct']}%")
    print(f"Session Audit ID:        {results['session_id']}")
    print("=================================================================\n")

if __name__ == "__main__":
    main()
