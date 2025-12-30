# Why Max Drawdown Can Exceed the Risk Limit

## The Question

**"I set `max_drawdown=0.15` (15%), but my simulation shows 19% max drawdown. Is this a bug?"**

## The Answer: No, this is correct behavior!

### How the Risk Manager Works

The risk manager checks drawdown **at signal generation time** (when a strategy wants to enter a new trade). It does **NOT** prevent holding existing positions through crashes.

### What Happened in Your Simulation

1. **t=12**: Strategy generates BUY signal for MSFT @ $200
   - Risk manager checks drawdown: ~0% (no drawdown yet)
   - ✅ **APPROVED** (0% < 15% limit)
   - Position opened: 10 shares of MSFT @ $200

2. **t=13-22**: **Holding the position** through market events
   - t=13: Price = $202, Equity = $10,020 (small gain)
   - t=14: Price crashes to $1, Equity = $8,010 (**-20% drawdown!**)
   - t=15-21: Price volatility continues
   - t=22: Price = $200, Equity = $10,000

3. **t=22**: Strategy generates SELL signal
   - Risk manager checks drawdown: ~0% (recovered)
   - ✅ **APPROVED**
   - Position closed

### Why the 19% Drawdown Occurred

The 19% drawdown happened **while holding an existing position**, not when generating a new signal. The risk manager:
- ✅ **Prevents entering new trades** when drawdown > 15%
- ❌ **Does NOT force exit** of existing positions

This is by design - the risk manager acts as a **gate for new trades**, not a position manager.

## Visual Timeline

```
t=12:  BUY signal → Drawdown: 0%  → ✅ APPROVED → Position opened
       ↓
t=13:  Price $202 → Equity $10,020 → Drawdown: 0%
       ↓
t=14:  Price $1   → Equity $8,010  → Drawdown: -20% ⚠️
       (But no new signal, so no check!)
       ↓
t=15-21: Holding through volatility
       ↓
t=22:  SELL signal → Drawdown: 0%  → ✅ APPROVED → Position closed
```

## Is This a Bug?

**No!** This is the intended behavior by design:

1. **Risk manager prevents new risk** (entering trades when in drawdown)
2. **It doesn't manage existing positions** (that's the strategy's job)
3. **Checks only at signal time** (for simplicity and performance)

The 19% drawdown occurred because:
- You were already in a position when the crash happened
- No new signals were generated during the crash (so no risk check)
- The strategy held through the crash (by design of HoldThroughCrashStrategy)

**This is the correct and intended behavior** - the risk manager acts as a gate for new trades, not a position manager.

## If You Want Stricter Control

If you want the risk manager to also prevent holding positions through excessive drawdown, you would need to:

1. **Add position monitoring** (check drawdown on every MarketEvent, not just signals)
2. **Force exits** (generate SELL signals when drawdown exceeds limit)

This would require modifying the risk manager to:
- Monitor positions continuously
- Generate exit signals when limits are exceeded
- Act as both a gate AND a position manager

## Current Behavior Summary

| Scenario | Risk Manager Action |
|----------|-------------------|
| New BUY signal when drawdown = 5% | ✅ APPROVED (5% < 15%) |
| New BUY signal when drawdown = 16% | ❌ REJECTED (16% > 15%) |
| Holding position, drawdown = 20% | ✅ Position continues (no new signal) |
| New SELL signal when drawdown = 20% | ✅ APPROVED (SELLs don't increase risk) |

## Testing This

To see the risk manager actually reject trades due to drawdown:

1. Set a very strict limit: `max_drawdown=0.05` (5%)
2. Use HoldThroughCrashStrategy that holds through crashes
3. After the crash, try to generate another BUY signal
4. The risk manager should reject it

Example:
```python
risk = RealRiskManager(
    portfolio=portfolio,
    max_drawdown=0.05,  # Very strict: 5%
    ...
)
```

With this setting, if you try to enter a new trade after the crash (when drawdown is -20%), it will be rejected.

## Conclusion

The 19% max drawdown is **not a bug**. It's the result of:
- Holding a position through a crash (strategy decision)
- Risk manager only checking at signal generation time
- No new signals generated during the crash period

The risk manager is working correctly - it prevents **entering new trades** when in drawdown, but doesn't force **exiting existing positions**.

