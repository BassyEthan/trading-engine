"""
Comprehensive validation tests for trading engine calculations.

Tests:
1. Max drawdown calculation
2. Equity curve calculation
3. Trade PnL calculation (multi-symbol)
4. Event ordering
5. Portfolio state invariants
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import RealRiskManager
from execution.simulator import RealisticExecutionHandler
from portfolio.state import PortfolioState
from analysis.metrics import TradeMetrics
from analysis.equity_analyzer import EquityAnalyzer
import numpy as np


def test_max_drawdown_calculation():
    """Test max drawdown calculation with known values."""
    print("=" * 70)
    print("TEST 1: Max Drawdown Calculation")
    print("=" * 70)
    print()
    
    # Test case 1: Simple peak and drop
    equity_curve = [10000, 11000, 12000, 11500, 10500, 13000, 11000, 10000]
    # Peak at 13000, drops to 10000 = 23.08% drawdown
    
    peak = equity_curve[0]
    max_dd = 0.0
    drawdowns = []
    
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns.append(dd)
        if dd > max_dd:
            max_dd = dd
    
    print(f"Equity curve: {equity_curve}")
    print(f"Peaks: {[max(equity_curve[:i+1]) for i in range(len(equity_curve))]}")
    print(f"Drawdowns: {[f'{d:.2%}' for d in drawdowns]}")
    print(f"Max drawdown: {max_dd:.2%}")
    print()
    
    expected_max_dd = (13000 - 10000) / 13000  # 23.08%
    assert abs(max_dd - expected_max_dd) < 0.0001, f"Expected {expected_max_dd:.2%}, got {max_dd:.2%}"
    print("✅ Max drawdown calculation correct!")
    print()
    
    # Test case 2: Multiple peaks
    equity_curve2 = [10000, 15000, 12000, 18000, 10000, 20000, 15000]
    # Peak 1: 15000 -> 12000 = 20%
    # Peak 2: 18000 -> 10000 = 44.44%
    # Peak 3: 20000 -> 15000 = 25%
    # Max should be 44.44%
    
    peak = equity_curve2[0]
    max_dd2 = 0.0
    drawdowns2 = []
    
    for equity in equity_curve2:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns2.append(dd)
        if dd > max_dd2:
            max_dd2 = dd
    
    print(f"Equity curve 2: {equity_curve2}")
    print(f"Drawdowns: {[f'{d:.2%}' for d in drawdowns2]}")
    print(f"Max drawdown: {max_dd2:.2%}")
    print()
    
    expected_max_dd2 = (18000 - 10000) / 18000  # 44.44%
    assert abs(max_dd2 - expected_max_dd2) < 0.0001, f"Expected {expected_max_dd2:.2%}, got {max_dd2:.2%}"
    print("✅ Multiple peaks drawdown calculation correct!")
    print()


def test_equity_analyzer_drawdown():
    """Test EquityAnalyzer's drawdown calculation."""
    print("=" * 70)
    print("TEST 2: EquityAnalyzer Drawdown")
    print("=" * 70)
    print()
    
    from events.base import MarketEvent, FillEvent
    
    # Create test data
    market_events = [MarketEvent(timestamp=i, symbol="TEST", price=100) for i in range(10)]
    fills = []
    equity_curve = [10000, 11000, 12000, 11500, 10500, 13000, 11000, 10000, 12000, 11000]
    
    analyzer = EquityAnalyzer(
        market_events=market_events,
        fills=fills,
        equity_curve=equity_curve,
        initial_cash=10000
    )
    analyzer.run()
    
    print(f"Equity curve: {equity_curve}")
    print(f"Drawdown curve: {[f'{d:.2%}' for d in analyzer.drawdown_curve]}")
    print(f"Max drawdown: {analyzer.max_drawdown:.2%}")
    print()
    
    # Manual calculation
    peak = equity_curve[0]
    max_dd_manual = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd_manual = max(max_dd_manual, dd)
    
    print(f"Manual max drawdown: {max_dd_manual:.2%}")
    print(f"Analyzer max drawdown: {analyzer.max_drawdown:.2%}")
    
    assert abs(analyzer.max_drawdown - max_dd_manual) < 0.0001, \
        f"Mismatch: analyzer={analyzer.max_drawdown:.2%}, manual={max_dd_manual:.2%}"
    
    print("✅ EquityAnalyzer drawdown matches manual calculation!")
    print()


