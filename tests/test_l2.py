"""L2 test generation, safety classification, and scoring — all deterministic, no network."""

from __future__ import annotations

from mcpvitals.connect import ToolInfo
from mcpvitals.l2_behavioral import (
    ToolBehavior,
    _score,
    gen_cases,
    is_read_only,
)


def test_read_only_classification():
    assert is_read_only("search_docs")
    assert is_read_only("get_user")
    assert is_read_only("list_items")
    assert not is_read_only("delete_user")
    assert not is_read_only("create_invoice")
    assert not is_read_only("ingest")


def test_gen_cases_covers_valid_and_invalid():
    tool = ToolInfo(
        name="search",
        description="Search things.",
        schema={
            "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
            "required": ["query"],
        },
    )
    cases = gen_cases(tool)
    kinds = {c.kind for c in cases}
    assert "valid" in kinds
    assert "missing_required" in kinds  # required present -> a drop case
    assert "wrong_type" in kinds        # a string param -> a type-flip case
    valid = next(c for c in cases if c.kind == "valid")
    assert set(valid.args) == {"query", "k"}
    missing = next(c for c in cases if c.kind == "missing_required")
    assert "query" not in missing.args


def test_score_rewards_success_and_graceful():
    good = ToolBehavior(
        tool="echo", called=True, valid_ok=1, valid_total=1,
        graceful_errors=2, invalid_total=2, latencies_ms=[10.0],
    )
    result = _score([good])
    assert result.score >= 90
    assert result.summary["success_rate"] == 1.0
    assert result.summary["graceful_rate"] == 1.0


def test_score_penalises_crashes():
    crashy = ToolBehavior(
        tool="bad", called=True, valid_ok=0, valid_total=1,
        graceful_errors=0, invalid_total=1, crashes=2, latencies_ms=[],
    )
    result = _score([crashy])
    assert result.score < 50


def test_no_callable_tools_scores_zero():
    skipped = ToolBehavior(tool="delete_all", called=False, note="skipped")
    result = _score([skipped])
    assert result.score == 0.0
    assert result.summary["called"] == 0
