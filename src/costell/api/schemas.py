"""Pydantic schemas for the Costell API."""

from pydantic import BaseModel, Field


class EstimationRequest(BaseModel):
    """Input schema for the /estimate endpoint."""

    # --- Effort Features ---
    estimated_effort: float = Field(
        ..., gt=0, description="The initial human estimate in person-hours."
    )
    team_size: float = Field(..., ge=0, description="Number of people on the team.")
    duration: float = Field(..., ge=0, description="Project duration in months.")
    function_points: float = Field(..., ge=0, description="Adjusted function points (AFP).")
    language: str = Field(..., description="Primary programming language or development type.")
    dataset_source: str = Field(default="user_input", description="Source of the project data.")

    # --- Financial Inputs ---
    blended_hourly_rate: float = Field(
        default=2500.0, gt=0, description="Blended hourly rate for the team in INR."
    )
    tooling_cost_per_month: float = Field(
        default=0.0, ge=0, description="Tooling/license cost per month in INR."
    )
    cloud_cost_per_month: float = Field(
        default=0.0, ge=0, description="Cloud/AI infrastructure cost per month in INR."
    )
    contingency_percent: float = Field(
        default=15.0, ge=0, le=50, description="Contingency buffer percentage."
    )


class CostBreakdown(BaseModel):
    """Detailed cost breakdown for the project."""

    personnel_cost: float = Field(..., description="Total personnel cost in INR.")
    tooling_cost: float = Field(..., description="Total tooling cost in INR.")
    cloud_cost: float = Field(..., description="Total cloud/infra cost in INR.")
    contingency: float = Field(..., description="Contingency buffer in INR.")
    total_cost: float = Field(..., description="Grand total cost in INR.")


class EstimationResponse(BaseModel):
    """Output schema for the /estimate endpoint."""

    # --- Effort Estimates ---
    p50_effort: float = Field(..., description="Most likely effort estimate in person-hours.")
    p80_lower_effort: float = Field(..., description="Lower bound of the 80% effort interval.")
    p80_upper_effort: float = Field(..., description="Upper bound of the 80% effort interval.")

    # --- Cost Estimates ---
    p50_cost: CostBreakdown = Field(..., description="Cost breakdown for the P50 estimate.")
    p80_lower_cost: CostBreakdown = Field(
        ..., description="Cost breakdown for the P80 lower bound."
    )
    p80_upper_cost: CostBreakdown = Field(
        ..., description="Cost breakdown for the P80 upper bound."
    )

    confidence_level: float = Field(
        default=0.8, description="The confidence level of the interval."
    )
