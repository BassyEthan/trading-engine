from datetime import datetime
from pathlib import Path

from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher

from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.one_shot import OneShotBuyStrategy
from strategies.mean_reversion import RollingMeanReversionStrategy
from strategies.hold_through_crash import HoldThroughCrashStrategy
from strategies.multi_signal import MultiSignalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.macd import MACDStrategy

from risk.engine import PassThroughRiskManager, RealRiskManager
from execution.simulator import ExecutionHandler, RealisticExecutionHandler
from portfolio.state import PortfolioState

from analysis.metrics import TradeMetrics
from analysis.equity_analyzer import EquityAnalyzer
from analysis.equity_plotter import plot_equity


# Entry point of trading engine.
# Responsibility is to wire together system components
# event queue, dispatcher, handlers start the event loop

# Doesn't contain trading logic, strategic logic, risk rules, or portfolio updates

# Purely exists to instatiate core objects, register handlers with the dispatcher, seed the system with initial events, and run the event-processing loop

# ----------------------
# STRATEGY CONFIGURATION
# ----------------------

STRATEGY_CONFIG = {
    "APPL": {
        "class": MACDStrategy,
        "params": {
  
        }
    },
    "MSFT": {
        "class": MACDStrategy,
        "params": {
            
        }
    },
    "GOOGL": {
        "class": MACDStrategy,
        "params": {
           
        }
    },
    "TSLA": {
        "class": MACDStrategy,
        "params": {}
    },
    "NVDA": {
        "class": MACDStrategy,
        "params": {
         
        }
    }
}

# ----------------------
# MARKET DATA CONFIGURATION
# ----------------------

# Option 1: Load from CSV files
CSV_DATA_DIR = "data/"  # Directory containing CSV files
CSV_PATTERN = "*.csv"   # File pattern

# Option 2: Load from Yahoo Finance
YAHOO_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
YAHOO_START_DATE = "2024-01-01"
YAHOO_END_DATE = "2024-12-31"

# Load market data from Yahoo Finance only
def load_price_data():
    """Load market data from Yahoo Finance. Returns (prices_dict, dates_dict)."""
    from data.loader import load_market_data
    
    errors = []
    
    # Try CSV directory first (if exists)
    if Path(CSV_DATA_DIR).exists():
        try:
            csv_data = load_market_data(
                "csv_dir",
                directory=CSV_DATA_DIR,
                pattern=CSV_PATTERN,
            )
            if csv_data:
                print(f"✓ Loaded {len(csv_data)} symbols from CSV: {list(csv_data.keys())}")
                # CSV doesn't have dates, return None for dates
                return csv_data, None
            else:
                errors.append(f"CSV directory '{CSV_DATA_DIR}' exists but contains no valid data files")
        except Exception as e:
            errors.append(f"CSV loading failed: {e}")
    else:
        errors.append(f"CSV directory '{CSV_DATA_DIR}' does not exist")
    
    # Try Yahoo Finance
    try:
        result = load_market_data(
            "yahoo",
            symbols=YAHOO_SYMBOLS,
            start_date=YAHOO_START_DATE,
            end_date=YAHOO_END_DATE,
            return_dates=True,
        )
        if isinstance(result, tuple):
            yahoo_data, dates_data = result
        else:
            yahoo_data = result
            dates_data = None
            
        if yahoo_data:
            print(f"✓ Loaded {len(yahoo_data)} symbols from Yahoo Finance: {list(yahoo_data.keys())}")
            if dates_data:
                print(f"  Data points per symbol:")
                for sym in yahoo_data.keys():
                    print(f"    {sym}: {len(yahoo_data[sym])} points")
            return yahoo_data, dates_data
        else:
            errors.append("Yahoo Finance returned no data")
    except Exception as e:
        errors.append(f"Yahoo Finance loading failed: {e}")
    
    # No data found - raise error
    error_msg = "Failed to load market data:\n"
    if errors:
        error_msg += "\n".join(f"  - {err}" for err in errors)
    error_msg += f"\n\nCSV directory checked: {CSV_DATA_DIR} (exists: {Path(CSV_DATA_DIR).exists()})"
    error_msg += f"\nYahoo Finance symbols: {YAHOO_SYMBOLS}"
    error_msg += "\n\nPlease ensure you have internet connectivity and valid symbols configured."
    raise RuntimeError(error_msg)

PRICE_DATA, DATE_DATA = load_price_data()

