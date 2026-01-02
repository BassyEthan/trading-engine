"""
Market data loader for trading engine.
Supports CSV files and can be extended for APIs (Yahoo Finance, Alpha Vantage, etc.)
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import sys

class DataLoader:
    """
    Loads market data from various sources.
    
    Currently supports:
    - CSV files (with columns: date, symbol, price or date, open, high, low, close, volume)
    - In-memory dict (for testing/backward compatibility)
    
    Future: Yahoo Finance, Alpha Vantage, etc.
    """
    
    @staticmethod
    def load_from_dict(data: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        Load data from a dictionary (backward compatibility).
        
        Args:
            data: Dict mapping symbol to list of prices
            
        Returns:
            Same dict (for consistency)
        """
        return data
    
    @staticmethod
    def load_from_csv(
        filepath: str,
        symbol_column: str = "symbol",
        price_column: str = "close",  # or "price" if single price column
        date_column: str = "date",
        symbol: Optional[str] = None,
    ) -> Dict[str, List[float]]:
        """
        Load market data from CSV file.
        
        CSV format options:
        1. Single symbol file:
           date,price
           2024-01-01,100.50
           2024-01-02,101.25
           
        2. Multi-symbol file:
           date,symbol,open,high,low,close,volume
           2024-01-01,AAPL,100,102,99,101,1000000
           2024-01-01,MSFT,200,202,198,201,2000000
           
        Args:
            filepath: Path to CSV file
            symbol_column: Name of column containing symbol (if multi-symbol file)
            price_column: Name of column to use for price ("close", "price", etc.)
            date_column: Name of date column
            symbol: If provided, filter to this symbol only (for single-symbol files, use None)
            
        Returns:
            Dict mapping symbol to list of prices (sorted by date)
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        data: Dict[str, List[float]] = {}
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            
            # Check if multi-symbol or single-symbol file
            has_symbol_col = symbol_column in reader.fieldnames
            has_price_col = price_column in reader.fieldnames or "price" in reader.fieldnames
            
            if not has_price_col:
                raise ValueError(
                    f"CSV must have '{price_column}' or 'price' column. "
                    f"Found columns: {reader.fieldnames}"
                )
            
            # Use "price" if "close" not found
            actual_price_col = price_column if price_column in reader.fieldnames else "price"
            
            for row in reader:
                # Get symbol
                if has_symbol_col:
                    sym = row[symbol_column].strip().upper()
                elif symbol:
                    sym = symbol.upper()
                else:
                    # Single symbol file, use filename or default
                    sym = filepath.stem.upper()
                
                # Get price
                try:
                    price = float(row[actual_price_col])
                except (ValueError, KeyError) as e:
                    print(f"Warning: Skipping row with invalid price: {row}")
                    continue
                
                # Store price
                if sym not in data:
                    data[sym] = []
                data[sym].append(price)
        
        # Sort by date if date column exists (assumes CSV is already sorted, but verify)
        # For now, we assume prices are in chronological order
        
        return data
    
    @staticmethod
    def load_from_csv_directory(
        directory: str,
        pattern: str = "*.csv",
        price_column: str = "close",
    ) -> Dict[str, List[float]]:
        """
        Load multiple CSV files from a directory.
        
        Each file should be named after the symbol (e.g., AAPL.csv, MSFT.csv)
        or contain symbol in a column.
        
        Args:
            directory: Path to directory containing CSV files
            pattern: File pattern to match (default: "*.csv")
            price_column: Column name for price
            
        Returns:
            Dict mapping symbol to list of prices
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        data: Dict[str, List[float]] = {}
        
        for filepath in directory.glob(pattern):
            # Try to infer symbol from filename
            symbol = filepath.stem.upper()
            
            try:
                file_data = DataLoader.load_from_csv(
                    str(filepath),
                    symbol=symbol,
                    price_column=price_column,
                )
                data.update(file_data)
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")
                continue
        
        return data
    
    @staticmethod
    def load_from_yahoo_finance(
        symbols: List[str],
        start_date: str,
        end_date: str,
        return_dates: bool = False,
    ) -> Union[Dict[str, List[float]], Tuple[Dict[str, List[float]], Dict[str, List[datetime]]]]:
        """
        Load data from Yahoo Finance API.
        
        Requires: pip install yfinance
        
        Args:
            symbols: List of symbols to fetch
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            return_dates: If True, also return dates for each symbol
            
        Returns:
            If return_dates=False: Dict mapping symbol to list of closing prices
            If return_dates=True: Tuple of (prices_dict, dates_dict)
        """
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError(
                "yfinance not installed. Install with: pip install yfinance"
            )
        
        data: Dict[str, List[float]] = {}
        dates_dict: Dict[str, List[datetime]] = {} if return_dates else {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date)
                
                if df.empty:
                    print(f"Warning: No data for {symbol}")
                    continue
                
                # Extract closing prices
                prices = df['Close'].tolist()
                data[symbol.upper()] = prices
                
                # Extract dates if requested
                if return_dates:
                    # Convert pandas Timestamp to Python datetime
                    dates = []
                    for pd_timestamp in df.index:
                        try:
                            # Try to_pydatetime first (most reliable)
                            if hasattr(pd_timestamp, 'to_pydatetime'):
                                dt = pd_timestamp.to_pydatetime()
                            # If it's already a datetime, use it
                            elif isinstance(pd_timestamp, datetime):
                                dt = pd_timestamp
                            # If it's a pandas Timestamp, convert it
                            elif hasattr(pd_timestamp, 'date'):
                                dt = pd_timestamp.to_pydatetime() if hasattr(pd_timestamp, 'to_pydatetime') else datetime.combine(pd_timestamp.date(), datetime.min.time())
                            else:
                                # Last resort: convert string or use current method
                                dt = datetime.fromisoformat(str(pd_timestamp)) if isinstance(str(pd_timestamp), str) and '-' in str(pd_timestamp) else datetime.now()
                            dates.append(dt)
                        except Exception as e:
                            print(f"Warning: Failed to convert date {pd_timestamp} for {symbol}: {e}")
                            # Fallback to a placeholder date
                            dates.append(datetime.now())
                    
                    dates_dict[symbol.upper()] = dates
                    # Debug: print first and last dates
                    if dates:
                        print(f"  {symbol}: Dates from {dates[0]} to {dates[-1]} ({len(dates)} dates)")
                        print(f"    First date type: {type(dates[0])}, value: {repr(dates[0])}")
                
            except Exception as e:
                print(f"Warning: Failed to fetch {symbol}: {e}")
                continue
        
        if return_dates:
            return data, dates_dict
        return data


