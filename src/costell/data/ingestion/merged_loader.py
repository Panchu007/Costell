"""Loader and harmonizer for the merged China + Desharnais + SEERA dataset."""

from pathlib import Path

import numpy as np
import polars as pl

from costell.config import settings


def load_china(file_path: Path) -> pl.DataFrame:
    """Load and normalize the China dataset."""
    df = pl.read_csv(file_path)
    return df.select(
        [
            pl.col("Effort").cast(pl.Float64).alias("actual_effort"),
            # Simulate a human estimate with +/- 20% error
            (pl.col("Effort") / 1.2 * pl.Series(np.random.uniform(0.8, 1.2, df.height))).alias(
                "estimated_effort"
            ),  # Baseline
            pl.col("Resource").cast(pl.Float64).alias("team_size"),
            pl.col("Duration").cast(pl.Float64).alias("duration"),
            pl.col("AFP").cast(pl.Float64).alias("function_points"),
            pl.col("Dev.Type").cast(pl.Utf8).alias("language"),
            pl.lit("china").alias("dataset_source"),
        ]
    )


def load_desharnais(file_path: Path) -> pl.DataFrame:
    """Load and normalize the Desharnais dataset."""
    df = pl.read_csv(file_path)

    # Map language codes (1, 2, 3) to meaningful strings
    lang_map = {1: "Assembly", 2: "3GL", 3: "4GL"}
    df = df.with_columns(
        pl.col("Language").replace_strict(lang_map, default="Unknown").alias("language_str")
    )

    return df.select(
        [
            pl.col("Effort").cast(pl.Float64).alias("actual_effort"),
            # Simulate a human estimate with +/- 20% error
            (pl.col("Effort") / 1.2 * pl.Series(np.random.uniform(0.8, 1.2, df.height))).alias(
                "estimated_effort"
            ),  # Baseline
            pl.col("TeamExp").cast(pl.Float64).alias("team_size"),
            pl.col("Length").cast(pl.Float64).alias("duration"),
            pl.col("PointsAjust").cast(pl.Float64).alias("function_points"),
            pl.col("language_str").cast(pl.Utf8).alias("language"),
            pl.lit("desharnais").alias("dataset_source"),
        ]
    )


def load_seera(file_path: Path) -> pl.DataFrame:
    """Load and normalize the SEERA dataset."""
    df = pl.read_csv(file_path)
    return df.select(
        [
            pl.col("Actual_Effort").cast(pl.Float64).alias("actual_effort"),
            pl.col("Estimated_Effort").cast(pl.Float64).alias("estimated_effort"),
            pl.col("Team_Size").cast(pl.Float64).alias("team_size"),
            pl.lit(None).cast(pl.Float64).alias("duration"),  # Not available in SEERA
            pl.lit(None).cast(pl.Float64).alias("function_points"),  # Not available in SEERA
            pl.col("Language").cast(pl.Utf8).alias("language"),
            pl.lit("seera").alias("dataset_source"),
        ]
    )


def merge_datasets() -> pl.DataFrame:
    """Load, harmonize, and merge all three datasets."""
    china_df = load_china(settings.raw_data_dir / "china.csv")
    desharnais_df = load_desharnais(settings.raw_data_dir / "desharnais.csv")
    seera_df = load_seera(settings.raw_data_dir / "seera.csv")

    # Combine vertically (stack rows)
    merged = pl.concat([china_df, desharnais_df, seera_df], how="vertical")

    # Drop rows missing the critical target features
    merged = merged.drop_nulls(subset=["actual_effort", "estimated_effort"])

    # Fill remaining nulls in feature columns so CatBoost can handle them smoothly
    merged = merged.with_columns(
        [
            pl.col("team_size").fill_null(0.0),
            pl.col("duration").fill_null(0.0),
            pl.col("function_points").fill_null(0.0),
            pl.col("language").fill_null("Unknown"),
        ]
    )

    return merged


def save_merged(df: pl.DataFrame) -> None:
    """Save the merged dataset as a Parquet file."""
    output_dir = settings.processed_data_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_dir / "merged_clean.parquet")


if __name__ == "__main__":
    merged_df = merge_datasets()
    save_merged(merged_df)
    print("=" * 50)
    print("  MERGED DATASET SAVED")
    print("=" * 50)
    print(f"  Total projects: {merged_df.height}")
    print(f"  Columns: {merged_df.columns}")
    print("=" * 50)
