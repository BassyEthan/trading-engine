# Complete Event Flow Walkthrough

## Overview

This document traces the complete event flow from entry point to final metrics, including all files, methods, data structures, and important details.

---

## 1. ENTRY POINT

### File: `scripts/test_ml_strategy.py` or `main.py`

**Function:** `compare_strategies()` or `main()`

**What happens:**
1. Load test data from JSON file
2. Initialize all components
3. Register event handlers
4. Seed initial events
5. Run event loop
6. Calculate metrics

---

## 2. DATA LOADING

### File: `scripts/test_ml_strategy.py` (line 28-35)

**Function:** `load_test_data()`

```python
def load_test_data():
    test_path = Path("data/ml_training/test_data.json")
    with open(test_path, 'r') as f:
        return json.load(f)  # Returns: {"AAPL": [prices...], "MSFT": [prices...]}
```

**Data Structure:**
- **Input:** JSON file with `{"SYMBOL": [price1, price2, ...]}`
- **Output:** Dictionary mapping symbol to list of prices (chronologically ordered)

**OR**

### File: `main.py` (line 97-148)

**Function:** `load_price_data()`

**Sources (in order):**
1. Fake data (if `USE_FAKE_DATA = True`)
2. CSV directory (`data/` folder)
3. Yahoo Finance API

**File:** `data/loader.py`
- `load_market_data()` - convenience function
- `DataLoader.load_from_csv()` - CSV parsing
- `DataLoader.load_from_yahoo_finance()` - API calls

**Data Structure:**
- Same format: `{"SYMBOL": [prices...]}`

---

## 3. COMPONENT INITIALIZATION

### File: `scripts/test_ml_strategy.py` (line 45-93)

**Order of initialization:**

#### 3.1 Core Infrastructure

```python
queue = PriorityEventQueue()      # core/event_queue.py
dispatcher = Dispatcher()          # core/dispatcher.py
portfolio = PortfolioState(initial_cash=10000.0)  # portfolio/state.py
```

**PriorityEventQueue** (`core/event_queue.py`):
- Uses `heapq` for priority queue
- Sorts by: `(timestamp, event_type_priority, counter)`
- Event priorities:
  - `MarketEvent: 0` (highest - processed first)
  - `SignalEvent: 1`
  - `OrderEvent: 2`
  - `FillEvent: 3` (lowest - processed last)

**Dispatcher** (`core/dispatcher.py`):
- Maintains `_handlers: Dict[EventType, List[Handler]]`
- Routes events to registered handlers
- Returns list of new events from handlers

**PortfolioState** (`portfolio/state.py`):
- Tracks: `cash`, `positions`, `realized_pnl`, `trades`, `latest_prices`
- Updates equity curve and mark-to-market values

#### 3.2 Risk Manager

```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.15,
    max_position_pct=0.30,
    max_total_exposure_pct=1.0,
    max_positions=None,
)
```

**File:** `risk/engine.py`
- `RealRiskManager.handle_signal()` - checks risk limits before allowing trades

#### 3.3 Execution Handler

```python
execution = RealisticExecutionHandler(
    spread_pct=0.001,
    base_slippage_pct=0.0005,
    impact_factor=0.000001,
    slippage_volatility=0.0002,
)
```

**File:** `execution/simulator.py`
- `RealisticExecutionHandler.handle_order()` - simulates execution with costs

#### 3.4 Strategies

```python
strategies = {}
for symbol in data.keys():
    strategies[symbol] = MLStrategy(
        model_path="ml/models/price_direction_model.pkl",
        symbol=symbol,
        buy_threshold=0.55,
        sell_threshold=0.45,
    )
```

**File:** `strategies/ml_strategy.py`
- `MLStrategy.__init__()` - loads model, initializes feature extractor
- `MLStrategy.handle_market()` - generates signals from market events

---

## 4. HANDLER REGISTRATION

### File: `scripts/test_ml_strategy.py` (line 83-93)

**Order matters!** Portfolio must be registered FIRST.

