"""mcp-vitals — reliability grades for MCP servers."""

from __future__ import annotations

__version__ = "0.1.0"

# Layer weights toward the final grade. Only L1 is implemented in M1; the rest are
# declared so the report can show the roadmap and the weighting is explicit.
LAYER_WEIGHTS = {"L1": 15, "L2": 30, "L3": 25, "L4": 15, "L5": 15}


def grade_letter(score: float) -> str:
    """Map a 0–100 score to an A–F grade."""
    for cutoff, letter in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= cutoff:
            return letter
    return "F"


def combine(layer_scores: dict[str, float]) -> float:
    """Weighted overall score across the layers that actually ran."""
    weights = {k: LAYER_WEIGHTS[k] for k in layer_scores if k in LAYER_WEIGHTS}
    total = sum(weights.values())
    if not total:
        return 0.0
    return round(sum(layer_scores[k] * weights[k] for k in weights) / total, 1)
