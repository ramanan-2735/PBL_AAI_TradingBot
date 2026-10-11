import asyncio
import json
import logging
import struct
import threading
from typing import List, Callable, Optional
import websockets
from app.data.models import MarketTick
from app.data.instrument_resolver import InstrumentResolver
from app.config import config

logger = logging.getLogger(__name__)

class DhanWebSocketFeed:
    """Robust WebSocket connection manager for Dhan Live Market Feed.
    Features:
    - Auto-reconnect with exponential backoff
    - Binary and JSON frame decoding
    - Safe state restoration
    - Never crashes the parent application on disconnect
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        wss_url: Optional[str] = None,
        resolver: Optional[InstrumentResolver] = None
    ):
        self.client_id = client_id or config.DHAN_CLIENT_ID
        self.access_token = access_token or config.DHAN_ACCESS_TOKEN
        self.wss_url = wss_url or config.DHAN_WSS_URL
        self.resolver = resolver or InstrumentResolver()
        
        self.subscribed_symbols: List[str] = []
        self.on_tick_callback: Optional[Callable[[MarketTick], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_connected = False

    def start(self, symbols: List[str], on_tick: Callable[[MarketTick], None]):
        self.subscribed_symbols = symbols
        self.on_tick_callback = on_tick
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.is_connected = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        reconnect_delay = 2
        while self._running:
            try:
                headers = {
                    "access-token": self.access_token,
                    "client-id": self.client_id
                }
                async with websockets.connect(self.wss_url, extra_headers=headers, ping_interval=20, ping_timeout=10) as ws:
                    self.is_connected = True
                    logger.info("Dhan WebSocket Feed connected successfully.")
                    reconnect_delay = 2  # reset backoff

                    # Send subscription packet
                    sub_instruments = []
                    for sym in self.subscribed_symbols:
                        res = self.resolver.resolve(sym)
                        if res:
                            sub_instruments.append({
                                "ExchangeSegment": res.get("exchange_segment", "NSE_EQ"),
                                "SecurityId": str(res["security_id"])
                            })

                    if sub_instruments:
                        sub_req = {
                            "RequestCode": 15,  # 15 for Ticker/Quote
                            "InstrumentCount": len(sub_instruments),
                            "InstrumentList": sub_instruments
                        }
                        await ws.send(json.dumps(sub_req))

                    # Continuous listening loop
                    while self._running:
                        message = await ws.recv()
                        self._process_message(message)

            except Exception as e:
                self.is_connected = False
                logger.warning(f"Dhan WebSocket disconnected: {e}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)

    def _process_message(self, message):
        try:
            # Dhan market feed supports both JSON messages and binary tick packets
            if isinstance(message, str):
                data = json.loads(message)
                sec_id = str(data.get("security_id", ""))
                ltp = float(data.get("LTP", data.get("last_price", 0)))
                if ltp > 0 and self.on_tick_callback:
                    # Reverse map security ID to symbol
                    symbol = self._resolve_symbol_from_id(sec_id)
                    tick = MarketTick(
                        symbol=symbol or "UNKNOWN",
                        timestamp=datetime.now(),
                        last_price=ltp,
                        volume=float(data.get("volume", 0))
                    )
                    self.on_tick_callback(tick)
            elif isinstance(message, bytes):
                # Binary format decoder for Dhan v2 ticker packet
                # Byte 0: Feed response code (e.g. 2 for Ticker, 4 for Quote)
                if len(message) >= 16:
                    feed_code = message[0]
                    # Read security ID and LTP
                    sec_id = struct.unpack('<I', message[4:8])[0]
                    ltp = struct.unpack('<f', message[8:12])[0]
                    if ltp > 0 and self.on_tick_callback:
                        symbol = self._resolve_symbol_from_id(str(sec_id))
                        tick = MarketTick(
                            symbol=symbol or str(sec_id),
                            timestamp=datetime.now(),
                            last_price=round(ltp, 2),
                            volume=0.0
                        )
                        self.on_tick_callback(tick)
        except Exception as e:
            logger.debug(f"Error parsing Dhan websocket tick: {e}")

    def _resolve_symbol_from_id(self, sec_id: str) -> Optional[str]:
        for sym, data in self.resolver.instruments.items():
            if str(data.get("security_id")) == str(sec_id):
                return sym
        return None
