"""Monte-Carlo simulation for project cost estimation."""

import numpy as np


def run_monte_carlo(
    p50_effort: float,
    mre_residuals: list[float],
    blended_hourly_rate: float,
    fixed_costs: float,
    contingency_percent: float,
    n_simulations: int = 10000,
) -> dict:
    """
    Run a Monte-Carlo simulation to generate a cost distribution.

    Args:
        p50_effort: The base effort estimate from the ML model.
        mre_residuals: Historical residuals (Absolute errors) from the ML model.
        blended_hourly_rate: Cost per hour.
        fixed_costs: Tooling + Cloud costs (already multiplied by duration).
        contingency_percent: Contingency buffer %.
        n_simulations: Number of iterations.

    Returns:
        A dict containing percentiles and the raw simulated costs.
    """
    if not mre_residuals:
        # Fallback if no residuals provided (e.g., 20% standard deviation)
        mre_residuals = [0.2]

    # 1. Randomly sample residuals for each simulation
    # This represents the "effort multiplier" (e.g., 1.1 = 10% overrun)
    sampled_mres = np.random.choice(mre_residuals, size=n_simulations, replace=True)

    # 2. Add randomness (some overruns, some underruns)
    # We randomly assign a positive or negative sign to simulate real-world variance
    signs = np.random.choice([-1, 1], size=n_simulations)
    multipliers = 1 + (sampled_mres * signs)

    # 3. Calculate simulated effort
    simulated_efforts = p50_effort * multipliers
    # Ensure effort doesn't drop below 0
    simulated_efforts = np.maximum(simulated_efforts, 0)

    # 4. Calculate simulated costs
    personnel_costs = simulated_efforts * blended_hourly_rate
    subtotals = personnel_costs + fixed_costs
    contingency = subtotals * (contingency_percent / 100.0)
    total_costs = subtotals + contingency

    # 5. Calculate percentiles
    percentiles = {
        "P10": np.percentile(total_costs, 10),
        "P50": np.percentile(total_costs, 50),
        "P80": np.percentile(total_costs, 80),
        "P90": np.percentile(total_costs, 90),
        "P95": np.percentile(total_costs, 95),
    }

    return {
        "n_simulations": n_simulations,
        "mean_cost": float(np.mean(total_costs)),
        "std_dev": float(np.std(total_costs)),
        "percentiles": {k: round(float(v), 2) for k, v in percentiles.items()},
        # Return a sample of 500 points for the frontend histogram to keep it fast
        "histogram_sample": np.random.choice(
            total_costs, size=min(500, n_simulations), replace=False
        ).tolist(),
    }
