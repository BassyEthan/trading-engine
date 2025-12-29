from dataclasses import dataclass
from datetime import datetime
from typing import Optional

#@dataclass rewrites the class for you - like defining an init func

@dataclass(frozen=True) #events are immutable facts
class MarketEvent:
    #Represents a new piece of market info
    timestamp: int
    symbol: str
    price: float

@dataclass(frozen=True) #events are immutable facts
class SignalEvent:
    #Represents an intent to trade, not an order
    timestamp: int
    symbol: str
    direction: str #BUY or SELL
    price: float

@dataclass(frozen=True) #events are immutable facts
class OrderEvent:
    #Represents an approved order sent for execution
    timestamp: int
    symbol: str
    direction: str
    quantity: int
    price: float

@dataclass(frozen=True) #events are immutable facts
class FillEvent:
    #Reprents an executed order. Only event allowed to change portfolio state
    timestamp: int
    symbol: str
    direction: str
    quantity: int
    fill_price: float
