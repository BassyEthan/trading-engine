from datetime import datetime
from typing import Optional
from core.logger import get_logger

from events.base import SignalEvent, OrderEvent
from portfolio.state import PortfolioState

logger = get_logger("RISK")


class PassThroughRiskManager:
    """
    Minimal risk manager - accepts all trades.
    Used for testing or when risk checks are not needed.
    """
    
    def __init__(self, fixed_quantity: int = 10):
        self.fixed_quantity = fixed_quantity

    def handle_signal(self, event: SignalEvent):
        order = OrderEvent(
            timestamp = event.timestamp,
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


class RealRiskManager:
    """
    Real risk manager that enforces trading limits.
    
    Checks (at signal generation time only):
    - Drawdown limits (max drawdown from peak equity)
    - Position size limits (max position per symbol, max total exposure)
    - Cash availability (can't buy without cash)
    - Position count limits (max number of open positions)
    
    Rejects trades that violate any limit and logs the reason.
    
    Note: Drawdown is checked when signals are generated, not continuously.
    This means existing positions can experience drawdown beyond the limit
    if they're held through market crashes. The risk manager prevents
    entering NEW trades when in drawdown, but doesn't force exits.
    """
    
    def __init__(
        self,
        portfolio: PortfolioState,
        fixed_quantity: int = 10,
        max_drawdown: float = 0.10,  # 10% max drawdown
        max_position_size: Optional[float] = None,  # Max position value (None = no limit)
        max_position_pct: float = 0.20,  # Max 20% of equity in single position
        max_total_exposure_pct: float = 1.0,  # Max 100% of equity in total positions
        max_positions: Optional[int] = None,  # Max number of open positions (None = no limit)
    ):
        self.portfolio = portfolio
        self.fixed_quantity = fixed_quantity
        self.max_drawdown = max_drawdown
        self.max_position_size = max_position_size
        self.max_position_pct = max_position_pct
        self.max_total_exposure_pct = max_total_exposure_pct
        self.max_positions = max_positions
        
        # Track rejections for reporting
        self.rejections: list[dict] = []
        self.peak_equity: float = portfolio.initial_cash
    
    def _get_current_equity(self) -> float:
        """
        Calculate current equity (cash + position values).
        
        Note: This uses the latest_prices from the portfolio, which should be
        updated by MarketEvent handlers before signals are generated.
        """
        equity = self.portfolio.cash
        for symbol, position in self.portfolio.positions.items():
            if symbol in self.portfolio.latest_prices:
                equity += position.quantity * self.portfolio.latest_prices[symbol]
        return equity
    
    def _get_current_drawdown(self) -> float:
        """Calculate current drawdown from peak equity."""
        current_equity = self._get_current_equity()
        
        # Update peak if we've hit a new high
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Calculate drawdown
        if self.peak_equity > 0:
            drawdown = (current_equity - self.peak_equity) / self.peak_equity
            return drawdown
        return 0.0
    
    def _check_drawdown_limit(self, signal: SignalEvent) -> tuple[bool, Optional[str]]:
        """Check if current drawdown exceeds limit."""
        current_dd = self._get_current_drawdown()
        
        # Drawdown is negative, so check if absolute value exceeds limit
        if abs(current_dd) > self.max_drawdown:
            reason = f"Drawdown {current_dd:.2%} exceeds limit {self.max_drawdown:.2%}"
            return False, reason
        
        return True, None
    
    def _check_position_size_limit(self, signal: SignalEvent) -> tuple[bool, Optional[str]]:
        """Check if position size would exceed limits."""
        current_equity = self._get_current_equity()
        order_value = self.fixed_quantity * signal.price
        
        # Check absolute position size limit
        if self.max_position_size is not None:
            if order_value > self.max_position_size:
                reason = f"Order value {order_value:.2f} exceeds max position size {self.max_position_size:.2f}"
                return False, reason
        
        # Check position size as % of equity
        if current_equity > 0:
            position_pct = order_value / current_equity
            if position_pct > self.max_position_pct:
                reason = f"Position {position_pct:.2%} of equity exceeds limit {self.max_position_pct:.2%}"
                return False, reason
        
        # Check total exposure limit
        total_exposure = sum(
            pos.quantity * self.portfolio.latest_prices.get(sym, 0)
            for sym, pos in self.portfolio.positions.items()
        )
        
        # Add new position to exposure if buying
        if signal.direction == "BUY":
            total_exposure += order_value
        
        if current_equity > 0:
            exposure_pct = total_exposure / current_equity
            if exposure_pct > self.max_total_exposure_pct:
                reason = f"Total exposure {exposure_pct:.2%} exceeds limit {self.max_total_exposure_pct:.2%}"
                return False, reason
        
        return True, None
    
    def _check_cash_availability(self, signal: SignalEvent) -> tuple[bool, Optional[str]]:
        """Check if we have enough cash to buy."""
        if signal.direction == "BUY":
            required_cash = self.fixed_quantity * signal.price
            if self.portfolio.cash < required_cash:
                reason = f"Insufficient cash: need {required_cash:.2f}, have {self.portfolio.cash:.2f}"
                return False, reason
        
        return True, None
    
    def _check_position_count_limit(self, signal: SignalEvent) -> tuple[bool, Optional[str]]:
        """Check if adding a new position would exceed position count limit."""
        if self.max_positions is not None and signal.direction == "BUY":
            # Count current positions
            current_count = len(self.portfolio.positions)
            
            # If this symbol already has a position, we're not adding a new one
            if signal.symbol not in self.portfolio.positions:
                if current_count >= self.max_positions:
                    reason = f"Position count {current_count} exceeds limit {self.max_positions}"
                    return False, reason
        
        return True, None
    
    def handle_signal(self, event: SignalEvent):
        """
        Check all risk limits before approving a trade.
        Returns OrderEvent if approved, empty list if rejected.
        
        Important: Updates portfolio.latest_prices with the signal's price
        to ensure mark-to-market equity is current before risk checks.
        """
        # Update portfolio price for this symbol to ensure mark-to-market is current
        # The signal price comes from the MarketEvent that just occurred
        self.portfolio.latest_prices[event.symbol] = event.price
        
        # Run all risk checks
        checks = [
            ("drawdown", self._check_drawdown_limit(event)),
            ("position_size", self._check_position_size_limit(event)),
            ("cash", self._check_cash_availability(event)),
            ("position_count", self._check_position_count_limit(event)),
        ]
        
        # Check each limit
        for check_name, (passed, reason) in checks:
            if not passed:
                # Log rejection
                logger.warning(
                    f"REJECTED {event.direction} {event.symbol} @ {event.price}: "
                    f"{reason} (check: {check_name})"
                )
                
                # Track rejection
                self.rejections.append({
                    "timestamp": event.timestamp,
                    "symbol": event.symbol,
                    "direction": event.direction,
                    "price": event.price,
                    "reason": reason,
                    "check": check_name,
                })
                
                # Return empty list (no order)
                return []
        
        # All checks passed - approve the trade
        order = OrderEvent(
            timestamp=event.timestamp,
            symbol=event.symbol,
            direction=event.direction,
            quantity=self.fixed_quantity,
            price=event.price
        )
        
        logger.info(
            f"APPROVED {event.direction} order for {event.symbol} "
            f"@ {event.price}, qty = {self.fixed_quantity}"
        )
        
        return [order]
    
    def get_rejection_summary(self) -> dict:
        """Get summary of rejected trades."""
        total_rejections = len(self.rejections)
        by_reason = {}
        by_check = {}
        
        for rejection in self.rejections:
            reason = rejection["reason"]
            check = rejection["check"]
            
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_check[check] = by_check.get(check, 0) + 1
        
        return {
            "total": total_rejections,
            "by_reason": by_reason,
            "by_check": by_check,
        }
