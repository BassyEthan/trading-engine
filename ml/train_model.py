"""
Train ML model for price direction prediction.

Trains a logistic regression model to predict if price will go up or down.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

from ml.prepare_data import prepare_training_data
from ml.feature_extractor import FeatureExtractor


def train_model(
    train_data_path: str,
    model_output_path: str,
    price_lookback: int = 3,
    ma_window: int = 5,
    volatility_window: int = 5,
):
    """
    Train logistic regression model.
    
    Args:
        train_data_path: Path to training data JSON file
        model_output_path: Path to save trained model
        price_lookback: Number of recent prices to include
        ma_window: Window size for moving average
        volatility_window: Window size for volatility
    """
    print("=" * 70)
    print("TRAINING LOGISTIC REGRESSION MODEL")
    print("=" * 70)
    print()
    
    # Prepare training data
    X_train, y_train = prepare_training_data(
        train_data_path,
        price_lookback=price_lookback,
        ma_window=ma_window,
        volatility_window=volatility_window,
    )
    
    print()
    print("=" * 70)
    print("TRAINING MODEL")
    print("=" * 70)
    print()
    
    # Create and train model
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        solver='lbfgs',  # Good for small datasets
    )
    
    print("Fitting model...")
    model.fit(X_train, y_train)
    print("✅ Model trained!")
    print()
    
    # Evaluate on training data
    y_pred = model.predict(X_train)
    accuracy = accuracy_score(y_train, y_pred)
    
    print("=" * 70)
    print("TRAINING PERFORMANCE")
    print("=" * 70)
    print()
    print(f"Accuracy: {accuracy:.2%}")
    print()
    print("Classification Report:")
    print(classification_report(y_train, y_pred, target_names=['Down', 'Up']))
    print()
    
    # Get feature importance (coefficients)
    print("Feature Importance (coefficients):")
    extractor = FeatureExtractor(
        price_lookback=price_lookback,
        ma_window=ma_window,
        volatility_window=volatility_window,
    )
    feature_names = extractor.get_feature_names()
    
    for name, coef in zip(feature_names, model.coef_[0]):
        print(f"  {name:20s}: {coef:+.4f}")
    print()
    
    # Save model and metadata
    model_dir = Path(model_output_path).parent
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'model': model,
        'feature_extractor': extractor,
        'price_lookback': price_lookback,
        'ma_window': ma_window,
        'volatility_window': volatility_window,
        'feature_names': feature_names,
        'training_accuracy': accuracy,
    }
    
    with open(model_output_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print("=" * 70)
    print("✅ MODEL SAVED")
    print("=" * 70)
    print(f"Saved to: {model_output_path}")
    print()
    print("Model metadata:")
    print(f"  Training samples: {len(X_train)}")
    print(f"  Features: {len(feature_names)}")
    print(f"  Training accuracy: {accuracy:.2%}")
    print()
    
    return model, model_data


if __name__ == "__main__":
    train_path = Path("data/ml_training/train_data.json")
    model_path = Path("ml/models/price_direction_model.pkl")
    
    if train_path.exists():
        train_model(
            train_data_path=str(train_path),
            model_output_path=str(model_path),
        )
        print("✅ Training complete! Model ready for use.")
    else:
        print(f"❌ Training data not found: {train_path}")

