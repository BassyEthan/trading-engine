from dataclasses import dataclass
from typing import Dict
from events.base import FillEvent
from core.logger import get_logger
# this is pure accounting and risk bookkeeping

logger = get_logger("PORTFOLIO")

@dataclass
class Position:
    quantity: int
    avg_cost: float


class PortfolioState:
    """
    single source of truth for portfolio state.
    Invariants:
        Cash can never go negative
        Positions only change on FillEvents
        Realized PnL only changes when positions are reduced or closed
    """

    def __init__(self, initial_cash: float):
        self.cash: float = initial_cash
        self.positions: Dict[str, Position] = {} #keys are strings, values are positions
        self.realized_pnl: float = 0.0
        self.trades: list[FillEvent] = []

    def handle_fill(self, event: FillEvent):
        #apply a FillEvent to the portfolio state. Only way portfolio state may change
        symbol = event.symbol
        qty = event.quantity
        price = event.fill_price
        direction = event.direction

        #append fills to trade history
        self.trades.append(event)
        logger.info(
            f"Recorded trade: {event.direction} {event.quantity} "
            f"{event.symbol} @ {event.fill_price}"
        )

        signed_qty = qty if direction == "BUY" else -qty #-qty for short
        cash_change = -signed_qty * price #cash moves in the opposite direction of shares - if u buy shares u lose cash, vise versa

        #enforce cash invariant
        if self.cash + cash_change < 0:
            raise ValueError("Insufficient cash for fill")
        
        #update or create position
        if symbol not in self.positions:
            self.positions[symbol] = Position(quantity = 0, avg_cost = 0.0)

        position = self.positions[symbol]

        # if reducing or closing position, realize pnl
        #position.quantity is how many shares you currently own (positive, long; negative short)
        #signed_qty - what you are trading rn + directional effect of new trade w(BUY 10: +10, SELL 10: -10)
        # after a trade fills, what is my new position and how much money did I make or lose?
        if position.quantity != 0 and (position.quantity * signed_qty < 0):
            closing_qty = min(abs(position.quantity), abs(signed_qty)) 
            pnl_per_share = price - position.avg_cost
            self.realized_pnl += closing_qty * pnl_per_share * (1 if position.quantity > 0 else -1)


        new_qty = position.quantity + signed_qty  

        if new_qty == 0:
            del self.positions[symbol]
        else:
            if position.quantity == 0: #if you just opened a trade
                new_avg_cost = price
            else: 
                total_cost = ( #adding on current trade
                    position.avg_cost * position.quantity
                    + price * signed_qty
                )
                new_avg_cost = total_cost/new_qty
            
            self.positions[symbol] = Position(
                quantity = new_qty,
                avg_cost = new_avg_cost
            )
        self.cash += cash_change

        logger.info(
            f"Cash = {self.cash:.2f}, Positions = {self.positions}"
        )







    