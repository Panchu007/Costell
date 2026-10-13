"""Training pipeline for the CatBoost effort estimation model."""

import numpy as np
import pandas as pd
import polars as pl
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split

from costell.config import settings


def load_data() -> tuple[pd.DataFrame, list[str], list[str], str]:
    """
    Load the processed merged dataset and define feature/target columns.
    """
    df = pl.read_parquet(settings.processed_data_dir / "merged_clean.parquet")
    df = df.to_pandas()

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

    return df, features, target, categorical


def calculate_kpis(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calculate MMRE and PRED(25) for the model predictions.

    Args:
        y_true: The actual effort values.
        y_pred: The predicted effort values.

    Returns:
        A dictionary containing MMRE and PRED(25) values.
    """
    # Magnitude of Relative Error for each prediction
    mre = np.abs(y_true - y_pred) / y_true

    mmre = float(np.mean(mre))
    pred_25 = float(np.mean(mre <= 0.25))

    return {"MMRE": mmre, "PRED(25)": pred_25}


def train_model(
    df: pd.DataFrame, features: list[str], target: str, categorical: list[str]
) -> tuple[CatBoostRegressor, pd.DataFrame, pd.Series]:
    """
    Train a CatBoost regressor on the SEERA data.

    Args:
        df: The cleaned DataFrame.
        features: List of feature column names.
        target: The name of the target column.
        categorical: List of categorical feature names.

    Returns:
        A tuple of (trained_model, test_features, test_targets).
    """
    X = df[features]
    y = df[target]

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Initialize the CatBoost model
    model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        verbose=0,
        random_state=42,
    )

    # Train the model, explicitly telling it which features are categorical
    model.fit(
        X_train,
        y_train,
        cat_features=categorical,
        eval_set=(X_test, y_test),
    )

    return model, X_test, y_test


def save_model(model: CatBoostRegressor) -> None:
    """Save the trained model to the models directory."""
    model_dir = settings.processed_data_dir.parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(model_dir / "catboost_effort.cbm")


if __name__ == "__main__":
    # 1. Load data
    df, features, target, categorical = load_data()

    # 2. Train model
    model, X_test, y_test = train_model(df, features, target, categorical)

    # 3. Make predictions
    y_pred = model.predict(X_test)

    # 4. Calculate KPIs
    kpis = calculate_kpis(y_test.values, y_pred)

    # 5. Print results
    print("=" * 50)
    print("  COSTELL — CatBoost Effort Model Results")
    print("=" * 50)
    print(f"  MMRE:      {kpis['MMRE']:.4f}  ({kpis['MMRE'] * 100:.2f}%)")
    print(f"  PRED(25):  {kpis['PRED(25)']:.4f}  ({kpis['PRED(25)'] * 100:.2f}%)")
    print("=" * 50)

    # 6. Save model
    save_model(model)
    print("Model saved to data/models/catboost_effort.cbm")
