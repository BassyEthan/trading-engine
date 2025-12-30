# Trading Engine Dashboard

A simple web-based UI for viewing trading engine results.

## Installation

1. Install Streamlit:
```bash
pip install streamlit
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

```bash
streamlit run ui_dashboard.py
```

This will:
- Open a web browser automatically
- Run the simulation
- Display all results in a clean dashboard

## Features

The dashboard shows:

1. **Key Metrics** (top row):
   - Final Equity
   - Total Return (with percentage)
   - Max Drawdown
   - Sharpe Ratio

2. **Equity Curve & Drawdown** (interactive plot):
   - Portfolio equity over time
   - Drawdown visualization

3. **Portfolio State**:
   - Current cash
   - Open positions (with unrealized PnL)
   - Final equity

4. **Performance Metrics**:
   - Initial capital
   - Total return breakdown
   - Realized vs Unrealized PnL
   - Trading statistics (trades, win rate, avg PnL)

5. **Risk Metrics**:
   - Max drawdown
   - Sharpe ratio

6. **Risk Rejections**:
   - Total rejected trades
   - Breakdown by check type

## Notes

- The dashboard runs the simulation each time you load/refresh the page
- All data is computed in real-time
- The equity curve plot is interactive (zoom, pan, etc.)

