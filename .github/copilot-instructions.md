# Costell - AI-Powered Cost Estimation Engine

## Project Overview
Costell is an AI-powered cost estimation engine designed specifically for the AI-native development era. It replaces traditional estimation models (COCOMO, function points) that assume human-only development teams. 

## The Core Problem
Traditional models fail to account for AI-augmented development (Copilot, Cursor, LLMs). They do not capture the "AI Leverage Factor" or new AI infrastructure costs (API calls, GPU compute). IT projects still go over budget by 45% on average.

## The Solution
A user pastes a Project Requirement Document (PRD). Costell outputs a full budget breakdown (People, Tooling, Cloud/AI Infra) with a statistically calibrated confidence range (P50/P80/P90). 

**Analogy:** Google Maps provides a range ("30 to 40 minutes"), not an exact point estimate. Costell does this for project cost.

## Core Innovation: The AI Leverage Factor (ALF)
ALF is a per-task metric (0.0 to 1.0) quantifying how much AI accelerates specific development tasks.
- 0.0 - 0.2: AI is useless (e.g., novel distributed systems algorithms)
- 0.3 - 0.5: AI is moderately helpful (e.g., API integrations)
- 0.6 - 0.8: AI significantly accelerates (e.g., CRUD endpoints, unit tests)
- 0.9 - 1.0: AI nearly automates (e.g., boilerplate, config files)

**Formula:** `Adjusted_Effort = Base_Effort × (1 - ALF × AI_Adoption_Rate)`

## System Architecture (The 5 Engines)
1. **Scope Decomposition Engine:** LLM (Qwen 2.5) breaks the PRD into a Work Breakdown Structure (WBS). Pydantic enforces strict output validation. The LLM is NEVER allowed to output numeric estimates.
2. **AI Leverage Engine:** A secondary ML model predicts the ALF score and estimates the AI infrastructure cost for each task in the WBS.
3. **Effort & Cost Engine:** Uses CatBoost Regressor to predict base effort (person-days). MAPIE wraps CatBoost for conformal prediction (P50/P80/P90 intervals). SHAP generates explainability.
4. **Scenario & Decision Engine:** Monte-Carlo simulation for scenario comparison. Sliders for "what-if" analysis. LLM generates plain-language advisory.
5. **Calibration & Learning Engine:** Compares actuals from Jira/ERP against estimates to retrain models via online learning.

## Core Principle: AI Advises, Models Decide
The LLM is only used for scope decomposition and advisory. It must NEVER output a numeric cost. All math and cost outputs must come from deterministic ML models (CatBoost, MAPIE) and be validated by Pydantic schemas.

## Tech Stack
- **Data Processing:** Polars, DuckDB
- **ML:** CatBoost, MAPIE (Conformal Prediction), SHAP, Scikit-Learn
- **LLM:** Qwen 2.5, Pydantic v2
- **Backend:** FastAPI, SQLModel, Uvicorn
- **Frontend:** Reflex
- **Orchestration:** Prefect
- **DevOps:** Docker, GitHub Actions, Pytest, Ruff, Mypy
- **Data Sources:** ISBSG, SEERA, COCOMO, Desharnais datasets

## Folder Structure
- `src/costell/api/` - FastAPI routes and endpoints
- `src/costell/core/` - Security, exceptions, constants
- `src/costell/data/` - Ingestion, validation, feature engineering
- `src/costell/ml/` - Training, evaluation, inference, conformal prediction
- `src/costell/llm/` - LLM integration, prompts, guardrails, RAG
- `src/costell/services/` - Business logic (scope, AI leverage, effort, scenario)
- `src/costell/frontend/` - Reflex UI
- `tests/` - Unit and integration tests

## Coding Standards (Global & Project Rules)
- Always use Python type hints (e.g., `def estimate(prd: str) -> dict:`)
- Follow PEP 8 style guidelines. Use `ruff` for formatting and linting.
- Use `structlog` for structured logging instead of `print()`.
- Write docstrings for all public functions and classes.
- Prefer `pathlib` over `os.path` for file operations.
- Use `pytest` with clear arrange-act-assert structure.
- Never commit secrets or API keys; use `.env` files.
- Use conventional commits format (`feat:`, `fix:`, `docs:`, `chore:`).
- All data schemas must use Pydantic v2.
- All ML inference must return P50/P80/P90 intervals via MAPIE.
- Use `Polars` instead of Pandas for all DataFrame operations.
- Every service module in `src/costell/services/` must have a corresponding unit test.

## Current Status / Next Step
The project scaffolding is complete. The immediate next step is to create the configuration module (`src/costell/config.py`) using `pydantic-settings`, then move on to data ingestion for the SEERA dataset.