# Risk Manager Guide - How It Works

## Current Limits (in `main.py`)

```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,              # Order size: 10 shares per trade
    max_drawdown=0.15,              # 15% max drawdown (stops trading if down 15%)
    max_position_pct=0.30,          # Max 30% of equity in single position
    max_total_exposure_pct=1.0,     # Max 100% of equity in total positions
    max_positions=None,             # No limit on number of positions
)
```

## How to Change Limits

### Step 1: Open `main.py`

Find the `RealRiskManager` initialization (around line 67):

```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.15,  # ← Change this
    max_position_pct=0.30,  # ← Change this
    max_total_exposure_pct=1.0,  # ← Change this
    max_positions=None,  # ← Change this
)
```

### Step 2: Adjust the Values

**Example: Stricter Limits**
```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.05,        # 5% max drawdown (very strict)
    max_position_pct=0.10,    # Max 10% per position (very conservative)
    max_total_exposure_pct=0.50,  # Max 50% total exposure
    max_positions=3,          # Max 3 open positions
)
```

**Example: Looser Limits**
```python
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.25,        # 25% max drawdown (more risk tolerance)
    max_position_pct=0.50,    # Max 50% per position (concentrated)
    max_total_exposure_pct=2.0,  # Max 200% (allows leverage)
    max_positions=None,       # No limit on positions
)
```

## How Each Limit Works

### 1. `max_drawdown` (Drawdown Limit)

**What it does**: Stops trading when portfolio drops too much from peak.

**How it works**:
1. Tracks peak equity (highest equity ever reached)
2. Calculates current drawdown: `(current_equity - peak_equity) / peak_equity`
3. Rejects trades if drawdown exceeds limit

**Example**:
- Start: $10,000 equity
- Peak: $11,000 equity (new high)
- Current: $9,350 equity
- Drawdown: (9,350 - 11,000) / 11,000 = -15%
- If `max_drawdown=0.15`: ✅ Trade allowed (exactly at limit)
- If `max_drawdown=0.10`: ❌ Trade rejected (exceeds 10% limit)

**When to use**:
- `0.05` (5%): Very conservative, stops trading quickly
- `0.10` (10%): Moderate risk control
- `0.15` (15%): Current setting, balanced
- `0.20` (20%): More risk tolerance

### 2. `max_position_pct` (Single Position Limit)

**What it does**: Prevents putting too much money in one stock.

**How it works**:
1. Calculates order value: `quantity × price`
2. Calculates as % of equity: `order_value / current_equity`
3. Rejects if exceeds limit

**Example**:
- Current equity: $10,000
- Trying to buy: 10 shares @ $500 = $5,000
- Position %: 5,000 / 10,000 = 50%
- If `max_position_pct=0.30`: ❌ Rejected (50% > 30%)
- If `max_position_pct=0.50`: ✅ Allowed (50% ≤ 50%)

**When to use**:
- `0.10` (10%): Very diversified, max 10% per stock
- `0.20` (20%): Diversified portfolio
- `0.30` (30%): Current setting, moderate concentration
- `0.50` (50%): Concentrated positions

### 3. `max_total_exposure_pct` (Total Exposure Limit)

**What it does**: Limits total money invested across all positions.

**How it works**:
1. Sums value of all current positions
2. Adds new position value if buying
3. Calculates as % of equity
4. Rejects if exceeds limit

**Example**:
- Current equity: $10,000
- Current positions: $3,000 (APPL) + $2,000 (MSFT) = $5,000 total
- Trying to buy: $4,000 (TSLA)
- Total exposure: $5,000 + $4,000 = $9,000
- Exposure %: 9,000 / 10,000 = 90%
- If `max_total_exposure_pct=1.0`: ✅ Allowed (90% ≤ 100%)
- If `max_total_exposure_pct=0.80`: ❌ Rejected (90% > 80%)

**When to use**:
- `0.50` (50%): Keep 50% cash, very conservative
- `0.80` (80%): Keep 20% cash buffer
- `1.0` (100%): Current setting, fully invested
- `1.5` (150%): Allows leverage (short selling)

### 4. `max_positions` (Position Count Limit)

**What it does**: Limits number of different stocks you can hold.

**How it works**:
1. Counts current open positions
2. If buying new symbol (not already held), checks count
3. Rejects if would exceed limit

**Example**:
- Current positions: APPL, MSFT, TSLA (3 positions)
- Trying to buy: GOOGL (new position)
- If `max_positions=3`: ❌ Rejected (would be 4 positions)
- If `max_positions=5`: ✅ Allowed (would be 4 positions)

