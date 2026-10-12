"""Loading and preprocessing utilities for the SEERA dataset."""

import re
from pathlib import Path

import polars as pl

from costell.config import settings

_CRITICAL_COLUMNS = ("actual_effort", "estimated_effort")


def _to_snake_case(column_name: str) -> str:
    """Normalize a column name to lowercase snake_case."""
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", column_name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return name.strip("_").lower()


def load_raw_seera(file_path: Path) -> pl.DataFrame:
    """Read the raw SEERA CSV and normalize its column names."""
    df = pl.read_csv(file_path)
    normalized_columns = [_to_snake_case(column) for column in df.columns]

    if len(normalized_columns) != len(set(normalized_columns)):
        raise ValueError("SEERA CSV contains column names that collide after normalization.")

    return df.rename(dict(zip(df.columns, normalized_columns, strict=True)))


def process_seera(df: pl.DataFrame) -> pl.DataFrame:
    """Drop rows with missing effort values and add effort error."""
    missing_columns = set(_CRITICAL_COLUMNS).difference(df.columns)
    if missing_columns:
        raise ValueError(
            f"SEERA data is missing required columns: {', '.join(sorted(missing_columns))}"
        )

    numeric_columns = [
        column for column, dtype in df.schema.items() if dtype.is_numeric()
    ]
    columns_to_cast = list(dict.fromkeys((*numeric_columns, *_CRITICAL_COLUMNS)))
    df = df.with_columns(
        [pl.col(column).cast(pl.Float64, strict=False) for column in columns_to_cast]
    )
    df = df.drop_nulls(subset=list(_CRITICAL_COLUMNS))

    return df.with_columns(
        (
            (pl.col("actual_effort") - pl.col("estimated_effort"))
            / pl.col("actual_effort")
        ).alias("effort_error")
    )


def save_processed(df: pl.DataFrame, output_dir: Path) -> None:
    """Save the processed SEERA DataFrame as a Parquet file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_dir / "seera_clean.parquet")


if __name__ == "__main__":
    raw_df = load_raw_seera(settings.raw_data_dir / "seera.csv")
    processed_df = process_seera(raw_df)
    save_processed(processed_df, settings.processed_data_dir)
