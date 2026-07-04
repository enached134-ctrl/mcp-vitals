"""L4 · Adversarial — tool-poisoning and over-permission heuristics.

Tool-description poisoning (hidden instructions to the agent embedded in a tool's
description) and over-broad capabilities are real MCP attack surfaces. L4 scans the
enumerated descriptions, prompts, and resource names for these patterns. It never calls
the server. An optional hook can ingest findings from a dedicated security scanner
(e.g. Invariant mcp-scan) — L4 is complementary to those, not a replacement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .connect import Inventory

# (compiled pattern, human label, severity) — severity is the points deducted.
_INJECTION = [
    (re.compile(r"ignore\s+(all\s+|the\s+|any\s+)?(previous|prior|earlier|above)", re.I),
     "instruction-override phrasing", 30),
    (re.compile(r"do\s+not\s+(tell|inform|mention|reveal|disclose)", re.I),
     "concealment instruction to the agent", 30),
    (re.compile(r"\b(system|developer)\s*(prompt|message|:)", re.I),
     "role/system-injection marker", 20),
    (re.compile(r"you\s+(must|should|shall|have to|are required to)\b", re.I),
     "model-directed imperative inside a tool description", 12),
    (re.compile(r"<\|.*?\|>|\[/?INST\]|<<SYS>>|###\s*instruction", re.I),
     "prompt-format control tokens embedded", 15),
    (re.compile(r"[​‌‍⁠﻿‮]"),
     "hidden/invisible unicode characters", 25),
]
_OVER_PERM = re.compile(
    r"\b(exec(ute)?|eval|shell|subprocess|spawn|rm\s+-rf|delete\s+all|drop\s+table|"
    r"arbitrary\s+(code|command|file|path)|any\s+(file|path|url)|sudo|chmod)\b", re.I)


@dataclass
class Finding:
    where: str
    label: str
    severity: int


@dataclass
class LayerResult:
    score: float
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


def _scan_text(where: str, text: str) -> list[Finding]:
    out: list[Finding] = []
    if not text:
        return out
    for pat, label, sev in _INJECTION:
        if pat.search(text):
            out.append(Finding(where, label, sev))
    if _OVER_PERM.search(text):
        out.append(Finding(where, "broad/dangerous capability advertised", 18))
    return out


def score(inv: Inventory) -> LayerResult:
    findings: list[Finding] = []
    for t in inv.tools:
        findings += _scan_text(f"tool:{t.name}", f"{t.name} {t.description}")
        for p, s in t.params.items():
            findings += _scan_text(f"tool:{t.name}:{p}", (s or {}).get("description", ""))
    for pr in inv.prompts:
        findings += _scan_text(f"prompt:{pr.get('name', '?')}", pr.get("name", ""))
    for r in inv.resources:
        findings += _scan_text(f"resource:{r.get('name', '?')}", r.get("name", ""))

    penalty = min(100, sum(f.severity for f in findings))
    return LayerResult(
        score=round(100 - penalty, 1),
        findings=findings,
        summary={"findings": len(findings), "penalty": penalty},
    )
