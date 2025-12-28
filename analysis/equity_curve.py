import matplotlib.pyplot as plt
from typing import List
from events.base import MarketEvent, FillEvent

def plot_equity_curve(
    market_events: List[MarketEvent],
    fills: List[FillEvent],
    initial_cash: float,
):
    prices = []
    equity = []
    trade_annotations = [] # (x,y,pnl)
    open_price = None
    open_qty = None

    buy_x, buy_y = [], []
    sell_x, sell_y = [], []

    holding_periods = []
    current_entry = None

    cash = initial_cash
    position_qty = 0
    fill_idx = 0

    
    #streaming through market events
    for i, event in enumerate(market_events):
        prices.append(event.price)

        #apply fills that occured at this time index
        while fill_idx < len(fills) and fills[fill_idx].timestamp <= event.timestamp:
            fill = fills[fill_idx]
            if fill.direction == "BUY":
                cash -= fill.fill_price * fill.quantity
                position_qty += fill.quantity
                buy_x.append(i)
                buy_y.append(fill.fill_price)

                open_price = fill.fill_price
                open_qty = fill.quantity

                if current_entry is None:
                    current_entry = i

            elif fill.direction == "SELL":
                cash += fill.fill_price * fill.quantity
                position_qty -= fill.quantity
                sell_x.append(i)
                sell_y.append(fill.fill_price)

                if open_price is not None:
                    pnl = (fill.fill_price - open_price) * fill.quantity
                    trade_annotations.append((i, fill.fill_price, pnl))
                    open_price = None
                    open_qty = None

                if position_qty == 0 and current_entry is not None:
                    holding_periods.append((current_entry, i))
                    current_entry = None

            fill_idx += 1
        
        equity.append(cash + position_qty * event.price)
    
    #computing drawdown
    peak = equity[0]
    drawdown = []

    for value in equity:
        peak = max(peak, value)
        drawdown.append((value - peak) / peak)
    max_drawdown = min(drawdown)

    #computing returns for Sharpe
    returns = []
    for i in range(1, len(equity)):
        r = (equity[i] - equity[i-1] / equity[i-1])
        returns.append(r)
    
    #Sharpe ratio
    import numpy as np # type: ignore
    if len(returns) > 1 and np.std(returns) != 0:
        sharpe = np.mean(returns) / np.std(returns)
    else:
        sharpe = 0.0



    #handle remaining fills that occured at or after the last market event
    last_i = len(market_events) - 1
    while fill_idx < len(fills):
        fill = fills[fill_idx]
        if fill.direction == "BUY":
            buy_x.append(last_i)
            buy_y.append(fill.fill_price)
            open_price = fill.fill_price
            open_qty = fill.quantity

            if current_entry is None:
                current_entry = last_i

        elif fill.direction == "SELL":
            sell_x.append(last_i)
            sell_y.append(fill.fill_price)

            if open_price is not None:
                pnl = (fill.fill_price - open_price) * fill.quantity
                trade_annotations.append((last_i, fill.fill_price, pnl))
                open_price = None
                open_qty = None

            if position_qty == 0 and current_entry is not None:
                holding_periods.append((current_entry, last_i))
                current_entry = None

        fill_idx += 1
    
    if current_entry is not None:
        holding_periods.append((current_entry, last_i))
    
    #plot
    fig, (ax1, ax3) = plt.subplots(
        2,1,
        figsize = (12,8),
        sharex = True,
        gridspec_kw = {"height_ratios": [3,1]}
        
        
    )

    #shade holding periods
    for start, end in holding_periods:
        ax1.axvspan(
            start,
            end,
            color = "gray",
            alpha = 0.15, 
            zorder = 0
        )

    ax1.plot(prices, label = "Price", color = "blue", alpha = 0.6)
    ax1.scatter(
        buy_x, 
        buy_y, 
        color = "green", 
        marker = "^", # type: ignore[arg-type]
        label = "BUY", 
        s = 100,
        edgecolors="black",
        linewidths=1.2,
        zorder = 2,
    )
    ax1.scatter(
        sell_x, 
        sell_y, 
        color = "red", 
        marker = "v",  # type: ignore[arg-type]
        label = "SELL", 
        s = 100,
        edgecolors = "black",
        linewidths = 1.2,
        zorder = 2,
    )

    for x, y, pnl in trade_annotations:
        ax1.annotate(
            f"{pnl:+.0f}",
            xy = (x, y),
            xytext = (0, 28),
            textcoords = "offset points",
            ha = "center",
            va = "bottom",
            fontsize = 11,
            color = "green" if pnl > 0 else "red",
            fontweight = "bold",
            arrowprops = dict(
                arrowstyle = "->",
                color = "green" if pnl > 0 else "red",
                lw = 1
            ),
            zorder = 5
        )

    ax1.set_ylabel("Price")
    ax1.legend(loc = "upper left")

    ax2 = ax1.twinx()
    ax2.plot(equity, label = "Equity", color = "black", linewidth = 2)
    ax2.set_ylabel("Equity")
    ax2.legend(loc = "upper right")

    ax3.fill_between(
        range(len(drawdown)),
        drawdown,
        0,
        color = "red",
        alpha = 0.3
    )

    #sharpe tells you how much risk you're taking
    ax3.text(
        0.99,
        0.15,
        f"Sharpe: {sharpe:.2f}",
        transform = ax3.transAxes,
        ha = "right",
        va = "bottom",
        fontsize = 11,
        color = "black",
        fontweight = "bold"
    )

    #drawdown tells you how far you were from your peak
    ax3.text(
        0.99,
        0.05,
        f"Max Drawdown: {max_drawdown:.2%}",
        transform = ax3.transAxes,
        ha = "right",
        va = "bottom",
        fontsize = 11,
        color = "red",
        fontweight = "bold"


    )
    ax3.set_ylabel("Drawdown")
    ax3.set_ylim(min(drawdown) * 1.1, 0)
    ax3.set_xlabel("Time")

    plt.title("Equity Curve with Trade Markers")
    plt.tight_layout()
    plt.show()

        