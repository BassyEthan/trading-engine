"""
Test ML strategy in trading engine.

Runs backtest with ML strategy and compares to mean reversion baseline.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.ml_strategy import MLStrategy
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import RealRiskManager
from execution.simulator import RealisticExecutionHandler
from portfolio.state import PortfolioState
from analysis.metrics import TradeMetrics
import numpy as np
import json


def load_test_data():
    """Load test data for backtesting."""
    test_path = Path("data/ml_training/test_data.json")
    if not test_path.exists():
        raise FileNotFoundError(f"Test data not found: {test_path}")
    
    with open(test_path, 'r') as f:
        return json.load(f)


def run_backtest(data, strategy_class, strategy_params, strategy_name):
    """Run backtest with given strategy."""
    print("=" * 70)
    print(f"BACKTEST: {strategy_name}")
    print("=" * 70)
    print()
    
    # Initialize components
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()
    portfolio = PortfolioState(initial_cash=10000.0)
    
    # Risk manager
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.15,
        max_position_pct=0.30,
        max_total_exposure_pct=1.0,
        max_positions=None,
    )
    
    # Execution handler
    execution = RealisticExecutionHandler(
        spread_pct=0.001,
        base_slippage_pct=0.0005,
        impact_factor=0.000001,
        slippage_volatility=0.0002,
    )
    
    # Create strategy instances for each symbol
    strategies = {}
    for symbol in data.keys():
        if strategy_class == MLStrategy:
            strategies[symbol] = strategy_class(
                model_path="ml/models/price_direction_model.pkl",
                symbol=symbol,
                **strategy_params,
            )
        else:
            strategies[symbol] = strategy_class(
                symbol=symbol,
                **strategy_params,
            )
    
    # IMPORTANT: Register portfolio handler FIRST so prices are updated before strategies
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    
    # Register strategies
    for strategy in strategies.values():
        dispatcher.register_handler(MarketEvent, strategy.handle_market)
    
    # Register other handlers
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # Seed market events - interleave by index (all symbols at index 0, then all at index 1, etc.)
    # This simulates realistic trading where multiple symbols trade simultaneously
    max_length = max(len(prices) for prices in data.values()) if data else 0
    
    timestamp = 0
    for i in range(max_length):
        for symbol, prices in data.items():
            if i < len(prices):
                event = MarketEvent(timestamp=timestamp, symbol=symbol, price=prices[i])
                queue.put(event)
        timestamp += 1
    
    # Run event loop
    print("Running backtest...")
    event_count = 0
    while not queue.is_empty():
        event = queue.get()
        event_count += 1
        
        # Dispatch event and process any new events generated
        new_events = dispatcher.dispatch(event)
        for new_event in new_events:
            queue.put(new_event)
    
    print(f"✅ Processed {event_count} events")
    print()
    
    # Calculate final equity (cash + open positions)
    final_equity = portfolio.cash
    for symbol, position in portfolio.positions.items():
        if symbol in portfolio.latest_prices:
            final_equity += position.quantity * portfolio.latest_prices[symbol]
    
    final_cash = portfolio.cash
    
    metrics = TradeMetrics(
        fills=portfolio.trades,
        initial_cash=10000.0,
        final_cash=final_cash,
        final_equity=final_equity,
    )
    
    # Calculate Sharpe ratio and max drawdown from equity curve
    # Build equity curve from equity_by_timestamp
    if portfolio.equity_by_timestamp:
        equity_curve = [portfolio.equity_by_timestamp[t] for t in sorted(portfolio.equity_by_timestamp.keys())]
    else:
        equity_curve = [portfolio.initial_cash]
    
    # Calculate Sharpe ratio (simplified)
    if len(equity_curve) > 1:
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] for i in range(1, len(equity_curve))]
        if returns:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0
    
    # Calculate max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    
    # Print results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"Initial Cash: ${metrics.initial_cash:,.2f}")
    print(f"Final Equity: ${final_equity:,.2f}")
    total_return = metrics.total_pnl() / metrics.initial_cash
    print(f"Total Return: {total_return:.2%}")
    print(f"Total PnL: ${metrics.total_pnl():,.2f}")
    print()
    print(f"Number of Trades: {metrics.num_trades()}")
    print(f"Win Rate: {metrics.win_rate():.2%}")
    print(f"Avg PnL per Trade: ${metrics.avg_pnl_per_trade():,.2f}")
    print()
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: {max_dd:.2%}")
    print()
    
    return {
        'strategy': strategy_name,
        'total_return': metrics.total_pnl() / metrics.initial_cash,
        'total_pnl': metrics.total_pnl(),
        'num_trades': len(portfolio.trades),
        'win_rate': metrics.win_rate() if len(portfolio.trades) > 0 else 0.0,
        'avg_pnl': metrics.avg_pnl_per_trade() if len(portfolio.trades) > 0 else 0.0,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'final_equity': final_equity,
    }


def compare_strategies():
    """Compare ML strategy vs mean reversion."""
    print("=" * 70)
    print("ML STRATEGY vs MEAN REVERSION COMPARISON")
    print("=" * 70)
    print()
    
    # Load test data
    data = load_test_data()
    print(f"Test data: {len(data)} symbols")
    print()
    
    # Test ML Strategy
    ml_results = run_backtest(
        data,
        MLStrategy,
        {'buy_threshold': 0.50001, 'sell_threshold': 0.49999},
        "ML Strategy (Logistic Regression)"
    )
    
    print()
    print()
    
    # Test Mean Reversion (baseline)
    mr_results = run_backtest(
        data,
        RollingMeanReversionStrategy,
        {'window': 5, 'threshold': 2.0},
        "Mean Reversion (Baseline)"
    )
    
    # Comparison
    print()
    print("=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Metric':<25} {'ML Strategy':<20} {'Mean Reversion':<20}")
    print("-" * 70)
    print(f"{'Total Return':<25} {ml_results['total_return']:>18.2%} {mr_results['total_return']:>18.2%}")
    print(f"{'Total PnL':<25} ${ml_results['total_pnl']:>17,.2f} ${mr_results['total_pnl']:>17,.2f}")
    print(f"{'Number of Trades':<25} {ml_results['num_trades']:>20} {mr_results['num_trades']:>20}")
    print(f"{'Win Rate':<25} {ml_results['win_rate']:>18.2%} {mr_results['win_rate']:>18.2%}")
    print(f"{'Avg PnL per Trade':<25} ${ml_results['avg_pnl']:>17,.2f} ${mr_results['avg_pnl']:>17,.2f}")
    print(f"{'Sharpe Ratio':<25} {ml_results['sharpe']:>20.2f} {mr_results['sharpe']:>20.2f}")
    print(f"{'Max Drawdown':<25} {ml_results['max_drawdown']:>18.2%} {mr_results['max_drawdown']:>18.2%}")
    print()
    
    # Winner
    if ml_results['total_return'] > mr_results['total_return']:
        print("🏆 ML Strategy wins on total return!")
    elif mr_results['total_return'] > ml_results['total_return']:
        print("🏆 Mean Reversion wins on total return!")
    else:
        print("🤝 Tie on total return!")
    print()


if __name__ == "__main__":
    compare_strategies()