```python
# 1. Portfolio FIRST (updates prices before strategies)
dispatcher.register_handler(MarketEvent, portfolio.handle_market)

# 2. Strategies (generate signals from updated prices)
for strategy in strategies.values():
    dispatcher.register_handler(MarketEvent, strategy.handle_market)

# 3. Risk Manager (validates signals)
dispatcher.register_handler(SignalEvent, risk.handle_signal)

# 4. Execution Handler (executes orders)
dispatcher.register_handler(OrderEvent, execution.handle_order)

# 5. Portfolio (records fills)
dispatcher.register_handler(FillEvent, portfolio.handle_fill)
```

**Why order matters:**
- Portfolio updates `latest_prices` from MarketEvent
- Strategies need current prices to generate signals
- Risk manager needs current equity (from latest prices) to check drawdown

**Data Structure in Dispatcher:**
```python
_handlers = {
    MarketEvent: [portfolio.handle_market, strategy1.handle_market, ...],
    SignalEvent: [risk.handle_signal],
    OrderEvent: [execution.handle_order],
    FillEvent: [portfolio.handle_fill],
}
```

---

## 5. EVENT SEEDING

### File: `scripts/test_ml_strategy.py` (line 95-101)

```python
timestamp = 0
for symbol, prices in data.items():
    for price in prices:
        event = MarketEvent(timestamp=timestamp, symbol=symbol, price=price)
        queue.put(event)  # Adds to priority queue
        timestamp += 1
```

**What happens:**
- Creates `MarketEvent` for each price
- Assigns sequential timestamps (0, 1, 2, ...)
- Adds to `PriorityEventQueue` (sorted by timestamp)

**Event Structure:**
```python
MarketEvent(
    timestamp=0,
    symbol="AAPL",
    price=178.27
)
```

**Queue State:**
- Heap contains: `[(0, 0, 0, MarketEvent(...)), (1, 0, 1, MarketEvent(...)), ...]`
- Sorted by: `(timestamp, priority, counter)`

---

## 6. EVENT LOOP

### File: `scripts/test_ml_strategy.py` (line 103-113)

```python
while not queue.is_empty():
    event = queue.get()  # Gets next event in timestamp order
    new_events = dispatcher.dispatch(event)  # Process event
    for new_event in new_events:
        queue.put(new_event)  # Add generated events back to queue
```

**Flow for each iteration:**

1. **Get next event** from queue (earliest timestamp, highest priority)
2. **Dispatch** to all registered handlers for that event type
3. **Collect** new events returned by handlers
4. **Add** new events back to queue (will be processed in order)

---

## 7. EVENT PROCESSING PIPELINE

### 7.1 MarketEvent Processing

**File:** `core/dispatcher.py` (line 32-47)

```python
def dispatch(self, event):
    handlers = self._handlers.get(type(event), [])
    new_events = []
    for handler in handlers:
        result = handler(event)  # Call handler
        if result:
            new_events.extend(result)  # Collect new events
    return new_events
```

**Handlers called (in registration order):**

#### Handler 1: Portfolio (`portfolio/state.py`)

**Method:** `PortfolioState.handle_market(event: MarketEvent)`

**What it does:**
```python
def handle_market(self, event: MarketEvent):
    # Update latest price for mark-to-market
    self.latest_prices[event.symbol] = event.price
    
    # Calculate current equity
    equity = self.cash
    for sym, pos in self.positions.items():
        if sym in self.latest_prices:
            equity += pos.quantity * self.latest_prices[sym]
    
    # Store equity by timestamp
    self.equity_by_timestamp[event.timestamp] = equity
    self.equity_curve.append(equity)
    
    return []  # No new events generated
```

**Data updates:**
- `latest_prices[event.symbol] = event.price`
- `equity_by_timestamp[timestamp] = equity`
- `equity_curve.append(equity)`

#### Handler 2: Strategy (`strategies/ml_strategy.py`)

**Method:** `MLStrategy.handle_market(event: MarketEvent)`

**What it does:**
```python
def handle_market(self, event: MarketEvent):
    # Update price history
    self.prices.append(event.price)
    
    # Extract features
    features = self.feature_extractor.extract_features(list(self.prices))
    
    # Predict probability
    prob_up = self.model.predict_proba([features])[0][1]
    
    # Generate signal
    if prob_up > self.buy_threshold and self.state == "FLAT":
        self.state = "LONG"
        return [SignalEvent(timestamp=..., symbol=..., direction="BUY", price=...)]
    
    elif prob_up < self.buy_threshold and self.state == "LONG":
        self.state = "FLAT"
        return [SignalEvent(timestamp=..., symbol=..., direction="SELL", price=...)]
    
    return []  # No signal
```

