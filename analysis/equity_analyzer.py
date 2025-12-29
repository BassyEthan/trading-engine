from typing import List, Tuple
from events.base import MarketEvent, FillEvent
import math

class EquityAnalyzer:
    def __init__(
            self,
            market_events: List[MarketEvent],
            fills: List[FillEvent],
            equity_curve: List[float],
            initial_cash: float,
    ):
        self.market_events = market_events
        self.fills = sorted(fills, key = lambda f: f.timestamp)
        self.equity_curve = equity_curve
        self.initial_cash = initial_cash

        self.drawdown_curve: List[float] = []
        self.max_drawdown: float = 0.0
        self.trade_markers: List[Tuple[int, float, float]] = []
        self.holding_periods: List[Tuple[int, int]] = []
        self.sharpe: float = 0.0

    def run(self):
        # Use equity curve from portfolio (mark-to-market)
        if not self.equity_curve:
            return

        fill_idx = 0
        peak = self.initial_cash

        open_price = None
        entry_idx = None

        returns = []

        for i, event in enumerate(self.market_events):

            while fill_idx < len(self.fills) and self.fills[fill_idx].timestamp <= event.timestamp:
                fill = self.fills[fill_idx]

                if fill.direction == "BUY":
                    open_price = fill.fill_price
                    entry_idx = i

                elif fill.direction == "SELL":
                    if open_price is not None:
                        pnl = (fill.fill_price - open_price) * fill.quantity
                        self.trade_markers.append((i, fill.fill_price, pnl))
                        open_price = None
                    
                    if entry_idx is not None:
                        self.holding_periods.append((entry_idx, i))
                        entry_idx = None
                fill_idx += 1

            # Use equity from portfolio (already mark-to-market)
            # Equity curve has one entry per market event, aligned by index
            if i < len(self.equity_curve):
                equity_value = self.equity_curve[i]

                # returns for sharpe
                if i > 0 and i - 1 < len(self.equity_curve):
                    prev_equity = self.equity_curve[i - 1]
                    if prev_equity > 0:
                        returns.append((equity_value - prev_equity) / prev_equity)

                # drawdown
                peak = max(peak, equity_value)
                self.drawdown_curve.append((equity_value - peak) / peak)
        
        self.max_drawdown = min(self.drawdown_curve) if self.drawdown_curve else 0.0
        self.sharpe = self._compute_sharpe(returns)

    def _compute_sharpe(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
        return mean / std * math.sqrt(252) if std > 0 else 0.0

