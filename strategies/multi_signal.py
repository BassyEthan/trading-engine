"""
MultiSignalStrategy - Generates multiple signals at specified timestamps
Useful for testing risk manager rejection behavior
"""

from datetime import datetime
from core.logger import get_logger
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent

logger = get_logger("STRATEGY")


class MultiSignalStrategy(Strategy):
    """
    A strategy that generates signals at multiple specified timestamps.
    Useful for testing risk manager behavior.
    
    Parameters:
        symbol: Symbol to trade
        signals: List of (timestamp, direction) tuples
                 e.g., [(12, 'BUY'), (14, 'BUY'), (22, 'SELL')]
    """
    
    def __init__(
        self,
        symbol: str | None = None,
        signals: list[tuple[int, str]] = [],
    ):
        super().__init__(symbol)
        self.signals = signals
        self.generated = set()  # Track which signals we've already generated
    
    def handle_market(self, event: MarketEvent):
        """Generate signal if this timestamp matches a signal definition."""
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
        # Check if we should generate a signal at this timestamp
        for ts, direction in self.signals:
            if event.timestamp == ts and (ts, direction) not in self.generated:
                self.generated.add((ts, direction))
                
                logger.info(
                    f"{direction} {event.symbol} @ {event.price:.2f} "
                    f"(signal at t={ts})"
                )
                
                return [
                    SignalEvent(
                        timestamp=event.timestamp,
                        symbol=event.symbol,
                        direction=direction,
                        price=event.price,
                    )
                ]
        
        return []

