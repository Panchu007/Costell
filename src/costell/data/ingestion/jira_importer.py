"""Module for parsing Jira CSV exports and extracting effort metrics."""

from io import BytesIO

import polars as pl


def parse_jira_csv(file_bytes: bytes) -> dict:
    """
    Parse a Jira CSV export and calculate total estimated effort.

    Args:
        file_bytes: The raw bytes of the uploaded CSV file.

    Returns:
        A dictionary with task count, total story points, and total hours.
    """
    try:
        # Load CSV using Polars
        df = pl.read_csv(BytesIO(file_bytes), infer_schema_length=10000)
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")

    # Normalize column names to lowercase to handle Jira's inconsistent exports
    df.columns = [c.lower().strip() for c in df.columns]

    # Try to find the Story Points column (it varies wildly in Jira)
    story_points_col = next(
        (c for c in df.columns if "story point" in c or c == "custom field (story points)"), None
    )

    # Try to find the Original Estimate column (usually in seconds or hours)
    estimate_col = next(
        (c for c in df.columns if "original estimate" in c or "time estimate" in c), None
    )

    total_points = 0.0
    total_hours = 0.0
    task_count = len(df)

    if story_points_col:
        # Sum up story points, replacing nulls with 0
        total_points = float(
            df[story_points_col].cast(pl.Float64, strict=False).fill_null(0.0).sum()
        )
        # Industry heuristic: 1 Story Point ≈ 8 hours of effort
        total_hours += total_points * 8.0

    if estimate_col:
        # Jira often exports time estimates in seconds, but sometimes string formats
        # We try to parse it as a number
        try:
            est_hours = float(df[estimate_col].cast(pl.Float64, strict=False).fill_null(0.0).sum())
            # If the value is huge, it's likely in seconds. Convert to hours.
            if est_hours > 10000:
                est_hours = est_hours / 3600.0
            total_hours += est_hours
        except Exception:
            pass  # Ignore if the column format is unparseable strings

    # Fallback: If no estimates found, assume 8 hours per task
    if total_hours == 0:
        total_hours = task_count * 8.0

    return {
        "task_count": task_count,
        "total_story_points": round(total_points, 2),
        "estimated_effort_hours": round(total_hours, 2),
        "columns_found": {"story_points": story_points_col, "estimate": estimate_col},
    }
