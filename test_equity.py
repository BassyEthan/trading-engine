"""
Test script to manually verify equity curve calculations
"""
from core.event_queue import EventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.one_shot import OneShotBuyStrategy
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import PassThroughRiskManager
from execution.simulator import ExecutionHandler
from portfolio.state import PortfolioState

PRICE_DATA = {
    "APPL": [100, 101, 102, 100, 100, 97, 100, 103, 98, 94, 96, 101],
    "MSFT": [200, 202, 1, 10, 105, 105, 1, 206, 207, 100, 200]
}

STRATEGY_CONFIG = {
    "APPL": {
        "class": RollingMeanReversionStrategy,
        "params": {"window": 5, "threshold": 2.0}
    },
    "MSFT": {
        "class": OneShotBuyStrategy,
        "params": {}
    }
}

def manual_calculate_equity():
    """Manually calculate expected equity at each step"""
    print("=" * 80)
    print("MANUAL EQUITY CALCULATION VERIFICATION")
    print("=" * 80)
    
    cash = 10000
    positions = {}  # {symbol: quantity}
    latest_prices = {}
    equity_history = []
    
    # Process events in order
    events = []
    t = 0
    for symbol, prices in PRICE_DATA.items():
        for price in prices:
            events.append(('market', t, symbol, price))
            t += 1
    
    # Based on the strategy, we know:
    # APPL: BUY at t=5 (price 97), SELL at t=6 (price 100)
    # APPL: BUY at t=9 (price 94), SELL at t=11 (price 101)
    # MSFT: BUY at t=12 (price 200), SELL at t=13 (price 202)
    
    fills = [
        ('fill', 5, 'APPL', 'BUY', 10, 97),
        ('fill', 6, 'APPL', 'SELL', 10, 100),
        ('fill', 9, 'APPL', 'BUY', 10, 94),
        ('fill', 11, 'APPL', 'SELL', 10, 101),
        ('fill', 12, 'MSFT', 'BUY', 10, 200),
        ('fill', 13, 'MSFT', 'SELL', 10, 202),
    ]
    
    # Combine and sort by timestamp
    all_events = events + fills
    all_events.sort(key=lambda x: (x[1], 0 if x[0] == 'market' else 1))  # market events first at same timestamp
    
    fill_idx = 0
    for event_type, timestamp, *rest in all_events:
        if event_type == 'market':
            symbol, price = rest
            latest_prices[symbol] = price
            
            # Calculate equity
            equity = cash
            for sym, qty in positions.items():
                if sym in latest_prices:
                    equity += qty * latest_prices[sym]
            
            equity_history.append((timestamp, symbol, price, equity, cash, dict(positions), dict(latest_prices)))
            
        elif event_type == 'fill':
            symbol, direction, quantity, fill_price = rest
            latest_prices[symbol] = fill_price
            
            if direction == 'BUY':
                cash -= quantity * fill_price
                positions[symbol] = positions.get(symbol, 0) + quantity
            else:  # SELL
                cash += quantity * fill_price
                positions[symbol] = positions.get(symbol, 0) - quantity
                if positions[symbol] == 0:
                    del positions[symbol]
            
            # Calculate equity after fill
            equity = cash
            for sym, qty in positions.items():
                if sym in latest_prices:
                    equity += qty * latest_prices[sym]
            
            equity_history.append((timestamp, symbol, fill_price, equity, cash, dict(positions), dict(latest_prices)))
    
    return equity_history

def run_simulation():
    """Run the actual simulation"""
    print("\n" + "=" * 80)
    print("SIMULATION RUN")
    print("=" * 80)
    
    queue = EventQueue()
    dispatcher = Dispatcher()
    
    risk = PassThroughRiskManager(fixed_quantity=10)
    execution = ExecutionHandler()
    portfolio = PortfolioState(initial_cash=10000)
    
    strategies = []
    for symbol, cfg in STRATEGY_CONFIG.items():
        strategy = cfg["class"](symbol=symbol, **cfg["params"])
        strategies.append(strategy)
        dispatcher.register_handler(MarketEvent, strategy.handle_market)
    
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
    
    step = 0
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for e in new_events:
            queue.put(e)
        step += 1
    
    return portfolio, market_events

