"""L3 · Agent-usability — the layer nobody else measures.

Give a model the server's full tool list and a realistic task, and ask it to pick the
right tool and construct valid arguments. That tests whether the *descriptions and
schemas* are good enough for an agent to actually use — not whether the server is safe
(security scanners) or its definitions are tidy (static graders).

L3 never calls the server. It reasons over the enumerated schemas with an LLM judge,
so it is safe on any target. Requires an LLM key (GEMINI_API_KEY by default).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from .connect import Inventory, ToolInfo

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def llm_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _llm(prompt: str, system: str | None = None, want_json: bool = False) -> str:
    import requests
    import urllib3

    urllib3.disable_warnings()
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    body: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.2}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if want_json:
        body["generationConfig"]["responseMimeType"] = "application/json"
    r = requests.post(
        _GEMINI_URL.format(model=model), params={"key": key}, json=body, timeout=60, verify=False
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@dataclass
class Trial:
    expected: str
    task: str
    picked: str = ""
    args_valid: bool = False
    correct: bool = False


@dataclass
class LayerResult:
    score: float
    trials: list[Trial] = field(default_factory=list)
    confusions: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    note: str = ""


def _tool_catalog(tools: list[ToolInfo]) -> str:
    lines = []
    for t in tools:
        params = ", ".join(
            f"{p}: {(s or {}).get('type', 'any')}" for p, s in t.params.items()
        ) or "(none)"
        lines.append(f"- {t.name}({params}) — {t.description or 'no description'}")
    return "\n".join(lines)


def _generate_task(tool: ToolInfo) -> str:
    prompt = (
        f"A software tool is named `{tool.name}` and described as: "
        f"\"{tool.description or 'no description'}\".\n"
        "Write ONE short, natural user request (a single sentence) that a person would "
        "type to an AI assistant, such that fulfilling it clearly requires THIS tool. "
        "Do not mention the tool name. Reply with only the sentence."
    )
    return _llm(prompt).strip().strip('"')


def _pick(task: str, tools: list[ToolInfo]) -> tuple[str, dict[str, Any]]:
    catalog = _tool_catalog(tools)
    system = (
        "You are an AI agent choosing which tool to call. Given the available tools and a "
        "user request, pick the single most appropriate tool and construct its arguments. "
        'Reply with JSON only: {"tool": "<name>", "arguments": { ... }}.'
    )
    prompt = (
        f"Available tools:\n{catalog}\n\nUser request: {task}\n\n"
        "Which tool, with what arguments?"
    )
    raw = _llm(prompt, system=system, want_json=True)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {"tool": "", "arguments": {}}
    return str(data.get("tool", "")), (data.get("arguments") or {})


def _args_valid(tool: ToolInfo, args: dict[str, Any]) -> bool:
    if not tool.required:
        return True
    return all(r in args and args[r] not in (None, "") for r in tool.required)


def run(inv: Inventory, max_tools: int = 12) -> LayerResult:
    if not llm_available():
        return LayerResult(score=0.0, note="skipped — set GEMINI_API_KEY to run L3")
    tools = inv.tools[:max_tools]
    by_name = {t.name: t for t in tools}
    trials: list[Trial] = []
    confusions: list[str] = []

    for tool in tools:
        try:
            task = _generate_task(tool)
            picked, args = _pick(task, tools)
        except Exception as exc:  # noqa: BLE001
            return LayerResult(score=0.0, note=f"LLM error: {type(exc).__name__}: {exc}")
        tr = Trial(expected=tool.name, task=task, picked=picked)
        tr.correct = picked == tool.name
        tr.args_valid = tr.correct and _args_valid(by_name.get(picked, tool), args)
        if not tr.correct and picked:
            confusions.append(f"{tool.name} → {picked}")
        trials.append(tr)

    n = len(trials) or 1
    sel = sum(t.correct for t in trials) / n
    argv = sum(t.args_valid for t in trials) / n
    score = round(100 * (0.7 * sel + 0.3 * argv), 1)
    return LayerResult(
        score=score, trials=trials, confusions=confusions,
        summary={"tasks": len(trials), "tool_selection_accuracy": round(sel, 3),
                 "argument_validity": round(argv, 3)},
    )
