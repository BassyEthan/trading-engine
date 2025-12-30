# Real Risk Manager

The `RealRiskManager` enforces trading limits and rejects dangerous trades before execution.

## Features

### 1. Drawdown Limits
- **Max Drawdown**: Hard stop when drawdown exceeds threshold
- **Peak Tracking**: Automatically tracks peak equity
- **Real-time Check**: Evaluates drawdown at signal generation time

### 2. Position Size Limits
- **Absolute Limit**: Max position value (optional)
- **Percentage Limit**: Max position as % of equity (default: 20%)
- **Total Exposure**: Max total exposure across all positions (default: 100%)

### 3. Cash Availability
- **Buying Power**: Rejects BUY orders if insufficient cash
- **Automatic Check**: Validates cash before approving orders

### 4. Position Count Limits
- **Max Positions**: Optional limit on number of open positions
- **New Position Check**: Prevents opening too many positions

### 5. Rejection Logging
- **Detailed Logging**: Every rejection logged with reason
- **Summary Statistics**: Track rejections by check type and reason
- **Debugging**: Easy to see why trades were rejected

## Usage

### Basic Usage

```python
from risk.engine import RealRiskManager
from portfolio.state import PortfolioState

portfolio = PortfolioState(initial_cash=10000)
risk = RealRiskManager(
    portfolio=portfolio,
    fixed_quantity=10,
    max_drawdown=0.15,  # 15% max drawdown
    max_position_pct=0.30,  # Max 30% of equity in single position
    max_total_exposure_pct=1.0,  # Max 100% of equity in total positions
    max_positions=None,  # No limit on number of positions
)
```

### Parameters

- `portfolio` (PortfolioState): Portfolio state to check limits against
- `fixed_quantity` (int): Default order quantity (default: 10)
- `max_drawdown` (float): Max drawdown threshold (default: 0.10 = 10%)
- `max_position_size` (float, optional): Max absolute position value (None = no limit)
- `max_position_pct` (float): Max position as % of equity (default: 0.20 = 20%)
- `max_total_exposure_pct` (float): Max total exposure as % of equity (default: 1.0 = 100%)
- `max_positions` (int, optional): Max number of open positions (None = no limit)

### Integration

The risk manager is integrated into the event flow:

```
SignalEvent → RealRiskManager.handle_signal() → OrderEvent (if approved) or [] (if rejected)
```

## Example: Rejection Scenarios

### Scenario 1: Drawdown Exceeded

```python
# Portfolio has 15% drawdown
# Risk manager has 10% max drawdown limit
# Result: Trade REJECTED
# Reason: "Drawdown -15.00% exceeds limit 10.00%"
```

### Scenario 2: Position Too Large

```python
# Trying to buy $5,000 position
# Portfolio equity: $10,000
# Max position %: 20%
# Result: Trade REJECTED
# Reason: "Position 50.00% of equity exceeds limit 20.00%"
```

### Scenario 3: Insufficient Cash

```python
# Trying to buy 10 shares @ $100 = $1,000
# Available cash: $500
# Result: Trade REJECTED
# Reason: "Insufficient cash: need 1000.00, have 500.00"
```

### Scenario 4: Too Many Positions

```python
# Already have 5 open positions
# Max positions: 5
# Trying to open 6th position
# Result: Trade REJECTED
# Reason: "Position count 5 exceeds limit 5"
```

## Rejection Summary

After simulation, get rejection statistics:

```python
summary = risk.get_rejection_summary()
print(f"Total rejections: {summary['total']}")
print(f"By check type: {summary['by_check']}")
print(f"By reason: {summary['by_reason']}")
```

## Comparison: PassThrough vs RealRiskManager

| Feature | PassThroughRiskManager | RealRiskManager |
|---------|------------------------|-----------------|
| Drawdown Check | ❌ None | ✅ Enforced |
| Position Limits | ❌ None | ✅ Enforced |
| Cash Check | ❌ None | ✅ Enforced |
| Position Count | ❌ None | ✅ Optional |
| Rejection Logging | ❌ None | ✅ Detailed |
| Use Case | Testing | Production |

## Testing

Run the test suite:

```bash
python3 tests/test_risk_manager.py
```

Tests verify:
- Drawdown limit enforcement
- Cash availability checks
- Position size limit enforcement
- Rejection logging

## Notes

1. **Drawdown Check Timing**: Drawdown is checked at signal generation time, not during holding period. This prevents entering new trades when already in drawdown.

2. **Peak Equity Tracking**: The risk manager automatically tracks peak equity and updates it when new highs are reached.

3. **Current Equity Calculation**: The risk manager calculates current equity on-the-fly using:
   - Cash
   - Position values (quantity × latest price)

4. **Rejection Behavior**: When a trade is rejected, the risk manager returns an empty list `[]` instead of an `OrderEvent`. This prevents the trade from being executed.

5. **Logging**: All rejections are logged at WARNING level with detailed reasons for easy debugging.

## Future Enhancements

See `docs/ROADMAP.md` for planned improvements:
- Leverage limits
- Daily loss limits
- Circuit breakers
- Per-trade max loss limits
- Risk limit alerts (80%, 90%, 95%)

