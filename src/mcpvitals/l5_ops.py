"""L5 · Ops — operational hygiene: transport security, error handling, API discipline.

Offline: derived from how the server connects and what it exposes, plus the L2 behavioral
signal when it was run. Modest by design — a local stdio server can't be judged on TLS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .connect import Inventory


@dataclass
class Check:
    name: str
    ok: bool
    weight: int
    detail: str = ""


@dataclass
class LayerResult:
    score: float
    checks: list[Check] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)


def score(inv: Inventory, graceful_rate: float | None = None) -> LayerResult:
    checks: list[Check] = []

    target = inv.target
    if target.startswith("https://"):
        checks.append(Check("transport is encrypted (https)", True, 35, "https"))
    elif target.startswith("http://"):
        checks.append(Check("transport is encrypted", False, 35, "plain http — use https"))
    else:
        checks.append(Check("transport (local stdio — TLS n/a)", True, 35, "stdio"))

    checks.append(Check("exposes at least one tool", len(inv.tools) > 0, 20,
                        f"{len(inv.tools)} tools"))

    # Input typing discipline — a proxy for a well-specified API contract.
    all_params = [(p, s) for t in inv.tools for p, s in t.params.items()]
    if all_params:
        typed = sum(1 for _, s in all_params if (s or {}).get("type") or (s or {}).get("anyOf"))
        checks.append(Check("tool inputs are typed", typed == len(all_params), 20,
                            f"{typed}/{len(all_params)} typed"))
    else:
        checks.append(Check("tool inputs (no arguments to type)", True, 20, "n/a"))

    if graceful_rate is not None:
        checks.append(Check("errors are handled gracefully", graceful_rate >= 0.9, 25,
                            f"graceful rate {graceful_rate:.0%}"))
    else:
        checks.append(Check("error handling (run --behavioral to measure)", True, 0,
                            "not measured"))

    total = sum(c.weight for c in checks)
    got = sum(c.weight for c in checks if c.ok)
    return LayerResult(
        score=round(100 * got / total, 1) if total else 0.0,
        checks=checks,
        summary={"transport": "https" if target.startswith("https")
                 else ("http" if target.startswith("http") else "stdio")},
    )