**Returns:** `List[SignalEvent]` or `[]`

**SignalEvent Structure:**
```python
SignalEvent(
    timestamp=5,
    symbol="AAPL",
    direction="BUY",
    price=178.27
)
```

---

### 7.2 SignalEvent Processing

**Handler:** Risk Manager (`risk/engine.py`)

**Method:** `RealRiskManager.handle_signal(event: SignalEvent)`

**What it does:**
```python
def handle_signal(self, event: SignalEvent):
    # Check all risk limits
    checks = [
        self._check_drawdown_limit(event),
        self._check_position_size_limit(event),
        self._check_cash_availability(event),
        self._check_position_count_limit(event),
    ]
    
    # If any check fails, reject
    for passed, reason in checks:
        if not passed:
            self.rejections.append((event, reason))
            return []  # Rejected - no order
    
    # All checks passed - create order
    quantity = self.fixed_quantity
    return [OrderEvent(timestamp=..., symbol=..., direction=..., quantity=...)]
```

**Risk Checks:**
1. **Drawdown:** `current_drawdown <= max_drawdown`
2. **Position Size:** `position_value <= max_position_pct * equity`
3. **Cash:** `order_cost <= available_cash`
4. **Position Count:** `num_positions <= max_positions`

**Returns:** `List[OrderEvent]` or `[]` (if rejected)

**OrderEvent Structure:**
```python
OrderEvent(
    timestamp=5,
    symbol="AAPL",
    direction="BUY",
    quantity=10
)
```

---

### 7.3 OrderEvent Processing

**Handler:** Execution Handler (`execution/simulator.py`)

**Method:** `RealisticExecutionHandler.handle_order(event: OrderEvent)`

**What it does:**
```python
def handle_order(self, event: OrderEvent):
    # Get current market price
    market_price = event.price  # From signal
    
    # Calculate execution costs
    spread_cost = market_price * self.spread_pct / 2
    slippage = market_price * (self.base_slippage_pct + random_variation)
    market_impact = event.quantity * self.impact_factor
    
    # Calculate fill price
    if event.direction == "BUY":
        fill_price = market_price + spread_cost + slippage + market_impact
    else:  # SELL
        fill_price = market_price - spread_cost - slippage - market_impact
    
    # Create fill event
    return [FillEvent(
        timestamp=event.timestamp,
        symbol=event.symbol,
        direction=event.direction,
        quantity=event.quantity,
        fill_price=fill_price
    )]
```

**Returns:** `List[FillEvent]`

**FillEvent Structure:**
```python
FillEvent(
    timestamp=5,
    symbol="AAPL",
    direction="BUY",
    quantity=10,
    fill_price=178.35  # Includes execution costs
)
```

---

### 7.4 FillEvent Processing

**Handler:** Portfolio (`portfolio/state.py`)

**Method:** `PortfolioState.handle_fill(event: FillEvent)`

**What it does:**
```python
def handle_fill(self, event: FillEvent):
    # Update latest price
    self.latest_prices[event.symbol] = event.fill_price
    
    # Calculate cash change
    signed_qty = event.quantity if event.direction == "BUY" else -event.quantity
    cash_change = -signed_qty * event.fill_price
    
    # Check cash invariant
    if self.cash + cash_change < 0:
        raise ValueError("Insufficient cash")
    
    # Update position
    if event.symbol not in self.positions:
        self.positions[event.symbol] = Position(quantity=0, avg_cost=0.0)
    
    position = self.positions[event.symbol]
    
    # Realize PnL if closing/reducing position
    if position.quantity != 0 and (position.quantity * signed_qty < 0):
        closing_qty = min(abs(position.quantity), abs(signed_qty))
        pnl_per_share = event.fill_price - position.avg_cost
        self.realized_pnl += closing_qty * pnl_per_share * sign
    
    # Update position
    new_qty = position.quantity + signed_qty
    if new_qty == 0:
        del self.positions[event.symbol]
    else:
        # Update average cost
        new_avg_cost = calculate_new_avg_cost(...)
        self.positions[event.symbol] = Position(quantity=new_qty, avg_cost=new_avg_cost)
    
    # Update cash
    self.cash += cash_change
    
    # Record trade
    self.trades.append(event)
    
    # Update equity
    equity = self.cash
    for sym, pos in self.positions.items():
        if sym in self.latest_prices:
            equity += pos.quantity * self.latest_prices[sym]
    self.equity_by_timestamp[event.timestamp] = equity
    
    return []  # No new events
```

