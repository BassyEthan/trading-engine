# ML Strategy Issue Analysis

## Problem: Strategy Only Trades Once

### Root Cause Identified

**Issue 1: Model Predictions Are Too Conservative**
- Model predictions range from **48-55%** (mean: **51.4%**)
- **100% of predictions fall in the "no action" zone** (0.45-0.55)
- Model is barely better than random (51% vs 50%)

**Issue 2: State Management Bug**
- If strategy buys once (rare prediction > 0.55), it enters LONG state
- All subsequent predictions are 48-55%
- Since predictions never drop below 0.45, it **never sells**
- **Strategy gets stuck in LONG state forever**

### Evidence

From analysis of 225 predictions across all symbols:
- **0 predictions > 0.55** (would trigger BUY)
- **0 predictions < 0.45** (would trigger SELL)
- **225 predictions (100%) in 0.45-0.55 range** (no action)

### The Bug

```python
# Current logic:
if prob_up > self.buy_threshold and self.state == "FLAT":  # BUY
    self.state = "LONG"
    
elif prob_up < self.sell_threshold and self.state == "LONG":  # SELL
    self.state = "FLAT"
```

**Problem:**
- If it buys once (rare prob > 0.55), state becomes LONG
- Future predictions (48-55%) never trigger SELL (need < 0.45)
- Strategy stuck in LONG state

### Solutions

#### Option 1: Adjust Thresholds (Quick Fix)
Use thresholds closer to 50%:
```python
buy_threshold=0.52   # Instead of 0.55
sell_threshold=0.48  # Instead of 0.45
```

#### Option 2: Use Relative Thresholds (Better)
Instead of absolute thresholds, use relative to 50%:
```python
# BUY if prob_up > 0.50 + margin
# SELL if prob_up < 0.50 - margin
margin = 0.02  # 2% margin
buy_threshold = 0.50 + margin   # 0.52
sell_threshold = 0.50 - margin  # 0.48
```

#### Option 3: Fix State Management (Best)
Add a timeout or force exit:
```python
# Force SELL if in LONG too long without signal
# Or use opposite signal: if prob_up < 0.50 when LONG, sell
```

#### Option 4: Improve Model (Long-term)
- Model is too conservative (51% accuracy)
- Need better features or different model
- Current model barely beats random

### Recommended Fix

**Immediate:** Adjust thresholds to 0.52/0.48 or 0.51/0.49

**Better:** Change logic to allow selling when prob < 0.50 (not just < 0.45)

**Best:** Retrain model with better features or use different model type

