"""SQLModel table definitions for Costell."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Estimate(SQLModel, table=True):
    """A single cost estimate stored in the database."""

    id: int | None = Field(default=None, primary_key=True)
    project_name: str = Field(default="Untitled Project", index=True)

    # --- Input Parameters ---
    estimated_effort: float
    team_size: float
    duration: float
    function_points: float
    language: str
    dataset_source: str = "user_input"
    blended_hourly_rate: float
    tooling_cost_per_month: float
    cloud_cost_per_month: float
    contingency_percent: float

    # --- Predicted Outputs (in INR) ---
    p50_effort: float
    p80_lower_effort: float
    p80_upper_effort: float
    p50_cost: float
    p80_lower_cost: float
    p80_upper_cost: float
    safe_budget: float

    # --- Actuals (logged after project completion) ---
    actual_effort: float | None = Field(default=None)
    actual_cost: float | None = Field(default=None)

    # --- Metadata ---
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actual_logged_at: datetime | None = Field(default=None)
