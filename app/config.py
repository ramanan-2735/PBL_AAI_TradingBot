import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class AppConfig(BaseModel):
    # Safety Banner
    SIMULATION_MODE_ONLY: bool = True
    SAFETY_BANNER: str = "SIMULATION ONLY — NO REAL ORDERS"

    # Dhan API (Market Data Only)
    DHAN_CLIENT_ID: str = Field(default_factory=lambda: os.getenv("DHAN_CLIENT_ID", ""))
    DHAN_ACCESS_TOKEN: str = Field(default_factory=lambda: os.getenv("DHAN_ACCESS_TOKEN", ""))
    DHAN_BASE_URL: str = Field(default_factory=lambda: os.getenv("DHAN_BASE_URL", "https://api.dhan.co/v2"))
    DHAN_WSS_URL: str = Field(default_factory=lambda: os.getenv("DHAN_WSS_URL", "wss://api-feed.dhan.co"))

    # LLM Provider Configuration
    LLM_BASE_URL: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    LLM_API_KEY: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    LLM_MODEL: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    LLM_TEMPERATURE: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1")))

    # Simulation Defaults
    INITIAL_CAPITAL: float = Field(default_factory=lambda: float(os.getenv("INITIAL_CAPITAL", "100000.0")))
    CURRENCY: str = "INR"
    LONG_ONLY: bool = True
    ALLOW_LEVERAGE: bool = False
    SIMULATION_SLIPPAGE_BPS: float = Field(default_factory=lambda: float(os.getenv("SIMULATION_SLIPPAGE_BPS", "5.0")))
    TRANSACTION_COST_PCT: float = Field(default_factory=lambda: float(os.getenv("TRANSACTION_COST_PCT", "0.0003")))

    # Risk Limits (Deterministic Safety Controls)
    MAX_POSITION_PCT: float = Field(default_factory=lambda: float(os.getenv("RISK_MAX_POSITION_PCT", "0.25")))
    MAX_ORDER_PCT: float = Field(default_factory=lambda: float(os.getenv("RISK_MAX_ORDER_PCT", "0.10")))
    DAILY_LOSS_LIMIT_PCT: float = Field(default_factory=lambda: float(os.getenv("RISK_DAILY_LOSS_LIMIT_PCT", "0.05")))
    MAX_DAILY_TRADES: int = 50

    # Paths
    DATABASE_PATH: str = "data/simulation_memory.db"
    DATA_MARKET_DIR: str = "data/market"
    CACHE_DIR: str = "data/cache"
    SAMPLE_DIR: str = "data/sample"

    # Default Demo Configuration
    DEFAULT_SYMBOL: str = "RELIANCE"
    DEFAULT_EXCHANGE: str = "NSE"
    DEFAULT_TIMEFRAME: str = "5m"

config = AppConfig()