**Data updates:**
- `cash` - updated with trade cost
- `positions[symbol]` - updated or deleted
- `realized_pnl` - updated if closing position
- `trades.append(fill)` - recorded
- `equity_by_timestamp[timestamp] = equity` - updated

---

## 8. EVENT ORDERING GUARANTEES

### File: `core/event_queue.py`

**PriorityEventQueue ensures:**

1. **Timestamp ordering:** All events at timestamp T processed before T+1
2. **Type ordering within timestamp:**
   - MarketEvent (priority 0) - updates prices
   - SignalEvent (priority 1) - generates signals
   - OrderEvent (priority 2) - creates orders
   - FillEvent (priority 3) - completes trades

**Example:**
```
Timestamp 5:
  - MarketEvent (AAPL, $178.27) → Portfolio updates price
  - MarketEvent (AAPL, $178.27) → Strategy generates SignalEvent
  - SignalEvent (BUY) → Risk creates OrderEvent
  - OrderEvent (BUY, 10) → Execution creates FillEvent
  - FillEvent (BUY, 10, $178.35) → Portfolio records trade

Timestamp 6:
  - MarketEvent (AAPL, $179.50) → ...
```

**Why this matters:**
- Portfolio sees latest prices before strategies
- Risk manager sees updated equity before checking limits
- All events at same timestamp complete before moving to next

---

## 9. METRICS CALCULATION

### File: `scripts/test_ml_strategy.py` (line 118-191)

**After event loop completes:**

```python
# Calculate final equity
final_equity = portfolio.cash
for symbol, position in portfolio.positions.items():
    if symbol in portfolio.latest_prices:
        final_equity += position.quantity * portfolio.latest_prices[symbol]

# Create metrics
metrics = TradeMetrics(
    fills=portfolio.trades,  # List[FillEvent]
    initial_cash=10000.0,
    final_cash=portfolio.cash,
    final_equity=final_equity,
)
```

**File:** `analysis/metrics.py`

**TradeMetrics calculates:**
- `total_pnl()` - `final_equity - initial_cash`
- `num_trades()` - number of round trips (BUY-SELL pairs)
- `win_rate()` - percentage of profitable trades
- `avg_pnl_per_trade()` - average PnL per round trip

**How it works:**
```python
def _compute_trade_pnls(self):
    trade_pnls = []
    entry_price = None
    quantity = None
    
    for fill in self.fills:
        if fill.direction == "BUY":
            entry_price = fill.fill_price
            quantity = fill.quantity
        elif fill.direction == "SELL":
            pnl = (fill.fill_price - entry_price) * quantity
            trade_pnls.append(pnl)
            entry_price = None
            quantity = None
    
    return trade_pnls
```

**Equity curve analysis:**
```python
equity_curve = [portfolio.equity_by_timestamp[t] for t in sorted(portfolio.equity_by_timestamp.keys())]

# Sharpe ratio
returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] for i in range(1, len(equity_curve))]
sharpe = (mean(returns) / std(returns)) * sqrt(252)

# Max drawdown
peak = equity_curve[0]
max_dd = 0.0
for equity in equity_curve:
    peak = max(peak, equity)
    dd = (peak - equity) / peak
    max_dd = max(max_dd, dd)
```

---

