"""
Visualize drawdown calculation to verify correctness.

Shows equity curve with peaks, troughs, and drawdown annotations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
import numpy as np


def visualize_drawdown_calculation(equity_curve, save_path=None):
    """Create detailed visualization of drawdown calculation."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    
    times = range(len(equity_curve))
    
    # Plot equity curve
    ax1.plot(times, equity_curve, 'b-', linewidth=2, label='Equity', alpha=0.7)
    
    # Calculate and plot running peak
    running_peak = []
    peak = equity_curve[0]
    for equity in equity_curve:
        peak = max(peak, equity)
        running_peak.append(peak)
    
    ax1.plot(times, running_peak, 'g--', linewidth=1.5, alpha=0.5, label='Running Peak')
    
    # Calculate drawdown
    drawdowns = []
    peak = equity_curve[0]
    max_dd = 0.0
    max_dd_idx = 0
    
    for i, equity in enumerate(equity_curve):
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns.append(dd)
        if dd > max_dd:
            max_dd = dd
            max_dd_idx = i
    
    # Find peak that led to max drawdown
    peak_before_max_dd = max(equity_curve[:max_dd_idx+1])
    peak_idx_before_max_dd = equity_curve.index(peak_before_max_dd)
    
    # Annotate max drawdown
    ax1.plot([peak_idx_before_max_dd, max_dd_idx], 
             [peak_before_max_dd, equity_curve[max_dd_idx]], 
             'r-', linewidth=3, alpha=0.7, label=f'Max Drawdown ({max_dd:.2%})')
    ax1.scatter([peak_idx_before_max_dd, max_dd_idx], 
                [peak_before_max_dd, equity_curve[max_dd_idx]], 
                color='red', s=100, zorder=5)
    ax1.annotate(f'Peak\n${peak_before_max_dd:,.0f}',
                 xy=(peak_idx_before_max_dd, peak_before_max_dd),
                 xytext=(peak_idx_before_max_dd, peak_before_max_dd + (max(equity_curve) - min(equity_curve)) * 0.1),
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax1.annotate(f'Trough\n${equity_curve[max_dd_idx]:,.0f}',
                 xy=(max_dd_idx, equity_curve[max_dd_idx]),
                 xytext=(max_dd_idx, equity_curve[max_dd_idx] - (max(equity_curve) - min(equity_curve)) * 0.1),
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', color='red', lw=2))
    
    # Highlight ranges 600-700 and 800-900
    if len(equity_curve) > 700:
        ax1.axvspan(600, 700, alpha=0.1, color='blue', label='Range 600-700')
    if len(equity_curve) > 900:
        ax1.axvspan(800, 900, alpha=0.1, color='orange', label='Range 800-900')
    
    ax1.set_ylabel('Equity ($)', fontsize=12)
    ax1.set_title('Equity Curve with Max Drawdown', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # Plot drawdown curve
    ax2.fill_between(times, [0] * len(drawdowns), drawdowns, color='red', alpha=0.3, label='Drawdown')
    ax2.plot(times, drawdowns, 'r-', linewidth=1.5)
    ax2.axhline(y=max_dd, color='red', linestyle='--', linewidth=2, 
                label=f'Max DD: {max_dd:.2%}')
    ax2.scatter([max_dd_idx], [max_dd], color='red', s=100, zorder=5)
    
    # Highlight ranges
    if len(equity_curve) > 700:
        ax2.axvspan(600, 700, alpha=0.1, color='blue')
    if len(equity_curve) > 900:
        ax2.axvspan(800, 900, alpha=0.1, color='orange')
    
    ax2.set_xlabel('Time Index', fontsize=12)
    ax2.set_ylabel('Drawdown', fontsize=12)
    ax2.set_title('Drawdown Curve', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([min(drawdowns) * 1.1, 0.01])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ Saved visualization to {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    return max_dd, peak_idx_before_max_dd, max_dd_idx


def analyze_peaks_in_ranges(equity_curve):
    """Analyze peaks and drops in specific ranges."""
    print("=" * 70)
    print("PEAK-TO-TROUGH ANALYSIS BY RANGE")
    print("=" * 70)
    print()
    
    # Range 600-700
    if len(equity_curve) > 700:
        segment_600_700 = equity_curve[600:701]
        
        # Find all local peaks in this range
        peaks_600_700 = []
        for i in range(1, len(segment_600_700) - 1):
            if segment_600_700[i] > segment_600_700[i-1] and segment_600_700[i] > segment_600_700[i+1]:
                peaks_600_700.append((600 + i, segment_600_700[i]))
        
        # Also check boundaries
        if segment_600_700[0] > segment_600_700[1]:
            peaks_600_700.append((600, segment_600_700[0]))
        if segment_600_700[-1] > segment_600_700[-2]:
            peaks_600_700.append((700, segment_600_700[-1]))
        
        print("Range 600-700:")
        print(f"  Equity range: ${min(segment_600_700):,.2f} to ${max(segment_600_700):,.2f}")
        print(f"  Local peaks found: {len(peaks_600_700)}")
        
        # For each peak, find subsequent trough
        for peak_idx, peak_val in peaks_600_700:
            if peak_idx < 700:
                segment_after = equity_curve[peak_idx:701]
                trough_val = min(segment_after)
                trough_idx = peak_idx + segment_after.index(trough_val)
                drop = (peak_val - trough_val) / peak_val
                print(f"    Peak at {peak_idx}: ${peak_val:,.2f} → Trough at {trough_idx}: ${trough_val:,.2f} ({drop:.2%} drop)")
        print()
    
    # Range 800-900
    if len(equity_curve) > 900:
        segment_800_900 = equity_curve[800:901]
        
        # Find all local peaks in this range
        peaks_800_900 = []
        for i in range(1, len(segment_800_900) - 1):
            if segment_800_900[i] > segment_800_900[i-1] and segment_800_900[i] > segment_800_900[i+1]:
                peaks_800_900.append((800 + i, segment_800_900[i]))
        
        # Also check boundaries
        if segment_800_900[0] > segment_800_900[1]:
            peaks_800_900.append((800, segment_800_900[0]))
        if segment_800_900[-1] > segment_800_900[-2]:
            peaks_800_900.append((900, segment_800_900[-1]))
        
        print("Range 800-900:")
        print(f"  Equity range: ${min(segment_800_900):,.2f} to ${max(segment_800_900):,.2f}")
        print(f"  Local peaks found: {len(peaks_800_900)}")
        
        # For each peak, find subsequent trough
        for peak_idx, peak_val in peaks_800_900:
            if peak_idx < 900:
                segment_after = equity_curve[peak_idx:901]
                trough_val = min(segment_after)
                trough_idx = peak_idx + segment_after.index(trough_val)
                drop = (peak_val - trough_val) / peak_val
                print(f"    Peak at {peak_idx}: ${peak_val:,.2f} → Trough at {trough_idx}: ${trough_val:,.2f} ({drop:.2%} drop)")
        print()


if __name__ == "__main__":
    # Run simulation to get equity curve
    from scripts.analyze_drawdown import run_simulation_and_analyze
    
    print("Running simulation...")
    equity_curve, market_events = run_simulation_and_analyze()
    
    if not equity_curve:
        print("❌ No equity curve generated")
        exit(1)
    
    print()
    print("Creating visualization...")
    max_dd, peak_idx, trough_idx = visualize_drawdown_calculation(
        equity_curve, 
        save_path="drawdown_analysis.png"
    )
    
    print()
    analyze_peaks_in_ranges(equity_curve)
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Max drawdown: {max_dd:.2%}")
    print(f"Peak: ${max(equity_curve[:trough_idx+1]):,.2f} at index {peak_idx}")
    print(f"Trough: ${equity_curve[trough_idx]:,.2f} at index {trough_idx}")
    print()
    print("✅ Visualization saved to drawdown_analysis.png")
    print("   Check the image to see the drawdown calculation visually!")


