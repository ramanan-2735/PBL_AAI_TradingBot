from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class MarketCandle(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @field_validator('open', 'high', 'low', 'close')
    @classmethod
    def check_positive_price(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError(f"Price must be positive and non-zero, got {v}")
        return float(v)

    @field_validator('volume')
    @classmethod
    def check_non_negative_volume(cls, v: float) -> float:
        if v is None or v < 0:
            raise ValueError(f"Volume must be non-negative, got {v}")
        return float(v)

    def validate_ohlc(self) -> bool:
        """Validates standard OHLC relationships: high >= max(open, close), low <= min(open, close)."""
        if self.high < max(self.open, self.close):
            return False
        if self.low > min(self.open, self.close):
            return False
        return True


class MarketTick(BaseModel):
    symbol: str
    timestamp: datetime
    last_price: float
    volume: float = 0.0
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None

    @field_validator('last_price')
    @classmethod
    def check_positive_price(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError(f"Last price must be positive, got {v}")
        return float(v)
