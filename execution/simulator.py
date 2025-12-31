from datetime import datetime
from events.base import OrderEvent, FillEvent
from core.logger import get_logger
import random

logger = get_logger("EXECUTION")

class ExecutionHandler: 
    """
    Simulates trade execution (perfect execution - no costs)

    Essentially, it takes an OrderEvent, turns it into a FillEvent and emit the FillEvent

    This is a simulation of paper trading only, and there is no latency or slippage for now
    """

    def handle_order(self, event: OrderEvent):
        #converts OrderEvent into FillEvent
        fill = FillEvent(
            timestamp = event.timestamp,
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


class RealisticExecutionHandler:
    """
    Realistic execution handler that simulates real-world trading costs.
    
    Includes:
    - Bid-ask spread (you buy at ask, sell at bid)
    - Slippage (market impact and timing)
    - Size-based impact (larger orders = more slippage)
    
    Parameters:
        spread_pct: Bid-ask spread as percentage (default: 0.1% for liquid stocks)
        base_slippage_pct: Base slippage percentage (default: 0.05%)
        impact_factor: Market impact factor per share (default: 0.0001% per share)
        slippage_volatility: Random slippage variation (default: 0.02%)
    """
    
    def __init__(
        self,
        spread_pct: float = 0.001,  # 0.1% spread
        base_slippage_pct: float = 0.0005,  # 0.05% base slippage
        impact_factor: float = 0.000001,  # 0.0001% per share
        slippage_volatility: float = 0.0002,  # 0.02% random variation
    ):
        self.spread_pct = spread_pct
        self.base_slippage_pct = base_slippage_pct
        self.impact_factor = impact_factor
        self.slippage_volatility = slippage_volatility
        
        # Track execution costs for reporting
        self.total_slippage_cost = 0.0
        self.total_spread_cost = 0.0
        self.trade_count = 0
    
    def _calculate_fill_price(self, order: OrderEvent) -> float:
        """
        Calculate realistic fill price including spread and slippage.
        
        For BUY orders:
        - Pay ask price (mid + spread/2)
        - Add slippage (base + size impact + random)
        
        For SELL orders:
        - Get bid price (mid - spread/2)
        - Subtract slippage (base + size impact + random)
        """
        mid_price = order.price
        spread_amount = mid_price * self.spread_pct / 2
        
        # Size-based market impact
        size_impact = mid_price * self.impact_factor * order.quantity
        
        # Random slippage variation
        random_slippage = mid_price * random.uniform(
            -self.slippage_volatility,
            self.slippage_volatility
        )
        
        # Base slippage
        base_slippage = mid_price * self.base_slippage_pct
        
        # Total slippage
        total_slippage = base_slippage + size_impact + random_slippage
        
        if order.direction == "BUY":
            # Buy at ask (mid + spread/2) + slippage
            fill_price = mid_price + spread_amount + total_slippage
            spread_cost = spread_amount * order.quantity
            slippage_cost = total_slippage * order.quantity
        else:  # SELL
            # Sell at bid (mid - spread/2) - slippage
            fill_price = mid_price - spread_amount - total_slippage
            spread_cost = spread_amount * order.quantity
            slippage_cost = total_slippage * order.quantity
        
        # Track costs
        self.total_spread_cost += spread_cost
        self.total_slippage_cost += slippage_cost
        self.trade_count += 1
        
        return fill_price
    
    def handle_order(self, event: OrderEvent):
        """
        Convert OrderEvent to FillEvent with realistic execution costs.
        """
        fill_price = self._calculate_fill_price(event)
        
        # Calculate costs for logging
        expected_cost = event.price * event.quantity
        actual_cost = fill_price * event.quantity
        execution_cost = abs(actual_cost - expected_cost)
        cost_pct = (execution_cost / expected_cost) * 100
        
        fill = FillEvent(
            timestamp=event.timestamp,
            symbol=event.symbol,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=fill_price
        )
        
        logger.info(
            f"Filled {event.direction} {event.quantity} {event.symbol} "
            f"@ {fill_price:.2f} (expected: {event.price:.2f}, "
            f"cost: ${execution_cost:.2f}, {cost_pct:.3f}%)"
        )
        
        return [fill]
    
    def get_execution_summary(self) -> dict:
        """Get summary of execution costs."""
        return {
            "total_trades": self.trade_count,
            "total_spread_cost": self.total_spread_cost,
            "total_slippage_cost": self.total_slippage_cost,
            "total_execution_cost": self.total_spread_cost + self.total_slippage_cost,
            "avg_cost_per_trade": (
                (self.total_spread_cost + self.total_slippage_cost) / self.trade_count
                if self.trade_count > 0 else 0
            ),
        }