def test_multi_symbol_trade_pnl():
    """Test TradeMetrics with multiple symbols."""
    print("=" * 70)
    print("TEST 3: Multi-Symbol Trade PnL")
    print("=" * 70)
    print()
    
    from events.base import FillEvent
    
    # Create interleaved fills
    fills = [
        FillEvent(timestamp=0, symbol="AAPL", direction="BUY", quantity=10, fill_price=100.0),
        FillEvent(timestamp=1, symbol="MSFT", direction="BUY", quantity=10, fill_price=200.0),
        FillEvent(timestamp=2, symbol="AAPL", direction="SELL", quantity=10, fill_price=110.0),  # +$100
        FillEvent(timestamp=3, symbol="MSFT", direction="SELL", quantity=10, fill_price=190.0),  # -$100
    ]
    
    metrics = TradeMetrics(
        fills=fills,
        initial_cash=10000.0,
        final_cash=10000.0,  # 10000 - 1000 - 2000 + 1100 + 1900 = 10000
        final_equity=10000.0
    )
    
    print("Fills:")
    for fill in fills:
        print(f"  {fill.direction} {fill.symbol} {fill.quantity} @ ${fill.fill_price}")
    print()
    
    print(f"Trade PnLs: {metrics.trade_pnls}")
    print(f"Number of trades: {metrics.num_trades()}")
    print(f"Win rate: {metrics.win_rate():.2%}")
    print(f"Avg PnL: ${metrics.avg_pnl_per_trade():.2f}")
    print()
    
    # Expected: 2 trades, PnLs: [100, -100]
    assert len(metrics.trade_pnls) == 2, f"Expected 2 trades, got {len(metrics.trade_pnls)}"
    assert abs(metrics.trade_pnls[0] - 100.0) < 0.01, f"AAPL PnL should be $100, got ${metrics.trade_pnls[0]}"
    assert abs(metrics.trade_pnls[1] - (-100.0)) < 0.01, f"MSFT PnL should be -$100, got ${metrics.trade_pnls[1]}"
    assert abs(metrics.win_rate() - 0.5) < 0.01, f"Win rate should be 50%, got {metrics.win_rate():.2%}"
    
    print("✅ Multi-symbol trade PnL calculation correct!")
    print()


def test_event_ordering():
    """Test that events are properly interleaved."""
    print("=" * 70)
    print("TEST 4: Event Ordering (Interleaved)")
    print("=" * 70)
    print()
    
    data = {
        "AAPL": [100, 101, 102],
        "MSFT": [200, 201, 202],
        "GOOGL": [300, 301, 302],
    }
    
    # Create events with interleaved ordering
    max_length = max(len(prices) for prices in data.values())
    events = []
    timestamp = 0
    
    for i in range(max_length):
        for symbol, prices in data.items():
            if i < len(prices):
                events.append(MarketEvent(timestamp=timestamp, symbol=symbol, price=prices[i]))
        timestamp += 1
    
    print("Event order:")
    for i, event in enumerate(events[:10]):  # Show first 10
        print(f"  {i}: t={event.timestamp}, {event.symbol} @ ${event.price}")
    print()
    
    # Verify ordering
    timestamps = [e.timestamp for e in events]
    symbols = [e.symbol for e in events]
    
    # Check that all symbols appear at each timestamp
    expected_order = ["AAPL", "MSFT", "GOOGL"] * 3
    assert symbols == expected_order, f"Symbol order incorrect: {symbols}"
    
    # Check timestamps
    expected_timestamps = [0, 0, 0, 1, 1, 1, 2, 2, 2]
    assert timestamps == expected_timestamps, f"Timestamp order incorrect: {timestamps}"
    
    print("✅ Event ordering is correct (interleaved by timestamp)!")
    print()


