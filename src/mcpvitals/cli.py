"""mcp-vitals CLI — `mcpvitals grade <target>`."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, grade_letter
from .connect import inspect
from .l1_static import score as score_l1
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
    grade = grade_letter(l1.score)

    html = render(inv, l1)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    result = {
        "target": args.target,
        "grade": grade,
        "score": l1.score,
        "layers": {"L1": l1.score},
        "tools": [{"name": t.tool, "score": t.score} for t in l1.tools],
        "summary": l1.summary,
    }
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n  GRADE: {grade}  (L1 static score {l1.score:.0f}/100)")
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
    g.add_argument("--tolerate-error", action="store_true",
                   help="still write a report on connection failure instead of exiting 2")
    g.set_defaults(func=_grade)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
