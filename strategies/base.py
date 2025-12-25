from datetime import datetime
from core.logger import get_logger

from events.base import MarketEvent, SignalEvent

logger = get_logger("STRATEGY")

class OneShotBuyStrategy:
    # simple strat to test event pipeline

    # behavior: on the first MarketEvent only, emit a BUY SignalEvent
    # then sell second MarketEvent, then ignore all future MarketEvents

    def __init__(self):
        self.state = "FLAT"

    def handle_market(self, event: MarketEvent):
        if self.state == "FLAT":
            self.state = "LONG"
        
            signal = SignalEvent(
                timestamp = datetime.utcnow(),
                symbol = event.symbol,
                direction = "BUY",
                price = event.price
            )
            logger.info(f"Emitting BUY signal for {event.symbol} @ {event.price}")
            return [signal]

        elif self.state == "LONG":
            self.state = "DONE"

            signal = SignalEvent(
                timestamp = datetime.utcnow(),
                symbol = event.symbol,
                direction = "SELL",
                price = event.price
            )

            logger.info(f"SELL {event.symbol} @ {event.price}")
            return [signal]
        
        else:
            return []