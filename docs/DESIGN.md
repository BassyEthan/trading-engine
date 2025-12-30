SYSTEM GOAL:

The system is a model agnostic, which means it doesn't care what is being traded, event-trading (e.g. new price tick, new order book udpate, risk limit overruled) system that will simulate how actual trading decks work. It takes market data as time-ordered events (live input). Additionally, it generates trading signals via pluggable strategies - this means that the strategy isn't hard-coded in the engine. And, before a trade happens, the system asks if we exceeded max position size, violated leverage limits, or increase drawdown beyond tolerance. If any, the trade will be rejected. The model will also simulate realistic execution with latency and slippage. There is also a single source of truth for portfolio state, meaning that there is only one place that tracks cash, positions, realized PnL and unrealized PnL, and exposure. After, each trade will be logged - but also why a signal was generated, why a trade was allowed or blocked, or what risk rule triggered. 

The focus of this model isn't to predict prices, find alpha, or beat the market, because models are very fragile, markets are non-stationary, and past performance lies, but rather because we want to focus on handling uncertainity, robust behavior when assumptions break. 

This project will teach me how a mediocre strategy and excellent execution can survive. On the other hand, a great strategy but poor execution will fail. 
It will also teach me:
    Systems thinking
    Async architecture understanding
    State management under uncertainity
    Real-world trading realism
    Engineering discipline over hype


Important definitions:
    Cash - amount of money you have currently not invested
    Positions - what you current own or owe in each instrument ("APPL": 10, "TSLA": -5)
    PnL - Profit n Loss
    Realized PnL - Profit or loss that is locked in because a position was closed. 
    Unrealized PnL - Profit or loss on open positions, based on current market prices
    Exposure - How much market risk you are actually taking; how sensitive are you to price movements?
    Alpha - returns that cannot be explained by market exposure or risk alone. If the market is flat, but I keep making money - that is strong alpha

    Only realized PnL affects cash permanantly 

FIXED CONSTRAINTS:

Language: Python
Market: historical replay (no live feeds yet)
Execution: paper trading only
Strategy: trivial (e.g. momentum threshold)

Core Components (list only)
Event queue / dispatcher
Strategy (signal generator)
Risk engine
Execution simulator
Portfolio state

Invariants 
Examples:
Cash can never go negative
Positions only change on fills
Risk engine is the final gate before execution
Portfolio state is the single source of truth