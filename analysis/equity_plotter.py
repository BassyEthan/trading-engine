import matplotlib.pyplot as plt
from analysis.equity_analyzer import EquityAnalyzer

def plot_equity(analyzer: EquityAnalyzer, show_price: bool = True):
    fig, (ax_eq, ax_dd) = plt.subplots(
        2, 1,
        figsize = (14, 8),
        sharex = True,
        gridspec_kw = {"height_ratios": [3, 1]},
        constrained_layout = True
    )

    #equity
    ax_eq.plot(
        analyzer.equity_curve,
        color = "#111111",
        linewidth = 2.5,
        label = "Equity"
    )

    #optional price
    if show_price:
        prices = [e.price for e in analyzer.market_events]
        ax_eq.plot(
            prices,
            color="#7f7f7f",
            alpha = 0.35,
            linewidth = 1,
            label = "Price"
        )
        
    #holding periods
    for start, end in analyzer.holding_periods:
        ax_eq.axvspan(start, end, color = "gray", alpha = 0.12)

    #trade annotations
    for x, _, pnl in analyzer.trade_markers:
        ax_eq.text(
            x,
            analyzer.equity_curve[x],
            f"{pnl:+.0f}",
            fontsize = 9,
            ha = "center",
            va = "bottom",
            color = "#2ca02c" if pnl > 0 else "#d62728", 
            fontweight = "bold",
            zorder = 5
        )
    
    ax_eq.legend()
    ax_eq.set_ylabel("Equity")

    #Drawdown
    ax_dd.fill_between(
        range(len(analyzer.drawdown_curve)),
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
    ax_dd.set_xlabel("Time")

    plt.tight_layout()
    plt.show()
    