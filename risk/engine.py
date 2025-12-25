from datetime import datetime
from core.logger import get_logger

from events.base import SignalEvent, OrderEvent

logger = get_logger("RISK")

class PassThroughRiskManager:
    # minimal risk

    #Behavior: accept every Signal Event, and convert it directly into an OrderEvent

    def __init__(self, fixed_quantity: int = 10):
        self.fixed_quantity = fixed_quantity

    def handle_signal(self, event: SignalEvent):
        order = OrderEvent(
            timestamp = datetime.utcnow(),
            symbol = event.symbol,
            direction = event.direction,
            quantity = self.fixed_quantity,
            price = event.price
        )

        logger.info(
            f"Approved {event.direction} order for {event.symbol} "
            f"@ {event.price}, qty = {self.fixed_quantity}"
        )

        return [order]