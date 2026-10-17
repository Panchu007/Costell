"""Analogy-Based Estimation (ABE) using k-Nearest Neighbors."""

import polars as pl
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from costell.config import settings


def estimate_effort_analogy(
    function_points: float,
    team_size: float,
    duration: float,
    k_neighbors: int = 3,
) -> dict:
    """
    Find the k most similar historical projects and average their actual effort.

    Args:
        function_points: Target project's AFP.
        team_size: Target project's team size.
        duration: Target project's duration in months.
        k_neighbors: Number of similar projects to average.

    Returns:
        A dict with the average effort from neighbors and the individual neighbors.
    """
    # 1. Load historical data
    df = pl.read_parquet(settings.processed_data_dir / "merged_clean.parquet").to_pandas()

    # 2. Select features for similarity matching.
    # We drop rows with missing values in these specific features.
    features = ["function_points", "team_size", "duration"]
    target = "actual_effort"

    # Filter out rows with invalid/zero values (we filled nulls with 0.0 during ingestion)
    df_clean = df.dropna(subset=features + [target]).copy()
    df_clean = df_clean[
        (df_clean["function_points"] > 0) & (df_clean["team_size"] > 0) & (df_clean["duration"] > 0)
    ]
    if df_clean.empty:
        raise ValueError("No historical data available with complete features.")

    # 3. Prepare the data for k-NN
    X_history = df_clean[features].values
    y_history = df_clean[target].values

    # 4. Standardize the features (crucial for k-NN so distance metrics are fair)
    scaler = StandardScaler()
    X_history_scaled = scaler.fit_transform(X_history)

    # 5. Fit the k-NN model
    # Ensure we don't ask for more neighbors than we have projects
    actual_k = min(k_neighbors, len(df_clean))
    knn = NearestNeighbors(n_neighbors=actual_k, metric="euclidean")
    knn.fit(X_history_scaled)

    # 6. Scale the target project's features
    X_target = [[function_points, team_size, duration]]
    X_target_scaled = scaler.transform(X_target)

    # 7. Find the neighbors
    distances, indices = knn.kneighbors(X_target_scaled)

    # 8. Extract the neighbors
    neighbors = []
    for i, idx in enumerate(indices[0]):
        row = df_clean.iloc[idx]
        neighbors.append(
            {
                "project_id": int(row.get("project_id", 0)) if "project_id" in row else int(idx),
                "distance": round(float(distances[0][i]), 4),
                "historical_effort": round(float(y_history[idx]), 2),
                "historical_fp": round(float(row["function_points"]), 2),
                "historical_team": round(float(row["team_size"]), 2),
            }
        )

    # 9. Calculate the average effort of the neighbors
    neighbor_efforts = [n["historical_effort"] for n in neighbors]
    average_effort = sum(neighbor_efforts) / len(neighbor_efforts)

    return {
        "model": "Analogy-Based Estimation (k-NN)",
        "k_neighbors": actual_k,
        "estimated_effort_hours": round(average_effort, 2),
        "neighbors": neighbors,
    }
