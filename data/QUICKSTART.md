# Quick Start: Using Real Market Data

## Option 1: CSV Files (Easiest)

1. **Create a data directory:**
   ```bash
   mkdir -p data
   ```

2. **Create CSV files** (one per symbol):
   ```csv
   date,close
   2024-01-01,150.00
   2024-01-02,151.50
   2024-01-03,149.75
   ```
   Save as `data/AAPL.csv`, `data/MSFT.csv`, etc.

3. **Update main.py:**
   ```python
   USE_FAKE_DATA = False
   CSV_DATA_DIR = "data/"
   ```

4. **Run:**
   ```bash
   python3 main.py
   ```

## Option 2: Yahoo Finance (Real-time)

1. **Install yfinance:**
   ```bash
   pip install yfinance
   ```

2. **Update main.py:**
   ```python
   USE_FAKE_DATA = False
   YAHOO_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
   YAHOO_START_DATE = "2024-01-01"
   YAHOO_END_DATE = "2024-12-31"
   ```

3. **Run:**
   ```bash
   python3 main.py
   ```

## Getting Sample Data

### Download from Yahoo Finance:
```python
import yfinance as yf

# Download data
ticker = yf.Ticker("AAPL")
df = ticker.history(start="2024-01-01", end="2024-12-31")

# Save to CSV
df[['Close']].to_csv('data/AAPL.csv', header=['close'])
```

### Or use the example generator:
```python
from data.example_data import create_sample_csv_files
create_sample_csv_files("data/sample/")
```

## CSV Format

**Single Symbol (recommended):**
```csv
date,close
2024-01-01,100.50
2024-01-02,101.25
2024-01-03,99.75
```

**Multi-Symbol:**
```csv
date,symbol,open,high,low,close,volume
2024-01-01,AAPL,100,102,99,101,1000000
2024-01-01,MSFT,200,202,198,201,2000000
```

## Notes

- Prices should be in chronological order
- The engine uses sequential timestamps (0, 1, 2, ...) for events
- Make sure symbol names in CSV match your strategy config
- CSV files are loaded automatically from the directory

