"""
Data preparation for ML training.

Converts raw price data to features and labels for model training.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import numpy as np
from typing import Dict, List, Tuple

from ml.feature_extractor import extract_features_from_sequence


def load_training_data(data_path: str) -> Dict[str, List[float]]:
    """
    Load training data from JSON file.
    
    Args:
        data_path: Path to JSON file with format {"SYMBOL": [prices...]}
        
    Returns:
        Dictionary mapping symbol to list of prices
    """
    with open(data_path, 'r') as f:
        data = json.load(f)
    return data


def prepare_features_and_labels(
    data: Dict[str, List[float]],
    price_lookback: int = 3,
    ma_window: int = 5,
    volatility_window: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert price data to features and labels.
    
    Args:
        data: Dictionary mapping symbol to list of prices
        price_lookback: Number of recent prices to include
        ma_window: Window size for moving average
        volatility_window: Window size for volatility
        
    Returns:
        Tuple of (X, y) where:
        - X: Feature matrix (n_samples, n_features)
        - y: Label array (n_samples,) with values 0 or 1
    """
    all_features = []
    all_labels = []
    
    print("Preparing features and labels from price data...")
    print(f"  Symbols: {list(data.keys())}")
    
    for symbol, prices in data.items():
        if not prices:
            print(f"  ⚠️  Skipping {symbol}: no data")
            continue
        
        # Extract features and labels for this symbol
        features, labels = extract_features_from_sequence(
            prices,
            price_lookback=price_lookback,
            ma_window=ma_window,
            volatility_window=volatility_window,
        )
        
        if features:
            all_features.extend(features)
            all_labels.extend(labels)
            print(f"  ✅ {symbol}: {len(features)} samples")
        else:
            print(f"  ⚠️  {symbol}: not enough data for features")
    
    if not all_features:
        raise ValueError("No features extracted from data. Check data format and length.")
    
    # Convert to numpy arrays
    X = np.array(all_features)
    y = np.array(all_labels)
    
    print(f"\n✅ Total samples: {len(X)}")
    print(f"   Features shape: {X.shape}")
    print(f"   Labels: {np.sum(y)} up, {len(y) - np.sum(y)} down")
    print(f"   Up ratio: {np.mean(y):.2%}")
    
    return X, y


def prepare_training_data(
    train_data_path: str,
    price_lookback: int = 3,
    ma_window: int = 5,
    volatility_window: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load and prepare training data.
    
    Args:
        train_data_path: Path to training data JSON file
        price_lookback: Number of recent prices to include
        ma_window: Window size for moving average
        volatility_window: Window size for volatility
        
    Returns:
        Tuple of (X_train, y_train)
    """
    print("=" * 70)
    print("PREPARING TRAINING DATA")
    print("=" * 70)
    print()
    
    # Load data
    print(f"Loading data from: {train_data_path}")
    data = load_training_data(train_data_path)
    
    # Prepare features and labels
    X, y = prepare_features_and_labels(
        data,
        price_lookback=price_lookback,
        ma_window=ma_window,
        volatility_window=volatility_window,
    )
    
    return X, y


if __name__ == "__main__":
    # Test with training data
    train_path = Path("data/ml_training/train_data.json")
    
    if train_path.exists():
        X, y = prepare_training_data(str(train_path))
        print()
        print("=" * 70)
        print("✅ DATA PREPARATION COMPLETE")
        print("=" * 70)
        print(f"Ready for training: {X.shape[0]} samples, {X.shape[1]} features")
    else:
        print(f"❌ Training data not found: {train_path}")

