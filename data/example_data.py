"""
Example data files and sample CSV format.
This file shows the expected CSV format for market data.
"""

# Example CSV format for single symbol:
SINGLE_SYMBOL_CSV = """date,close
2024-01-01,100.50
2024-01-02,101.25
2024-01-03,99.75
2024-01-04,102.00
"""

# Example CSV format for multi-symbol:
MULTI_SYMBOL_CSV = """date,symbol,open,high,low,close,volume
2024-01-01,AAPL,100,102,99,101,1000000
2024-01-01,MSFT,200,202,198,201,2000000
2024-01-02,AAPL,101,103,100,102,1100000
2024-01-02,MSFT,201,203,199,202,2100000
"""

# Example: Create sample CSV files for testing
def create_sample_csv_files(directory: str = "data/sample/"):
    """Create sample CSV files for testing."""
    from pathlib import Path
    
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    
    # AAPL sample data
    aapl_data = """date,close
2024-01-01,150.00
2024-01-02,151.50
2024-01-03,149.75
2024-01-04,152.25
2024-01-05,153.00
"""
    (directory / "AAPL.csv").write_text(aapl_data)
    
    # MSFT sample data
    msft_data = """date,close
2024-01-01,380.00
2024-01-02,382.50
2024-01-03,378.75
2024-01-04,385.00
2024-01-05,387.50
"""
    (directory / "MSFT.csv").write_text(msft_data)
    
    print(f"Created sample CSV files in {directory}")

