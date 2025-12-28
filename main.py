from datetime import datetime

from core.event_queue import EventQueue
from core.dispatcher import Dispatcher

from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.one_shot import OneShotBuyStrategy
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import PassThroughRiskManager
from execution.simulator import ExecutionHandler
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
        "class": RollingMeanReversionStrategy,
        "params": {
            "window": 5,
            "threshold": 2.0,
        }
    },
    "MSFT": {
        "class": OneShotBuyStrategy,
        "params": {}
    }
}

# ----------------------
# MARKET DATA - fake rn
# ----------------------

PRICE_DATA = {
    "APPL": [100, 101, 102, 99, 95, 97, 100, 103, 98, 94, 96, 101],
    "MSFT": [200, 202, 201, 203, 105, 105, 204, 206, 207, 100, 200]
}

def main():
    
    #core infrastructure
    queue = EventQueue()
    dispatcher = Dispatcher()

    #components
    risk = PassThroughRiskManager(fixed_quantity=10)
    execution = ExecutionHandler()
    portfolio = PortfolioState(initial_cash=10000)

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


    #register handlers
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)

    market_events = []

    for symbol, prices in PRICE_DATA.items():
        for price in prices:
            event = MarketEvent(
                timestamp = datetime.utcnow(),
                symbol = symbol,
                price = price
            )
            market_events.append(event)
            queue.put(event)
        
        

    #event loop
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)

        for e in new_events:
            queue.put(e)

    #analysis
    analyzer = EquityAnalyzer(
        market_events = market_events,
        fills = portfolio.trades,
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

    #final portfolio state
    print("\n--- FINAL PORTFOLIO STATE ---")
    print("Cash:", portfolio.cash)
    print("Positions:", portfolio.positions)
    print("Realized PnL:", portfolio.realized_pnl)
    print(f"Max Drawdown: {analyzer.max_drawdown:.2%}")
    print(f"Sharpe Ratio: {analyzer.sharpe:.2f}")



    #metrics
    metrics = TradeMetrics(
        fills = portfolio.trades,
        initial_cash = 10_000,
        final_cash = portfolio.cash,
    )
    metrics.summary()

    #plot
    plot_equity(analyzer, show_price = False)



    
if __name__ == "__main__":
    main()