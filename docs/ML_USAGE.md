# How to Run and Test ML Strategy

## Quick Start

### 1. Compare ML Strategy vs Mean Reversion

Run the comparison script:

```bash
python3 scripts/test_ml_strategy.py
```

This will:
- Run backtest with ML strategy (logistic regression)
- Run backtest with mean reversion (baseline)
- Show side-by-side comparison of metrics
- Display winner

**Output includes:**
- Total return
- Number of trades
- Win rate
- Sharpe ratio
- Max drawdown

---

### 2. Test ML Strategy Only

If you want to test just the ML strategy:

```python
from scripts.test_ml_strategy import run_backtest, load_test_data
from strategies.ml_strategy import MLStrategy

# Load test data
data = load_test_data()

# Run backtest
results = run_backtest(
    data,
    MLStrategy,
    {'buy_threshold': 0.6, 'sell_threshold': 0.4},
    "ML Strategy"
)

print(f"Total Return: {results['total_return']:.2%}")
print(f"Number of Trades: {results['num_trades']}")
```

Or create a simple test script:

```python
# test_ml_only.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.test_ml_strategy import run_backtest, load_test_data
from strategies.ml_strategy import MLStrategy

data = load_test_data()
results = run_backtest(
    data,
    MLStrategy,
    {'buy_threshold': 0.55, 'sell_threshold': 0.45},  # More lenient thresholds
    "ML Strategy Test"
)
```

---

### 3. Adjust Thresholds

The ML strategy uses probability thresholds to generate signals:
- **BUY** when `prob_up > buy_threshold`
- **SELL** when `prob_up < sell_threshold`

**Current defaults:** `buy_threshold=0.6, sell_threshold=0.4`

**Problem:** These might be too strict (generates 0 trades)

**Solutions:**

#### Option A: More Lenient Thresholds
```python
# In test_ml_strategy.py, change:
ml_results = run_backtest(
    data,
    MLStrategy,
    {'buy_threshold': 0.55, 'sell_threshold': 0.45},  # More lenient
    "ML Strategy"
)
```

#### Option B: Even More Lenient
```python
{'buy_threshold': 0.52, 'sell_threshold': 0.48}  # Very lenient
```

#### Option C: Test Different Thresholds
```python
# Test multiple threshold combinations
thresholds = [
    (0.6, 0.4),   # Original (strict)
    (0.55, 0.45), # Medium
    (0.52, 0.48), # Lenient
    (0.51, 0.49), # Very lenient
]

for buy, sell in thresholds:
    results = run_backtest(
        data,
        MLStrategy,
        {'buy_threshold': buy, 'sell_threshold': sell},
        f"ML Strategy (buy={buy}, sell={sell})"
    )
    print(f"Buy={buy}, Sell={sell}: {results['num_trades']} trades, {results['total_return']:.2%} return")
```

---

### 4. Use in Main Trading Engine

To use ML strategy in `main.py`:

#### Step 1: Edit `main.py`

Find `STRATEGY_CONFIG` and add ML strategy:

```python
STRATEGY_CONFIG = {
    "AAPL": {
        "class": MLStrategy,  # Use ML strategy
        "params": {
            "model_path": "ml/models/price_direction_model.pkl",
            "buy_threshold": 0.55,
            "sell_threshold": 0.45,
        }
    },
    # ... other symbols
}
```

#### Step 2: Import MLStrategy

At the top of `main.py`, add:

```python
from strategies.ml_strategy import MLStrategy
```

#### Step 3: Run

```bash
python3 main.py
```

---

### 5. Debug: Why No Trades?

If ML strategy generates 0 trades, check:

#### A. Check Model Predictions

```python
from strategies.ml_strategy import MLStrategy
import json

# Load test data
with open("data/ml_training/test_data.json") as f:
    data = json.load(f)

# Create strategy
strategy = MLStrategy(
    model_path="ml/models/price_direction_model.pkl",
    symbol="AAPL",
    buy_threshold=0.6,
    sell_threshold=0.4,
)

# Check predictions on first few prices
prices = data["AAPL"][:20]
for i, price in enumerate(prices):
    from events.base import MarketEvent
    event = MarketEvent(timestamp=i, symbol="AAPL", price=price)
    signals = strategy.handle_market(event)
    
    # Get probability (you'll need to modify strategy to expose this)
    # Or check strategy.prices to see if features are being extracted
```

#### B. Check Feature Extraction

```python
from ml.feature_extractor import FeatureExtractor
import json

with open("data/ml_training/test_data.json") as f:
    data = json.load(f)

extractor = FeatureExtractor()
prices = data["AAPL"][:10]

features = extractor.extract_features(prices)
print(f"Features: {features}")
print(f"Feature names: {extractor.get_feature_names()}")
```

#### C. Check Model Output

```python
import pickle
import numpy as np

# Load model
with open("ml/models/price_direction_model.pkl", 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']
extractor = model_data['feature_extractor']

# Test on sample features
prices = [100, 101, 102, 99, 98, 100, 103]
features = extractor.extract_features(prices)

if features is not None:
    prob_up = model.predict_proba([features])[0][1]
    print(f"Probability of going up: {prob_up:.2%}")
    print(f"Would BUY: {prob_up > 0.6}")
    print(f"Would SELL: {prob_up < 0.4}")
```

---

### 6. Retrain Model

If you want to retrain with different parameters:

```bash
python3 ml/train_model.py
```

This will:
- Load training data from `data/ml_training/train_data.json`
- Extract features and labels
- Train logistic regression model
- Save to `ml/models/price_direction_model.pkl`
- Show training accuracy and feature importance

---

### 7. Test on Different Data

To test on different time periods:

```python
from data.loader import load_market_data
from scripts.test_ml_strategy import run_backtest
from strategies.ml_strategy import MLStrategy

# Load different data
data = load_market_data(
    "yahoo",
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# Run backtest
results = run_backtest(
    data,
    MLStrategy,
    {'buy_threshold': 0.55, 'sell_threshold': 0.45},
    "ML Strategy (2023)"
)
```

---

## Common Issues

### Issue: "No module named 'ml'"

**Fix:** Make sure you're running from project root:
```bash
cd /Users/ethanlung/Documents/projects/trading-engine
python3 scripts/test_ml_strategy.py
```

### Issue: "Model not found"

**Fix:** Train the model first:
```bash
python3 ml/train_model.py
```

### Issue: "0 trades generated"

**Causes:**
- Thresholds too strict (try 0.55/0.45 or 0.52/0.48)
- Model predictions too conservative
- Not enough price history for features

**Fix:** Lower thresholds or check model predictions

---

## Quick Reference

| Command | What It Does |
|---------|-------------|
| `python3 scripts/test_ml_strategy.py` | Compare ML vs mean reversion |
| `python3 ml/train_model.py` | Retrain the model |
| `python3 ml/prepare_data.py` | Check data preparation |
| `python3 main.py` | Run main engine (if ML added to config) |

---

## Next Steps

1. **Adjust thresholds** to generate more trades
2. **Test on different time periods** to check robustness
3. **Compare with other strategies** (momentum, breakout)
4. **Try different features** (add more technical indicators)
5. **Experiment with different models** (random forest, XGBoost)

