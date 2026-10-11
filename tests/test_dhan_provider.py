import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.data.providers.dhan_provider import DhanMarketDataProvider
from app.data.instrument_resolver import InstrumentResolver

def test_instrument_resolver():
    resolver = InstrumentResolver()
    reliance = resolver.resolve("RELIANCE")
    assert reliance is not None
    assert reliance["security_id"] == "2885"
    assert reliance["exchange_segment"] == "NSE_EQ"
    assert "TCS" in resolver.get_supported_symbols()

def test_dhan_provider_unconfigured_behavior():
    # If credentials are blank, provider gracefully returns empty/None with NO crashes
    provider = DhanMarketDataProvider(client_id="", access_token="")
    assert provider.is_configured() is False
    candles = provider.get_historical_candles("RELIANCE", datetime(2026, 1, 1), datetime(2026, 1, 2))
    assert candles == []
    quote = provider.get_latest_quote("RELIANCE")
    assert quote is None

@patch("requests.Session.post")
def test_dhan_provider_historical_parsing(mock_post):
    # Mocking valid Dhan v2 API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "timestamp": [1704099300, 1704099360],
        "open": [2500.0, 2505.0],
        "high": [2510.0, 2515.0],
        "low": [2495.0, 2500.0],
        "close": [2505.0, 2512.0],
        "volume": [1200, 1500]
    }

    provider = DhanMarketDataProvider(client_id="dummy_id", access_token="dummy_token")
    assert provider.is_configured() is True

    candles = provider.get_historical_candles("RELIANCE", datetime(2026, 1, 1), datetime(2026, 1, 2))
    assert len(candles) == 2
    assert candles[0].symbol == "RELIANCE"
    assert candles[0].open == 2500.0
    assert candles[0].close == 2505.0
    assert candles[1].close == 2512.0
