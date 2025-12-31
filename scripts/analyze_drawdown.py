"""
Detailed drawdown analysis tool.

Analyzes equity curve to find all peaks, their subsequent drops, and verify max drawdown.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from core.event_queue import PriorityEventQueue
from core.dispatcher import Dispatcher
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategies.mean_reversion import RollingMeanReversionStrategy
from risk.engine import RealRiskManager
from execution.simulator import RealisticExecutionHandler
from portfolio.state import PortfolioState


def run_simulation_and_analyze():
    """Run simulation and analyze drawdown in detail."""
    from data.loader import load_market_data
    
    # Load test data
    test_path = Path("data/ml_training/test_data.json")
    if not test_path.exists():
        print("❌ Test data not found. Run: python3 scripts/download_ml_data.py")
        return
    
    with open(test_path, 'r') as f:
        data = json.load(f)
    
    # Initialize components
    queue = PriorityEventQueue()
    dispatcher = Dispatcher()
    portfolio = PortfolioState(initial_cash=10000.0)
    
    risk = RealRiskManager(
        portfolio=portfolio,
        fixed_quantity=10,
        max_drawdown=0.50,  # High limit for testing
        max_position_pct=0.30,
        max_total_exposure_pct=1.0,
        max_positions=None,
    )
    
    execution = RealisticExecutionHandler(
        spread_pct=0.001,
        base_slippage_pct=0.0005,
        impact_factor=0.000001,
        slippage_volatility=0.0002,
    )
    
    # Simple strategy
    strategies = {}
    for symbol in data.keys():
        strategies[symbol] = RollingMeanReversionStrategy(
            symbol=symbol,
            window=5,
            threshold=2.0,
        )
    
    dispatcher.register_handler(MarketEvent, portfolio.handle_market)
    for strategy in strategies.values():
        dispatcher.register_handler(MarketEvent, strategy.handle_market)
    dispatcher.register_handler(SignalEvent, risk.handle_signal)
    dispatcher.register_handler(OrderEvent, execution.handle_order)
    dispatcher.register_handler(FillEvent, portfolio.handle_fill)
    
    # Seed events (interleaved)
    max_length = max(len(prices) for prices in data.values())
    market_events = []
    timestamp = 0
    for i in range(max_length):
        for symbol, prices in data.items():
            if i < len(prices):
                event = MarketEvent(timestamp=timestamp, symbol=symbol, price=prices[i])
                market_events.append(event)
                queue.put(event)
        timestamp += 1
    
    # Run simulation
    while not queue.is_empty():
        event = queue.get()
        new_events = dispatcher.dispatch(event)
        for new_event in new_events:
            queue.put(new_event)
    
    # Rebuild equity curve
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
    
    return aligned_equity_curve, market_events


def analyze_drawdown_detailed(equity_curve):
    """Detailed drawdown analysis showing all peaks and drops."""
    print("=" * 70)
    print("DETAILED DRAWDOWN ANALYSIS")
    print("=" * 70)
    print()
    
    print(f"Equity curve length: {len(equity_curve)} points")
    print(f"Equity range: ${min(equity_curve):,.2f} to ${max(equity_curve):,.2f}")
    print()
    
    # Track peaks and their subsequent drops
    peak = equity_curve[0]
    peak_indices = [0]
    drawdowns = []
    
    for i, equity in enumerate(equity_curve):
        if equity > peak:
            peak = equity
            peak_indices.append(i)
        
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns.append(dd)
    
    print(f"Number of peaks: {len(peak_indices)}")
    print(f"Peak indices: {peak_indices[:10]}..." if len(peak_indices) > 10 else f"Peak indices: {peak_indices}")
    print()
    
    # Analyze each peak and its subsequent drop
    peaks_analysis = []
    for i, peak_idx in enumerate(peak_indices):
        peak_value = equity_curve[peak_idx]
        
        # Find the lowest point AFTER this peak (before next peak)
        if peak_idx < len(equity_curve) - 1:
            # Find next peak
            next_peak_idx = None
            if i + 1 < len(peak_indices):
                next_peak_idx = peak_indices[i + 1]
            
            # Find minimum between this peak and next peak (or end)
            end_idx = next_peak_idx if next_peak_idx else len(equity_curve)
            
            # Only look forward from peak
            if end_idx > peak_idx:
                segment = equity_curve[peak_idx:end_idx]
                min_value = min(segment)
                min_idx = peak_idx + segment.index(min_value)
                
                # Only count if trough comes after peak
                if min_idx > peak_idx:
                    drop_pct = (peak_value - min_value) / peak_value
                    drop_amount = peak_value - min_value
                    
                    peaks_analysis.append({
                        'peak_idx': peak_idx,
                        'peak_value': peak_value,
                        'min_idx': min_idx,
                        'min_value': min_value,
                        'drop_pct': drop_pct,
                        'drop_amount': drop_amount,
                        'duration': min_idx - peak_idx,
                    })
    
    # Sort by drop percentage (largest first)
    peaks_analysis.sort(key=lambda x: x['drop_pct'], reverse=True)
    
    print("TOP 10 PEAK-TO-TROUGH DROPS:")
    print("-" * 70)
    print(f"{'Rank':<6} {'Peak Index':<12} {'Peak Value':<15} {'Trough Index':<15} {'Trough Value':<15} {'Drop %':<12} {'Duration':<10}")
    print("-" * 70)
    
    for rank, info in enumerate(peaks_analysis[:10], 1):
        print(f"{rank:<6} {info['peak_idx']:<12} ${info['peak_value']:>13,.2f} {info['min_idx']:<15} ${info['min_value']:>13,.2f} {info['drop_pct']:>11.2%} {info['duration']:<10}")
    
    print()
    
    # Max drawdown
    max_dd = max(drawdowns)
    max_dd_idx = drawdowns.index(max_dd)
    
    # Find the peak that led to this max drawdown
    peak_before_max_dd = max(equity_curve[:max_dd_idx+1])
    peak_idx_before_max_dd = equity_curve.index(peak_before_max_dd)
    
    print("=" * 70)
    print("MAX DRAWDOWN")
    print("=" * 70)
    print()
    print(f"Max drawdown: {max_dd:.2%}")
    print(f"Peak: ${peak_before_max_dd:,.2f} at index {peak_idx_before_max_dd}")
    print(f"Trough: ${equity_curve[max_dd_idx]:,.2f} at index {max_dd_idx}")
    print(f"Drop amount: ${peak_before_max_dd - equity_curve[max_dd_idx]:,.2f}")
    print(f"Duration: {max_dd_idx - peak_idx_before_max_dd} points")
    print()
    
    # Check specific ranges the user mentioned
    if len(equity_curve) > 900:
        print("=" * 70)
        print("SPECIFIC RANGE ANALYSIS")
        print("=" * 70)
        print()
        
        # Range 600-700: Find peak-to-trough drawdown within this range
        range_600_700 = equity_curve[600:701] if len(equity_curve) > 700 else []
        if range_600_700:
            # Find peak in this range, then find lowest point after it
            peak_600_700 = max(range_600_700)
            peak_idx_600_700 = 600 + range_600_700.index(peak_600_700)
            
            # Find minimum AFTER the peak (within range)
            if peak_idx_600_700 < 700:
                segment_after_peak = equity_curve[peak_idx_600_700:701]
                trough_600_700 = min(segment_after_peak)
                trough_idx_600_700 = peak_idx_600_700 + segment_after_peak.index(trough_600_700)
                drop_600_700 = (peak_600_700 - trough_600_700) / peak_600_700 if peak_600_700 > 0 else 0.0
            else:
                trough_600_700 = peak_600_700
                trough_idx_600_700 = peak_idx_600_700
                drop_600_700 = 0.0
            
            print(f"Range 600-700:")
            print(f"  Peak: ${peak_600_700:,.2f} at index {peak_idx_600_700}")
            print(f"  Trough after peak: ${trough_600_700:,.2f} at index {trough_idx_600_700}")
            print(f"  Drop: {drop_600_700:.2%}")
            print()
        
        # Range 800-900: Find peak-to-trough drawdown within this range
        range_800_900 = equity_curve[800:901] if len(equity_curve) > 900 else []
        if range_800_900:
            # Find peak in this range, then find lowest point after it
            peak_800_900 = max(range_800_900)
            peak_idx_800_900 = 800 + range_800_900.index(peak_800_900)
            
            # Find minimum AFTER the peak (within range)
            if peak_idx_800_900 < 900:
                segment_after_peak = equity_curve[peak_idx_800_900:901]
                trough_800_900 = min(segment_after_peak)
                trough_idx_800_900 = peak_idx_800_900 + segment_after_peak.index(trough_800_900)
                drop_800_900 = (peak_800_900 - trough_800_900) / peak_800_900 if peak_800_900 > 0 else 0.0
            else:
                trough_800_900 = peak_800_900
                trough_idx_800_900 = peak_idx_800_900
                drop_800_900 = 0.0
            
            print(f"Range 800-900:")
            print(f"  Peak: ${peak_800_900:,.2f} at index {peak_idx_800_900}")
            print(f"  Trough after peak: ${trough_800_900:,.2f} at index {trough_idx_800_900}")
            print(f"  Drop: {drop_800_900:.2%}")
            print()
        
        # Compare
        if range_600_700 and range_800_900:
            print("Comparison:")
            if drop_600_700 > drop_800_900:
                print(f"  Range 600-700 has larger drop ({drop_600_700:.2%} vs {drop_800_900:.2%})")
            else:
                print(f"  Range 800-900 has larger drop ({drop_800_900:.2%} vs {drop_600_700:.2%})")
            print()
            print(f"  Max drawdown ({max_dd:.2%}) is from peak at index {peak_idx_before_max_dd}")
            if peak_idx_before_max_dd >= 600 and peak_idx_before_max_dd <= 700:
                print(f"  ✓ Max drawdown is in range 600-700")
            elif peak_idx_before_max_dd >= 800 and peak_idx_before_max_dd <= 900:
                print(f"  ✓ Max drawdown is in range 800-900")
            else:
                print(f"  Max drawdown is outside both ranges")
    
    return peaks_analysis, max_dd, max_dd_idx


if __name__ == "__main__":
    print("=" * 70)
    print("DRAWDOWN ANALYSIS TOOL")
    print("=" * 70)
    print()
    print("Running simulation...")
    print()
    
    equity_curve, market_events = run_simulation_and_analyze()
    
    if not equity_curve:
        print("❌ No equity curve generated")
        exit(1)
    
    peaks_analysis, max_dd, max_dd_idx = analyze_drawdown_detailed(equity_curve)
    
    print("=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70)

