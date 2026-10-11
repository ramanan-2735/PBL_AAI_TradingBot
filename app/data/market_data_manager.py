import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import pandas as pd
from app.data.models import MarketCandle
from app.data.normalizer import MarketDataNormalizer
from app.data.providers.dhan_provider import DhanMarketDataProvider
from app.data.providers.mock_provider import MockMarketDataProvider
from app.config import config

logger = logging.getLogger(__name__)

class MarketDataManager:
    """Manages downloading, local Parquet caching, and loading of historical candles.
    Guarantees that repeated requests reuse cached data without hitting APIs unnecessarily.
    """

    def __init__(self, base_cache_dir: Optional[str] = None):
        self.base_cache_dir = base_cache_dir or config.DATA_MARKET_DIR
        os.makedirs(self.base_cache_dir, exist_ok=True)
        self.dhan_provider = DhanMarketDataProvider()
        self.mock_provider = MockMarketDataProvider(seed=42)

    def _get_cache_path(self, symbol: str, start_date: date, end_date: date, timeframe: str) -> str:
        sym_dir = os.path.join(self.base_cache_dir, symbol.upper())
        os.makedirs(sym_dir, exist_ok=True)
        fname = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}_{timeframe}.parquet"
        return os.path.join(sym_dir, fname)

    def is_cached(self, symbol: str, start_date: date, end_date: date, timeframe: str) -> bool:
        cache_file = self._get_cache_path(symbol, start_date, end_date, timeframe)
        return os.path.exists(cache_file) and os.path.getsize(cache_file) > 0

    def load_from_cache(self, symbol: str, start_date: date, end_date: date, timeframe: str) -> Optional[List[MarketCandle]]:
        cache_file = self._get_cache_path(symbol, start_date, end_date, timeframe)
        if not os.path.exists(cache_file):
            return None
        try:
            df = pd.read_parquet(cache_file)
            candles = []
            for _, row in df.iterrows():
                candles.append(MarketCandle(
                    symbol=str(row["symbol"]),
                    timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"])
                ))
            return MarketDataNormalizer.deduplicate_and_sort(candles)
        except Exception as e:
            logger.warning(f"Error reading parquet cache {cache_file}: {e}")
            return None

    def save_to_cache(self, candles: List[MarketCandle], symbol: str, start_date: date, end_date: date, timeframe: str):
        if not candles:
            return
        cache_file = self._get_cache_path(symbol, start_date, end_date, timeframe)
        try:
            records = [{
                "symbol": c.symbol,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume
            } for c in candles]
            df = pd.DataFrame(records)
            df.to_parquet(cache_file, index=False)
            logger.info(f"Cached {len(candles)} candles to {cache_file}")
        except Exception as e:
            logger.error(f"Failed to cache candles to parquet: {e}")

    def get_market_data(
        self,
        symbol: str = "RELIANCE",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframe: str = "5m",
        force_download: bool = False
    ) -> Tuple[List[MarketCandle], str]:
        """Fetches candles: First checks Parquet cache, then tries Dhan if configured,
        or gracefully generates high-fidelity deterministic market data if Dhan is unconfigured.
        """
        symbol = symbol.upper()
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)

        # 1. Check local Parquet cache first
        if not force_download and self.is_cached(symbol, start_date, end_date, timeframe):
            cached = self.load_from_cache(symbol, start_date, end_date, timeframe)
            if cached and len(cached) > 0:
                return cached, "CACHED"

        # 2. Try Dhan API if configured
        candles = []
        source = "DHAN"
        if self.dhan_provider.is_configured():
            dt_start = datetime.combine(start_date, datetime.min.time())
            dt_end = datetime.combine(end_date, datetime.max.time())
            candles = self.dhan_provider.get_historical_candles(symbol, dt_start, dt_end, timeframe)

        # 3. If unconfigured or failed, fallback to high-fidelity Mock provider
        if not candles:
            source = "SYNTHETIC_MARKET_WALK"
            dt_start = datetime.combine(start_date, datetime.min.time())
            dt_end = datetime.combine(end_date, datetime.max.time())
            candles = self.mock_provider.get_historical_candles(symbol, dt_start, dt_end, timeframe)

        # 4. Save to cache
        if candles:
            self.save_to_cache(candles, symbol, start_date, end_date, timeframe)

        return candles, source