## 10. COMPLETE FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ENTRY POINT                                               │
│    scripts/test_ml_strategy.py:compare_strategies()          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. DATA LOADING                                              │
│    load_test_data() → {"AAPL": [prices...]}                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. INITIALIZATION                                            │
│    - PriorityEventQueue()                                    │
│    - Dispatcher()                                            │
│    - PortfolioState(initial_cash=10000)                     │
│    - RealRiskManager(...)                                    │
│    - RealisticExecutionHandler(...)                          │
│    - MLStrategy(...) for each symbol                         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. HANDLER REGISTRATION                                      │
│    dispatcher.register_handler(MarketEvent, portfolio)      │
│    dispatcher.register_handler(MarketEvent, strategy)        │
│    dispatcher.register_handler(SignalEvent, risk)            │
│    dispatcher.register_handler(OrderEvent, execution)         │
│    dispatcher.register_handler(FillEvent, portfolio)         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. EVENT SEEDING                                             │
│    for symbol, prices in data.items():                       │
│        for price in prices:                                  │
│            queue.put(MarketEvent(timestamp, symbol, price))  │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. EVENT LOOP                                                │
│    while not queue.is_empty():                               │
│        event = queue.get()  # Earliest timestamp             │
│        new_events = dispatcher.dispatch(event)               │
│        for new_event in new_events:                          │
│            queue.put(new_event)                              │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. EVENT PROCESSING                                          │
│                                                              │
│    MarketEvent → Portfolio.handle_market()                  │
│                 → Updates latest_prices, equity              │
│                                                              │
│    MarketEvent → Strategy.handle_market()                    │
│                 → Generates SignalEvent (if conditions met)   │
│                                                              │
│    SignalEvent → Risk.handle_signal()                        │
│                 → Checks limits, creates OrderEvent          │
│                                                              │
│    OrderEvent → Execution.handle_order()                      │
│                → Calculates fill_price, creates FillEvent   │
│                                                              │
│    FillEvent → Portfolio.handle_fill()                       │
│               → Updates cash, positions, realized_pnl       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. METRICS CALCULATION                                       │
│    TradeMetrics(fills=portfolio.trades, ...)                 │
│    - total_pnl, win_rate, avg_pnl_per_trade                 │
│    - Sharpe ratio, max drawdown                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. KEY DATA STRUCTURES

### Events

```python
MarketEvent(timestamp, symbol, price)
SignalEvent(timestamp, symbol, direction, price)
OrderEvent(timestamp, symbol, direction, quantity)
FillEvent(timestamp, symbol, direction, quantity, fill_price)
```

### Portfolio State

```python
PortfolioState:
    cash: float
    positions: Dict[str, Position]  # {"AAPL": Position(quantity=10, avg_cost=178.35)}
    realized_pnl: float
    trades: List[FillEvent]
    latest_prices: Dict[str, float]  # {"AAPL": 179.50}
    equity_by_timestamp: Dict[int, float]  # {5: 10000, 6: 10050, ...}
    equity_curve: List[float]  # [10000, 10050, ...]
```

### Position

```python
Position(quantity: int, avg_cost: float)
```

---

## 12. IMPORTANT INVARIANTS

1. **Cash never goes negative** - checked in `PortfolioState.handle_fill()`
2. **Positions only change on FillEvents** - enforced by architecture
3. **Events processed in timestamp order** - guaranteed by `PriorityEventQueue`
4. **Portfolio updates prices before strategies** - registration order matters
5. **All events at timestamp T complete before T+1** - priority queue ensures this

---

## 13. EXECUTION COSTS

**Applied in:** `execution/simulator.py:RealisticExecutionHandler.handle_order()`

**Costs:**
- **Spread:** `price * spread_pct / 2` (half spread on each side)
- **Slippage:** `price * (base_slippage_pct + random_variation)`
- **Market Impact:** `quantity * impact_factor`

**Example:**
```
Market price: $100.00
Spread (0.1%): $0.05
Slippage (0.05%): $0.05
Impact (10 shares × 0.0001%): $0.001

BUY fill_price: $100.00 + $0.05 + $0.05 + $0.001 = $100.101
```

---

## 14. RISK CHECKS

**Applied in:** `risk/engine.py:RealRiskManager.handle_signal()`

**Checks (all must pass):**
1. **Drawdown:** Current drawdown ≤ max_drawdown (15%)
2. **Position Size:** Position value ≤ max_position_pct × equity (30%)
3. **Cash:** Order cost ≤ available cash
4. **Position Count:** Number of positions ≤ max_positions

**If any check fails:**
- Signal rejected
- Rejection logged in `risk.rejections`
- No OrderEvent created

---

## Summary

The system processes events in strict chronological order, with type-based priorities ensuring:
1. Prices update first (MarketEvent)
2. Signals generate from updated prices (SignalEvent)
3. Risk validates signals (OrderEvent)
4. Execution simulates fills (FillEvent)
5. Portfolio records trades and updates state

This guarantees deterministic, realistic trading simulation with proper state management.

