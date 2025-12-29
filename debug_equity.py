"""
Debug script to check equity during stress test periods
"""
from main import *
import sys

# Suppress plot
import matplotlib
matplotlib.use('Agg')

queue = EventQueue()
dispatcher = Dispatcher()
risk = PassThroughRiskManager(fixed_quantity=10)
execution = ExecutionHandler()
portfolio = PortfolioState(initial_cash=10000)

strategies = []
for symbol, cfg in STRATEGY_CONFIG.items():
    strategy = cfg['class'](symbol=symbol, **cfg['params'])
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

# Track equity and positions at each step
equity_trace = []

while not queue.is_empty():
    event = queue.get()
    
    # Track state before processing
    if isinstance(event, MarketEvent):
        equity = portfolio.cash
        for sym, pos in portfolio.positions.items():
            if sym in portfolio.latest_prices:
                equity += pos.quantity * portfolio.latest_prices[sym]
        
        equity_trace.append({
            'timestamp': event.timestamp,
            'symbol': event.symbol,
            'price': event.price,
            'equity': equity,
            'cash': portfolio.cash,
            'positions': dict(portfolio.positions),
            'latest_prices': dict(portfolio.latest_prices)
        })
    
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

print("=" * 80)
print("EQUITY TRACE DURING STRESS PERIODS")
print("=" * 80)

print("\n--- MSFT Stress Period (prices: 1, 10, 105, 105, 1, 206, 207, 100, 200) ---")
print("Timestamps 12-22")
print(f"{'t':<4} {'Symbol':<6} {'Price':<8} {'Equity':<12} {'Cash':<12} {'Positions':<30} {'Equity Change':<15}")
print("-" * 100)

prev_equity = 10000
for i, event in enumerate(market_events):
    if event.timestamp >= 12:
        equity = aligned_equity_curve[i]
        pos_str = ", ".join([f"{k}:{v.quantity}" for k, v in portfolio.positions.items()]) if portfolio.positions else "None"
        eq_change = equity - prev_equity
        change_str = f"{eq_change:+.2f}" if abs(eq_change) > 0.01 else "0.00"
        print(f"{event.timestamp:<4} {event.symbol:<6} {event.price:<8.2f} {equity:<12.2f} {portfolio.cash:<12.2f} {pos_str:<30} {change_str:<15}")
        prev_equity = equity

print("\n--- APPL Stress Period (price drops to 97, then 94) ---")
print("Timestamps 5-11")
print(f"{'t':<4} {'Symbol':<6} {'Price':<8} {'Equity':<12} {'Cash':<12} {'Positions':<30} {'Equity Change':<15}")
print("-" * 100)

prev_equity = 10000
for i, event in enumerate(market_events):
    if 5 <= event.timestamp <= 11:
        equity = aligned_equity_curve[i]
        # Get positions at this point in replay
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
        eq_change = equity - prev_equity
        change_str = f"{eq_change:+.2f}" if abs(eq_change) > 0.01 else "0.00"
        print(f"{event.timestamp:<4} {event.symbol:<6} {event.price:<8.2f} {equity:<12.2f} {replay_cash_check:<12.2f} {pos_str:<30} {change_str:<15}")
        prev_equity = equity

print("\n--- Key Insight: When are positions held during price drops? ---")
print("\nFills:")
for fill in portfolio.trades:
    print(f"  t={fill.timestamp} {fill.direction} {fill.quantity} {fill.symbol} @ {fill.fill_price}")

print("\nPrice drops while holding positions:")
for i, event in enumerate(market_events):
    if i > 0:
        prev_price = market_events[i-1].price if market_events[i-1].symbol == event.symbol else None
        if prev_price and event.price < prev_price:
            # Check if we're holding this symbol
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
            
            if event.symbol in replay_positions_check and replay_positions_check[event.symbol] > 0:
                equity_before = aligned_equity_curve[i-1] if i > 0 else 10000
                equity_after = aligned_equity_curve[i]
                print(f"  t={event.timestamp} {event.symbol} drops {prev_price:.2f} -> {event.price:.2f} | "
                      f"Position: {replay_positions_check[event.symbol]} | "
                      f"Equity: {equity_before:.2f} -> {equity_after:.2f} | "
                      f"Change: {equity_after - equity_before:+.2f}")