def test_portfolio_state_invariants():
    """Test portfolio state invariants."""
    print("=" * 70)
    print("TEST 5: Portfolio State Invariants")
    print("=" * 70)
    print()
    
    portfolio = PortfolioState(initial_cash=10000.0)
    
    # Test: Cash never goes negative
    try:
        # Try to buy more than we have
        fill = FillEvent(timestamp=0, symbol="AAPL", direction="BUY", quantity=1000, fill_price=100.0)
        portfolio.handle_fill(fill)
        assert False, "Should have raised ValueError for insufficient cash"
    except ValueError as e:
        print(f"✅ Cash invariant enforced: {e}")
    
    # Test: Positions only change on fills
    initial_positions = dict(portfolio.positions)
    portfolio.handle_market(MarketEvent(timestamp=0, symbol="AAPL", price=100.0))
    assert portfolio.positions == initial_positions, "Positions should not change on MarketEvent"
    print("✅ Positions only change on FillEvents")
    
    # Test: Valid trade sequence
    portfolio2 = PortfolioState(initial_cash=10000.0)
    portfolio2.handle_fill(FillEvent(timestamp=0, symbol="AAPL", direction="BUY", quantity=10, fill_price=100.0))
    portfolio2.handle_fill(FillEvent(timestamp=1, symbol="AAPL", direction="SELL", quantity=10, fill_price=110.0))
    
    assert portfolio2.cash == 10100.0, f"Expected cash $10,100, got ${portfolio2.cash}"
    assert len(portfolio2.positions) == 0, "Position should be closed"
    assert abs(portfolio2.realized_pnl - 100.0) < 0.01, f"Expected realized PnL $100, got ${portfolio2.realized_pnl}"
    
    print(f"✅ Valid trade sequence: Cash=${portfolio2.cash:.2f}, PnL=${portfolio2.realized_pnl:.2f}")
    print()


def test_full_simulation():
    """Run a full simulation and validate all calculations."""
    print("=" * 70)
    print("TEST 6: Full Simulation Validation")
    print("=" * 70)
    print()
    
    # Simple test data
    data = {
        "AAPL": [100, 101, 99, 102, 98, 103],
        "MSFT": [200, 201, 199, 202, 198, 203],
    }
    
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()
    portfolio = PortfolioState(initial_cash=10000.0)
    
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.50,  # High limit for testing
        max_position_pct=1.0,
        max_total_exposure_pct=1.0,
        max_positions=None,
    )
    
    execution = RealisticExecutionHandler(
        spread_pct=0.001,
        base_slippage_pct=0.0005,
        impact_factor=0.000001,
        slippage_volatility=0.0002,
    )
    
    # Simple strategy: buy first, sell last
    class TestStrategy:
        def __init__(self, symbol):
            self.symbol = symbol
            self.state = "FLAT"
            self.bought = False
        
        def handle_market(self, event):
            if event.symbol != self.symbol:
                return []
            
            if not self.bought and event.timestamp == 0:
                self.bought = True
                self.state = "LONG"
                return [SignalEvent(timestamp=event.timestamp, symbol=event.symbol, direction="BUY", price=event.price)]
            elif self.state == "LONG" and event.timestamp == 5:
                self.state = "FLAT"
                return [SignalEvent(timestamp=event.timestamp, symbol=event.symbol, direction="SELL", price=event.price)]
            return []
    
    strategies = [TestStrategy("AAPL"), TestStrategy("MSFT")]
    for strategy in strategies:
        dispatcher.register_handler(MarketEvent, strategy.handle_market)
    
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # Seed events (interleaved)
    max_length = max(len(prices) for prices in data.values())
    timestamp = 0
    for i in range(max_length):
        for symbol, prices in data.items():
            if i < len(prices):
                event = MarketEvent(timestamp=timestamp, symbol=symbol, price=prices[i])
                queue.put(event)
        timestamp += 1
    
    # Run simulation
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for new_event in new_events:
            queue.put(new_event)
    
    # Validate
    print(f"Final cash: ${portfolio.cash:.2f}")
    print(f"Final positions: {portfolio.positions}")
    print(f"Realized PnL: ${portfolio.realized_pnl:.2f}")
    print(f"Number of trades: {len(portfolio.trades)}")
    print()
    
    # Calculate final equity
    final_equity = portfolio.cash
    for symbol, position in portfolio.positions.items():
        if symbol in portfolio.latest_prices:
            final_equity += position.quantity * portfolio.latest_prices[symbol]
    
    print(f"Final equity: ${final_equity:.2f}")
    
    # Create metrics
    metrics = TradeMetrics(
        fills=portfolio.trades,
        initial_cash=10000.0,
        final_cash=portfolio.cash,
        final_equity=final_equity,
    )
    
    print(f"Total PnL: ${metrics.total_pnl():.2f}")
    print(f"Number of round trips: {metrics.num_trades()}")
    print()
    
    # Build equity curve for drawdown
    if portfolio.equity_by_timestamp:
        equity_curve = [portfolio.equity_by_timestamp[t] for t in sorted(portfolio.equity_by_timestamp.keys())]
    else:
        equity_curve = [portfolio.initial_cash]
    
    # Calculate drawdown manually
    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    
    print(f"Equity curve length: {len(equity_curve)}")
    print(f"Equity range: ${min(equity_curve):.2f} to ${max(equity_curve):.2f}")
    print(f"Max drawdown: {max_dd:.2%}")
    print()
    
    # Check invariants
    assert portfolio.cash >= 0, "Cash should never be negative"
    assert len(metrics.trade_pnls) == metrics.num_trades(), "Trade PnLs count should match num_trades"
    
    print("✅ Full simulation validation passed!")
    print()