def main():
    
    #core infrastructure
    # Use PriorityEventQueue for timestamp-ordered processing
    # This ensures all events at timestamp T are fully processed before T+1
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()

    #components
    portfolio = PortfolioState(initial_cash=10000)
    
    # Use RealRiskManager with limits
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.15,  # 15% max drawdown
        max_position_pct=0.30,  # Max 30% of equity in single position
        max_total_exposure_pct=1.0,  # Max 100% of equity in total positions
        max_positions=None,  # No limit on number of positions
    )
    
    # Use realistic execution handler with slippage and spread costs
    execution = RealisticExecutionHandler(
        spread_pct=0.001,  # 0.1% bid-ask spread
        base_slippage_pct=0.0005,  # 0.05% base slippage
        impact_factor=0.000001,  # 0.0001% per share market impact
        slippage_volatility=0.0002,  # 0.02% random variation
    )

    # IMPORTANT: Register portfolio handler FIRST so prices are updated before strategies generate signals
    # This ensures risk manager sees the latest mark-to-market equity when checking drawdown
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)

    #register strategies
    strategies = []
    
    for symbol, cfg in STRATEGY_CONFIG.items():
        strategy_cls = cfg["class"]
        params = cfg["params"]

        strategy = strategy_cls(symbol = symbol, **params)
        strategies.append(strategy)

        dispatcher.register_handler(
            MarketEvent,
            strategy.handle_market
        )


    #register other handlers
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)

    market_events = []
    
    # Create date mapping: timestamp -> date
    # Since we interleave events by index, all symbols at index i share the same date
    # Use dates from first symbol that has dates, or None if no dates available
    dates_list = None
    if DATE_DATA:
        # Find first symbol with dates - all symbols should have same dates for same index
        for symbol in PRICE_DATA.keys():
            if symbol in DATE_DATA and DATE_DATA[symbol]:
                dates_list = DATE_DATA[symbol]
                print(f"\n✓ Using dates from {symbol}: {len(dates_list)} dates")
                if dates_list:
                    print(f"  Date range: {dates_list[0]} to {dates_list[-1]}")
                    print(f"  First date type: {type(dates_list[0])}, value: {repr(dates_list[0])}")
                    # Verify dates are reasonable (not 1970)
                    if dates_list[0].year < 2020:
                        print(f"  ⚠️  WARNING: First date year is {dates_list[0].year}, expected 2024!")
                break
    else:
        print("\n⚠️  No date data available - using timestamps for x-axis")

    # Interleave events by index (all symbols at index 0, then all at index 1, etc.)
    # This simulates realistic trading where multiple symbols trade simultaneously
    max_length = max(len(prices) for prices in PRICE_DATA.values()) if PRICE_DATA else 0
    
    t = 0
    for i in range(max_length):
        for symbol, prices in PRICE_DATA.items():
            if i < len(prices):
                event = MarketEvent(
                    timestamp = t,
                    symbol = symbol,
                    price = prices[i]
                )
                market_events.append(event)
                queue.put(event)
        t += 1
        
        

    #event loop
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)

        for e in new_events:
            queue.put(e)

    # Rebuild equity curve aligned with market events
    # The issue: MarketEvents are processed before FillEvents, so MarketEvent t=14
    # might compute equity before FillEvent t=13 updates cash. We need to recompute
    # equity correctly by replaying events in order.
    
    # Recompute equity curve by replaying all events in chronological order
    aligned_equity_curve = []
    replay_cash = portfolio.initial_cash
    replay_positions = {}
    replay_prices = {}
    
    # Get all events sorted by timestamp
    all_events = []
    for event in market_events:
        all_events.append(('market', event.timestamp, event.symbol, event.price))
    for fill in portfolio.trades:
        all_events.append(('fill', fill.timestamp, fill.symbol, fill.direction, fill.quantity, fill.fill_price))
    
    all_events.sort(key=lambda x: (x[1], 0 if x[0] == 'market' else 1))  # market events first at same timestamp
    
    event_idx = 0
    for i, market_event in enumerate(market_events):
        # Process all events up to this market event's timestamp
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
                else:  # SELL
                    replay_cash += qty * price
                    replay_positions[symbol] = replay_positions.get(symbol, 0) - qty
                    if replay_positions[symbol] == 0:
                        del replay_positions[symbol]
            event_idx += 1
        
        # Compute equity at this market event
        equity = replay_cash
        for sym, qty in replay_positions.items():
            if sym in replay_prices:
                equity += qty * replay_prices[sym]
        aligned_equity_curve.append(equity)
    
    # If no events, use initial cash
    if not aligned_equity_curve:
        aligned_equity_curve = [portfolio.initial_cash] * len(market_events)
    
    # Create dates array aligned with market events (one date per market event)
    # Each market event at timestamp t should use dates_list[t]
    dates_for_plotting = None
    if dates_list:
        dates_for_plotting = []
        for event in market_events:
            if event.timestamp < len(dates_list):
                dates_for_plotting.append(dates_list[event.timestamp])
            else:
                # Fallback if timestamp is out of range
                dates_for_plotting.append(dates_list[-1] if dates_list else None)
        print(f"\n✓ Created dates array for plotting: {len(dates_for_plotting)} dates")
        if dates_for_plotting:
            print(f"  Date range in plot: {dates_for_plotting[0]} to {dates_for_plotting[-1]}")
    
    #analysis
    analyzer = EquityAnalyzer(
        market_events = market_events,
        fills = portfolio.trades,
        equity_curve = aligned_equity_curve,
        initial_cash = 10_000
    )
    analyzer.run()


    #trade history
    print("\n--- TRADE HISTORY ---")
    for trade in portfolio.trades:
        print(
            f"{trade.timestamp} | "
            f"{trade.direction} {trade.quantity} "
            f"{trade.symbol} @ {trade.fill_price}"
        )

    # Calculate final equity (cash + open positions)
    final_equity = portfolio.cash
    for symbol, position in portfolio.positions.items():
        if symbol in portfolio.latest_prices:
            final_equity += position.quantity * portfolio.latest_prices[symbol]
    
    # Final portfolio state (current holdings only)
    print("\n--- FINAL PORTFOLIO STATE ---")
    print(f"Cash: ${portfolio.cash:,.2f}")
    if portfolio.positions:
        print("Open Positions:")
        for symbol, position in portfolio.positions.items():
            current_price = portfolio.latest_prices.get(symbol, 0)
            position_value = position.quantity * current_price
            unrealized_pnl = position_value - (position.quantity * position.avg_cost)
            print(f"  {symbol}: {position.quantity} shares @ ${position.avg_cost:.2f} avg")
            print(f"    Current price: ${current_price:.2f}")
            print(f"    Position value: ${position_value:,.2f}")
            print(f"    Unrealized PnL: ${unrealized_pnl:,.2f}")
    else:
        print("Open Positions: None")
    print(f"Final Equity: ${final_equity:,.2f}")
    
    # Performance metrics (all stats consolidated here)
    metrics = TradeMetrics(
        fills = portfolio.trades,
        initial_cash = 10_000,
        final_cash = portfolio.cash,
        final_equity = final_equity,
    )
    metrics.summary()
    
    # Risk metrics
    print("\n--- RISK METRICS ---")
    print(f"Max Drawdown: {analyzer.max_drawdown:.2%}")
    print(f"Sharpe Ratio: {analyzer.sharpe:.2f}")
    
    # Risk rejection summary
    if hasattr(risk, 'get_rejection_summary'):
        rejection_summary = risk.get_rejection_summary()
        if rejection_summary["total"] > 0:
            print("\n--- RISK REJECTIONS ---")
            print(f"Total rejected trades: {rejection_summary['total']}")
            print("Rejections by check:")
            for check, count in rejection_summary["by_check"].items():
                print(f"  {check}: {count}")
            print("Rejections by reason:")
            for reason, count in list(rejection_summary["by_reason"].items())[:5]:  # Show first 5
                print(f"  {reason}: {count}")
        else:
            print("\n--- RISK REJECTIONS ---")
            print("No trades rejected")
    
    # Execution cost summary
    if hasattr(execution, 'get_execution_summary'):
        exec_summary = execution.get_execution_summary()
        if exec_summary["total_trades"] > 0:
            print("\n--- EXECUTION COSTS ---")
            print(f"Total trades: {exec_summary['total_trades']}")
            print(f"Total spread cost: ${exec_summary['total_spread_cost']:,.2f}")
            print(f"Total slippage cost: ${exec_summary['total_slippage_cost']:,.2f}")
            print(f"Total execution cost: ${exec_summary['total_execution_cost']:,.2f}")
            print(f"Average cost per trade: ${exec_summary['avg_cost_per_trade']:,.2f}")
            if final_equity > 0:
                cost_pct = (exec_summary['total_execution_cost'] / portfolio.initial_cash) * 100
                print(f"Execution cost as % of initial capital: {cost_pct:.2f}%")

    #plot
    plot_equity(analyzer, show_price = False, dates = dates_for_plotting)



    
if __name__ == "__main__":
    main()