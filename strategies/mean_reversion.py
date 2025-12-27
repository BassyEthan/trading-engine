from collections import deque
from datetime import datetime
from typing import Deque

from core.logger import get_logger
from events.base import MarketEvent, SignalEvent

logger = get_logger("STRATEGY")

class RollingMeanReversionStrategy:
    #rolling mean reversion strategy with absolute threshold.

    """
    Behavior:
        maintain a rolling window of prices
        BUY wen price < mean - threshold (if FLAT)
        SELL when price >= mean (if LONG)
        repeat indefinitely
    """

    def __init__(
            self, 
            window: int = 5,
            threshold: float = 2.0, 
            symbol: str | None = None
    ):
        self.window = window
        self.threshold = threshold
        self.symbol = symbol

        self.prices: Deque[float] = deque(maxlen=window)
        self.state = "FLAT" #flat or long
        self.entry_price: float | None = None

    def handle_market(self, event: MarketEvent):
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
        #update rolling window
        self.prices.append(event.price)

        #not enough data to compute mean
        if len(self.prices) < self.window:
            return []
        
        mean_price = sum(self.prices) / len(self.prices)
        lower_band = mean_price - self.threshold #lower part

        # ---- ENTRY LOGIC ----
        if self.state == "FLAT" and event.price < lower_band:
            self.state = "LONG"
            self.entry_price = event.price
            
            logger.info(
                f"BUY {event.symbol} @ {event.price:.2f} "
                f"(mean = {mean_price:.2f}, lower = {lower_band:.2f})"
            )

            return [
                SignalEvent(
                    timestamp = event.timestamp,
                    symbol = event.symbol,
                    direction = "BUY",
                    price = event.price,
                )
            ]
        
        # ---- EXIT LOGIC ----
        if self.state == "LONG" and event.price >= mean_price:
            self.state = "FLAT"
            self.entry_price = None
            
            logger.info(
                f"SELL {event.symbol} @ {event.price:.2f} "
                f"(mean = {mean_price:.2f})"
            )

            return [
                SignalEvent(
                    timestamp = datetime.utcnow(),
                    symbol = event.symbol,
                    direction = "SELL",
                    price = event.price,
                )
            ]
    
        return []
