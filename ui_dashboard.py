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
from execution.simulator import ExecutionHandler, RealisticExecutionHandler
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
    # Use realistic execution handler with slippage and spread costs
    execution = RealisticExecutionHandler(
        spread_pct=0.001,  # 0.1% bid-ask spread
        base_slippage_pct=0.0005,  # 0.05% base slippage
        impact_factor=0.000001,  # 0.0001% per share market impact
        slippage_volatility=0.0002,  # 0.02% random variation
    )
    
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
    
    # Seed market events - interleave by index (all symbols at index 0, then all at index 1, etc.)
    # This simulates realistic trading where multiple symbols trade simultaneously
    max_length = max(len(prices) for prices in PRICE_DATA.values()) if PRICE_DATA else 0
    
    market_events = []
    t = 0
    for i in range(max_length):
        for symbol, prices in PRICE_DATA.items():
            if i < len(prices):
                event = MarketEvent(timestamp=t, symbol=symbol, price=prices[i])
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
    
    # Get execution costs if available
    execution_costs = None
    if hasattr(execution, 'total_execution_cost'):
        execution_costs = {
            'total_spread_cost': execution.total_spread_cost,
            'total_slippage_cost': execution.total_slippage_cost,
            'total_execution_cost': execution.total_execution_cost,
            'num_fills': len(portfolio.trades),
        }
    
    return {
        'portfolio': portfolio,
        'analyzer': analyzer,
        'metrics': metrics,
        'risk': risk,
        'rejection_summary': rejection_summary,
        'market_events': market_events,
        'equity_curve': aligned_equity_curve,
        'final_equity': final_equity,
        'execution_costs': execution_costs,
    }

