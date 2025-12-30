"""
Test that risk manager correctly rejects trades when drawdown > limit.
"""

import sys
import os
import matplotlib
matplotlib.use('Agg')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher
from portfolio.state import PortfolioState
from risk.engine import RealRiskManager
from execution.simulator import ExecutionHandler
from events.base import MarketEvent, SignalEvent
from strategies.multi_signal import MultiSignalStrategy


def test_drawdown_rejection():
    """Test that risk manager rejects trades when drawdown exceeds limit."""
    
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()
    portfolio = PortfolioState(initial_cash=10000)
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.15,  # 15% limit
    )
    
    execution = ExecutionHandler()
    strategy = MultiSignalStrategy(
        symbol='MSFT',
        signals=[
            (12, 'BUY'),   # Buy at t=12
            (14, 'BUY'),   # Try to buy again at t=14 (during crash)
        ]
    )
    
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    dispatcher.register_handler(MarketEvent, strategy.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # Step 1: Buy at t=12 @ $200
    event = MarketEvent(timestamp=12, symbol='MSFT', price=200)
    new_events = dispatcher.dispatch(event)
    for e in new_events:
        queue.put(e)
    
    # Process fill from t=12
    while not queue.is_empty():
        e = queue.get()
        if isinstance(e, FillEvent) and e.symbol == 'MSFT':
            portfolio.handle_fill(e)
            break
        new_events = dispatcher.dispatch(e)
        for ne in new_events:
            queue.put(ne)
    
    # Step 2: Price update at t=13
    event = MarketEvent(timestamp=13, symbol='MSFT', price=202)
    portfolio.handle_market(event)
    dispatcher.dispatch(event)
    
    # Step 3: CRASH at t=14 @ $1
    event = MarketEvent(timestamp=14, symbol='MSFT', price=1)
    portfolio.handle_market(event)  # Update price first
    
    # Check equity and drawdown
    equity = risk._get_current_equity()
    dd = risk._get_current_drawdown()
    print(f"t=14: After crash, equity={equity:.2f}, drawdown={dd:.2%}")
    
    assert abs(dd) > 0.15, f"Drawdown {dd:.2%} should be > 15%"
    
    # Step 4: Generate signal and check rejection
    new_events = dispatcher.dispatch(event)
    rejected = False
    for e in new_events:
        if isinstance(e, SignalEvent) and e.symbol == 'MSFT' and e.timestamp == 14:
            result = risk.handle_signal(e)
            if not result:  # Empty list means rejected
                rejected = True
                print(f"✅ CORRECT: Trade rejected (drawdown {dd:.2%} > 15%)")
            else:
                print(f"❌ ERROR: Trade approved when it should be rejected!")
    
    assert rejected, "Risk manager should reject trade when drawdown > 15%"
    print("✅ Test passed: Risk manager correctly rejects trades in drawdown")


if __name__ == "__main__":
    from events.base import OrderEvent, FillEvent
    test_drawdown_rejection()