**When to use**:
- `None`: No limit (current setting)
- `3`: Focused portfolio, max 3 stocks
- `5`: Moderate diversification
- `10`: Well diversified

### 5. `fixed_quantity` (Order Size)

**What it does**: How many shares to buy/sell per order.

**How it works**:
- All orders use this fixed quantity
- Affects position size calculations

**Example**:
- `fixed_quantity=10`: Buy 10 shares per order
- `fixed_quantity=100`: Buy 100 shares per order (larger positions)

## Step-by-Step: How a Trade Gets Checked

When a strategy generates a `SignalEvent`, here's what happens:

```
1. SignalEvent arrives at risk manager
   ↓
2. Check Drawdown Limit
   - Calculate current equity
   - Calculate drawdown from peak
   - If drawdown > limit → REJECT
   ↓
3. Check Position Size Limit
   - Calculate order value (quantity × price)
   - Check if exceeds max_position_pct
   - Check if exceeds max_position_size (if set)
   - If exceeds → REJECT
   ↓
4. Check Total Exposure Limit
   - Sum all current positions
   - Add new position if buying
   - Check if exceeds max_total_exposure_pct
   - If exceeds → REJECT
   ↓
5. Check Cash Availability
   - If BUY: Check if cash >= order_value
   - If insufficient → REJECT
   ↓
6. Check Position Count Limit
   - Count current positions
   - If buying new symbol, check if count < max_positions
   - If exceeds → REJECT
   ↓
7. All checks passed → APPROVE
   - Create OrderEvent
   - Return [OrderEvent]
   
   OR
   
   Any check failed → REJECT
   - Log rejection reason
   - Return [] (empty list)
```

## Real Example Walkthrough

Let's trace a real trade:

**Scenario**: Strategy wants to buy MSFT @ $200

**Current State**:
- Equity: $10,000
- Cash: $8,000
- Positions: APPL (value: $2,000)
- Peak equity: $10,500
- Current drawdown: -4.76%

**Risk Manager Settings**:
```python
max_drawdown=0.15
max_position_pct=0.30
max_total_exposure_pct=1.0
fixed_quantity=10
```

**Step-by-Step Check**:

1. **Drawdown Check**:
   - Current drawdown: -4.76%
   - Limit: 15%
   - ✅ PASS (4.76% < 15%)

2. **Position Size Check**:
   - Order value: 10 × $200 = $2,000
   - Position %: $2,000 / $10,000 = 20%
   - Limit: 30%
   - ✅ PASS (20% < 30%)

3. **Total Exposure Check**:
   - Current exposure: $2,000 (APPL)
   - New exposure: $2,000 + $2,000 = $4,000
   - Exposure %: $4,000 / $10,000 = 40%
   - Limit: 100%
   - ✅ PASS (40% < 100%)

4. **Cash Check**:
   - Required: $2,000
   - Available: $8,000
   - ✅ PASS ($8,000 >= $2,000)

5. **Position Count Check**:
   - Current: 1 position (APPL)
   - Would be: 2 positions (APPL + MSFT)
   - Limit: None (no limit)
   - ✅ PASS

**Result**: ✅ **APPROVED** - OrderEvent created

## Changing Limits: Quick Reference

| Limit | Current | Stricter | Looser |
|-------|---------|----------|--------|
| `max_drawdown` | 0.15 (15%) | 0.05 (5%) | 0.25 (25%) |
| `max_position_pct` | 0.30 (30%) | 0.10 (10%) | 0.50 (50%) |
| `max_total_exposure_pct` | 1.0 (100%) | 0.50 (50%) | 2.0 (200%) |
| `max_positions` | None | 3 | None |

## Testing Your Limits

After changing limits, run:

```bash
python3 main.py
```

Look for:
- `--- RISK REJECTIONS ---` section
- Rejection reasons in logs
- How many trades were rejected

To see rejections in action, try:
- Very strict drawdown (0.05) with HoldThroughCrashStrategy
- Very strict position size (0.10) with large orders
- Low cash scenario

## Common Configurations

### Conservative (Low Risk)
```python
max_drawdown=0.05,
max_position_pct=0.10,
max_total_exposure_pct=0.50,
max_positions=5,
```

### Balanced (Current)
```python
max_drawdown=0.15,
max_position_pct=0.30,
max_total_exposure_pct=1.0,
max_positions=None,
```

### Aggressive (High Risk)
```python
max_drawdown=0.25,
max_position_pct=0.50,
max_total_exposure_pct=2.0,
max_positions=None,
```

