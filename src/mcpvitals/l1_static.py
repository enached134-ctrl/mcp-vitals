"""L1 · Static — deterministic schema-quality scoring for each tool.

No model calls, no server calls: this reads the enumerated tool schemas and applies
linter rules that decide how usable the definitions are for an LLM agent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .connect import Inventory, ToolInfo

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class Check:
    name: str
    ok: bool
    weight: int
    detail: str = ""


@dataclass
class ToolScore:
    tool: str
    score: float
    checks: list[Check] = field(default_factory=list)


@dataclass
class LayerResult:
    score: float  # 0..100
    tools: list[ToolScore] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


def _score_tool(t: ToolInfo) -> ToolScore:
    checks: list[Check] = []
    desc = (t.description or "").strip()
    params = t.params

    checks.append(Check("description present", bool(desc), 25))
    checks.append(Check("description is meaningful (≥20 chars)", len(desc) >= 20, 15,
                        f"{len(desc)} chars"))
    checks.append(Check("description ≠ tool name", desc.lower() != t.name.lower(), 5))
    checks.append(Check("tool name is clear (snake_case)", bool(_NAME_RE.match(t.name)), 10))

    if params:
        documented = [p for p, s in params.items() if (s or {}).get("description")]
        typed = [p for p, s in params.items() if (s or {}).get("type") or (s or {}).get("anyOf")]
        checks.append(Check(
            "every parameter is documented", len(documented) == len(params), 25,
            f"{len(documented)}/{len(params)} params have descriptions",
        ))
        checks.append(Check(
            "every parameter is typed", len(typed) == len(params), 15,
            f"{len(typed)}/{len(params)} params typed",
        ))
        checks.append(Check("required fields declared", bool(t.required) or len(params) == 0, 5,
                            f"required: {t.required or 'none'}"))
    else:
        # A no-argument tool can't fail param checks; award the param weight if it's
        # genuinely argument-free (common for status/health tools).
        checks.append(Check("parameters (none declared)", True, 45, "no arguments"))

    total = sum(c.weight for c in checks)
    got = sum(c.weight for c in checks if c.ok)
    pct = round(100 * got / total, 1) if total else 0.0
    return ToolScore(tool=t.name, score=pct, checks=checks)


def score(inv: Inventory) -> LayerResult:
    tools = [_score_tool(t) for t in inv.tools]
    agg = round(sum(t.score for t in tools) / len(tools), 1) if tools else 0.0
    passed = sum(1 for t in tools if t.score >= 80)
    return LayerResult(
        score=agg,
        tools=tools,
        summary={"tools": len(tools), "solid": passed, "weak": len(tools) - passed},
    )
