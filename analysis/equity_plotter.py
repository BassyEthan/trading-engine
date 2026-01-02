import matplotlib.pyplot as plt
from typing import Optional, List
from datetime import datetime
from analysis.equity_analyzer import EquityAnalyzer

def plot_equity(analyzer: EquityAnalyzer, show_price: bool = True, dates: Optional[List[datetime]] = None):
    fig, (ax_eq, ax_dd) = plt.subplots(
        2, 1,
        figsize = (14, 8),
        sharex = True,
        gridspec_kw = {"height_ratios": [3, 1]},
        constrained_layout = True
    )

    # Use dates for x-axis if available, otherwise use indices
    # Ensure dates are properly formatted datetime objects
    if dates and len(dates) == len(analyzer.equity_curve):
        # Verify dates are datetime objects, not timestamps
        x_data = []
        for d in dates:
            if isinstance(d, datetime):
                x_data.append(d)
            elif isinstance(d, (int, float)):
                # If it's a number, it might be a Unix timestamp - convert it
                try:
                    x_data.append(datetime.fromtimestamp(d))
                except (ValueError, OSError):
                    # If timestamp is too large/small, it might be in milliseconds or wrong
                    x_data.append(datetime.now())  # Fallback
            else:
                x_data.append(datetime.now())  # Fallback
        x_data = x_data
    else:
        x_data = range(len(analyzer.equity_curve))
    
    #equity
    ax_eq.plot(
        x_data,
        analyzer.equity_curve,
        color = "#111111",
        linewidth = 2.5,
        label = "Equity"
    )

    #optional price
    if show_price:
        prices = [e.price for e in analyzer.market_events]
        ax_eq.plot(
            x_data,
            prices,
            color="#7f7f7f",
            alpha = 0.35,
            linewidth = 1,
            label = "Price"
        )
        
    #holding periods
    for start, end in analyzer.holding_periods:
        if dates and start < len(dates) and end < len(dates):
            ax_eq.axvspan(dates[start], dates[end], color = "gray", alpha = 0.12)
        else:
            ax_eq.axvspan(start, end, color = "gray", alpha = 0.12)

    #entry markers with symbols
    for x, equity_val, symbol in analyzer.entry_markers:
        x_pos = dates[x] if dates and x < len(dates) else x
        ax_eq.scatter(
            x_pos,
            equity_val,
            color = "#2ca02c",
            marker = "^",
            s = 80,
            edgecolors = "black",
            linewidths = 1,
            zorder = 4,
            alpha = 0.7
        )
        ax_eq.text(
            x_pos,
            equity_val,
            symbol,
            fontsize = 8,
            ha = "center",
            va = "bottom",
            color = "#2ca02c",
            fontweight = "bold",
            bbox = dict(boxstyle = "round,pad=0.3", facecolor = "white", edgecolor = "#2ca02c", alpha = 0.8),
            zorder = 5
        )

    #trade annotations (exit PnL)
    for x, _, pnl in analyzer.trade_markers:
        x_pos = dates[x] if dates and x < len(dates) else x
        ax_eq.text(
            x_pos,
            analyzer.equity_curve[x],
            f"{pnl:+.0f}",
            fontsize = 9,
            ha = "center",
            va = "top",
            color = "#2ca02c" if pnl > 0 else "#d62728", 
            fontweight = "bold",
            zorder = 5
        )
    
    ax_eq.legend()
    ax_eq.set_ylabel("Equity")

    #Drawdown
    dd_x_data = dates if dates and len(dates) == len(analyzer.drawdown_curve) else range(len(analyzer.drawdown_curve))
    ax_dd.fill_between(
        dd_x_data,
        analyzer.drawdown_curve,
        0,
        color = "#d62728",
        alpha = 0.25
    )

    ax_dd.text(
        0.99,
        0.05,
        f"Max DD: {analyzer.max_drawdown:.2%}\nSharpe: {analyzer.sharpe:.2f}",
        transform = ax_dd.transAxes,
        ha = "right",
        va = "bottom",
        fontsize = 11,
        fontweight = "bold"
    )

    ax_dd.set_ylabel("Drawdown")
    ax_dd.set_xlabel("Date" if dates else "Time")
    
    # Format x-axis dates if available
    if dates:
        fig = ax_eq.figure
        fig.autofmt_xdate()  # Rotate date labels
        # Use DateFormatter for better date spacing
        from matplotlib.dates import DateFormatter, AutoDateLocator
        date_format = DateFormatter('%Y-%m-%d')
        ax_eq.xaxis.set_major_formatter(date_format)
        ax_dd.xaxis.set_major_formatter(date_format)
        # Auto-adjust date locator for better spacing
        ax_eq.xaxis.set_major_locator(AutoDateLocator())
        ax_dd.xaxis.set_major_locator(AutoDateLocator())

    plt.tight_layout()
    plt.show()
    