def compare_results(manual_history, portfolio, market_events):
    """Compare manual calculations with simulation results"""
    print("\n" + "=" * 80)
    print("COMPARISON: MANUAL vs SIMULATION")
    print("=" * 80)
    
    # Rebuild equity curve using the same replay logic as main.py
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
    
    if not aligned_equity_curve:
        aligned_equity_curve = [portfolio.initial_cash] * len(market_events)
    
    print(f"\nMarket Events: {len(market_events)}")
    print(f"Equity Curve Length: {len(aligned_equity_curve)}")
    print(f"Manual History Entries: {len(manual_history)}")
    
    # Extract equity values at market event timestamps from manual calculation
    manual_equity_at_events = {}
    for ts, symbol, price, equity, cash, positions, prices_dict in manual_history:
        if (ts, symbol, price) in [(e.timestamp, e.symbol, e.price) for e in market_events]:
            manual_equity_at_events[ts] = equity
    
    # Build manual equity curve aligned with market events
    manual_equity_curve = []
    last_manual_equity = 10000
    for i, event in enumerate(market_events):
        if event.timestamp in manual_equity_at_events:
            last_manual_equity = manual_equity_at_events[event.timestamp]
        manual_equity_curve.append(last_manual_equity)
    
    print(f"\n{'Timestamp':<10} {'Symbol':<6} {'Price':<8} {'Manual Equity':<15} {'Sim Equity':<15} {'Match':<6}")
    print("-" * 80)
    
    matches = 0
    for i, event in enumerate(market_events):
        manual_eq = manual_equity_curve[i] if i < len(manual_equity_curve) else 0
        sim_eq = aligned_equity_curve[i] if i < len(aligned_equity_curve) else 0
        match = "✓" if abs(manual_eq - sim_eq) < 0.01 else "✗"
        if match == "✓":
            matches += 1
        
        print(f"{event.timestamp:<10} {event.symbol:<6} {event.price:<8.2f} {manual_eq:<15.2f} {sim_eq:<15.2f} {match:<6}")
    
    print(f"\nMatches: {matches}/{len(market_events)}")
    
    # Show key points
    print("\n" + "=" * 80)
    print("KEY EVENTS BREAKDOWN")
    print("=" * 80)
    
    for ts, symbol, price, equity, cash, positions, prices_dict in manual_history[:20]:  # First 20 events
        pos_str = ", ".join([f"{k}:{v}" for k, v in positions.items()]) if positions else "None"
        print(f"t={ts:2d} | {symbol:4s} @ {price:6.2f} | Equity: {equity:8.2f} | Cash: {cash:8.2f} | Positions: {pos_str}")
    
    # Calculate stats
    print("\n" + "=" * 80)
    print("STATISTICS COMPARISON")
    print("=" * 80)
    
    # Manual drawdown
    peak = 10000
    max_dd = 0
    for equity in manual_equity_curve:
        peak = max(peak, equity)
        dd = (equity - peak) / peak
        max_dd = min(max_dd, dd)
    
    # Simulation drawdown (from analyzer)
    from analysis.equity_analyzer import EquityAnalyzer
    analyzer = EquityAnalyzer(
        market_events=market_events,
        fills=portfolio.trades,
        equity_curve=aligned_equity_curve,
        initial_cash=10000
    )
    analyzer.run()
    
    print(f"Manual Max Drawdown: {max_dd:.2%}")
    print(f"Simulation Max Drawdown: {analyzer.max_drawdown:.2%}")
    print(f"Manual Final Equity: {manual_equity_curve[-1]:.2f}")
    print(f"Simulation Final Equity: {aligned_equity_curve[-1]:.2f}")
    print(f"Simulation Final Cash: {portfolio.cash:.2f}")
    print(f"Simulation Sharpe: {analyzer.sharpe:.2f}")
    
    return matches == len(market_events)

if __name__ == "__main__":
    manual_history = manual_calculate_equity()
    portfolio, market_events = run_simulation()
    is_correct = compare_results(manual_history, portfolio, market_events)
    
    print("\n" + "=" * 80)
    if is_correct:
        print("✓ VERIFICATION PASSED: All equity values match!")
    else:
        print("✗ VERIFICATION FAILED: Some equity values don't match")
    print("=" * 80)

