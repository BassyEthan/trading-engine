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

- ✅ **Event-driven architecture** with timestamp-ordered processing
- ✅ **Pluggable strategies** (mean reversion, momentum, custom)
- ✅ **Mark-to-market equity tracking** (updates on every market event)
- ✅ **Portfolio state management** (single source of truth)
- ✅ **Real risk management** (drawdown limits, position size, exposure)
- ✅ **Realistic execution** (slippage, bid-ask spread, market impact)
- ✅ **Real market data** (CSV files, Yahoo Finance API)
- ✅ **Performance analytics** (equity curve, drawdown, Sharpe ratio)
- ✅ **Web dashboard** (Streamlit UI for visualization)
- ✅ **Multi-symbol support** (trade multiple assets simultaneously)

## Quick Start

### Basic Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation with real data (Yahoo Finance)
python3 main.py

# Or use CSV files (see data/QUICKSTART.md)
# Place CSV files in data/ directory, then run:
python3 main.py

# Run web dashboard
streamlit run ui_dashboard.py
```

### Data Configuration

Edit `main.py` to configure data source:

```python
# Use fake data for testing
USE_FAKE_DATA = True

# Or use real data
USE_FAKE_DATA = False
CSV_DATA_DIR = "data/"  # CSV files
# OR
YAHOO_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
YAHOO_START_DATE = "2024-01-01"
YAHOO_END_DATE = "2024-12-31"
```

### Testing

```bash
# Run individual tests
python3 tests/test_equity.py
python3 tests/test_risk_rejection.py
python3 tests/test_hold_strategy.py
```

## Project Structure

```
trading-engine/
├── main.py                 # Entry point and configuration
├── ui_dashboard.py         # Streamlit web dashboard
├── core/                   # Core infrastructure
│   ├── event_queue.py     # Priority queue (timestamp-ordered)
│   ├── dispatcher.py      # Event routing (multi-handler support)
│   └── logger.py          # Logging utilities
├── events/                 # Event definitions
│   └── base.py            # MarketEvent, SignalEvent, OrderEvent, FillEvent
├── strategies/             # Trading strategies
│   ├── base.py            # Strategy base class
│   ├── mean_reversion.py  # Rolling mean reversion strategy
│   ├── one_shot.py        # Simple buy-and-hold strategy
│   ├── hold_through_crash.py  # Stress test strategy
│   └── multi_signal.py    # Multi-signal test strategy
├── risk/                   # Risk management
│   └── engine.py          # RealRiskManager (enforces limits)
├── execution/              # Order execution
│   └── simulator.py       # RealisticExecutionHandler (slippage, spread)
├── portfolio/              # Portfolio state
│   └── state.py           # Single source of truth for portfolio
├── data/                   # Market data loading
│   ├── loader.py          # CSV, Yahoo Finance data loader
│   └── example_data.py    # Sample data formats
├── analysis/               # Performance analysis
│   ├── equity_analyzer.py # Equity curve analysis
│   ├── equity_plotter.py  # Visualization
│   └── metrics.py          # Performance metrics (realized/unrealized PnL)
├── tests/                  # Test suite
│   ├── test_equity.py     # Equity calculation verification
│   ├── test_hold_strategy.py  # Strategy demonstration
│   ├── test_risk_manager.py   # Risk manager tests
│   ├── test_risk_rejection.py # Risk rejection verification
│   ├── stress_test.py     # Stress testing
│   └── debug_equity.py    # Debugging tools
└── docs/                   # Documentation
    ├── DESIGN.md          # System design and goals
    ├── ROADMAP.md         # Long-term roadmap
    ├── STRATEGY_EXAMPLES.md  # Strategy usage examples
    ├── RISK_MANAGER_GUIDE.md # Risk manager documentation
    ├── DRAWDOWN_EXPLANATION.md # Drawdown behavior explained
    ├── EVENT_ORDERING.md  # Timestamp-ordered processing
    └── EXECUTION_REALISM.md # Execution costs explained
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

## Current Status

### ✅ Implemented
- **Real Risk Manager** - Enforces drawdown, position size, and exposure limits
- **Realistic Execution** - Slippage, bid-ask spread, market impact
- **Real Market Data** - CSV files and Yahoo Finance API support
- **Timestamp-Ordered Processing** - Deterministic event processing
- **Mark-to-Market Equity** - Real-time portfolio valuation
- **Multi-Symbol Support** - Trade multiple assets simultaneously
- **Web Dashboard** - Streamlit UI for visualization
- **Comprehensive Metrics** - Realized/unrealized PnL, drawdown, Sharpe ratio

### 🚧 Future Enhancements
- Order types (limit, stop-loss, take-profit)
- Latency simulation
- Partial fills
- Multi-timeframe data
- Live trading interface

See `docs/ROADMAP.md` for detailed roadmap.

## Documentation

- `docs/DESIGN.md` - System design and philosophy
- `docs/ROADMAP.md` - Long-term development roadmap
- `docs/STRATEGY_EXAMPLES.md` - Strategy usage examples
- `docs/RISK_MANAGER_GUIDE.md` - Risk manager configuration and usage
- `docs/DRAWDOWN_EXPLANATION.md` - Understanding drawdown behavior
- `docs/EVENT_ORDERING.md` - Timestamp-ordered event processing
- `docs/EXECUTION_REALISM.md` - Execution costs and slippage
- `data/README.md` - Market data loading guide
- `UI_README.md` - Web dashboard usage

## Testing

Run verification tests:
```bash
python3 tests/test_equity.py      # Verify equity calculations
python3 tests/test_hold_strategy.py  # See equity drops during crashes
python3 tests/stress_test.py     # Stress test scenarios
```

## License

Educational project - use at your own risk.

