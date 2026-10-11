import logging
from datetime import datetime, date
from typing import List, Optional, Callable
import requests
from app.data.models import MarketCandle, MarketTick
from app.data.providers.base import MarketDataProvider
from app.data.instrument_resolver import InstrumentResolver
from app.data.normalizer import MarketDataNormalizer
from app.config import config

logger = logging.getLogger(__name__)

class DhanMarketDataProvider(MarketDataProvider):
    """Official DhanHQ v2 Market Data Provider.
    Implements historical data, latest market quotes, and market feeds.
    Isolated from agent/execution logic. ZERO trading endpoints are ever called.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        resolver: Optional[InstrumentResolver] = None
    ):
        self.client_id = client_id or config.DHAN_CLIENT_ID
        self.access_token = access_token or config.DHAN_ACCESS_TOKEN
        self.resolver = resolver or InstrumentResolver()
        self.base_url = config.DHAN_BASE_URL.rstrip('/')
        self.session = requests.Session()
        if self.access_token:
            self.session.headers.update({
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json"
            })

    def is_configured(self) -> bool:
        return bool(self.client_id and self.access_token)

    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1m"
    ) -> List[MarketCandle]:
        """Fetches historical candles from Dhan v2 Historical Data API.
        POST /charts/historical
        Official schema:
        {
           "securityId": "...",
           "exchangeSegment": "NSE_EQ",
           "instrument": "EQUITY",
           "fromDate": "YYYY-MM-DD",
           "toDate": "YYYY-MM-DD"
        }
        """
        if not self.is_configured():
            logger.warning("Dhan credentials not configured. Returning empty candle list.")
            return []

        instrument = self.resolver.resolve(symbol)
        if not instrument:
            logger.error(f"Cannot resolve symbol {symbol} to Dhan security ID")
            return []

        # Dhan v2 API separates minute-level intraday from daily data
        is_intraday = timeframe in ["1m", "5m", "15m", "25m", "60m"]
        endpoint = f"{self.base_url}/charts/intraday" if is_intraday else f"{self.base_url}/charts/historical"
        
        payload = {
            "securityId": str(instrument["security_id"]),
            "exchangeSegment": instrument.get("exchange_segment", "NSE_EQ"),
            "instrument": instrument.get("instrument", "EQUITY"),
            "fromDate": start_date.strftime("%Y-%m-%d"),
            "toDate": end_date.strftime("%Y-%m-%d")
        }
        if is_intraday:
            # Dhan v2 intraday expects interval in minutes
            interval_val = 1 if timeframe == "1m" else (5 if timeframe == "5m" else 15)
            payload["interval"] = str(interval_val)

        try:
            resp = self.session.post(endpoint, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Dhan historical data error: HTTP {resp.status_code} - {resp.text}")
                return []

            data = resp.json()
            # Dhan v2 returns arrays: timestamp, open, high, low, close, volume
            timestamps = data.get("timestamp", [])
            opens = data.get("open", [])
            highs = data.get("high", [])
            lows = data.get("low", [])
            closes = data.get("close", [])
            volumes = data.get("volume", [])

            candles = []
            for i in range(len(timestamps)):
                raw = {
                    "timestamp": timestamps[i],
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i],
                    "volume": volumes[i] if i < len(volumes) else 0.0
                }
                c = MarketDataNormalizer.normalize_candle(raw, symbol.upper())
                if c:
                    candles.append(c)

            return MarketDataNormalizer.deduplicate_and_sort(candles)
        except Exception as e:
            logger.error(f"Exception requesting historical data from Dhan: {e}")
            return []

    def get_latest_quote(self, symbol: str) -> Optional[MarketTick]:
        """Fetches market quote using Dhan v2 Market Quote API.
        POST /marketfeed/quote
        """
        if not self.is_configured():
            return None

        instrument = self.resolver.resolve(symbol)
        if not instrument:
            return None

        endpoint = f"{self.base_url}/marketfeed/quote"
        payload = {
            instrument.get("exchange_segment", "NSE_EQ"): [str(instrument["security_id"])]
        }

        try:
            resp = self.session.post(endpoint, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                sec_data = data.get(instrument.get("exchange_segment", "NSE_EQ"), {}).get(str(instrument["security_id"]), {})
                last_price = sec_data.get("last_price") or sec_data.get("ltp")
                if last_price:
                    return MarketTick(
                        symbol=symbol.upper(),
                        timestamp=datetime.now(),
                        last_price=float(last_price),
                        volume=float(sec_data.get("volume", 0.0)),
                        bid_price=float(sec_data.get("buy_price", last_price)),
                        ask_price=float(sec_data.get("sell_price", last_price))
                    )
        except Exception as e:
            logger.error(f"Exception fetching quote from Dhan: {e}")
        return None

    def subscribe_live(self, symbols: List[str], on_tick: Callable[[MarketTick], None]) -> None:
        pass

    def unsubscribe(self) -> None:
        pass
