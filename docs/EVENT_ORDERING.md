# Event Ordering and Processing

## Current Architecture

The trading engine uses a **FIFO event queue** that processes events in the order they arrive. This is simple and efficient, but has implications for event ordering.

### How It Works Now

```
1. MarketEvent t=12 (MSFT) → generates SignalEvent → OrderEvent → FillEvent
2. MarketEvent t=13 (APPL) → (already in queue, processed next)
3. MarketEvent t=14 (MSFT) → generates SignalEvent → Risk check
4. FillEvent t=12 (MSFT) → (processed later, after t=14)
```

**Problem**: The risk manager at t=14 might check drawdown before the t=12 fill has been processed, leading to incorrect risk assessments.

## The Issue

When events are generated during processing (e.g., MarketEvent → SignalEvent → OrderEvent → FillEvent), the generated events are added to the end of the queue. This means:

- Events at timestamp T might not be fully processed before events at T+1
- Risk checks might see stale portfolio state
- Equity calculations during live processing might be incorrect

**Note**: The equity curve reconstruction in `main.py` already handles this by replaying events in chronological order, but this doesn't help during live event processing.

## Solutions

### Option 1: Timestamp-Ordered Processing (Recommended for Long-Term)

**Pros:**
- ✅ Guarantees correctness - all events at timestamp T are fully processed before T+1
- ✅ Risk manager always sees current portfolio state
- ✅ No edge cases or subtle bugs
- ✅ Production-ready architecture

**Cons:**
- ❌ More complex implementation
- ❌ Requires priority queue or sorting
- ❌ Slightly more overhead

**Implementation Approach:**
1. Use a priority queue (heap) instead of FIFO queue
2. Sort by `(timestamp, event_type_priority)` 
3. Process all events at timestamp T before moving to T+1
4. Ensure all generated events at T are processed before T+1

### Option 2: Keep Current Approach (Acceptable for Now)

**Pros:**
- ✅ Simple and fast
- ✅ Works correctly in most cases
- ✅ Easy to understand

**Cons:**
- ❌ Edge cases where risk checks see stale state
- ❌ Requires careful handler ordering
- ❌ Not production-ready for real trading

**Mitigations:**
- Register portfolio handler first (already done)
- Update portfolio price in risk manager (already done)
- Document the limitation
- Use equity curve reconstruction for final analysis (already done)

## Recommendation

**For a long-term project, I recommend Option 1 (Timestamp-Ordered Processing).**

### Why?

1. **Correctness**: Trading systems must be correct. Subtle ordering bugs can lead to:
   - Incorrect risk checks
   - Wrong position sizing
   - Incorrect PnL calculations

2. **Scalability**: As you add more features (multiple symbols, real-time data, backtesting), event ordering becomes more critical.

3. **Maintainability**: Explicit ordering is easier to reason about and debug.

4. **Production Readiness**: Real trading systems need deterministic event processing.

### Implementation Priority

- **High Priority**: If you're planning to use this for real trading or complex strategies
- **Medium Priority**: If you're building a research/backtesting tool
- **Low Priority**: If this is just for learning and simple demos

## Implementation Status

✅ **IMPLEMENTED**: Timestamp-ordered processing is now the default!

The system now uses `PriorityEventQueue` which:
- Processes events in strict timestamp order
- Ensures all events at timestamp T are fully processed before T+1
- Guarantees risk manager sees correct portfolio state
- Uses event type priorities within the same timestamp:
  - MarketEvent = 0 (highest priority - updates prices first)
  - SignalEvent = 1 (generated from market events)
  - OrderEvent = 2 (created from signals)
  - FillEvent = 3 (completes the cycle)

### Benefits

- ✅ **Correctness**: Risk checks always see current portfolio state
- ✅ **Deterministic**: Same events always process in same order
- ✅ **Production-ready**: No edge cases or subtle bugs
- ✅ **Verified**: Risk manager now correctly rejects trades when drawdown > limit

### Migration

The old `EventQueue` (FIFO) is still available for backward compatibility, but `main.py` now uses `PriorityEventQueue` by default. All new code should use `PriorityEventQueue`.

