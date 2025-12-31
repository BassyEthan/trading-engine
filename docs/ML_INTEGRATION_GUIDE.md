# ML Models Integration Guide

## Philosophy & Alignment

Your trading engine's core philosophy is:
> "A mediocre strategy with excellent execution can survive. A great strategy with poor execution will fail."

**Key Question**: How do ML models fit into this philosophy?

### The Good
- ML can identify patterns humans miss
- Can adapt to different market regimes
- Can process many features simultaneously
- Can learn from historical data

### The Bad
- Models are fragile (overfitting, data leakage)
- Markets are non-stationary (past patterns don't predict future)
- Complex models are hard to debug
- May ignore execution costs in predictions

### The Reality
- ML is a tool, not a silver bullet
- Execution quality still matters more than prediction accuracy
- Simple models often outperform complex ones
- Testing and validation are critical

---

## Where ML Fits in Your Architecture

### Current Event Flow
```
MarketEvent → Strategy → SignalEvent → Risk → OrderEvent → Execution → FillEvent
```

### ML Integration Points

#### 1. **Strategy Layer** (Signal Generation) ⭐ **RECOMMENDED START**
- ML model predicts: BUY, SELL, or HOLD
- Input: Historical prices, features (MA, volatility, etc.)
- Output: SignalEvent
- **Pros**: Natural fit, easy to test
- **Cons**: Model needs to be trained offline

#### 2. **Risk Layer** (Risk Prediction)
- ML model predicts: Drawdown risk, volatility
- Input: Current portfolio state, market conditions
- Output: Risk adjustments (position sizing, limits)
- **Pros**: Dynamic risk management
- **Cons**: Harder to validate, adds complexity

#### 3. **Position Sizing** (How Much to Trade)
- ML model predicts: Optimal position size
- Input: Signal confidence, volatility, portfolio state
- Output: Position size recommendation
- **Pros**: Can optimize risk-adjusted returns
- **Cons**: Requires careful backtesting

---

## Recommended Approach

### Phase 1: Simple ML Strategy (Start Here)

**Goal**: Prove ML can work in your framework

**Implementation**:
1. Create `MLStrategy` base class
2. Train simple model (linear regression or small MLP)
3. Model predicts: next price direction (up/down)
4. Generate BUY/SELL signals based on prediction
5. Compare performance vs rule-based strategies

**Example**:
```python
class SimpleMLStrategy(Strategy):
    def __init__(self, symbol, model_path):
        # Load pre-trained model
        self.model = load_model(model_path)
        self.price_history = deque(maxlen=20)
    
    def handle_market(self, event):
        # Collect features
        features = self._extract_features(event)
        
        # Predict
        prediction = self.model.predict(features)
        
        # Generate signal
        if prediction > threshold and self.state == "FLAT":
            return [SignalEvent(...)]  # BUY
        elif prediction < -threshold and self.state == "LONG":
            return [SignalEvent(...)]  # SELL
```

### Phase 2: Feature Engineering

**Features to Consider**:
- Price history (last N prices)
- Moving averages (5, 10, 20 period)
- Volatility (rolling std dev)
- Price changes (returns)
- Technical indicators (RSI, MACD if you add them)

**Important**: 
- No future data leakage!
- Features must be computable at prediction time
- Use only past data

### Phase 3: Model Training Pipeline

**Workflow**:
1. **Data Collection**: Gather historical market data
2. **Feature Extraction**: Create features from raw prices
3. **Label Creation**: Define what to predict (next return, direction, etc.)
4. **Train/Test Split**: Walk-forward validation (train on past, test on future)
5. **Model Training**: Train model on training set
6. **Validation**: Test on out-of-sample data
7. **Backtesting**: Run in your trading engine with execution costs

**Key Principle**: 
- Train offline, use online
- Never retrain during backtest (that's cheating!)

---

## Model Types to Consider

### 1. **Linear Models** (Start Here)
- **Linear Regression**: Predict next price/return
- **Logistic Regression**: Predict direction (up/down)
- **Pros**: Simple, interpretable, fast
- **Cons**: Limited to linear patterns

### 2. **Tree-Based Models**
- **Random Forest**: Ensemble of decision trees
- **XGBoost**: Gradient boosting
- **Pros**: Handles non-linear patterns, feature importance
- **Cons**: Can overfit, less interpretable

### 3. **Neural Networks**
- **MLP**: Multi-layer perceptron
- **LSTM**: For time series
- **Pros**: Can learn complex patterns
- **Cons**: Hard to debug, needs lots of data, overfitting risk

### 4. **Time Series Models**
- **ARIMA**: Traditional time series
- **Prophet**: Facebook's time series model
- **Pros**: Designed for temporal data
- **Cons**: May not capture non-linear patterns

---

## Critical Considerations

### 1. **Data Leakage** ⚠️
**Problem**: Using future information to predict past
**Example**: Using tomorrow's price to predict today's signal
**Solution**: 
- Only use past data for features
- Walk-forward validation (train on t-100 to t-1, test on t)

### 2. **Overfitting** ⚠️
**Problem**: Model memorizes training data, fails on new data
**Signs**: 
- Train accuracy: 95%, Test accuracy: 50%
- Performance drops in live trading
**Solution**:
- Use train/validation/test splits
- Regularization (L1/L2)
- Simpler models
- Cross-validation

### 3. **Non-Stationarity** ⚠️
**Problem**: Market patterns change over time
**Example**: Model trained on 2020 data fails in 2024
**Solution**:
- Retrain periodically (but not during backtest!)
- Use rolling windows
- Monitor performance degradation

### 4. **Execution Costs** ⚠️
**Problem**: ML predicts price moves, but doesn't account for slippage
**Example**: Model predicts +0.5% move, but execution costs are 0.2%
**Solution**:
- Include execution costs in backtesting
- Filter signals by minimum expected return
- Your `RealisticExecutionHandler` already handles this!

### 5. **Evaluation Metrics** ⚠️
**Problem**: Accuracy doesn't equal profitability
**Example**: 60% accuracy but losing money (wrong predictions are bigger losses)
**Solution**:
- Use your existing metrics: Sharpe ratio, total return, max drawdown
- Compare ML strategy vs baseline (mean reversion)
- Consider risk-adjusted returns

---

## Recommended Implementation Plan

### Step 1: Proof of Concept (1-2 weeks)
1. Create `MLStrategy` base class
2. Train simple linear model on historical data
3. Integrate into your strategy framework
4. Run backtest and compare to mean reversion
5. **Goal**: Prove ML can generate signals that work

### Step 2: Feature Engineering (1 week)
1. Add feature extraction (MA, volatility, returns)
2. Create feature pipeline
3. Test different feature combinations
4. **Goal**: Improve model inputs

### Step 3: Model Comparison (1-2 weeks)
1. Try different models (linear, tree-based, neural net)
2. Compare performance
3. Analyze feature importance
4. **Goal**: Find best model for your data

### Step 4: Production Hardening (1 week)
1. Add model versioning
2. Add performance monitoring
3. Add retraining pipeline
4. **Goal**: Make it production-ready

---

## Example: Simple ML Strategy

```python
from strategies.base import Strategy
from events.base import MarketEvent, SignalEvent
from collections import deque
import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle

class SimpleMLStrategy(Strategy):
    """
    Simple ML strategy using logistic regression to predict price direction.
    
    Features:
    - Last 5 prices
    - 5-period moving average
    - Price change (return)
    
    Prediction:
    - Probability of price going up
    - Buy if prob > 0.6, Sell if prob < 0.4
    """
    
    def __init__(self, symbol=None, model_path=None, lookback=5):
        super().__init__(symbol)
        self.lookback = lookback
        self.prices = deque(maxlen=lookback)
        self.state = "FLAT"
        
        # Load pre-trained model
        if model_path:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
        else:
            # Train a simple model (in practice, train offline)
            self.model = self._train_default_model()
    
    def _train_default_model(self):
        """Train a simple default model (for demo only)"""
        # In practice, train on real historical data
        model = LogisticRegression()
        # Dummy training (replace with real data)
        X = np.random.randn(100, 3)  # 3 features
        y = np.random.randint(0, 2, 100)  # Binary labels
        model.fit(X, y)
        return model
    
    def _extract_features(self, event):
        """Extract features from current price history"""
        if len(self.prices) < self.lookback:
            return None
        
        prices_array = np.array(list(self.prices))
        
        # Feature 1: Last price
        last_price = prices_array[-1]
        
        # Feature 2: Moving average
        ma = np.mean(prices_array)
        
        # Feature 3: Price change (return)
        price_change = (last_price - prices_array[-2]) / prices_array[-2] if len(prices_array) > 1 else 0
        
        return np.array([[last_price, ma, price_change]])
    
    def handle_market(self, event: MarketEvent):
        if self.symbol and event.symbol != self.symbol:
            return []
        
        self.prices.append(event.price)
        
        # Need enough data for features
        if len(self.prices) < self.lookback:
            return []
        
        # Extract features
        features = self._extract_features(event)
        if features is None:
            return []
        
        # Predict probability of price going up
        prob_up = self.model.predict_proba(features)[0][1]
        
        # Generate signals
        signals = []
        
        # Buy if high probability of going up
        if prob_up > 0.6 and self.state == "FLAT":
            self.state = "LONG"
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="BUY",
                price=event.price
            ))
        
        # Sell if low probability of going up
        elif prob_up < 0.4 and self.state == "LONG":
            self.state = "FLAT"
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="SELL",
                price=event.price
            ))
        
        return signals
```

---

## Key Takeaways

1. **Start Simple**: Linear models first, then complex
2. **Test Rigorously**: Walk-forward validation, compare to baselines
3. **Account for Costs**: Your execution handler already does this!
4. **Monitor Performance**: Track train vs test performance gap
5. **Keep It Interpretable**: Simple models are easier to debug
6. **Respect Your Philosophy**: Execution quality > prediction accuracy

---

## Questions to Answer Before Building

1. **What to predict?**
   - Price direction (up/down)?
   - Price level?
   - Return magnitude?
   - Volatility?

2. **What features?**
   - Just prices?
   - Technical indicators?
   - Multi-symbol features?

3. **How to train?**
   - Offline training pipeline?
   - Online learning?
   - Retraining schedule?

4. **How to evaluate?**
   - Accuracy?
   - Sharpe ratio?
   - Total return?
   - Risk-adjusted metrics?

5. **How to integrate?**
   - Replace strategy layer?
   - Enhance existing strategies?
   - Hybrid approach (ML + rules)?

---

## My Recommendation

**Start with a simple ML strategy that:**
1. Uses linear regression or logistic regression
2. Predicts price direction (up/down)
3. Uses simple features (prices, MA, returns)
4. Trains offline on historical data
5. Generates signals like your existing strategies
6. Gets tested with your execution costs and risk manager

**Then compare:**
- ML strategy vs mean reversion strategy
- Performance metrics (Sharpe, return, drawdown)
- Number of trades, win rate
- Execution costs impact

**This proves:**
- ML can work in your framework
- Whether it's better than rule-based
- What challenges you'll face

**Then decide:**
- Is it worth the complexity?
- Should you go deeper (more features, better models)?
- Or stick with rule-based strategies?

---

## Resources

- **Scikit-learn**: Great for simple ML models
- **XGBoost**: For tree-based models
- **TensorFlow/PyTorch**: For neural networks (if needed)
- **Walk-forward validation**: Critical for time series
- **Feature engineering**: Often more important than model choice


