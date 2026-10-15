"""FastAPI application for the Costell estimation engine."""

from contextlib import asynccontextmanager

import pandas as pd
from catboost import CatBoostRegressor
from fastapi import FastAPI, HTTPException

from costell.api.schemas import CostBreakdown, EstimationRequest, EstimationResponse
from costell.config import settings

# Global variable to hold the model
model: CatBoostRegressor | None = None

# The calibrated margin from our conformal prediction step
Q_MARGIN = 615.49


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the ML model on startup."""
    global model
    model_path = settings.processed_data_dir.parent / "models" / "catboost_effort.cbm"
    if not model_path.exists():
        raise RuntimeError(
            f"Model file not found at {model_path}. Please run the training script first."
        )

    model = CatBoostRegressor()
    model.load_model(model_path)
    print(f"✅ CatBoost model loaded successfully from {model_path}")
    yield
    model = None


app = FastAPI(
    title="Costell API",
    description="AI-powered cost estimation engine for the AI-native development era.",
    version=settings.project_version,
    lifespan=lifespan,
)


def _calculate_cost_breakdown(
    effort_hours: float,
    request: EstimationRequest,
) -> CostBreakdown:
    """Calculate the full cost breakdown for a given effort value."""
    # 1. Personnel Cost = Effort (hours) × Blended Hourly Rate
    personnel_cost = effort_hours * request.blended_hourly_rate

    # 2. Tooling Cost = Monthly cost × Duration
    tooling_cost = request.tooling_cost_per_month * request.duration

    # 3. Cloud Cost = Monthly cost × Duration
    cloud_cost = request.cloud_cost_per_month * request.duration

    # 4. Subtotal before contingency
    subtotal = personnel_cost + tooling_cost + cloud_cost

    # 5. Contingency = Subtotal × Contingency %
    contingency = subtotal * (request.contingency_percent / 100.0)

    # 6. Grand Total
    total_cost = subtotal + contingency

    return CostBreakdown(
        personnel_cost=round(personnel_cost, 2),
        tooling_cost=round(tooling_cost, 2),
        cloud_cost=round(cloud_cost, 2),
        contingency=round(contingency, 2),
        total_cost=round(total_cost, 2),
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model_loaded": model is not None}


@app.post("/estimate", response_model=EstimationResponse)
def estimate(request: EstimationRequest):
    """
    Predict effort and total project cost with an 80% confidence interval.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    # Convert the request into a DataFrame for CatBoost
    df = pd.DataFrame(
        [
            {
                "estimated_effort": request.estimated_effort,
                "team_size": request.team_size,
                "duration": request.duration,
                "function_points": request.function_points,
                "language": request.language,
                "dataset_source": request.dataset_source,
            }
        ]
    )

    # Predict P50 effort
    p50_effort = float(model.predict(df)[0])

    # Calculate P80 effort interval using the conformal margin
    p80_lower_effort = max(p50_effort - Q_MARGIN, 0)
    p80_upper_effort = p50_effort + Q_MARGIN

    # Calculate cost breakdowns for all three effort scenarios
    p50_cost = _calculate_cost_breakdown(p50_effort, request)
    p80_lower_cost = _calculate_cost_breakdown(p80_lower_effort, request)
    p80_upper_cost = _calculate_cost_breakdown(p80_upper_effort, request)

    return EstimationResponse(
        p50_effort=round(p50_effort, 2),
        p80_lower_effort=round(p80_lower_effort, 2),
        p80_upper_effort=round(p80_upper_effort, 2),
        p50_cost=p50_cost,
        p80_lower_cost=p80_lower_cost,
        p80_upper_cost=p80_upper_cost,
        confidence_level=0.8,
    )
