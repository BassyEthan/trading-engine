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

                if current_entry is None:
                    current_entry = i

            elif fill.direction == "SELL":
                cash += fill.fill_price * fill.quantity
                position_qty -= fill.quantity
                sell_x.append(i)
                sell_y.append(fill.fill_price)

                if position_qty == 0 and current_entry is not None:
                    holding_periods.append((current_entry, i))
                    current_entry = None

            fill_idx += 1
        
        equity.append(cash + position_qty * event.price)
        
    #handle remaining fills that occured at or after the last market event
    last_i = len(market_events) - 1
    while fill_idx < len(fills):
        fill = fills[fill_idx]
        if fill.direction == "BUY":
            buy_x.append(last_i)
            buy_y.append(fill.fill_price)

            if current_entry is None:
                current_entry = last_i

        elif fill.direction == "SELL":
            sell_x.append(last_i)
            sell_y.append(fill.fill_price)

            if position_qty == 0 and current_entry is not None:
                holding_periods.append((current_entry, last_i))
                current_entry = None

        fill_idx += 1
    
    if current_entry is not None:
        holding_periods.append((current_entry, last_i))
    
    #plot
    fig, ax1 = plt.subplots(figsize = (12,6))

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
        marker = "^", 
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
        marker = "v",   
        label = "SELL", 
        s = 100,
        edgecolors = "black",
        linewidths = 1.2,
        zorder = 2,
    )
    ax1.set_ylabel("Price")
    ax1.legend(loc = "upper left")

    ax2 = ax1.twinx()
    ax2.plot(equity, label = "Equity", color = "black", linewidth = 2)
    ax2.set_ylabel("Equity")
    ax2.legend(loc = "upper right")

    plt.title("Equity Curve with Trade Markers")
    plt.tight_layout()
    plt.show()

        