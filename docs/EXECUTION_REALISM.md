# Execution Realism Guide

## What is Execution Realism?

Execution realism simulates the real-world costs and delays of trading. Your current `ExecutionHandler` is "perfect" - it fills orders instantly at the exact price you see. Real trading is not perfect.

## Why It Matters

**Without execution realism:**
- Your backtest shows +3% return
- But in real trading, you might only get +1%
- The difference is execution costs!

**With execution realism:**
- Backtest shows realistic performance
- You know what to expect in live trading
- Can optimize strategies for real-world conditions

## Components

### 1. Slippage

**What:** Difference between expected price and actual fill price

**Example:**
- You see MSFT at $200.00
- You place a market order to buy
- You actually fill at $200.15 (slippage = +$0.15)

**Causes:**
- Bid-ask spread (buy at ask, sell at bid)
- Market impact (your order moves price)
- Time delay (price changes while order executes)

**Typical:** 0.05% - 0.5% for liquid stocks

### 2. Bid-Ask Spread

**What:** Difference between buy and sell price

**Example:**
- MSFT bid: $199.95 (what you get selling)
- MSFT ask: $200.05 (what you pay buying)
- Spread: $0.10 (0.05%)

**You always pay the spread when trading**

**Typical:**
- Liquid stocks: 0.01% - 0.1%
- Illiquid stocks: 0.5% - 2%

### 3. Market Impact

**What:** Your order moves the price

**Example:**
- MSFT at $200.00
- You buy 10,000 shares (large order)
- Price moves to $200.50 (you moved the market)
- You fill at worse price

**Formula:** Impact = f(order_size, liquidity, volatility)

**Large orders = more impact**

### 4. Latency

**What:** Time delay between order and fill

**Example:**
- You see signal at 10:00:00.000
- Order sent at 10:00:00.050 (50ms delay)
- Fill received at 10:00:00.150 (100ms total)
- Price may have changed during delay

**Typical:** 10-200ms for electronic trading

### 5. Partial Fills

**What:** Order doesn't fill completely

**Example:**
- You want to buy 1,000 shares
- Only 600 shares available at your price
- You get partial fill, rest fills later (or not)

**Common for:**
- Large orders
- Limit orders
- Illiquid stocks

## How It Affects Your Results

### Current (Perfect Execution):
```
Buy 10 shares @ $200.00 → Fill @ $200.00
Sell 10 shares @ $201.00 → Fill @ $201.00
Profit: $10.00 (5%)
```

### With Execution Costs (Realistic):
```
Buy 10 shares @ $200.00 → Fill @ $200.20 (spread + slippage)
Sell 10 shares @ $201.00 → Fill @ $200.80 (spread + slippage)
Profit: $6.00 (3%)
Lost $4.00 (2%) to execution costs!
```

## Implementation Approaches

### 1. Simple Model (Start Here)
- Fixed spread (e.g., 0.1% for all stocks)
- Fixed slippage (e.g., 0.05% per trade)
- Simple and fast
- Good for initial testing

### 2. Realistic Model
- Dynamic spread (varies by stock, volatility)
- Size-based slippage (larger orders = more slippage)
- Time-of-day effects (worse at market open/close)
- More accurate but more complex

### 3. Advanced Model
- Order book simulation
- Volume-weighted average price (VWAP)
- Latency modeling
- Partial fills
- Most realistic but computationally expensive

## Real-World Examples

### Example 1: Small Order (10 shares)
- Stock: AAPL @ $150.00
- Spread: $0.10 (0.067%)
- Slippage: $0.05 (0.033%)
- **Total cost: $0.15 (0.1%)**

### Example 2: Medium Order (1,000 shares)
- Stock: AAPL @ $150.00
- Spread: $0.10 (0.067%)
- Slippage: $0.20 (0.133%) - more impact
- **Total cost: $0.30 (0.2%)**

### Example 3: Large Order (10,000 shares)
- Stock: AAPL @ $150.00
- Spread: $0.10 (0.067%)
- Slippage: $0.50 (0.333%) - significant impact
- **Total cost: $0.60 (0.4%)**

## Impact on Strategy Performance

Execution costs can significantly impact strategy returns:

- **High-frequency strategies:** Execution costs can eat 50%+ of profits
- **Mean reversion:** Small profits become losses with costs
- **Trend following:** Less affected (larger moves)
- **Position sizing:** Larger positions = more costs

## Best Practices

1. **Always include execution costs in backtests**
   - Otherwise you're overestimating performance

2. **Use realistic assumptions**
   - Don't assume perfect execution
   - Use industry-standard spreads/slippage

3. **Test sensitivity**
   - What if slippage is 2x worse?
   - Does strategy still work?

4. **Optimize for execution**
   - Smaller positions = less impact
   - Trade liquid stocks = lower costs
   - Avoid trading at market open/close

## Next Steps

See `docs/ROADMAP.md` Phase 2 for implementation details.

