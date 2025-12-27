from typing import List
from events.base import FillEvent

class TradeMetrics:
    #Computes basic performance metrics from a list of FillEvents.
    #Assumes trades are BUY followed by SELL, there are no overlapping positions

    def __init__(
            self,
            fills: List[FillEvent],
            initial_cash: float,
            final_cash: float,
    ):
        self.fills = fills
        self.initial_cash = initial_cash
        self.final_cash = final_cash

        self.trade_pnls = self._compute_trade_pnls()

    def _compute_trade_pnls(self) -> List[float]:
        # pairs BUY and SELL fills into round trips and compute PnL per trade.
        #if BUY then remember entry, if SELL than compute PnL and close trade
        trade_pnls = []
        entry_price = None
        quantity = None

        for fill in self.fills:
            if fill.direction == "BUY":
                entry_price = fill.fill_price
                quantity = fill.quantity
            
            elif fill.direction == "SELL":
                assert entry_price is not None
                assert quantity is not None
                pnl = (fill.fill_price - entry_price) * quantity
                trade_pnls.append(pnl)

                entry_price = None
                quantity = None
        return trade_pnls
    
    def total_pnl(self) -> float:
        return self.final_cash - self.initial_cash
    
    def num_trades(self) -> int:
        return len(self.trade_pnls)
    
    def win_rate(self) -> float:
        if not self.trade_pnls:
            return 0.0
        wins = sum(1 for pnl in self.trade_pnls if pnl > 0)
        return wins / len(self.trade_pnls)
    
    def avg_pnl_per_trade(self) -> float:
        if not self.trade_pnls:
            return 0.0
        return sum(self.trade_pnls) / len(self.trade_pnls)
    
    def summary(self) -> None:
        print("\n--- PERFORMANCE METRICS ---")
        print(f"Total PnL: {self.total_pnl():.2f}")
        print(f"Number of trades: {self.num_trades()}")
        print(f"Win rate: {self.win_rate() * 100:.1f}%")
        print(f"Average PnL per trade: {self.avg_pnl_per_trade():.2f}")
        print(f"Trade PnLs: {self.trade_pnls}")
