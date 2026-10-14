"""FastAPI application for the Costell estimation engine."""

from contextlib import asynccontextmanager

import pandas as pd
from catboost import CatBoostRegressor
from costell.api.schemas import EstimationRequest, EstimationResponse
from fastapi import FastAPI, HTTPException

from costell.config import settings

# Global variable to hold the model
model: CatBoostRegressor | None = None

# The calibrated margin we calculated in the previous step
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
    # Cleanup on shutdown (if any)
    model = None


app = FastAPI(
    title="Costell API",
    description="AI-powered cost estimation engine for the AI-native development era.",
    version=settings.project_version,
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model_loaded": model is not None}


@app.post("/estimate", response_model=EstimationResponse)
def estimate(request: EstimationRequest):
    """
    Predict effort with an 80% confidence interval.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    # Convert the request into a Pandas DataFrame for CatBoost
    df = pd.DataFrame([request.model_dump()])

    # Generate the point prediction (P50)
    p50 = float(model.predict(df)[0])

    # Calculate the 80% conformal interval
    p80_lower = max(p50 - Q_MARGIN, 0)  # Clip at 0, effort cannot be negative
    p80_upper = p50 + Q_MARGIN

    return EstimationResponse(
        p50_estimate=p50,
        p80_lower=p80_lower,
        p80_upper=p80_upper,
        confidence_level=0.8,
    )