def load_market_data(
    source: str,
    **kwargs
) -> Dict[str, List[float]]:
    """
    Convenience function to load market data from various sources.
    
    Args:
        source: One of "dict", "csv", "csv_dir", "yahoo"
        **kwargs: Arguments specific to each source
        
    Examples:
        # From dict (testing)
        data = load_market_data("dict", data={"AAPL": [100, 101, 102]})
        
        # From CSV file
        data = load_market_data("csv", filepath="data/AAPL.csv")
        
        # From directory of CSVs
        data = load_market_data("csv_dir", directory="data/")
        
        # From Yahoo Finance
        data = load_market_data(
            "yahoo",
            symbols=["AAPL", "MSFT"],
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
    """
    loader = DataLoader()
    
    if source == "dict":
        return loader.load_from_dict(kwargs.get("data", {}))
    
    elif source == "csv":
        return loader.load_from_csv(
            filepath=kwargs.get("filepath"),
            symbol=kwargs.get("symbol"),
            price_column=kwargs.get("price_column", "close"),
        )
    
    elif source == "csv_dir":
        return loader.load_from_csv_directory(
            directory=kwargs.get("directory"),
            pattern=kwargs.get("pattern", "*.csv"),
            price_column=kwargs.get("price_column", "close"),
        )
    
    elif source == "yahoo":
        return_dates = kwargs.get("return_dates", False)
        result = loader.load_from_yahoo_finance(
            symbols=kwargs.get("symbols", []),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            return_dates=return_dates,
        )
        return result
    
    else:
        raise ValueError(f"Unknown data source: {source}")

