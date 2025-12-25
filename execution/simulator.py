from datetime import datetime
from events.base import OrderEvent, FillEvent
from core.logger import get_logger

logger = get_logger("EXECUTION")

class ExecutionHandler: 
    """
    Simulates trade execution

    Essentially, it takes an OrderEvent, turns it into a FillEvent and emit the FillEvent

    This is a simulation of paper trading only, and there is no latency or slippage for now
    """

    def handle_order(self, event: OrderEvent):
        #converts OrderEvent into FillEvent
        fill = FillEvent(
            timestamp = datetime.utcnow(),
            symbol = event.symbol,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=event.price
        )

        logger.info(
            f"Filled {event.direction} {event.quantity} {event.symbol}"
            f"@ {event.price}"
        )
        return [fill]
