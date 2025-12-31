"""
Script to download and save historical data for ML training.

Usage:
    python scripts/download_ml_data.py
"""

import sys
import os
from pathlib import Path

# Add project root to path so we can import data module
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.loader import load_market_data
import json

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
    
    print("=" * 70)
    print("DOWNLOADING DATA FOR ML TRAINING")
    print("=" * 70)
    print()
    
    print(f"📥 Downloading training data ({TRAIN_START} to {TRAIN_END})...")
    try:
        train_data = load_market_data(
            "yahoo",
            symbols=SYMBOLS,
            start_date=TRAIN_START,
            end_date=TRAIN_END
        )
        print(f"✅ Downloaded {len(train_data)} symbols")
    except Exception as e:
        print(f"❌ Error downloading training data: {e}")
        return None, None
    
    print()
    print(f"📥 Downloading test data ({TEST_START} to {TEST_END})...")
    try:
        test_data = load_market_data(
            "yahoo",
            symbols=SYMBOLS,
            start_date=TEST_START,
            end_date=TEST_END
        )
        print(f"✅ Downloaded {len(test_data)} symbols")
    except Exception as e:
        print(f"❌ Error downloading test data: {e}")
        return None, None
    
    print()
    print("=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)
    
    # Training data summary
    print("\n📊 Training Data:")
    for symbol, prices in train_data.items():
        if prices:
            first_price = prices[0]
            last_price = prices[-1]
            return_pct = ((last_price - first_price) / first_price) * 100
            print(f"   {symbol:6s}: {len(prices):4d} prices | "
                  f"${first_price:7.2f} → ${last_price:7.2f} "
                  f"({return_pct:+6.2f}%)")
        else:
            print(f"   {symbol:6s}: No data")
    
    # Test data summary
    print("\n📊 Test Data:")
    for symbol, prices in test_data.items():
        if prices:
            first_price = prices[0]
            last_price = prices[-1]
            return_pct = ((last_price - first_price) / first_price) * 100
            print(f"   {symbol:6s}: {len(prices):4d} prices | "
                  f"${first_price:7.2f} → ${last_price:7.2f} "
                  f"({return_pct:+6.2f}%)")
        else:
            print(f"   {symbol:6s}: No data")
    
    # Save training data
    train_file = OUTPUT_DIR / "train_data.json"
    with open(train_file, 'w') as f:
        json.dump(train_data, f, indent=2)
    print(f"\n💾 Saved training data to: {train_file}")
    
    # Save test data
    test_file = OUTPUT_DIR / "test_data.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    print(f"💾 Saved test data to: {test_file}")
    
    print()
    print("=" * 70)
    print("✅ DONE! Data ready for ML training.")
    print("=" * 70)
    
    return train_data, test_data

if __name__ == "__main__":
    train_data, test_data = download_and_save()

