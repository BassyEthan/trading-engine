from typing import Optional, List
from events.base import MarketEvent, SignalEvent

class Strategy:
    def __init__(self, symbol: Optional[str] = None):
        self.symbol = symbol
    
    def handle_market(self, event: MarketEvent) -> List[SignalEvent]:
        raise NotImplementedError






