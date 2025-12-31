SYSTEM GOAL:

The system is a model-agnostic, event-driven trading engine that simulates how actual trading systems work. It processes market data as time-ordered events and generates trading signals via pluggable strategies. Before a trade executes, the system enforces risk limits (drawdown, position size, exposure). The system simulates realistic execution with slippage, bid-ask spread, and market impact. Portfolio state is the single source of truth, tracking cash, positions, realized PnL, and unrealized PnL. All trades are logged with full audit trail including why signals were generated, why trades were allowed or blocked, and what risk rules triggered.

The focus of this model isn't to predict prices, find alpha, or beat the market, because models are very fragile, markets are non-stationary, and past performance lies. Rather, we focus on handling uncertainty, robust behavior when assumptions break, and realistic execution simulation.

This project demonstrates how a mediocre strategy with excellent execution can survive, while a great strategy with poor execution will fail.

**Key Learnings:**
- Systems thinking
- Event-driven architecture
- State management under uncertainty
- Real-world trading realism
- Engineering discipline over hype


Important definitions:
    Cash - amount of money you have currently not invested
    Positions - what you current own or owe in each instrument ("APPL": 10, "TSLA": -5)
    PnL - Profit n Loss
    Realized PnL - Profit or loss that is locked in because a position was closed. 
    Unrealized PnL - Profit or loss on open positions, based on current market prices
    Exposure - How much market risk you are actually taking; how sensitive are you to price movements?
    Alpha - returns that cannot be explained by market exposure or risk alone. If the market is flat, but I keep making money - that is strong alpha

    Only realized PnL affects cash permanantly 

FIXED CONSTRAINTS:

Language: Python
Market: historical replay (no live feeds yet)
Execution: paper trading only
Strategy: trivial (e.g. momentum threshold)

## Core Components

### Event Infrastructure
- **PriorityEventQueue** - Timestamp-ordered event processing (ensures deterministic execution)
- **Dispatcher** - Routes events to multiple handlers (supports multiple handlers per event type)

### Trading Components
- **Strategies** - Pluggable signal generators (mean reversion, momentum, custom)
- **Risk Engine** - `RealRiskManager` enforces limits (drawdown, position size, exposure)
- **Execution Handler** - `RealisticExecutionHandler` simulates slippage, spread, market impact
- **Portfolio State** - Single source of truth for cash, positions, PnL

### Data & Analysis
- **Data Loader** - CSV files and Yahoo Finance API support
- **Equity Analyzer** - Performance metrics (drawdown, Sharpe ratio)
- **Trade Metrics** - Realized/unrealized PnL, win rate, trade statistics
- **Web Dashboard** - Streamlit UI for visualization

Invariants 
Examples:
Cash can never go negative
Positions only change on fills
Risk engine is the final gate before execution
Portfolio state is the single source of truth