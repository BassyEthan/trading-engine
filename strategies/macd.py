"""
MACD (Moving Average Convergence Divergence) Strategy.

MACD = EMA12 - EMA26
Signal = EMA9 of MACD
Histogram = MACD - Signal

Strategy:
- BUY when MACD crosses above signal (MACD > Signal)
- SELL when MACD crosses below signal (MACD < Signal)
- Also considers histogram positive vs negative
"""

from collections import deque
from typing import Deque, List, Optional

from core.logger import get_logger
from events.base import MarketEvent, SignalEvent
from strategies.base import Strategy

logger = get_logger("STRATEGY")


def calculate_ema(prices: List[float], period: int) -> float:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        prices: List of prices (should be at least period length)
        period: EMA period (e.g., 12, 26, 9)
        
    Returns:
        EMA value
    """
    if len(prices) < period:
        return None
    
    # Use simple average for first EMA value
    ema = sum(prices[-period:]) / period
    
    # Calculate smoothing factor
    multiplier = 2.0 / (period + 1)
    
    # Calculate EMA for remaining prices
    for price in prices[-period+1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


class MACDStrategy(Strategy):
    """
    MACD Strategy using Signal Line Crossover.
    
    Behavior:
        - Maintains price history to calculate EMAs
        - BUY when MACD crosses above signal (and histogram is positive)
        - SELL when MACD crosses below signal (and histogram is negative)
        - Requires at least 26 prices to calculate MACD
    """
    
    def __init__(
        self,
        symbol: Optional[str] = None,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        super().__init__(symbol)
        self.fast_period = fast_period  # EMA12
        self.slow_period = slow_period   # EMA26
        self.signal_period = signal_period  # EMA9 of MACD
        
        # Store enough prices for slow EMA (need at least slow_period)
        self.prices: Deque[float] = deque(maxlen=slow_period + 10)
        
        # Store MACD values for signal line calculation
        self.macd_values: Deque[float] = deque(maxlen=signal_period + 5)
        
        self.state = "FLAT"  # FLAT or LONG
        self.prev_macd: Optional[float] = None
        self.prev_signal: Optional[float] = None
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate EMA from price list."""
        if len(prices) < period:
            return None
        
        # Start with simple moving average
        ema = sum(prices[:period]) / period
        
        # Apply EMA formula for remaining prices
        multiplier = 2.0 / (period + 1)
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_macd(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD, Signal, and Histogram.
        
        Returns:
            (macd, signal, histogram) or (None, None, None) if not enough data
        """
        prices_list = list(self.prices)
        
        # Need at least slow_period prices
        if len(prices_list) < self.slow_period:
            return None, None, None
        
        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(prices_list, self.fast_period)
        slow_ema = self._calculate_ema(prices_list, self.slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None, None, None
        
        # MACD = Fast EMA - Slow EMA
        macd = fast_ema - slow_ema
        
        # Add MACD to history for signal calculation
        self.macd_values.append(macd)
        
        # Calculate signal (EMA of MACD)
        macd_list = list(self.macd_values)
        if len(macd_list) < self.signal_period:
            signal = None
        else:
            signal = self._calculate_ema(macd_list, self.signal_period)
        
        # Histogram = MACD - Signal
        if signal is not None:
            histogram = macd - signal
        else:
            histogram = None
        
        return macd, signal, histogram
    
    def handle_market(self, event: MarketEvent) -> List[SignalEvent]:
        """Handle market event and generate signals."""
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
        # Update price history
        self.prices.append(event.price)
        
        # Calculate MACD, Signal, and Histogram
        macd, signal, histogram = self._calculate_macd()
        
        # Not enough data yet
        if macd is None or signal is None:
            return []
        
        signals = []
        
        # Check for crossover
        # BUY: MACD crosses above signal (was below, now above)
        if self.state == "FLAT":
            if self.prev_macd is not None and self.prev_signal is not None:
                # Crossover: MACD was below signal, now above
                if self.prev_macd <= self.prev_signal and macd > signal:
                    # Also check histogram is positive (trend strengthening)
                    if histogram is not None and histogram > 0:
                        self.state = "LONG"
                        logger.info(
                            f"MACD BUY {event.symbol} @ {event.price:.2f} "
                            f"(MACD={macd:.4f}, Signal={signal:.4f}, Hist={histogram:.4f})"
                        )
                        signals.append(
                            SignalEvent(
                                timestamp=event.timestamp,
                                symbol=event.symbol,
                                direction="BUY",
                                price=event.price,
                            )
                        )
        
        # SELL: MACD crosses below signal (was above, now below)
        elif self.state == "LONG":
            if self.prev_macd is not None and self.prev_signal is not None:
                # Crossover: MACD was above signal, now below
                if self.prev_macd >= self.prev_signal and macd < signal:
                    # Also check histogram is negative (trend weakening)
                    if histogram is not None and histogram < 0:
                        self.state = "FLAT"
                        logger.info(
                            f"MACD SELL {event.symbol} @ {event.price:.2f} "
                            f"(MACD={macd:.4f}, Signal={signal:.4f}, Hist={histogram:.4f})"
                        )
                        signals.append(
                            SignalEvent(
                                timestamp=event.timestamp,
                                symbol=event.symbol,
                                direction="SELL",
                                price=event.price,
                            )
                        )
        
        # Update previous values for next crossover detection
        self.prev_macd = macd
        self.prev_signal = signal
        
        return signals

