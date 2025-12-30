"""
Test script to demonstrate HoldThroughCrashStrategy
Shows how equity drops when holding positions through price crashes
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_queue import EventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.hold_through_crash import HoldThroughCrashStrategy
from risk.engine import PassThroughRiskManager
from execution.simulator import ExecutionHandler
from portfolio.state import PortfolioState
from analysis.equity_analyzer import EquityAnalyzer
from analysis.equity_plotter import plot_equity
import matplotlib
matplotlib.use('Agg')  # Suppress plots for testing

# Use the same price data as main.py
PRICE_DATA = {
    "APPL": [100, 101, 102, 100, 100, 97, 100, 103, 98, 94, 96, 101],
    "MSFT": [200, 202, 1, 10, 105, 105, 1, 206, 207, 100, 200]
}

def main():
    print("=" * 80)
    print("HOLD THROUGH CRASH STRATEGY TEST")
    print("=" * 80)
    print("\nThis strategy will:")
    print("  - Buy MSFT at t=12 (before crash)")
    print("  - Hold through the crash at t=14+ (prices: 1, 10, 105, etc.)")
    print("  - Sell at t=22")
    print("  - You should see equity DROP during the crash!\n")
    
    queue = EventQueue()
    dispatcher = Dispatcher()
    
    risk = PassThroughRiskManager(fixed_quantity=10)
    execution = ExecutionHandler()
    portfolio = PortfolioState(initial_cash=10000)
    
    # Use HoldThroughCrashStrategy for MSFT
    msft_strategy = HoldThroughCrashStrategy(
        symbol="MSFT",
        buy_at_timestamp=12,
        sell_at_timestamp=22
    )
    dispatcher.register_handler(MarketEvent, msft_strategy.handle_market)
    
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    market_events = []
    t = 0
    for symbol, prices in PRICE_DATA.items():
        for price in prices:
            event = MarketEvent(timestamp=t, symbol=symbol, price=price)
            market_events.append(event)
            queue.put(event)
            t += 1
    
    # Process events
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for e in new_events:
            queue.put(e)
    
    # Rebuild equity curve (same as main.py)
    aligned_equity_curve = []
    replay_cash = portfolio.initial_cash
    replay_positions = {}
    replay_prices = {}
    
    all_events = []
    for event in market_events:
        all_events.append(('market', event.timestamp, event.symbol, event.price))
    for fill in portfolio.trades:
        all_events.append(('fill', fill.timestamp, fill.symbol, fill.direction, fill.quantity, fill.fill_price))
    
    all_events.sort(key=lambda x: (x[1], 0 if x[0] == 'market' else 1))
    
    event_idx = 0
    for i, market_event in enumerate(market_events):
        while event_idx < len(all_events) and all_events[event_idx][1] <= market_event.timestamp:
            evt = all_events[event_idx]
            if evt[0] == 'market':
                _, ts, symbol, price = evt
                replay_prices[symbol] = price
            elif evt[0] == 'fill':
                _, ts, symbol, direction, qty, price = evt
                replay_prices[symbol] = price
                if direction == 'BUY':
                    replay_cash -= qty * price
                    replay_positions[symbol] = replay_positions.get(symbol, 0) + qty
                else:
                    replay_cash += qty * price
                    replay_positions[symbol] = replay_positions.get(symbol, 0) - qty
                    if replay_positions[symbol] == 0:
                        del replay_positions[symbol]
            event_idx += 1
        
        equity = replay_cash
        for sym, qty in replay_positions.items():
            if sym in replay_prices:
                equity += qty * replay_prices[sym]
        aligned_equity_curve.append(equity)
    
    # Analysis
    analyzer = EquityAnalyzer(
        market_events=market_events,
        fills=portfolio.trades,
        equity_curve=aligned_equity_curve,
        initial_cash=10000
    )
    analyzer.run()
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print(f"\nTrade History:")
    for trade in portfolio.trades:
        print(f"  t={trade.timestamp} {trade.direction} {trade.quantity} {trade.symbol} @ {trade.fill_price}")
    
    print(f"\nFinal Portfolio State:")
    print(f"  Cash: {portfolio.cash:.2f}")
    print(f"  Positions: {portfolio.positions}")
    print(f"  Realized PnL: {portfolio.realized_pnl:.2f}")
    
    print(f"\nEquity Curve Analysis:")
    print(f"  Initial Equity: {aligned_equity_curve[0]:.2f}")
    print(f"  Final Equity: {aligned_equity_curve[-1]:.2f}")
    print(f"  Max Equity: {max(aligned_equity_curve):.2f}")
    print(f"  Min Equity: {min(aligned_equity_curve):.2f}")
    print(f"  Max Drawdown: {analyzer.max_drawdown:.2%}")
    print(f"  Sharpe Ratio: {analyzer.sharpe:.2f}")
    
    print(f"\nEquity During MSFT Crash (t=12-22):")
    print(f"{'t':<4} {'MSFT Price':<12} {'Equity':<12} {'Change':<12} {'Positions':<20}")
    print("-" * 70)
    
    prev_equity = aligned_equity_curve[0]
    for i, event in enumerate(market_events):
        if event.symbol == 'MSFT' and event.timestamp >= 12:
            equity = aligned_equity_curve[i]
            change = equity - prev_equity
            change_str = f"{change:+.2f}" if abs(change) > 0.01 else "0.00"
            
            # Get positions at this point
            replay_cash_check = 10000
            replay_positions_check = {}
            replay_prices_check = {}
            for evt in all_events:
                if evt[1] <= event.timestamp:
                    if evt[0] == 'market':
                        _, ts, symbol, price = evt
                        replay_prices_check[symbol] = price
                    elif evt[0] == 'fill':
                        _, ts, symbol, direction, qty, price = evt
                        replay_prices_check[symbol] = price
                        if direction == 'BUY':
                            replay_cash_check -= qty * price
                            replay_positions_check[symbol] = replay_positions_check.get(symbol, 0) + qty
                        else:
                            replay_cash_check += qty * price
                            replay_positions_check[symbol] = replay_positions_check.get(symbol, 0) - qty
                            if replay_positions_check[symbol] == 0:
                                del replay_positions_check[symbol]
            
            pos_str = ", ".join([f"{k}:{v}" for k, v in replay_positions_check.items()]) if replay_positions_check else "None"
            print(f"{event.timestamp:<4} {event.price:<12.2f} {equity:<12.2f} {change_str:<12} {pos_str:<20}")
            prev_equity = equity
    
    print("\n" + "=" * 80)
    print("✓ You should see equity DROP when MSFT price crashes!")
    print("=" * 80)

if __name__ == "__main__":
    main()

