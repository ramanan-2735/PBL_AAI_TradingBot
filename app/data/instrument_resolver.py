import logging
from typing import Dict, Optional
import requests
import json
import os

logger = logging.getLogger(__name__)

class InstrumentResolver:
    """Resolves standard NSE stock tickers (e.g., RELIANCE, TCS) to Dhan security IDs.
    Uses official Dhan scrip master and fallback cache.
    """
    
    # Authoritative offline fallback mappings for major NSE equities
    DEFAULT_EQUITY_MAP: Dict[str, dict] = {
        "RELIANCE": {"security_id": "2885", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "TCS": {"security_id": "11536", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "INFY": {"security_id": "1594", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "HDFCBANK": {"security_id": "1333", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "TATAMOTORS": {"security_id": "3456", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "ICICIBANK": {"security_id": "4963", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
        "SBIN": {"security_id": "3045", "exchange_segment": "NSE_EQ", "instrument": "EQUITY", "lot_size": 1},
    }

    DHAN_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

    def __init__(self, cache_file: str = "data/cache/instruments.json"):
        self.cache_file = cache_file
        self.instruments: Dict[str, dict] = dict(self.DEFAULT_EQUITY_MAP)
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cached = json.load(f)
                    self.instruments.update(cached)
            except Exception as e:
                logger.warning(f"Could not load instrument cache: {e}")

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.instruments, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save instrument cache: {e}")

    def resolve(self, symbol: str) -> Optional[dict]:
        sym = symbol.upper().strip()
        if sym in self.instruments:
            return self.instruments[sym]
        return None

    def get_security_id(self, symbol: str) -> Optional[str]:
        info = self.resolve(symbol)
        return info["security_id"] if info else None

    def get_supported_symbols(self) -> list[str]:
        return list(self.instruments.keys())
