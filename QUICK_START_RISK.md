# Quick Start: Risk Manager Limits

## Current Limits (in `main.py` line 67-74)

```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,              # ← Order size: 10 shares
    max_drawdown=0.15,              # ← 15% max drawdown
    max_position_pct=0.30,          # ← Max 30% per position
    max_total_exposure_pct=1.0,     # ← Max 100% total exposure
    max_positions=None,             # ← No limit on # of positions
)
```

## How to Change Limits

### 1. Open `main.py`
### 2. Find line 67 (the `RealRiskManager` initialization)
### 3. Change the numbers:

**Example: Make it stricter**
```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.05,        # Changed: 5% instead of 15%
    max_position_pct=0.10,     # Changed: 10% instead of 30%
    max_total_exposure_pct=0.50,  # Changed: 50% instead of 100%
    max_positions=3,           # Changed: Max 3 positions
)
```

## What Each Limit Does

### `max_drawdown=0.15` (15%)
- **What**: Stops trading if portfolio drops 15% from peak
- **Example**: If you hit $11,000 then drop to $9,350 (15% down), trading stops
- **Change to**: `0.05` for strict, `0.25` for loose

### `max_position_pct=0.30` (30%)
- **What**: Max 30% of equity in one stock
- **Example**: With $10,000 equity, can't buy more than $3,000 of one stock
- **Change to**: `0.10` for diversified, `0.50` for concentrated

### `max_total_exposure_pct=1.0` (100%)
- **What**: Max 100% of equity invested total
- **Example**: With $10,000 equity, can invest up to $10,000 total
- **Change to**: `0.50` to keep 50% cash, `2.0` to allow leverage

### `max_positions=None`
- **What**: No limit on number of different stocks
- **Change to**: `3` to limit to 3 stocks, `5` for 5 stocks

### `fixed_quantity=10`
- **What**: Buy/sell 10 shares per order
- **Change to**: `100` for larger orders, `5` for smaller

## How It Works: Step by Step

When a strategy wants to trade:

```
1. Strategy generates SignalEvent (e.g., "BUY MSFT @ $200")
   ↓
2. Risk Manager checks:
   ✓ Drawdown OK? (not down more than 15%)
   ✓ Position size OK? (not more than 30% of equity)
   ✓ Total exposure OK? (not more than 100% invested)
   ✓ Have enough cash? (can afford the order)
   ✓ Position count OK? (not too many positions)
   ↓
3. If ALL checks pass:
   → Creates OrderEvent (trade approved)
   → Trade executes
   
   If ANY check fails:
   → Returns empty list (trade rejected)
   → Logs reason (e.g., "Drawdown -16% exceeds limit 15%")
```

## See It In Action

After changing limits, run:
```bash
python3 main.py
```

Look for:
- `--- RISK REJECTIONS ---` section at the end
- Warning messages like: `[RISK] REJECTED BUY MSFT @ 200: Drawdown -16% exceeds limit 15%`

## Quick Examples

**Very Conservative** (stops trading quickly):
```python
max_drawdown=0.05,        # Stop at 5% down
max_position_pct=0.10,    # Max 10% per stock
max_total_exposure_pct=0.50,  # Keep 50% cash
max_positions=3,          # Max 3 stocks
```

**Current Setting** (balanced):
```python
max_drawdown=0.15,        # Stop at 15% down
max_position_pct=0.30,    # Max 30% per stock
max_total_exposure_pct=1.0,  # Fully invested
max_positions=None,       # No limit
```

**Aggressive** (more risk):
```python
max_drawdown=0.25,        # Stop at 25% down
max_position_pct=0.50,    # Max 50% per stock
max_total_exposure_pct=2.0,  # Allow leverage
max_positions=None,       # No limit
```

