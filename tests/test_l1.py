"""L1 scoring is deterministic and rewards well-documented tools — no network needed."""

from __future__ import annotations

from mcpvitals import grade_letter
from mcpvitals.connect import Inventory, ToolInfo
from mcpvitals.l1_static import score


def _inv(*tools: ToolInfo) -> Inventory:
    return Inventory(target="test", tools=list(tools))


def test_well_documented_tool_scores_high():
    good = ToolInfo(
        name="search_docs",
        description="Search the indexed documentation and return the top matching passages.",
        schema={
            "properties": {
                "query": {"type": "string", "description": "The natural-language search query."},
                "k": {"type": "integer", "description": "How many results to return."},
            },
            "required": ["query"],
        },
    )
    result = score(_inv(good))
    assert result.score == 100.0
    assert grade_letter(result.score) == "A"


def test_undocumented_params_are_penalised():
    weak = ToolInfo(
        name="ask",
        description="Answer a question with the multi-agent RAG pipeline and return citations.",
        schema={"properties": {"question": {"type": "string"}}, "required": ["question"]},
    )
    result = score(_inv(weak))
    # Description checks pass but the undocumented param costs the documentation weight.
    assert 60 <= result.score < 90
    assert any(c.name == "every parameter is documented" and not c.ok
               for c in result.tools[0].checks)


def test_missing_description_tanks_the_grade():
    bad = ToolInfo(name="do", description="", schema={})
    result = score(_inv(bad))
    assert grade_letter(result.score) in {"D", "F"}


def test_no_arg_tool_not_penalised_for_params():
    health = ToolInfo(
        name="health", description="Return server health and readiness status.", schema={}
    )
    result = score(_inv(health))
    assert result.score >= 80
