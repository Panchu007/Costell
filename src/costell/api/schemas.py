"""Pydantic schemas for the Costell API."""

from pydantic import BaseModel, Field


class EstimationRequest(BaseModel):
    """Input schema for the /estimate endpoint."""

    estimated_effort: float = Field(
        ..., gt=0, description="The initial human estimate in person-hours."
    )
    team_size: float = Field(..., ge=0, description="Number of people on the team.")
    duration: float = Field(..., ge=0, description="Project duration in months.")
    function_points: float = Field(..., ge=0, description="Adjusted function points (AFP).")
    language: str = Field(..., description="Primary programming language or development type.")
    dataset_source: str = Field(default="user_input", description="Source of the project data.")


class EstimationResponse(BaseModel):
    """Output schema for the /estimate endpoint."""

    p50_estimate: float = Field(..., description="The most likely effort estimate in person-hours.")
    p80_lower: float = Field(..., description="Lower bound of the 80% confidence interval.")
    p80_upper: float = Field(..., description="Upper bound of the 80% confidence interval.")
    confidence_level: float = Field(
        default=0.8, description="The confidence level of the interval."
    )
