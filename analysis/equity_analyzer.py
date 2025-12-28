from typing import List, Tuple
from events.base import MarketEvent, FillEvent
import math

class EquityAnalyzer:
    def __init__(
            self,
            market_events: List[MarketEvent],
            fills: List[FillEvent],
            initial_cash: float,
    ):
        self.market_events = market_events
        self.fills = sorted(fills, key = lambda f: f.timestamp)
        self.initial_cash = initial_cash

        self.equity_curve: List[float] = []
        self.drawdown_curve: List[float] = []
        self.max_drawdown: float = 0.0
        self.trade_markers: List[Tuple[int, float, float]] = []
        self.holding_periods: List[Tuple[int, int]] = []
        self.sharpe: float = 0.0

    def run(self):
        cash = self.initial_cash
        position_qty = 0
        fill_idx = 0
        peak = self.initial_cash

        open_price = None
        entry_idx = None

        equity = []
        returns = []

        for i, event in enumerate(self.market_events):

            while fill_idx < len(self.fills) and self.fills[fill_idx].timestamp <= event.timestamp:
                fill = self.fills[fill_idx]

                if fill.direction == "BUY":
                    cash -= fill.fill_price * fill.quantity
                    position_qty += fill.quantity
                    open_price = fill.fill_price
                    entry_idx = i

                elif fill.direction == "SELL":
                    cash += fill.fill_price * fill.quantity
                    position_qty -= fill.quantity
                    if open_price is not None:
                        pnl = (fill.fill_price - open_price) * fill.quantity
                        self.trade_markers.append((i, fill.fill_price, pnl))
                        open_price = None
                    
                    if position_qty == 0 and entry_idx is not None:
                        self.holding_periods.append((entry_idx, i))
                        entry_idx = None
                fill_idx += 1
            
            equity_value = cash + position_qty * event.price
            equity.append(equity_value)

            # returns for sharpe
            if len(equity) > 1:
                returns.append((equity[-1] - equity[-2])/ equity[-2])

            # drawdown
            peak = max(peak, equity_value)
            self.drawdown_curve.append((equity_value - peak) / peak)
        
        self.equity_curve = equity
        self.max_drawdown = min(self.drawdown_curve) if self.drawdown_curve else 0.0
        self.sharpe = self._compute_sharpe(returns)

    def _compute_sharpe(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
        return mean / std * math.sqrt(252) if std > 0 else 0.0

