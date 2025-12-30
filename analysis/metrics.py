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
            final_equity: float = None,  # Optional: if provided, use for total_pnl
    ):
        self.fills = fills
        self.initial_cash = initial_cash
        self.final_cash = final_cash
        self.final_equity = final_equity  # If None, will use final_cash (backward compat)

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
        """
        Calculate total PnL (realized + unrealized).
        
        If final_equity is provided, uses equity (includes open positions).
        Otherwise, uses final_cash (only realized PnL from closed trades).
        """
        if self.final_equity is not None:
            return self.final_equity - self.initial_cash
        else:
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
        print(f"Initial Capital: ${self.initial_cash:,.2f}")
        if self.final_equity is not None:
            print(f"Final Equity: ${self.final_equity:,.2f}")
            print(f"Total Return: ${self.total_pnl():,.2f} ({self.total_pnl() / self.initial_cash * 100:.2f}%)")
            print(f"  Realized PnL: ${self.final_cash - self.initial_cash:,.2f}")
            print(f"  Unrealized PnL: ${self.final_equity - self.final_cash:,.2f}")
        else:
            print(f"Final Cash: ${self.final_cash:,.2f}")
            print(f"Total PnL (realized only): ${self.total_pnl():,.2f}")
        print(f"\nTrading Statistics:")
        print(f"  Number of trades: {self.num_trades()}")
        print(f"  Win rate: {self.win_rate() * 100:.1f}%")
        print(f"  Average PnL per trade: ${self.avg_pnl_per_trade():.2f}")
        if self.trade_pnls:
            print(f"  Trade PnLs: {[f'${pnl:.2f}' for pnl in self.trade_pnls]}")
