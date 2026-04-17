# lab7/test_agent.py
"""
Agent eval suite — Week 7
Jordan Rivera: AI Quality & Reliability Engineer

10 tasks across 4 categories.
Run: uv run pytest lab7/test_agent.py -v -m "not slow"
CI:  uv run pytest lab7/test_agent.py -v (all tests, real Claude)

Markers:
  slow     — makes real API calls, runs in CI only
  unit     — mocks tool calls, runs anywhere
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lab7.agent_loop import run_agent, execute_tool, TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_step_types(result: dict) -> list:
    return [s["type"] for s in result["steps"]]


def get_tool_names_called(result: dict) -> list:
    return [s["toolName"] for s in result["steps"] if s["type"] == "tool_call"]


def assert_structural_guarantees(result: dict, max_loops: int = 5):
    """Invariants that must hold on every agent run regardless of query."""
    assert "steps" in result
    assert "finalResponse" in result
    assert "loopsUsed" in result
    assert "terminatedEarly" in result

    # Hard loop ceiling
    assert result["loopsUsed"] <= max_loops, (
        f"loopsUsed {result['loopsUsed']} exceeded maxLoops {max_loops}"
    )

    # Valid step types only
    valid_types = {
        "planning", "tool_call", "tool_result",
        "synthesizing", "complete", "loop_limit", "error",
    }
    for step in result["steps"]:
        assert step["type"] in valid_types, f"Invalid step type: {step['type']}"

    # planning always first
    assert result["steps"][0]["type"] == "planning"

    # finalResponse never empty
    assert result["finalResponse"].strip()


# ---------------------------------------------------------------------------
# Canned responses for unit tests — no API calls
# ---------------------------------------------------------------------------

SEARCH_SUCCESS = {
    "error": False,
    "query": "refund policy",
    "results": "[1] source: refund_policy.txt\nRefunds available within 30 days.",
    "num_results": 1,
}

WEATHER_SUCCESS = {
    "error": False,
    "location": "Denver",
    "temperature_f": 62,
    "condition": "snowy",
    "humidity_pct": 31,
}

REMINDER_SUCCESS = {
    "error": False,
    "id": "test-abc123",
    "text": "Review PR",
    "time": "tomorrow at 9am",
    "created_at": "2026-04-17T09:00:00",
}

SEARCH_ERROR = {
    "error": True,
    "message": "Chroma is unavailable",
}

WEATHER_ERROR = {
    "error": True,
    "message": "Weather service is unavailable",
}


# ===========================================================================
# Category 1 — Unit tests (no API calls, mocked tools)
# These run in CI and locally. Fast, deterministic.
# ===========================================================================

class TestExecuteTool:
    """execute_tool contracts — allowlist, never raises, always returns dict."""

    def test_unknown_tool_returns_error(self):
        """Allowlist — unknown tool name rejected, never executed."""
        result = execute_tool("hallucinated_tool", {"query": "test"})
        assert result["error"] is True
        assert "Unknown tool" in result["message"]

    def test_unknown_tool_does_not_raise(self):
        """execute_tool never raises regardless of input."""
        result = execute_tool("drop_table", {"sql": "DROP TABLE users"})
        assert isinstance(result, dict)
        assert result["error"] is True

    def test_valid_tool_names_accepted(self):
        """All three registered tools are in the allowlist."""
        for name in ["search_documents", "get_current_weather", "save_reminder"]:
            assert name in TOOL_REGISTRY


class TestStructuralGuarantees:
    """Structural invariants — must hold on every run."""

    @pytest.mark.slow
    def test_planning_always_first(self):
        """planning step is always the first step."""
        result = run_agent("What is the refund policy?")
        assert result["steps"][0]["type"] == "planning"

    @pytest.mark.slow
    def test_final_response_never_empty(self):
        """finalResponse is never empty string."""
        result = run_agent("What is the refund policy?")
        assert result["finalResponse"].strip()

    @pytest.mark.slow
    def test_loops_used_within_bounds(self):
        """loopsUsed never exceeds maxLoops."""
        result = run_agent("What is the refund policy?")
        assert result["loopsUsed"] <= result["maxLoops"]

    @pytest.mark.slow
    def test_all_step_types_valid(self):
        """Every step has a valid type."""
        result = run_agent("What is the weather in Denver?")
        assert_structural_guarantees(result)


# ===========================================================================
# Category 2 — Tool routing (slow, real Claude)
# Does the model call the correct tool for each query?
# ===========================================================================

class TestToolRouting:

    @pytest.mark.slow
    def test_document_query_calls_search(self):
        """Refund policy query → search_documents called."""
        result = run_agent("What is the refund policy?")
        assert_structural_guarantees(result)
        tools_called = get_tool_names_called(result)
        assert "search_documents" in tools_called, (
            f"Expected search_documents, got: {tools_called}"
        )

    @pytest.mark.slow
    def test_weather_query_calls_weather(self):
        """Weather query → get_current_weather called."""
        result = run_agent("What is the weather in Chicago?")
        assert_structural_guarantees(result)
        tools_called = get_tool_names_called(result)
        assert "get_current_weather" in tools_called, (
            f"Expected get_current_weather, got: {tools_called}"
        )

    @pytest.mark.slow
    def test_reminder_query_calls_save_reminder(self):
        """Reminder query → save_reminder called."""
        result = run_agent("Remind me to review the PR tomorrow at 9am")
        assert_structural_guarantees(result)
        tools_called = get_tool_names_called(result)
        assert "save_reminder" in tools_called, (
            f"Expected save_reminder, got: {tools_called}"
        )

    @pytest.mark.slow
    def test_multi_tool_query_calls_multiple_tools(self):
        """Combined query → both search_documents and get_current_weather called."""
        result = run_agent(
            "What is the refund policy and what is the weather in Denver?"
        )
        assert_structural_guarantees(result)
        tools_called = get_tool_names_called(result)
        assert "search_documents" in tools_called, (
            f"search_documents missing from: {tools_called}"
        )
        assert "get_current_weather" in tools_called, (
            f"get_current_weather missing from: {tools_called}"
        )


# ===========================================================================
# Category 3 — Loop limit enforcement
# Hard ceiling must hold. Partial result returned, never an exception.
# ===========================================================================

class TestLoopLimit:

    @pytest.mark.slow
    def test_loop_limit_enforced(self):
        """Agent terminates at max_loops=1, returns partial result."""
        # max_loops=1 forces early termination on any multi-step task
        result = run_agent(
            "What is the refund policy and the weather in Denver "
            "and remind me about the PR?",
            max_loops=1,
        )
        # Must terminate — either naturally or at limit
        assert result["loopsUsed"] <= 1
        # finalResponse must exist — never an empty string or exception
        assert result["finalResponse"].strip()

    @pytest.mark.slow
    def test_loop_limit_terminates_gracefully(self):
        """loop_limit_reached step present when ceiling hit without completion."""
        result = run_agent(
            "What is the refund policy?",
            max_loops=1,
        )
        assert result["loopsUsed"] <= 1
        # If terminated early, loop_limit step must be present
        if result["terminatedEarly"]:
            step_types = get_step_types(result)
            assert "loop_limit" in step_types, (
                f"loop_limit step missing when terminatedEarly=True: {step_types}"
            )

    @pytest.mark.slow
    def test_normal_task_does_not_hit_limit(self):
        """Simple single-tool query completes well within default limit."""
        result = run_agent("What is the weather in Denver?")
        assert result["terminatedEarly"] is False
        assert result["loopsUsed"] < result["maxLoops"]


# ===========================================================================
# Category 4 — Failure modes
# Tool errors handled per system prompt tiering. No hallucination.
# ===========================================================================

class TestFailureModes:

    @pytest.mark.slow
    def test_search_error_stops_agent(self):
        """Tier 1: search_documents error → agent stops, reports unavailability."""
        with patch(
            "lab7.agent_loop.execute_tool",
            side_effect=lambda name, inp: (
                SEARCH_ERROR if name == "search_documents" else {}
            ),
        ):
            result = run_agent("What is the refund policy?")

        assert result["finalResponse"].strip()
        # Response must acknowledge unavailability, not fabricate content
        response_lower = result["finalResponse"].lower()
        assert any(
            phrase in response_lower
            for phrase in ["unavailable", "unable", "cannot", "error"]
        ), f"Expected unavailability language, got: {result['finalResponse'][:200]}"

    @pytest.mark.slow
    def test_weather_error_continues(self):
        """Tier 2: weather error → agent continues, notes limitation."""
        with patch(
            "lab7.agent_loop.execute_tool",
            side_effect=lambda name, inp: (
                WEATHER_ERROR if name == "get_current_weather"
                else execute_tool.__wrapped__(name, inp)
                if hasattr(execute_tool, "__wrapped__")
                else {"error": True, "message": "mocked"}
            ),
        ):
            result = run_agent("What is the weather in Denver?")

        # Agent must still produce a response — not crash
        assert result["finalResponse"].strip()
        assert result["loopsUsed"] <= result["maxLoops"]
