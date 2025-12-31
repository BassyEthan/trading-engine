"""
ML-based trading strategy.

Uses a pre-trained logistic regression model to predict price direction
and generate BUY/SELL signals.
"""

import sys
from pathlib import Path
from collections import deque
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pickle
import numpy as np
from core.logger import get_logger
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent
from ml.feature_extractor import FeatureExtractor

logger = get_logger("STRATEGY")


class MLStrategy(Strategy):
    """
    ML-based strategy using logistic regression to predict price direction.
    
    Behavior:
    - Maintains rolling window of prices
    - Extracts features from price history
    - Uses ML model to predict probability of price going up
    - BUY if prob_up > buy_threshold (default: 0.6)
    - SELL if prob_up < sell_threshold (default: 0.4)
    """
    
    def __init__(
        self,
        model_path: str,
        symbol: Optional[str] = None,
        buy_threshold: float = 0.6,
        sell_threshold: float = 0.4,
    ):
        """
        Initialize ML strategy.
        
        Args:
            model_path: Path to saved model pickle file
            symbol: Symbol to trade (None = trade all symbols)
            buy_threshold: Probability threshold for BUY signal (default: 0.6)
            sell_threshold: Probability threshold for SELL signal (default: 0.4)
        """
        super().__init__(symbol)
        
        # Load model
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.feature_extractor = model_data['feature_extractor']
        self.price_lookback = model_data['price_lookback']
        self.ma_window = model_data['ma_window']
        self.volatility_window = model_data['volatility_window']
        
        # Strategy parameters
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        
        # State tracking
        self.state = "FLAT"
        self.prices = deque(maxlen=max(self.price_lookback, self.ma_window, self.volatility_window) + 1)
        
        logger.info(
            f"MLStrategy initialized: "
            f"buy_threshold={buy_threshold:.2f}, "
            f"sell_threshold={sell_threshold:.2f}"
        )
    
    def handle_market(self, event: MarketEvent) -> List[SignalEvent]:
        """
        Generate signals based on ML predictions.
        
        Args:
            event: MarketEvent with price information
            
        Returns:
            List of SignalEvents (empty if no signal)
        """
        if self.symbol is not None and event.symbol != self.symbol:
            return []
        
        # Update price history
        self.prices.append(event.price)
        
        # Need enough data for feature extraction
        min_length = max(self.price_lookback, self.ma_window, self.volatility_window)
        if len(self.prices) < min_length:
            return []
        
        # Extract features
        features = self.feature_extractor.extract_features(list(self.prices))
        if features is None:
            return []
        
        # Predict probability of price going up
        prob_up = self.model.predict_proba([features])[0][1]
        
        signals = []
        
        # BUY signal: high probability of going up
        if prob_up > self.buy_threshold and self.state == "FLAT":
            self.state = "LONG"
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="BUY",
                price=event.price,
            ))
            logger.info(
                f"ML BUY {event.symbol} @ {event.price:.2f} "
                f"(prob_up={prob_up:.2%})"
            )
        
        # SELL signal: probability drops below buy threshold (model no longer confident it will go up)
        # This prevents getting stuck in LONG state when predictions stay above sell_threshold
        elif prob_up < self.buy_threshold and self.state == "LONG":
            self.state = "FLAT"
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="SELL",
                price=event.price,
            ))
            logger.info(
                f"ML SELL {event.symbol} @ {event.price:.2f} "
                f"(prob_up={prob_up:.2%}, dropped below buy_threshold={self.buy_threshold:.2%})"
            )
        
        return signals

