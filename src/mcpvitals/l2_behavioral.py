"""L2 · Behavioral — generate a test suite from each tool's schema and run it.

Safety (see the benchmark ethics in the README): by default only tools that look
**read-only** by name are actually called. Write-ish tools are reported as skipped
unless `include_write=True` — which you should only pass for servers you run yourself.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass, field
from typing import Any

from .connect import Inventory, ToolInfo, _client

READ_HINTS = ("get", "list", "search", "read", "find", "query", "fetch", "ask", "describe",
              "count", "lookup", "echo", "add", "sum", "divide", "slow", "status", "health")
WRITE_HINTS = ("create", "delete", "update", "set", "write", "send", "post", "put",
               "remove", "ingest", "insert", "drop", "exec", "run", "publish")

CALL_TIMEOUT = 15.0
LATENCY_THRESHOLD_MS = 5000.0


def is_read_only(name: str) -> bool:
    n = name.lower()
    if any(n.startswith(w) or f"_{w}" in n for w in WRITE_HINTS):
        return False
    return any(n.startswith(r) or r in n for r in READ_HINTS)


def _synth(schema: dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return "test"
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    return {
        "string": "test", "integer": 1, "number": 1.0, "boolean": True,
        "array": [], "object": {},
    }.get(t, "test")


@dataclass
class Case:
    kind: str          # "valid" | "missing_required" | "wrong_type"
    args: dict[str, Any]


def gen_cases(tool: ToolInfo) -> list[Case]:
    params, required = tool.params, tool.required
    valid = {p: _synth(s) for p, s in params.items()}
    cases = [Case("valid", dict(valid))]
    if required:
        drop = dict(valid)
        drop.pop(required[0], None)
        cases.append(Case("missing_required", drop))
    # wrong type: flip the first string param to an int (or vice-versa)
    for p, s in params.items():
        if (s or {}).get("type") == "string":
            bad = dict(valid)
            bad[p] = 12345
            cases.append(Case("wrong_type", bad))
            break
    return cases


@dataclass
class ToolBehavior:
    tool: str
    called: bool
    valid_ok: int = 0
    valid_total: int = 0
    graceful_errors: int = 0
    invalid_total: int = 0
    crashes: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    note: str = ""

    @property
    def p50(self) -> float:
        return round(statistics.median(self.latencies_ms), 1) if self.latencies_ms else 0.0

    @property
    def p95(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return round(s[min(len(s) - 1, int(0.95 * len(s)))], 1)


@dataclass
class LayerResult:
    score: float
    tools: list[ToolBehavior] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _classify(exc: BaseException) -> str:
    n = type(exc).__name__.lower()
    if isinstance(exc, asyncio.TimeoutError) or "timeout" in n:
        return "timeout"
    if "toolerror" in n or "mcperror" in n or "validation" in n:
        return "graceful"
    return "crash"


async def _run(inv: Inventory, include_write: bool) -> LayerResult:
    behaviors: list[ToolBehavior] = []
    client = _client(inv.target)
    async with client:
        for tool in inv.tools:
            if not include_write and not is_read_only(tool.name):
                behaviors.append(
                    ToolBehavior(tool.name, called=False, note="skipped (write-ish; safety)")
                )
                continue
            b = ToolBehavior(tool.name, called=True)
            for case in gen_cases(tool):
                loop = asyncio.get_event_loop()
                start = loop.time()
                try:
                    call = client.call_tool(tool.name, case.args)
                    await asyncio.wait_for(call, timeout=CALL_TIMEOUT)
                    outcome = "ok"
                except BaseException as exc:  # noqa: BLE001 - we classify all failures
                    outcome = _classify(exc)
                elapsed = (loop.time() - start) * 1000
                if case.kind == "valid":
                    b.valid_total += 1
                    if outcome == "ok":
                        b.valid_ok += 1
                        b.latencies_ms.append(elapsed)
                    elif outcome in ("timeout", "crash"):
                        b.crashes += 1
                else:
                    b.invalid_total += 1
                    if outcome == "graceful":
                        b.graceful_errors += 1
                    elif outcome in ("timeout", "crash"):
                        b.crashes += 1
            behaviors.append(b)
    return _score(behaviors)


def _score(behaviors: list[ToolBehavior]) -> LayerResult:
    called = [b for b in behaviors if b.called]
    if not called:
        return LayerResult(score=0.0, tools=behaviors,
                           summary={"called": 0, "note": "no read-only tools to exercise"})
    vt = sum(b.valid_total for b in called) or 1
    it = sum(b.invalid_total for b in called) or 1
    success = sum(b.valid_ok for b in called) / vt
    graceful = sum(b.graceful_errors for b in called) / it
    all_lat = [ms for b in called for ms in b.latencies_ms]
    p95 = sorted(all_lat)[min(len(all_lat) - 1, int(0.95 * len(all_lat)))] if all_lat else 0.0
    over = max(0.0, p95 - LATENCY_THRESHOLD_MS)
    fast = 1.0 if p95 <= LATENCY_THRESHOLD_MS else max(0.0, 1 - over / 10000)
    crash_free = 1.0 if sum(b.crashes for b in called) == 0 else 0.0
    score = round(100 * (0.40 * success + 0.30 * graceful + 0.20 * fast + 0.10 * crash_free), 1)
    return LayerResult(
        score=score, tools=behaviors,
        summary={"called": len(called), "success_rate": round(success, 3),
                 "graceful_rate": round(graceful, 3), "p95_ms": round(p95, 1)},
    )


def run(inv: Inventory, include_write: bool = False) -> LayerResult:
    return asyncio.run(_run(inv, include_write))
