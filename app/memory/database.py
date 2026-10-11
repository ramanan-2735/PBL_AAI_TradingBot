import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class SimulationDatabase:
    """Thread-safe SQLite database for audit records, agent memory, and snapshots."""

    def __init__(self, db_path: str = "data/simulation_memory.db"):
        self.db_path = db_path
        self._memory_conn = None
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_sessions (
                session_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                symbol TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Agent decisions audit table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                confidence REAL NOT NULL,
                decision_summary TEXT NOT NULL,
                risk_summary TEXT,
                risk_approved INTEGER NOT NULL,
                risk_reason TEXT,
                raw_indicators TEXT
            )
            """)

            # Executed trades table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                requested_price REAL NOT NULL,
                executed_price REAL NOT NULL,
                slippage REAL NOT NULL,
                fees REAL NOT NULL,
                total_cost REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                decision_summary TEXT
            )
            """)

            # Portfolio snapshots table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL,
                positions_value REAL NOT NULL,
                total_portfolio_value REAL NOT NULL,
                total_pnl REAL NOT NULL,
                total_return_pct REAL NOT NULL
            )
            """)
            conn.commit()

    def record_session(self, session_id: str, mode: str, symbol: str, initial_capital: float):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO simulation_sessions (session_id, mode, symbol, initial_capital) VALUES (?, ?, ?, ?)",
                (session_id, mode, symbol, initial_capital)
            )
            conn.commit()

    def record_decision(
        self,
        session_id: str,
        timestamp: str,
        symbol: str,
        price: float,
        action: str,
        quantity: int,
        confidence: float,
        decision_summary: str,
        risk_summary: str,
        risk_approved: bool,
        risk_reason: str,
        raw_indicators: dict
    ):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_decisions (
                    session_id, timestamp, symbol, price, action, quantity,
                    confidence, decision_summary, risk_summary, risk_approved,
                    risk_reason, raw_indicators
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, timestamp, symbol, price, action, quantity,
                confidence, decision_summary, risk_summary, 1 if risk_approved else 0,
                risk_reason, json.dumps(raw_indicators)
            ))
            conn.commit()

    def record_trade(self, session_id: str, trade: dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades (
                    trade_id, session_id, timestamp, symbol, action, quantity,
                    requested_price, executed_price, slippage, fees, total_cost,
                    realized_pnl, decision_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade["trade_id"], session_id, str(trade["timestamp"]),
                trade["symbol"], trade["action"], trade["quantity"],
                trade["requested_price"], trade["executed_price"], trade["slippage"],
                trade["fees"], trade["total_cost"], trade.get("realized_pnl", 0.0),
                trade.get("decision_summary", "")
            ))
            conn.commit()

    def record_snapshot(self, session_id: str, snap: dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO portfolio_snapshots (
                    session_id, timestamp, cash, positions_value,
                    total_portfolio_value, total_pnl, total_return_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, str(snap["timestamp"]), snap["cash"],
                snap["positions_value"], snap["total_portfolio_value"],
                snap["total_pnl"], snap["total_return_pct"]
            ))
            conn.commit()

    def get_recent_decisions(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, action, symbol, quantity, confidence, decision_summary
                FROM agent_decisions
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_session_trades(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades WHERE session_id = ? ORDER BY timestamp ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_session_snapshots(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM portfolio_snapshots WHERE session_id = ? ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
