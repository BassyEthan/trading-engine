from datetime import datetime
from core.logger import get_logger
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent

logger = get_logger("STRATEGY")

class OneShotBuyStrategy(Strategy):
    # simple strat to test event pipeline

    # behavior: on the first MarketEvent only, emit a BUY SignalEvent
    # then sell second MarketEvent, then ignore all future MarketEvents

    def __init__(self, symbol = None):
        super().__init__(symbol)
        self.state = "FLAT"

    def handle_market(self, event: MarketEvent):
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
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