# Data Collection Guide for ML Models

## Quick Answer

**Yes, get data first!** You need historical data to:
1. **Train** your ML models
2. **Test** your models (out-of-sample)
3. **Compare** ML vs rule-based strategies

---

## Recommended Data Sources

### 1. **Yahoo Finance** ⭐ **BEST FOR STARTING**

**Why:**
- Free
- Easy to use (you already have `yfinance` installed)
- Good historical coverage (10+ years for most stocks)
- No API keys needed

**How to get:**
```python
from data.loader import load_market_data

# Get 2 years of data for training
train_data = load_market_data(
    "yahoo",
    symbols=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
    start_date="2022-01-01",
    end_date="2023-12-31"
)

# Get 1 year for testing (out-of-sample)
test_data = load_market_data(
    "yahoo",
    symbols=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**What you get:**
- Daily closing prices
- Automatically sorted chronologically
- Multiple symbols at once

**Limitations:**
- Rate limits (don't fetch too frequently)
- Some symbols may have gaps
- Delayed data (15-20 min delay for free tier)

---

### 2. **CSV Files** (If you have them)

**Why:**
- Full control over data
- Can include custom features
- No API rate limits
- Works offline

**How to get:**
- Download from financial data providers
- Export from trading platforms
- Use free datasets (see below)

**Format:**
```csv
date,close
2022-01-01,100.50
2022-01-02,101.25
2022-01-03,99.75
```

**Usage:**
```python
from data.loader import load_market_data

data = load_market_data(
    "csv_dir",
    directory="data/",
    price_column="close"
)
```

---

## How Much Data Do You Need?

### Minimum Requirements

**For Training:**
- **At least 1 year** of daily data (252 trading days)
- **More is better**: 2-3 years gives you ~500-750 samples
- **Multiple symbols**: 5-10 symbols for diversity

**For Testing:**
- **At least 6 months** out-of-sample (separate from training)
- **Same symbols** as training (for fair comparison)

### Recommended Split

```
Total: 3 years of data
├── Training: 2 years (2022-2023)
└── Testing: 1 year (2024)
```

**Why this split?**
- Enough data to learn patterns
- Recent test data (current market conditions)
- Walk-forward validation (train on past, test on future)

---

## What Symbols Should You Use?

### Start with Liquid Stocks (Recommended)

**Large Cap Tech:**
- `AAPL` (Apple)
- `MSFT` (Microsoft)
- `GOOGL` (Google)
- `AMZN` (Amazon)
- `META` (Meta/Facebook)

**Why these?**
- High liquidity (tight spreads)
- Good historical data
- Less prone to manipulation
- Representative of market

**Other Options:**
- `TSLA` (Tesla) - volatile, good for testing
- `NVDA` (NVIDIA) - tech, trending
- `SPY` (S&P 500 ETF) - market proxy

### How Many Symbols?

**Start with 3-5 symbols:**
- Easier to manage
- Faster to download/process
- Enough diversity for initial testing

**Scale up later:**
- 10-20 symbols for more robust models
- Different sectors for diversification

---

## Data Collection Script

Here's a script to download and save data for ML training:

```python
"""
Script to download and save historical data for ML training.
"""

from data.loader import load_market_data
import json
from pathlib import Path

# Configuration
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
TRAIN_START = "2022-01-01"
TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"
TEST_END = "2024-12-31"

OUTPUT_DIR = Path("data/ml_training/")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_and_save():
    """Download data and save to JSON files."""
    
    print("📥 Downloading training data...")
    train_data = load_market_data(
        "yahoo",
        symbols=SYMBOLS,
        start_date=TRAIN_START,
        end_date=TRAIN_END
    )
    
    print("📥 Downloading test data...")
    test_data = load_market_data(
        "yahoo",
        symbols=SYMBOLS,
        start_date=TEST_START,
        end_date=TEST_END
    )
    
    # Save training data
    train_file = OUTPUT_DIR / "train_data.json"
    with open(train_file, 'w') as f:
        json.dump(train_data, f, indent=2)
    print(f"✅ Saved training data to {train_file}")
    print(f"   Symbols: {list(train_data.keys())}")
    print(f"   Data points per symbol: {[len(prices) for prices in train_data.values()]}")
    
    # Save test data
    test_file = OUTPUT_DIR / "test_data.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    print(f"✅ Saved test data to {test_file}")
    print(f"   Symbols: {list(test_data.keys())}")
    print(f"   Data points per symbol: {[len(prices) for prices in test_data.values()]}")
    
    return train_data, test_data

if __name__ == "__main__":
    train_data, test_data = download_and_save()
```

**Run it:**
```bash
python scripts/download_ml_data.py
```

---

## Alternative: Free Datasets

If you want pre-packaged data:

### 1. **Yahoo Finance Historical Data**
- Already integrated in your system
- Free, no signup needed

### 2. **Kaggle Datasets**
- Search: "stock market data", "S&P 500 historical"
- Free, pre-cleaned
- Download as CSV

### 3. **Quandl (now Nasdaq Data Link)**
- Free tier available
- Good quality data
- Requires API key (free)

### 4. **Alpha Vantage**
- Free tier: 5 API calls/min, 500 calls/day
- Good for small datasets
- Requires API key (free)

---

## Data Quality Checklist

Before using data for ML:

✅ **Chronological order**: Prices should be sorted by date
✅ **No missing values**: Fill gaps or remove incomplete periods
✅ **No duplicates**: Check for duplicate dates
✅ **Reasonable prices**: Check for outliers (e.g., $0.01 or $1,000,000)
✅ **Consistent frequency**: Daily data should be daily (not mix daily/weekly)
✅ **Enough history**: At least 1 year, preferably 2-3 years

---

## Recommended Workflow

### Step 1: Download Data (Now)
```bash
# Create script to download
python scripts/download_ml_data.py
```

### Step 2: Inspect Data
```python
import json
from pathlib import Path

# Load data
with open("data/ml_training/train_data.json") as f:
    data = json.load(f)

# Check
for symbol, prices in data.items():
    print(f"{symbol}: {len(prices)} prices")
    print(f"  First: ${prices[0]:.2f}, Last: ${prices[-1]:.2f}")
```

### Step 3: Train/Test Split
- Use 2022-2023 for training
- Use 2024 for testing
- **Never** train on test data!

### Step 4: Feature Engineering
- Extract features (MA, volatility, returns)
- Create labels (next price direction)
- Save processed data

### Step 5: Model Training
- Train on training set
- Validate on validation set (subset of training)
- Test on test set (only once!)

---

## Quick Start Command

**Download data right now:**

```python
from data.loader import load_market_data

# Get 2 years for training
train = load_market_data(
    "yahoo",
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date="2022-01-01",
    end_date="2023-12-31"
)

# Get 1 year for testing
test = load_market_data(
    "yahoo",
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"Training: {len(train)} symbols, {sum(len(p) for p in train.values())} total prices")
print(f"Testing: {len(test)} symbols, {sum(len(p) for p in test.values())} total prices")
```

---

## Summary

1. **Get data first** ✅
2. **Use Yahoo Finance** (easiest, free)
3. **Get 2-3 years** of data
4. **Split train/test** (2022-2023 train, 2024 test)
5. **Start with 3-5 symbols** (AAPL, MSFT, GOOGL)
6. **Save data** to JSON/CSV for reuse

**Next step:** Once you have data, we'll build the ML training pipeline!

