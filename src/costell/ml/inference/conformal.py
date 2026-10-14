"""Custom Split Conformal Prediction wrapper for the CatBoost effort model."""

import numpy as np
import pandas as pd
import polars as pl
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split

from costell.config import settings


def load_data() -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """Load the merged dataset and define features/target."""
    df = pl.read_parquet(settings.processed_data_dir / "merged_clean.parquet").to_pandas()

    target = "actual_effort"
    features = [
        "estimated_effort",
        "team_size",
        "duration",
        "function_points",
        "language",
        "dataset_source",
    ]
    categorical = ["language", "dataset_source"]

    X = df[features]
    y = df[target]
    return X, y, features, categorical


def train_conformal_model(
    X: pd.DataFrame, y: pd.Series, categorical: list[str], alpha: float = 0.2
):
    """
    Train a CatBoost model and calibrate it for conformal prediction.

    Returns:
        A tuple of (trained_model, calibration_quantile, X_calib, y_calib).
    """
    # Split data into training and calibration sets (70/30)
    X_train, X_calib, y_train, y_calib = train_test_split(X, y, test_size=0.3, random_state=42)

    # Base model: CatBoost
    base_model = CatBoostRegressor(
        iterations=500, learning_rate=0.05, depth=6, verbose=0, random_state=42
    )

    # Fit the base model on the training set
    base_model.fit(X_train, y_train, cat_features=categorical)

    # --- Conformal Calibration Step ---
    # 1. Predict on the calibration set
    y_calib_pred = base_model.predict(X_calib)

    # 2. Calculate absolute residuals (how wrong was the model on unseen data?)
    residuals = np.abs(y_calib.values - y_calib_pred)

    # 3. Find the quantile that gives us our desired confidence level.
    # For alpha=0.2 (80% confidence), we need the 0.8 quantile of the residuals.
    q = float(np.quantile(residuals, 1 - alpha))

    return base_model, q, X_calib, y_calib


def predict_interval(model: CatBoostRegressor, q: float, X_test: pd.DataFrame):
    """
    Generate point predictions and conformal prediction intervals.

    The interval is simply: [prediction - q, prediction + q]
    We clip the lower bound at 0 because effort cannot be negative.
    """
    y_pred = model.predict(X_test)
    lower_bounds = np.maximum(y_pred - q, 0)  # <-- Clip negative lower bounds to 0
    upper_bounds = y_pred + q
    return y_pred, lower_bounds, upper_bounds


def evaluate_coverage(
    model: CatBoostRegressor,
    q: float,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    confidence_level: float = 0.8,
) -> None:
    """Evaluate the empirical coverage of the conformal intervals."""
    y_pred, lower_bounds, upper_bounds = predict_interval(model, q, X_test)

    # Calculate empirical coverage: % of true values that fall within the interval
    within_interval = ((y_test >= lower_bounds) & (y_test <= upper_bounds)).mean()

    print(f"  Target Coverage: {confidence_level * 100:.0f}%")
    print(f"  Empirical Coverage: {within_interval * 100:.2f}%")


if __name__ == "__main__":
    X, y, features, categorical = load_data()

    print("=" * 60)
    print("  COSTELL — Custom Split Conformal Prediction Engine")
    print("=" * 60)

    model, q, X_calib, y_calib = train_conformal_model(X, y, categorical, alpha=0.2)
    print(f"\n  Calibration Quantile (q): {q:.2f} hours")

    # Use a small sample from the calibration set to demonstrate the ranges
    X_sample = X_calib.head(5)
    y_sample = y_calib.head(5)

    y_pred, lower_bounds, upper_bounds = predict_interval(model, q, X_sample)

    print("\n  Sample Predictions with 80% Confidence Intervals:")
    print("  " + "-" * 56)
    for i in range(len(X_sample)):
        actual = y_sample.iloc[i]
        pred = y_pred[i]
        lower = lower_bounds[i]
        upper = upper_bounds[i]
        print(
            f"  Project {i + 1}: Actual = {actual:.0f}h | P50 = {pred:.0f}h | P80 Range = [{lower:.0f}h, {upper:.0f}h]"
        )

    print("\n  Interval Calibration Check:")
    print("  " + "-" * 56)
    evaluate_coverage(model, q, X_calib, y_calib, confidence_level=0.8)
    print("=" * 60)
