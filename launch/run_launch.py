"""Launch run — grade a curated set of public, locally-runnable MCP servers.

Ethics (see the README): official reference servers only, run locally from their
published packages, read-only behavioral tests, no auth bypass. Produces a league
table + STATE-OF-MCP.md. Requires: node/npx, GEMINI_API_KEY (for L3).

Run:  python launch/run_launch.py
"""

from __future__ import annotations

import json
import pathlib
import tempfile

from mcpvitals import combine, grade_letter
from mcpvitals.connect import inspect
from mcpvitals.l1_static import score as score_l1
from mcpvitals.l2_behavioral import run as run_l2
from mcpvitals.l3_agent import llm_available
from mcpvitals.l3_agent import run as run_l3

_TMP = tempfile.mkdtemp(prefix="mcpvitals-fs-")

# Official reference servers — public, open-source, safe to run locally.
SERVERS = [
    ("everything", "npx -y @modelcontextprotocol/server-everything"),
    ("memory", "npx -y @modelcontextprotocol/server-memory"),
    ("sequential-thinking", "npx -y @modelcontextprotocol/server-sequential-thinking"),
    ("filesystem", f"npx -y @modelcontextprotocol/server-filesystem {_TMP}"),
]

OUT = pathlib.Path(__file__).resolve().parent


def grade_one(name: str, target: str) -> dict:
    print(f"\n=== {name} ===")
    inv = inspect(target)
    if inv.error:
        print(f"  connection failed: {inv.error}")
        return {"name": name, "error": inv.error}
    l1 = score_l1(inv)
    layers = {"L1": l1.score}
    l2 = run_l2(inv, include_write=False)
    layers["L2"] = l2.score
    row = {"name": name, "tools": len(inv.tools),
           "L1": l1.score, "L2": l2.score, "l2_summary": l2.summary}
    if llm_available():
        l3 = run_l3(inv)
        if not l3.note:
            layers["L3"] = l3.score
            row["L3"] = l3.score
            row["l3_summary"] = l3.summary
            row["confusions"] = l3.confusions
    overall = combine(layers)
    row["overall"] = overall
    row["grade"] = grade_letter(overall)
    print(f"  {row['grade']}  {overall:.0f}  (tools={row['tools']} · {layers})")
    return row


def write_report(rows: list[dict]) -> None:
    graded = [r for r in rows if "overall" in r]
    graded.sort(key=lambda r: r["overall"], reverse=True)
    (OUT / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = ["# State of MCP Reliability — a starter league table",
             "",
             "Official MCP reference servers, graded by "
             "[mcp-vitals](https://github.com/enached134-ctrl/mcp-vitals) "
             "(static + behavioral + agent-usability). Read-only, run locally. Not a "
             "security audit — this measures whether the tools *work* and whether an "
             "agent can *use* them.",
             "",
             "| Server | Grade | Overall | L1 | L2 | L3 | Tools |",
             "|---|---|---|---|---|---|---|"]
    for r in graded:
        c1 = f"{r['L1']:.0f}" if "L1" in r else "–"
        c2 = f"{r['L2']:.0f}" if "L2" in r else "–"
        c3 = f"{r['L3']:.0f}" if "L3" in r else "–"
        lines.append(
            f"| {r['name']} | **{r['grade']}** | {r['overall']:.0f} | "
            f"{c1} | {c2} | {c3} | {r.get('tools', '–')} |"
        )
    failed = [r for r in rows if "error" in r]
    if failed:
        lines += ["", "### Did not start", ""]
        lines += [f"- `{r['name']}` — {r['error']}" for r in failed]

    confusions = [(r["name"], c) for r in graded for c in r.get("confusions", [])]
    if confusions:
        lines += ["", "### Agent tool-confusions observed (L3)", "",
                  "Where a model picked the wrong tool for a task — a description-clarity signal:"]
        lines += [f"- **{n}**: `{c}`" for n, c in confusions]

    lines += [
        "",
        "### Method & honest limitations",
        "",
        "- **L2** generates test inputs from JSON schemas only — it has no semantic idea of "
        "what a *meaningful* argument is. A tool that needs a specific well-formed payload "
        "(e.g. sequential-thinking's single `sequentialthinking` tool) can score low on L2 "
        "because the synthetic input isn't valid *content*, even though the server is fine. "
        "Read that as \"needs richer, tool-aware test cases\", not \"broken server\".",
        "- **L3** tasks are auto-generated (one per tool) — a starting signal, not a "
        "human-labeled benchmark. The confusions above are real, but a curated calibration "
        "set (a later milestone) would make the accuracy numbers authoritative.",
        "- Read-only, official reference servers, run locally. This is a *starter* table; the "
        "harness (`launch/run_launch.py`) grades any list of targets.",
    ]
    (OUT / "STATE-OF-MCP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT / 'STATE-OF-MCP.md'} ({len(graded)} graded, {len(failed)} failed)")


def main() -> None:
    rows = []
    for name, target in SERVERS:
        try:
            rows.append(grade_one(name, target))
        except Exception as exc:  # noqa: BLE001
            print(f"  {name} crashed: {exc}")
            rows.append({"name": name, "error": f"{type(exc).__name__}: {exc}"})
    write_report(rows)


if __name__ == "__main__":
    main()
