"""
HoldThroughCrashStrategy - A strategy that holds positions through price crashes
for stress testing equity curve behavior.

This strategy is designed to demonstrate how equity responds to price movements
when positions are held during market crashes.
"""

from datetime import datetime
from core.logger import get_logger
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent

logger = get_logger("STRATEGY")


class HoldThroughCrashStrategy(Strategy):
    """
    A strategy that buys at a specified timestamp and holds until a later timestamp,
    allowing you to see equity drops during price crashes.
    
    Useful for:
    - Stress testing equity curve calculations
    - Testing risk management during drawdowns
    - Verifying mark-to-market equity updates
    
    Parameters:
        symbol: Symbol to trade
        buy_at_timestamp: Market event timestamp to buy at
        sell_at_timestamp: Market event timestamp to sell at
    """
    
    def __init__(
        self,
        symbol: str | None = None,
        buy_at_timestamp: int = 0,
        sell_at_timestamp: int = 100,
    ):
        super().__init__(symbol)
        self.buy_at_timestamp = buy_at_timestamp
        self.sell_at_timestamp = sell_at_timestamp
        self.state = "FLAT"
        self.bought = False
        self.sold = False
    
    def handle_market(self, event: MarketEvent):
        """
        Generate BUY signal at buy_at_timestamp, SELL signal at sell_at_timestamp.
        Ignores all other market events.
        """
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
        # Buy at specified timestamp
        if event.timestamp == self.buy_at_timestamp and not self.bought:
            self.bought = True
            self.state = "LONG"
            
            logger.info(
                f"BUY {event.symbol} @ {event.price:.2f} "
                f"(holding until t={self.sell_at_timestamp})"
            )
            
            return [
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    direction="BUY",
                    price=event.price,
                )
            ]
        
        # Sell at specified timestamp
        if event.timestamp == self.sell_at_timestamp and self.bought and not self.sold:
            self.sold = True
            self.state = "FLAT"
            
            logger.info(
                f"SELL {event.symbol} @ {event.price:.2f} "
                f"(held from t={self.buy_at_timestamp} to t={self.sell_at_timestamp})"
            )
            
            return [
                SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    direction="SELL",
                    price=event.price,
                )
            ]
        
        return []

