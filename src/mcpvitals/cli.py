"""mcp-vitals CLI — `mcpvitals grade <target>`."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, combine, grade_letter
from .connect import inspect
from .l1_static import score as score_l1
from .l2_behavioral import run as run_l2
from .report import render


def _grade(args: argparse.Namespace) -> int:
    print(f"mcp-vitals {__version__} — connecting to: {args.target}")
    inv = inspect(args.target)
    if inv.error:
        print(f"  connection failed: {inv.error}", file=sys.stderr)
        if not args.tolerate_error:
            return 2
    print(f"  enumerated {len(inv.tools)} tools, {len(inv.resources)} resources, "
          f"{len(inv.prompts)} prompts")

    l1 = score_l1(inv)
    layers = {"L1": l1.score}

    l2 = None
    if args.behavioral and not inv.error:
        print("  running L2 behavioral suite "
              f"({'incl. write tools' if args.behavioral_write else 'read-only, safe'})...")
        l2 = run_l2(inv, include_write=args.behavioral_write)
        layers["L2"] = l2.score
        print(f"    L2: {l2.summary}")

    overall = combine(layers)
    grade = grade_letter(overall)

    html = render(inv, l1, l2)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    result = {
        "target": args.target,
        "grade": grade,
        "score": overall,
        "layers": layers,
        "tools": [{"name": t.tool, "score": t.score} for t in l1.tools],
        "summary": {"l1": l1.summary, "l2": (l2.summary if l2 else None)},
    }
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    detail = f"L1 {l1.score:.0f}" + (f" · L2 {l2.score:.0f}" if l2 else "")
    print(f"\n  GRADE: {grade}  (overall {overall:.0f}/100 · {detail})")
    for t in sorted(l1.tools, key=lambda x: x.score):
        print(f"    {grade_letter(t.score)}  {t.score:5.0f}  {t.tool}")
    print(f"\n  report: {args.out}   scores: {args.json_out}")

    if args.min_grade and grade > args.min_grade:  # letters: 'A' < 'B' < ... so > is worse
        print(f"  FAIL: grade {grade} below required minimum {args.min_grade}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="mcpvitals", description="Reliability grades for MCP servers")
    ap.add_argument("--version", action="version", version=f"mcp-vitals {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grade", help="grade an MCP server (http(s):// URL or stdio command)")
    g.add_argument("target", help='e.g. "python -m my_server" or "https://host/mcp"')
    g.add_argument("--out", default="report.html", help="HTML report path")
    g.add_argument("--json-out", default="score.json", help="score JSON path")
    g.add_argument("--min-grade", help="CI gate: fail if the grade is worse than this (e.g. B)")
    g.add_argument("--behavioral", action="store_true",
                   help="run the L2 behavioral suite (calls read-only tools)")
    g.add_argument("--behavioral-write", action="store_true",
                   help="also exercise write-ish tools — only for servers you run yourself")
    g.add_argument("--tolerate-error", action="store_true",
                   help="still write a report on connection failure instead of exiting 2")
    g.set_defaults(func=_grade)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
