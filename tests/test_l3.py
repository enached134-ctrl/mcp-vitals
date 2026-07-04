"""L3 scoring + arg-validation are deterministic; the LLM is stubbed (no network)."""

from __future__ import annotations

import mcpvitals.l3_agent as l3
from mcpvitals.connect import Inventory, ToolInfo


def _inv() -> Inventory:
    return Inventory(target="test", tools=[
        ToolInfo("search", "Search the docs.", {"properties": {"q": {"type": "string"}},
                                                "required": ["q"]}),
        ToolInfo("add", "Add two numbers.", {"properties": {"a": {"type": "integer"},
                                                            "b": {"type": "integer"}},
                                             "required": ["a", "b"]}),
    ])


def test_args_valid_requires_all_required():
    tool = ToolInfo("add", "", {"properties": {"a": {}, "b": {}}, "required": ["a", "b"]})
    assert l3._args_valid(tool, {"a": 1, "b": 2})
    assert not l3._args_valid(tool, {"a": 1})
    assert not l3._args_valid(tool, {"a": 1, "b": ""})


def test_perfect_agent_scores_100(monkeypatch):
    monkeypatch.setattr(l3, "llm_available", lambda: True)
    monkeypatch.setattr(l3, "_generate_task", lambda tool: f"please use {tool.name}")
    # A perfect agent always picks the expected tool with valid args.
    def fake_pick(task, tools):
        name = task.split()[-1]
        by = {t.name: t for t in tools}
        args = {r: "x" for r in by[name].required}
        return name, args
    monkeypatch.setattr(l3, "_pick", fake_pick)
    res = l3.run(_inv())
    assert res.score == 100.0
    assert res.summary["tool_selection_accuracy"] == 1.0


def test_confused_agent_is_penalised(monkeypatch):
    monkeypatch.setattr(l3, "llm_available", lambda: True)
    monkeypatch.setattr(l3, "_generate_task", lambda tool: f"task for {tool.name}")
    # Always pick "search" regardless — half right, half confused.
    monkeypatch.setattr(l3, "_pick", lambda task, tools: ("search", {"q": "x"}))
    res = l3.run(_inv())
    assert res.score < 100
    assert any("→ search" in c for c in res.confusions)


def test_skips_without_key(monkeypatch):
    monkeypatch.setattr(l3, "llm_available", lambda: False)
    res = l3.run(_inv())
    assert res.score == 0.0
    assert "GEMINI_API_KEY" in res.note
