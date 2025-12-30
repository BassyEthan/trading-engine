"""
Test script to verify RealRiskManager rejects trades correctly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_queue import EventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.hold_through_crash import HoldThroughCrashStrategy
from risk.engine import RealRiskManager
from execution.simulator import ExecutionHandler
from portfolio.state import PortfolioState

def test_drawdown_rejection():
    """Test that trades are rejected when drawdown exceeds limit"""
    print("=" * 80)
    print("TEST: Drawdown Limit Rejection")
    print("=" * 80)
    
    queue = EventQueue()
    dispatcher = Dispatcher()
    portfolio = PortfolioState(initial_cash=10000)
    
    # Create risk manager with strict 5% drawdown limit
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.05,  # 5% max drawdown - very strict
    )
    
    execution = ExecutionHandler()
    
    # Strategy that will hold through crash
    strategy = HoldThroughCrashStrategy(
        symbol="MSFT",
        buy_at_timestamp=12,
        sell_at_timestamp=22
    )
    
    dispatcher.register_handler(MarketEvent, strategy.handle_market)
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # MSFT prices with crash
    msft_prices = [200, 202, 1, 10, 105, 105, 1, 206, 207, 100, 200]
    market_events = []
    
    for i, price in enumerate(msft_prices):
        event = MarketEvent(timestamp=i+12, symbol='MSFT', price=price)
        market_events.append(event)
        queue.put(event)
    
    # Process events
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for e in new_events:
            queue.put(e)
    
    # Check results
    print(f"\nTrades executed: {len(portfolio.trades)}")
    print(f"Rejections: {risk.get_rejection_summary()}")
    
    # After the crash at t=14, drawdown should exceed 5%, so subsequent signals should be rejected
    if risk.get_rejection_summary()["total"] > 0:
        print("✓ Drawdown rejection working!")
    else:
        print("⚠ No rejections - drawdown might not have exceeded limit at signal times")
    
    return risk.get_rejection_summary()

def test_cash_rejection():
    """Test that trades are rejected when insufficient cash"""
    print("\n" + "=" * 80)
    print("TEST: Cash Availability Rejection")
    print("=" * 80)
    
    portfolio = PortfolioState(initial_cash=500)  # Low cash
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
    )
    
    # Try to buy expensive stock
    signal = SignalEvent(timestamp=0, symbol='EXPENSIVE', direction='BUY', price=100)
    result = risk.handle_signal(signal)
    
    if not result:  # Empty list = rejected
        print("✓ Cash rejection working!")
        print(f"  Rejection reason: {risk.rejections[0]['reason']}")
    else:
        print("✗ Cash rejection failed")
    
    return len(result) == 0

def test_position_size_rejection():
    """Test that trades are rejected when position size exceeds limit"""
    print("\n" + "=" * 80)
    print("TEST: Position Size Limit Rejection")
    print("=" * 80)
    
    portfolio = PortfolioState(initial_cash=10000)
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=100,  # Large quantity
        max_position_pct=0.10,  # Max 10% of equity in single position
    )
    
    # Try to buy expensive stock (100 shares * 100 = 10,000, which is 100% of equity)
    signal = SignalEvent(timestamp=0, symbol='EXPENSIVE', direction='BUY', price=100)
    result = risk.handle_signal(signal)
    
    if not result:  # Empty list = rejected
        print("✓ Position size rejection working!")
        print(f"  Rejection reason: {risk.rejections[0]['reason']}")
    else:
        print("✗ Position size rejection failed")
    
    return len(result) == 0

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("REAL RISK MANAGER TESTS")
    print("=" * 80)
    
    test_drawdown_rejection()
    test_cash_rejection()
    test_position_size_rejection()
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)

