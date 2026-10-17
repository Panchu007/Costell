"""FastAPI application for the Costell estimation engine."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pandas as pd
from catboost import CatBoostRegressor
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from sqlmodel import Session, select

from costell.api.schemas import CostBreakdown, EstimationRequest, EstimationResponse
from costell.config import settings
from costell.db.models import Estimate
from costell.db.session import get_session, init_db
from costell.llm.decomposer import WorkBreakdownStructure, decompose_prd

# Global variable to hold the model
model: CatBoostRegressor | None = None

# The calibrated margin from our conformal prediction step
Q_MARGIN = 615.49


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the ML model and initialize the database on startup."""
    global model
    model_path = settings.processed_data_dir.parent / "models" / "catboost_effort.cbm"
    if not model_path.exists():
        raise RuntimeError(
            f"Model file not found at {model_path}. Please run the training script first."
        )

    model = CatBoostRegressor()
    model.load_model(model_path)
    print(f"✅ CatBoost model loaded from {model_path}")

    init_db()
    print("✅ Database initialized")

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
    personnel_cost = effort_hours * request.blended_hourly_rate
    tooling_cost = request.tooling_cost_per_month * request.duration
    cloud_cost = request.cloud_cost_per_month * request.duration
    subtotal = personnel_cost + tooling_cost + cloud_cost
    contingency = subtotal * (request.contingency_percent / 100.0)
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
def estimate(
    request: EstimationRequest,
    session: Session = Depends(get_session),
):
    """Predict effort and total project cost, and save to the database."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

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

    p50_effort = float(model.predict(df)[0])
    p80_lower_effort = max(p50_effort - Q_MARGIN, 0)
    p80_upper_effort = p50_effort + Q_MARGIN

    p50_cost = _calculate_cost_breakdown(p50_effort, request)
    p80_lower_cost = _calculate_cost_breakdown(p80_lower_effort, request)
    p80_upper_cost = _calculate_cost_breakdown(p80_upper_effort, request)

    # --- Persist to Database ---
    record = Estimate(
        project_name=request.project_name,
        estimated_effort=request.estimated_effort,
        team_size=request.team_size,
        duration=request.duration,
        function_points=request.function_points,
        language=request.language,
        dataset_source=request.dataset_source,
        blended_hourly_rate=request.blended_hourly_rate,
        tooling_cost_per_month=request.tooling_cost_per_month,
        cloud_cost_per_month=request.cloud_cost_per_month,
        contingency_percent=request.contingency_percent,
        p50_effort=round(p50_effort, 2),
        p80_lower_effort=round(p80_lower_effort, 2),
        p80_upper_effort=round(p80_upper_effort, 2),
        p50_cost=p50_cost.total_cost,
        p80_lower_cost=p80_lower_cost.total_cost,
        p80_upper_cost=p80_upper_cost.total_cost,
        safe_budget=p80_upper_cost.total_cost,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return EstimationResponse(
        p50_effort=round(p50_effort, 2),
        p80_lower_effort=round(p80_lower_effort, 2),
        p80_upper_effort=round(p80_upper_effort, 2),
        p50_cost=p50_cost,
        p80_lower_cost=p80_lower_cost,
        p80_upper_cost=p80_upper_cost,
        confidence_level=0.8,
    )


# ============================================================
# HISTORY & ACTUALS
# ============================================================
@app.get("/history")
def get_history(session: Session = Depends(get_session)):
    """Return all stored estimates, newest first."""
    statement = select(Estimate).order_by(Estimate.created_at.desc())
    estimates = session.exec(statement).all()
    return estimates


class ActualUpdate(PydanticBaseModel):
    """Request body for logging actuals."""

    actual_effort: float = Field(..., gt=0)
    actual_cost: float = Field(..., ge=0)


@app.patch("/estimates/{estimate_id}/actual")
def log_actual(
    estimate_id: int,
    payload: ActualUpdate,
    session: Session = Depends(get_session),
):
    """Log the actual effort and cost for a completed project."""
    record = session.get(Estimate, estimate_id)
    if not record:
        raise HTTPException(status_code=404, detail="Estimate not found.")

    record.actual_effort = payload.actual_effort
    record.actual_cost = payload.actual_cost
    record.actual_logged_at = datetime.now(UTC)

    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@app.get("/kpis")
def get_kpis(session: Session = Depends(get_session)):
    """
    Compute variance KPIs from estimates that have logged actuals.

    Returns MMRE, MdMRE, PRED(25), estimation bias, and count of completed projects.
    """
    statement = select(Estimate).where(Estimate.actual_effort.is_not(None))
    completed = session.exec(statement).all()

    if not completed:
        return {
            "completed_projects": 0,
            "mmre": None,
            "mdmre": None,
            "pred_25": None,
            "bias": None,
        }

    errors = []
    signed_errors = []
    for r in completed:
        actual = r.actual_effort
        predicted = r.p50_effort
        mre = abs(actual - predicted) / actual
        errors.append(mre)
        signed_errors.append((predicted - actual) / actual)

    errors_sorted = sorted(errors)
    n = len(errors_sorted)
    median = (
        errors_sorted[n // 2]
        if n % 2 == 1
        else (errors_sorted[n // 2 - 1] + errors_sorted[n // 2]) / 2
    )

    import numpy as np

    return {
        "completed_projects": n,
        "mmre": round(float(np.mean(errors)), 4),
        "mdmre": round(float(median), 4),
        "pred_25": round(float(np.mean([e <= 0.25 for e in errors])), 4),
        "bias": round(float(np.mean(signed_errors)), 4),
    }


# ============================================================
# LLM SCOPE DECOMPOSITION
# ============================================================
class DecomposeRequest(PydanticBaseModel):
    """Input schema for the /decompose endpoint."""

    prd_text: str = Field(..., min_length=50, description="The PRD text to decompose.")


@app.post("/decompose", response_model=WorkBreakdownStructure)
def decompose(request: DecomposeRequest):
    """Decompose a PRD into a Work Breakdown Structure using the LLM."""
    try:
        return decompose_prd(request.prd_text)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# BASELINE: COCOMO II
# ============================================================
from costell.ml.baselines.cocomo import estimate_effort_cocomo


class CocomoRequest(PydanticBaseModel):
    """Input schema for the /baselines/cocomo endpoint."""

    function_points: float = Field(..., gt=0, description="Adjusted Function Points (AFP).")
    language: str = Field(..., description="Programming language for FP-to-SLOC conversion.")


@app.post("/baselines/cocomo")
def cocomo_baseline(request: CocomoRequest):
    """
    Estimate effort using the classic COCOMO II formula.
    Used as a baseline to compare against our ML model.
    """
    return estimate_effort_cocomo(
        function_points=request.function_points,
        language=request.language,
    )


# ============================================================
# BASELINE: Analogy-Based Estimation (k-NN)
# ============================================================
from costell.ml.baselines.analogy import estimate_effort_analogy


class AnalogyRequest(PydanticBaseModel):
    """Input schema for the /baselines/analogy endpoint."""

    function_points: float = Field(..., gt=0, description="Adjusted Function Points.")
    team_size: float = Field(..., gt=0, description="Number of people on the team.")
    duration: float = Field(..., gt=0, description="Project duration in months.")
    k_neighbors: int = Field(
        default=3, ge=1, le=10, description="Number of similar projects to average."
    )


@app.post("/baselines/analogy")
def analogy_baseline(request: AnalogyRequest):
    """
    Estimate effort by finding the k most similar historical projects and averaging their actuals.
    """
    try:
        return estimate_effort_analogy(
            function_points=request.function_points,
            team_size=request.team_size,
            duration=request.duration,
            k_neighbors=request.k_neighbors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# BASELINE: Monte-Carlo Simulation
# ============================================================
from costell.ml.baselines.monte_carlo import run_monte_carlo


class MonteCarloRequest(PydanticBaseModel):
    """Input schema for the /baselines/monte-carlo endpoint."""

    estimated_effort: float = Field(..., gt=0)
    team_size: float = Field(..., gt=0)
    duration: float = Field(..., gt=0)
    function_points: float = Field(..., gt=0)
    language: str = Field(...)
    dataset_source: str = Field(default="user_input")
    blended_hourly_rate: float = Field(..., gt=0)
    tooling_cost_per_month: float = Field(..., ge=0)
    cloud_cost_per_month: float = Field(..., ge=0)
    contingency_percent: float = Field(..., ge=0)
    n_simulations: int = Field(default=10000, ge=1000, le=50000)


@app.post("/baselines/monte-carlo")
def monte_carlo_baseline(request: MonteCarloRequest):
    """
    Run a Monte-Carlo simulation to generate a probability distribution of project costs.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    # 1. Get the P50 effort from the ML model
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
    p50_effort = float(model.predict(df)[0])

    # 2. We need historical residuals to simulate realistic variance.
    # In a production system, we'd pull these from the DB. For now, we'll use a realistic proxy.
    # The training MMRE was ~14.4%, so residuals typically range from 5% to 35%.
    residuals = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

    # 3. Calculate fixed costs (Tooling + Cloud)
    fixed_costs = (request.tooling_cost_per_month + request.cloud_cost_per_month) * request.duration

    # 4. Run the simulation
    result = run_monte_carlo(
        p50_effort=p50_effort,
        mre_residuals=residuals,
        blended_hourly_rate=request.blended_hourly_rate,
        fixed_costs=fixed_costs,
        contingency_percent=request.contingency_percent,
        n_simulations=request.n_simulations,
    )

    # Add the base effort to the response for reference
    result["base_p50_effort"] = round(p50_effort, 2)

    return result
