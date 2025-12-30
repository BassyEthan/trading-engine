"""
Simple Streamlit dashboard for trading engine results.
Run with: streamlit run ui_dashboard.py
"""

import streamlit as st
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

# Add project root to path
sys.path.insert(0, '.')

from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher
from portfolio.state import PortfolioState
from risk.engine import RealRiskManager
from execution.simulator import ExecutionHandler
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.mean_reversion import RollingMeanReversionStrategy
from strategies.one_shot import OneShotBuyStrategy
from strategies.multi_signal import MultiSignalStrategy
from analysis.metrics import TradeMetrics
from analysis.equity_analyzer import EquityAnalyzer

# Import config from main
from main import PRICE_DATA, STRATEGY_CONFIG

def run_simulation():
    """Run the trading simulation and return all results."""
    # Core infrastructure
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()
    
    # Components
    portfolio = PortfolioState(initial_cash=10000)
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.15,
        max_position_pct=0.30,
        max_total_exposure_pct=1.0,
        max_positions=None,
    )
    execution = ExecutionHandler()
    
    # Register portfolio handler first
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    
    # Register strategies
    strategies = []
    for symbol, cfg in STRATEGY_CONFIG.items():
        strategy_cls = cfg["class"]
        params = cfg["params"]
        strategy = strategy_cls(symbol=symbol, **params)
        strategies.append(strategy)
        dispatcher.register_handler(MarketEvent, strategy.handle_market)
    
    # Register other handlers
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # Seed market events
    market_events = []
    t = 0
    for symbol, prices in PRICE_DATA.items():
        for price in prices:
            event = MarketEvent(timestamp=t, symbol=symbol, price=price)
            market_events.append(event)
            queue.put(event)
            t += 1
    
    # Event loop
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for e in new_events:
            queue.put(e)
    
    # Rebuild equity curve aligned with market events
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
    
    if not aligned_equity_curve:
        aligned_equity_curve = [portfolio.initial_cash] * len(market_events)
    
    # Calculate final equity
    final_equity = portfolio.cash
    for symbol, position in portfolio.positions.items():
        if symbol in portfolio.latest_prices:
            final_equity += position.quantity * portfolio.latest_prices[symbol]
    
    # Create analyzer
    analyzer = EquityAnalyzer(
        market_events=market_events,
        fills=portfolio.trades,
        equity_curve=aligned_equity_curve,
        initial_cash=10000
    )
    analyzer.run()
    
    # Create metrics
    metrics = TradeMetrics(
        fills=portfolio.trades,
        initial_cash=10000,
        final_cash=portfolio.cash,
        final_equity=final_equity,
    )
    
    # Get rejection summary
    rejection_summary = None
    if hasattr(risk, 'get_rejection_summary'):
        rejection_summary = risk.get_rejection_summary()
    
    return {
        'portfolio': portfolio,
        'analyzer': analyzer,
        'metrics': metrics,
        'risk': risk,
        'rejection_summary': rejection_summary,
        'market_events': market_events,
        'equity_curve': aligned_equity_curve,
        'final_equity': final_equity,
    }

def plot_equity_curve(equity_curve, market_events):
    """Create equity curve plot."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Equity curve
    times = [e.timestamp for e in market_events]
    ax1.plot(times, equity_curve, 'b-', linewidth=2, label='Equity')
    ax1.axhline(y=equity_curve[0], color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_ylabel('Equity ($)', fontsize=12)
    ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Drawdown
    peak = equity_curve[0]
    drawdown = []
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak if peak > 0 else 0
        drawdown.append(dd)
    
    ax2.fill_between(times, drawdown, 0, color='red', alpha=0.3, label='Drawdown')
    ax2.plot(times, drawdown, 'r-', linewidth=1.5)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel('Drawdown', fontsize=12)
    ax2.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim([min(drawdown) * 1.1, 0.01])
    
    plt.tight_layout()
    return fig

# Streamlit app
st.set_page_config(page_title="Trading Engine Dashboard", layout="wide")

st.title("📈 Trading Engine Dashboard")
st.markdown("---")

# Run simulation
with st.spinner("Running simulation..."):
    results = run_simulation()

portfolio = results['portfolio']
analyzer = results['analyzer']
metrics = results['metrics']
risk = results['risk']
rejection_summary = results['rejection_summary']
equity_curve = results['equity_curve']
market_events = results['market_events']
final_equity = results['final_equity']

# Main metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Final Equity", f"${final_equity:,.2f}")
with col2:
    total_return = metrics.total_pnl()
    return_pct = (total_return / 10000) * 100
    st.metric("Total Return", f"${total_return:,.2f}", f"{return_pct:+.2f}%")
with col3:
    st.metric("Max Drawdown", f"{analyzer.max_drawdown:.2%}")
with col4:
    st.metric("Sharpe Ratio", f"{analyzer.sharpe:.2f}")

st.markdown("---")

# Equity curve plot
st.subheader("📊 Equity Curve & Drawdown")
fig = plot_equity_curve(equity_curve, market_events)
st.pyplot(fig)
plt.close(fig)

# Two column layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("💼 Portfolio State")
    st.write(f"**Cash:** ${portfolio.cash:,.2f}")
    
    if portfolio.positions:
        st.write("**Open Positions:**")
        for symbol, position in portfolio.positions.items():
            current_price = portfolio.latest_prices.get(symbol, 0)
            position_value = position.quantity * current_price
            unrealized_pnl = position_value - (position.quantity * position.avg_cost)
            st.write(f"""
            **{symbol}**
            - Shares: {position.quantity} @ ${position.avg_cost:.2f} avg
            - Current: ${current_price:.2f}
            - Value: ${position_value:,.2f}
            - Unrealized PnL: ${unrealized_pnl:,.2f}
            """)
    else:
        st.write("**Open Positions:** None")
    
    st.write(f"**Final Equity:** ${final_equity:,.2f}")

with col2:
    st.subheader("📊 Performance Metrics")
    st.write(f"**Initial Capital:** ${metrics.initial_cash:,.2f}")
    st.write(f"**Final Equity:** ${final_equity:,.2f}")
    st.write(f"**Total Return:** ${total_return:,.2f} ({return_pct:+.2f}%)")
    
    realized_pnl = portfolio.cash - metrics.initial_cash
    unrealized_pnl = final_equity - portfolio.cash
    st.write(f"**Realized PnL:** ${realized_pnl:,.2f}")
    st.write(f"**Unrealized PnL:** ${unrealized_pnl:,.2f}")
    
    st.write("**Trading Statistics:**")
    st.write(f"- Number of trades: {metrics.num_trades()}")
    st.write(f"- Win rate: {metrics.win_rate() * 100:.1f}%")
    st.write(f"- Avg PnL per trade: ${metrics.avg_pnl_per_trade():.2f}")

st.markdown("---")

# Risk metrics and rejections
col1, col2 = st.columns(2)

with col1:
    st.subheader("⚠️ Risk Metrics")
    st.write(f"**Max Drawdown:** {analyzer.max_drawdown:.2%}")
    st.write(f"**Sharpe Ratio:** {analyzer.sharpe:.2f}")

with col2:
    st.subheader("🚫 Risk Rejections")
    if rejection_summary and rejection_summary["total"] > 0:
        st.write(f"**Total rejected trades:** {rejection_summary['total']}")
        st.write("**Rejections by check:**")
        for check, count in rejection_summary["by_check"].items():
            st.write(f"- {check}: {count}")
    else:
        st.write("No trades rejected")

st.markdown("---")
st.caption("Trading Engine Dashboard - Run simulation to see results")

