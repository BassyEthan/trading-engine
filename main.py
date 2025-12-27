from datetime import datetime

from core.event_queue import EventQueue
from core.dispatcher import Dispatcher

from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
#from strategies.base import OneShotBuyStrategy
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import PassThroughRiskManager
from execution.simulator import ExecutionHandler
from portfolio.state import PortfolioState

from analysis.metrics import TradeMetrics
from analysis.equity_curve import plot_equity_curve


# Entry point of trading engine.
# Responsibility is to wire together system components
# event queue, dispatcher, handlers start the event loop

# Doesn't contain trading logic, strategic logic, risk rules, or portfolio updates

# Purely exists to instatiate core objects, register handlers with the dispatcher, seed the system with initial events, and run the event-processing loop

def main():
    
    #core infrastructure
    queue = EventQueue()
    dispatcher = Dispatcher()

    #components
    #RollingMeanReversionStrategy
    strategy = RollingMeanReversionStrategy(
        window = 5,
        threshold = 2.0,
        symbol = "APPL"
    )
    risk = PassThroughRiskManager(fixed_quantity=10)
    execution = ExecutionHandler()
    portfolio = PortfolioState(initial_cash=10000)

    #register handlers
    dispatcher.register_handler(MarketEvent, strategy.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)

    prices = [100, 101, 102, 99, 95, 97, 100, 103, 98, 94, 96, 101]
    market_events = []

    for price in prices:
        
        event = MarketEvent(
            timestamp = datetime.utcnow(),
            symbol = "APPL",
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


    #metrics
    metrics = TradeMetrics(
        fills = portfolio.trades,
        initial_cash = 10_000,
        final_cash = portfolio.cash,
    )
    metrics.summary()

    #equity curve
    plot_equity_curve(
        market_events = market_events,
        fills = portfolio.trades,
        initial_cash = 10_000,
    )



    
if __name__ == "__main__":
    main()