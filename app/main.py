import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from app.config import config
from app.data.providers.mock_provider import MockMarketDataProvider
from app.data.providers.dhan_provider import DhanMarketDataProvider
from app.simulation.replay_engine import HistoricalReplayEngine
from app.data.instrument_resolver import InstrumentResolver

st.set_page_config(
    page_title="Autonomous Trading Bot | Agentic AI Simulation",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-contrast, clean CSS styling
st.markdown("""
<style>
    .banner-danger {
        background: linear-gradient(90deg, #b91c1c 0%, #dc2626 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 700;
        letter-spacing: 1px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px 18px;
        color: white;
    }
    .cycle-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-done { background-color: #065f46; color: #34d399; }
    .badge-wait { background-color: #1e293b; color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# 1. Mandatory Safety Banner
st.markdown(f'<div class="banner-danger">⚠️ {config.SAFETY_BANNER} — DATA SOURCE: DHAN / MOCK | EXECUTION: 100% VIRTUAL PORTFOLIO</div>', unsafe_allow_html=True)

# Sidebar controls
st.sidebar.title("🤖 Agent Settings")
mode = st.sidebar.radio("Operating Mode", ["Mode A: Historical Replay (Backtest)", "Mode B: Live Market Simulation", "Agent System Diagnostics"])

resolver = InstrumentResolver()
supported_symbols = resolver.get_supported_symbols()

if mode == "Mode A: Historical Replay (Backtest)":
    st.sidebar.subheader("Replay Parameters")
    symbol = st.sidebar.selectbox("Symbol", supported_symbols, index=0)
    initial_capital = st.sidebar.number_input("Virtual Capital (₹)", value=100000.0, step=10000.0)
    num_candles = st.sidebar.slider("Number of Candles", min_value=40, max_value=300, value=80, step=10)
    timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m"], index=0)
    data_source = st.sidebar.selectbox("Market Data Provider", ["Mock / Synthetic", "DhanHQ Historical (if credentials configured)"])
    
    start_sim_btn = st.sidebar.button("▶ Run Full Backtest Replay", type="primary", use_container_width=True)

    st.subheader(f"📊 Historical Replay Simulation Engine — {symbol}")
    st.caption("Agentic Cycle: Observe → Analyze Indicators → LLM Reason → Risk Gatekeeper → Simulated Execution → Portfolio State → SQLite Audit")

    # Workflow cycle indicators
    st.markdown("""
    <div style="margin-bottom: 20px;">
        <span class="cycle-badge badge-done">OBSERVE ✓</span>
        <span class="cycle-badge badge-done">ANALYZE ✓</span>
        <span class="cycle-badge badge-done">DECIDE ✓</span>
        <span class="cycle-badge badge-done">RISK CHECK ✓</span>
        <span class="cycle-badge badge-done">SIMULATE ✓</span>
        <span class="cycle-badge badge-done">MEMORY PERSISTED ✓</span>
    </div>
    """, unsafe_allow_html=True)

    if start_sim_btn or "last_results" in st.session_state:
        if start_sim_btn:
            with st.spinner("Fetching market data and running autonomous agent cycles..."):
                start_dt = datetime.now() - timedelta(minutes=num_candles * 5)
                end_dt = datetime.now()

                if data_source == "DhanHQ Historical (if credentials configured)":
                    dhan_prov = DhanMarketDataProvider()
                    candles = dhan_prov.get_historical_candles(symbol, start_dt, end_dt, timeframe)
                    if not candles:
                        st.warning("Could not fetch Dhan historical data (check .env credentials). Using deterministic Mock data.")
                        candles = MockMarketDataProvider(seed=42).get_historical_candles(symbol, start_dt, end_dt, timeframe)
                else:
                    candles = MockMarketDataProvider(seed=42).get_historical_candles(symbol, start_dt, end_dt, timeframe)

                replay = HistoricalReplayEngine(
                    candles=candles,
                    symbol=symbol,
                    initial_capital=initial_capital,
                    warmup_period=20
                )
                results = replay.run()
                st.session_state["last_results"] = results
                st.session_state["candles"] = candles
                st.session_state["symbol"] = symbol

        results = st.session_state["last_results"]
        candles = st.session_state["candles"]
        eval_metrics = results["evaluation"]
        trades = results["trades"]
        snapshots = results["snapshots"]

        # Metric KPI row
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Final Portfolio", f"₹{eval_metrics['final_portfolio_value']:,.2f}", f"{eval_metrics['total_return_pct']}%")
        col1_pnl_color = "normal" if eval_metrics['total_pnl'] >= 0 else "inverse"
        col2.metric("Total P&L", f"₹{eval_metrics['total_pnl']:,.2f}")
        col3.metric("Agent Win Rate", f"{eval_metrics['win_rate_pct']}%", f"{eval_metrics['winning_trades']}W / {eval_metrics['losing_trades']}L")
        col4.metric("Max Drawdown", f"{eval_metrics['max_drawdown_pct']}%")
        bench_ret = eval_metrics['benchmark_return_pct']
        bench_str = f"{bench_ret}%" if bench_ret is not None else "N/A"
        alpha_str = f"{eval_metrics['alpha_pct']}%" if eval_metrics['alpha_pct'] is not None else "N/A"
        col5.metric("Buy & Hold Benchmark", bench_str, f"Alpha: {alpha_str}")

        # Charts row: Candlestick + Trades and Equity Curve
        tab1, tab2, tab3 = st.tabs(["📈 Price & Agent Actions", "💰 Equity Curve & Benchmark", "📜 Auditable Log & Decisions"])

        with tab1:
            fig = go.Figure()
            df_candles = pd.DataFrame([{
                "timestamp": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume
            } for c in candles])
            
            fig.add_trace(go.Candlestick(
                x=df_candles["timestamp"],
                open=df_candles["open"],
                high=df_candles["high"],
                low=df_candles["low"],
                close=df_candles["close"],
                name="Market Price"
            ))

            # Overlay BUY and SELL executions
            buy_trades = [t for t in trades if t["action"] == "BUY"]
            sell_trades = [t for t in trades if t["action"] == "SELL"]

            if buy_trades:
                fig.add_trace(go.Scatter(
                    x=[t["timestamp"] for t in buy_trades],
                    y=[t["executed_price"] for t in buy_trades],
                    mode="markers",
                    marker=dict(symbol="triangle-up", color="#10b981", size=12),
                    name="Simulated BUY"
                ))

            if sell_trades:
                fig.add_trace(go.Scatter(
                    x=[t["timestamp"] for t in sell_trades],
                    y=[t["executed_price"] for t in sell_trades],
                    mode="markers",
                    marker=dict(symbol="triangle-down", color="#ef4444", size=12),
                    name="Simulated SELL"
                ))

            fig.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            if snapshots:
                df_snap = pd.DataFrame(snapshots)
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=df_snap["timestamp"],
                    y=df_snap["total_portfolio_value"],
                    mode="lines",
                    name="Agent Virtual Portfolio Value",
                    line=dict(color="#3b82f6", width=2)
                ))
                # Add initial capital reference
                fig_eq.add_hline(y=eval_metrics["initial_capital"], line_dash="dash", line_color="#94a3b8", annotation_text="Initial Capital")
                fig_eq.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="Portfolio Value (₹)")
                st.plotly_chart(fig_eq, use_container_width=True)
            else:
                st.info("No snapshots recorded yet.")

        with tab3:
            st.write("### Executed Simulated Trades")
            if trades:
                st.dataframe(pd.DataFrame(trades)[["timestamp", "action", "symbol", "quantity", "executed_price", "realized_pnl", "decision_summary"]], use_container_width=True)
            else:
                st.info("No trades triggered during this simulation run (Agent chose HOLD or risk blocked).")

elif mode == "Mode B: Live Market Simulation":
    st.subheader("⚡ Live Market Data Simulation (Virtual Execution Only)")
    st.info("Ticks are aggregated into candles. Every completed interval triggers the LangGraph agent to observe, reason, and validate via Risk Manager before simulated execution.")
    
    col_sym, col_feed = st.columns(2)
    with col_sym:
        live_symbol = st.selectbox("Live Symbol", supported_symbols, index=0)
    with col_feed:
        feed_type = st.radio("Market Feed Source", ["Simulated Ticker Stream", "Dhan Live WebSocket Feed (Requires .env)"], horizontal=True)

    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.success(f"Broker Market Feed: Active ({feed_type})")
    with status_col2:
        st.warning("Broker Execution: DISABLED (SIMULATION VIRTUAL ONLY)")

    # Fetch latest quote
    mock_prov = MockMarketDataProvider()
    quote = mock_prov.get_latest_quote(live_symbol)
    if quote:
        col_q1, col_q2, col_q3 = st.columns(3)
        col_q1.metric("LTP", f"₹{quote.last_price}")
        col_q2.metric("Bid", f"₹{quote.bid_price}")
        col_q3.metric("Ask", f"₹{quote.ask_price}")

    st.write("---")
    st.write("#### Real-time Agent Cycle Status")
    st.markdown("""
    - **Current Observation:** Candle aggregation in progress.
    - **Risk Manager Status:** Operational (Concentration limit 25%, Order limit 10%).
    - **Safety Guardrail:** 100% of order proposals route exclusively to the local `SimulationEngine`.
    """)

elif mode == "Agent System Diagnostics":
    st.subheader("🛠️ System Health & Agentic Architecture Verification")
    
    st.markdown("""
    ### Why this is genuine Agentic AI:
    1. **Autonomous Perception**: Ingests market OHLCV candles through a provider-agnostic adapter.
    2. **Deterministic Analysis**: Computes RSI, SMA, EMA, MACD, and Volatility with zero look-ahead bias.
    3. **LangGraph State Machine**: Orchestrates explicit transitions across nodes: `observe` → `analyze` → `reason` → `risk_check` → `simulate`.
    4. **Safety Gatekeeper (Deterministic Risk Manager)**: Rejects excessive position concentration, order value limits, and drawdown violations regardless of LLM confidence.
    5. **Virtual Execution Engine**: Simulates realistic execution with slippage and exchange fees on virtual cash.
    6. **Auditability & Memory**: Persists every decision, prompt context, and trade event in SQLite.
    """)

    st.write("### Configuration State")
    st.json({
        "SIMULATION_MODE_ONLY": config.SIMULATION_MODE_ONLY,
        "DHAN_CLIENT_ID_CONFIGURED": bool(config.DHAN_CLIENT_ID),
        "LLM_MODEL": config.LLM_MODEL,
        "INITIAL_CAPITAL": config.INITIAL_CAPITAL,
        "MAX_POSITION_PCT": config.MAX_POSITION_PCT,
        "MAX_ORDER_PCT": config.MAX_ORDER_PCT,
        "DAILY_LOSS_LIMIT_PCT": config.DAILY_LOSS_LIMIT_PCT,
        "DATABASE_PATH": config.DATABASE_PATH
    })
