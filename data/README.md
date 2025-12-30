# Market Data Loading

The trading engine supports multiple data sources for market data.

## Data Sources

### 1. Fake Data (Default)
For testing and development. Configured in `main.py`:
```python
USE_FAKE_DATA = True
```

### 2. CSV Files
Load from CSV files in a directory.

**Single Symbol Format:**
```csv
date,close
2024-01-01,100.50
2024-01-02,101.25
2024-01-03,99.75
```

**Multi-Symbol Format:**
```csv
date,symbol,open,high,low,close,volume
2024-01-01,AAPL,100,102,99,101,1000000
2024-01-01,MSFT,200,202,198,201,2000000
```

**Usage:**
1. Create a `data/` directory
2. Place CSV files there (named by symbol, e.g., `AAPL.csv`)
3. Set in `main.py`:
   ```python
   USE_FAKE_DATA = False
   CSV_DATA_DIR = "data/"
   ```

### 3. Yahoo Finance API
Fetch real-time or historical data from Yahoo Finance.

**Requirements:**
```bash
pip install yfinance
```

**Usage:**
Set in `main.py`:
```python
USE_FAKE_DATA = False
YAHOO_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
YAHOO_START_DATE = "2024-01-01"
YAHOO_END_DATE = "2024-12-31"
```

## Example: Creating Sample Data

```python
from data.example_data import create_sample_csv_files

# Create sample CSV files
create_sample_csv_files("data/sample/")
```

## Data Format

The data loader expects:
- **Input**: Dict mapping symbol to list of prices
- **Output**: Same format (for compatibility)
- **Prices**: Should be in chronological order

The trading engine will create `MarketEvent`s from the price data, using sequential timestamps (0, 1, 2, ...).

## Future Enhancements

- Alpha Vantage API support
- Polygon.io API support
- Real-time data streaming
- OHLCV data support (currently uses close price)
- Multiple timeframe support

