"""
Stress test: Force positions to be held through price crashes
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import *
import matplotlib
matplotlib.use('Agg')

# Create a strategy that holds through crashes
class HoldThroughCrashStrategy:
    def __init__(self, symbol, buy_at_t, sell_at_t):
        self.symbol = symbol
        self.buy_at_t = buy_at_t
        self.sell_at_t = sell_at_t
        self.state = "FLAT"
        self.bought = False
    
    def handle_market(self, event):
        if event.symbol != self.symbol:
            return []
        
        if event.timestamp == self.buy_at_t and not self.bought:
            self.bought = True
            self.state = "LONG"
            return [SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="BUY",
                price=event.price
            )]
        
        if event.timestamp == self.sell_at_t and self.bought:
            self.state = "FLAT"
            return [SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="SELL",
                price=event.price
            )]
        
        return []

# Run stress test
queue = EventQueue()
dispatcher = Dispatcher()
risk = PassThroughRiskManager(fixed_quantity=10)
execution = ExecutionHandler()
portfolio = PortfolioState(initial_cash=10000)

# Force MSFT to be held through the crash (buy at t=12, sell at t=22)
msft_strategy = HoldThroughCrashStrategy("MSFT", buy_at_t=12, sell_at_t=22)
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

while not queue.is_empty():
    event = queue.get()
    new_events = dispatcher.dispatch(event)
    for e in new_events:
        queue.put(e)

# Rebuild equity curve
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
print("STRESS TEST: Holding MSFT through crash")
print("=" * 80)
print(f"\nMSFT Price Sequence: {PRICE_DATA['MSFT']}")
print(f"Buy at t=12 @ {PRICE_DATA['MSFT'][0]}, Sell at t=22 @ {PRICE_DATA['MSFT'][-1]}")
print(f"\n{'t':<4} {'Symbol':<6} {'Price':<8} {'Equity':<12} {'Cash':<12} {'Positions':<20} {'Change':<12}")
print("-" * 80)

prev_equity = 10000
for i, event in enumerate(market_events):
    if event.symbol == 'MSFT' and event.timestamp >= 12:
        equity = aligned_equity_curve[i]
        change = equity - prev_equity
        pos_str = ", ".join([f"{k}:{v}" for k, v in replay_positions.items()]) if replay_positions else "None"
        
        # Recalculate positions at this point
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
        change_str = f"{change:+.2f}" if abs(change) > 0.01 else "0.00"
        print(f"{event.timestamp:<4} {event.symbol:<6} {event.price:<8.2f} {equity:<12.2f} {replay_cash_check:<12.2f} {pos_str:<20} {change_str:<12}")
        prev_equity = equity

print(f"\nFinal Equity: {aligned_equity_curve[-1]:.2f}")
print(f"Max Drawdown: {min([(eq - max(aligned_equity_curve[:i+1])) / max(aligned_equity_curve[:i+1]) for i, eq in enumerate(aligned_equity_curve)]) * 100:.2f}%")

