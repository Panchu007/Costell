"""COCOMO II baseline estimator for comparison against our ML model."""

# Language-specific SLOC per Function Point ratios.
# Source: QSM Function Point Language Table, ISBSG benchmarks.
# "3GL" and "4GL" are generic fallback categories.
FP_TO_SLOC = {
    "Python": 50,
    "Java": 53,
    "C++": 53,
    "C#": 54,
    "JavaScript": 47,
    "Assembly": 320,
    "3GL": 53,
    "4GL": 20,
    "Unknown": 53,  # Default to 3GL
}

# COCOMO II Post-Architecture constants
COCOMO_A = 2.94
COCOMO_E = 0.91  # Simplified exponent (assumes standard scale factors)
EAF_DEFAULT = 1.0  # Effort Adjustment Factor (simplified)
HOURS_PER_PERSON_MONTH = 152.0


def estimate_effort_cocomo(
    function_points: float,
    language: str,
    eaf: float = EAF_DEFAULT,
) -> dict:
    """
    Estimate effort using the COCOMO II formula.

    Args:
        function_points: Adjusted Function Points (AFP).
        language: Programming language for FP-to-SLOC conversion.
        eaf: Effort Adjustment Factor (default 1.0 for a standard project).

    Returns:
        A dict with the estimate in person-months and person-hours,
        plus the intermediate KSLOC value.
    """
    sloc_per_fp = FP_TO_SLOC.get(language, FP_TO_SLOC["Unknown"])
    total_sloc = function_points * sloc_per_fp
    ksloc = total_sloc / 1000.0

    effort_pm = COCOMO_A * (ksloc**COCOMO_E) * eaf
    effort_hours = effort_pm * HOURS_PER_PERSON_MONTH

    return {
        "model": "COCOMO II",
        "sloc_per_fp": sloc_per_fp,
        "total_sloc": round(total_sloc, 2),
        "ksloc": round(ksloc, 4),
        "effort_person_months": round(effort_pm, 2),
        "effort_hours": round(effort_hours, 2),
    }
