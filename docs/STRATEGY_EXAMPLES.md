# Strategy Examples

This document provides examples and usage instructions for all available trading strategies.

---

## RollingMeanReversionStrategy

A mean reversion strategy that buys when price drops below a rolling mean threshold and sells when price returns to the mean.

### How It Works

1. Maintains a rolling window of recent prices
2. Calculates the mean of the window
3. **BUY** when price < (mean - threshold) and currently FLAT
4. **SELL** when price >= mean and currently LONG
5. Repeats indefinitely

### Parameters

- `window` (int): Number of prices to include in rolling mean calculation (default: 5)
- `threshold` (float): Price deviation below mean to trigger buy (default: 2.0)
- `symbol` (str, optional): Symbol to trade (if None, trades all symbols)

### Usage Example

```python
STRATEGY_CONFIG = {
    "APPL": {
        "class": RollingMeanReversionStrategy,
        "params": {
            "window": 5,        # Use last 5 prices for mean
            "threshold": 2.0,   # Buy when price < mean - 2.0
        }
    }
}
```

### Example Behavior

With `window=5` and `threshold=2.0`:
- Prices: [100, 101, 102, 100, 100, 97, ...]
- Mean of first 5: 100.6
- Lower band: 100.6 - 2.0 = 98.6
- When price hits 97 < 98.6 → **BUY**
- When price returns to 100 >= 100 → **SELL**

### Use Cases

- Range-bound markets
- Mean reversion opportunities
- Testing strategy framework

### Notes

- Requires `window` prices before generating first signal
- State machine: FLAT ↔ LONG
- Can generate multiple round trips

---

## OneShotBuyStrategy

A simple test strategy that buys on the first market event and sells on the second, then stops trading.

### How It Works

1. **First MarketEvent**: Emit BUY signal
2. **Second MarketEvent**: Emit SELL signal
3. **All subsequent events**: Ignore (state = DONE)

### Parameters

- `symbol` (str, optional): Symbol to trade (if None, trades all symbols)

### Usage Example

```python
STRATEGY_CONFIG = {
    "MSFT": {
        "class": OneShotBuyStrategy,
        "params": {}
    }
}
```

### Example Behavior

- t=0: MarketEvent for MSFT → **BUY** signal
- t=1: MarketEvent for MSFT → **SELL** signal
- t=2+: MarketEvent for MSFT → No signals (DONE)

### Use Cases

- Testing event pipeline
- Verifying basic strategy framework
- Simple backtesting validation

### Notes

- Only generates one round trip per symbol
- Useful for debugging and testing
- Not intended for production trading

---

## HoldThroughCrashStrategy

A strategy designed to hold positions through price crashes for stress testing equity curve behavior.

### How It Works

1. Buys at a specified `buy_at_timestamp`
2. Holds the position through all market events between buy and sell
3. Sells at a specified `sell_at_timestamp`
4. Ignores all other market events

### Parameters

- `symbol` (str, optional): Symbol to trade (if None, trades all symbols)
- `buy_at_timestamp` (int): Market event timestamp to buy at (default: 0)
- `sell_at_timestamp` (int): Market event timestamp to sell at (default: 100)

### Usage Example

```python
STRATEGY_CONFIG = {
    "MSFT": {
        "class": HoldThroughCrashStrategy,
        "params": {
            "buy_at_timestamp": 12,   # Buy at market event timestamp 12
            "sell_at_timestamp": 22,  # Sell at market event timestamp 22
        }
    }
}
```

### Example Behavior

When holding MSFT through a crash (t=12 to t=22):
- t=12: Buy MSFT @ 200
- t=13: Hold (price = 202, equity = 10,020)
- t=14: Hold through crash (price = 1, equity = 8,010, **-20% drawdown**)
- t=15-21: Hold through volatility
- t=22: Sell MSFT @ 200

### Use Cases

1. **Stress Testing**: See how equity responds to price crashes
2. **Risk Testing**: Test risk limits during drawdowns
3. **Equity Verification**: Verify mark-to-market equity calculations

### Example Output

When holding MSFT through the crash (t=12 to t=22):
- t=14: Equity drops from 10,020 to 8,010 (-2,010) when price crashes to 1
- t=18: Equity drops again to 8,010 (-1,040) when price crashes to 1 again
- Max drawdown: -20.06%

This demonstrates that equity calculation is working correctly - it drops when you hold positions during price crashes!

### Test Script

Run `tests/test_hold_strategy.py` to see a complete example:

```bash
python3 tests/test_hold_strategy.py
```

---

## Strategy Comparison

| Strategy | Complexity | Use Case | Signals Generated |
|----------|-----------|----------|-------------------|
| OneShotBuyStrategy | Simple | Testing | 1 round trip |
| RollingMeanReversionStrategy | Medium | Mean reversion trading | Multiple round trips |
| HoldThroughCrashStrategy | Simple | Stress testing | 1 round trip (configurable) |

---

## Creating Your Own Strategy

All strategies inherit from `Strategy` base class:

```python
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent

class MyStrategy(Strategy):
    def __init__(self, symbol=None, **params):
        super().__init__(symbol)
        # Initialize your strategy state
    
    def handle_market(self, event: MarketEvent) -> List[SignalEvent]:
        # Your strategy logic here
        # Return list of SignalEvent objects (or empty list)
        if should_buy:
            return [SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="BUY",
                price=event.price
            )]
        return []
```

### Key Points

- `handle_market()` receives every MarketEvent
- Return empty list `[]` if no signal
- Return list of `SignalEvent` objects if you want to trade
- Strategy state persists between calls
- Filter by `symbol` if strategy is symbol-specific

---

## Configuration Tips

### Multiple Strategies

You can run multiple strategies simultaneously:

```python
STRATEGY_CONFIG = {
    "APPL": {
        "class": RollingMeanReversionStrategy,
        "params": {"window": 5, "threshold": 2.0}
    },
    "MSFT": {
        "class": HoldThroughCrashStrategy,
        "params": {"buy_at_timestamp": 12, "sell_at_timestamp": 22}
    }
}
```

### Same Strategy, Different Symbols

```python
STRATEGY_CONFIG = {
    "APPL": {
        "class": RollingMeanReversionStrategy,
        "params": {"window": 5, "threshold": 2.0}
    },
    "MSFT": {
        "class": RollingMeanReversionStrategy,
        "params": {"window": 10, "threshold": 3.0}
    }
}
```

### Testing Strategy

Use `OneShotBuyStrategy` for quick validation:

```python
STRATEGY_CONFIG = {
    "TEST": {
        "class": OneShotBuyStrategy,
        "params": {}
    }
}
```