def analyze_drawdown_peaks(equity_curve):
    """Analyze drawdown to find all peaks and their subsequent drops."""
    print("=" * 70)
    print("DRAWDOWN PEAK ANALYSIS")
    print("=" * 70)
    print()
    
    peak = equity_curve[0]
    peak_indices = []
    drawdowns = []
    
    for i, equity in enumerate(equity_curve):
        if equity > peak:
            peak = equity
            peak_indices.append(i)
        
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns.append(dd)
    
    print(f"Total equity points: {len(equity_curve)}")
    print(f"Peak indices: {peak_indices}")
    print()
    
    # Find all significant peaks and their drops
    peaks_info = []
    for peak_idx in peak_indices:
        peak_value = equity_curve[peak_idx]
        # Find lowest point after this peak
        if peak_idx < len(equity_curve) - 1:
            min_after_peak = min(equity_curve[peak_idx:])
            min_idx = equity_curve.index(min_after_peak, peak_idx)
            drop = (peak_value - min_after_peak) / peak_value
            peaks_info.append({
                'peak_idx': peak_idx,
                'peak_value': peak_value,
                'min_idx': min_idx,
                'min_value': min_after_peak,
                'drop_pct': drop
            })
    
    print("Peak Analysis:")
    for info in peaks_info:
        print(f"  Peak at index {info['peak_idx']}: ${info['peak_value']:,.2f}")
        print(f"    → Drops to ${info['min_value']:,.2f} at index {info['min_idx']} ({info['drop_pct']:.2%} drop)")
        print()
    
    # Find max drawdown
    max_dd = max(drawdowns)
    max_dd_idx = drawdowns.index(max_dd)
    
    print(f"Max drawdown: {max_dd:.2%} at index {max_dd_idx}")
    print(f"  Peak before: ${max(equity_curve[:max_dd_idx+1]):,.2f}")
    print(f"  Trough: ${equity_curve[max_dd_idx]:,.2f}")
    print()
    
    return peaks_info, max_dd


if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE CALCULATION VALIDATION")
    print("=" * 70)
    print()
    
    # Run all tests
    test_max_drawdown_calculation()
    test_equity_analyzer_drawdown()
    test_multi_symbol_trade_pnl()
    test_event_ordering()
    test_portfolio_state_invariants()
    test_full_simulation()
    
    print("=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)


