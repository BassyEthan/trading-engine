"""
Feature extraction for ML models.

Extracts features from price history to use as inputs for ML models.
"""

import numpy as np
from collections import deque
from typing import List, Optional


class FeatureExtractor:
    """
    Extracts features from price history.
    
    Features:
    - Last N prices (price_lookback)
    - Moving average (ma_window)
    - Price return (current vs previous)
    - Volatility (rolling standard deviation)
    """
    
    def __init__(
        self,
        price_lookback: int = 3,
        ma_window: int = 5,
        volatility_window: int = 5,
    ):
        """
        Initialize feature extractor.
        
        Args:
            price_lookback: Number of recent prices to include (default: 3)
            ma_window: Window size for moving average (default: 5)
            volatility_window: Window size for volatility calculation (default: 5)
        """
        self.price_lookback = price_lookback
        self.ma_window = ma_window
        self.volatility_window = volatility_window
    
    def extract_features(self, prices: List[float]) -> Optional[np.ndarray]:
        """
        Extract features from a list of prices.
        
        Args:
            prices: List of prices in chronological order (most recent last)
            
        Returns:
            Feature vector as numpy array, or None if not enough data
        """
        if len(prices) < max(self.price_lookback, self.ma_window, self.volatility_window):
            return None
        
        features = []
        
        # Feature 1-3: Last N prices (normalized by most recent price)
        recent_prices = prices[-self.price_lookback:]
        current_price = prices[-1]
        
        # Normalize prices by current price (makes features scale-invariant)
        normalized_prices = [p / current_price for p in recent_prices]
        features.extend(normalized_prices)
        
        # Feature 4: Moving average (normalized)
        ma_window_prices = prices[-self.ma_window:]
        ma = np.mean(ma_window_prices)
        normalized_ma = ma / current_price
        features.append(normalized_ma)
        
        # Feature 5: Price return (current vs previous)
        if len(prices) >= 2:
            return_pct = (prices[-1] - prices[-2]) / prices[-2]
            features.append(return_pct)
        else:
            features.append(0.0)
        
        # Feature 6: Volatility (rolling standard deviation of returns)
        if len(prices) >= self.volatility_window + 1:
            returns = []
            for i in range(len(prices) - self.volatility_window, len(prices)):
                if i > 0:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)
            
            if returns:
                volatility = np.std(returns)
                features.append(volatility)
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        return np.array(features)
    
    def get_feature_names(self) -> List[str]:
        """Get names of features for interpretability."""
        names = []
        
        # Last N prices
        for i in range(self.price_lookback):
            names.append(f"price_{i+1}_ago")
        
        # Moving average
        names.append(f"ma_{self.ma_window}")
        
        # Return
        names.append("return")
        
        # Volatility
        names.append(f"volatility_{self.volatility_window}")
        
        return names
    
    def get_num_features(self) -> int:
        """Get total number of features."""
        return self.price_lookback + 3  # prices + MA + return + volatility


def extract_features_from_sequence(
    prices: List[float],
    price_lookback: int = 3,
    ma_window: int = 5,
    volatility_window: int = 5,
) -> tuple[List[np.ndarray], List[int]]:
    """
    Extract features and labels from a price sequence.
    
    This function slides a window through the price sequence, extracting
    features at each point and creating labels (1 = price goes up, 0 = price goes down).
    
    Args:
        prices: List of prices in chronological order
        price_lookback: Number of recent prices to include
        ma_window: Window size for moving average
        volatility_window: Window size for volatility
        
    Returns:
        Tuple of (features_list, labels_list)
        - features_list: List of feature vectors
        - labels_list: List of labels (1 = up, 0 = down)
    """
    extractor = FeatureExtractor(
        price_lookback=price_lookback,
        ma_window=ma_window,
        volatility_window=volatility_window,
    )
    
    features_list = []
    labels_list = []
    
    # Need at least (max_window + 1) prices to create one feature/label pair
    min_length = max(price_lookback, ma_window, volatility_window) + 1
    
    if len(prices) < min_length:
        return [], []
    
    # Slide window through prices
    for i in range(min_length - 1, len(prices) - 1):
        # Extract features from prices up to index i
        price_window = prices[:i+1]
        features = extractor.extract_features(price_window)
        
        if features is not None:
            # Label: 1 if next price > current price, 0 otherwise
            current_price = prices[i]
            next_price = prices[i + 1]
            label = 1 if next_price > current_price else 0
            
            features_list.append(features)
            labels_list.append(label)
    
    return features_list, labels_list

