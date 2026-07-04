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
