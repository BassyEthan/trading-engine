# Trading Engine

An event-driven trading engine focused on robust execution and risk management rather than strategy optimization.

> "A mediocre strategy with excellent execution can survive. A great strategy with poor execution will fail."

## Philosophy

This project emphasizes:
- **Systems thinking** - Understanding how components interact
- **Robust behavior** - Handling uncertainty and edge cases
- **Execution quality** - Realistic simulation of trading mechanics
- **Engineering discipline** - Clean architecture over hype

## Features

- ✅ Event-driven architecture
- ✅ Pluggable strategies
- ✅ Mark-to-market equity tracking
- ✅ Portfolio state management
- ✅ Risk management framework (currently PassThrough)
- ✅ Execution simulation
- ✅ Performance analytics

## Quick Start

```bash
# Run the main simulation
python3 main.py

# Run tests
python3 -m pytest tests/  # If using pytest
# Or run individual tests:
python3 tests/test_equity.py
python3 tests/test_hold_strategy.py
```

## Project Structure

```
trading-engine/
├── main.py                 # Entry point
├── core/                   # Core infrastructure
│   ├── event_queue.py     # FIFO event queue
│   ├── dispatcher.py       # Event routing
│   └── logger.py          # Logging utilities
├── events/                 # Event definitions
│   └── base.py            # MarketEvent, SignalEvent, OrderEvent, FillEvent
├── strategies/             # Trading strategies
│   ├── base.py            # Strategy base class
│   ├── mean_reversion.py  # Mean reversion strategy
│   ├── one_shot.py        # Simple test strategy
│   └── hold_through_crash.py  # Stress test strategy
├── risk/                   # Risk management
│   └── engine.py          # Risk manager (currently PassThrough)
├── execution/              # Order execution
│   └── simulator.py       # Execution handler
├── portfolio/              # Portfolio state
│   └── state.py           # Single source of truth for portfolio
├── analysis/               # Performance analysis
│   ├── equity_analyzer.py # Equity curve analysis
│   ├── equity_plotter.py  # Visualization
│   └── metrics.py         # Performance metrics
├── tests/                  # Test suite
│   ├── test_equity.py     # Equity calculation verification
│   ├── test_hold_strategy.py  # Strategy demonstration
│   ├── stress_test.py     # Stress testing
│   └── debug_equity.py    # Debugging tools
└── docs/                   # Documentation
    ├── DESIGN.md          # System design and goals
    ├── ROADMAP.md         # Long-term roadmap
    └── STRATEGY_EXAMPLES.md  # Strategy usage examples
```

## Configuration

Edit `STRATEGY_CONFIG` in `main.py` to configure strategies:

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

## Key Concepts

### Events
- **MarketEvent**: New price data
- **SignalEvent**: Trading intent from strategy
- **OrderEvent**: Approved order (after risk check)
- **FillEvent**: Executed trade (only event that changes portfolio)

### Portfolio State
- Single source of truth for cash, positions, and equity
- Mark-to-market equity updates on every MarketEvent
- Invariants: Cash never negative, positions only change on fills

### Event Flow
```
MarketEvent → Strategy → SignalEvent → Risk → OrderEvent → Execution → FillEvent → Portfolio
```

## Current Limitations

- Risk manager is PassThrough (accepts all trades)
- Execution has no latency or slippage
- Historical data only (hardcoded)
- Simple strategies for testing

See `docs/ROADMAP.md` for planned improvements.

## Documentation

- `docs/DESIGN.md` - System design and philosophy
- `docs/ROADMAP.md` - Long-term development roadmap
- `docs/STRATEGY_EXAMPLES.md` - Strategy usage examples

## Testing

Run verification tests:
```bash
python3 tests/test_equity.py      # Verify equity calculations
python3 tests/test_hold_strategy.py  # See equity drops during crashes
python3 tests/stress_test.py     # Stress test scenarios
```

## License

Educational project - use at your own risk.