def plot_equity_curve(equity_curve, market_events, fills=None):
    """Create equity curve plot with entry markers."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Equity curve
    times = [e.timestamp for e in market_events]
    ax1.plot(times, equity_curve, 'b-', linewidth=2, label='Equity')
    ax1.axhline(y=equity_curve[0], color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    
    # Add entry markers with symbols
    if fills:
        # Create timestamp to index mapping
        timestamp_to_index = {e.timestamp: i for i, e in enumerate(market_events)}
        
        # Track BUY entries
        for fill in fills:
            if fill.direction == "BUY" and fill.timestamp in timestamp_to_index:
                idx = timestamp_to_index[fill.timestamp]
                if idx < len(equity_curve):
                    # Plot marker
                    ax1.scatter(
                        fill.timestamp,
                        equity_curve[idx],
                        color='#2ca02c',
                        marker='^',
                        s=100,
                        edgecolors='black',
                        linewidths=1,
                        zorder=4,
                        alpha=0.8
                    )
                    # Add symbol label
                    ax1.text(
                        fill.timestamp,
                        equity_curve[idx],
                        fill.symbol,
                        fontsize=8,
                        ha='center',
                        va='bottom',
                        color='#2ca02c',
                        fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#2ca02c', alpha=0.8),
                        zorder=5
                    )
    
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
st.set_page_config(
    page_title="Trading Engine Dashboard", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Reset Streamlit defaults that interfere */
    h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
        background: transparent !important;
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #ffffff !important;
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
        background: transparent !important;
    }
    
    .section-header {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1a1a1a !important;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        background: transparent !important;
    }
    
    .subsection-header {
        font-size: 0.9rem;
        font-weight: 600;
        color: #1a1a1a !important;
        margin-top: 1.25rem;
        margin-bottom: 0.75rem;
        background: transparent !important;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0.25rem 0;
    }
    
    .metric-label {
        font-size: 0.75rem;
        color: #666666 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    
    .position-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.75rem;
        transition: box-shadow 0.2s;
    }
    
    .position-card:hover {
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .profit {
        color: #16a34a;
        font-weight: 500;
    }
    
    .loss {
        color: #dc2626;
        font-weight: 500;
    }
    
    .neutral {
        color: #666;
        font-weight: 500;
    }
    
    .stat-box {
        background: #fafafa;
        padding: 1rem;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.75rem;
    }
    
    /* Ensure proper spacing between sections */
    .section-spacer {
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Trading Engine Dashboard</h1>', unsafe_allow_html=True)
st.markdown("---")

# Run simulation
with st.spinner("Running simulation..."):
    results = run_simulation()

portfolio = results['portfolio']
analyzer = results['analyzer']
metrics = results['metrics']
risk = results['risk']
rejection_summary = results['rejection_summary']
execution_costs = results.get('execution_costs')
equity_curve = results['equity_curve']
market_events = results['market_events']
final_equity = results['final_equity']

# Main metrics row - Top KPIs
total_return = metrics.total_pnl()
return_pct = (total_return / 10000) * 100

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-label">Final Equity</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value" style="color: #ffffff !important;">${final_equity:,.2f}</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-label">Total Return</div>', unsafe_allow_html=True)
    color_class = "profit" if return_pct >= 0 else "loss"
    st.markdown(f'<div class="metric-value {color_class}">${total_return:,.2f}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="{color_class}" style="font-size: 0.9rem; margin-top: 0.25rem;">{return_pct:+.2f}%</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-label">Max Drawdown</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value loss">{analyzer.max_drawdown:.2%}</div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-label">Sharpe Ratio</div>', unsafe_allow_html=True)
    sharpe_class = "profit" if analyzer.sharpe > 1 else "neutral" if analyzer.sharpe > 0 else "loss"
    st.markdown(f'<div class="metric-value {sharpe_class}">{analyzer.sharpe:.2f}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Equity curve plot
st.markdown('<div class="section-header">Equity Curve & Drawdown</div>', unsafe_allow_html=True)
fig = plot_equity_curve(equity_curve, market_events, fills=portfolio.trades)
st.pyplot(fig)
plt.close(fig)
st.markdown("<br>", unsafe_allow_html=True)

# Two column layout
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-header" style="color: #ffffff !important;">Portfolio State</div>', unsafe_allow_html=True)
    
    # Cash
    st.markdown(f"""
    <div class="stat-box">
        <div class="metric-label">Cash</div>
        <div class="metric-value">${portfolio.cash:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="subsection-header" style="color: #ffffff !important;">Open Positions</div>', unsafe_allow_html=True)
    if portfolio.positions:
        for symbol, position in portfolio.positions.items():
            current_price = portfolio.latest_prices.get(symbol, 0)
            position_value = position.quantity * current_price
            unrealized_pnl = position_value - (position.quantity * position.avg_cost)
            pnl_class = "profit" if unrealized_pnl >= 0 else "loss"
            
            st.markdown(f"""
            <div class="position-card">
                <div style="font-weight: 600; font-size: 1rem; color: #1a1a1a; margin-bottom: 0.75rem;">{symbol}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem;">
                    <div>
                        <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.25rem;">SHARES</div>
                        <div style="font-weight: 500; color: #1a1a1a;">{position.quantity}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.25rem;">AVG COST</div>
                        <div style="font-weight: 500; color: #1a1a1a;">${position.avg_cost:.2f}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.25rem;">CURRENT</div>
                        <div style="font-weight: 500; color: #1a1a1a;">${current_price:.2f}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.25rem;">VALUE</div>
                        <div style="font-weight: 500; color: #1a1a1a;">${position_value:,.2f}</div>
                    </div>
                </div>
                <div style="padding-top: 0.75rem; border-top: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.75rem; color: #666; text-transform: uppercase;">Unrealized PnL</span>
                    <span class="{pnl_class}" style="font-weight: 600; font-size: 1rem;">${unrealized_pnl:,.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="stat-box" style="text-align: center; color: #666; padding: 2rem;">
            No open positions
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="subsection-header" style="margin-top: 1.5rem; color: #ffffff !important;">Final Equity</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stat-box">
        <div class="metric-value">${final_equity:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-header" style="color: #ffffff !important;">Performance Metrics</div>', unsafe_allow_html=True)
    
    # Capital metrics
    st.markdown('<div class="subsection-header">Capital</div>', unsafe_allow_html=True)
    col_cap1, col_cap2 = st.columns(2)
    with col_cap1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Initial Capital</div>
            <div class="metric-value">${metrics.initial_cash:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_cap2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Final Equity</div>
            <div class="metric-value">${final_equity:,.2f} </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Returns
    st.markdown('<div class="subsection-header" style="margin-top: 1rem; color: #ffffff !important;">Returns</div>', unsafe_allow_html=True)
    realized_pnl = portfolio.cash - metrics.initial_cash
    unrealized_pnl = final_equity - portfolio.cash
    return_class = "profit" if return_pct >= 0 else "loss"
    realized_class = "profit" if realized_pnl >= 0 else "loss"
    unrealized_class = "profit" if unrealized_pnl >= 0 else "loss"
    
    st.markdown(f"""
    <div class="stat-box">
        <div class="metric-label">Total Return</div>
        <div class="metric-value {return_class}">${total_return:,.2f}</div>
        <div class="{return_class}" style="font-size: 0.9rem; margin-top: 0.25rem;">{return_pct:+.2f}%</div>
    </div>
    <div class="stat-box">
        <div class="metric-label">Realized PnL</div>
        <div class="metric-value {realized_class}">${realized_pnl:,.2f}</div>
    </div>
    <div class="stat-box">
        <div class="metric-label">Unrealized PnL</div>
        <div class="metric-value {unrealized_class}">${unrealized_pnl:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Trading statistics
    st.markdown('<div class="subsection-header" style="margin-top: 1rem; color: #ffffff !important;">Trading Statistics</div>', unsafe_allow_html=True)
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Trades</div>
            <div class="metric-value">{metrics.num_trades()}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{metrics.win_rate() * 100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col_stat2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Avg PnL/Trade</div>
            <div class="metric-value">${metrics.avg_pnl_per_trade():.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Execution costs
    if execution_costs:
        st.markdown('<div class="subsection-header" style="margin-top: 1rem;">Execution Costs</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Breakdown</div>
            <div style="margin-top: 0.75rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
                    <span style="color: #666;">Spread</span>
                    <span style="color: #1a1a1a; font-weight: 500;">${execution_costs['total_spread_cost']:,.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
                    <span style="color: #666;">Slippage</span>
                    <span style="color: #1a1a1a; font-weight: 500;">${execution_costs['total_slippage_cost']:,.2f}</span>
                </div>
                <div style="padding-top: 0.75rem; border-top: 1px solid #e0e0e0; margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #1a1a1a;">Total</span>
                    <span style="font-weight: 600; font-size: 1.1rem; color: #1a1a1a;">${execution_costs['total_execution_cost']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
        if execution_costs['num_fills'] > 0:
            avg_cost = execution_costs['total_execution_cost'] / execution_costs['num_fills']
            st.markdown(f"""
            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">
                Avg per trade: <span style="font-weight: 500; color: #1a1a1a;">${avg_cost:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)

# Risk metrics and rejections
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-header">Risk Metrics</div>', unsafe_allow_html=True)
    col_risk1, col_risk2 = st.columns(2)
    with col_risk1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value loss">{analyzer.max_drawdown:.2%}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_risk2:
        sharpe_class = "profit" if analyzer.sharpe > 1 else "neutral" if analyzer.sharpe > 0 else "loss"
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value {sharpe_class}">{analyzer.sharpe:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-header">Risk Rejections</div>', unsafe_allow_html=True)
    if rejection_summary and rejection_summary["total"] > 0:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-label">Total Rejected</div>
            <div class="metric-value loss">{rejection_summary['total']}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="margin-top: 1rem; font-size: 0.75rem; color: #666; text-transform: uppercase; margin-bottom: 0.5rem;">Breakdown by Check</div>', unsafe_allow_html=True)
        for check, count in rejection_summary["by_check"].items():
            st.markdown(f"""
            <div class="stat-box" style="padding: 0.75rem; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.9rem; color: #1a1a1a;">{check}</span>
                    <span style="font-weight: 600; color: #dc2626;">{count}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="stat-box" style="text-align: center; padding: 2rem; color: #666;">
            No trades rejected
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #999; padding: 1rem; font-size: 0.85rem;'>
    Trading Engine Dashboard - Results from latest simulation run
</div>
""", unsafe_allow_html=True)

